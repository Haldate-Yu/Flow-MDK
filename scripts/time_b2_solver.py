#!/usr/bin/env python
"""Solver-runtime baselines for the ->B2 speedup cells (L9).

Times a Mascaret rerun of each B2 real-exam case in the standard docker
image and makes ``runtime_s`` available to the evaluation rollouts — the
denominator of the ->B2 speedup cells (4 of 5 were ``None``; see
``data/real_cases/scenarios_1d/`` metas). Three routes by case:

- ``wqh`` / ``zxh`` / ``mdx_upstream`` — rerun-truth cases: full
  ``run_real_family.py --mode validate`` rerun (bit-exact / previously
  validated); the fresh measured runtime is attached with the rerun truth.
- ``mdx`` — replay-truth case whose template reruns cleanly: TIMING-ONLY —
  scratch workdir, measured wall-clock, results discarded; the historical
  .opt truth stays untouched (the template rerun carries the known 15.4%
  deviation and must never replace the exam truth).
- ``mdx_downstream`` — replay-truth case whose template cannot run in this
  build (L8 non-ASCII section names): npz-geometry rebuild through the
  coupled-chain zxh-recipe machinery, driven by the historical event's
  upstream Q; timing representative (same geometry / horizon / cadence,
  600 s output — slightly conservative), truth untouched.

Run on the SERVER (the rollout inference times the speedups are divided
against were measured there). Truth is never replaced for the replay
cases; attached runtimes carry an explicit ``runtime_source`` label.

Usage (repo root, docker engine up):

    python scripts/time_b2_solver.py --case wqh      # or zxh / mdx_upstream / mdx / mdx_downstream
    python scripts/time_b2_solver.py --all
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flow_mdk.utils.io import load_scenario, save_scenario  # noqa: E402
from run_real_family import (  # noqa: E402
    IMAGE,
    RUNS_ROOT,
    _opt_path,
    _prepare_launcher_files,
    mode_validate,
    run_mascaret,
)

SCENARIOS_1D = Path("data/real_cases/scenarios_1d")
REPO = Path(__file__).resolve().parents[1]


def preflight_portable_sources(cases: list[str]) -> None:
    """Make template paths portable before timing (round-3 lesson: the stored
    ``meta['source']`` values are machine-specific absolute paths from the
    importing machine; the server round failed 4/5 with empty StopIteration
    errors because of exactly this).

    - repo-internal absolute paths are rewritten repo-relative (portable);
    - external templates (schinta mdx / mdxUpStream, not vendored in the repo
      by data policy) fall back to ``data/real_sources/<name>`` — scp the
      project dir there on the target machine before running.
    """
    for case in cases:
        p = SCENARIOS_1D / f"{case}.npz"
        sc = load_scenario(p)
        src = Path(sc.meta["source"])
        if src.exists():
            try:
                rel = src.resolve().relative_to(REPO)
                sc.meta["source"] = str(rel)
                save_scenario(sc, p)
                print(f"[time] {case}: source normalized to repo-relative ({rel})")
            except ValueError:
                pass  # external path that exists on this machine: keep
            continue
        fb = Path("data/real_sources") / src.name
        if fb.exists():
            sc.meta["source"] = str(fb)
            save_scenario(sc, p)
            print(f"[time] {case}: source missing here -> rewrote to {fb}")
        else:
            print(f"[time] {case}: WARNING template not available ({src}); "
                  f"scp it to data/real_sources/{src.name} and rerun")


def _label(route: str) -> dict:
    return {"runtime_source": f"{route} timed {time.strftime('%Y-%m-%d')} ({IMAGE})"}


def attach_runtime(case: str, runtime: float, route: str) -> None:
    sc = load_scenario(SCENARIOS_1D / f"{case}.npz")
    sc.meta["runtime_s"] = float(runtime)
    sc.meta.update(_label(route))
    save_scenario(sc, SCENARIOS_1D / f"{case}.npz")
    print(f"[time] {case}: runtime {runtime:.1f}s ({route}) -> meta; truth untouched")


def validate_route(case: str) -> None:
    """wqh / zxh / mdx_upstream: validated full rerun, runtime attached."""
    report = mode_validate(case, SCENARIOS_1D, IMAGE)
    # mode_validate already attached runtime_s + validation report; stamp the
    # route label on top for the L9 provenance
    sc = load_scenario(SCENARIOS_1D / f"{case}.npz")
    sc.meta.update(_label("template_rerun_validate"))
    save_scenario(sc, SCENARIOS_1D / f"{case}.npz")
    print(f"[time] {case}: runtime {report['runtime_s']:.1f}s "
          f"(validate route, rerun truth refreshed)")


def timing_only_template(case: str) -> None:
    """mdx: scratch template rerun, measured, discarded; truth untouched."""
    sc = load_scenario(SCENARIOS_1D / f"{case}.npz")
    source = Path(sc.meta["source"])
    stem = next(c.stem for c in source.glob("*.xcas") if not c.name.endswith(".ftl"))
    workdir = RUNS_ROOT / f"time_{case}"
    if workdir.exists():
        shutil.rmtree(workdir)
    shutil.copytree(source, workdir, ignore=shutil.ignore_patterns("*.ftl"))
    _prepare_launcher_files(workdir, stem)
    print(f"[time] {case}: scratch template rerun ({stem}.xcas) ...")
    runtime = run_mascaret(workdir, f"{stem}.xcas", IMAGE)
    attach_runtime(case, runtime, "template_rerun_timed_only")


def timing_rebuild_downstream(case: str = "mdx_downstream") -> None:
    """mdx_downstream: npz-geometry rebuild (L8-safe), historical inflow law."""
    from couple_mdx_chain import _build_downstream_project

    sc = load_scenario(SCENARIOS_1D / f"{case}.npz")
    # historical event's upstream Q (section 0), subsampled to a ~600 s law.
    # Cold-start shaping: the historical series sits at flood level at t=0 and
    # a step start makes the vertical discretisation non-converge (~5.8 h in);
    # a 2 h linear ramp-in (floor 0.2x) runs clean. Timing proxy only — the
    # exam truth (historical .opt) is untouched.
    times = sc.times
    step = max(1, int(round(600.0 / float(np.median(np.diff(times))))))
    idx = np.arange(0, len(times), step)
    ramp = np.clip(times[idx] / 7200.0, 0.2, 1.0)
    q_series = np.column_stack([times[idx], sc.dynamic[idx, 0, 1] * ramp])
    duration = float(times[-1])

    proj = RUNS_ROOT / f"time_{case}"
    _build_downstream_project(sc, proj, q_series, duration)
    print(f"[time] {case}: npz-geometry rebuild rerun "
          f"({len(idx)} law points, horizon {duration:.0f}s) ...")
    runtime = run_mascaret(proj, "mascaret.xcas", IMAGE)
    attach_runtime(case, runtime, "npz_rebuild_timed_only")


ROUTES = {
    "wqh": validate_route,
    "zxh": validate_route,
    "mdx_upstream": validate_route,
    "mdx": timing_only_template,
    "mdx_downstream": timing_rebuild_downstream,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=sorted(ROUTES))
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not args.all and not args.case:
        parser.error("need --case or --all")
    cases = sorted(ROUTES) if args.all else [args.case]
    preflight_portable_sources(cases)
    failures = []
    for case in cases:
        try:
            ROUTES[case](case)
        except Exception as exc:  # one failed case must not kill the batch
            failures.append(case)
            print(f"[time] {case}: FAILED ({exc})")
    if failures:
        print(f"[time] done with FAILURES: {failures}")
    print("[time] done — refresh ->B2 evals to fill the speedup cells "
          "(scripts/run_L9_speedup_baselines.sh step 2)")


if __name__ == "__main__":
    main()
