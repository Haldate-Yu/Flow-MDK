#!/usr/bin/env python
"""M4 v2 · parameterized coupled-chain family generator (round 4 prep).

Generalizes the v1 single-chain orchestration (``couple_mdx_chain.py``) to a
family of coupled truths: each scenario perturbs the chain entrance law the
same way the B1 families perturb their masters — an amplitude scale and a
time stretch of mdx_upstream's downstream-end Q(t) — and re-runs the 2D leg
(TELEMAC-2D, ~30 min) plus the downstream reach rebuild (Mascaret, ~25 s).

Per scenario i (workdir ``data/real_cases/coupled_chain/fam{i:03d}/``):

    entrance law  q'(t) = q_scale * Q_up(t / t_stretch)   (v1: scale=1, stretch=1)
    stage 2d      prep qsl/sections/cas + TELEMAC-2D rerun (ncsize MPI)
    stage 1d      FLUX BOUNDARY parse -> exit Q(t) -> downstream rebuild + run
    assemble      ingest coupled 2D truth + downstream .opt -> chain npz
                  (same rules as the v1 dry run: common 1800 s grid, 15 h
                  window, shared 4-col static layout, 48 interface edges)

The v1 simplifications carry over unchanged (one-way Q coupling, 2D exit
stage clamped at Z=280, gateless downstream reach) and are stamped into each
scenario's meta. Batch is serial: each 2D run already uses ncsize MPI ranks.

Idempotent: scenarios with an existing chain npz are skipped, so an
interrupted batch resumes with ``--num`` unchanged (condition draws are
keyed by index, so resuming or extending --num never duplicates or shifts
an earlier scenario's parameters — fixed 2026-09-21).

Server usage (CPU only, docker image required; ~32 min per scenario):

    python scripts/build_coupled_family.py --num 12 --seed 11 2>&1 \
        | tee data/coupled_family_$(date +%m%d).log
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

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from flow_mdk.utils.io import Scenario, load_scenario, save_scenario  # noqa: E402
from couple_mdx_chain import (  # noqa: E402
    CHAIN,
    IMAGE,
    MESH_NPZ,
    NCFILES,
    T2D_SRC,
    UPSTREAM_NPZ,
    _build_downstream_project,
    _cli_class,
    _node_xy,
    _read_exit_flux,
    _read_opt,
)

# entrance-law perturbation ranges: the B1 family protocol (scenarios_real)
Q_SCALE_RANGE = (0.5, 2.0)
TIME_STRETCH_RANGE = (0.8, 1.6)


def _prep_2d(fam_dir: Path, name: str, times: np.ndarray, q_out: np.ndarray,
             q_scale: float, t_stretch: float) -> tuple[Path, Path]:
    """Coupled 2D workdir with the perturbed entrance law; returns (cas, log)."""
    workdir = fam_dir / "mdx_2d_coupled"
    workdir.mkdir(parents=True, exist_ok=True)
    for f in NCFILES:
        shutil.copy2(T2D_SRC / f, workdir / f)

    # perturbed entrance law: amplitude x q_scale, clock x t_stretch. The
    # upstream law spans 0..86400 s, so even the fastest stretch (x0.8)
    # covers the 15 h 2D window; the T=0 guard stays (PLANTE: OUT OF RANGE).
    t_p = times * t_stretch
    q_p = q_out * q_scale
    qsl_lines = [
        "#", f"# COUPLED ENTRANCE ({name}): Q(2) = mdx_upstream Q * {q_scale:.4f},"
             f" clock x {t_stretch:.4f};",
        "# Z(1) kept at the template's constant 280 m (exit stage)",
        "#", "T       Q(2) Z(1)", "s       m3/s m      ",
    ]
    if t_p[0] > 1e-6:
        qsl_lines.append(f"0.0 {q_p[0]:.3f} 280")
    for t, q in zip(t_p, q_p):
        qsl_lines.append(f"{t:.1f} {q:.3f} 280")
    (workdir / "t2d_coupled.qsl").write_text(
        "\n".join(qsl_lines) + "\n\n", encoding="ascii")

    sections = (T2D_SRC / "sections.txt").read_text(encoding="utf-8")
    outflow = _cli_class(T2D_SRC / "mdx_BC.cli", "544")["544"]
    xy = _node_xy(T2D_SRC / "geo.slf")
    ends = [outflow[int(np.argmin(xy[outflow, 1]))],
            outflow[int(np.argmax(xy[outflow, 1]))]]
    # replicate the working v1 artifact byte-for-byte: comment line and the
    # original "N -1" count line kept UNCHANGED, CHAIN_EXIT appended at the
    # end (the solver accepts extra sections beyond the declared count, and
    # the chain's exit Q is parsed from the listing FLUX BOUNDARY blocks
    # anyway — the sections/flowrate output is belt-and-braces)
    sections = sections.rstrip("\n") + f"\nCHAIN_EXIT FLOW\n{ends[0]} {ends[1]}\n"
    (workdir / "sections_coupled.txt").write_text(sections, encoding="ascii")

    cas_text = (T2D_SRC / "mdx.cas").read_text(encoding="utf-8")
    for old, new in [
        ("RESULTS FILE = 'res.slf'", f"RESULTS FILE = 'res_coupled.slf'"),
        ("SECTIONS INPUT FILE = 'sections.txt'",
         "SECTIONS INPUT FILE = 'sections_coupled.txt'"),
        ("SECTIONS OUTPUT FILE = 'flowrate.txt'",
         "SECTIONS OUTPUT FILE = 'flowrate_coupled.txt'"),
        ("LIQUID BOUNDARIES FILE = 't2d_canal.qsl'",
         "LIQUID BOUNDARIES FILE = 't2d_coupled.qsl'"),
        ("TITLE = 'Baxter river tutorial1'", f"TITLE = '{name}'"),
    ]:
        assert old in cas_text, f"cas pattern missing: {old}"
        cas_text = cas_text.replace(old, new)
    (workdir / "mdx_coupled.cas").write_text(cas_text, encoding="ascii")
    return workdir / "mdx_coupled.cas", workdir / "run.log"


def _run_2d(cas: Path, log: Path, ncsize: int) -> float:
    import subprocess

    cmd = ["docker", "run", "--rm", "--shm-size=2g",
           "-v", f"{cas.parent.resolve()}:/work",
           IMAGE, "bash", "-lc",
           "export PATH=\"${HOMETEL}/builds/${USETELCFG}/bin:$PATH\" && "
           "cd /work && "
           "python3 ${HOMETEL}/scripts/python3/telemac2d.py mdx_coupled.cas "
           f"--ncsize={ncsize}"]
    t0 = time.perf_counter()
    with open(log, "w", encoding="utf-8") as fh:
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT)
    runtime = time.perf_counter() - t0
    if proc.returncode != 0 or not (cas.parent / "res_coupled.slf").exists():
        print(f"[2d] FAILED rc={proc.returncode} after {runtime / 60:.0f} min "
              f"(see {log})")
        raise RuntimeError(f"2D run failed for {cas.parent}")
    return runtime


def _stage_1d(fam_dir: Path, name: str) -> tuple[np.ndarray, float]:
    """Exit-flux parse -> downstream rebuild + Mascaret run; returns (q_series, runtime)."""
    flow = _read_exit_flux(fam_dir / "mdx_2d_coupled" / "run.log")
    grid = np.arange(0.0, 54000.0 + 1e-6, 600.0)
    q = np.interp(grid, flow[:, 0], flow[:, 1])
    tail = np.arange(54000.0 + 600.0, 86400.0 + 1e-6, 600.0)
    q_series = np.column_stack([
        np.concatenate([grid, tail]),
        np.concatenate([q, np.full(len(tail), q[-1])]),
    ])

    proj = fam_dir / "mdx_downstream_coupled"
    down = load_scenario(REPO / "data/real_cases/scenarios_1d/mdx_downstream.npz")
    _build_downstream_project(down, proj, q_series)
    from run_real_family import run_mascaret

    runtime = run_mascaret(proj, "mascaret.xcas", image=IMAGE)
    print(f"[1d] {name}: downstream rebuilt+run in {runtime:.0f}s "
          f"(exit Q {q.min():.0f}..{q.max():.0f} m3/s)")
    return q_series, runtime


def _assemble(fam_dir: Path, name: str, q_scale: float, t_stretch: float,
              up: Scenario) -> Scenario:
    """v1 assemble rules, parameterized paths (chain npz per scenario)."""
    from build_mdx_chain_graph import (HORIZON_S, TARGET_DT, common_static_1d,
                                       common_static_2d, resample)
    from flow_mdk.data.graph_coupled import Interface, SubGraph, build_coupled_graph
    from ingest_telemac2d_truth import ingest_results

    mesh_coupled_path = fam_dir / "mdx_2d_coupled.npz"
    shutil.copy2(MESH_NPZ, mesh_coupled_path)
    qc2d = ingest_results(fam_dir / "mdx_2d_coupled" / "res_coupled.slf",
                          mesh_coupled_path,
                          listing=fam_dir / "mdx_2d_coupled" / "run.log",
                          solver_tag=f"coupled_chain_{name}", force=True)
    if qc2d.get("problems"):
        print(f"[asm] {name}: 2D QC PROBLEMS: {qc2d['problems']}")
    mesh = load_scenario(mesh_coupled_path)
    print(f"[asm] {name}: 2D truth {qc2d['frames']} frames, "
          f"h_max {qc2d['h_max_m']:.2f} m")

    down = load_scenario(REPO / "data/real_cases/scenarios_1d/mdx_downstream.npz")
    opt = _read_opt(fam_dir / "mdx_downstream_coupled" / "mascaret_ecr.opt")
    vi = {v.strip().upper(): i for i, v in enumerate(opt["variables"])}
    y_idx = next(i for k, i in vi.items() if k == "Y")
    q_idx = next(i for k, i in vi.items() if k == "Q")
    x_profile = np.concatenate([[0.0], np.cumsum(down.edge_attr[0::2, 0])])
    sec_absc = np.nan_to_num(opt["abscissa"], nan=np.inf).min(axis=0)
    sec_absc = np.where(np.isfinite(sec_absc), sec_absc, np.nan)
    sel = np.array([int(np.nanargmin(np.where(np.isfinite(sec_absc),
                                              np.abs(sec_absc - x), np.inf)))
                    for x in x_profile])
    depth = opt["data"][:, :, y_idx][:, sel]
    q = opt["data"][:, :, q_idx][:, sel]
    down_coupled = Scenario(
        name=f"mdx_downstream_{name}", node_static=down.node_static,
        edge_index=down.edge_index, edge_attr=down.edge_attr,
        dynamic=np.stack([depth, q], axis=-1).astype(np.float32),
        wet=(depth > 1e-3).astype(np.uint8), times=opt["times"],
        meta={**down.meta, "solver": f"coupled_chain_{name}"})

    classes = _cli_class(T2D_SRC / "mdx_BC.cli", ("455", "544"))
    inflow, outflow = classes["455"], classes["544"]
    up_al, up_info = resample(up, TARGET_DT, HORIZON_S)
    mesh_al, mesh_info = resample(mesh, TARGET_DT, HORIZON_S)
    down_al, down_info = resample(down_coupled, TARGET_DT, HORIZON_S)

    subs = [
        SubGraph("mdx_upstream", "1d", common_static_1d(up_al.node_static),
                 up_al.edge_index, up_al.edge_attr),
        SubGraph("mdx_2d_coupled", "2d",
                 common_static_2d(mesh_al.node_static, inflow, outflow),
                 mesh_al.edge_index, mesh_al.edge_attr),
        SubGraph(f"mdx_downstream_{name}", "1d",
                 common_static_1d(down_al.node_static),
                 down_al.edge_index, down_al.edge_attr),
    ]
    coupled = build_coupled_graph(
        subs,
        [Interface(a=0, nodes_a=[up.node_static.shape[0] - 1], b=1,
                   nodes_b=inflow, kind="chain_to_mesh", length_m=25.0),
         Interface(a=1, nodes_a=outflow, b=2, nodes_b=[0],
                   kind="mesh_to_chain", length_m=25.0)],
        meta={"layout": "coupled_1d2d", "dynamic_vars": ["h", "Q_or_|q|"],
              "elevation_feature_idx": 0,
              "solver": f"coupled_chain_{name}"},
    )
    scenario = Scenario(
        name=name,
        node_static=coupled.node_static,
        edge_index=coupled.edge_index,
        edge_attr=coupled.edge_attr,
        dynamic=np.concatenate(
            [up_al.dynamic, mesh_al.dynamic, down_al.dynamic], axis=1),
        wet=np.concatenate([up_al.wet, mesh_al.wet, down_al.wet], axis=1),
        times=up_al.times,
        meta={**coupled.meta, "interfaces": coupled.interfaces,
              "node_offsets": coupled.node_offsets,
              "family": {"q_scale": float(q_scale),
                         "time_stretch": float(t_stretch)},
              "coupling": {
                  "scheme": "one-way Q chain (v1): upstream Q -> 2D entrance "
                            "(Z exit clamped 280) -> exit Q/Z -> downstream loi",
                  "no_stage_feedback": True,
                  "gateless_downstream": True,
                  "2d_ingest_qc": qc2d,
                  "time_alignment": {"mdx_upstream": up_info, "mdx_2d": mesh_info,
                                     "mdx_downstream": down_info},
              }},
    )
    return scenario


def _draw_conditions(seed: int, num: int) -> list:
    """Per-index (q_scale, t_stretch) draws: index 0 is the v1 parity draw
    (1.0, 1.0, consumes no RNG), then two uniforms per index in order.

    Drawn up front and keyed by index so that the value for scenario i never
    depends on which scenarios already exist on disk (see module note above).
    """
    rng = np.random.default_rng(seed)
    out = [(1.0, 1.0)]
    for _ in range(1, num):
        out.append((float(rng.uniform(*Q_SCALE_RANGE)),
                    float(rng.uniform(*TIME_STRETCH_RANGE))))
    return out


def _upsert(report: list, entry: dict) -> list:
    """Replace-or-append by scenario name; keeps the family record sorted and
    intact across extension runs."""
    kept = [r for r in report if r.get("name") != entry.get("name")]
    kept.append(entry)
    return sorted(kept, key=lambda r: r.get("name", ""))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num", type=int, default=12,
                        help="family size (including the v1 baseline scenario)")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--ncsize", type=int, default=4)
    parser.add_argument("--prep-only", action="store_true",
                        help="write workdirs without running solvers (dry check)")
    args = parser.parse_args()

    up = load_scenario(UPSTREAM_NPZ)
    times = up.times
    q_out = up.dynamic[:, -1, 1]  # Q at the downstream end section
    draws = _draw_conditions(args.seed, args.num)

    report_path = CHAIN / "coupled_family_report.json"
    report: list = []
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — corrupt record must not block the run
            report = []
    batch = []
    for i in range(args.num):
        name = f"mdx_chain_fam{i:03d}"
        fam_dir = CHAIN / name
        out_npz = fam_dir / f"{name}.npz"
        # index-keyed: scenario i's conditions never depend on what exists on disk
        q_scale, t_stretch = draws[i]
        if out_npz.exists():
            print(f"[fam] {name}: npz exists, skip "
                  f"(q_scale={q_scale:.3f} t_stretch={t_stretch:.3f})")
            continue
        batch.append(name)
        print(f"=== [{name}] q_scale={q_scale:.3f} t_stretch={t_stretch:.3f} ===")
        t0 = time.perf_counter()
        try:
            cas, log = _prep_2d(fam_dir, name, times, q_out, q_scale, t_stretch)
            if args.prep_only:
                print(f"[fam] {name}: prep only, skipping solvers")
                continue
            t2d_s = _run_2d(cas, log, args.ncsize)
            _stage_1d(fam_dir, name)
            scenario = _assemble(fam_dir, name, q_scale, t_stretch, up)
            save_scenario(scenario, out_npz)
            mins = (time.perf_counter() - t0) / 60
            print(f"[fam] {name}: DONE in {mins:.1f} min "
                  f"({scenario.num_nodes} nodes, "
                  f"{scenario.dynamic.shape[0]} frames) -> {out_npz}")
            report = _upsert(report, {"name": name, "q_scale": q_scale,
                                      "time_stretch": t_stretch,
                                      "t2d_min": t2d_s / 60,
                                      "total_min": mins, "status": "ok"})
        except Exception as exc:
            mins = (time.perf_counter() - t0) / 60
            print(f"[fam] {name}: FAILED after {mins:.1f} min ({exc})")
            report = _upsert(report, {"name": name, "q_scale": q_scale,
                                      "time_stretch": t_stretch,
                                      "status": f"failed: {exc}"})
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    ok = sum(1 for r in report if r.get("status") == "ok")
    print(f"[fam] batch done: this batch {len(batch)} scenario(s) attempted; "
          f"record {ok}/{len(report)} ok -> {report_path}")


if __name__ == "__main__":
    main()
