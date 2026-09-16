#!/usr/bin/env python
"""Build the real-2D exam suite (L12): zero-shot transfer of the E4/E5 2D
models onto the real TELEMAC-2D projects (wqh_2d / mdx_2d, 65k nodes).

The trained 2D models (``runs/MS4_2d_*``) were trained on the synthetic
family (``data/scenarios_2d_family``, 4096-node structured grids). This
script rewrites the real-project mesh npz (``data/real_cases/meshes_2d``)
into the SAME 6-column static feature layout so the checkpoints load and
score without any retraining:

    synthetic: [area, elevation, slope_x, slope_y, manning, breach]
    real:      [area, bottom, friction(Manning n)]  -> mapped by

    area     <- col0 (triangle areas; honest domain gap vs 10000 m2 cells)
    elevation<- col1 shifted to local datum (minus bed min; constant offset
                preserves gradients/dynamics, recorded in meta)
    slope_xy <- per-node least-squares gradient from the dual graph (exact
                neighbour geometry: edge normal = centre direction, edge
                length = centre distance)
    manning  <- col2 (both families store Manning n)
    breach   <- 1 on the flow-imposed boundary nodes parsed from the .cli
                (LIUBOR/LIVBOR in {4,5}; 1-based node ids), else 0

Frame cadence is subsampled to the training dt (1800 s) so the model's
implicit time step matches: 600 s truth -> every 3rd frame (wqh_2d 151->51,
mdx_2d 91->31). Truth values themselves are untouched.

Known zero-shot domain gaps (measured, not adjusted): |q| ~1-8 m/s in the
real channel floods vs <=0.035 m/s in the synthetic family; bed relief
~260 m vs ~3.7 m; triangle areas vs uniform 100 m cells.

    python scripts/build_real_2d_exam.py --out data/real_cases/exams_2d
    python scripts/evaluate.py --config runs/MS4_2d_flow_mdk_s0/config.yaml \
        --checkpoint runs/MS4_2d_flow_mdk_s0/last.pt \
        --data-root data/real_cases/exams_2d --split test --steps 48
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.utils.io import Scenario, load_scenario, save_scenario  # noqa: E402

TARGET_DT_S = 1800.0


def parse_cli_flow_nodes(cli_path: Path) -> list[int]:
    """0-based node ids of flow-imposed boundary nodes from a TELEMAC .cli.

    .cli columns: LIHBOR LIUBOR LIVBOR <prescribed values> ... NOD SEQ (# ...);
    NOD is 1-based (validated: min NOD == 1 over every file seen so far).
    """
    nodes: list[int] = []
    for line in cli_path.read_text(errors="replace").splitlines():
        t = line.split()
        if len(t) < 13:
            continue
        try:
            liu, liv, nod = int(t[1]), int(t[2]), int(t[11])
        except ValueError:
            continue
        if liu in (4, 5) or liv in (4, 5):
            nodes.append(nod - 1)
    return nodes


def node_gradients(node_static: np.ndarray, edge_index: np.ndarray,
                   edge_attr: np.ndarray, elev_col: int = 1) -> np.ndarray:
    """Per-node least-squares gradient [N,2] from the dual graph.

    Both layouts store edge_attr as [normal_x, normal_y, centre_distance]
    with the unit normal pointing source -> target, so neighbour offsets are
    exact (v = n * d). Nodes with degenerate neighbourhoods (collinear /
    single neighbour) fall back to (0, 0) via an L2 ridge.
    """
    z = node_static[:, elev_col].astype(np.float64)
    src, dst = edge_index
    nx, ny, d = (edge_attr[:, 0].astype(np.float64),
                 edge_attr[:, 1].astype(np.float64),
                 edge_attr[:, 2].astype(np.float64))
    dx, dy = nx * d, ny * d
    dz = z[dst] - z[src]

    n = node_static.shape[0]
    sxx = np.bincount(src, weights=dx * dx, minlength=n)
    sxy = np.bincount(src, weights=dx * dy, minlength=n)
    syy = np.bincount(src, weights=dy * dy, minlength=n)
    sxz = np.bincount(src, weights=dx * dz, minlength=n)
    syz = np.bincount(src, weights=dy * dz, minlength=n)

    ridge = 1e-6 * max(sxx.max(), syy.max(), 1.0)
    det = sxx * (syy + ridge) - sxy * sxy
    det = np.where(np.abs(det) < 1e-12, np.nan, det)
    gx = (sxz * (syy + ridge) - syz * sxy) / det
    gy = (syz * sxx - sxz * sxy) / det
    grad = np.stack([np.nan_to_num(gx), np.nan_to_num(gy)], axis=1)
    return grad.astype(np.float32)


def subsample_frames(scenario: Scenario, target_dt: float) -> tuple[Scenario, dict]:
    """Keep frames on the target-dt cadence (constant step assumed)."""
    times = scenario.times
    step = float(np.median(np.diff(times)))
    if abs(step - target_dt) < 1e-6:
        return scenario, {"cadence_s": step, "frames_kept": len(times),
                          "target_dt_s": target_dt}
    stride = int(round(target_dt / step))
    assert stride >= 1 and abs(stride * step - target_dt) < 1e-6, (
        f"cadence {step}s is not an integer divisor of target {target_dt}s")
    keep = np.arange(0, len(times), stride)
    # a trailing partial cycle is dropped: the last kept frame must land on
    # the cadence grid, otherwise the model would be asked for uneven steps
    keep = keep[np.isclose(times[keep] / target_dt, np.round(times[keep] / target_dt))]
    sub = Scenario(
        name=scenario.name,
        node_static=scenario.node_static,
        edge_index=scenario.edge_index,
        edge_attr=scenario.edge_attr,
        dynamic=scenario.dynamic[keep],
        wet=scenario.wet[keep],
        times=times[keep],
        meta=dict(scenario.meta),
    )
    return sub, {"cadence_s": float(step), "stride": stride,
                 "frames_kept": int(len(keep)), "frames_original": int(len(times))}


def build_exam(mesh_npz: Path, cli_path: Path | None, out_path: Path,
               target_dt: float = TARGET_DT_S) -> dict:
    scenario = load_scenario(mesh_npz)
    assert scenario.meta.get("layout") == "2d_mesh", "expected real 2D mesh"
    assert scenario.dynamic.shape[0] > 3, "truth not attached to mesh npz"

    sub, cadence = subsample_frames(scenario, target_dt)

    ns = sub.node_static.astype(np.float32)
    datum_shift = float(ns[:, 1].min())
    slope = node_gradients(ns, sub.edge_index, sub.edge_attr)
    breach = np.zeros(len(ns), dtype=np.float32)
    inflow_nodes = parse_cli_flow_nodes(cli_path) if cli_path else []
    breach[inflow_nodes] = 1.0
    static6 = np.stack(
        [ns[:, 0], ns[:, 1] - datum_shift, slope[:, 0], slope[:, 1],
         ns[:, 2], breach], axis=1).astype(np.float32)

    meta = {
        "layout": "2d_mesh",
        "dynamic_vars": ["h", "|q|"],
        "elevation_feature_idx": 1,
        "solver": "real_exam_zero_shot",
        "source_mesh": str(mesh_npz),
        "exam_provenance": {
            "role": "real-2D exam (L12): zero-shot transfer of MS4_2d models",
            "truth_source": scenario.meta.get("telemac2d_truth", {}).get("results"),
            "datum_shift_m": datum_shift,
            "static_layout": ["area", "elevation_local", "slope_x", "slope_y",
                              "manning_n", "breach"],
            "inflow_nodes": len(inflow_nodes),
            "cli_file": str(cli_path) if cli_path else None,
            "unadjusted_domain_gaps": [
                "|q| real ~1-8 m/s vs synth <=0.035 m/s",
                "bed relief ~260 m vs synth ~3.7 m",
                "triangle areas 2-2699 m2 vs synth uniform 10000 m2",
            ],
            **cadence,
        },
    }
    exam = Scenario(name=mesh_npz.stem, node_static=static6,
                    edge_index=sub.edge_index, edge_attr=sub.edge_attr,
                    dynamic=sub.dynamic, wet=sub.wet, times=sub.times,
                    meta=meta)
    save_scenario(exam, out_path)

    h = sub.dynamic[..., 0]
    return {
        "case": mesh_npz.stem,
        "out": str(out_path),
        "frames": f"{cadence.get('frames_original')}->{cadence.get('frames_kept')} @ {cadence.get('cadence_s'):.0f}s",
        "horizon_h": float(sub.times[-1] / 3600.0),
        "datum_shift_m": datum_shift,
        "inflow_nodes": len(inflow_nodes),
        "h_max": float(h.max()),
        "q_max": float(sub.dynamic[..., 1].max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh-dir", type=Path,
                        default=Path("data/real_cases/meshes_2d"))
    parser.add_argument("--run-dir", type=Path,
                        default=Path("data/real_cases/telemac2d_runs"))
    parser.add_argument("--out", type=Path, default=Path("data/real_cases/exams_2d"))
    parser.add_argument("--target-dt", type=float, default=TARGET_DT_S)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    reports = []
    for mesh in sorted(args.mesh_dir.glob("*.npz")):
        case = mesh.stem  # e.g. wqh_2d
        cli = args.run_dir / case / f"{case.split('_')[0]}_BC.cli"
        if not cli.exists():
            alt = sorted(args.run_dir / case.glob("*.cli"))
            cli = alt[0] if alt else None
        info = build_exam(mesh, cli, args.out / mesh.name, args.target_dt)
        reports.append(info)
        print(f"[exam] {info['case']}: {info['frames']} frames "
              f"(horizon {info['horizon_h']:.1f} h), datum shift "
              f"{info['datum_shift_m']:.2f} m, {info['inflow_nodes']} inflow "
              f"nodes, h_max {info['h_max']:.2f} m, q_max {info['q_max']:.2f} m/s"
              f" -> {info['out']}")

    names = sorted(p.stem for p in args.out.glob("*.npz"))
    split_path = args.out / "split.json"
    split_path.write_text(json.dumps({"test": names}, indent=1), encoding="utf-8")
    print(f"[exam] split.json -> {split_path}: test={names}")


if __name__ == "__main__":
    main()
