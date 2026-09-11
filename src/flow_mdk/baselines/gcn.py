"""GCN baseline: encoder-decoder harness with a GCNConv processor.

Node inputs are stacked into a single feature matrix X = (Xd, Xs) that
passes through one encoder MLP (SWE-GNN paper App. A1 protocol), then L
GCNConv layers (symmetric normalization with self-loops, Kipf & Welling)
with residual updates; a Tanh caps the last layer as in SWE-GNN. The
decoder is the shared bias-free MLP predicting the residual increment.

Note: the paper's formula writes the propagation as (I - D^-1/2 A D^-1/2)
(the normalized *Laplacian*); we use the standard GCN propagation
D^-1/2 (A+I) D^-1/2 here — to be reconciled against the official repository
(see baselines/README.md comparison checklist).
"""

from __future__ import annotations

import torch
import torch.nn as nn
from torch_geometric.nn import GCNConv

from flow_mdk.config import ModelConfig
from flow_mdk.layers.message import make_mlp
from flow_mdk.models.base import AutoregressiveSurrogate
from flow_mdk.models.decoder import Decoder

__all__ = ["GCNSurrogate"]


class GCNSurrogate(AutoregressiveSurrogate):
    def __init__(self, cfg: ModelConfig, num_static_features: int, num_edge_features: int):
        super().__init__()
        self.cfg = cfg
        g = cfg.hidden_dim
        p1 = cfg.num_previous_steps + 1
        # single node encoder over the stacked (Xd, Xs) matrix, as in App. A1
        self.node_encoder = make_mlp(
            cfg.num_dynamic_vars * p1 + num_static_features, g, g
        )
        self.convs = nn.ModuleList(
            GCNConv(g, g, improved=True) for _ in range(cfg.num_message_passing_layers)
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
        for i, conv in enumerate(self.convs):
            h = h + conv(h, edge_index)  # residual update, as in Eq. 8
            if i == len(self.convs) - 1:
                h = self.out_act(h)
            else:
                h = self.activation(h)
        return self.decoder(h)
