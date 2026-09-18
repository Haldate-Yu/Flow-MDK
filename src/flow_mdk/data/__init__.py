"""Data pipeline: graph construction, features, datasets, topology records."""

from flow_mdk.data.dataset import FlowDataset, collate_flow
from flow_mdk.data.features import (
    FeatureLayout,
    attach_water_level,
    layouts_1d,
    layouts_2d,
)
from flow_mdk.data.graph_1d import build_1d_graph
from flow_mdk.data.graph_2d import build_2d_grid_graph, perlin_dem
from flow_mdk.data.topology import edge_activity_sequence, wet_mask

__all__ = [
    "FeatureLayout",
    "FlowDataset",
    "attach_water_level",
    "build_1d_graph",
    "build_2d_grid_graph",
    "collate_flow",
    "edge_activity_sequence",
    "layouts_1d",
    "layouts_2d",
    "perlin_dem",
    "wet_mask",
]
