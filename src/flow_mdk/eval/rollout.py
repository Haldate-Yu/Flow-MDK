"""Rollout evaluation of a trained model against scenario ground truth."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from flow_mdk.config import ExperimentConfig
from flow_mdk.eval.metrics import csi, mae_per_variable, rmse_per_variable
from flow_mdk.models.factory import build_model
from flow_mdk.utils.io import Scenario, ScenarioStore

__all__ = ["RolloutReport", "load_model", "rollout_scenario", "evaluate_scenarios"]


@dataclass
class RolloutReport:
    scenario: str
    prediction: np.ndarray  # [T_pred, N, O]
    truth: np.ndarray  # [T_pred, N, O]
    seconds: float  # wall time of the surrogate rollout
    solver_seconds: float | None  # reference runtime from scenario metadata
    wet_thresholds: tuple[float, ...] = (0.05, 0.3)

    @property
    def speedup(self) -> float | None:
        if self.solver_seconds and self.solver_seconds > 0:
            return self.solver_seconds / max(self.seconds, 1e-9)
        return None


def load_model(
    config: ExperimentConfig,
    num_static_features: int,
    num_edge_features: int,
    checkpoint: str | Path | None = None,
    device: torch.device | None = None,
):
    """Instantiate (and optionally restore) a model from a config."""
    model = build_model(config.model, num_static_features, num_edge_features)
    if checkpoint is not None:
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        model.load_state_dict(state["model_state"])
    if device is not None:
        model = model.to(device)
    model.eval()
    return model


def rollout_scenario(
    model,
    scenario: Scenario,
    n_steps: int,
    elevation_feature_idx: int,
    device: torch.device | None = None,
) -> RolloutReport:
    """Autoregressive rollout from the scenario's initial window."""
    device = device or next(model.parameters()).device
    n_steps = min(
        n_steps, scenario.num_steps - model.cfg.num_previous_steps - 1
    )
    n_steps = max(n_steps, 1)  # always predict at least one step

    base_static = torch.from_numpy(scenario.node_static.astype(np.float32)).to(device)
    dyn_seq = torch.from_numpy(scenario.dynamic[: model.cfg.num_previous_steps + 1].astype(np.float32)).to(device)
    edge_index = torch.from_numpy(scenario.edge_index).to(device)
    edge_attr = torch.from_numpy(scenario.edge_attr.astype(np.float32)).to(device)

    # attach the water level of the last input frame
    last_depth = dyn_seq[-1][:, 0]
    static = torch.cat([base_static, (base_static[:, elevation_feature_idx] + last_depth)[:, None]], dim=1)

    start = time.perf_counter()
    with torch.no_grad():
        pred = model.rollout(static, dyn_seq, edge_index, edge_attr, n_steps)
    seconds = time.perf_counter() - start

    truth = scenario.dynamic[model.cfg.num_previous_steps + 1 : model.cfg.num_previous_steps + 1 + n_steps]
    solver_seconds = scenario.meta.get("runtime_s")
    return RolloutReport(
        scenario=scenario.name,
        prediction=pred.cpu().numpy(),
        truth=truth.astype(np.float32),
        seconds=seconds,
        solver_seconds=float(solver_seconds) if solver_seconds else None,
    )


def evaluate_scenarios(
    model: FlowMDKNet,
    root: str | Path,
    names: list[str],
    n_steps: int,
    elevation_feature_idx: int,
    device: torch.device | None = None,
) -> list[RolloutReport]:
    """Evaluate a list of scenarios and aggregate metric summaries."""
    store = ScenarioStore(root)
    reports = []
    for name in names:
        scenario = store.load(name)
        if scenario.num_steps <= model.cfg.num_previous_steps + 1:
            print(f"[eval] {name}: skipped (truth pending: {scenario.num_steps} frames)")
            continue
        report = rollout_scenario(model, scenario, n_steps, elevation_feature_idx, device)

        rmse = rmse_per_variable(report.prediction, report.truth)
        mae = mae_per_variable(report.prediction, report.truth)
        depth_pred = report.prediction[..., 0]
        depth_true = report.truth[..., 0]
        csi_scores = [csi(depth_pred, depth_true, thr) for thr in report.wet_thresholds]
        print(
            f"[eval] {name}: RMSE={np.round(rmse, 4).tolist()} "
            f"MAE={np.round(mae, 4).tolist()} "
            f"CSI(0.05/0.3)={np.round(csi_scores, 3).tolist()} "
            f"time={report.seconds:.2f}s"
            + (f" speedup={report.speedup:.1f}x" if report.speedup else "")
        )
        reports.append(report)
    return reports
