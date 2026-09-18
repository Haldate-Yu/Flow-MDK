"""1D river-network graph construction (M1).

Cross-sections are nodes; consecutive sections along a branch are edges;
confluences become branching nodes. The graph is stored with *both* arc
orientations of every link (message passing is undirected; the MDK
transition matrix selects the downstream direction at run time from the
water-surface gradient).
"""

from __future__ import annotations

import numpy as np

__all__ = ["build_1d_graph", "chain_links"]


def chain_links(num_nodes: int) -> list[tuple[int, int]]:
    """Undirected links of a single open chain 0-1-2-...-(n-1)."""
    return [(i, i + 1) for i in range(num_nodes - 1)]


def build_1d_graph(
    x: np.ndarray,
    z_bottom: np.ndarray,
    width: np.ndarray,
    links: list[tuple[int, int]] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Build the 1D network graph.

    Parameters
    ----------
    x: [N] longitudinal abscissa [m] (increasing downstream within a branch).
    z_bottom: [N] bed elevation [m].
    width: [N] active channel width [m].
    links: undirected (i, j) section pairs; defaults to a single chain in
        node order.

    Returns
    -------
    edge_index: [2, 2*len(links)] int64, both orientations per link.
    edge_attr: [2*len(links), 3] float32: [dx, width_avg, bed_slope] with
        bed_slope = (z_j - z_i) / dx signed along the arc direction.
    """
    x = np.asarray(x, dtype=np.float64)
    z = np.asarray(z_bottom, dtype=np.float64)
    w = np.asarray(width, dtype=np.float64)
    n = x.size
    if links is None:
        links = chain_links(n)

    src, dst, feats = [], [], []
    for i, j in links:
        dx = abs(x[j] - x[i])
        if dx <= 0:
            raise ValueError(f"Degenerate link ({i}, {j}): zero length")
        for a, b in ((i, j), (j, i)):
            src.append(a)
            dst.append(b)
            feats.append([dx, 0.5 * (w[a] + w[b]), (z[b] - z[a]) / dx])

    edge_index = np.stack([src, dst], axis=0).astype(np.int64)
    edge_attr = np.asarray(feats, dtype=np.float32)
    return edge_index, edge_attr
