"""Encoders: static, dynamic (bias-free), edge.

SWE-GNN (2023) Sec. 3.1.1: three shared MLPs expand inputs to a hidden
embedding G. The *dynamic* encoder and the decoder have **no bias terms**:
a bias would inject non-zero values at dry nodes and create water out of
nothing (dry sections/cells must stay dry).
"""

from __future__ import annotations

import torch.nn as nn

from flow_mdk.layers.message import make_mlp

__all__ = ["DynamicEncoder", "EdgeEncoder", "StaticEncoder"]


class StaticEncoder(nn.Module):
    """phi_s: static node features -> G (with bias: statics may be non-zero dry)."""

    def __init__(self, in_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.mlp = make_mlp(in_dim, hidden_dim, hidden_dim)

    def forward(self, x):
        return self.mlp(x)


class DynamicEncoder(nn.Module):
    """phi_d: dynamic window (p+1 frames x O vars) -> G, **bias-free**."""

    def __init__(self, in_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.mlp = make_mlp(in_dim, hidden_dim, hidden_dim, bias=False)

    def forward(self, x):
        return self.mlp(x)


class EdgeEncoder(nn.Module):
    """phi_eps: geometric edge features -> G (with bias)."""

    def __init__(self, in_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.mlp = make_mlp(in_dim, hidden_dim, hidden_dim)

    def forward(self, x):
        return self.mlp(x)
