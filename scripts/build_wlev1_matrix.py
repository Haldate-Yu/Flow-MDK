#!/usr/bin/env python
"""W1 (Card 1) water-level-fix comparison matrix: corrected channel vs legacy.

Mirrors scripts/build_generalization_matrix.py, but folds BOTH generations so
the Card 1 verdict reads directly:

  * W1_*  — water-level channel corrected (``w = bed elevation + h``,
            ``elevation_feature_idx: 1``), retrained in this round;
  * MS4_2d_* / MS4b_2d_swegnn_* / L16_mdkoff_2d_* — the legacy paper arms
    (channel = ``area + h``), kept as the idx0 reference columns;
  * floors — persist (legacy rows + new exam rows) and the new all-dry floor.

    python scripts/build_wlev1_matrix.py [--registry runs/results.csv]
    # -> docs/wlev1_matrix.{md,csv}
"""
from __future__ import annotations

import argparse
import csv
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_MD = REPO / "docs" / "wlev1_matrix.md"
OUT_CSV = REPO / "docs" / "wlev1_matrix.csv"

DOMAINS = [
    ("2D 域内", ("data/scenarios_2d_family", "test"), None),
    ("2D →真实考卷 H=8", ("data/real_cases/exams_2d_h8", "test"), None),
    ("2D →真实考卷 全时程", ("data/real_cases/exams_2d", "test"), None),
    ("2D →大域 12.8km 零样本", ("data/scenarios_2d_larger", "test"), None),
]

FAMILIES = [
    # W1 corrected-channel generation (Card 1)
    (re.compile(r"^W1_2d_flow_mdk_s\d+$"), "flow_mdk(w1)"),
    (re.compile(r"^W1_2d_swegnn1x8_s\d+$"), "swegnn1x8(w1)"),
    (re.compile(r"^W1_2d_ssgc_s\d+$"), "ssgc(w1)"),
    (re.compile(r"^W1_2d_mdkoff_s\d+$"), "mdkoff(w1)"),
    (re.compile(r"^W1_floor_alldry_\w+$"), "alldry(floor)"),
    (re.compile(r"^W1_floor_persist_\w+$"), "persist(floor,exams)"),
    # legacy idx0 reference arms (paper numbers)
    (re.compile(r"^MS4_2d_flow_mdk_s\d+$"), "flow_mdk(idx0)"),
    (re.compile(r"^MS4b_2d_swegnn_s\d+$"), "swegnn1x8(idx0)"),
    (re.compile(r"^MS4_2d_ssgc_s\d+$"), "ssgc(idx0)"),
    (re.compile(r"^L16_mdkoff_2d_s\d+$"), "mdkoff(idx0)"),
    (re.compile(r"^MS4_2d_(gcn|gat)_s\d+$"), None),  # context baselines
    (re.compile(r"^floor_persist_\w+$"), "persist(floor)"),
]

MODEL_PATTERNS = [  # order matters: first hit wins
    (re.compile(r"^W1_floor_alldry"), "alldry(floor)"),
    (re.compile(r"^W1_floor_persist"), "persist(floor,exams)"),
    (re.compile(r"^floor_persist"), "persist(floor)"),
    (re.compile(r"^W1_2d_flow_mdk"), "flow_mdk(w1)"),
    (re.compile(r"^W1_2d_swegnn1x8"), "swegnn1x8(w1)"),
    (re.compile(r"^W1_2d_ssgc"), "ssgc(w1)"),
    (re.compile(r"^W1_2d_mdkoff"), "mdkoff(w1)"),
    (re.compile(r"^MS4b_2d_swegnn"), "swegnn1x8(idx0)"),
    (re.compile(r"mdkoff"), "mdkoff(idx0)"),
    (re.compile(r"^MS4_2d_flow_mdk"), "flow_mdk(idx0)"),
    (re.compile(r"^MS4_2d_ssgc"), "ssgc(idx0)"),
    (re.compile(r"^MS4_2d_gcn"), "gcn(idx0)"),
    (re.compile(r"^MS4_2d_gat"), "gat(idx0)"),
]
SEED_RE = re.compile(r"_s(\d+)$")
STAMP_RE = re.compile(r"_\d{8}_\d{6}$")
PROTO_RE = re.compile(r"^(ptbest_|ptema_)")

MODEL_ORDER = [name for _, name in MODEL_PATTERNS]


def parse_run(run: str) -> tuple[str, str, str] | None:
    if run.startswith("ptbest_"):
        protocol, run = "best", run[len("ptbest_"):]
    elif run.startswith("ptema_"):
        protocol, run = "ema", run[len("ptema_"):]
    else:
        protocol = "last"
    if not any(p.match(run) for p, _ in FAMILIES):
        return None
    run = STAMP_RE.sub("", run)
    m = SEED_RE.search(run)
    seed = m.group(1) if m else "0"
    base = SEED_RE.sub("", run)
    for pat, name in MODEL_PATTERNS:
        if pat.search(base):
            return name, protocol, seed
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", default=str(REPO / "runs" / "results.csv"))
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.registry, newline="", encoding="utf-8")))
    cell: dict[tuple[str, str, str], dict[str, float]] = defaultdict(dict)
    n_dropped = 0
    for r in rows:
        if r["kind"] != "eval" or not r["rmse"]:
            continue
        parsed = parse_run(r["run"])
        if parsed is None:
            n_dropped += 1
            continue
        model, protocol, seed = parsed
        label = next((lab for lab, k, _ in DOMAINS
                      if k == (r["data_root"], r["split"])), None)
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
                    key=lambda m: MODEL_ORDER.index(m)
                    if m in MODEL_ORDER else 99)
    labels = [lab for lab, _, _ in DOMAINS]

    lines = [
        "# W1 · Card 1 水位通道修正对比矩阵（h-RMSE，m，registry 自动生成）",
        "",
        "> 生成：`python scripts/build_wlev1_matrix.py`。(w1) = 修正通道"
        "（`w = 床面高程 + h`，本轮重训）；(idx0) = 论文旧臂（通道 = `面积 + h`，"
        "保留作对照）；floor 行与通道无关（无参数、不读特征）。",
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
    print(f"[wlev1-matrix] {len(cell)} (model, protocol, domain) cells "
          f"from {args.registry}")
    print(f"[wlev1-matrix] {n_dropped} eval rows outside the Card 1 whitelist (excluded)")
    print(f"[wlev1-matrix] wrote {OUT_MD}")
    print(f"[wlev1-matrix] wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
