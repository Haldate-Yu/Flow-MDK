#!/usr/bin/env python
"""Part A v2: paper-scale synthetic dataset (130 scenarios, SWE-GNN protocol).

Mirrors the HESS 2023 dataset design on our 1D family:

| subset | scenarios | design | paper counterpart |
|---|---|---|---|
| A1 | 100 | random geometry x hydrology family, 60/20/20 split | dataset 1 (100 sims) |
| A2 | 20  | hydrology parameters *outside* the A1 training ranges (unseen event shapes) | dataset 2 (unseen breach) |
| A3  | 10  | larger domain: 400 sections / 40 km / longer simulation | dataset 3 (128x128 grid, 120 h) |

Scenarios carry reference-solver truth (diffusive wave, cross-check); the
canonical ground truth is Mascaret (full SWE, regime-aligned with the paper)
attached afterwards by ``scripts/run_partA_mascaret.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.gen.scenarios_1d import Scenario1DParams, generate_1d_scenario  # noqa: E402
from flow_mdk.utils.io import save_scenario  # noqa: E402

SEED_BASE = 31415926


def _sample(seed: int, i: int, sections: int, duration_h: float, length: float,
            unseen_hydrology: bool = False) -> Scenario1DParams:
    rng = np.random.default_rng(seed)
    # geometry family: width/slope/roughness ranges (same spirit as paper's
    # random Perlin topographies, transposed to 1D)
    params = dict(
        num_sections=sections,
        length=length,
        slope=float(rng.uniform(5e-4, 3e-3)),
        width_base=float(rng.uniform(12.0, 45.0)),
        width_amplitude=float(rng.uniform(0.0, 0.6)),
        bed_form_amplitude=float(rng.uniform(0.1, 0.8)),
        strickler_base=float(rng.uniform(20.0, 45.0)),
        strickler_rel_std=float(rng.uniform(0.1, 0.35)),
        patch_scale=float(rng.uniform(500.0, 3000.0)),
    )
    if unseen_hydrology:
        # outside the A1 ranges: sharper, taller, multi-modal events
        params.update(
            q_peak=float(rng.uniform(150.0, 300.0)),
            time_to_peak=float(rng.uniform(600.0, 1500.0)),
            peak_sharpness=float(rng.uniform(5.0, 8.0)),
        )
    else:
        params.update(
            q_peak=float(rng.uniform(40.0, 160.0)),
            time_to_peak=float(rng.uniform(1800.0, 5400.0)),
            peak_sharpness=float(rng.uniform(1.2, 4.5)),
        )
    return Scenario1DParams(
        **params,
        duration=duration_h * 3600.0,
        dt=30.0,
        dt_out=600.0,
        seed=seed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/scenarios_partA_v2")
    parser.add_argument("--skip-solver", action="store_true",
                        help="skip the reference diffusive-wave solve (truth "
                             "comes from Mascaret anyway)")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    names = {"A1": [], "A2": [], "A3": []}

    # A1: 100 scenarios, 60/20/20 split (paper dataset 1)
    for i in range(100):
        p = _sample(SEED_BASE + i, i, sections=100, duration_h=8.0, length=10_000.0)
        sc = generate_1d_scenario(p, f"A1_{i:03d}")
        if args.skip_solver:
            sc.meta["solver"] = "pending_mascaret_rerun"
        save_scenario(sc, out / f"{sc.name}.npz")
        names["A1"].append(sc.name)
    # A2: 20 scenarios with unseen hydrology (paper dataset 2)
    for i in range(20):
        p = _sample(SEED_BASE + 1000 + i, i, sections=100, duration_h=8.0,
                    length=10_000.0, unseen_hydrology=True)
        sc = generate_1d_scenario(p, f"A2_{i:03d}")
        if args.skip_solver:
            sc.meta["solver"] = "pending_mascaret_rerun"
        save_scenario(sc, out / f"{sc.name}.npz")
        names["A2"].append(sc.name)
    # A3: 10 scenarios on a larger domain (paper dataset 3)
    for i in range(10):
        p = _sample(SEED_BASE + 2000 + i, i, sections=400, duration_h=16.0,
                    length=40_000.0)
        sc = generate_1d_scenario(p, f"A3_{i:03d}")
        if args.skip_solver:
            sc.meta["solver"] = "pending_mascaret_rerun"
        save_scenario(sc, out / f"{sc.name}.npz")
        names["A3"].append(sc.name)

    split = {
        "A1_train": names["A1"][:60],
        "A1_val": names["A1"][60:80],
        "A1_test": names["A1"][80:],
        "A2_test": names["A2"],   # unseen hydrology: test-only
        "A3_test": names["A3"],   # larger domain: test-only
        # flat views consumed by scripts/train.py / evaluate.py
        "train": names["A1"][:60],
        "val": names["A1"][60:80],
        "test": names["A1"][80:] + names["A2"] + names["A3"],
    }
    (out / "split.json").write_text(json.dumps(split, indent=2), encoding="utf-8")
    meta = {
        "protocol": "SWE-GNN HESS 2023 dataset alignment (130 simulations)",
        "subsets": {k: len(v) for k, v in names.items()},
        "truth": "diffusive_wave_reference (cross-check) + mascaret (canonical, "
                 "attached by scripts/run_partA_mascaret.py)",
    }
    (out / "dataset_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Part A v2: {sum(len(v) for v in names.values())} scenarios -> {out}")


if __name__ == "__main__":
    main()
