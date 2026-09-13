#!/usr/bin/env python
"""Plot the per-layer MDK identity coefficient λ₀ across training (L5).

The trainer logs ``mdk_lambda0`` (one value per processor layer) into
history.json every epoch. This tool turns one or more runs into curves so
the smoothing-depth behaviour can be read off directly: λ₀ collapsing
towards 0 means the residual identity path is being switched off and the
MDK series is smoothing deep; a healthy run keeps a non-vanishing λ₀.

    python scripts/plot_mdk_lambda0.py runs/L2_partA_flow_mdk
    python scripts/plot_mdk_lambda0.py --prefix L3_B1 --out runs/lambda0_L3.png

Outputs (next to --out): a PNG (one line per run x layer), a CSV with the
full curves, and a first/last-epoch summary table on stdout. Runs without
λ₀ (non-MDK architectures log an empty list) are reported and skipped.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

MODELS = ("ssgc", "flow_mdk", "swegnn", "gat", "gcn", "persistence")


def model_name(run_dir: Path) -> str:
    name = re.sub(r"_\d{8}_\d{6}$", "", run_dir.name)
    for m in sorted(MODELS, key=len, reverse=True):
        if m in name:
            return m
    return name


def load_curves(run_dir: Path) -> dict[int, list[tuple[int, float]]]:
    """run -> {layer: [(epoch, λ₀), ...]} from history.json."""
    history = json.loads((run_dir / "history.json").read_text(encoding="utf-8"))
    curves: dict[int, list[tuple[int, float]]] = {}
    for entry in history:
        values = entry.get("mdk_lambda0") or []
        for layer, value in enumerate(values):
            curves.setdefault(layer, []).append((int(entry["epoch"]), float(value)))
    return curves


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="*", type=Path, help="run directories")
    parser.add_argument("--prefix", default=None,
                        help="discover runs/<prefix>_<model>[_<stamp>] under runs/")
    parser.add_argument("--out", default="runs/lambda0_curves.png", type=Path)
    args = parser.parse_args()

    run_dirs = list(args.runs)
    if args.prefix:
        run_dirs += sorted(Path("runs").glob(f"{args.prefix}_*"))
    run_dirs = [d for d in run_dirs if (d / "history.json").exists()]
    if not run_dirs:
        raise SystemExit("no run directories with history.json found")

    all_points: list[tuple[str, int, int, float]] = []
    skipped = []
    print(f"{'run':42s} layers  λ₀ first epoch      λ₀ last epoch")
    for run in run_dirs:
        curves = load_curves(run)
        if not curves:
            skipped.append(run)
            continue
        label = f"{model_name(run)} ({run.name})"
        first_last = []
        for layer, points in sorted(curves.items()):
            all_points += [(run.name, layer, e, v) for e, v in points]
            first_last.append((layer, points[0][1], points[-1][1]))
        layers_str = "/".join(f"L{l}: {v0:.3f}→{v1:.3f}" for l, v0, v1 in first_last)
        print(f"{label:42s} {layers_str}")
    for run in skipped:
        print(f"[skip] {run.name}: no λ₀ logged (non-MDK architecture)")

    if not all_points:
        print("nothing to plot")
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    csv_path = args.out.with_suffix(".csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["run", "layer", "epoch", "mdk_lambda0"])
        writer.writerows(all_points)
    print(f"curves -> {csv_path}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available — PNG skipped")
        return

    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = plt.get_cmap("tab10")
    for i, run in enumerate({r for r, _, _, _ in all_points}):
        for layer in sorted({l for r, l, _, _ in all_points if r == run}):
            pts = [(e, v) for r, l, e, v in all_points if r == run and l == layer]
            ax.plot([e for e, _ in pts], [v for _, v in pts],
                    color=colors(i % 10),
                    linestyle=["-", "--", ":", "-."][layer % 4],
                    linewidth=1.5, label=f"{model_name(Path(run))} L{layer}")
    ax.set_xlabel("epoch")
    ax.set_ylabel("λ₀ (per layer)")
    ax.set_title("MDK identity coefficient λ₀ across training")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"figure -> {args.out}")


if __name__ == "__main__":
    main()
