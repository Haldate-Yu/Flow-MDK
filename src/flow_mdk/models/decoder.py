"""Decoder: shared MLP, **bias-free**, residual increment prediction.

SWE-GNN Eq. 10: U_{t+1} = U_t + phi(H_d^(L)). phi has two layers with hidden
dimension G and PReLU; no bias (dry nodes must decode exactly zero
increment when the processor output carries no signal).
"""

from __future__ import annotations

import torch.nn as nn

from flow_mdk.layers.message import make_mlp

__all__ = ["Decoder"]


class Decoder(nn.Module):
    def __init__(self, hidden_dim: int, out_dim: int) -> None:
        super().__init__()
        self.mlp = make_mlp(hidden_dim, hidden_dim, out_dim, bias=False)

    def forward(self, x):
        return self.mlp(x)
