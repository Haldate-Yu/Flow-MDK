#!/usr/bin/env python
"""Assemble the M5 generalization matrix from runs/results.csv (paper budget).

Rows   = model x checkpoint protocol (last.pt / best.pt), mean±std over seeds
Cols  = evaluation domains (in-domain, generalization subsets, zero-shot,
        real exams), as recorded by the registry (data_root + split).

Only paper-budget run families are folded (G=64): partA_paper_* / L3_B1_paper_*
(single-seed s0 rounds), MS4_partA_* / MS4_B1_* / B1v2_* / MS4_2d_* /
MS5_partA_2x8mdk_* (3 seeds), L14_dt*_* (dt trade-off), L16_mdkoff_* /
E61_partA_full_* (ablation/recipe arms when present), unet_2d_* / unet_2d_e6_*.
Local-budget rounds (G=32 L2/L3/MS_*/E6_partA) are excluded by design.

B1 has TWO recorded generations on different family sizes and they do NOT give
the same verdict, so they are kept as separate columns rather than pooled:
  v2/130  B1v2_*          family_all rebuilt to 130 scenarios (SWE-GNN protocol)
  v1/117  L3_B1_paper_* + MS4_B1_*   the round-3 (E3) generation
**v2/130 is the reporting generation** (decided 2026-09-21; it is the benchmark
declared in paper_architecture_plan 4); v1/117 is retained as the sensitivity
check against the family extension, whose failure to reproduce the v1 verdict
is itself a recorded methodology finding.

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

# (domain label, (data_root, split), run-name regex or None)
# The regex disambiguates domains that share a (root, split) — the two B1
# generations — by matching the RAW registry run name (before protocol/seed
# stripping). Order matters: first match wins.
DOMAINS = [
    ("2D 域内", ("data/scenarios_2d_family", "test"), None),
    ("2D →真实考卷 H=8", ("data/real_cases/exams_2d_h8", "test"), None),
    ("2D →真实考卷 全时程", ("data/real_cases/exams_2d", "test"), None),
    ("2D →大域 12.8km 零样本", ("data/scenarios_2d_larger", "test"),
     r"^(MS4_2d_|MS4b_2d_|L16_mdkoff_2d|floor_persist_2d_larger)"),
]

# run-name family whitelist (paper budget) -> display model
FAMILIES = [
    (re.compile(r"^MS4_2d_(swegnn|flow_mdk|ssgc|gcn|gat)_s\d+$"), None),
    (re.compile(r"^MS4c_2d_\w+p8_s\d+$"), None),
    (re.compile(r"^L16_mdkoff_2d_s\d+$"), "flow_mdk(-MDK)"),
    # U-Net 2D baseline (round 3): real-exam zero-shot cells stay empty by
    # design — a grid CNN cannot ingest the unstructured 65k-node meshes
    # (UNetSurrogate refuses non-grid node counts); noted in the matrix doc.
    (re.compile(r"^unet_2d_s\d+$"), "unet"),
    (re.compile(r"^unet_2d_e6_s\d+$"), "unet(E6配方)"),
    # 1x8 official-depth SWE-GNN arm (round 7)
    (re.compile(r"^MS4b_2d_swegnn_s\d+$"), "swegnn(1x8)"),
    # persistence floor rows (A4): the no-skill reference, one per data root
    (re.compile(r"^floor_persist_\w+$"), "persist(floor)"),
]
MODEL_PATTERNS = [  # order matters: first hit wins
    (re.compile(r"^floor_persist"), "persist(floor)"),
    (re.compile(r"^MS4b_2d_swegnn"), "swegnn(1x8)"),
    (re.compile(r"mdkoff"), "flow_mdk(-MDK)"),
    (re.compile(r"unet_2d_e6"), "unet(E6配方)"),
    (re.compile(r"unet"), "unet"),
    (re.compile(r"flow_mdk"), "flow_mdk"),
    (re.compile(r"ssgc"), "ssgc"),
    (re.compile(r"swegnn"), "swegnn"),
    (re.compile(r"gcn"), "gcn"),
    (re.compile(r"gat"), "gat"),
]
SEED_RE = re.compile(r"_s(\d+)$")
STAMP_RE = re.compile(r"_\d{8}_\d{6}$")
PROTO_RE = re.compile(r"^(ptbest_|ptema_)")


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
        fam_name = PROTO_RE.sub("", r["run"])  # predicates match the run, not its protocol
        label = next((lab for lab, k, pat in DOMAINS
                      if k == key and (pat is None or re.search(pat, fam_name))),
                     None)
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
    labels = [lab for lab, _, _ in DOMAINS]

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
