#!/usr/bin/env python
"""Build Δt-multiplied scenario roots for the big-Δt trade-off experiment (L14,
PLAN M2: layer/k vs time step, SWE-GNN Fig. 8 analog).

Keeps frame 0 and every m-th frame of every scenario npz, so the effective
model time step is m x the native solver output cadence while the physics is
unchanged. The MDK series truncation K must scale with sqrt(m) to stay
physics-matched (K = ceil(sqrt(2 D dt)/dx)); the training scripts pair each
root with its K (L14: K0=2 -> K=3 at m=2, K=4 at m=3).

    python scripts/subsample_scenarios_dt.py \
        --src data/scenarios_partA_v2 --dst data/scenarios_partA_v2_dt2 --stride 2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.utils.io import Scenario, load_scenario, save_scenario  # noqa: E402


def subsample(scenario: Scenario, stride: int) -> Scenario:
    keep = np.arange(0, scenario.num_steps, stride)
    edge_flow = None
    if scenario.edge_flow is not None:
        edge_flow = scenario.edge_flow[keep]
    meta = dict(scenario.meta)
    meta["dt_subsample"] = {
        "stride": int(stride),
        "frames_original": int(scenario.num_steps),
        "frames_kept": int(len(keep)),
        "note": "effective model dt = stride x native output cadence",
    }
    return Scenario(
        name=scenario.name,
        node_static=scenario.node_static,
        edge_index=scenario.edge_index,
        edge_attr=scenario.edge_attr,
        dynamic=scenario.dynamic[keep],
        wet=scenario.wet[keep],
        times=scenario.times[keep],
        meta=meta,
        edge_flow=edge_flow,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--dst", type=Path, required=True)
    parser.add_argument("--stride", type=int, required=True)
    args = parser.parse_args()

    args.dst.mkdir(parents=True, exist_ok=True)
    frames = []
    for npz in sorted(args.src.glob("*.npz")):
        scenario = load_scenario(npz)
        sub = subsample(scenario, args.stride)
        save_scenario(sub, args.dst / npz.name)
        frames.append(sub.num_steps)
    for extra in args.src.glob("*.json"):
        (args.dst / extra.name).write_text(extra.read_text(encoding="utf-8"),
                                           encoding="utf-8")
    frames = np.array(frames)
    windows = np.maximum(0, frames - 2 - 8 + 1)  # p=1, H=8
    print(f"[dt x{args.stride}] {len(frames)} scenarios -> {args.dst}")
    print(f"  frames kept: min={frames.min()} p50={np.median(frames):.0f} "
          f"max={frames.max()}; H=8 windows per scenario: min={windows.min()} "
          f"p50={np.median(windows):.0f}")
    if windows.min() < 1:
        raise SystemExit("some scenarios have no H=8 windows at this stride")


if __name__ == "__main__":
    main()
