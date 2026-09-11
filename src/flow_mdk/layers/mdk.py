"""Flow-directed Markov Diffusion Kernel (MDK) propagation.

The transition matrix P is built on the *directed* hydraulic graph: an arc
i -> j exists (and carries weight) only in the downstream direction of the
flow, weighted by discharge magnitude. Rows of P are re-normalized at every
model step over the currently *wet* sub-graph, so the receptive field adapts
as wet/dry fronts move.

The filter applied to a node field x is the truncated series

    F x = lambda0 * x + sum_{m=1}^{K} w_m * P^m x,
    w_m = lambda0 * (1 - lambda0)^m          ("geometric", S2GC MDK), or
    w_m = (1 - lambda0) / K                  ("uniform", truncated Neumann).

``lambda0`` is the identity (teleport) coefficient: it is the structural
over-smoothing cap promised in the plan (lambda0 * I term). In "geometric"
mode it can be learned and coincides with the S2GC teleport probability.

All operations are scatter-based (sparse, O(K * E)); no dense N x N matrix is
ever formed, which keeps large meshes tractable.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
from torch_geometric.utils import softmax

__all__ = [
    "MDKPropagation",
    "direction_gates",
    "hydraulic_edge_weights",
    "suggest_num_steps",
]


def suggest_num_steps(diffusivity: float, dt: float, dx_mean: float) -> int:
    """Physics-matched series truncation order.

    The MDK receptive field should cover the physical diffusion length
    ``sqrt(2 * D * dt)`` traveled within one model time step ``dt``, so

        K = ceil( sqrt(2 * D * dt) / dx_mean )   (at least 1).

    ``diffusivity`` D is an *effective* hyper-parameter of the surrogate
    (backwater/diffusive-wave scaling), not the molecular diffusivity.
    """
    length = math.sqrt(2.0 * diffusivity * dt)
    return max(1, math.ceil(length / max(dx_mean, 1e-12)))


def hydraulic_edge_weights(
    depth: torch.Tensor,
    discharge: torch.Tensor,
    edge_index: torch.Tensor,
    mode: str = "discharge",
) -> torch.Tensor:
    """Base conductance per directed arc from the current hydraulic state.

    - ``discharge``: w_ij = (|q_i| + |q_j|) / 2 — flow-weighted (plan M2);
    - ``uniform``:   w_ij = 1.
    """
    if mode == "uniform":
        return torch.ones(edge_index.size(1), device=edge_index.device, dtype=depth.dtype)
    if mode == "discharge":
        src, dst = edge_index[0], edge_index[1]
        q = discharge.abs()
        return 0.5 * (q[src] + q[dst])
    raise ValueError(f"Unknown edge weight mode: {mode}")


def direction_gates(
    water_level: torch.Tensor,
    edge_index: torch.Tensor,
    beta: float = 1.0,
) -> torch.Tensor:
    """Per-arc direction gate in (0, 1) from the water-surface gradient.

    Arc i -> j is open when node i sits hydraulically *upstream* of j
    (w_i > w_j). With g = sigmoid(beta * (w_src - w_dst)), a flat water
    surface (still water / lake at rest) yields g = 0.5 on both arcs —
    isotropic diffusion — while a strong gradient silences the uphill arc,
    which recovers the supercritical (purely downstream) limit.
    """
    src, dst = edge_index[0], edge_index[1]
    head_diff = water_level[src] - water_level[dst]
    return torch.sigmoid(beta * head_diff)


class MDKPropagation(nn.Module):
    """Truncated MDK series with per-step wet/dry renormalization.

    Parameters
    ----------
    num_steps:
        Series truncation order K (see :func:`suggest_num_steps`).
    weighting:
        ``"geometric"`` (S2GC MDK) or ``"uniform"`` (plain Neumann truncation).
    lambda0:
        Identity (teleport) coefficient; the lambda0 * I over-smoothing cap.
    learn_lambda:
        Learn lambda0 through a sigmoid remap into (lambda_min, 1).
    renormalize:
        Re-scale the truncated geometric weights so they sum to exactly 1
        (the closed-form S2GC truncation slightly shrinks the signal
        otherwise). Off by default to stay faithful to S2GC.
    symmetric:
        Use the symmetric normalization D^{-1/2} A D^{-1/2} over *both* arc
        directions instead of the directed row-stochastic P. This is the
        SSGC / symmetric-MDK ablation ("-定向性").
    """

    def __init__(
        self,
        num_steps: int = 2,
        weighting: str = "geometric",
        lambda0: float = 0.3,
        learn_lambda: bool = True,
        renormalize: bool = False,
        symmetric: bool = False,
        lambda_min: float = 0.02,
    ) -> None:
        super().__init__()
        if weighting not in ("geometric", "uniform"):
            raise ValueError(f"Unknown weighting mode: {weighting}")
        if num_steps < 1:
            raise ValueError("num_steps must be >= 1")
        self.num_steps = num_steps
        self.weighting = weighting
        self.symmetric = symmetric
        self.renormalize = renormalize
        self.lambda_min = lambda_min
        if learn_lambda:
            # sigmoid remap: raw=0 -> (lambda_min+1)/2
            self.lambda0_logit = nn.Parameter(
                torch.tensor(_inverse_sigmoid_midpoint(lambda0, lambda_min))
            )
        else:
            self.lambda0_logit = None
            self._lambda0_fixed = float(lambda0)

    @property
    def lambda0(self) -> torch.Tensor | float:
        if self.lambda0_logit is None:
            return self._lambda0_fixed
        return self.lambda_min + (1.0 - self.lambda_min) * torch.sigmoid(
            self.lambda0_logit
        )

    def _series_weights(self, lambda0: torch.Tensor | float) -> list[torch.Tensor | float]:
        """Weights w_m for m = 0..K; w_0 multiplies the identity term."""
        if self.weighting == "geometric":
            weights = [lambda0 * (1.0 - lambda0) ** m for m in range(self.num_steps + 1)]
        else:  # uniform
            rest = (1.0 - lambda0) / self.num_steps
            weights = [lambda0] + [rest] * self.num_steps
        if self.renormalize:
            total = sum(weights)
            weights = [w / total for w in weights]
        return weights

    def _normalize_weights(
        self,
        edge_weight: torch.Tensor,
        edge_index: torch.Tensor,
        num_nodes: int,
        active: torch.Tensor,
    ) -> torch.Tensor:
        """Row-normalize arc weights over the active (wet) sub-graph.

        Returns per-arc coefficients c_e such that the one-hop propagation
        ``y_i = sum_e c_e * x_src(e)`` equals (P x)_i with rows of P summing
        to 1 over active incoming arcs and 0 for nodes without wet sources.
        """
        src, dst = edge_index[0], edge_index[1]
        # softmax over the incoming arcs of each node, restricted to active arcs
        masked = torch.where(active, edge_weight, torch.zeros_like(edge_weight))
        coeff = softmax(masked, dst, num_nodes=num_nodes)
        # nodes whose incoming arcs are all inactive must receive nothing
        # (softmax over zeros would spread uniformly), so re-mask explicitly.
        return coeff * active.to(coeff.dtype)

    def _symmetric_normalize(
        self,
        edge_weight: torch.Tensor,
        edge_index: torch.Tensor,
        num_nodes: int,
        active: torch.Tensor,
    ) -> torch.Tensor:
        """D^{-1/2} A D^{-1/2} over the active sub-graph (SSGC ablation)."""
        src, dst = edge_index[0], edge_index[1]
        w = edge_weight * active.to(edge_weight.dtype)
        deg = torch.zeros(num_nodes, device=w.device, dtype=w.dtype)
        deg.index_add_(0, src, w)
        deg.index_add_(0, dst, w)
        inv_sqrt = torch.where(deg > 0, deg.rsqrt(), torch.zeros_like(deg))
        return w * inv_sqrt[src] * inv_sqrt[dst]

    def _propagate(
        self,
        x: torch.Tensor,
        coeff: torch.Tensor,
        edge_index: torch.Tensor,
        num_nodes: int,
    ) -> torch.Tensor:
        src, dst = edge_index[0], edge_index[1]
        out = torch.zeros_like(x)
        out.index_add_(0, dst, coeff.unsqueeze(-1) * x[src])
        return out

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor,
        wet_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Apply the MDK filter to node field ``x``.

        Parameters
        ----------
        x: [N, C] node field (in our architecture: the advection increment).
        edge_index: [2, E] directed arcs (both orientations of every link).
        edge_weight: [E] base per-arc conductance (already direction-gated by
            the caller, see :func:`direction_gates`).
        wet_mask: [N] bool; when given, arcs are gated by the wet sub-graph
            (per :attr:`wet_gate` of the parent config, applied by the caller
            through ``edge_weight`` zeroing) and rows re-normalized per step.
        """
        num_nodes = x.size(0)
        src, dst = edge_index[0], edge_index[1]
        if wet_mask is None:
            active = torch.ones(edge_index.size(1), dtype=torch.bool, device=x.device)
        else:
            active = wet_mask[src]  # dry nodes never relay diffusion
        if self.symmetric:
            coeff = self._symmetric_normalize(edge_weight, edge_index, num_nodes, active)
        else:
            coeff = self._normalize_weights(edge_weight, edge_index, num_nodes, active)

        lambda0 = self.lambda0
        weights = self._series_weights(lambda0)

        out = weights[0] * x
        term = x
        for m in range(1, self.num_steps + 1):
            term = self._propagate(term, coeff, edge_index, num_nodes)
            out = out + weights[m] * term
        return out


def _inverse_sigmoid_midpoint(value: float, lo: float) -> float:
    """Sigmoid-domain pre-image of ``value`` under lo + (1-lo)*sigmoid(x)."""
    p = (value - lo) / (1.0 - lo)
    p = min(max(p, 1e-4), 1.0 - 1e-4)
    return math.log(p / (1.0 - p))
