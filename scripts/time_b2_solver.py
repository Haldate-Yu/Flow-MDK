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
import re
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


# routes whose template project (meta['source']) is actually read; the
# mdx_downstream rebuild works from npz geometry alone.
NEEDS_SOURCE = {"wqh", "zxh", "mdx_upstream", "mdx"}


def _source_candidates(raw: str) -> list[Path]:
    """Local candidate locations for a stored ``meta['source']`` template dir.

    The value is written by whichever machine imported the case, so it can be
    repo-relative (POSIX or Windows separators) or machine-absolute (Windows
    drive letters / a foreign POSIX checkout). Round-4 server lesson: such
    strings neither resolve nor even *parse* on Linux — ``Path`` keeps
    ``data\\real_sources\\wqh`` as one component and the ``.name`` of
    ``D:\\...\\telemac1d\\mdx`` is the whole string — so the naive
    ``data/real_sources / src.name`` fallback joined garbage. Normalise
    separators first, then try: the path itself, its repo-relative reading,
    and the staged copies under ``data/real_sources/`` (schinta templates are
    scp'd there by hand; they are not vendored into the repo by data policy).
    """
    norm = raw.replace("\\", "/")
    parts = [p for p in norm.split("/") if p and p != "."]
    if len(parts) > 1 and re.fullmatch(r"[A-Za-z]:", parts[0]):
        parts = parts[1:]
    cands = [Path(norm)]
    if parts and parts[0] == "data":
        cands.append(Path(*parts))
    if "real_sources" in parts:
        tail = parts[parts.index("real_sources") + 1:] or parts[-1:]
        cands.append(Path("data", "real_sources", *tail))          # keeps any parents
        if len(tail) > 1:
            cands.append(Path("data", "real_sources", tail[-1]))   # flat staging
    elif parts:
        cands.append(Path("data", "real_sources", parts[-1]))      # documented flat staging
        if len(parts) >= 2:
            cands.append(Path("data", "real_sources", *parts[-2:]))  # parent-preserving
    seen: set[str] = set()
    out: list[Path] = []
    for c in cands:
        if str(c) not in seen:
            seen.add(str(c))
            out.append(c)
    return out


def preflight_portable_sources(cases: list[str]) -> None:
    """Make template paths portable before timing (round-3 lesson: the stored
    ``meta['source']`` values are machine-specific paths from the importing
    machine; the server round failed 4/5 with empty StopIteration errors
    because of exactly this).

    Repo-internal paths are rewritten repo-relative with forward slashes
    (portable on POSIX and Windows); external templates (schinta mdx /
    mdxUpStream, not vendored in the repo by data policy) fall back to the
    staged copies under ``data/real_sources/`` — scp the project dir there on
    the target machine before running.
    """
    for case in cases:
        if case not in NEEDS_SOURCE:
            continue
        p = SCENARIOS_1D / f"{case}.npz"
        sc = load_scenario(p)
        raw = str(sc.meta["source"])
        for cand in _source_candidates(raw):
            if not cand.exists():
                continue
            try:
                new = cand.resolve().relative_to(REPO).as_posix()
            except ValueError:
                new = cand.as_posix()  # external path that exists here: keep
            if new != raw:
                sc.meta["source"] = new
                save_scenario(sc, p)
                print(f"[time] {case}: source normalized to {new}")
            break
        else:
            print(f"[time] {case}: WARNING template not available ({raw}); "
                  f"scp it to data/real_sources/<name> and rerun")


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
