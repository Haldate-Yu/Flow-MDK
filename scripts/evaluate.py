#!/usr/bin/env python
"""Evaluate a trained model on the test split (SWE-GNN protocol metrics).

    python scripts/evaluate.py --config runs/flow_mdk_1d/config.yaml \\
        --checkpoint runs/flow_mdk_1d/best.pt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.config import load_config  # noqa: E402
from flow_mdk.eval.metrics import csi, mae_per_variable, rmse_per_variable  # noqa: E402
from flow_mdk.eval.rollout import evaluate_scenarios, load_model  # noqa: E402
from flow_mdk.utils.seed import get_device  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--split", default="test", choices=("train", "val", "test"))
    parser.add_argument("--data-root", default=None,
                        help="override config.data.root (zero-shot transfer evaluation)")
    parser.add_argument("--steps", type=int, default=0,
                        help="rollout steps (0 = full scenario)")
    args = parser.parse_args()

    config = load_config(args.config)
    device = get_device(config.device)
    data_root = args.data_root or config.data.root
    split_path = Path(data_root) / "split.json"
    if split_path.exists():
        split = json.loads(split_path.read_text(encoding="utf-8"))
    else:
        names = sorted(p.stem for p in Path(data_root).glob("*.npz"))
        split = {"train": names, "val": names, "test": names}
    names = split[args.split]

    # feature layout: 1D elev idx 0, 2D elev idx 1
    elev_idx = 0 if config.data.name.startswith("1d") else 1
    probe = sorted(p for p in Path(data_root).glob("*.npz"))
    if not probe:
        raise SystemExit(f"no scenarios under {data_root}")
    from flow_mdk.utils.io import load_scenario

    scenario0 = load_scenario(probe[0])
    num_static = scenario0.node_static.shape[1] + 1
    num_edge = scenario0.edge_attr.shape[1]

    model = load_model(config, num_static, num_edge, args.checkpoint, device)
    steps = args.steps or (scenario0.num_steps - config.model.num_previous_steps - 1)
    reports = evaluate_scenarios(model, data_root, names, steps, elev_idx, device)

    out_dir = Path(config.out_dir)
    suffix = f"_{Path(data_root).name}" if args.data_root else ""
    summary = []
    for r in reports:
        summary.append({
            "scenario": r.scenario,
            "rmse": rmse_per_variable(r.prediction, r.truth).tolist(),
            "mae": mae_per_variable(r.prediction, r.truth).tolist(),
            "csi_0p05": csi(r.prediction[..., 0], r.truth[..., 0], 0.05),
            "csi_0p3": csi(r.prediction[..., 0], r.truth[..., 0], 0.3),
            "seconds": r.seconds,
            "speedup": r.speedup,
        })
    out_name = f"eval_{args.split}{suffix}.json"
    (out_dir / out_name).write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    rmse_mean = np.mean([s["rmse"] for s in summary], axis=0).tolist()
    print(f"mean test RMSE per variable: {np.round(rmse_mean, 4).tolist()} "
          f"-> {out_dir / out_name}")


if __name__ == "__main__":
    main()
