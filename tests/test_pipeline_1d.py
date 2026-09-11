"""End-to-end pipeline smoke test (tiny): generate -> dataset -> train ->
evaluate. Keeps the model and data minimal so it runs on CPU in seconds."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture(scope="module")
def tiny_scenarios(tmp_path_factory):
    from flow_mdk.gen.scenarios_1d import Scenario1DParams, generate_1d_scenario
    from flow_mdk.utils.io import save_scenario

    root = tmp_path_factory.mktemp("scen")
    names = []
    for i in range(4):
        params = Scenario1DParams(
            num_sections=30, length=3000.0, duration=3 * 3600, dt=30.0,
            dt_out=600.0, q_peak=60.0 + 20 * i, seed=100 + i,
        )
        sc = generate_1d_scenario(params, f"t{i}")
        save_scenario(sc, root / f"t{i}.npz")
        names.append(sc.name)
    return root, names


def test_end_to_end(tiny_scenarios, tmp_path):
    root, names = tiny_scenarios
    import torch

    from flow_mdk.config import ExperimentConfig, MDKConfig, ModelConfig, TrainConfig
    from flow_mdk.data.dataset import FlowDataset
    from flow_mdk.eval.rollout import rollout_scenario
    from flow_mdk.models.flow_mdk_gnn import FlowMDKNet
    from flow_mdk.train.trainer import Trainer
    from flow_mdk.utils.io import load_scenario

    cfg = ExperimentConfig()
    cfg.model = ModelConfig(
        hidden_dim=16, num_message_passing_layers=2,
        elevation_feature_idx=0,
        mdk=MDKConfig(num_steps=2, lambda0=0.3, learn_lambda=True),
    )
    cfg.train = TrainConfig(max_epochs=3, horizon_max=2, curriculum_steps=1,
                            batch_size=2, early_stop_patience=10)
    cfg.out_dir = str(tmp_path / "run")

    train_set = FlowDataset(root, names[:2], horizon=1, elevation_feature_idx=0)
    val_set = FlowDataset(root, names[2:3], horizon=2, elevation_feature_idx=0)
    assert len(train_set) > 0 and len(val_set) > 0

    model = FlowMDKNet(cfg.model, train_set.num_static_features,
                       train_set.scenarios[0].edge_attr.shape[1])
    trainer = Trainer(cfg, train_set, val_set, model)
    result = trainer.fit()
    assert result.epochs_run >= 1
    assert result.checkpoint.exists()

    # evaluate a full rollout on the held-out scenario
    scenario = load_scenario(root / f"{names[3]}.npz")
    report = rollout_scenario(model, scenario, n_steps=10, elevation_feature_idx=0)
    assert report.prediction.shape == (10, scenario.num_nodes, 2)
    assert np.isfinite(report.prediction).all()

    # curriculum produces the expected horizon ramp
    horizons = [row["horizon"] for row in result.history]
    assert horizons[0] == 1 and horizons[-1] == min(cfg.train.horizon_max, 3)
