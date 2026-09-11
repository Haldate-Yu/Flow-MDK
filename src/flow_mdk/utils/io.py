"""Scenario storage: one scenario = one .npz file.

Schema (see plan/PLAN.md "数据格式约定"):

==================  ==========================  =====================================
field               shape                       content
==================  ==========================  =====================================
node_static         [N, Fs]           float32   static node features (no time dep.)
edge_index          [2, E]            int64     directed edges (both directions)
edge_attr           [E, Fe]           float32   geometric edge features
dynamic             [T, N, O]         float32   hydraulic variables per frame
wet                 [T, N]            uint8     dry/wet mask per frame
times               [T]               float64   physical time of each frame [s]
edge_flow           [T, E/2]          float32   optional discharge per undirected link
meta                str                         JSON: params, grid, boundary info
==================  ==========================  =====================================

``dynamic`` carries the model variables ordered as declared by the scenario
metadata ``dynamic_vars`` (2D: ``["h", "|q|"]``, 1D: ``["h", "Q"]``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Scenario:
    """In-memory view of one generated scenario."""

    name: str
    node_static: np.ndarray  # [N, Fs]
    edge_index: np.ndarray  # [2, E]
    edge_attr: np.ndarray  # [E, Fe]
    dynamic: np.ndarray  # [T, N, O]
    wet: np.ndarray  # [T, N] uint8
    times: np.ndarray  # [T]
    meta: dict = field(default_factory=dict)
    edge_flow: np.ndarray | None = None  # [T, E/2] optional

    @property
    def num_nodes(self) -> int:
        return self.node_static.shape[0]

    @property
    def num_steps(self) -> int:
        return self.dynamic.shape[0]


def save_scenario(scenario: Scenario, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "node_static": scenario.node_static.astype(np.float32),
        "edge_index": scenario.edge_index.astype(np.int64),
        "edge_attr": scenario.edge_attr.astype(np.float32),
        "dynamic": scenario.dynamic.astype(np.float32),
        "wet": scenario.wet.astype(np.uint8),
        "times": scenario.times.astype(np.float64),
        "meta": np.array(json.dumps(scenario.meta, ensure_ascii=False)),
    }
    if scenario.edge_flow is not None:
        payload["edge_flow"] = scenario.edge_flow.astype(np.float32)
    np.savez_compressed(path, **payload)
    return path


def load_scenario(path: str | Path) -> Scenario:
    path = Path(path)
    data = np.load(path, allow_pickle=False)
    edge_flow = data["edge_flow"] if "edge_flow" in data.files else None
    return Scenario(
        name=path.stem,
        node_static=data["node_static"],
        edge_index=data["edge_index"],
        edge_attr=data["edge_attr"],
        dynamic=data["dynamic"],
        wet=data["wet"],
        times=data["times"],
        meta=json.loads(str(data["meta"])),
        edge_flow=edge_flow,
    )


class ScenarioStore:
    """Lists and loads scenarios from a directory of .npz files."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        if not self.root.exists():
            raise FileNotFoundError(f"Scenario root does not exist: {self.root}")

    def list_names(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.npz"))

    def load(self, name: str) -> Scenario:
        return load_scenario(self.root / f"{name}.npz")
