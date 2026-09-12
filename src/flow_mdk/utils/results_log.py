"""Append-only CSV registry of training/evaluation results.

Every ``scripts/train.py`` and ``scripts/evaluate.py`` invocation appends one
row to ``results.csv`` sitting next to the run directories (typically
``runs/results.csv``) — one row per result, never overwritten, so rounds of
experiments stay comparable and nothing is lost when a run directory is
re-used or a checkpoint is retrained. The registry travels with ``runs/``
into ``datasets/runs/`` via ``scripts/archive_datasets.py``.

Column set is a fixed superset for both kinds; rows fill what applies and
leave the rest empty (``kind`` distinguishes ``train`` / ``eval``).
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

HEADER = [
    "timestamp",
    "kind",          # train | eval
    "run",           # out_dir basename
    "out_dir",
    # training identity
    "arch", "hidden_dim", "num_layers", "hops_per_layer", "mdk_use",
    "data_root", "seed", "max_epochs", "epochs_run",
    "best_val_loss", "best_epoch", "train_seconds",
    # evaluation identity / metrics
    "split", "checkpoint", "n_scenarios",
    "rmse", "mae", "csi_0p05", "csi_0p3",   # per-variable, ";"-joined
    "report",        # eval json / history path
]


def registry_path(out_dir: str | Path) -> Path:
    """results.csv lives next to the run directories (e.g. runs/results.csv)."""
    return Path(out_dir).parent / "results.csv"


def append_result(row: dict, out_dir: str | Path) -> Path:
    """Append one result row to the registry next to ``out_dir``."""
    path = registry_path(out_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    record = {"timestamp": datetime.now().isoformat(timespec="seconds"),
              **row}
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({k: record.get(k, "") for k in HEADER})
    return path
