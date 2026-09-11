"""GAT baseline: encoder-decoder harness with a GATConv processor.

Follows the SWE-GNN paper's GAT comparison (App. A2): attention
coefficients a(h_i, h_j) over neighbours, edge features fed to the
attention mechanism (edge_dim), residual updates between layers, Tanh on
the last layer, shared bias-free decoder predicting the residual increment.
"""

from __future__ import annotations

import torch
import torch.nn as nn
from torch_geometric.nn import GATConv

from flow_mdk.config import ModelConfig
from flow_mdk.layers.message import make_mlp
from flow_mdk.models.base import AutoregressiveSurrogate
from flow_mdk.models.decoder import Decoder

__all__ = ["GATSurrogate"]


class GATSurrogate(AutoregressiveSurrogate):
    def __init__(
        self,
        cfg: ModelConfig,
        num_static_features: int,
        num_edge_features: int,
        heads: int = 4,
    ) -> None:
        super().__init__()
        self.cfg = cfg
        g = cfg.hidden_dim
        p1 = cfg.num_previous_steps + 1
        self.node_encoder = make_mlp(
            cfg.num_dynamic_vars * p1 + num_static_features, g, g
        )
        self.edge_encoder = make_mlp(num_edge_features, g, g)
        self.convs = nn.ModuleList(
            GATConv(g, g, heads=heads, concat=False, edge_dim=g)
            for _ in range(cfg.num_message_passing_layers)
        )
        self.activation = nn.PReLU()
        self.out_act = nn.Tanh()
        self.decoder = Decoder(g, cfg.num_dynamic_vars)

    def forward(
        self,
        node_static: torch.Tensor,
        dyn_flat: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
    ) -> torch.Tensor:
        h = self.node_encoder(torch.cat([dyn_flat, node_static], dim=-1))
        e = self.edge_encoder(edge_attr)
        for i, conv in enumerate(self.convs):
            h = h + conv(h, edge_index, edge_attr=e)  # residual update
            if i == len(self.convs) - 1:
                h = self.out_act(h)
            else:
                h = self.activation(h)
        return self.decoder(h)
