"""Tests for the M4 interface flux-continuity loss plumbing (round 5).

Covers: truth-calibrated ell recovery, zero penalty on truth-consistent
states, positive penalty on inconsistent states, per-item local indexing
(collated batches), and a CPU end-to-end training smoke on a tiny coupled
scenario with the term enabled.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def _tiny_coupled_scenario(name: str, q_exit: float = 10.0):
    """3-node 1D chain + 4-node 2D grid glued by one chain->mesh interface.

    Truth satisfies the flux identity exactly: Q at node 2 (chain exit) =
    |q|_3 + |q|_4 with per-node boundary length ell = 1 m.
    """
    from flow_mdk.utils.io import Scenario

    n, t = 7, 6
    node_static = np.zeros((n, 5), dtype=np.float32)
    node_static[:3, 4] = 1.0  # 1D kind flag
    node_static[:3, 0] = 100.0  # bed
    node_static[3:, 0] = 90.0
    # 1D chain edges (both orientations) + 2D ring edges + interface edges
    e = [(0, 1), (1, 0), (1, 2), (2, 1),
         (3, 4), (4, 3), (4, 5), (5, 4), (5, 6), (6, 5), (6, 3), (3, 6),
         (2, 3), (3, 2), (2, 4), (4, 2)]
    edge_index = np.array(e, dtype=np.int64).T
    edge_attr = np.zeros((len(e), 3), dtype=np.float32)
    edge_attr[:12, 0] = 500.0  # 1D arc lengths
    edge_attr[12:, 2] = 25.0  # interface placeholder length in col 2
    dynamic = np.zeros((t, n, 2), dtype=np.float32)
    dynamic[:, :, 0] = 1.0  # everywhere wet
    dynamic[:, 2, 1] = q_exit  # chain exit Q
    dynamic[:, [3, 4], 1] = q_exit / 2  # mesh entrance |q| per node
    times = np.arange(t, dtype=np.float64) * 600.0
    meta = {
        "layout": "coupled_1d2d",
        "dynamic_vars": ["h", "Q_or_|q|"],
        "interfaces": [{
            "kind": "chain_to_mesh", "a": 0, "b": 1,
            "nodes_a_global": [2], "nodes_b_global": [3, 4],
            "num_edges": 4, "length_m": 2.0,
        }],
    }
    return Scenario(name=name, node_static=node_static, edge_index=edge_index,
                    edge_attr=edge_attr, dynamic=dynamic,
                    wet=np.ones((t, n), dtype=np.uint8), times=times, meta=meta)


@pytest.fixture()
def coupled_root(tmp_path):
    from flow_mdk.utils.io import save_scenario

    sc = _tiny_coupled_scenario("coup")
    save_scenario(sc, tmp_path / "coup.npz")
    (tmp_path / "split.json").write_text(
        '{"train": ["coup"], "val": ["coup"], "test": ["coup"]}')
    return tmp_path


class TestExtractInterfaces:
    def test_calibrates_ell_from_truth(self, coupled_root):
        from flow_mdk.data.dataset import extract_interfaces
        from flow_mdk.utils.io import load_scenario

        sc = load_scenario(coupled_root / "coup.npz")
        recs = extract_interfaces(sc)
        assert len(recs) == 1
        # identity holds exactly with ell = 1 m per boundary node
        assert recs[0]["ell"] == pytest.approx(1.0)

    def test_skips_zero_flux_mesh_side(self, tmp_path):
        from flow_mdk.data.dataset import extract_interfaces
        from flow_mdk.utils.io import save_scenario

        sc = _tiny_coupled_scenario("dry")
        sc.dynamic[:, [3, 4], 1] = 0.0  # stage-boundary-like: no |q| signal
        save_scenario(sc, tmp_path / "dry.npz")
        assert extract_interfaces(sc) == []


class TestBatchPlumbing:
    def test_collate_carries_uniform_iface(self, coupled_root):
        from flow_mdk.data.dataset import FlowDataset, collate_flow

        ds = FlowDataset(coupled_root, ["coup"], horizon=2,
                         elevation_feature_idx=0)
        assert ds.ifaces[0] and ds.ifaces[0][0]["ell"] == pytest.approx(1.0)
        batch = collate_flow([ds[i] for i in range(3)])
        assert batch.iface is not None
        assert batch.iface["a_idx"].tolist() == [[2]]
        assert batch.iface["b_idx"].tolist() == [[3, 4]]
        assert batch.iface["ell"].tolist() == [1.0]

    def test_collate_disables_on_mixed_structure(self, coupled_root, tmp_path):
        from flow_mdk.data.dataset import FlowDataset, collate_flow
        from flow_mdk.utils.io import Scenario, save_scenario

        plain = _tiny_coupled_scenario("plain")
        plain.meta = {}  # same graph, no interface bookkeeping
        save_scenario(plain, tmp_path / "plain.npz")
        ds = FlowDataset(tmp_path, ["coup", "plain"], horizon=2,
                         elevation_feature_idx=0)
        n_win = sum(1 for s, _ in ds._index if s == 0)
        batch = collate_flow([ds[0], ds[n_win]])  # coup window + plain window
        assert batch.iface is None


class TestPenalty:
    def _iface(self):
        import torch
        return {
            "a_idx": torch.tensor([[2]]), "a_mask": torch.tensor([[1.0]]),
            "b_idx": torch.tensor([[3, 4]]),
            "b_mask": torch.tensor([[1.0, 1.0]]),
            "ell": torch.tensor([1.0]),
        }

    def test_zero_on_truth_consistent_state(self):
        import torch

        from flow_mdk.train.loss import interface_flux_penalty
        state = torch.zeros(2, 7, 2)
        state[:, 2, 1] = 10.0
        state[:, [3, 4], 1] = 5.0
        assert interface_flux_penalty(state, self._iface()) < 1e-6

    def test_positive_and_item_local(self):
        import pytest
        import torch

        from flow_mdk.train.loss import interface_flux_penalty

        def make_state(q4_item1: float):
            state = torch.zeros(2, 7, 2)
            state[:, 2, 1] = 10.0
            state[:, [3, 4], 1] = 5.0
            state[1, 4, 1] = q4_item1  # break ONLY item 1's mesh side
            return state

        base = interface_flux_penalty(make_state(5.0), self._iface())
        assert base < 1e-6
        # item 1 residual = |10 - 7| / (0.5*(10+7) + 1); item 0 stays exact;
        # the batch mean pins down per-item (local) indexing numerically
        broken = interface_flux_penalty(make_state(2.0), self._iface())
        assert broken == pytest.approx((3.0 / 9.5) / 2, rel=1e-4)

    def test_dry_step_contributes_zero(self):
        import torch

        from flow_mdk.train.loss import interface_flux_penalty
        state = torch.zeros(1, 7, 2)
        assert interface_flux_penalty(state, self._iface()) < 1e-6


def test_prepare_family_root(tmp_path, monkeypatch, capsys):
    """The flattening script: 12 fams -> links + 9/1/2 split, idempotent."""
    import json

    from flow_mdk.utils.io import save_scenario

    chain = tmp_path / "chain"
    fam = tmp_path / "family"
    for i in range(12):
        name = f"mdx_chain_fam{i:03d}"
        d = chain / name
        d.mkdir(parents=True)
        save_scenario(_tiny_coupled_scenario(name), d / f"{name}.npz")

    script = Path(__file__).resolve().parents[1] / "scripts" / \
        "prepare_coupled_family_root.py"
    sys.path.insert(0, str(script.parent))
    import prepare_coupled_family_root as prep
    for _ in range(2):  # second pass exercises the "kept" idempotent path
        monkeypatch.setattr(sys, "argv",
                            ["prep", "--chain-root", str(chain),
                             "--family-root", str(fam)])
        prep.main()
    capsys.readouterr()
    split = json.loads((fam / "split.json").read_text(encoding="utf-8"))
    assert split["test"] == ["mdx_chain_fam000", "mdx_chain_fam011"]
    assert split["val"] == ["mdx_chain_fam010"]
    assert len(split["train"]) == 9
    assert sorted(p.name for p in fam.glob("*.npz")) == \
        [f"mdx_chain_fam{i:03d}.npz" for i in range(12)]


def test_real_chain_calibration():
    """Round-5 gate: the REAL v1 chain npz must yield exactly one active
    chain->mesh interface with a sane calibrated boundary length."""
    from flow_mdk.data.dataset import extract_interfaces
    from flow_mdk.utils.io import load_scenario

    npz = Path(__file__).resolve().parents[1] / "data" / "real_cases" / \
        "coupled_chain" / "mdx_chain_v1.npz"
    if not npz.exists():
        pytest.skip("real chain npz not present on this machine")
    recs = extract_interfaces(load_scenario(npz))
    assert len(recs) == 1
    assert recs[0]["a"] == [33]
    assert len(recs[0]["b"]) == 17
    # truth-implied segment length ~334 m over 17 nodes (~19.7 m/node,
    # cross-validated against the 25 m placeholder geometry)
    assert 10.0 < recs[0]["ell"] < 30.0


def test_end_to_end_cons_smoke(coupled_root, tmp_path):
    """One-epoch CPU train with the term enabled must run and log."""
    import torch

    from flow_mdk.config import MDKConfig, ModelConfig, TrainConfig, ExperimentConfig
    from flow_mdk.data.dataset import FlowDataset
    from flow_mdk.models.flow_mdk_gnn import FlowMDKNet
    from flow_mdk.train.trainer import Trainer

    cfg = ExperimentConfig()
    cfg.model = ModelConfig(
        hidden_dim=16, num_message_passing_layers=2,
        elevation_feature_idx=0,
        mdk=MDKConfig(num_steps=2, lambda0=0.3, learn_lambda=True),
    )
    cfg.train = TrainConfig(max_epochs=2, horizon_max=2, curriculum_steps=1,
                            batch_size=2, early_stop_patience=10,
                            interface_cons_weight=0.1)
    cfg.out_dir = str(tmp_path / "run")

    train_set = FlowDataset(coupled_root, ["coup"], horizon=1,
                            elevation_feature_idx=0)
    val_set = FlowDataset(coupled_root, ["coup"], horizon=2,
                          elevation_feature_idx=0)
    model = FlowMDKNet(cfg.model, train_set.num_static_features,
                       train_set.scenarios[0].edge_attr.shape[1])
    trainer = Trainer(cfg, train_set, val_set, model)
    result = trainer.fit()
    assert result.epochs_run >= 1
    assert np.isfinite(result.best_val_loss)
    assert torch.isfinite(torch.tensor(result.history[-1]["train_loss"]))
