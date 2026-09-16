"""Tests for the M4 coupled 1D-2D graph builder."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.data.graph_1d import build_1d_graph
from flow_mdk.data.graph_2d import build_2d_grid_graph
from flow_mdk.data.graph_coupled import (
    NODE_TYPE_1D,
    NODE_TYPE_2D,
    Interface,
    SubGraph,
    build_coupled_graph,
)


def _tiny_chain(n: int = 4) -> SubGraph:
    x = np.linspace(0, 300, n)
    z = np.linspace(10, 4, n)
    width = np.full(n, 12.0)
    edge_index, edge_attr = build_1d_graph(x, z, width)
    static = np.stack([z, width], axis=1).astype(np.float32)
    return SubGraph("chain", "1d", static, edge_index, edge_attr)


def _tiny_grid(nx: int = 3, ny: int = 3, d: float = 50.0) -> tuple[SubGraph, np.ndarray]:
    edge_index, edge_attr, centers = build_2d_grid_graph(nx, ny, d, d)
    z = np.linspace(4, 0, nx * ny).astype(np.float32)
    static = np.stack([np.full(nx * ny, d * d, dtype=np.float32), z], axis=1)
    return SubGraph("mesh", "2d", static, edge_index, edge_attr), centers


def test_coupled_chain_mesh_counts_and_types():
    chain = _tiny_chain(4)
    mesh, centers = _tiny_grid(3, 3)
    # 2D west column (leftmost cell centres) as inflow boundary nodes
    west = [int(i) for i in np.where(centers[:, 0] == centers[:, 0].min())[0]]
    coupled = build_coupled_graph(
        [chain, mesh],
        [Interface(a=0, nodes_a=[3], b=1, nodes_b=west, length_m=25.0)],
    )
    # node type channel appended; 1D rows flagged 1.0, 2D rows 0.0
    assert coupled.node_static.shape == (4 + 9, 3)
    assert np.all(coupled.node_static[:4, -1] == NODE_TYPE_1D)
    assert np.all(coupled.node_static[4:, -1] == NODE_TYPE_2D)
    # local edges preserved + 2 * (1x3) bipartite interface edges
    n_chain_edges = chain.edge_index.shape[1]
    n_mesh_edges = mesh.edge_index.shape[1]
    assert coupled.edge_index.shape[1] == n_chain_edges + n_mesh_edges + 6
    # interface edges carry the placeholder attribute [0, 0, length]
    iface_attr = coupled.edge_attr[-6:]
    assert np.all(iface_attr[:, :2] == 0.0)
    assert np.allclose(iface_attr[:, 2], 25.0)
    # 1D/2D edge semantics unchanged inside their own blocks
    assert np.allclose(coupled.edge_attr[:n_chain_edges], chain.edge_attr)
    assert np.allclose(coupled.edge_attr[n_chain_edges:n_chain_edges + n_mesh_edges],
                       mesh.edge_attr)


def test_coupled_interface_offsets_and_reachability():
    chain = _tiny_chain(4)
    mesh, centers = _tiny_grid(3, 3)
    west = [int(i) for i in np.where(centers[:, 0] == centers[:, 0].min())[0]]
    coupled = build_coupled_graph(
        [chain, mesh],
        [Interface(a=0, nodes_a=[3], b=1, nodes_b=west)],
    )
    src, dst = coupled.edge_index
    # interface edges must point at offset-corrected mesh nodes (>= 4)
    iface_src, iface_dst = src[-6:], dst[-6:]
    assert np.all((iface_src < 4) | (iface_dst < 4))  # one endpoint in the chain
    assert np.all(np.maximum(iface_src, iface_dst) >= 4)  # other in the mesh
    # reachability: BFS from chain node 0 must reach every mesh node
    adj: dict[int, list[int]] = {}
    for a, b in zip(src.tolist(), dst.tolist()):
        adj.setdefault(a, []).append(b)
    seen, stack = {0}, [0]
    while stack:
        for nb in adj.get(stack.pop(), []):
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    assert seen == set(range(coupled.num_nodes))


def test_coupled_chain_mesh_chain_three_subgraphs():
    up, _ = _tiny_grid(2, 2)
    chain = _tiny_chain(3)
    down, centers = _tiny_grid(2, 2)
    left = [int(i) for i in np.where(centers[:, 0] == centers[:, 0].min())[0]]
    right = [int(i) for i in np.where(centers[:, 0] == centers[:, 0].max())[0]]
    coupled = build_coupled_graph(
        [up, chain, down],
        [
            Interface(a=0, nodes_a=left, b=1, nodes_b=[0], kind="mesh_to_chain",
                      length_m=10.0),
            Interface(a=1, nodes_a=[2], b=2, nodes_b=right, kind="chain_to_mesh",
                      length_m=10.0),
        ],
    )
    assert coupled.num_nodes == 4 + 3 + 4
    assert len(coupled.interfaces) == 2
    assert all(rec["num_edges"] == 2 * len(rec["nodes_a_global"]) * len(rec["nodes_b_global"])
               for rec in coupled.interfaces)
    # 1D subgraph sits in the middle: global ids 4..6
    assert np.all(coupled.node_static[4:7, -1] == NODE_TYPE_1D)


def test_coupled_rejects_bad_interfaces():
    chain = _tiny_chain(3)
    mesh, centers = _tiny_grid(2, 2)
    with pytest.raises(ValueError):
        build_coupled_graph([chain], [])  # nothing coupled
    with pytest.raises(ValueError):
        build_coupled_graph([chain, mesh],
                            [Interface(a=0, nodes_a=[], b=1, nodes_b=[0])])
    with pytest.raises(ValueError):
        build_coupled_graph([chain, mesh],
                            [Interface(a=0, nodes_a=[0], b=0, nodes_b=[1])])
