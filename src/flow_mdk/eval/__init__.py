"""Evaluation: metrics (SWE-GNN protocol) and rollout inference."""

from flow_mdk.eval.metrics import (
    csi,
    dirichlet_energy,
    ks_test,
    mae_per_variable,
    rmse_per_variable,
)
from flow_mdk.eval.rollout import evaluate_scenarios, rollout_scenario

__all__ = [
    "csi",
    "dirichlet_energy",
    "evaluate_scenarios",
    "ks_test",
    "mae_per_variable",
    "rmse_per_variable",
    "rollout_scenario",
]
