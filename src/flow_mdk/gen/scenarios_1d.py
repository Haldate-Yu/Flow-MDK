"""1D scenario family: geometry, hydrographs, reference solver, assembly.

Reference solver
----------------
Implicit diffusive-wave on a rectangular channel:

    continuity : d(B h)/dt + dQ/dx = 0
    flux       : Q = K (B h) h^{2/3} sqrt(S_f),  S_f = (w_i - w_j)/dx,
                 w = z_b + h (water surface)

Solved with a Newton iteration on the water-surface vector (tridiagonal
Jacobians, Thomas algorithm). The smooth flux law
``f(s) = s / sqrt(|s| + eps)`` keeps the Jacobian well-posed at slack water
and recovers the square-root law away from it. Dry sections carry no flux
naturally because the conveyance C ~ h^{5/3} vanishes.

The diffusive wave is exactly the "diffusive backwater" regime the MDK
branch targets, which makes it a useful testbed for M2 ablations — while
Mascaret (full 1D SWE) provides the production ground truth.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from flow_mdk.data.features import layouts_1d
from flow_mdk.data.graph_1d import build_1d_graph
from flow_mdk.data.topology import edge_activity_sequence
from flow_mdk.utils.io import Scenario

__all__ = [
    "Scenario1DParams",
    "DiffusiveWaveSolver",
    "generate_1d_scenario",
    "hydrograph",
]


@dataclass
class Scenario1DParams:
    length: float = 10_000.0  # reach length [m]
    num_sections: int = 100
    slope: float = 1e-3  # bed slope
    bed_form_amplitude: float = 0.5  # smooth bed-form amplitude [m]
    width_base: float = 20.0
    width_amplitude: float = 6.0  # sinusoidal width variation
    strickler_base: float = 30.0  # K [m^{1/3}/s]
    strickler_rel_std: float = 0.25  # lognormal patch relative std
    patch_scale: float = 1000.0  # roughness patch length scale [m]
    q_base: float = 5.0  # base flow [m3/s]
    q_peak: float = 120.0
    time_to_peak: float = 3600.0  # hydrograph time to peak [s]
    peak_sharpness: float = 3.0  # gamma-shape exponent (steep peak if high)
    dt: float = 30.0  # solver time step [s]
    dt_out: float = 600.0  # output frame interval [s]
    duration: float = 8 * 3600.0  # simulated time [s]
    seed: int = 0


def hydrograph(t: np.ndarray, params: Scenario1DParams) -> np.ndarray:
    """Gamma-shaped inflow hydrograph: base flow + single peak."""
    shape = np.power(
        np.clip(t / params.time_to_peak, 0.0, None) * np.exp(1.0 - t / params.time_to_peak),
        params.peak_sharpness,
    )
    return params.q_base + (params.q_peak - params.q_base) * shape


def _thomas_solve(lower: np.ndarray, diag: np.ndarray, upper: np.ndarray, rhs: np.ndarray) -> np.ndarray:
    """Tridiagonal solve (Thomas algorithm); arrays are modified in place."""
    n = diag.size
    cp = np.empty(n)
    dp = np.empty(n)
    cp[0] = upper[0] / diag[0]
    dp[0] = rhs[0] / diag[0]
    for i in range(1, n):
        m = diag[i] - lower[i] * cp[i - 1]
        cp[i] = upper[i] / m if i < n - 1 else 0.0
        dp[i] = (rhs[i] - lower[i] * dp[i - 1]) / m
    x = np.empty(n)
    x[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


class DiffusiveWaveSolver:
    """Implicit diffusive-wave solver on a rectangular 1D reach."""

    FLUX_EPS = 1e-4  # [m] slack-water smoothing scale

    def __init__(self, x: np.ndarray, z: np.ndarray, width: np.ndarray, strickler: np.ndarray):
        self.x = np.asarray(x, float)
        self.z = np.asarray(z, float)
        self.b = np.asarray(width, float)
        self.k = np.asarray(strickler, float)
        self.n = self.x.size
        self.dx = np.diff(self.x)
        if np.any(self.dx <= 0):
            raise ValueError("section abscissa must be strictly increasing")

    # flux and its derivatives w.r.t. the two end water levels
    def _flux(self, wl: float, wr: float, il: int, ir: int):
        dx = self.dx[il]
        hl = max(wl - self.z[il], 0.0)
        hr = max(wr - self.z[ir], 0.0)
        hbar = 0.5 * (hl + hr)
        if hbar <= 0.0:
            return 0.0, 0.0, 0.0
        bbar = 0.5 * (self.b[il] + self.b[ir])
        kbar = 0.5 * (self.k[il] + self.k[ir])
        c = kbar * bbar * hbar ** (5.0 / 3.0) / np.sqrt(dx)
        s = wl - wr
        f = s / np.sqrt(abs(s) + self.FLUX_EPS)
        q = c * f
        dc_dh = (5.0 / 3.0) * kbar * bbar * hbar ** (2.0 / 3.0) / np.sqrt(dx)
        df_ds = (0.5 * abs(s) + self.FLUX_EPS) / (abs(s) + self.FLUX_EPS) ** 1.5
        # hbar depends on each end level with factor 1/2
        dq_dwl = 0.5 * dc_dh * f + c * df_ds
        dq_dwr = 0.5 * dc_dh * f - c * df_ds
        return q, dq_dwl, dq_dwr

    def run(self, q_in: np.ndarray, times: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray, float]:
        """Integrate at step ``dt`` over the fine grid ``times`` (spacing == dt).

        Boundary conditions: prescribed inflow Q_up(t) at the upstream end;
        normal-depth free outflow at the downstream end. Returns per-step
        fields (h [T,N], Q_nodes [T,N]) and the wall-clock runtime; the
        caller subsamples to the output interval.
        """
        t0 = time.perf_counter()
        n = self.n
        h = np.zeros(n)  # dry start
        w = self.z + h

        steps = len(times) - 1
        h_out = [h.copy()]
        q_out = [np.zeros(n)]
        for step in range(1, steps + 1):
            q_up = float(q_in[step])
            w = self._newton_step(w, h, q_up, dt)
            h = np.maximum(w - self.z, 0.0)
            q_mid = self._interface_fluxes(w)
            q_nodes = np.empty(n)
            q_nodes[1:-1] = 0.5 * (q_mid[:-1] + q_mid[1:])
            q_nodes[0] = q_up
            q_nodes[-1] = q_mid[-1]
            h_out.append(h.copy())
            q_out.append(q_nodes)

        runtime = time.perf_counter() - t0
        return np.asarray(h_out), np.asarray(q_out), runtime

    def _interface_fluxes(self, w: np.ndarray) -> np.ndarray:
        q = np.empty(self.n - 1)
        for i in range(self.n - 1):
            q[i] = self._flux(w[i], w[i + 1], i, i + 1)[0]
        return q

    def _normal_outflow(self, w_last: float, i: int):
        h = max(w_last - self.z[i], 0.0)
        s0 = max((self.z[i - 1] - self.z[i]) / self.dx[i - 1], 1e-5)
        if h <= 0:
            return 0.0, 0.0
        c = self.k[i] * self.b[i] * h ** (5.0 / 3.0)
        q = c * np.sqrt(s0)
        dq_dw = (5.0 / 3.0) * self.k[i] * self.b[i] * h ** (2.0 / 3.0) * np.sqrt(s0)
        return q, dq_dw

    def _newton_step(self, w: np.ndarray, h_prev: np.ndarray, q_up: float, dt: float) -> np.ndarray:
        """One implicit step: Newton on the water surface w (tridiagonal J).

        The continuity residual uses the *signed* area B (w - z) so that the
        filling of a dry upstream node is well-posed at start-up (conveyance
        stays clamped at zero depth inside the flux law); tiny negative
        depths of order dt*q/(B dx) are an accepted start-up artifact and
        are clipped when the fields are written.
        """
        n = self.n
        w = w.copy()
        area_prev = self.b * h_prev
        for _ in range(20):
            lower = np.zeros(n)
            diag = np.zeros(n)
            upper = np.zeros(n)
            rhs = np.zeros(n)

            q_dn, dq_dn_dw = self._normal_outflow(w[-1], n - 1)

            for i in range(n):
                area_new = self.b[i] * (w[i] - self.z[i])
                if i == 0:
                    q_r, dqr_wl, dqr_wr = self._flux(w[0], w[1], 0, 1)
                    r = area_new - area_prev[0] + dt / self.dx[0] * (q_r - q_up)
                    diag[0] = self.b[0] + dt / self.dx[0] * dqr_wl
                    upper[0] = dt / self.dx[0] * dqr_wr
                elif i == n - 1:
                    q_l, dql_wl, dql_wr = self._flux(w[-2], w[-1], n - 2, n - 1)
                    r = area_new - area_prev[-1] + dt / self.dx[-1] * (q_dn - q_l)
                    lower[-1] = -dt / self.dx[-1] * dql_wl
                    diag[-1] = self.b[-1] + dt / self.dx[-1] * (dq_dn_dw - dql_wr)
                else:
                    dx = 0.5 * (self.dx[i - 1] + self.dx[i])
                    q_l, dql_wl, dql_wr = self._flux(w[i - 1], w[i], i - 1, i)
                    q_r, dqr_wl, dqr_wr = self._flux(w[i], w[i + 1], i, i + 1)
                    r = area_new - area_prev[i] + dt / dx * (q_r - q_l)
                    lower[i] = -dt / dx * dql_wl
                    diag[i] = self.b[i] + dt / dx * (dqr_wl - dql_wr)
                    upper[i] = dt / dx * dqr_wr
                rhs[i] = -r

            dw = _thomas_solve(lower, diag, upper, rhs)
            w = w + dw
            if np.max(np.abs(dw)) < 1e-7:
                break
        else:
            raise RuntimeError("Newton iteration did not converge; reduce dt")
        return w


def generate_1d_scenario(params: Scenario1DParams, name: str) -> Scenario:
    """Sample one scenario family member and run the reference solver."""
    rng = np.random.default_rng(params.seed)
    n = params.num_sections
    x = np.linspace(0.0, params.length, n)

    # bed: plane slope + smooth random bed forms of bounded amplitude
    pert = np.cumsum(rng.normal(0.0, 0.02, n))
    pert = np.convolve(pert, np.ones(9) / 9.0, mode="same")
    pert -= np.linspace(pert[0], pert[-1], n)  # remove trend to keep slope
    std = pert.std()
    pert = pert / std * params.bed_form_amplitude if std > 1e-12 else pert * 0.0
    z = params.slope * (params.length - x) + pert

    # width: sinusoidal variation + noise
    phase = rng.uniform(0.0, 2.0 * np.pi)
    width = params.width_base + params.width_amplitude * np.sin(
        2 * np.pi * x / params.length * rng.uniform(1.0, 3.0) + phase
    )
    width += rng.normal(0.0, 0.5, n)
    width = np.clip(width, params.width_base * 0.5, None)

    # Strickler field: lognormal patches (plan M0: 糙率 K 场扰动)
    patch_centers = np.arange(0.0, params.length, params.patch_scale)
    weights = np.exp(-0.5 * ((x[:, None] - patch_centers[None, :]) / params.patch_scale) ** 2)
    weights /= weights.sum(axis=1, keepdims=True)
    log_factors = np.log(np.clip(
        rng.normal(1.0, params.strickler_rel_std, patch_centers.size), 0.5, 2.0
    ))
    strickler = params.strickler_base * np.exp(weights @ log_factors)

    times = np.arange(0.0, params.duration + 1e-9, params.dt)
    q_in = hydrograph(times, params)

    solver = DiffusiveWaveSolver(x, z, width, strickler)
    h, q_nodes, runtime = solver.run(q_in, times, params.dt)

    out_every = max(1, int(round(params.dt_out / params.dt)))
    h_frames = h[::out_every]
    q_frames = q_nodes[::out_every]
    times_out = times[::out_every]

    # graph + statics
    edge_index, edge_attr = build_1d_graph(x, z, width)
    boundary_flag = np.zeros(n)
    boundary_flag[0], boundary_flag[-1] = 1.0, 2.0
    node_static = np.stack([z, width, strickler, boundary_flag], axis=1).astype(np.float32)
    dynamic = np.stack([h_frames, q_frames], axis=-1).astype(np.float32)  # [T, N, 2]
    wet = (h_frames > 1e-3).astype(np.uint8)

    layout = layouts_1d
    activity = edge_activity_sequence(wet, edge_index, gate="source")
    meta = {
        "layout": layout.name,
        "dynamic_vars": list(layout.dynamic_names),
        "elevation_feature_idx": layout.elevation_feature_idx,
        "solver": "diffusive_wave_reference",
        "solver_params": {
            "dt": params.dt,
            "duration": params.duration,
            "q_peak": params.q_peak,
            "time_to_peak": params.time_to_peak,
            "peak_sharpness": params.peak_sharpness,
        },
        "geometry": {"length": params.length, "num_sections": n, "slope": params.slope},
        "boundary": {"upstream": "inflow_hydrograph", "downstream": "normal_depth"},
        "runtime_s": runtime,
        "edge_activity": {
            "appear_frames": int((np.diff(activity.astype(np.int8), axis=0) > 0).sum()),
            "disappear_frames": int((np.diff(activity.astype(np.int8), axis=0) < 0).sum()),
        },
    }

    return Scenario(
        name=name,
        node_static=node_static,
        edge_index=edge_index,
        edge_attr=edge_attr,
        dynamic=dynamic,
        wet=wet,
        times=times_out,
        meta=meta,
        edge_flow=None,
    )
