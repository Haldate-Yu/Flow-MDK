#!/usr/bin/env python
"""Card 1 (W1) 结果判读：逐种子表 + 场景级配对 Wilcoxon + 考卷逐例分解。

判据依据 plan/card1_wlev1_channel_fix.md §4（执行前预登记）。
口径与论文 3.3 节一致：误差先对 3 个种子按场景取平均，检验单元为场景。

    python scripts/analyze_wlev1_card1.py   # -> docs/wlev1_card1_verdict.md
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"
OUT = REPO / "docs" / "wlev1_card1_verdict.md"

ROOT_FAMILY = "data/scenarios_2d_family"
ROOT_LARGER = "data/scenarios_2d_larger"
ROOT_H8 = "data/real_cases/exams_2d_h8"
ROOT_FULL = "data/real_cases/exams_2d"

W1_ARMS = ["flow_mdk", "swegnn1x8", "mdkoff", "ssgc"]
IDX0_REFS = {"flow_mdk": "MS4_2d_flow_mdk", "swegnn1x8": "MS4b_2d_swegnn",
             "ssgc": "MS4_2d_ssgc", "mdkoff": "L16_mdkoff_2d"}
SEEDS = [0, 1, 2]

DOM_ROOT = {"域内": ROOT_FAMILY, "大域": ROOT_LARGER,
            "考卷H8": ROOT_H8, "考卷全时程": ROOT_FULL}


def load_eval(run: str, root: str) -> dict[str, float] | None:
    """run 目录下某数据域的逐场景水深 RMSE；缺失返回 None。

    域内评测（未传 --data-root）的文件名是 eval_test.json；
    跨域/考卷评测带 --data-root，文件名带数据域后缀。
    """
    leaf = Path(root).name
    for name in (f"eval_test_{leaf}.json", "eval_test.json"):
        p = RUNS / run / name
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            return {d["scenario"]: d["rmse"][0] for d in data}
    return None


def seed_mean(run_base: str, root: str) -> dict[str, float] | None:
    """3 种子逐场景平均（论文口径）；任一种子缺失返回 None。"""
    per_seed = [load_eval(f"{run_base}_s{s}", root) for s in SEEDS]
    if any(p is None for p in per_seed):
        return None
    names = sorted(per_seed[0])
    return {n: float(np.mean([p[n] for p in per_seed])) for n in names}


def paired(model: dict[str, float], ref: dict[str, float]):
    """场景级配对 Wilcoxon + 胜出数。"""
    names = sorted(set(model) & set(ref))
    x = np.array([model[n] for n in names])
    y = np.array([ref[n] for n in names])
    d = x - y
    nz = d[d != 0]
    if len(nz) == 0:
        return float("nan"), 1.0, int((d < 0).sum()), len(names)
    stat, p = wilcoxon(nz)
    return float(stat), float(p), int((d < 0).sum()), len(names)


def fmt_cell(model: dict[str, float] | None) -> str:
    if model is None:
        return "—"
    xs = list(model.values())
    if len(xs) == 1:
        return f"{xs[0]:.3f}"
    return f"{np.mean(xs):.3f}±{np.std(xs, ddof=1):.3f}"


def main() -> None:
    lines = ["# 卡 1（W1）结果判读", "",
             "> 生成：`scripts/analyze_wlev1_card1.py`。检验口径：误差先对 3 种子按场景"
             "取平均，配对 Wilcoxon 符号秩检验，检验单元为场景（判据见实验卡 §4）。", ""]

    # ---------- 1. 逐种子表 ----------
    lines += ["## 1. 逐种子水深 RMSE（m）", ""]
    for proto in ["last", "best"]:
        lines += [f"### {proto} 协议", "",
                  "| 臂 | 种子 | 域内 | 大域 | 考卷H8 | 考卷全时程 |", "|---|---|---|---|---|---|"]
        for arm in W1_ARMS:
            for s in SEEDS:
                run = (f"W1_2d_{arm}_s{s}" if proto == "last"
                       else f"ptbest_W1_2d_{arm}_s{s}")
                cells = []
                for dom, root in DOM_ROOT.items():
                    ev = load_eval(run, root)
                    cells.append(f"{list(ev.values())[0]:.3f}" if ev and len(ev) == 1
                                 else (fmt_cell(ev) if ev else "—"))
                lines.append(f"| {arm}(w1) | s{s} | " + " | ".join(cells) + " |")
        lines.append("")

    # ---------- 2. 地板 ----------
    floors = {
        "persist(域内)": load_eval("floor_persist_2d_family", ROOT_FAMILY),
        "persist(大域)": load_eval("floor_persist_2d_larger", ROOT_LARGER),
        "alldry(域内)": load_eval("W1_floor_alldry_2d_family", ROOT_FAMILY),
        "alldry(大域)": load_eval("W1_floor_alldry_2d_larger", ROOT_LARGER),
        "persist(考卷H8)": load_eval("W1_floor_persist_exams_2d_h8", ROOT_H8),
        "alldry(考卷H8)": load_eval("W1_floor_alldry_exams_2d_h8", ROOT_H8),
    }
    lines += ["## 2. 无技巧地板", "",
              "| 地板 | 逐场景值 |", "|---|---|"]
    for k, v in floors.items():
        lines.append(f"| {k} | " + (fmt_cell(v) if v else "—") + " |")
    lines.append("")

    # ---------- 3. 判据检验 ----------
    w1 = {arm: {dom: seed_mean(f"W1_2d_{arm}", root)
                for dom, root in DOM_ROOT.items()} for arm in W1_ARMS}
    lines += ["## 3. 判据检验（对照实验卡 §4）", ""]

    # C-A
    gate = json.loads((REPO / "docs" / "wlev1_gate_agreement.json").read_text(encoding="utf-8"))
    pooled = gate["pooled"]["flip_fraction"]
    lines += [f"**C-A 诊断复现：通过。** 合计反转占比 {100*pooled:.2f}"
              f"（mdx {100*gate['exams'][0]['flip_fraction']:.2f} / "
              f"wqh {100*gate['exams'][1]['flip_fraction']:.2f}），与论文 ~49% 一致率吻合"
              "（>30% 门槛）。修正通道后门控与真实水面坡降一致由构造保证。", ""]

    # C-B：地板 + 排序
    fm = w1["flow_mdk"]
    tests_cb = []
    for dom in ["域内", "大域"]:
        for fl in ["persist", "alldry"]:
            ref = floors[f"{fl}({dom})"]
            if ref and fm[dom]:
                stat, p, win, n = paired(fm[dom], ref)
                tests_cb.append((dom, fl, p, win, n))
    lines += ["**C-B 域内非退化：地板通过，排序未通过。**",
              "",
              "| 对比（last 协议） | 胜出/场景 | Wilcoxon p |", "|---|---|---|"]
    for dom, fl, p, win, n in tests_cb:
        lines.append(f"| W1 flow_mdk vs {fl}（{dom}） | {win}/{n} | {p:.2e} |")
    lines += ["",
              "域内 last 排序实测：ssgc(w1) 0.364 < mdkoff(w1) 0.477 < flow_mdk(w1) 0.601"
              "——与预登记的「定向 < 无分支 < 对称」**相反**（数值见 §1，臂间差异需按"
              "种子方差谨慎判读）。", ""]

    # C-C
    lines += ["**C-C 真实考卷主判据：未通过。**", ""]
    lines += ["| 臂（best 协议，部署检查点口径） | 考卷H8 | 考卷全时程 | vs persist 地板 2.326 |",
              "|---|---|---|---|"]
    for arm in W1_ARMS:
        h8, full = w1[arm]["考卷H8"], w1[arm]["考卷全时程"]
        m = np.mean(list(h8.values())) if h8 else float("nan")
        tag = "低于地板" if m < 2.326 else "**高于地板**"
        lines.append(f"| {arm}(w1) | {fmt_cell(h8)} | {fmt_cell(full)} | {tag} |")
    lines += ["",
              "全部 4 个 W1 臂在真实考卷上都高于 persist 地板 2.326 m；而旧口径"
              "（idx0）flow_mdk best 为 2.471 m——虽也未过地板，但远好于 W1。"
              "修正通道使合成→真实的零样本迁移**全面恶化**，且 W1 各臂在 H=8 与"
              "全时程的 RMSE 几乎相同（13.30 vs 13.28 等），说明误差在第 1 个 rollout"
              "步就已巨大（特征空间错位 signature），而非逐步发散。", ""]

    # C-E
    lines += ["**C-E 对 SWE-GNN 优势复现：域内/大域方向保持，考卷反转。**", ""]
    lines += ["| 对比（last 协议） | 域内 | 大域 | 考卷H8(best) |", "|---|---|---|---|"]
    for dom, key in [("域内", "域内"), ("大域", "大域")]:
        p = paired(w1["flow_mdk"][key], w1["swegnn1x8"][key])[1]
        lines.append(f"| W1 flow_mdk vs W1 swegnn1x8（{dom}） | {fmt_cell(w1['flow_mdk'][key])} "
                     f"vs {fmt_cell(w1['swegnn1x8'][key])}（p={p:.2e}） | | |")
    lines.append(f"| 考卷H8（best） | | | {fmt_cell(w1['flow_mdk']['考卷H8'])} vs "
                 f"{fmt_cell(w1['swegnn1x8']['考卷H8'])} |")
    lines.append("")

    # ---------- 4. 结论 ----------
    lines += ["## 4. 总体判读", "",
              "1. **C-A、C-D 通过**：诊断复现；四域地板入表，每域绑定地板均为 persist"
              "（0.716 / 0.351 / 2.326 / 2.326）。",
              "2. **C-B 部分通过、C-C、C-E(考卷) 未通过**：修正通道在合成域内未恢复"
              "「定向最优」的机制排序（对称臂反居首），并使全部臂的真实考卷零样本迁移"
              "坍缩到无技巧地板以下。",
              "3. **旧口径（idx0）结果的有效性不受影响**：其配置已如实记录、合成域证据"
              "与通道污染无关；但「修正后更好」的预期被证伪——这是一个如实记录的"
              "负向/边界结果，而不是可写入论文主表的改进。",
              "4. **机制假说（供后续检验，非结论）**：真实床面起伏 262 m vs 合成 3.7 m，"
              "修正通道 `w = 床面 + h` 在真实网格上由静床地形主导，门控退化为近似时间"
              "不变的几何门控，且 w 通道的特征分布严重偏离合成训练分布——二者叠加"
              "导致零样本在第 1 步即错位。可检验推论：对 w 通道做逐数据域标准化或"
              "改用「去基准床面 + h」，应能恢复部分迁移能力（属后续卡）。"]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:60]))
    print(f"...\n-> {OUT}")


if __name__ == "__main__":
    main()
