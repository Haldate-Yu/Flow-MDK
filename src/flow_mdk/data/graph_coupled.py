"""Coupled 1D-2D graph construction (M4 v1, data structure only).

A coupled scenario glues subgraphs of different dimensionality into ONE
homogeneous graph so the existing SWE-GNN-style message passing can run
without architecture surgery:

- 1D river-network chains (``build_1d_graph`` layout),
- 2D mesh/grid dual graphs (``build_2d_grid_graph`` / real meshes),
- interface edges between a chain-boundary section and the adjacent mesh
  boundary nodes (bipartite, both orientations), carrying a placeholder
  ``[0, 0, length]`` attribute — interface edges intentionally carry NO
  local 1D/2D geometry semantics.

Two deliberate v1 simplifications (documented for the M4 training round):

1. Subgraph kind is exposed as an extra STATIC node-feature channel
   (``1.0`` = 1D section, ``0.0`` = 2D cell) instead of heterogeneous
   conv layers; the model can branch on it through the encoder MLP.
2. Edge features keep each subgraph's LOCAL semantics under the shared
   3-column layout — 1D arcs: ``[dx, width_avg, signed bed slope]``
   (``graph_1d.build_1d_graph``), 2D arcs: ``[normal_x, normal_y, length]``
   (``graph_2d``). Mixed semantics inside one graph is acceptable for v1
   because message passing treats edge_attr as opaque inputs, but a shared
   edge schema is the first candidate upgrade if v1 underfits.

Interface mass conservation (PLAN M4 bullet 2) is NOT modelled here; with
real coupled truth (chain-side Q vs mesh-side per-node flux) it becomes a
trainable flux term on the interface edges — the CoupledGraph keeps the
interface bookkeeping needed to address those edges.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["SubGraph", "Interface", "CoupledGraph", "build_coupled_graph"]

NODE_TYPE_1D = 1.0
NODE_TYPE_2D = 0.0


@dataclass
class SubGraph:
    """One 1D chain or 2D mesh participating in a coupled scenario."""

    name: str
    kind: str  # '1d' or '2d'
    node_static: np.ndarray  # [N, F]
    edge_index: np.ndarray  # [2, E] both orientations, local indices
    edge_attr: np.ndarray  # [E, 3]

    def __post_init__(self) -> None:
        if self.kind not in ("1d", "2d"):
            raise ValueError(f"kind must be '1d' or '2d', got {self.kind!r}")


@dataclass
class Interface:
    """Coupling between a chain-boundary node set and a mesh-boundary set."""

    a: int  # subgraph index (upstream side)
    nodes_a: list[int]  # local node ids on side a
    b: int  # subgraph index (downstream side)
    nodes_b: list[int]  # local node ids on side b
    kind: str = "chain_to_mesh"  # or 'mesh_to_chain'
    length_m: float = 0.0  # representative interface length for edge_attr

    def __post_init__(self) -> None:
        if not self.nodes_a or not self.nodes_b:
            raise ValueError("interface needs non-empty node sets on both sides")


@dataclass
class CoupledGraph:
    node_static: np.ndarray  # [N_tot, F+1] (kind channel appended last)
    edge_index: np.ndarray  # [2, E_tot] local + interface edges
    edge_attr: np.ndarray  # [E_tot, 3]
    node_offsets: list[int]  # start index of each subgraph
    edge_offsets: list[int]  # start index of each subgraph's edges
    interfaces: list[dict]  # resolved bookkeeping (global ids, spans)
    meta: dict = field(default_factory=dict)

    @property
    def num_nodes(self) -> int:
        return self.node_static.shape[0]


def build_coupled_graph(
    subgraphs: list[SubGraph],
    interfaces: list[Interface],
    meta: dict | None = None,
) -> CoupledGraph:
    """Glue subgraphs into one graph with typed nodes and interface edges."""
    if not subgraphs:
        raise ValueError("need at least one subgraph")

    statics, edge_idx, edge_attr = [], [], []
    node_off, edge_off = [], []
    n_total = e_total = 0
    for si, sub in enumerate(subgraphs):
        node_off.append(n_total)
        edge_off.append(e_total)
        n, e = sub.node_static.shape[0], sub.edge_index.shape[1]
        type_col = np.full((n, 1),
                           NODE_TYPE_1D if sub.kind == "1d" else NODE_TYPE_2D,
                           dtype=np.float32)
        statics.append(np.concatenate([sub.node_static, type_col], axis=1))
        edge_idx.append(sub.edge_index + n_total)
        edge_attr.append(sub.edge_attr)
        n_total += n
        e_total += e

    iface_records = []
    for iface in interfaces:
        if not (0 <= iface.a < len(subgraphs)) or not (0 <= iface.b < len(subgraphs)):
            raise ValueError(f"interface references bad subgraph index {iface.a}/{iface.b}")
        if iface.a == iface.b:
            raise ValueError("interface must couple two different subgraphs")
        ga = np.asarray(iface.nodes_a) + node_off[iface.a]
        gb = np.asarray(iface.nodes_b) + node_off[iface.b]
        # bipartite all-to-all, both orientations, placeholder geometry
        src = np.repeat(ga, len(gb))
        dst = np.tile(gb, len(ga))
        pairs = np.stack([src, dst])
        both = np.concatenate([pairs, pairs[::-1]], axis=1)
        attrs = np.zeros((both.shape[1], 3), dtype=np.float32)
        attrs[:, 2] = float(iface.length_m)
        edge_idx.append(both.astype(np.int64))
        edge_attr.append(attrs)
        e_total += both.shape[1]
        iface_records.append({
            "kind": iface.kind,
            "a": iface.a, "b": iface.b,
            "nodes_a_global": ga.tolist(),
            "nodes_b_global": gb.tolist(),
            "num_edges": int(both.shape[1]),
            "length_m": float(iface.length_m),
        })

    coupled = CoupledGraph(
        node_static=np.concatenate(statics, axis=0).astype(np.float32),
        edge_index=np.concatenate(edge_idx, axis=1).astype(np.int64),
        edge_attr=np.concatenate(edge_attr, axis=0).astype(np.float32),
        node_offsets=node_off,
        edge_offsets=edge_off,
        interfaces=iface_records,
        meta=meta or {},
    )
    _validate(coupled, subgraphs, interfaces)
    return coupled


def _validate(g: CoupledGraph, subgraphs: list[SubGraph],
              interfaces: list[Interface]) -> None:
    e = g.edge_index
    if e.min() < 0 or e.max() >= g.num_nodes:
        raise ValueError("edge_index out of bounds")
    if g.node_static.shape[1] != subgraphs[0].node_static.shape[1] + 1:
        raise ValueError("type channel not appended")
    for rec, iface in zip(g.interfaces, interfaces):
        off_a, off_b = g.node_offsets[iface.a], g.node_offsets[iface.b]
        assert rec["nodes_a_global"][0] - off_a in iface.nodes_a
        assert rec["nodes_b_global"][0] - off_b in iface.nodes_b
    if not g.interfaces:
        raise ValueError("coupled graph has no interfaces; nothing is coupled")
