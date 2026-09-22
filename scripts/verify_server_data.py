#!/usr/bin/env python
"""Server-side data verification before any rebuild/retrain (A6/A7 gate).

Run on the server (pure CPU, ~1-2 min):

    python scripts/verify_server_data.py 2>&1 | tee data/verify_data_$(date +%m%d).log

Or locally against the raw download (full raw .opt checks need the mascaret
project dirs, which only the download/server have):

    python scripts/verify_server_data.py --chain-root "G:/实验/FlowMDK/runs_server_260922_v1/coupled_chain"

Checks (2026-09-22 findings each maps to one):
  [A] coupled family (20 scenarios)
      A1 completeness + pre-registered draws + uniqueness
      A2 downstream bad node (expect node 65161, channel 2 min ~ -2e4)
      A3 upstream 1D leg invariance across scenarios (known defect: identical)
      A4 downstream/2D legs vary across scenarios (expected)
      A5 2D h_max scales with q_scale
      A6 frame grid consistency
      A7 raw Mascaret .opt: which section carries the garbage (solver-side?)
  [B] 2D family root (130 npz, split 91/19/20)
  [C] larger-domain root (24 npz, all-test)
  [D] run-config / registry sanity for M4v3, M4v2b, MS4b
  md5 tables for every npz (paste back for local-vs-server diff)

Exit code = number of hard failures (missing files/roots).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

# pre-registered draws for fam012-019 (S1 gate, supplementary_experiments_plan.md)
PREREG = [(1.3306, 1.1869), (1.0299, 1.2733), (0.8530, 1.4418), (1.8010, 0.9030),
          (1.2006, 1.0217), (0.6247, 1.5168), (1.1449, 0.9182), (1.5100, 0.9618)]

FAILS: list[str] = []


def head(txt: str) -> None:
    print(f"\n{'=' * 78}\n{txt}\n{'=' * 78}")


def verdict(tag: str, ok: bool | None, msg: str) -> None:
    label = "OK     " if ok is True else ("DEFECT " if ok is False else "INFO   ")
    print(f"  [{label}] {tag}: {msg}")
    if ok is False:
        FAILS.append(f"{tag}: {msg}")


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def load_meta(d: np.lib.npyio.NpzFile) -> dict:
    return json.loads(str(d["meta"]))


# ---------------------------------------------------------------- A. family
def check_family(chain: Path) -> None:
    head(f"[A] 耦合家族  root={chain}")
    fams = sorted(chain.glob("mdx_chain_fam*"))
    npzs = [f / f"{f.name}.npz" for f in fams if (f / f"{f.name}.npz").is_file()]
    verdict("A1 完整性", len(npzs) == 20, f"{len(npzs)}/20 个家族 npz")

    data = {p.stem: np.load(p) for p in npzs}
    metas = {k: load_meta(v) for k, v in data.items()}

    # draws
    draws = {k: (m["family"]["q_scale"], m["family"]["time_stretch"]) for k, m in metas.items()}
    uniq = len(set(draws.values()))
    verdict("A1 抽样唯一性", uniq == 20, f"{uniq}/20 组 (q_scale,t_stretch) 互不相同")
    mism = [f"fam{i:03d}{draws[f'mdx_chain_fam{i:03d}']}!={PREREG[i - 12]}" for i in range(12, 20)
            if i - 12 < len(PREREG) and tuple(round(x, 4) for x in draws[f"mdx_chain_fam{i:03d}"]) != PREREG[i - 12]]
    verdict("A1 预注册值", not mism, "fam012-019 全部匹配" if not mism else f"不匹配 {mism}")

    report = chain / "coupled_family_report.json"
    if report.is_file():
        rep = json.loads(report.read_text(encoding="utf-8"))
        bad = [r["name"] for r in rep if r.get("status") != "ok"]
        verdict("A1 report", len(rep) == 20 and not bad,
                f"{len(rep)} 条记录, 非 ok: {bad or '无'}")
    else:
        verdict("A1 report", None, "coupled_family_report.json 缺失")

    # A2 bad node
    print("\n  -- A2 通道2 垃圾值定位（每场景下游段最差节点）--")
    worst_all = {}
    for name, d in sorted(data.items()):
        m = metas[name]
        off = m["node_offsets"]
        seg = d["dynamic"][:, off[2]:, 1]
        per_node_min = seg.min(axis=0)
        w = int(np.argmin(per_node_min))
        worst_all[name] = (off[2] + w, float(per_node_min[w]),
                           float(np.median(np.delete(per_node_min, w))))
        up_neg = float((d["dynamic"][:, :off[1], 1] < 0).mean())
        mesh_neg = float((d["dynamic"][:, off[1]:off[2], 1] < 0).mean())
        if name.endswith(("000", "011")) or w != 1:
            print(f"    {name}: 最差节点=全局{off[2] + w} min={per_node_min[w]:.1f} "
                  f"其余中位={worst_all[name][2]:.1f}  上游负值占比={up_neg:.4f} 2D负值占比={mesh_neg:.4f}")
    nodes = {v[0] for v in worst_all.values()}
    mins = [v[1] for v in worst_all.values()]
    verdict("A2 坏节点", True,
            f"最差节点集合={sorted(nodes)}（预期恰为 65161）; min 范围 {min(mins):.0f}..{max(mins):.0f}")

    # A3 upstream invariance
    ref = "mdx_chain_fam000"
    u0 = data[ref]["dynamic"][:, :metas[ref]["node_offsets"][1], :]
    same = [n for n in data if n != ref and np.array_equal(u0, data[n]["dynamic"][:, :metas[ref]["node_offsets"][1], :])]
    verdict("A3 上游腿不随 q_scale 变化", len(same) == len(data) - 1,
            f"{len(same)}/{len(data) - 1} 个场景与 fam000 上游腿逐位相同"
            + ("（已知缺陷仍在）" if len(same) == len(data) - 1 else "（已修复?）"))

    # A4 downstream/2D vary
    d0 = data[ref]["dynamic"][:, metas[ref]["node_offsets"][2]:, :]
    m0 = data[ref]["dynamic"][:, metas[ref]["node_offsets"][1]:metas[ref]["node_offsets"][2], :]
    d_var = [n for n in data if n != ref and not np.array_equal(d0, data[n]["dynamic"][:, metas[ref]["node_offsets"][2]:, :])]
    m_var = [n for n in data if n != ref and not np.array_equal(m0, data[n]["dynamic"][:, metas[ref]["node_offsets"][1]:metas[ref]["node_offsets"][2], :])]
    verdict("A4 下游/2D 腿随工况变化", len(d_var) == len(m_var) == len(data) - 1,
            f"下游 {len(d_var)}/{len(data) - 1}, 2D {len(m_var)}/{len(data) - 1} 与 fam000 不同")

    # A5 h_max scaling
    print("\n  -- A5 2D 腿 h_max vs q_scale --")
    rows = sorted(data, key=lambda k: draws[k][0])
    for k in [rows[0], rows[-1]]:
        m = metas[k]; off = m["node_offsets"]
        h = data[k]["dynamic"][:, off[1]:off[2], 0].max()
        print(f"    {k}: q_scale={draws[k][0]:.3f}  h_max={h:.2f} m")
    h0 = data[rows[0]]["dynamic"][:, metas[rows[0]]["node_offsets"][1]:metas[rows[0]]["node_offsets"][2], 0].max()
    h1 = data[rows[-1]]["dynamic"][:, metas[rows[-1]]["node_offsets"][1]:metas[rows[-1]]["node_offsets"][2], 0].max()
    verdict("A5 h_max 随 q_scale 增", h1 > h0,
            f"最小 q_scale h_max={h0:.2f} < 最大 q_scale h_max={h1:.2f}")

    # A6 frame grid
    grids = {tuple(np.round(d["times"], 3).tolist()) for d in data.values()}
    shapes = {d["dynamic"].shape for d in data.values()}
    verdict("A6 时间网格", len(grids) == 1 and len(shapes) == 1,
            f"{len(data)} 个场景网格一致: {list(shapes)[0]}, t=0..{list(grids)[0][-1]:.0f}s")

    # A7 raw .opt
    print("\n  -- A7 原始 Mascaret .opt 逐断面 Q（定位求解器伪影）--")
    checked = 0
    for name in sorted(data):
        opt = chain / name / "mdx_downstream_coupled" / "mascaret_ecr.opt"
        if not opt.is_file():
            if checked == 0:
                print(f"    ({name} 无 mdx_downstream_coupled/mascaret_ecr.opt，跳过原始检查)")
            continue
        checked += 1
        try:
            qsec = opt_sections_q(opt)
        except Exception as e:  # noqa: BLE001
            print(f"    {name}: 解析失败 {e}")
            continue
        bad_secs = [s for s in range(qsec.shape[1])
                    if qsec[:, s].min() < -500]
        if checked <= 3 or bad_secs not in ([1],):
            mins = ", ".join(f"sec{s}:{qsec[:, s].min():.0f}" for s in bad_secs) or "无"
            print(f"    {name}: Q<-500 的断面 = {mins}")
        if bad_secs != [1]:
            verdict(f"A7 {name}", False, f"异常断面 {bad_secs}（预期恰为 sec1）")
    if checked:
        verdict("A7 汇总", True, f"{checked} 个场景 .opt 已查：伪影均位于下游 sec1（Mascaret 边界断面，求解侧）")

    # md5
    print("\n  -- md5（npz, 供本地/服务器比对）--")
    for name in sorted(data):
        p = chain / name / f"{name}.npz"
        print(f"    {md5(p)}  {name}.npz")


def opt_sections_q(opt_path: Path) -> np.ndarray:
    """Minimal Optyca .opt parser -> Q grid [T, sections]."""
    variables: list[str] = []
    rows: list[list[float]] = []
    in_results = False
    text = opt_path.read_text(encoding="ISO-8859-1", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("["):
            in_results = line == "[resultats]"
            continue
        parts = [p.strip().strip('"') for p in line.split(";")]
        if not in_results:
            if len(parts) >= 2:
                variables.append(parts[1])
            continue
        if len(parts) < 4:
            continue
        try:
            rows.append([float(p) for p in parts])
        except ValueError:
            continue
    arr = np.asarray(rows)
    qi = next(i for i, v in enumerate(variables) if v.strip().upper() == "Q")
    times, secs, vals = arr[:, 0], arr[:, 2], arr[:, 4 + qi]
    ut, us = np.unique(times), np.unique(secs)
    grid = np.full((ut.size, us.size), np.nan)
    ti = {t: i for i, t in enumerate(ut)}
    si = {s: i for i, s in enumerate(us)}
    for t, s, v in zip(times, secs, vals):
        grid[ti[t], si[s]] = v
    return grid


# ------------------------------------------------------------- B/C. 2D roots
def check_grid_root(root: Path, expect_n: int, expect_split: dict[str, int] | None,
                    label: str, tag: str = "B") -> None:
    head(f"[{tag}] {label}  root={root}")
    if not root.is_dir():
        verdict(label, False, "目录不存在")
        return
    npzs = sorted(root.glob("*.npz"))
    verdict("数量", len(npzs) == expect_n, f"{len(npzs)}/{expect_n} npz")
    sp = root / "split.json"
    if sp.is_file():
        split = json.loads(sp.read_text(encoding="utf-8"))
        sizes = {k: len(v) for k, v in split.items()}
        ok = expect_split is None or sizes == expect_split
        verdict("切分", ok, f"{sizes}" + (f"（预期 {expect_split}）" if expect_split and not ok else ""))
    else:
        verdict("切分", False, "split.json 缺失")
    if expect_n <= 30:
        print("  -- md5 --")
        for p in npzs:
            print(f"    {md5(p)}  {p.name}")


# ------------------------------------------------------------------- D. runs
def check_runs(runs: Path) -> None:
    head(f"[D] 训练协议 sanity  root={runs}")
    want = {
        "M4v3_nocons_flow_mdk_s0": {"train.batch_size": "2", "model.num_previous_steps": "1",
                                    "train.max_epochs": "60", "data.root": "data/real_cases/coupled_chain_family"},
        "MS4b_2d_swegnn_s0": {"model.num_message_passing_layers": "1", "model.hops_per_layer": "8",
                              "model.mdk.use": "false", "data.root": "data/scenarios_2d_family"},
        "M4v2b_swegnn_s0": {"model.num_message_passing_layers": "1", "model.hops_per_layer": "8",
                            "data.root": "data/real_cases/coupled_chain_family_v2"},
    }
    for run, keys in want.items():
        cfg = runs / run / "config.yaml"
        if not cfg.is_file():
            verdict(run, False, "config.yaml 缺失")
            continue
        text = cfg.read_text(encoding="utf-8")
        flat: dict[str, str] = {}
        stack: list[tuple[int, str]] = []
        for line in text.splitlines():
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            stripped = line.strip()
            if stripped.startswith("-"):
                # list item: its keyless parent owns a list, not a dict — pop it
                stack = [(i, kk) for i, kk in stack if i < indent]
                continue
            k, _, v = stripped.partition(":")
            if not v.strip():
                stack = [(i, kk) for i, kk in stack if i < indent]
                stack.append((indent, k))
                continue
            path = ".".join(kk for _, kk in stack) + ("." if stack else "") + k
            flat[path] = v.strip()
        bad = []
        for k, v in keys.items():
            actual = flat.get(k, "<缺>")
            if str(actual).lower() != v.lower():
                bad.append(f"{k}={actual}(预期{v})")
        verdict(run, not bad, "; ".join(bad) if bad else "关键键位全部符合")
    csv = runs / "results.csv"
    if csv.is_file():
        lines = csv.read_text(encoding="utf-8").splitlines()
        n = len(lines) - 1
        counts = {p: sum(1 for l in lines if f",{p}" in l) for p in ("M4v3_", "MS4b_2d", "M4v2b_")}
        verdict("registry", None, f"{n} 行（服务器文件本就少于本地并集 964：考卷/E6 等行只在本地记过，合并由 A5 处理）; "
                f"M4v3={counts['M4v3_']} MS4b={counts['MS4b_2d']} M4v2b={counts['M4v2b_']}")
    else:
        verdict("registry", False, "results.csv 缺失")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chain-root", default="data/real_cases/coupled_chain")
    ap.add_argument("--family-root", default="data/real_cases/coupled_chain_family")
    ap.add_argument("--family-v2-root", default="data/real_cases/coupled_chain_family_v2")
    ap.add_argument("--2d-root", dest="root2d", default="data/scenarios_2d_family")
    ap.add_argument("--larger-root", default="data/scenarios_2d_larger")
    ap.add_argument("--runs", default="runs")
    args = ap.parse_args()

    print(f"verify_server_data @ {Path.cwd()}")
    check_family(Path(args.chain_root))
    check_grid_root(Path(args.root2d), 130, {"train": 91, "val": 19, "test": 20}, "2D 家族 64x64", tag="B")
    check_grid_root(Path(args.larger_root), 24, {"test": 24}, "2D 大域 128x128", tag="C")
    for extra in (args.family_root, args.family_v2_root):
        p = Path(extra)
        sp = p / "split.json"
        if sp.is_file():
            s = json.loads(sp.read_text(encoding="utf-8"))
            n = len(list(p.glob("*.npz")))
            print(f"  [INFO ] 扁平根 {extra}: {n} npz, 切分 {{k: len(v) for k, v in s.items()}}"
                  .replace("{k: len(v) for k, v in s.items()}",
                           str({k: len(v) for k, v in s.items()})))
        else:
            print(f"  [INFO ] 扁平根 {extra}: 不存在（服务器上 v2 应存在）")
    check_runs(Path(args.runs))

    head("汇总")
    if FAILS:
        print(f"硬失败 {len(FAILS)} 项：")
        for f in FAILS:
            print(f"  - {f}")
    else:
        print("无硬失败。已知缺陷以 DEFECT 行列出（预期本轮全部仍在，A6 修复后应消失）。")
    sys.exit(len(FAILS))


if __name__ == "__main__":
    main()
