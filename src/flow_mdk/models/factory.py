"""Model factory: build any architecture from a ModelConfig.

``arch`` values:
- ``flow_mdk``             — Flow-MDK (SWE-GNN backbone + directed MDK branch)
- ``baseline_gcn``         — GCN processor baseline
- ``baseline_gat``         — GAT processor baseline
- ``baseline_persistence`` — zero-increment reference
"""

from __future__ import annotations

from flow_mdk.config import ModelConfig
from flow_mdk.models.flow_mdk_gnn import FlowMDKNet

__all__ = ["build_model", "ARCHITECTURES"]

ARCHITECTURES = ("flow_mdk", "baseline_gcn", "baseline_gat", "baseline_persistence")


def build_model(cfg: ModelConfig, num_static_features: int, num_edge_features: int):
    if cfg.arch == "flow_mdk":
        return FlowMDKNet(cfg, num_static_features, num_edge_features)
    if cfg.arch == "baseline_gcn":
        from flow_mdk.baselines.gcn import GCNSurrogate

        return GCNSurrogate(cfg, num_static_features, num_edge_features)
    if cfg.arch == "baseline_gat":
        from flow_mdk.baselines.gat import GATSurrogate

        return GATSurrogate(cfg, num_static_features, num_edge_features)
    if cfg.arch == "baseline_persistence":
        from flow_mdk.baselines.persistence import PersistenceSurrogate

        return PersistenceSurrogate(cfg)
    raise ValueError(
        f"Unknown arch '{cfg.arch}'; expected one of {', '.join(ARCHITECTURES)}"
    )
