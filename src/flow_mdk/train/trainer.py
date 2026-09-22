"""Training loop: Adam + step decay + curriculum horizon + early stopping.

Follows the SWE-GNN training recipe (Sec. 4.2): lr 5e-3 decayed 90% every
7 epochs, up to 150 epochs with early stopping, recursive multistep loss
with horizon growing via curriculum learning. Checkpoints and history go to
the run directory (git-ignored).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from flow_mdk.config import ExperimentConfig
from flow_mdk.data.dataset import FlowDataset, GroupedBatchSampler, collate_flow
from flow_mdk.models.flow_mdk_gnn import FlowMDKNet
from flow_mdk.train.curriculum import HorizonScheduler
from flow_mdk.train.loss import multistep_rollout_loss
from flow_mdk.utils.log import get_logger
from flow_mdk.utils.seed import seed_everything

__all__ = ["Trainer", "TrainResult"]

logger = get_logger("flow_mdk.train")


@dataclass
class TrainResult:
    best_val_loss: float
    best_epoch: int
    epochs_run: int
    history: list[dict]
    checkpoint: Path


class Trainer:
    def __init__(
        self,
        config: ExperimentConfig,
        train_set: FlowDataset,
        val_set: FlowDataset,
        model: FlowMDKNet,
        device: torch.device | None = None,
    ) -> None:
        self.config = config
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.model = model.to(self.device)
        self.train_loader = DataLoader(
            train_set,
            batch_sampler=GroupedBatchSampler(
                train_set, config.train.batch_size, shuffle=True
            ),
            collate_fn=collate_flow,
        )
        self.val_loader = DataLoader(
            val_set,
            batch_sampler=GroupedBatchSampler(
                val_set, config.train.batch_size, shuffle=False
            ),
            collate_fn=collate_flow,
        )
        self.scheduler = HorizonScheduler(
            config.train.horizon_max, config.train.curriculum_steps
        )
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=config.train.lr)
        self.lr_sched = torch.optim.lr_scheduler.StepLR(
            self.optimizer,
            step_size=config.train.lr_step_epochs,
            gamma=config.train.lr_decay,
        )
        self.out_dir = Path(config.out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        # E6: per-step EMA of the model weights (drift-robust checkpoint).
        # With ema_after_curriculum the average starts only once the rollout
        # horizon reaches horizon_max — averaging over curriculum-phase
        # weights was shown to underperform last.pt (E6 probes).
        self.ema_state: dict[str, torch.Tensor] | None = (
            {k: v.detach().clone() for k, v in self.model.state_dict().items()}
            if config.train.ema_decay and not config.train.ema_after_curriculum
            else None
        )

    def _ema_update(self, curriculum_done: bool) -> None:
        if not self.config.train.ema_decay:
            return
        if self.ema_state is None:
            if self.config.train.ema_after_curriculum and not curriculum_done:
                return
            self.ema_state = {
                k: v.detach().clone() for k, v in self.model.state_dict().items()
            }
            return
        d = self.config.train.ema_decay
        with torch.no_grad():
            msd = self.model.state_dict()
            for k, v in self.ema_state.items():
                v.mul_(d).add_(msd[k], alpha=1.0 - d)

    def _epoch_loss(self, loader: DataLoader, horizon: int, train: bool) -> float:
        self.model.train(train)
        total, count = 0.0, 0
        with torch.set_grad_enabled(train):
            for batch in loader:
                batch.node_static = batch.node_static.to(self.device)
                batch.dyn_flat = batch.dyn_flat.to(self.device)
                batch.edge_index = batch.edge_index.to(self.device)
                batch.edge_attr = batch.edge_attr.to(self.device)
                batch.targets = batch.targets.to(self.device)
                loss, _ = multistep_rollout_loss(
                    self.model,
                    batch,
                    horizon,
                    var_weights=self.config.train.var_weights,
                    only_where_water=self.config.train.only_where_water,
                )
                if train:
                    self.optimizer.zero_grad()
                    loss.backward()
                    if self.config.train.grad_clip_value:
                        # official recipe: gradient VALUE clipping at 0.5
                        torch.nn.utils.clip_grad_value_(
                            self.model.parameters(), self.config.train.grad_clip_value
                        )
                    self.optimizer.step()
                    self._ema_update(horizon >= self.config.train.horizon_max)
                total += float(loss.detach())
                count += 1
        return total / max(count, 1)

    def fit(self) -> TrainResult:
        cfg = self.config
        seed_everything(cfg.seed)
        history: list[dict] = []
        best_val, best_epoch, patience = float("inf"), 0, 0
        best_path = self.out_dir / "best.pt"

        for epoch in range(1, cfg.train.max_epochs + 1):
            horizon = self.scheduler.horizon_at(epoch)
            t0 = time.perf_counter()
            train_loss = self._epoch_loss(self.train_loader, horizon, train=True)
            # E6: fixed-horizon validation keeps val values comparable across
            # epochs (the curriculum-following default makes val-best pick a
            # low-horizon epoch — every L4/MS4 best.pt is an H=1 state).
            val_h = cfg.train.val_horizon if cfg.train.val_horizon > 0 else horizon
            val_loss = self._epoch_loss(self.val_loader, val_h, train=False)
            self.lr_sched.step()
            row = {
                "epoch": epoch,
                "horizon": horizon,
                "train_loss": train_loss,
                "val_loss": val_loss,
                "lr": self.optimizer.param_groups[0]["lr"],
                "seconds": time.perf_counter() - t0,
                "mdk_lambda0": self.model.mdk_lambda0(),
                "val_horizon": val_h,
            }
            history.append(row)
            logger.info(
                "epoch %3d | H=%d | train %.5f | val@H%d %.5f | %.1fs",
                epoch,
                horizon,
                train_loss,
                val_h,
                val_loss,
                row["seconds"],
            )
            if val_loss < best_val - 1e-6:
                best_val, best_epoch, patience = val_loss, epoch, 0
                torch.save(
                    {"model_state": self.model.state_dict(), "config_epoch": epoch},
                    best_path,
                )
            else:
                if not (cfg.train.early_stop_after_curriculum
                        and horizon < cfg.train.horizon_max):
                    # E6: never accumulate patience mid-curriculum when the
                    # gate is on (stopping at H<max truncates training).
                    patience += 1
                    if patience >= cfg.train.early_stop_patience:
                        logger.info("early stopping at epoch %d", epoch)
                        break
            # last-epoch checkpoint: with curriculum learning the best-val
            # selector tends to pick a low-horizon epoch, while the final
            # model trained at the full horizon rolls out more stably
            torch.save(
                {"model_state": self.model.state_dict(), "config_epoch": epoch},
                self.out_dir / "last.pt",
            )
            if self.ema_state is not None:
                torch.save(
                    {
                        "model_state": {k: v.clone()
                                        for k, v in self.ema_state.items()},
                        "config_epoch": epoch,
                        "ema_decay": cfg.train.ema_decay,
                    },
                    self.out_dir / "ema.pt",
                )

        return TrainResult(
            best_val_loss=best_val,
            best_epoch=best_epoch,
            epochs_run=len(history),
            history=history,
            checkpoint=best_path,
        )
