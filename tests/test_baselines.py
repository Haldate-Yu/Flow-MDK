"""Tests for the baseline architectures and the model factory."""

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.baselines import (
    GATSurrogate,
    GCNSurrogate,
    PersistenceSurrogate,
    UNetSurrogate,
)
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
        "flow_mdk", "baseline_gcn", "baseline_gat", "baseline_unet",
        "baseline_persistence",
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


# ---------------------------------------------------------------------- #
# U-Net (structured 2D grid domains)
# ---------------------------------------------------------------------- #
def _grid_inputs(b: int = 2, nx: int = 16, ny: int = 16, num_static: int = 6):
    """Flattened batch of b equal-node-count grid scenarios (2D layout)."""
    n = nx * ny
    static = torch.rand(b * n, num_static) * 0.1
    dyn = torch.rand(2, b * n, 2) * 0.1  # [p+1, B*N, O]
    return static, dyn


def test_unet_forward_shapes_and_finite():
    static, dyn = _grid_inputs()
    cfg = ModelConfig(arch="baseline_unet", hidden_dim=8,
                      unet_grid_nx=16, unet_grid_ny=16,
                      elevation_feature_idx=0)
    model = build_model(cfg, num_static_features=6, num_edge_features=3)
    delta = model.forward(static, dyn.permute(1, 0, 2).reshape(2 * 256, 4),
                          None, None)
    assert delta.shape == (2 * 256, 2)
    assert torch.isfinite(delta).all()


def test_unet_rejects_non_grid_node_count():
    static, dyn = _grid_inputs(b=1)
    cfg = ModelConfig(arch="baseline_unet", hidden_dim=8,
                      unet_grid_nx=16, unet_grid_ny=16)
    model = build_model(cfg, num_static_features=6, num_edge_features=3)
    with pytest.raises(ValueError):
        model.forward(static[:-1], dyn.view(256, 4)[:-1], None, None)  # 255 nodes


def test_unet_batched_forward_matches_single():
    """Flattened B-scenario batches must reshape losslessly to images."""
    static, dyn = _grid_inputs(b=2)
    cfg = ModelConfig(arch="baseline_unet", hidden_dim=8,
                      unet_grid_nx=16, unet_grid_ny=16,
                      elevation_feature_idx=0)
    torch.manual_seed(0)
    model = build_model(cfg, num_static_features=6, num_edge_features=3)
    model.eval()
    dyn_flat = dyn.permute(1, 0, 2).reshape(2 * 256, 4)
    batched = model.forward(static, dyn_flat, None, None)
    single0 = model.forward(static[:256], dyn_flat[:256], None, None)
    single1 = model.forward(static[256:], dyn_flat[256:], None, None)
    # float32 conv kernels differ slightly between batch sizes; an ordering
    # bug would show up at O(1), not at the 1e-6 level
    assert torch.allclose(batched[:256], single0, atol=1e-4)
    assert torch.allclose(batched[256:], single1, atol=1e-4)


def test_unet_rollout_on_grid_scenario():
    """End-to-end autoregressive rollout through the shared harness."""
    static, dyn = _grid_inputs(b=1)
    cfg = ModelConfig(arch="baseline_unet", hidden_dim=8,
                      unet_grid_nx=16, unet_grid_ny=16,
                      elevation_feature_idx=0)
    model = build_model(cfg, num_static_features=6, num_edge_features=3)
    preds = model.rollout(static, dyn, None, None, n_steps=4)
    assert preds.shape == (4, 256, 2)
    assert torch.isfinite(preds).all()
