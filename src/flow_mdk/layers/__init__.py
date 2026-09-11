"""Graph neural layers: the MDK propagation core, the SWE-GNN difference
message ("psi"), and the advection-diffusion operator-split layer.

References
----------
- SWE-GNN: Bentivoglio et al., HESS 27, 4227-4246, 2023 (Eqs. 7-9).
- S2GC / MDK: Zhang et al., "Simple Spectral Graph Convolution", ICLR 2021
  (arXiv:2002.07421): the Markov Diffusion Kernel is the truncated geometric
  series  S = sum_{m=0}^{K} lambda0 * (1-lambda0)^m * P^m  over a random-walk
  transition matrix P, whose m=0 term is the lambda0 * I identity that caps
  over-smoothing.
"""

from flow_mdk.layers.mdk import (
    MDKPropagation,
    direction_gates,
    hydraulic_edge_weights,
    suggest_num_steps,
)
from flow_mdk.layers.message import PsiMessage
from flow_mdk.layers.splitting import OperatorSplitLayer

__all__ = [
    "MDKPropagation",
    "OperatorSplitLayer",
    "PsiMessage",
    "direction_gates",
    "hydraulic_edge_weights",
    "suggest_num_steps",
]
