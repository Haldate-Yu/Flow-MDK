#!/usr/bin/env python
"""Attach Mascaret (full SWE) ground truth to the Part A v2 scenarios (L1).

The unsteady Mascaret kernels refuse to start without an initial water line
(err 349) and keyboard-mode inline lines segfault the v8p4 kernel, so every
scenario runs the official two-stage initialisation of
``examples/mascaret/1_Steady_Kernel``:

1. SARAP steady kernel (constant base-flow inflow, normal-depth downstream
   stage) -> converged gradually-varied backwater profile;
2. the profile is written as ``init.lig`` (permanent/LIDO listing format)
   and the transient run starts from it.

Scenarios whose SARAP stage fails (e.g. critical flow over bed humps) fall
back to a uniform-depth init line. The diffusive-wave reference stored in
the npz is kept in metadata as a cross-check.

    python scripts/run_partA_mascaret.py --root data/scenarios_partA_v2 \
        --split A1_train --limit 2      # pilot
    python scripts/run_partA_mascaret.py --root data/scenarios_partA_v2 \
        --all --workers 3               # full batch (resumable)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flow_mdk.utils.io import Scenario, load_scenario, save_scenario  # noqa: E402
from import_real_cases import parse_opthyca  # noqa: E402
from run_mascaret import (  # noqa: E402
    _fill_init_line,
    _write_init_lig,
    build_project_from_template,
)
from run_real_family import (  # noqa: E402
    _opt_path,
    _prepare_launcher_files,
    _subsample,
    run_mascaret,
)

RUNS_ROOT = Path("data/partA_v2_mascaret_runs")


def _scenario_x(scenario: Scenario) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(scenario.edge_attr[0::2, 0])])


def _steady_init_line(scenario: Scenario, workdir: Path, image: str) -> dict:
    """Stage 1: SARAP steady profile -> init.lig (fill-line fallback).

    Runs in ``workdir/steady`` so it never collides with the transient
    project files at the workdir root. On dry bed-hump sections the steady
    solve is retried with escalating inflow (the event quickly drowns the
    humps anyway; a wetter init line only changes the warm-up minutes).
    """
    x = _scenario_x(scenario)
    z = scenario.node_static[:, 0]
    width = scenario.node_static[:, 1]
    mean_k = float(np.mean(scenario.node_static[:, 2]))
    slope = float(scenario.meta["geometry"]["slope"])
    sp = scenario.meta.get("solver_params") or scenario.meta["geometry"]
    q_base = float(sp.get("q_base", 5.0))

    last_error = ""
    for q_try in (q_base, 3.0 * q_base, 9.0 * q_base):
        try:
            steady_dir = workdir / "steady"
            xcas = build_project_from_template(scenario, steady_dir, steady=True,
                                               steady_q=q_try)
            stem = xcas.stem
            _prepare_launcher_files(steady_dir, stem)
            run_mascaret(steady_dir, xcas.name, image)
            opt = parse_opthyca(_opt_path(steady_dir, stem))
            vi = {v: i for i, v in enumerate(opt["variables"])}
            frame = -1  # last stored step of the steady run
            x_s = opt["abscissa"][frame]
            z_s = opt["data"][frame][:, vi["Z"]]
            if "Q" in vi:
                q_s = opt["data"][frame][:, vi["Q"]]
            else:
                q_s = opt["data"][frame][:, vi["QMIN"]] + opt["data"][frame][:, vi["QMAJ"]]
            order = np.argsort(x_s)
            x_s, z_s, q_s = x_s[order], z_s[order], q_s[order]
            if not (x_s.size >= 2 and np.isfinite(z_s).all() and np.isfinite(q_s).all()):
                raise RuntimeError("SARAP output degenerate")
            if abs(float(np.median(q_s)) - q_try) > max(0.5 * q_try, 1.0):
                raise RuntimeError(
                    f"SARAP discharge drift: median {np.median(q_s):.2f} vs {q_try}"
                )
            _write_init_lig(workdir / "init.lig", x_s, z_s, q_s)
            depth_min = float(np.min(z_s - np.interp(x_s, x, z)))
            return {"init_mode": "sarap_steady", "init_sections": int(x_s.size),
                    "init_depth_min_m": round(depth_min, 3),
                    "init_steady_q": round(q_try, 2)}
        except (RuntimeError, FileNotFoundError) as exc:
            last_error = str(exc)

    z_surf = _fill_init_line(z, width, mean_k, slope, q_base)
    _write_init_lig(workdir / "init.lig", x, z_surf, np.full(x.size, q_base))
    return {"init_mode": "fill_fallback", "init_error": last_error[:200]}


def _collect_truth(scenario: Scenario, runtime: float) -> dict:
    """Map the transient .opt onto the scenario sections + plausibility QC."""
    opt = parse_opthyca(_opt_path(RUNS_ROOT / scenario.name, "mascaret"))
    x = _scenario_x(scenario)
    sec_absc = np.nan_to_num(opt["abscissa"], nan=np.inf).min(axis=0)
    sel = np.asarray([int(np.nanargmin(np.abs(sec_absc - xv))) for xv in x])
    vi = {v: i for i, v in enumerate(opt["variables"])}
    depth = opt["data"][:, sel, vi["Y"]]
    q = opt["data"][:, sel, vi["Q"]]
    idx = _subsample(opt["times"])
    dynamic = np.stack([depth[idx], q[idx]], axis=-1).astype(np.float32)
    times = opt["times"][idx].astype(np.float64)

    # plausibility gate against the diffusive-wave reference still stored
    reference_h_max = float(scenario.dynamic[..., 0].max())
    sp = scenario.meta.get("solver_params") or scenario.meta["geometry"]
    q_peak = float(sp.get("q_peak", float(scenario.dynamic[..., 1].max())))
    h_max = float(dynamic[..., 0].max())
    q_max = float(dynamic[..., 1].max())
    problems = []
    if np.isnan(dynamic).any() or dynamic.shape[0] < 3:
        problems.append("degenerate output")
    if h_max > 3.0 * reference_h_max + 1.0:
        problems.append(
            f"h_max blow-up ({h_max:.1f} m vs reference {reference_h_max:.1f} m)")
    if q_max > 3.0 * q_peak:
        problems.append(f"Q_max blow-up ({q_max:.0f} vs peak {q_peak:.0f})")
    return {"dynamic": dynamic, "times": times, "runtime_s": runtime,
            "h_max": h_max, "q_max": q_max, "problems": problems}


def process_scenario(root: Path, name: str, image: str) -> dict:
    scenario = load_scenario(root / f"{name}.npz")
    reference_solver = scenario.meta.get("solver", "diffusive_wave_reference")
    reference_h_max = float(scenario.dynamic[..., 0].max())
    workdir = RUNS_ROOT / name

    # transient project first: it (re)creates the workdir and seeds the
    # uniform-depth fallback init.lig; the SARAP stage then runs in
    # workdir/steady and may overwrite init.lig with the converged profile
    print(f"[partA] {name}: building transient project ...", flush=True)
    try:
        xcas = build_project_from_template(scenario, workdir, steady=False)
    except RuntimeError as exc:
        return {"scenario": name, "status": "failed",
                "error": f"project build: {exc}"}
    stem = xcas.stem
    _prepare_launcher_files(workdir, stem)

    print(f"[partA] {name}: SARAP steady init ...", flush=True)
    init = _steady_init_line(scenario, workdir, image)
    print(f"[partA] {name}: transient ({init['init_mode']}) ...", flush=True)
    try:
        t0 = time.perf_counter()
        run_mascaret(workdir, xcas.name, image)
        runtime = time.perf_counter() - t0
        run = _collect_truth(scenario, runtime)
    except (RuntimeError, FileNotFoundError) as exc:
        return {"scenario": name, "status": "failed", "init": init,
                "error": str(exc)[:300]}
    if run["problems"]:
        return {"scenario": name, "status": "failed", "init": init,
                "error": "; ".join(run["problems"]),
                "h_max": run["h_max"], "q_max": run["q_max"]}

    scenario.dynamic = run["dynamic"]
    scenario.wet = (run["dynamic"][..., 0] > 1e-3).astype(np.uint8)
    scenario.times = run["times"]
    scenario.meta["solver"] = "mascaret_docker_rerun"
    scenario.meta["runtime_s"] = float(run["runtime_s"])
    scenario.meta["reference_solver"] = reference_solver
    scenario.meta["mascaret_truth"] = {
        **init,
        "frames": int(run["dynamic"].shape[0]),
        "h_max_m": round(run["h_max"], 3),
        "q_max_m3s": round(run["q_max"], 2),
        "h_max_reference_m": round(reference_h_max, 3),
        "project": str(workdir),
    }
    save_scenario(scenario, root / f"{name}.npz")
    print(f"[partA] {name}: {run['dynamic'].shape[0]} frames, "
          f"h_max {run['h_max']:.2f} m, {run['runtime_s']:.0f}s", flush=True)
    return {"scenario": name, "status": "ok", "init": init,
            "frames": int(run["dynamic"].shape[0]), "h_max": run["h_max"],
            "q_max": run["q_max"], "runtime_s": run["runtime_s"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="data/scenarios_partA_v2")
    parser.add_argument("--split", default=None,
                        help="process only names listed under this split.json key")
    parser.add_argument("--all", action="store_true", help="process every npz")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--image", default="flow-mdk-telemac:v8p4r0p1",
                        help="patched-kernel solver image (XAJ/YFIX fixes, "
                             "see datasets/telemac-mascaret-v8p4r0/PATCHES.md)")
    parser.add_argument("--workers", type=int, default=3,
                        help="concurrent docker containers (scenarios are independent)")
    parser.add_argument("--force", action="store_true",
                        help="re-run scenarios that already carry Mascaret truth")
    args = parser.parse_args()

    root = Path(args.root)
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    split = json.loads((root / "split.json").read_text(encoding="utf-8"))
    if args.all:
        names = sorted(p.stem for p in root.glob("*.npz"))
    elif args.split:
        names = split[args.split]
    else:
        parser.error("--split or --all required")

    pending = []
    for name in names:
        scenario = load_scenario(root / f"{name}.npz")
        if (scenario.meta.get("solver") == "mascaret_docker_rerun"
                and not args.force):
            print(f"[partA] {name}: already has Mascaret truth, skip")
            continue
        pending.append(name)
    if args.limit:
        pending = pending[:args.limit]
    print(f"[partA] {len(pending)} scenarios pending", flush=True)

    reports = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(process_scenario, root, name, args.image): name
                   for name in pending}
        for fut in as_completed(futures):
            reports.append(fut.result())

    ok = [r for r in reports if r["status"] == "ok"]
    failed = [r for r in reports if r["status"] != "ok"]
    summary = {
        "processed": len(ok),
        "failed": len(failed),
        "failed_names": [r["scenario"] for r in failed],
        "init_modes": {
            "sarap_steady": sum(1 for r in ok
                                if r["init"]["init_mode"] == "sarap_steady"),
            "fill_fallback": sum(1 for r in ok
                                 if r["init"]["init_mode"] == "fill_fallback"),
        },
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (RUNS_ROOT / "batch_log.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in reports) + "\n",
        encoding="utf-8")
    (RUNS_ROOT / "_batch_report.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    # completion marker consumed by scripts/run_L2_partA_swe.sh
    (RUNS_ROOT / "_batch_done.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[partA] done: {summary['processed']} ok, {summary['failed']} failed "
          f"{summary['failed_names']}; init modes {summary['init_modes']}")


if __name__ == "__main__":
    main()
