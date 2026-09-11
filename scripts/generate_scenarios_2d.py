#!/usr/bin/env python
"""Generate the 2D Perlin-DEM scenario family (plan M0 acceptance: >= 10).

Scenarios carry the dual graph, statics and boundary metadata; ground truth
is attached afterwards by TELEMAC-2D (scripts/run_telemac2d_docker.py).

    python scripts/generate_scenarios_2d.py --out data/scenarios_2d --num 10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.gen.scenarios_2d import Scenario2DParams, generate_2d_scenario  # noqa: E402
from flow_mdk.utils.io import save_scenario  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the 2D scenario family")
    parser.add_argument("--out", default="data/scenarios_2d")
    parser.add_argument("--num", type=int, default=10)
    parser.add_argument("--grid", type=int, default=64, help="nx = ny cells")
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--duration-h", type=float, default=48.0)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    names = []
    for idx in range(args.num):
        params = Scenario2DParams(
            nx=args.grid,
            ny=args.grid,
            seed=args.seed + idx,
            simulation_hours=args.duration_h,
            # dataset-2 style: breach location varies (SWE-GNN Fig. 4a)
            breach_side=["west", "south", "east", "north"][idx % 4],
        )
        scenario = generate_2d_scenario(params, f"2d_{idx:04d}")
        save_scenario(scenario, out / f"{scenario.name}.npz")
        names.append(scenario.name)
        print(f"  {scenario.name}: {params.nx}x{params.ny} cells, "
              f"{len(scenario.edge_index[0])} arcs, breach={params.breach_side}")

    n_train = int(0.6 * len(names))
    n_val = int(0.2 * len(names))
    split = {
        "train": names[:n_train],
        "val": names[n_train : n_train + n_val],
        "test": names[n_train + n_val :],
    }
    (out / "split.json").write_text(json.dumps(split, indent=2), encoding="utf-8")
    print(f"generated {len(names)} 2D scenarios in {out}")


if __name__ == "__main__":
    main()
