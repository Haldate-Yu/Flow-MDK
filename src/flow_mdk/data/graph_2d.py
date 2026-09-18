"""2D floodplain graph construction (M3, brought online for M0 scenarios).

The dual graph follows SWE-GNN Fig. 1: cell centres are nodes; neighbouring
cells are connected; edge features are the outward unit normal n_ij and the
shared side length l_ij. For structured grids the direction between centres
coincides with the face normal, which keeps the construction exact.

Also hosts the Perlin-noise DEM generator used to reproduce the SWE-GNN
scenario family (random plausible topographies, Perlin 2002).
"""

from __future__ import annotations

import numpy as np

__all__ = ["build_2d_grid_graph", "perlin_dem"]


def build_2d_grid_graph(
    nx: int,
    ny: int,
    dx: float,
    dy: float,
    connectivity: int = 4,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Dual graph of a structured nx x ny grid (row-major, y fastest).

    Returns
    -------
    edge_index: [2, 2*num_links] both orientations of every neighbour link.
    edge_attr: [2*num_links, 3]: [normal_x, normal_y, side_length] where the
        normal points from source to target node.
    cell_centers: [N, 2] physical coordinates (x, y) of cell centres.
    """
    if connectivity not in (4, 8):
        raise ValueError("connectivity must be 4 or 8")

    xs = (np.arange(nx) + 0.5) * dx
    ys = (np.arange(ny) + 0.5) * dy
    xx, yy = np.meshgrid(xs, ys, indexing="ij")  # [nx, ny]
    centers = np.stack([xx.ravel(), yy.ravel()], axis=1)

    def nid(i: int, j: int) -> int:
        return i * ny + j

    offsets = [(1, 0), (0, 1)]  # each undirected link visited exactly once
    if connectivity == 8:
        offsets += [(1, 1), (1, -1)]

    src, dst, feats = [], [], []
    for di, dj in offsets:
        i_range = range(max(0, -di), nx - max(0, di))
        j_range = range(max(0, -dj), ny - max(0, dj))
        for i in i_range:
            for j in j_range:
                a, b = nid(i, j), nid(i + di, j + dj)
                vec = centers[b] - centers[a]
                dist = float(np.hypot(*vec))
                normal = vec / dist
                # shared face length: dx for vertical neighbours, dy for
                # horizontal ones; diagonal links (connectivity 8) use the
                # mean of both (approximation, flagged in the metadata).
                length = dx if dj == 0 else dy
                if di != 0 and dj != 0:
                    length = 0.5 * (dx + dy)
                for u, v in ((a, b), (b, a)):
                    src.append(u)
                    dst.append(v)
                    nx_, ny_ = (centers[v] - centers[u]) / dist
                    feats.append([nx_, ny_, length])

    edge_index = np.stack([src, dst], axis=0).astype(np.int64)
    edge_attr = np.asarray(feats, dtype=np.float32)
    return edge_index, edge_attr, centers


# ---------------------------------------------------------------------- #
# Perlin noise DEM
# ---------------------------------------------------------------------- #
def _smoothstep(t: np.ndarray) -> np.ndarray:
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _perlin_octave(shape: tuple[int, int], freq: tuple[int, int], rng: np.random.Generator) -> np.ndarray:
    """One Perlin octave on a regular grid of ``shape`` cells."""
    nx, ny = shape
    fx, fy = freq
    # lattice gradients at (fx+1) x (fy+1) corners
    angles = rng.uniform(0.0, 2.0 * np.pi, size=(fx + 1, fy + 1))
    grad_x, grad_y = np.cos(angles), np.sin(angles)

    gx = np.linspace(0.0, fx, nx, endpoint=False)
    gy = np.linspace(0.0, fy, ny, endpoint=False)
    i0 = np.floor(gx).astype(int)
    j0 = np.floor(gy).astype(int)
    tx = _smoothstep(gx - i0)  # [nx]
    ty = _smoothstep(gy - j0)  # [ny]

    # corner dot products for every cell: broadcast to [nx, ny]
    def dot_at(i_off: int, j_off: int) -> np.ndarray:
        rx = (gx - i0) - i_off  # offset of sample inside the lattice cell
        ry = (gy - j0) - j_off
        gxg = grad_x[i0 + i_off, :][:, j0 + j_off]  # [nx, ny]
        gyg = grad_y[i0 + i_off, :][:, j0 + j_off]
        return gxg * rx[:, None] + gyg * ry[None, :]

    n00 = dot_at(0, 0)
    n10 = dot_at(1, 0)
    n01 = dot_at(0, 1)
    n11 = dot_at(1, 1)
    nx0 = n00 + tx[:, None] * (n10 - n00)
    nx1 = n01 + tx[:, None] * (n11 - n01)
    return nx0 + ty[None, :] * (nx1 - nx0)


def perlin_dem(
    shape: tuple[int, int],
    cell_size: float,
    z_range: tuple[float, float] = (0.0, 5.0),
    base_freq: int = 4,
    octaves: int = 4,
    persistence: float = 0.5,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Random plausible topography via fractal Perlin noise (SWE-GNN Sec. 4.1).

    Returns
    -------
    elevation: [nx, ny] terrain elevation [m].
    gradients: [nx, ny, 2] central-difference slope components (dz/dx, dz/dy).
    """
    rng = np.random.default_rng(seed)
    field = np.zeros(shape)
    freq = float(base_freq)
    amp = 1.0
    for _ in range(octaves):
        fx = max(1, int(round(freq)))
        field += amp * _perlin_octave(shape, (fx, fx), rng)
        freq *= 2.0
        amp *= persistence

    zmin, zmax = field.min(), field.max()
    if zmax - zmin < 1e-12:
        field = np.zeros(shape)
    else:
        field = (field - zmin) / (zmax - zmin)
    elevation = z_range[0] + field * (z_range[1] - z_range[0])

    gx = np.gradient(elevation, cell_size, axis=0)
    gy = np.gradient(elevation, cell_size, axis=1)
    gradients = np.stack([gx, gy], axis=-1)
    return elevation.astype(np.float64), gradients.astype(np.float64)
