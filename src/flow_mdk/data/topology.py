"""Dry/wet topology bookkeeping (plan M0: 干湿判定与图拓扑快照).

The wet mask drives (a) the per-step renormalization of the MDK transition
matrix and (b) the "topology snapshots": which edges are active over time.
Only the *activity* is stored (uint8 per frame), never a new graph, keeping
the npz schema compact.
"""

from __future__ import annotations

import numpy as np

__all__ = ["edge_activity_sequence", "topology_transitions", "wet_mask"]


def wet_mask(depth: np.ndarray, threshold: float = 1e-3) -> np.ndarray:
    """Boolean wet mask from a depth field.

    depth: [T, N] (or [N]); returns matching bool array.
    """
    return depth > threshold


def edge_activity_sequence(
    wet: np.ndarray,
    edge_index: np.ndarray,
    gate: str = "source",
) -> np.ndarray:
    """Per-frame arc activity used by the diffusion sub-graph.

    wet: [T, N] uint8/bool; edge_index: [2, E] directed arcs.
    gate="source": an arc is active when its *source* node is wet (dry nodes
    never relay diffusion); gate="both" requires both endpoints wet.

    Returns [T, E] uint8.
    """
    if gate not in ("source", "both"):
        raise ValueError(f"Unknown gate: {gate}")
    w = wet.astype(bool)
    src_wet = w[:, edge_index[0]]
    if gate == "source":
        return src_wet.astype(np.uint8)
    return (src_wet & w[:, edge_index[1]]).astype(np.uint8)


def topology_transitions(activity: np.ndarray) -> dict[str, np.ndarray]:
    """Frames at which arcs appear or disappear (topology change log).

    activity: [T, E] uint8 from :func:`edge_activity_sequence`.
    Returns {"appear_frames": [K], "disappear_frames": [K], "arc_ids": [K]}.
    """
    diff = np.diff(activity.astype(np.int8), axis=0)
    appear_t, appear_e = np.nonzero(diff > 0)
    vanish_t, vanish_e = np.nonzero(diff < 0)
    return {
        "appear_frames": appear_t,
        "disappear_frames": vanish_t,
        "arc_ids": np.concatenate([appear_e, vanish_e]),
    }
