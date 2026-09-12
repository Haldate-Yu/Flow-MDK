#!/usr/bin/env python
"""Train a Flow-MDK / SWE-GNN model from an experiment config.

    python scripts/train.py --config configs/1d_flow_mdk.yaml
    python scripts/train.py --config configs/1d_flow_mdk.yaml \\
        --set train.max_epochs=5 model.hidden_dim=32
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.config import dump_config, load_config  # noqa: E402
from flow_mdk.data.dataset import FlowDataset  # noqa: E402
from flow_mdk.models.factory import build_model  # noqa: E402
from flow_mdk.train.trainer import Trainer  # noqa: E402
from flow_mdk.utils.results_log import append_result  # noqa: E402
from flow_mdk.utils.seed import get_device, seed_everything  # noqa: E402


def apply_overrides(config, pairs: list[str]):
    """--set a.b.c=v dotted-path overrides on the config dataclasses."""
    for pair in pairs:
        path, _, raw = pair.partition("=")
        node = config
        parts = path.split(".")
        for part in parts[:-1]:
            node = getattr(node, part)
        old = getattr(node, parts[-1])
        coerced = type(old)(raw) if isinstance(old, (int, float, str)) else json.loads(raw)
        setattr(node, parts[-1], coerced)
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--set", nargs="*", default=[], help="dotted overrides a.b=v")
    args = parser.parse_args()

    config = load_config(args.config)
    config = apply_overrides(config, args.set)
    seed_everything(config.seed)
    device = get_device(config.device)
    print(f"device: {device} | arch={config.model.arch} "
          f"mdk={config.model.mdk.use} directed={config.model.mdk.directed} "
          f"K={config.model.mdk.num_steps}")

    split_path = Path(config.data.root) / "split.json"
    if split_path.exists():
        split = json.loads(split_path.read_text(encoding="utf-8"))
    else:
        names = sorted(p.stem for p in Path(config.data.root).glob("*.npz"))
        n_train = int(config.data.train_frac * len(names))
        n_val = int(config.data.val_frac * len(names))
        split = {"train": names[:n_train], "val": names[n_train : n_train + n_val],
                 "test": names[n_train + n_val :]}
        if not split["val"]:
            split["val"] = list(split["train"])
        if not split["test"]:
            split["test"] = list(split["val"])

    elev_idx = 0 if config.data.name.startswith("1d") else 1
    common = dict(num_previous_steps=config.model.num_previous_steps,
                  elevation_feature_idx=elev_idx)
    train_set = FlowDataset(config.data.root, split["train"], horizon=1, **common)
    try:
        val_set = FlowDataset(config.data.root, split["val"],
                              horizon=config.train.horizon_max, **common)
    except ValueError:
        # validation split too short (e.g. truth pending): reuse training names
        val_set = FlowDataset(config.data.root, split["train"],
                              horizon=config.train.horizon_max, **common)

    model = build_model(config.model, train_set.num_static_features,
                        train_set.scenarios[0].edge_attr.shape[1])

    out_dir = Path(config.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # stamp the resolved config before training starts, so even a killed run
    # leaves its exact configuration behind
    dump_config(config, out_dir / "config.yaml")

    trainer = Trainer(config, train_set, val_set, model, device=device)
    result = trainer.fit()

    history_path = out_dir / "history.json"
    if history_path.exists():
        # re-using an out_dir: keep the previous round's curve, never clobber
        backup = out_dir / (
            "history_"
            f"{datetime.fromtimestamp(history_path.stat().st_mtime):%Y%m%d_%H%M%S}.json"
        )
        history_path.replace(backup)
    history_path.write_text(
        json.dumps(result.history, indent=2), encoding="utf-8"
    )
    registry = append_result({
        "kind": "train",
        "run": out_dir.name,
        "out_dir": str(out_dir),
        "arch": config.model.arch,
        "hidden_dim": config.model.hidden_dim,
        "num_layers": config.model.num_message_passing_layers,
        "hops_per_layer": config.model.hops_per_layer,
        "mdk_use": config.model.mdk.use,
        "data_root": config.data.root,
        "seed": config.seed,
        "max_epochs": config.train.max_epochs,
        "epochs_run": result.epochs_run,
        "best_val_loss": f"{result.best_val_loss:.6f}",
        "best_epoch": result.best_epoch,
        "train_seconds": round(sum(r["seconds"] for r in result.history)),
        "report": str(out_dir / "history.json"),
    }, out_dir)
    print(f"best val loss {result.best_val_loss:.5f} @ epoch {result.best_epoch}; "
          f"checkpoint {result.checkpoint}; logged -> {registry}")


if __name__ == "__main__":
    main()
