#!/usr/bin/env python
"""Gate-direction agreement diagnostic on the real 2D exam meshes (Card 1).

Background (paper 2.2/4.4): the legacy water-level channel was built as
``w = area + h`` (``elevation_feature_idx: 0`` — column 0 is the cell-area
column). On the real unstructured meshes (areas 2-879 m2, CV 1.29) the area
term drowns the true water-surface slope and the MDK direction gate agrees
with the physical slope at ~49% — i.e. near coin-flip. On the synthetic
family (uniform 100 m cells) the area term is a per-run constant and every
paper number is unaffected.

With the corrected channel (``w = bed elevation + h``, idx=1) the gate input
equals the physical water-surface slope BY CONSTRUCTION, so the agreement is
100% by definition. What this script quantifies is therefore the *pollution*:
per exam mesh, how many wet/wet directed-edge comparisons had their gate
direction flipped by the legacy channel. Those flip fractions are the honest
"before" numbers for the Card 1 report; the "after" statement is structural.

For each frame t and each undirected edge (i, j) with both endpoints wet:

    s* = sign((z_i + h_i) - (z_j + h_j))        # true water-surface slope
    s0 = sign((A_i + h_i) - (A_j + h_j))        # legacy area+h channel (idx=0)
    flip := (s0 != s*) and s* != 0 and s0 != 0

Pure numpy, no torch, ~1 min for both exam meshes.

Usage:

    python scripts/diagnose_gate_agreement.py \
        --data-root data/real_cases/exams_2d --out docs/wlev1_gate_agreement.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.utils.io import load_scenario  # noqa: E402

AREA_COL = 0   # legacy (buggy)  water-level channel source
ELEV_COL = 1   # corrected         water-level channel source (bed elevation)


def diagnose_scenario(npz: Path) -> dict:
    sc = load_scenario(npz)
    static = sc.node_static
    area, elev = static[:, AREA_COL], static[:, ELEV_COL]
    h = sc.dynamic[:, :, 0]                      # [T, N] depth
    src, dst = sc.edge_index
    undirected = src < dst                       # each pair once
    s_src, s_dst = src[undirected], dst[undirected]

    flips = 0
    comps = 0
    for t in range(h.shape[0]):
        both_wet = (sc.wet[t, s_src] > 0) & (sc.wet[t, s_dst] > 0)
        if not both_wet.any():
            continue
        dh_s, dh_d = h[t, s_src], h[t, s_dst]
        true_sign = np.sign((elev[s_src] + dh_s) - (elev[s_dst] + dh_d))
        bug_sign = np.sign((area[s_src] + dh_s) - (area[s_dst] + dh_d))
        valid = both_wet & (true_sign != 0) & (bug_sign != 0)
        comps += int(valid.sum())
        flips += int(((bug_sign != true_sign) & valid).sum())

    area_cv = float(area.std() / area.mean()) if area.mean() else float("nan")
    return {
        "exam": sc.name,
        "nodes": int(sc.num_nodes),
        "frames": int(h.shape[0]),
        "wet_edge_frame_comparisons": comps,
        "gate_direction_flips": flips,
        "flip_fraction": round(flips / comps, 4) if comps else None,
        "area_min_m2": round(float(area.min()), 2),
        "area_max_m2": round(float(area.max()), 2),
        "area_cv": round(area_cv, 3),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", default="data/real_cases/exams_2d")
    ap.add_argument("--split", default="test")
    ap.add_argument("--out", default="docs/wlev1_gate_agreement.json")
    args = ap.parse_args()

    root = Path(args.data_root)
    split_path = root / "split.json"
    if split_path.is_file():
        names = json.loads(split_path.read_text(encoding="utf-8"))[args.split]
    else:
        names = sorted(p.stem for p in root.glob("*.npz"))

    rows = [diagnose_scenario(root / f"{n}.npz") for n in names]
    total_c = sum(r["wet_edge_frame_comparisons"] for r in rows)
    total_f = sum(r["gate_direction_flips"] for r in rows)
    report = {
        "channel_legacy": "area + h        (elevation_feature_idx: 0)",
        "channel_fixed": "bed elevation + h (elevation_feature_idx: 1) — equals the "
                         "true water-surface slope by construction (agreement 100%)",
        "note": "flip_fraction = share of wet/wet edge-frame comparisons whose "
                "gate direction the legacy area+h channel inverts w.r.t. the "
                "true water-surface slope; the corrected channel has zero flips "
                "by construction.",
        "pooled": {
            "wet_edge_frame_comparisons": total_c,
            "gate_direction_flips": total_f,
            "flip_fraction": round(total_f / total_c, 4) if total_c else None,
        },
        "exams": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(f"{'exam':<10} {'nodes':>7} {'frames':>7} {'comparisons':>12} "
          f"{'flips':>10} {'flip%':>8}")
    for r in rows:
        print(f"{r['exam']:<10} {r['nodes']:>7} {r['frames']:>7} "
              f"{r['wet_edge_frame_comparisons']:>12} {r['gate_direction_flips']:>10} "
              f"{100 * r['flip_fraction']:>7.2f}%")
    print(f"{'POOLED':<10} {'':>7} {'':>7} {total_c:>12} {total_f:>10} "
          f"{100 * report['pooled']['flip_fraction']:>7.2f}%")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
