#!/usr/bin/env python
"""WSE 通道的域间一致性诊断（Card 1 的机制补充，纯 CPU、无需训练）。

问题：为什么修正通道（w = 床面 + h）在合成域内小幅变化，却让真实考卷零样本
迁移全面坍缩？本脚本量化两个候选通道在三个数据域上的**特征语义**：

  旧通道 legacy: w = area + h      （elevation_feature_idx: 0）
  修正通道 fixed: w = bed  + h      （elevation_feature_idx: 1）

对每个域统计：
  * w 的均值/标准差/取值范围；
  * w 与 bed、与水深 h 的相关系数（谁主导该通道）；
  * 逐边水位差 Δw 的方差分解：corr(Δw, Δh)（越接近 1 说明该通道越接近"水深
    梯度"通道，越接近 0 说明被静床地形主导）。

判读要点：若 legacy 在两个域上都 ≈ "水深主导"（corr(w,h) 高、corr(Δw,Δh) 高），
而 fixed 在合成域是水深/水面主导、在真实域是**床面主导**，则零样本坍缩的机制
就是"通道语义域间不一致"（训练分布与测试分布错位），而非"方向机制本身无益"。

    python scripts/diagnose_wse_channel_domains.py \
        --out docs/wlev1_channel_domain_shift.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.utils.io import load_scenario  # noqa: E402

DOMAINS = {
    "合成域(域内)": "data/scenarios_2d_family",
    "大域(12.8km)": "data/scenarios_2d_larger",
    "真实考卷": "data/real_cases/exams_2d",
}


def stats_for(npz: Path) -> dict:
    sc = load_scenario(npz)
    st = sc.node_static
    area, bed = st[:, 0], st[:, 1]
    h = sc.dynamic[:, :, 0]                       # [T, N]
    w_legacy = area[None, :] + h
    w_fixed = bed[None, :] + h

    src, dst = sc.edge_index
    und = src < dst
    s, d = src[und], dst[und]
    dh = h[:, s] - h[:, d]
    dw_legacy = w_legacy[:, s] - w_legacy[:, d]
    dw_fixed = w_fixed[:, s] - w_fixed[:, d]

    def corr(a, b):
        a, b = np.asarray(a, dtype=np.float64).ravel(), np.asarray(b, dtype=np.float64).ravel()
        if a.std() == 0 or b.std() == 0:
            return float("nan")
        return float(np.corrcoef(a, b)[0, 1])

    bed_b = np.broadcast_to(bed[None, :], h.shape)
    return {
        "scenario": sc.name,
        "nodes": int(sc.num_nodes),
        "frames": int(h.shape[0]),
        "bed_relief_m": float(bed.max() - bed.min()),
        "depth_max_m": float(h.max()),
        "depth_mean_wet_m": float(h[h > 1e-3].mean()),
        "legacy": {
            "w_std": float(w_legacy.std()),
            "corr_w_bed": corr(w_legacy, bed_b),
            "corr_w_depth": corr(w_legacy, bed_b * 0 + np.broadcast_to(h, h.shape)),
            "corr_dw_dh": corr(dw_legacy, dh),
        },
        "fixed": {
            "w_std": float(w_fixed.std()),
            "corr_w_bed": corr(w_fixed, bed_b),
            "corr_w_depth": corr(w_fixed, np.broadcast_to(h, h.shape)),
            "corr_dw_dh": corr(dw_fixed, dh),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="docs/wlev1_channel_domain_shift.json")
    args = ap.parse_args()

    rows = []
    for label, root in DOMAINS.items():
        files = sorted(Path(root).glob("*.npz"))[:3]      # 每域抽 3 个场景
        for f in files:
            r = stats_for(f)
            r["domain"] = label
            rows.append(r)
            print(f"{label:<14} {r['scenario']:<14} 床面起伏 {r['bed_relief_m']:8.2f} m  "
                  f"最大水深 {r['depth_max_m']:6.2f} m")
            for ch in ("legacy", "fixed"):
                c = r[ch]
                print(f"    {ch:<7} w_std={c['w_std']:9.2f}  corr(w,bed)={c['corr_w_bed']:+.3f}  "
                      f"corr(w,h)={c['corr_w_depth']:+.3f}  corr(Δw,Δh)={c['corr_dw_dh']:+.3f}")

    # 汇总（按域平均）
    summary = {}
    for label in DOMAINS:
        sel = [r for r in rows if r["domain"] == label]
        summary[label] = {
            "bed_relief_m": float(np.mean([r["bed_relief_m"] for r in sel])),
            "legacy_corr_w_depth": float(np.mean([r["legacy"]["corr_w_depth"] for r in sel])),
            "legacy_corr_dw_dh": float(np.mean([r["legacy"]["corr_dw_dh"] for r in sel])),
            "fixed_corr_w_depth": float(np.mean([r["fixed"]["corr_w_depth"] for r in sel])),
            "fixed_corr_w_bed": float(np.mean([r["fixed"]["corr_w_bed"] for r in sel])),
            "fixed_corr_dw_dh": float(np.mean([r["fixed"]["corr_dw_dh"] for r in sel])),
        }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "scenarios": rows}, indent=2,
                              ensure_ascii=False), encoding="utf-8")
    print("\n=== 分域汇总 ===")
    for label, s in summary.items():
        print(f"{label:<14} 床面起伏 {s['bed_relief_m']:8.2f} m | "
              f"legacy: corr(w,h)={s['legacy_corr_w_depth']:+.3f} corr(Δw,Δh)={s['legacy_corr_dw_dh']:+.3f} | "
              f"fixed: corr(w,h)={s['fixed_corr_w_depth']:+.3f} "
              f"corr(w,bed)={s['fixed_corr_w_bed']:+.3f} corr(Δw,Δh)={s['fixed_corr_dw_dh']:+.3f}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
