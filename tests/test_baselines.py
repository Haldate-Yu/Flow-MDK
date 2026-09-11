"""Tests for the baseline architectures and the model factory."""

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.baselines import GATSurrogate, GCNSurrogate, PersistenceSurrogate
from flow_mdk.config import ModelConfig
from flow_mdk.models.factory import ARCHITECTURES, build_model


def _tiny_model(arch: str):
    cfg = ModelConfig(arch=arch, hidden_dim=16, num_message_passing_layers=2,
                      elevation_feature_idx=0)
    return build_model(cfg, num_static_features=5, num_edge_features=3)


def _inputs(n: int = 8):
    import numpy as np

    from flow_mdk.data.graph_1d import build_1d_graph

    x = np.linspace(0.0, 1000.0, n)
    z = 1e-3 * (x[-1] - x)
    edge_index, edge_attr = build_1d_graph(x, z, np.full(n, 20.0))
    static = torch.randn(n, 5) * 0.1
    dyn = torch.randn(2, n, 2) * 0.1
    dyn[..., 0] = dyn[..., 0].abs()  # depth must be non-negative
    return (
        static,
        dyn,
        torch.from_numpy(edge_index),
        torch.from_numpy(edge_attr.astype(np.float32)),
    )


def test_factory_covers_all_architectures():
    assert set(ARCHITECTURES) == {
        "flow_mdk", "baseline_gcn", "baseline_gat", "baseline_persistence"
    }
    for arch in ARCHITECTURES:
        model = _tiny_model(arch)
        assert model is not None
        assert callable(model.mdk_lambda0)  # shared harness hook


def test_persistence_is_identity():
    static, dyn, edge_index, edge_attr = _inputs()
    model = _tiny_model("baseline_persistence")
    out = model.rollout(static, dyn, edge_index, edge_attr, n_steps=6)
    # persistence predicts the last input frame forever
    assert torch.allclose(out, dyn[-1].expand(6, -1, -1))


def test_gcn_shapes_and_finite():
    static, dyn, edge_index, edge_attr = _inputs()
    model = _tiny_model("baseline_gcn")
    preds = model.rollout(static, dyn, edge_index, edge_attr, n_steps=4)
    assert preds.shape == (4, 8, 2)
    assert torch.isfinite(preds).all()


def test_gat_shapes_and_finite():
    static, dyn, edge_index, edge_attr = _inputs()
    model = _tiny_model("baseline_gat")
    preds = model.rollout(static, dyn, edge_index, edge_attr, n_steps=4)
    assert preds.shape == (4, 8, 2)
    assert torch.isfinite(preds).all()


def test_baseline_batched_forward_matches_single():
    """The factory models must work on the flattened training batches."""
    static, dyn, edge_index, edge_attr = _inputs(4)
    model = _tiny_model("baseline_gcn")
    dyn_flat = dyn.permute(1, 0, 2).reshape(4, 4)
    single = model.forward(static, dyn_flat, edge_index, edge_attr)
    assert single.shape == (4, 2)


def test_unknown_arch_raises():
    with pytest.raises(ValueError):
        build_model(ModelConfig(arch="nope"), 5, 3)
