#!/usr/bin/env python
"""Build the training/validation/test dataset views.

For M0 the scenario generator already writes .npz files; this script
finalises the split (explicit or ratio-based), stores dataset statistics
and writes a manifest used by training/evaluation.

    python scripts/build_dataset.py --root data/scenarios_1d
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.utils.io import ScenarioStore, load_scenario  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="data/scenarios_1d")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--train-frac", type=float, default=0.6)
    parser.add_argument("--val-frac", type=float, default=0.2)
    args = parser.parse_args()

    root = Path(args.root)
    store = ScenarioStore(root)
    names = store.list_names()
    if not names:
        raise SystemExit(f"no scenarios found under {root}")

    rng = np.random.default_rng(args.seed)
    rng.shuffle(names)
    n_train = int(args.train_frac * len(names))
    n_val = int(args.val_frac * len(names))
    split = {
        "train": sorted(names[:n_train]),
        "val": sorted(names[n_train : n_train + n_val]),
        "test": sorted(names[n_train + n_val :]),
    }
    (root / "split.json").write_text(json.dumps(split, indent=2), encoding="utf-8")

    # dataset statistics (depth/discharge ranges and wet fraction)
    stats = {}
    for name in names:
        sc = store.load(name)
        stats[name] = {
            "num_nodes": int(sc.num_nodes),
            "num_steps": int(sc.num_steps),
            "h_max": float(sc.dynamic[..., 0].max()),
            "q_max": float(sc.dynamic[..., 1].max()),
            "wet_fraction": float(sc.wet.mean()),
            "runtime_s": sc.meta.get("runtime_s"),
        }
    (root / "stats.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"split written: {len(split['train'])}/{len(split['val'])}/{len(split['test'])} "
        f"(train/val/test) into {root/'split.json'}; stats.json covers {len(names)} scenarios"
    )


if __name__ == "__main__":
    main()
