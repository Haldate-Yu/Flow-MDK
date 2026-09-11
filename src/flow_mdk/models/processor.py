"""Processor: L stacked operator-split layers with a residual linear lift.

Follows SWE-GNN Eq. 9 (h_d^(0) = h_d W^(0); per-layer message + linear
update; Tanh on the last layer) extended with the MDK diffusion branch
inside every layer (see layers/splitting.py).
"""

from __future__ import annotations

import torch
import torch.nn as nn

from flow_mdk.config import ModelConfig
from flow_mdk.layers.splitting import HydraulicState, OperatorSplitLayer

__all__ = ["HydraulicsProcessor"]


class HydraulicsProcessor(nn.Module):
    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        g = cfg.hidden_dim
        self.lift = nn.Linear(g, g, bias=False)  # W^(0)
        self.layers = nn.ModuleList(
            OperatorSplitLayer(
                g,
                cfg.mdk,
                is_last=(i == cfg.num_message_passing_layers - 1),
                hops_per_layer=cfg.hops_per_layer,
                hidden_activation=cfg.hidden_activation,
            )
            for i in range(cfg.num_message_passing_layers)
        )

    def forward(
        self,
        hs: torch.Tensor,
        hd: torch.Tensor,
        e_emb: torch.Tensor,
        edge_index: torch.Tensor,
        hyd: HydraulicState,
    ) -> torch.Tensor:
        """hs/e_emb stay constant across layers (topography is static)."""
        hd = self.lift(hd)
        for layer in self.layers:
            hd = layer(hs, hd, e_emb, edge_index, hyd)
        return hd
