"""Tests for the 1D reference solver (diffusive wave)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.gen.scenarios_1d import Scenario1DParams, generate_1d_scenario


def _params(**kw) -> Scenario1DParams:
    return Scenario1DParams(num_sections=40, duration=4 * 3600, dt=30.0,
                            length=5000.0, seed=7, **kw)


def test_solver_mass_balance():
    """Inflow volume ≈ outflow volume + stored volume (loose tolerance)."""
    p = _params(q_peak=100.0)
    sc = generate_1d_scenario(p, "mb")
    h, q = sc.dynamic[..., 0], sc.dynamic[..., 1]
    dx = p.length / (p.num_sections - 1)
    width = sc.node_static[:, 1].mean()
    stored = float((h[-1] * width * dx).sum())
    inflow_vol = float(np.trapezoid(q[:, 0], sc.times))
    outflow_vol = float(np.trapezoid(q[:, -1], sc.times))
    # volume arriving but still travelling ≈ stored; allow slack for the
    # discretised downstream law
    assert inflow_vol - outflow_vol >= -0.05 * inflow_vol
    assert abs((inflow_vol - outflow_vol) - stored) < 0.25 * inflow_vol


def test_flood_wave_propagates_downstream():
    p = _params(q_peak=120.0, time_to_peak=1800.0, peak_sharpness=4.0)
    sc = generate_1d_scenario(p, "wave")
    q = sc.dynamic[..., 1]
    t_up = int(np.argmax(q[:, 0]))
    t_down = int(np.argmax(q[:, -1]))
    assert t_down > t_up, "flood peak must arrive later downstream"
    assert np.isfinite(sc.dynamic).all()


def test_dry_start_and_wetting_front():
    sc = generate_1d_scenario(_params(), "dry")
    h = sc.dynamic[..., 0]
    assert np.all(h[0] == 0.0)  # dry initial condition
    wet = sc.wet
    assert wet[0].sum() == 0 and wet[-1].sum() > 0


def test_scenario_meta_complete():
    sc = generate_1d_scenario(_params(), "meta")
    for key in ("layout", "dynamic_vars", "elevation_feature_idx", "solver",
                "runtime_s", "boundary"):
        assert key in sc.meta
    assert sc.meta["layout"] == "1d_chain"
    assert sc.meta["solver"] == "diffusive_wave_reference"
