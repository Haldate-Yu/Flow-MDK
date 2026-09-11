"""2D scenario family (plan M0: Perlin-noise DEM + parameterised boundary).

Mirrors the SWE-GNN dataset construction (Sec. 4.1): random plausible
topographies over a square polder domain, dry initial condition, constant
inflow discharge through a breach on the border. Ground truth comes from
TELEMAC-2D (``scripts/run_telemac2d_docker.py``); scenarios generated here
are self-consistent training inputs even before a solver run attaches truth
(``dynamic`` is filled with zeros and ``meta["solver"] = "pending"``).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from flow_mdk.data.features import layouts_2d
from flow_mdk.data.graph_2d import build_2d_grid_graph, perlin_dem
from flow_mdk.data.topology import edge_activity_sequence
from flow_mdk.utils.io import Scenario

__all__ = ["Scenario2DParams", "generate_2d_scenario"]


@dataclass
class Scenario2DParams:
    nx: int = 64
    ny: int = 64
    cell_size: float = 100.0  # [m]
    z_range: tuple[float, float] = (0.0, 5.0)
    base_freq: int = 4
    octaves: int = 4
    manning: float = 0.03
    breach_discharge: float = 50.0  # [m3/s] constant inflow (SWE-GNN setting)
    breach_width_cells: int = 3
    breach_side: str = "west"  # west/east/south/north
    simulation_hours: float = 48.0
    dt_out: float = 1800.0  # output frame interval [s]
    seed: int = 0


def _breach_cells(params: Scenario2DParams) -> list[int]:
    """Border cells through which the breach inflow enters, as node ids."""
    ny = params.ny
    half = params.breach_width_cells // 2
    j0 = ny // 2
    js = range(max(0, j0 - half), min(ny, j0 + half + 1))
    if params.breach_side == "west":
        return [0 * ny + j for j in js]
    if params.breach_side == "east":
        return [(params.nx - 1) * ny + j for j in js]
    if params.breach_side == "south":
        return [i * ny + 0 for i in range(max(0, j0 - half), min(params.nx, j0 + half + 1))]
    if params.breach_side == "north":
        return [i * ny + (params.ny - 1) for i in range(max(0, j0 - half), min(params.nx, j0 + half + 1))]
    raise ValueError(f"Unknown breach side: {params.breach_side}")


def generate_2d_scenario(params: Scenario2DParams, name: str) -> Scenario:
    """Generate one Perlin DEM flood scenario (dual graph, no truth yet)."""
    elevation, gradients = perlin_dem(
        (params.nx, params.ny),
        params.cell_size,
        z_range=params.z_range,
        base_freq=params.base_freq,
        octaves=params.octaves,
        seed=params.seed,
    )
    edge_index, edge_attr, centers = build_2d_grid_graph(
        params.nx, params.ny, params.cell_size, params.cell_size
    )

    n = params.nx * params.ny
    area = np.full(n, params.cell_size**2, dtype=np.float32)
    elevation_flat = elevation.ravel().astype(np.float32)
    slope_flat = gradients.reshape(-1, 2).astype(np.float32)
    manning = np.full(n, params.manning, dtype=np.float32)
    breach = np.zeros(n, dtype=np.float32)
    breach_nodes = _breach_cells(params)
    breach[breach_nodes] = 1.0
    node_static = np.stack(
        [area, elevation_flat, slope_flat[:, 0], slope_flat[:, 1], manning, breach],
        axis=1,
    )

    num_frames = int(params.simulation_hours * 3600.0 / params.dt_out) + 1
    times = np.arange(num_frames) * params.dt_out
    dynamic = np.zeros((num_frames, n, 2), dtype=np.float32)  # filled by solver
    wet = np.zeros((num_frames, n), dtype=np.uint8)

    activity = edge_activity_sequence(wet, edge_index, gate="source")
    meta = {
        "layout": layouts_2d.name,
        "dynamic_vars": list(layouts_2d.dynamic_names),
        "elevation_feature_idx": layouts_2d.elevation_feature_idx,
        "solver": "pending",  # filled by scripts/run_telemac2d_docker.py
        "grid": {
            "nx": params.nx,
            "ny": params.ny,
            "cell_size": params.cell_size,
            "connectivity": 4,
        },
        "boundary": {
            "type": "breach_inflow",
            "discharge": params.breach_discharge,
            "nodes": [int(i) for i in breach_nodes],
            "side": params.breach_side,
        },
        "initial_condition": "dry",
        "simulation_hours": params.simulation_hours,
        "dt_out": params.dt_out,
        "runtime_s": None,
        "topology_changes": int((np.diff(activity.astype(np.int8), axis=0) != 0).sum()),
    }
    return Scenario(
        name=name,
        node_static=node_static,
        edge_index=edge_index,
        edge_attr=edge_attr,
        dynamic=dynamic,
        wet=wet,
        times=times,
        meta=meta,
    )
