"""Feature layout conventions shared by generators, datasets and models.

Layouts
-------
1D (Mascaret-style river chain):

====================  ===  ============================
static channel        idx  content
====================  ===  ============================
z_bottom (elevation)  0    bed elevation [m]
width                 1    active channel width [m]
strickler_k           2    Strickler/Manning K [m^1/3/s]
boundary_flag         3    0 interior, 1 inflow, 2 outflow
====================  ===  ============================
dynamic: ``[h, Q]`` — water depth [m], discharge [m3/s] (plan: 1D uses Q).
edge: ``[dx, width_avg, bed_slope]``.

2D (SWE-GNN Sec. 3.2, Eq. 11):

====================  ===  ============================
static channel        idx  content
====================  ===  ============================
area                  0    cell area [m2]
elevation             1    terrain elevation [m]
slope_x               2
slope_y               3
manning               4
====================  ===  ============================
dynamic: ``[h, |q|]`` — depth [m], unit-discharge modulus [m2/s].
edge: ``[normal_x, normal_y, length]`` (outward unit normal, side length).

The water level ``w = elevation + h`` is *not stored* in scenario files: it
is appended as the last static channel at window-build time
(:func:`attach_water_level`), exactly because it must track the current
frame during rollouts (SWE-GNN Sec. 3.1.3).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["FeatureLayout", "attach_water_level", "layouts_2d"]


@dataclass(frozen=True)
class FeatureLayout:
    name: str
    static_names: tuple[str, ...]
    dynamic_names: tuple[str, ...]
    edge_names: tuple[str, ...]
    elevation_feature_idx: int  # channel inside *base* static features

    @property
    def num_static(self) -> int:
        return len(self.static_names) + 1  # + appended water level

    @property
    def num_dynamic(self) -> int:
        return len(self.dynamic_names)

    @property
    def num_edge(self) -> int:
        return len(self.edge_names)


layouts_2d = FeatureLayout(
    name="2d_grid",
    static_names=("area", "elevation", "slope_x", "slope_y", "manning"),
    dynamic_names=("h", "|q|"),
    edge_names=("normal_x", "normal_y", "length"),
    elevation_feature_idx=1,
)


def attach_water_level(
    static: np.ndarray, elevation_idx: int, depth: np.ndarray
) -> np.ndarray:
    """Append the water-level channel ``w = elevation + h`` to base statics.

    static: [N, Fs_base] base features; depth: [N] current water depth.
    Returns [N, Fs_base + 1].
    """
    w = (static[:, elevation_idx] + depth).astype(static.dtype, copy=False)
    return np.concatenate([static, w[:, None]], axis=1)
