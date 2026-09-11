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
- U-Net (grid CNN)  — planned for M5, requires regular-grid reshaping

Note: unlike Flow-MDK, the standard-GNN baselines do *not* preserve the
dry-node guarantee (their node encoders carry bias and their propagation
mixes statics into dry cells) — that difference is part of what the
comparison measures.
"""

from flow_mdk.baselines.gat import GATSurrogate
from flow_mdk.baselines.gcn import GCNSurrogate
from flow_mdk.baselines.persistence import PersistenceSurrogate

__all__ = ["GATSurrogate", "GCNSurrogate", "PersistenceSurrogate"]
