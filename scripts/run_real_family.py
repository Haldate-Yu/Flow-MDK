#!/usr/bin/env python
"""Run real-basin Mascaret projects in the TELEMAC docker image.

Two modes:

- ``validate``: re-run a master project **as imported** and compare the new
  .opt against the stored historical .opt (the 复算校验 admission check of
  plan/PLAN.md). Reports water-level / discharge RMSE and fills the scenario
  metadata with the verification result.
- ``family``: materialise + run every pending scenario of a real-master
  family (see flow_mdk.gen.scenarios_real) and attach the replayed truth to
  each npz.

Examples
--------
    python scripts/run_real_family.py --mode validate --case mdx
    python scripts/run_real_family.py --mode family --family-dir data/real_cases/family_mdx
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flow_mdk.utils.io import Scenario, load_scenario, save_scenario  # noqa: E402
from import_real_cases import parse_opthyca  # noqa: E402

IMAGE = "flow-mdk-telemac:v8p4r0"
RUNS_ROOT = Path("data/real_cases/mascaret_runs")


def run_mascaret(workdir: Path, xcas_name: str, image: str = IMAGE) -> float:
    """Run ``mascaret`` inside the image; returns wall-clock runtime."""
    workdir = workdir.resolve()
    # the image's setenv.sh omits the TELEMAC bin dir from PATH, and its
    # default WORKDIR is the source tree -> cd /work explicitly
    cmd = [
        "docker", "run", "--rm", "-v", f"{workdir}:/work",
        image, "bash", "-lc",
        'export PATH="${HOMETEL}/builds/${USETELCFG}/bin:$PATH" && '
        f"cd /work && mascaret {xcas_name}",
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    runtime = time.perf_counter() - t0
    if proc.returncode != 0:
        (workdir / "docker_stderr.log").write_text(
            proc.stdout[-20000:] + "\n=====\n" + proc.stderr[-20000:],
            encoding="utf-8",
        )
        raise RuntimeError(
            f"mascaret failed in {workdir} (see docker_stderr.log); "
            f"rc={proc.returncode}"
        )
    return runtime


def _prepare_launcher_files(workdir: Path, stem: str) -> None:
    """Files the standalone launcher expects but some templates omit.

    - ``FichierCas.txt``: the launcher always opens it (Java-side launches
      generate it at run time);
    - ``Abaques.txt`` / ``Controle.txt``: opened for writing; projects whose
      templates lack them fail with "Error opening file".
    """
    (workdir / "FichierCas.txt").write_text(f"{stem}.xcas\n", encoding="ascii")
    for name in ("Abaques.txt", "Controle.txt"):
        f = workdir / name
        if not f.exists():
            # Abaques.txt holds the standard Debord lookup tables (universal
            # constants of the Mascaret manual); borrow them from a project
            # that ships the file, otherwise write an empty placeholder.
            std = RUNS_ROOT / "validate_mdx" / "Abaques.txt"
            f.write_text(std.read_text(encoding="ascii") if std.exists() else "",
                         encoding="ascii")


def _opt_path(workdir: Path, stem: str) -> Path:
    # result filename comes from <fichResultat> (default <stem>_ecr.opt)
    text = (workdir / f"{stem}.xcas").read_text(encoding="ISO-8859-1", errors="replace")
    m = re.search(r"<fichResultat>([^<]+)</fichResultat>", text)
    return workdir / (m.group(1).strip() if m else f"{stem}_ecr.opt")


def _map_profiles_to_mesh(opt: dict, x: np.ndarray) -> tuple[np.ndarray, float]:
    """Column selection of the .opt mesh sections nearest to each profile."""
    sec_absc = np.nan_to_num(opt["abscissa"], nan=np.inf).min(axis=0)
    sel = np.asarray([
        int(np.nanargmin(np.abs(sec_absc - xv))) for xv in x
    ])
    mis = float(np.max(np.abs(sec_absc[sel] - x)))
    return sel, mis


def _subsample(times: np.ndarray, target: float = 600.0) -> np.ndarray:
    step = float(np.median(np.diff(times))) if times.size > 1 else 1.0
    period = max(target, step)
    idx = [0]
    for i in range(1, times.size):
        if times[i] - times[idx[-1]] >= period - 1e-6:
            idx.append(i)
    return np.asarray(idx)


def _opt_to_dynamic(opt: dict, sel: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    vi = {v: i for i, v in enumerate(opt["variables"])}
    depth = opt["data"][:, sel, vi["Y"]]
    q = opt["data"][:, sel, vi["Q"]]
    idx = _subsample(opt["times"])
    dynamic = np.stack([depth[idx], q[idx]], axis=-1).astype(np.float32)
    return dynamic, opt["times"][idx]


def _attach_truth(scenario: Scenario, dynamic: np.ndarray, times: np.ndarray,
                  runtime: float, extra: dict) -> Scenario:
    scenario.dynamic = dynamic
    scenario.wet = (dynamic[..., 0] > 1e-3).astype(np.uint8)
    scenario.times = times.astype(np.float64)
    scenario.meta["solver"] = "mascaret_docker_rerun"
    scenario.meta["runtime_s"] = float(runtime)
    scenario.meta.update(extra)
    return scenario


def _scenario_x(node_static: np.ndarray, edge_attr: np.ndarray) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(edge_attr[0::2, 0])])


# --------------------------------------------------------------------- #
def mode_validate(case: str, scenarios_root: Path, image: str) -> dict:
    """复算校验: re-run the master project and compare with the stored .opt."""
    scenario = load_scenario(scenarios_root / f"{case}.npz")
    source = Path(scenario.meta["source"])
    stem = next(
        c.stem for c in source.glob("*.xcas") if not c.name.endswith(".ftl")
    )
    workdir = RUNS_ROOT / f"validate_{case}"
    if workdir.exists():
        shutil.rmtree(workdir)
    shutil.copytree(source, workdir, ignore=shutil.ignore_patterns("*.ftl"))
    _prepare_launcher_files(workdir, stem)

    print(f"[validate] running {case} ({stem}.xcas) in {image} ...")
    runtime = run_mascaret(workdir, f"{stem}.xcas", image)
    opt = parse_opthyca(_opt_path(workdir, stem))
    x = _scenario_x(scenario.node_static, scenario.edge_attr)
    sel, mis = _map_profiles_to_mesh(opt, x)
    dynamic, times = _opt_to_dynamic(opt, sel)

    # compare against the historical truth stored at import time (only for
    # masters that carry replayed .opt truth; pending cases just get filled)
    has_ref = scenario.meta.get("solver") == "mascaret_opt_replay"
    report = {
        "case": case, "runtime_s": runtime,
        "rerun_frames": int(dynamic.shape[0]),
        "abscissa_max_diff_m": mis,
        "depth_max_rerun_m": float(dynamic[..., 0].max()),
    }
    if has_ref:
        ref = scenario.dynamic
        ref_t = scenario.times
        n = min(len(times), len(ref_t))
        z_rmse = float(np.sqrt(np.mean((dynamic[:n, :, 0] - ref[:n, :, 0]) ** 2)))
        q_rmse = float(np.sqrt(np.mean((dynamic[:n, :, 1] - ref[:n, :, 1]) ** 2)))
        report.update({
            "reference_frames": int(ref.shape[0]),
            "depth_rmse_m": z_rmse, "discharge_rmse_m3s": q_rmse,
            "depth_max_reference_m": float(ref[..., 0].max()),
        })
        q_peak = float(ref[..., 1].max())
        passed = z_rmse < 0.5 and q_rmse < max(0.10 * q_peak, 1.0)
    else:
        z_rmse = q_rmse = None
        passed = dynamic.shape[0] > 5  # truth filled, cadence sane
    report["passed"] = bool(passed)

    # keep the rerun as the scenario truth (identical solver, fresh cadence)
    _attach_truth(scenario, dynamic, times, runtime, {
        "validation": report,
    })
    save_scenario(scenario, scenarios_root / f"{case}.npz")

    out = scenarios_root.parent / f"validation_{case}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if has_ref:
        print(
            f"[validate] {case}: depth RMSE {z_rmse:.3f} m, discharge RMSE "
            f"{q_rmse:.1f} m3/s, runtime {runtime:.0f}s -> {'PASS' if passed else 'FAIL'}"
        )
    else:
        print(f"[validate] {case}: truth FILLED ({dynamic.shape[0]} frames, "
              f"runtime {runtime:.0f}s)")
    return report


def mode_family(family_dir: Path, image: str, limit: int | None) -> list[dict]:
    """Materialise + run + attach truth for every pending family scenario."""
    from flow_mdk.gen.scenarios_real import materialise_mascaret_project

    reports = []
    npz_files = sorted(family_dir.glob("*.npz"))
    done = 0
    for npz_path in npz_files:
        if limit and done >= limit:
            break
        scenario = load_scenario(npz_path)
        if scenario.meta.get("solver") != "pending_mascaret_rerun":
            continue
        workdir = RUNS_ROOT / scenario.name
        print(f"[family] {scenario.name}: running mascaret ...")
        try:
            xcas_path = materialise_mascaret_project(scenario, workdir)
            stem = xcas_path.stem
            _prepare_launcher_files(workdir, stem)
            runtime = run_mascaret(workdir, xcas_path.name, image)
            opt = parse_opthyca(_opt_path(workdir, stem))
        except (RuntimeError, FileNotFoundError) as exc:
            # the v8p4 solver occasionally segfaults mid-run on some states;
            # record the failure and keep the batch going
            print(f"[family] {scenario.name}: FAILED ({exc})")
            reports.append({"scenario": scenario.name, "status": "failed",
                            "error": str(exc)[:300]})
            continue
        x = _scenario_x(scenario.node_static, scenario.edge_attr)
        sel, mis = _map_profiles_to_mesh(opt, x)
        dynamic, times = _opt_to_dynamic(opt, sel)
        # physical plausibility gate: the v8p4 solver occasionally produces
        # non-physical blow-ups (steep waves + gate transients) instead of
        # crashing — reject anything far outside the master's observed range
        master = load_scenario(
            Path("data/real_cases/scenarios_1d") / f"{scenario.meta['master']}.npz"
        )
        h_cap = 2.5 * float(master.dynamic[..., 0].max())
        q_cap = 6.0 * float(master.dynamic[..., 1].max()) * float(
            scenario.meta["family"]["q_scale"]
        )
        if (
            np.isnan(dynamic).any()
            or dynamic.shape[0] < 2
            or dynamic[..., 0].max() > h_cap
            or dynamic[..., 1].max() > q_cap
        ):
            print(
                f"[family] {scenario.name}: FAILED (plausibility: "
                f"h_max {dynamic[..., 0].max():.1f} m cap {h_cap:.1f}, "
                f"Q_max {dynamic[..., 1].max():.0f} cap {q_cap:.0f})"
            )
            reports.append({"scenario": scenario.name, "status": "failed",
                            "error": "implausible output"})
            continue
        scenario.dynamic = dynamic
        scenario.wet = (dynamic[..., 0] > 1e-3).astype(np.uint8)
        scenario.times = times.astype(np.float64)
        scenario.meta["solver"] = "mascaret_docker_rerun"
        scenario.meta["runtime_s"] = float(runtime)
        scenario.meta["validation"] = {"abscissa_max_diff_m": mis}
        save_scenario(scenario, npz_path)
        print(
            f"[family] {scenario.name}: {dynamic.shape[0]} frames, "
            f"h_max {dynamic[..., 0].max():.2f} m, {runtime:.0f}s"
        )
        reports.append({"scenario": scenario.name, "status": "ok",
                        "runtime_s": runtime, "frames": int(dynamic.shape[0])})
        done += 1
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("validate", "family"), required=True)
    parser.add_argument("--case", help="validate mode: master case name")
    parser.add_argument("--scenarios-root", default="data/real_cases/scenarios_1d")
    parser.add_argument("--family-dir", help="family mode: directory of npz scenarios")
    parser.add_argument("--image", default=IMAGE)
    parser.add_argument("--limit", type=int, default=None,
                        help="family mode: run at most N pending scenarios")
    args = parser.parse_args()

    if args.mode == "validate":
        mode_validate(args.case, Path(args.scenarios_root), args.image)
    else:
        if not args.family_dir:
            parser.error("--family-dir is required in family mode")
        reports = mode_family(Path(args.family_dir), args.image, args.limit)
        (Path(args.family_dir) / "run_report.json").write_text(
            json.dumps(reports, indent=2), encoding="utf-8"
        )
        print(f"{len(reports)} scenarios computed; report -> {args.family_dir}/run_report.json")


if __name__ == "__main__":
    main()
