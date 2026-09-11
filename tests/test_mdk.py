"""Tests for the MDK propagation core."""

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.layers.mdk import (
    MDKPropagation,
    direction_gates,
    hydraulic_edge_weights,
    suggest_num_steps,
)


def _chain(n: int):
    """Chain graph with both arc orientations, uniform weights."""
    src, dst = [], []
    for i in range(n - 1):
        src += [i, i + 1]
        dst += [i + 1, i]
    edge_index = torch.tensor([src, dst], dtype=torch.long)
    weight = torch.ones(edge_index.size(1))
    return edge_index, weight


def test_suggest_num_steps_matches_diffusion_length():
    # D=1 m2/s, dt=100 s -> L_d = sqrt(200) ~ 14.1 m; dx=10 m -> K=2
    assert suggest_num_steps(1.0, 100.0, 10.0) == 2
    assert suggest_num_steps(1.0, 100.0, 100.0) == 1
    assert suggest_num_steps(0.0, 100.0, 10.0) == 1  # floor at 1


def test_lambda0_one_is_identity():
    edge_index, weight = _chain(4)
    x = torch.randn(4, 3)
    mdk = MDKPropagation(num_steps=2, weighting="geometric", lambda0=1.0,
                         learn_lambda=False)
    out = mdk(x, edge_index, weight)
    assert torch.allclose(out, x, atol=1e-6)


def test_series_spreads_one_hop_and_renormalizes():
    edge_index, weight = _chain(3)  # arcs: 0->1, 1->0, 1->2, 2->1
    # x = one-hot at node 0; uniform weights -> P mixes neighbours equally
    x = torch.zeros(3, 1)
    x[0, 0] = 1.0
    mdk = MDKPropagation(num_steps=1, weighting="uniform", lambda0=0.0,
                         learn_lambda=False)
    out = mdk(x, edge_index, weight)
    # with lambda0 = 0 the identity term vanishes: a node keeps nothing of its
    # own value; node 1 receives 0.5 from upstream (node 0), nodes 0/2 get 0
    assert torch.allclose(out[:, 0], torch.tensor([0.0, 0.5, 0.0]), atol=1e-6)


def test_geometric_weights_truncated_sum():
    edge_index, weight = _chain(3)
    x = torch.ones(3, 1)
    mdk = MDKPropagation(num_steps=4, weighting="geometric", lambda0=0.3,
                         learn_lambda=False)
    out = mdk(x, edge_index, weight)
    # constant field: P^m x == x, so out = x * sum_m lambda0 (1-lambda0)^m
    total = sum(0.3 * 0.7 ** m for m in range(5))
    assert torch.allclose(out, total * x, atol=1e-5)
    # renormalized variant restores magnitude 1
    mdk_rn = MDKPropagation(num_steps=4, weighting="geometric", lambda0=0.3,
                            learn_lambda=False, renormalize=True)
    assert torch.allclose(mdk_rn(x, edge_index, weight), x, atol=1e-5)


def test_dry_sources_never_relay():
    edge_index, weight = _chain(3)  # 0 - 1 - 2
    wet = torch.tensor([False, True, False])
    # wet node 1 carries a signal; dry nodes 0/2 have zero increments
    x = torch.zeros(3, 2)
    x[1, 0] = 1.0
    mdk = MDKPropagation(num_steps=2, weighting="uniform", lambda0=0.0,
                         learn_lambda=False)
    out = mdk(x, edge_index, weight, wet_mask=wet)
    # node 0 and 2 receive from wet node 1 (wetting), node 1 keeps its signal,
    # and no signal can hop *through* a dry node (2 hops reach nothing new)
    assert out[0, 0] > 0 and out[2, 0] > 0
    x2 = torch.zeros(3, 2)
    x2[0, 1] = 1.0  # signal only on a dry node: must not propagate at all
    out2 = mdk(x2, edge_index, weight, wet_mask=wet)
    assert torch.allclose(out2, torch.zeros(3, 2), atol=1e-7)


def test_symmetric_mode_runs():
    edge_index, weight = _chain(4)
    x = torch.randn(4, 2)
    mdk = MDKPropagation(num_steps=2, weighting="geometric", lambda0=0.3,
                         learn_lambda=False, symmetric=True)
    out = mdk(x, edge_index, weight)
    assert out.shape == x.shape and torch.isfinite(out).all()


def test_learned_lambda0_range():
    mdk = MDKPropagation(num_steps=1, lambda0=0.9, learn_lambda=True)
    val = float(mdk.lambda0)
    assert 0.02 <= val < 1.0


def test_hydraulic_weights_and_direction_gates():
    n = 3
    edge_index = torch.tensor([[0, 1, 1, 2], [1, 0, 2, 1]])
    h = torch.tensor([1.0, 0.5, 0.0])
    q = torch.tensor([10.0, 5.0, 0.0])
    w = hydraulic_edge_weights(h, q, edge_index, mode="discharge")
    assert torch.allclose(w, torch.tensor([7.5, 7.5, 2.5, 2.5]))
    wse = torch.tensor([10.0, 9.0, 9.0])  # node 0 upstream, 1-2 flat
    g = direction_gates(wse, edge_index, beta=10.0)
    # downhill arc 0->1 open, uphill arc 1->0 shut, flat pair splits 0.5/0.5
    assert g[0] > 0.99 and g[1] < 0.01
    assert abs(float(g[2]) - 0.5) < 1e-6 and abs(float(g[3]) - 0.5) < 1e-6


def test_multi_hop_receptive_field():
    n = 6
    edge_index, weight = _chain(n)
    x = torch.zeros(n, 1)
    x[0, 0] = 1.0
    mdk = MDKPropagation(num_steps=2, weighting="uniform", lambda0=0.0,
                         learn_lambda=False)
    out = mdk(x, edge_index, weight)
    # with K=2 hops the signal reaches node 2 but not node 3
    assert out[2, 0] > 0
    assert out[3, 0] == 0.0
    assert out[4, 0] == 0.0
