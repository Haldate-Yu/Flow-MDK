"""Tests for graph construction and datasets."""

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.data.dataset import FlowDataset, collate_flow, window_count
from flow_mdk.data.graph_1d import build_1d_graph
from flow_mdk.data.graph_2d import build_2d_grid_graph, perlin_dem
from flow_mdk.data.topology import edge_activity_sequence, topology_transitions


def test_chain_graph_both_orientations():
    n = 6
    x = np.linspace(0, 500, n)
    z = np.linspace(10, 0, n)
    width = np.full(n, 15.0)
    edge_index, edge_attr = build_1d_graph(x, z, width)
    assert edge_index.shape == (2, 2 * (n - 1))
    assert edge_attr.shape == (2 * (n - 1), 3)
    # dx constant 100 m
    assert np.allclose(edge_attr[:, 0], 100.0)
    # bed slope signed along arc direction: downstream arcs negative
    assert np.all(edge_attr[0::2, 2] < 0) and np.all(edge_attr[1::2, 2] > 0)


def test_grid_dual_graph_normals_and_lengths():
    nx, ny, d = 4, 3, 50.0
    edge_index, edge_attr, centers = build_2d_grid_graph(nx, ny, d, d)
    # 4-connectivity: horizontal links nx*(ny-1), vertical (nx-1)*ny
    n_links = nx * (ny - 1) + (nx - 1) * ny
    assert edge_index.shape == (2, 2 * n_links)
    # normals are unit vectors
    norms = np.linalg.norm(edge_attr[:, :2], axis=1)
    assert np.allclose(norms, 1.0)
    # side lengths are d
    assert np.allclose(edge_attr[:, 2], d)
    assert centers.shape == (nx * ny, 2)


def test_perlin_dem_properties():
    elev, grad = perlin_dem((32, 32), 100.0, z_range=(0.0, 5.0), seed=3)
    assert elev.shape == (32, 32)
    assert grad.shape == (32, 32, 2)
    assert elev.min() >= 0.0 and elev.max() <= 5.0
    # reproducible with the same seed
    elev2, _ = perlin_dem((32, 32), 100.0, z_range=(0.0, 5.0), seed=3)
    assert np.allclose(elev, elev2)


def test_topology_activity_and_transitions():
    wet = np.zeros((3, 3), dtype=np.uint8)
    wet[0] = [1, 0, 0]  # frame 0: node 0 wet
    wet[1] = [1, 1, 0]  # frame 1: wetting front advanced
    wet[2] = [1, 1, 1]  # frame 2: all wet
    edge_index = np.array([[0, 1, 1, 2], [1, 0, 2, 1]])
    activity = edge_activity_sequence(wet, edge_index, gate="source")
    assert activity.shape == (3, 4)
    assert activity[0, 0] == 1 and activity[0, 2] == 0  # arc 1->2 inactive
    assert activity[2, 2] == 1
    trans = topology_transitions(activity)
    assert (trans["appear_frames"] == 1).any()


def test_window_count():
    assert window_count(50, 1, 8) == 50 - 2 - 8 + 1
    assert window_count(5, 1, 8) == 0
