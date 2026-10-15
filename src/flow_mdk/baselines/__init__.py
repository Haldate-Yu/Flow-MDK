"""Baseline architectures for the comparison protocol (plan M5).

Following the SWE-GNN paper's own comparison design (App. A): the
encoder-decoder structure and the autoregressive residual harness are kept
fixed, and only the *processor* (the propagation rule) is swapped. This
isolates the contribution of the hydraulics-based / MDK propagation.

Included
--------
- ``gcn``           — GCNConv processor (Kipf & Welling symmetric normalization)
- ``gat``           — GATConv processor with edge features in the attention
- ``persistence``   — zero-increment reference (U_{t+1} = U_t)
- ``alldry``        — all-dry reference (h = |q| = 0 at every step; Card 1)
- ``unet``          — U-Net CNN processor on structured 2D grids (M5)

Note: unlike Flow-MDK, the standard-GNN baselines do *not* preserve the
dry-node guarantee (their node encoders carry bias and their propagation
mixes statics into dry cells) — that difference is part of what the
comparison measures.
"""

from flow_mdk.baselines.alldry import AlldrySurrogate
from flow_mdk.baselines.gat import GATSurrogate
from flow_mdk.baselines.gcn import GCNSurrogate
from flow_mdk.baselines.persistence import PersistenceSurrogate
from flow_mdk.baselines.unet import UNetSurrogate

__all__ = ["AlldrySurrogate", "GATSurrogate", "GCNSurrogate",
           "PersistenceSurrogate", "UNetSurrogate"]
