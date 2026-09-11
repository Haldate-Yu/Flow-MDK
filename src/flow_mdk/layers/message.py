"""SWE-GNN hydraulics-based message function ("psi").

Implements the processor message of SWE-GNN (Bentivoglio et al., 2023,
Eq. 7): the edge message multiplies a learned source-term estimate by the
*difference* of the dynamic embeddings of the two endpoints,

    s_ij = psi(hs_i, hs_j, hd_i, hd_j, eps_ij)  (.)  (hd_j - hd_i),

which mirrors the finite-volume flux evaluation delta F_ij ~ J_ij (u_j - u_i)
and acts as an approximate Riemann solver: no water-related feature can
propagate unless at least one endpoint is non-zero. The psi output is
L2-normalized along the embedding dimension for training stability.
"""

from __future__ import annotations

import torch
import torch.nn as nn

__all__ = ["PsiMessage", "make_mlp"]


def make_mlp(
    in_dim: int,
    hidden_dim: int,
    out_dim: int,
    bias: bool = True,
    num_hidden: int = 1,
    activate_output: bool = True,
) -> nn.Sequential:
    """SWE-GNN style MLP: Linear layers interleaved with PReLU.

    ``activate_output`` mirrors the official SWE-GNN implementation, which
    appends the activation after the *final* Linear as well (official
    ``make_mlp`` always ends with an activation).
    """
    layers: list[nn.Module] = []
    dims = [in_dim] + [hidden_dim] * num_hidden + [out_dim]
    for i, (a, b) in enumerate(zip(dims[:-1], dims[1:])):
        layers.append(nn.Linear(a, b, bias=bias))
        if i < len(dims) - 2:
            layers.append(nn.PReLU())
        elif activate_output:
            layers.append(nn.PReLU())
    return nn.Sequential(*layers)


class PsiMessage(nn.Module):
    """psi(.): R^{5G} -> R^G, two layers, hidden 2G, PReLU, L2-normalized."""

    def __init__(self, hidden_dim: int) -> None:
        super().__init__()
        self.mlp = make_mlp(5 * hidden_dim, 2 * hidden_dim, hidden_dim)

    def forward(
        self,
        hs_i: torch.Tensor,
        hs_j: torch.Tensor,
        hd_i: torch.Tensor,
        hd_j: torch.Tensor,
        e_ij: torch.Tensor,
    ) -> torch.Tensor:
        """Messages for every directed arc.

        hs_i/hs_j: [E, G] static embeddings at arc endpoints (i = source,
        j = target); hd_i/hd_j: [E, G] current dynamic embeddings; e_ij:
        [E, G] edge embedding. Returns s_ij with shape [E, G].
        """
        features = torch.cat([hs_i, hs_j, hd_i, hd_j, e_ij], dim=-1)
        gate = self.mlp(features)
        gate = gate / (gate.norm(dim=-1, keepdim=True) + 1e-8)
        return gate * (hd_j - hd_i)
