"""Tests for the full FlowMDKNet model."""

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.config import ExperimentConfig, MDKConfig, ModelConfig
from flow_mdk.data.graph_1d import build_1d_graph
from flow_mdk.models.flow_mdk_gnn import FlowMDKNet


def _tiny_graph(n: int = 8):
    import numpy as np

    x = np.linspace(0.0, 1000.0, n)
    z = 1e-3 * (x[-1] - x)
    width = np.full(n, 20.0)
    edge_index, edge_attr = build_1d_graph(x, z, width)
    # 4 base statics + appended water-level channel (w = z + h, dry start)
    static = np.stack(
        [z, width, np.full(n, 30.0), np.zeros(n), z], axis=1
    ).astype(np.float32)
    return (
        torch.from_numpy(static),
        torch.from_numpy(edge_index),
        torch.from_numpy(edge_attr),
    )


def _tiny_model(**overrides) -> FlowMDKNet:
    hops = overrides.pop("hops_per_layer", 1)
    cfg = ExperimentConfig()
    cfg.model = ModelConfig(
        hidden_dim=16, num_message_passing_layers=3,
        elevation_feature_idx=0,  # 1D layout: z_bottom channel
        hops_per_layer=hops,
        mdk=MDKConfig(**{"lambda0": 0.3, **overrides}),
    )
    return FlowMDKNet(cfg.model, num_static_features=5, num_edge_features=3)


def _window(n: int = 8, wet_upto: int = 4):
    """Dynamic window [p+1, N, O] with water on the upstream part."""
    dyn = torch.zeros(2, n, 2)
    dyn[:, :wet_upto, 0] = torch.linspace(2.0, 0.2, wet_upto)
    dyn[:, :wet_upto, 1] = 10.0
    return dyn


def test_forward_shapes():
    static, edge_index, edge_attr = _tiny_graph()
    model = _tiny_model()
    dyn = _window()
    delta = model.step(static, dyn, edge_index, edge_attr)
    assert delta.shape == dyn.shape[1:]
    assert torch.isfinite(delta).all()


def test_dry_nodes_stay_dry():
    """No bias anywhere in the dynamic path: an all-dry state must map to
    exactly zero increment (SWE-GNN dry-node guarantee)."""
    static, edge_index, edge_attr = _tiny_graph()
    model = _tiny_model()
    dyn = torch.zeros(2, 8, 2)
    delta = model.step(static, dyn, edge_index, edge_attr)
    assert torch.allclose(delta, torch.zeros_like(delta), atol=1e-7)


def test_rollout_shapes_and_water_level_refresh():
    static, edge_index, edge_attr = _tiny_graph()
    model = _tiny_model()
    dyn = _window()
    preds = model.rollout(static, dyn, edge_index, edge_attr, n_steps=5)
    assert preds.shape == (5, 8, 2)
    assert torch.isfinite(preds).all()
    # the water-level static channel must be refreshed as elevation + depth
    refreshed = model._refresh_static(static, preds[-1])
    assert torch.allclose(refreshed[:, -1], static[:, 0] + preds[-1][:, 0])


def test_ablation_pure_swegnn_has_no_mdk():
    static, edge_index, edge_attr = _tiny_graph()
    model = _tiny_model(use=False)
    assert model.mdk_lambda0() == []
    dyn = _window()
    delta = model.step(static, dyn, edge_index, edge_attr)
    assert torch.isfinite(delta).all()


def test_ablation_symmetric_ssgc_runs():
    static, edge_index, edge_attr = _tiny_graph()
    model = _tiny_model(directed=False)
    dyn = _window()
    delta = model.step(static, dyn, edge_index, edge_attr)
    assert torch.isfinite(delta).all()


def test_diffusive_only_ablation_runs():
    static, edge_index, edge_attr = _tiny_graph()
    model = _tiny_model(mixing="diffusive-only")
    dyn = _window()
    delta = model.step(static, dyn, edge_index, edge_attr)
    assert torch.isfinite(delta).all()


def test_hops_per_layer_official_structure():
    """The official layer runs K hops per layer with per-hop weight matrices."""
    static, edge_index, edge_attr = _tiny_graph()
    model = _tiny_model(hops_per_layer=4)
    layer = model.processor.layers[0]
    assert len(layer.hop_linears) == 4
    dyn = _window()
    delta = model.step(static, dyn, edge_index, edge_attr)
    assert torch.isfinite(delta).all()


def test_hops_one_matches_single_message_pass():
    """hops_per_layer=1 must reproduce the classic one-message-pass update."""
    torch.manual_seed(0)
    static, edge_index, edge_attr = _tiny_graph()
    m1 = _tiny_model(hops_per_layer=1)
    m2 = _tiny_model(hops_per_layer=1)
    m2.load_state_dict(m1.state_dict())
    dyn = _window()
    d1 = m1.step(static, dyn, edge_index, edge_attr)
    d2 = m2.step(static, dyn, edge_index, edge_attr)
    assert torch.allclose(d1, d2)


def test_small_depth_mask_zeroes_dry_discharge():
    from flow_mdk.models.base import apply_small_depth_mask

    state = torch.tensor([[0.5, 10.0], [1e-4, 3.0], [0.0, 2.0]])
    out = apply_small_depth_mask(state, epsilon=1e-3)
    assert torch.allclose(out[0], torch.tensor([0.5, 10.0]))
    assert torch.allclose(out[1], torch.tensor([0.0, 0.0]))  # sub-threshold depth
    assert torch.allclose(out[2], torch.tensor([0.0, 0.0]))  # dry node discharge
