#!/usr/bin/env python
"""Synthetic 2D scenario family for M3 (SWE-GNN polder protocol, transposed).

Random Perlin polders (64x64 @ 100 m cells, dry start) flooded by a constant
breach discharge through one border side; truth comes from TELEMAC-2D via
``scripts/run_telemac2d_docker.py`` (source-point inflow next to the breach
border). Design mirrors generate_partA_v2.py: A1-style random family with a
70/15/15 split; scale the count once the pipeline is validated.

    python scripts/generate_scenarios_2d_family.py --num 20 --out data/scenarios_2d
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.gen.scenarios_2d import Scenario2DParams, generate_2d_scenario  # noqa: E402
from flow_mdk.utils.io import save_scenario  # noqa: E402

SIDES = ("west", "east", "south", "north")
SEED_BASE = 271828


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num", type=int, default=20)
    parser.add_argument("--out", default="data/scenarios_2d")
    parser.add_argument("--prefix", default="T2D")
    parser.add_argument("--nx", type=int, default=64)
    parser.add_argument("--ny", type=int, default=64)
    parser.add_argument("--cell-size", type=float, default=100.0, dest="cell_size")
    parser.add_argument("--seed-base", type=int, default=SEED_BASE, dest="seed_base")
    parser.add_argument("--split-mode", choices=("70-15-15", "generalization"),
                        default="70-15-15", dest="split_mode",
                        help="generalization puts every scenario under 'test' "
                             "(held-out domain-size set for models trained on the "
                             "smaller domain)")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    names = []
    for k in range(args.num):
        rng = np.random.default_rng(args.seed_base + k)
        params = Scenario2DParams(
            seed=args.seed_base + k,
            nx=args.nx,
            ny=args.ny,
            cell_size=args.cell_size,
            breach_side=SIDES[k % 4],
            breach_discharge=float(rng.uniform(20.0, 80.0)),
            breach_width_cells=int(rng.integers(3, 6)),
            z_range=(0.0, float(rng.uniform(3.0, 6.0))),
        )
        name = f"{args.prefix}_{k:03d}"
        scenario = generate_2d_scenario(params, name)
        save_scenario(scenario, out / f"{name}.npz")
        names.append(name)
        print(f"[fam2d] {name}: side={params.breach_side} Q="
              f"{params.breach_discharge:.1f} z_max={params.z_range[1]:.1f} "
              f"breach_w={params.breach_width_cells}")

    # flat views for scripts/train.py / evaluate.py
    if args.split_mode == "generalization":
        split = {"test": names}
    else:
        n_train = int(args.num * 0.7)
        n_val = int(args.num * 0.15)
        split = {
            "train": names[:n_train],
            "val": names[n_train:n_train + n_val],
            "test": names[n_train + n_val:],
        }
    (out / "split.json").write_text(json.dumps(split, indent=2), encoding="utf-8")
    domain_km = args.nx * args.cell_size / 1000.0
    meta = {
        "protocol": "SWE-GNN polder protocol on structured grids (M3)",
        "grid": f"{args.nx}x{args.ny} @ {args.cell_size:.0f} m cells, dry start, "
                f"constant breach inflow",
        "domain_km": f"{domain_km:.1f}x{args.ny * args.cell_size / 1000.0:.1f} km",
        "inflow": "TELEMAC source point adjacent to the breach border",
        "truth": "telemac2d_docker_rerun via scripts/run_telemac2d_docker.py",
        "count": args.num,
        "split_mode": args.split_mode,
        "seed_base": args.seed_base,
    }
    if (args.nx, args.ny) != (64, 64):
        meta["note"] = (
            "LARGER-DOMAIN set: not the 6.4 km training family. Evaluate the "
            "64x64-trained checkpoints here zero-shot for domain-size "
            "generalization (mirrors SWE-GNN dataset 3, 12.8 km / g=128). "
            "U-Net cannot be evaluated here without care: 128x128 nodes is a "
            "multiple of its 64x64 grid, so it silently reshapes instead of "
            "refusing — exclude it from this root.")
    (out / "family_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[fam2d] {args.num} scenarios -> {out}; "
          f"split {({k: len(v) for k, v in split.items()})}")


if __name__ == "__main__":
    main()
