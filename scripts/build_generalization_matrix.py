#!/usr/bin/env python
"""Assemble the M5 generalization matrix from runs/results.csv (paper budget).

Rows   = model x checkpoint protocol (last.pt / best.pt), mean±std over seeds
Cols  = evaluation domains (in-domain, generalization subsets, zero-shot,
        real exams), as recorded by the registry (data_root + split).

Only paper-budget run families are folded (G=64): partA_paper_* / L3_B1_paper_*
(single-seed s0 rounds), MS4_partA_* / MS4_B1_* / MS4_2d_* / MS5_partA_2x8mdk_*
(3 seeds), L16_mdkoff_* / E61_partA_full_* (ablation/recipe arms when present).
Local-budget rounds (G=32 L2/L3/MS_*/E6_partA) are excluded by design.

    python scripts/build_generalization_matrix.py          # -> docs/generalization_matrix.{md,csv}
"""

from __future__ import annotations

import csv
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "runs" / "results.csv"
OUT_MD = REPO / "docs" / "generalization_matrix.md"
OUT_CSV = REPO / "docs" / "generalization_matrix.csv"

# domain label <- (data_root, split)
DOMAINS = [
    ("1D 域内 A-test", ("data/scenarios_partA_v2", "test")),
    ("1D →A2 未见水情", ("data/scenarios_partA_v2", "A2_test")),
    ("1D →A3 更大域", ("data/scenarios_partA_v2", "A3_test")),
    ("1D B1 真实域内", ("data/real_cases/family_all", "test")),
    ("1D →B2 真实考卷", ("data/real_cases/scenarios_1d", "val")),
    ("1D →fam_mdx 零样本", ("data/real_cases/family_mdx", "test")),
    ("1D →fam_zxh 零样本", ("data/real_cases/family_zxh", "test")),
    ("1D →fam_wqh 零样本", ("data/real_cases/family_wqh", "test")),
    ("2D 域内", ("data/scenarios_2d_family", "test")),
    ("2D →真实考卷 H=8", ("data/real_cases/exams_2d_h8", "test")),
    ("2D →真实考卷 全时程", ("data/real_cases/exams_2d", "test")),
]

# run-name family whitelist (paper budget) -> display model
FAMILIES = [
    (re.compile(r"^partA_paper_(swegnn|flow_mdk|gcn|gat)_"), None),
    (re.compile(r"^L3_B1_paper_(swegnn|flow_mdk|ssgc)_"), None),
    (re.compile(r"^MS4_partA_(swegnn|flow_mdk|gcn|gat)_s\d+$"), None),
    (re.compile(r"^MS4_B1_(swegnn|flow_mdk|ssgc)_s\d+$"), None),
    (re.compile(r"^MS4_2d_(swegnn|flow_mdk|ssgc)_s\d+$"), None),
    (re.compile(r"^MS5_partA_2x8mdk_s\d+$"), "2x8mdk"),
    (re.compile(r"^L16_mdkoff_(partA|2d)_s\d+$"), "flow_mdk(-MDK)"),
    (re.compile(r"^E61_partA_full_s\d+$"), "flow_mdk(E6配方)"),
    # U-Net 2D baseline (round 3): real-exam zero-shot cells stay empty by
    # design — a grid CNN cannot ingest the unstructured 65k-node meshes
    # (UNetSurrogate refuses non-grid node counts); noted in the matrix doc.
    (re.compile(r"^unet_2d_s\d+$"), "unet"),
]
MODEL_PATTERNS = [  # order matters: first hit wins
    (re.compile(r"2x8mdk"), "2x8mdk"),
    (re.compile(r"mdkoff"), "flow_mdk(-MDK)"),
    (re.compile(r"E61|E6配方"), "flow_mdk(E6配方)"),
    (re.compile(r"unet"), "unet"),
    (re.compile(r"flow_mdk"), "flow_mdk"),
    (re.compile(r"ssgc"), "ssgc"),
    (re.compile(r"swegnn"), "swegnn"),
    (re.compile(r"gcn"), "gcn"),
    (re.compile(r"gat"), "gat"),
]
SEED_RE = re.compile(r"_s(\d+)$")
STAMP_RE = re.compile(r"_\d{8}_\d{6}$")


def parse_run(run: str) -> tuple[str, str, str] | None:
    """run name -> (model, protocol, seed) or None if not a paper-budget row."""
    if run.startswith("ptbest_"):
        protocol, run = "best", run[len("ptbest_"):]
    elif run.startswith("ptema_"):
        protocol, run = "ema", run[len("ptema_"):]
    else:
        protocol = "last"
    if not any(p.match(run) for p, _ in FAMILIES):
        return None
    run = STAMP_RE.sub("", run)  # timestamped single-seed rounds = s0
    m = SEED_RE.search(run)
    seed = m.group(1) if m else "0"
    base = SEED_RE.sub("", run)
    for pat, name in MODEL_PATTERNS:
        if pat.search(base):
            return name, protocol, seed
    return None


def main() -> None:
    rows = list(csv.DictReader(open(REGISTRY, newline="", encoding="utf-8")))
    # (model, protocol, domain) -> {seed: h_rmse}
    cell = defaultdict(dict)
    n_dropped = 0
    for r in rows:
        if r["kind"] != "eval" or not r["rmse"]:
            continue
        parsed = parse_run(r["run"])
        if parsed is None:
            n_dropped += 1
            continue
        model, protocol, seed = parsed
        key = (r["data_root"], r["split"])
        label = next((lab for lab, k in DOMAINS if k == key), None)
        if label is None:
            continue
        h = float(r["rmse"].split(";")[0])
        cell[(model, protocol, label)][seed] = h

    def fmt(vals: dict[str, float]) -> str:
        if not vals:
            return "—"
        xs = list(vals.values())
        if len(xs) == 1:
            return f"{xs[0]:.3f}"
        return f"{st.mean(xs):.3f}±{st.stdev(xs):.3f}"

    models = sorted({m for m, _, _ in cell},
                    key=lambda m: (MODEL_PATTERNS and [n for _, n in MODEL_PATTERNS].index(m)
                                   if m in [n for _, n in MODEL_PATTERNS] else 99))
    labels = [lab for lab, _ in DOMAINS]

    lines = [
        "# M5 泛化矩阵 · h-RMSE（m，paper budget，registry 自动生成）",
        "",
        "> 生成：`python scripts/build_generalization_matrix.py`（runs/results.csv → 本表）。"
        "只折叠 G=64 论文预算 run 家族；last/best 双协议，跨种子 mean±std（单种子为单值）。"
        "行为模型 × 协议，列为评测域（域内 → 泛化子集 → 真实域/考卷）。人工判读见 "
        "[results_partA_swe.md](results_partA_swe.md)。",
        "",
    ]
    csv_lines = ["model,protocol," + ",".join(labels)]
    for protocol, title in [("last", "last.pt 协议"), ("best", "best.pt 协议")]:
        lines += [f"## {title}", "",
                  "| model | " + " | ".join(labels) + " |",
                  "|---|" + "---|" * len(labels)]
        for m in models:
            cells = [fmt(cell.get((m, protocol, lab), {})) for lab in labels]
            if all(c == "—" for c in cells):
                continue
            lines.append(f"| {m} | " + " | ".join(cells) + " |")
            csv_lines.append(f"{m},{protocol}," + ",".join(
                ";".join(f"{v:.6f}" for _, v in sorted(cell.get((m, protocol, lab), {}).items()))
                for lab in labels))
        lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    OUT_CSV.write_text("\n".join(csv_lines), encoding="utf-8")
    print(f"[matrix] {len(cell)} (model, protocol, domain) cells from {REGISTRY}")
    print(f"[matrix] {n_dropped} eval rows outside the paper-budget whitelist (excluded)")
    print(f"[matrix] wrote {OUT_MD}")
    print(f"[matrix] wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
