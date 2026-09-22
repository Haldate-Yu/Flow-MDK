"""Regression tests for the coupling-family condition draws.

Guards the 2026-09-21 fix: a scenario's (q_scale, t_stretch) must be keyed by
its index and must not depend on which scenarios already exist on disk. Before
the fix the draws happened after the "npz exists -> skip" check, so extending
or resuming a batch shifted the stream and produced duplicate condition draws.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_coupled_family import (  # noqa: E402
    Q_SCALE_RANGE, TIME_STRETCH_RANGE, _draw_conditions, _upsert,
)


def test_index_zero_is_the_parity_draw_and_consumes_no_rng():
    draws = _draw_conditions(11, 12)
    assert draws[0] == (1.0, 1.0)


def test_draws_match_the_recorded_family():
    """fam001/fam002 as recorded in coupled_family_report.json."""
    d = _draw_conditions(11, 12)
    assert d[1] == pytest.approx((0.692855, 1.199422), abs=1e-6)
    assert d[2] == pytest.approx((1.402248, 0.822951), abs=1e-6)


def test_extending_num_does_not_change_earlier_draws():
    """The whole point of the fix: --num 20 must not perturb fam001-011."""
    small, large = _draw_conditions(11, 12), _draw_conditions(11, 20)
    assert large[:12] == small
    # and the 13th scenario onward are new values, not repeats of fam001+
    assert large[12] not in small[1:]


def test_stream_is_reproducible_from_the_record():
    """Replaying the RNG by hand reproduces the same per-index draws."""
    rng = np.random.default_rng(11)
    d = _draw_conditions(11, 8)
    for i in range(1, 8):
        assert d[i] == (pytest.approx(rng.uniform(*Q_SCALE_RANGE)),
                        pytest.approx(rng.uniform(*TIME_STRETCH_RANGE)))


def test_upsert_keeps_history_and_sorts():
    rep = [{"name": "b", "status": "ok"}, {"name": "a", "status": "ok"}]
    rep = _upsert(rep, {"name": "b", "status": "failed"})
    assert [r["name"] for r in rep] == ["a", "b"]
    assert rep[1]["status"] == "failed"
    assert len(rep) == 2  # replaced, not appended twice
