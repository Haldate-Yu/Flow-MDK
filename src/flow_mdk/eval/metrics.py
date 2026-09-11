"""Metrics following the SWE-GNN evaluation protocol (Sec. 4.3):

- multistep RMSE / MAE per hydraulic variable over the whole rollout;
- CSI (critical success index) of the inundation extent at depth thresholds;
- KS significance test between models (scipy optional);
- Dirichlet energy of the embedding as the over-smoothing monitor (plan M2).
"""

from __future__ import annotations

import numpy as np
import torch

__all__ = [
    "csi",
    "dirichlet_energy",
    "ks_test",
    "mae_per_variable",
    "rmse_per_variable",
]


def rmse_per_variable(pred: np.ndarray, true: np.ndarray) -> np.ndarray:
    """RMSE per variable over the whole rollout.

    pred/true: [T, N, O]. Returns [O].
    """
    return np.sqrt(((pred - true) ** 2).mean(axis=(0, 1)))


def mae_per_variable(pred: np.ndarray, true: np.ndarray) -> np.ndarray:
    """MAE per variable over the whole rollout. pred/true: [T, N, O] -> [O]."""
    return np.abs(pred - true).mean(axis=(0, 1))


def csi(pred: np.ndarray, true: np.ndarray, threshold: float) -> float:
    """Critical success index of the wet extent above a depth threshold.

    CSI = hits / (hits + misses + false alarms), averaged over frames.
    pred/true: [T, N] depth fields; 1.0 when no pairs exist.
    """
    pred_wet = pred > threshold
    true_wet = true > threshold
    hits = float(np.logical_and(pred_wet, true_wet).sum())
    misses = float(np.logical_and(~pred_wet, true_wet).sum())
    false_alarms = float(np.logical_and(pred_wet, ~true_wet).sum())
    denom = hits + misses + false_alarms
    return hits / denom if denom > 0 else 1.0


def ks_test(sample_a: np.ndarray, sample_b: np.ndarray) -> tuple[float, float]:
    """Two-sample Kolmogorov-Smirnov test (p < 0.05 protocol)."""
    try:
        from scipy.stats import ks_2samp
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("scipy is required for the KS test: pip install scipy") from exc
    result = ks_2samp(sample_a, sample_b)
    return float(result.statistic), float(result.pvalue)


def dirichlet_energy(
    embeddings: torch.Tensor, edge_index: torch.Tensor
) -> float:
    """Dirichlet energy  sum_{(i,j)} ||x_i - x_j||^2  of a node embedding.

    Tracked across processor layers to quantify over-smoothing (plan M2):
    a healthy layer keeps a non-vanishing energy; collapse to ~0 signals
    that the MDK series is smoothing too deep.
    """
    src, dst = edge_index[0], edge_index[1]
    diff = embeddings[src] - embeddings[dst]
    return float((diff**2).sum())
