"""Windowed training dataset over scenario .npz files.

A training item is a (scenario, t0) pair: the input window is the (p+1)
frames [t0 .. t0+p], the targets are the H frames [t0+p+1 .. t0+p+H].
The water-level static channel is rebuilt for the *last input frame*, so
windows starting mid-simulation are consistent.

Collation flattens graphs the PyG way (node offsets per item), so batches
may mix scenarios of different topology; targets are stacked densely and
therefore require equal node counts within a batch (true inside a scenario
family, which is how sampling is grouped by default).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from flow_mdk.utils.io import Scenario, ScenarioStore

__all__ = ["FlowDataset", "FlowBatch", "collate_flow"]


@dataclass
class FlowBatch:
    node_static: torch.Tensor  # [B*N, Fs]
    dyn_flat: torch.Tensor  # [B*N, (p+1)*O]
    edge_index: torch.Tensor  # [2, B*E]
    edge_attr: torch.Tensor  # [B*E, Fe]
    targets: torch.Tensor  # [B, H, N, O]
    batch_vec: torch.Tensor  # [B*N] scenario index per node
    num_nodes_per_item: int  # N (uniform within a family batch)
    node_static_list: list[torch.Tensor]  # per-item statics (rollout use)
    iface: dict | None = None  # interface bookkeeping for the flux-continuity
    # loss: LOCAL node indices padded across the K active chain->mesh
    # interfaces of the batch's shared topology:
    #   a_idx [K, A], a_mask [K, A]  (1D side nodes carrying Q)
    #   b_idx [K, B], b_mask [K, B]  (2D side nodes carrying |q|)
    #   ell [K]                      (calibrated boundary metres per mesh node)


def window_count(num_steps: int, p: int, horizon: int) -> int:
    """Number of valid window starts for input p+1 frames + H targets."""
    return max(0, num_steps - (p + 1) - horizon + 1)


def extract_interfaces(scenario: Scenario, q_channel: int = 1,
                       wet_rel: float = 0.1, min_wet: int = 3) -> list[dict]:
    """Active chain->mesh interfaces with a calibrated per-node boundary length.

    A one-way Q handoff satisfies ``Q_chain_exit ~= sum_v |q|_v * ell_v`` in
    the truth (the qsl inflow is the chain's exit Q); the mesh boundary
    segment length L is therefore identifiable from the truth as
    ``|B| * median(Q_a / sum_v |q|_v)`` over wet steps, and ``ell = L/|B|``
    assumes a uniform split across the boundary nodes. Interfaces whose mesh
    side carries no flux signal (e.g. stage/ Z boundaries, where nodal |q|
    stays ~0) or without enough wet steps are skipped. Only chain->mesh
    handoffs are extracted: the reverse mesh->chain boundary has no usable
    nodal |q| signal in the v1 truth.
    """
    recs: list[dict] = []
    for iface in scenario.meta.get("interfaces", []):
        if iface.get("kind") != "chain_to_mesh":
            continue
        a = list(iface["nodes_a_global"])
        b = list(iface["nodes_b_global"])
        q_a = scenario.dynamic[:, a, q_channel].sum(axis=1).astype(np.float64)
        q_b = np.abs(scenario.dynamic[:, b, q_channel]).astype(np.float64)
        q_b_sum = q_b.sum(axis=1)
        wet = q_a > max(q_a.max() * wet_rel, 1e-6)
        if wet.sum() < min_wet or q_b_sum[wet].max() <= 0:
            continue
        ell = float(np.median(len(b) * q_a[wet] / q_b_sum[wet])) / len(b)
        if not np.isfinite(ell) or ell <= 0:
            continue
        recs.append({"a": a, "b": b, "ell": ell})
    return recs


class GroupedBatchSampler(torch.utils.data.Sampler):
    """Batches of window indices sharing the same node count.

    Real-basin scenarios have heterogeneous topologies, so a batch must not
    mix node counts (collate_flow requires it). Each epoch regenerates the
    grouping with fresh shuffling inside every node-count group.
    """

    def __init__(self, dataset: FlowDataset, batch_size: int, shuffle: bool = True):
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle
        self._groups: dict[int, list[int]] = {}
        for i in range(len(dataset)):
            self._groups.setdefault(dataset.node_count(i), []).append(i)

    def __len__(self) -> int:
        return sum(
            (len(g) + self.batch_size - 1) // self.batch_size
            for g in self._groups.values()
        )

    def __iter__(self):
        rng = np.random.default_rng()
        batches: list[list[int]] = []
        for group in self._groups.values():
            idxs = list(group)
            if self.shuffle:
                rng.shuffle(idxs)
            for start in range(0, len(idxs), self.batch_size):
                batches.append(idxs[start : start + self.batch_size])
        if self.shuffle:
            rng.shuffle(batches)
        return iter(batches)


class FlowDataset(Dataset):
    """Windows sampled from a fixed list of scenarios.

    Parameters
    ----------
    root / names: scenario store and file stems to use (a split).
    horizon: H target steps (curriculum adjusts it externally).
    num_previous_steps: p.
    elevation_feature_idx: channel of the bed/terrain elevation in the base
        static features; the water level is appended as the last channel.
    """

    def __init__(
        self,
        root: str | Path,
        names: list[str],
        horizon: int,
        num_previous_steps: int = 1,
        elevation_feature_idx: int = 0,
    ) -> None:
        self.store = ScenarioStore(root)
        self.names = list(names)
        self.horizon = horizon
        self.p = num_previous_steps
        self.elev_idx = elevation_feature_idx
        loaded = [self.store.load(n) for n in self.names]
        if not loaded:
            raise ValueError("Empty scenario split")
        # drop scenarios too short for the requested window (e.g. truth
        # pending a solver re-run) so partial datasets still load
        self.scenarios: list[Scenario] = []
        self._index: list[tuple[int, int]] = []
        skipped = []
        for sc in loaded:
            w = window_count(sc.num_steps, self.p, self.horizon)
            if w <= 0:
                skipped.append(sc.name)
                continue
            s = len(self.scenarios)
            self.scenarios.append(sc)
            self._index.extend((s, t0) for t0 in range(w))
        if skipped:
            import logging

            logging.getLogger("flow_mdk.data").warning(
                "skipped scenarios without valid windows: %s", skipped
            )
        if not self._index:
            raise ValueError(
                "No valid windows: sequences shorter than (p+1)+H "
                f"(p={self.p}, H={self.horizon})"
            )
        # node count of every dataset item (heterogeneous real cases make
        # same-size batching necessary; see flow_mdk.data.GroupedBatchSampler)
        self.node_counts = np.asarray(
            [self.scenarios[s].num_nodes for s, _ in self._index]
        )
        # interface bookkeeping for the flux-continuity loss, aligned with
        # self.scenarios (skipped scenarios dropped alongside them)
        self.ifaces = [extract_interfaces(sc) for sc in self.scenarios]

    def node_count(self, idx: int) -> int:
        return int(self.node_counts[idx])

    @property
    def num_static_features(self) -> int:
        return self.scenarios[0].node_static.shape[1] + 1

    def __len__(self) -> int:
        return len(self._index)

    def __getitem__(self, idx: int) -> dict:
        s, t0 = self._index[idx]
        sc = self.scenarios[s]
        p = self.p
        dyn_seq = sc.dynamic[t0 : t0 + p + 1]  # [p+1, N, O]
        targets = sc.dynamic[t0 + p + 1 : t0 + p + 1 + self.horizon]  # [H, N, O]
        last_depth = dyn_seq[-1][:, 0]
        static = np.concatenate(
            [sc.node_static, (sc.node_static[:, self.elev_idx] + last_depth)[:, None]],
            axis=1,
        )
        iface = self.ifaces[s]
        return {
            "name": sc.name,
            "node_static": torch.from_numpy(static.astype(np.float32)),
            "dyn_seq": torch.from_numpy(dyn_seq.astype(np.float32)),
            "edge_index": torch.from_numpy(sc.edge_index),
            "edge_attr": torch.from_numpy(sc.edge_attr),
            "targets": torch.from_numpy(targets.astype(np.float32)),
            "iface_a": [np.asarray(r["a"], dtype=np.int64) for r in iface],
            "iface_b": [np.asarray(r["b"], dtype=np.int64) for r in iface],
            "iface_ell": [r["ell"] for r in iface],
        }


def collate_flow(batch: list[dict]) -> FlowBatch:
    """Flatten graphs with node offsets; targets stacked densely [B, H, N, O]."""
    b = len(batch)
    n = batch[0]["node_static"].size(0)
    for item in batch:
        assert item["node_static"].size(0) == n, "batch requires equal node counts"

    statics, dyns, attrs, offsets, edges = [], [], [], [], []
    node_offset = 0
    for item in batch:
        statics.append(item["node_static"])
        dyns.append(item["dyn_seq"])
        attrs.append(item["edge_attr"])
        e = item["edge_index"] + node_offset
        edges.append(e)
        offsets.append(
            torch.full((n,), len(offsets), dtype=torch.long, device=e.device)
        )
        node_offset += n

    dyn_seq = torch.stack(dyns, dim=0)  # [B, p+1, N, O]
    p1, o = dyn_seq.size(1), dyn_seq.size(3)
    dyn_flat = (
        dyn_seq.permute(0, 2, 1, 3).reshape(b * n, p1 * o).contiguous()
    )

    # interface bookkeeping: shared only when every item carries the exact
    # same active-interface structure (true within a coupled family; mixed
    # splits silently disable the flux-continuity term)
    iface = None
    fa0, fb0, fe0 = batch[0]["iface_a"], batch[0]["iface_b"], batch[0]["iface_ell"]
    if fa0:
        same = all(
            len(it["iface_a"]) == len(fa0)
            and all(np.array_equal(x, y) for x, y in zip(it["iface_a"], fa0))
            and all(np.array_equal(x, y) for x, y in zip(it["iface_b"], fb0))
            and it["iface_ell"] == fe0
            for it in batch
        )
        if same:
            k = len(fa0)
            a_max = max(len(x) for x in fa0)
            b_max = max(len(x) for x in fb0)
            a_idx = torch.zeros((k, a_max), dtype=torch.long)
            a_mask = torch.zeros((k, a_max), dtype=torch.float32)
            b_idx = torch.zeros((k, b_max), dtype=torch.long)
            b_mask = torch.zeros((k, b_max), dtype=torch.float32)
            for i, (ia, ib) in enumerate(zip(fa0, fb0)):
                a_idx[i, : len(ia)] = torch.from_numpy(ia)
                a_mask[i, : len(ia)] = 1.0
                b_idx[i, : len(ib)] = torch.from_numpy(ib)
                b_mask[i, : len(ib)] = 1.0
            iface = {
                "a_idx": a_idx, "a_mask": a_mask,
                "b_idx": b_idx, "b_mask": b_mask,
                "ell": torch.tensor(fe0, dtype=torch.float32),
            }

    return FlowBatch(
        node_static=torch.cat(statics, dim=0),
        dyn_flat=dyn_flat,
        edge_index=torch.cat(edges, dim=1),
        edge_attr=torch.cat(attrs, dim=0),
        targets=torch.stack([item["targets"] for item in batch], dim=0),
        batch_vec=torch.cat(offsets, dim=0),
        num_nodes_per_item=n,
        node_static_list=statics,
        iface=iface,
    )
