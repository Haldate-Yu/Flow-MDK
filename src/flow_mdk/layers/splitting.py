"""Advection-diffusion operator splitting: one Flow-MDK processor layer.

Each processor layer evaluates two branches on the *same* increment field
and mixes them:

1. **Advection branch** — the SWE-GNN difference message (approximate Riemann
   solver), aggregated over neighbours and applied for ``hops_per_layer``
   consecutive hops, each with its own weight matrix (this mirrors the
   official implementation, whose SWEGNN layer loops K=8 times internally
   with one ``filter_matrix`` Linear per hop).
2. **Diffusion branch** — the flow-directed MDK filter applied to the
   layer's advection increment (residual filtering: the filter acts on the
   increment, never on the state itself, so the lambda0 * I term plays the
   role of "no diffusion" and dry nodes that receive no increment stay dry).

    running_k+1  = running_k + W_k . sum_j s_ij(running_k)
    Delta_adv    = running_H - hd
    Delta_tilde  = MDK(Delta_adv)
    hd'          = hd + alpha * Delta_adv + (1 - alpha) * Delta_tilde
                 (+ activation: Tanh on the last layer, per config otherwise)

With ``mdk.use=False`` and ``mixing`` forced to advection this reduces
exactly to the official SWE-GNN layer.

Ablation switches (see config.MDKConfig):
    - ``use=False``                     -> pure SWE-GNN ("-MDK");
    - ``directed=False``                -> symmetric MDK / SSGC ("-定向性");
    - ``mixing="diffusive-only"``       -> pure MDK branch ("-分裂").
"""

from __future__ import annotations

import torch
import torch.nn as nn

from flow_mdk.config import MDKConfig
from flow_mdk.layers.mdk import MDKPropagation
from flow_mdk.layers.message import PsiMessage

__all__ = ["HydraulicState", "OperatorSplitLayer"]


class HydraulicState:
    """Per-model-step hydraulic tensors shared by all processor layers.

    Attributes
    ----------
    wet_mask: [N] bool — nodes carrying water (h > threshold).
    edge_weight: [E] per-arc conductance = base (discharge) weight x
        direction gate; recomputed at every model step so dry/wet and flow
        reversal are honoured (per-step renormalization happens inside the
        MDK filter).
    """

    __slots__ = ("edge_weight", "wet_mask")

    def __init__(self, wet_mask: torch.Tensor, edge_weight: torch.Tensor) -> None:
        self.wet_mask = wet_mask
        self.edge_weight = edge_weight


class OperatorSplitLayer(nn.Module):
    """One processor layer: hops of difference messages + MDK diffusion."""

    def __init__(
        self,
        hidden_dim: int,
        mdk_cfg: MDKConfig,
        is_last: bool = False,
        hops_per_layer: int = 1,
        hidden_activation: str = "prelu",
    ) -> None:
        super().__init__()
        self.mdk_cfg = mdk_cfg
        self.is_last = is_last
        self.hops_per_layer = max(1, int(hops_per_layer))
        self.psi = PsiMessage(hidden_dim)
        # one weight matrix per hop, as the official filter_matrix ModuleList
        self.hop_linears = nn.ModuleList(
            nn.Linear(hidden_dim, hidden_dim, bias=False)
            for _ in range(self.hops_per_layer)
        )
        if mdk_cfg.use:
            self.mdk = MDKPropagation(
                num_steps=mdk_cfg.num_steps,
                weighting=mdk_cfg.weighting,
                lambda0=mdk_cfg.lambda0,
                learn_lambda=mdk_cfg.learn_lambda,
                symmetric=not mdk_cfg.directed,
            )
            if mdk_cfg.mixing == "learned":
                # per-channel mixing gate, initialised at alpha = 0.5
                self.alpha_logit = nn.Parameter(torch.zeros(hidden_dim))
            elif mdk_cfg.mixing == "fixed":
                self.register_buffer(
                    "alpha_logit", torch.full((hidden_dim,), float("nan"))
                )
        self.inter_activation: nn.Module = (
            nn.Tanh() if is_last else nn.PReLU() if hidden_activation == "prelu" else nn.Tanh()
        )

    def _alpha(self) -> torch.Tensor | None:
        if not self.mdk_cfg.use or self.mdk_cfg.mixing == "diffusive-only":
            return None
        if self.mdk_cfg.mixing == "learned":
            return torch.sigmoid(self.alpha_logit)
        return torch.sigmoid(torch.zeros_like(self.alpha_logit)).fill_(
            self.mdk_cfg.alpha_value
        )

    def forward(
        self,
        hs: torch.Tensor,
        hd: torch.Tensor,
        e_emb: torch.Tensor,
        edge_index: torch.Tensor,
        hyd: HydraulicState,
    ) -> torch.Tensor:
        src, dst = edge_index[0], edge_index[1]

        # --- advection branch: hops of difference messages -----------------
        running = hd
        for k in range(self.hops_per_layer):
            s = self.psi(hs[src], hs[dst], running[src], running[dst], e_emb)
            aggregated = torch.zeros_like(hd)
            aggregated.index_add_(0, dst, s)
            running = running + self.hop_linears[k](aggregated)
        delta_adv = running - hd

        # --- diffusion branch: MDK filter on the layer increment -----------
        if self.mdk_cfg.use:
            delta_mdk = self.mdk(
                delta_adv, edge_index, hyd.edge_weight, wet_mask=hyd.wet_mask
            )
            alpha = self._alpha()
            if alpha is None:  # "diffusive-only"
                delta = delta_mdk
            else:
                delta = alpha * delta_adv + (1.0 - alpha) * delta_mdk
        else:
            delta = delta_adv

        hd = hd + delta
        return self.inter_activation(hd)
