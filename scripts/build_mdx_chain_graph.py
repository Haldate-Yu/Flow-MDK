#!/usr/bin/env python
"""Assemble the mdx 1D-2D coupled chain as ONE graph (M4 step 1, structural
dry run).

Chain: mdx_upstream (1D, 34 sections) -> mdx_2d (2D, 65,126 cells) ->
mdx_downstream (1D, 29 sections). The three segments currently carry
INDEPENDENT solver truths (their interface boundary conditions were set
independently), so the assembled npz is a PIPELINE EXERCISE only: interface
fluxes are NOT conserved and the result must not be used as training truth.
It validates the coupled-graph path (features, interfaces, time alignment,
dataset/trainer plumbing) ahead of the real coupled solver runs.

Time alignment: common 1800 s grid over 0-15 h (the 2D segment's horizon;
31 frames). upstream is native 1800 s; 2D is subsampled x3 (600 s); the
downstream segment (native 1200 s) takes the NEAREST frame per grid point
(skew up to 600 s, recorded in meta).

Static features are mapped to a shared 4-column layout (plus the graph
kind channel appended by build_coupled_graph):

    [bed_z, width, Manning n, boundary_flag]

- 1D segments: [z, width, Strickler K -> n = 1/K, existing 1/2 end flags]
- 2D segment:  [bottom, area (width proxy), friction n, 1=inflow / 2=outflow]

Interfaces (from mdx_BC.cli geometry): the 17 '4 5 5' nodes sit at the SW
corner = inflow (chain enters here); the 7 '5 4 4' nodes at the NE corner =
outflow. Interface edges are bipartite, both orientations, placeholder
geometry — see flow_mdk/data/graph_coupled.py.

    python scripts/build_mdx_chain_graph.py
    python scripts/train.py --config configs/1d_flow_mdk.yaml --set \
        out_dir=runs/smoke_chain data.root=data/real_cases/coupled_chain \
        model.hidden_dim=32 train.max_epochs=2 ...   # overfit smoke
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flow_mdk.utils.io import Scenario, load_scenario, save_scenario  # noqa: E402
from flow_mdk.data.graph_coupled import (  # noqa: E402
    Interface, SubGraph, build_coupled_graph,
)

TARGET_DT = 1800.0
HORIZON_S = 15.0 * 3600.0  # 2D segment limits the shared window
RUNS = Path("data/real_cases/telemac2d_runs")


def cli_flow_classes(cli_path: Path) -> dict[str, list[int]]:
    """0-based node ids per .cli boundary class ('455' inflow / '544' outflow)."""
    out: dict[str, list[int]] = {}
    for line in cli_path.read_text(errors="replace").splitlines():
        t = line.split()
        if len(t) < 13:
            continue
        try:
            key, nod = f"{t[0]}{t[1]}{t[2]}", int(t[11])
        except ValueError:
            continue
        if key in ("455", "544"):
            out.setdefault(key, []).append(nod - 1)
    return out


def resample(scenario: Scenario, target_dt: float, horizon_s: float) -> tuple[Scenario, dict]:
    """Frames on the common grid; nearest-frame mapping for odd cadences."""
    times = scenario.times
    grid = np.arange(0, horizon_s + 1e-6, target_dt)
    step = float(np.median(np.diff(times)))
    # nearest frame per grid point: exact for native multiples, <=dt/2 skew otherwise
    idx = np.array([int(np.argmin(np.abs(times - g))) for g in grid])
    skew = times[idx] - grid
    info = {"native_dt_s": step, "max_skew_s": float(np.abs(skew).max())}
    edge_flow = None
    if scenario.edge_flow is not None:
        edge_flow = scenario.edge_flow[idx]
    return Scenario(
        name=scenario.name, node_static=scenario.node_static,
        edge_index=scenario.edge_index, edge_attr=scenario.edge_attr,
        dynamic=scenario.dynamic[idx], wet=scenario.wet[idx],
        times=grid, meta=dict(scenario.meta), edge_flow=edge_flow,
    ), info


def common_static_1d(ns: np.ndarray) -> np.ndarray:
    """[z, width, Strickler K, flag] -> [bed_z, width, Manning n, flag]."""
    out = ns.copy()
    out[:, 2] = 1.0 / np.maximum(ns[:, 2], 1e-6)
    return out


def common_static_2d(ns: np.ndarray, inflow: list[int],
                     outflow: list[int]) -> np.ndarray:
    """[area, bottom, friction] -> [bed_z, width(proxy), n, boundary_flag]."""
    out = np.zeros((ns.shape[0], 4), dtype=np.float32)
    out[:, 0] = ns[:, 1]
    out[:, 1] = ns[:, 0]
    out[:, 2] = ns[:, 2]
    out[inflow, 3] = 1.0
    out[outflow, 3] = 2.0
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=Path("data/real_cases/coupled_chain"))
    args = parser.parse_args()

    up = load_scenario(Path("data/real_cases/scenarios_1d/mdx_upstream.npz"))
    mesh = load_scenario(Path("data/real_cases/meshes_2d/mdx_2d.npz"))
    down = load_scenario(Path("data/real_cases/scenarios_1d/mdx_downstream.npz"))

    classes = cli_flow_classes(RUNS / "mdx_2d" / "mdx_BC.cli")
    inflow, outflow = classes["455"], classes["544"]
    assert inflow and outflow, "boundary classes not found in mdx_BC.cli"

    up_al, up_info = resample(up, TARGET_DT, HORIZON_S)
    mesh_al, mesh_info = resample(mesh, TARGET_DT, HORIZON_S)
    down_al, down_info = resample(down, TARGET_DT, HORIZON_S)
    n_frames = mesh_al.dynamic.shape[0]

    subs = [
        SubGraph("mdx_upstream", "1d", common_static_1d(up_al.node_static),
                 up_al.edge_index, up_al.edge_attr),
        SubGraph("mdx_2d", "2d", common_static_2d(mesh_al.node_static, inflow, outflow),
                 mesh_al.edge_index, mesh_al.edge_attr),
        SubGraph("mdx_downstream", "1d", common_static_1d(down_al.node_static),
                 down_al.edge_index, down_al.edge_attr),
    ]
    coupled = build_coupled_graph(
        subs,
        [
            Interface(a=0, nodes_a=[up.node_static.shape[0] - 1], b=1,
                      nodes_b=inflow, kind="chain_to_mesh", length_m=25.0),
            Interface(a=1, nodes_a=outflow, b=2, nodes_b=[0],
                      kind="mesh_to_chain", length_m=25.0),
        ],
        meta={
            "layout": "coupled_1d2d",
            "dynamic_vars": ["h", "Q_or_|q|"],
            "elevation_feature_idx": 0,
            "solver": "dry_run_uncoupled_truths",
        },
    )

    n_up = up.node_static.shape[0]
    n_mesh = mesh.node_static.shape[0]
    dynamic = np.concatenate(
        [up_al.dynamic, mesh_al.dynamic, down_al.dynamic], axis=1).astype(np.float32)
    wet = np.concatenate([up_al.wet, mesh_al.wet, down_al.wet], axis=1).astype(np.uint8)

    scenario = Scenario(
        name="mdx_chain_dryrun",
        node_static=coupled.node_static,
        edge_index=coupled.edge_index,
        edge_attr=coupled.edge_attr,
        dynamic=dynamic,
        wet=wet,
        times=up_al.times,
        meta={
            **coupled.meta,
            "interfaces": coupled.interfaces,
            "node_offsets": coupled.node_offsets,
            "dry_run": {
                "role": "M4 pipeline exercise ONLY — interface fluxes NOT "
                        "conserved (independent truths); not training truth",
                "time_alignment": {"target_dt_s": TARGET_DT,
                                   "horizon_s": HORIZON_S,
                                   "frames": n_frames,
                                   "mdx_upstream": up_info,
                                   "mdx_2d": mesh_info,
                                   "mdx_downstream": down_info},
                "static_layout": ["bed_z", "width", "manning_n", "boundary_flag",
                                  "graph_kind(1d=1/2d=0)"],
                "inflow_nodes": len(inflow), "outflow_nodes": len(outflow),
            },
        },
    )
    args.out.mkdir(parents=True, exist_ok=True)
    out = save_scenario(scenario, args.out / "mdx_chain_dryrun.npz")
    (args.out / "split.json").write_text(
        json.dumps({"train": ["mdx_chain_dryrun"], "val": ["mdx_chain_dryrun"],
                    "test": ["mdx_chain_dryrun"]}, indent=1), encoding="utf-8")

    print(f"[chain] nodes {scenario.num_nodes} "
          f"(1D {n_up} + 2D {n_mesh} + 1D {down.node_static.shape[0]}), "
          f"edges {scenario.edge_index.shape[1]}, frames {n_frames} @ {TARGET_DT:.0f}s")
    print(f"[chain] interfaces: upstream->{len(inflow)} inflow nodes, "
          f"{len(outflow)} outflow nodes->downstream "
          f"({sum(r['num_edges'] for r in coupled.interfaces)} interface edges)")
    print(f"[chain] time skew: upstream {up_info['max_skew_s']:.0f}s, "
          f"2d {mesh_info['max_skew_s']:.0f}s, downstream {down_info['max_skew_s']:.0f}s")
    print(f"[chain] DRY RUN npz -> {out}")


if __name__ == "__main__":
    main()
