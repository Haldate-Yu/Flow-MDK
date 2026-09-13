"""Rollout evaluation of a trained model against scenario ground truth."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from flow_mdk.config import ExperimentConfig
from flow_mdk.eval.metrics import csi, dirichlet_energy, mae_per_variable, rmse_per_variable
from flow_mdk.models.factory import build_model
from flow_mdk.utils.io import Scenario, ScenarioStore

__all__ = [
    "RolloutReport",
    "attach_dirichlet_monitor",
    "load_model",
    "rollout_scenario",
    "evaluate_scenarios",
]


@dataclass
class RolloutReport:
    scenario: str
    prediction: np.ndarray  # [T_pred, N, O]
    truth: np.ndarray  # [T_pred, N, O]
    seconds: float  # wall time of the surrogate rollout
    solver_seconds: float | None  # reference runtime from scenario metadata
    wet_thresholds: tuple[float, ...] = (0.05, 0.3)
    dirichlet: list[float] | None = None  # per processor layer, per edge, per step

    @property
    def speedup(self) -> float | None:
        if self.solver_seconds and self.solver_seconds > 0:
            return self.solver_seconds / max(self.seconds, 1e-9)
        return None


def attach_dirichlet_monitor(
    model,
) -> tuple[list[float], list[int], list]:
    """Register forward hooks recording per-layer Dirichlet energy (L5).

    Covers both harnesses: the Flow-MDK processor (``model.processor.layers``)
    and the GCN/GAT baselines (``model.convs``). The edge_index is located
    generically among the layer inputs as the integer [2, E] tensor. Energy is
    normalised by edge count so scenarios of different size aggregate cleanly;
    the collapse signal (later layers -> ~0) is unaffected by the choice.

    Returns (per-layer energy totals, per-layer call counts, hook handles).
    """
    layers: list = list(getattr(getattr(model, "processor", None), "layers", []) or [])
    layers += list(getattr(model, "convs", []) or [])
    totals = [0.0] * len(layers)
    calls = [0] * len(layers)

    def make(idx: int):
        def hook(_module, inputs, output) -> None:
            edge_index = next(
                (a for a in inputs
                 if isinstance(a, torch.Tensor) and a.dtype == torch.long
                 and a.dim() == 2),
                None,
            )
            if (edge_index is None or edge_index.shape[1] == 0
                    or not isinstance(output, torch.Tensor) or output.dim() != 2):
                return
            totals[idx] += dirichlet_energy(output, edge_index) / edge_index.shape[1]
            calls[idx] += 1
        return hook

    handles = [layer.register_forward_hook(make(i)) for i, layer in enumerate(layers)]
    return totals, calls, handles


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
    totals, calls, handles = attach_dirichlet_monitor(model)
    try:
        with torch.no_grad():
            pred = model.rollout(static, dyn_seq, edge_index, edge_attr, n_steps)
    finally:
        for handle in handles:
            handle.remove()
    seconds = time.perf_counter() - start
    dirichlet = (
        [t / c for t, c in zip(totals, calls)] if calls and all(calls) else None
    )

    truth = scenario.dynamic[model.cfg.num_previous_steps + 1 : model.cfg.num_previous_steps + 1 + n_steps]
    solver_seconds = scenario.meta.get("runtime_s")
    return RolloutReport(
        scenario=scenario.name,
        prediction=pred.cpu().numpy(),
        truth=truth.astype(np.float32),
        seconds=seconds,
        solver_seconds=float(solver_seconds) if solver_seconds else None,
        dirichlet=dirichlet,
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
