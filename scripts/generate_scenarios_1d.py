#!/usr/bin/env python
"""Generate the 1D scenario family (plan M0 acceptance: >= 50 scenarios).

Examples
--------
    python scripts/generate_scenarios_1d.py --out data/scenarios_1d --num 50
    python scripts/generate_scenarios_1d.py --out data/scenarios_1d --num 50 --jobs 8
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.gen.scenarios_1d import Scenario1DParams, generate_1d_scenario  # noqa: E402
from flow_mdk.utils.io import save_scenario  # noqa: E402


def _run_job(job: tuple[str, int, int, dict]) -> str:
    """Worker: (out_dir, seed, idx, overrides) -> saved scenario name."""
    out_dir, seed, idx, overrides = job
    params = Scenario1DParams(seed=seed + idx, **overrides)
    scenario = generate_1d_scenario(params, f"1d_{idx:04d}")
    save_scenario(scenario, Path(out_dir) / f"{scenario.name}.npz")
    return scenario.name


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the 1D scenario family")
    parser.add_argument("--out", default="data/scenarios_1d")
    parser.add_argument("--num", type=int, default=50)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--steep-frac", type=float, default=0.35,
                        help="fraction of scenarios with steep flood peaks")
    parser.add_argument("--num-sections", type=int, default=100)
    parser.add_argument("--duration-h", type=float, default=8.0)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    jobs = []
    for idx in range(args.num):
        steep = (idx / max(args.num, 1)) < args.steep_frac
        overrides = {
            "num_sections": args.num_sections,
            "duration": args.duration_h * 3600.0,
            # peak family: steep vs slow (plan M0: 陡峰/缓峰)
            "peak_sharpness": 4.0 if steep else 1.5,
            "time_to_peak": 1800.0 if steep else 5400.0,
            "q_peak": float(40.0 + (idx * 37) % 160),
        }
        jobs.append((str(out), args.seed, idx, overrides))

    if args.jobs > 1:
        with mp.Pool(args.jobs) as pool:
            names = pool.map(_run_job, jobs)
    else:
        names = [_run_job(job) for job in jobs]

    # deterministic split 60/20/20 (plan: train / val / test)
    n_train = int(0.6 * len(names))
    n_val = int(0.2 * len(names))
    split = {
        "train": names[:n_train],
        "val": names[n_train : n_train + n_val],
        "test": names[n_train + n_val :],
    }
    (out / "split.json").write_text(json.dumps(split, indent=2), encoding="utf-8")
    print(
        f"generated {len(names)} scenarios in {out} "
        f"(train/val/test = {len(split['train'])}/{len(split['val'])}/{len(split['test'])})"
    )


if __name__ == "__main__":
    main()
