#!/usr/bin/env python
"""M4 stage-1 coupled truth generation for the mdx chain (file-exchange,
one-way Q coupling — v1).

Chain: mdx_upstream (1D, existing truth) -> mdx_2d (TELEMAC-2D, rerun) ->
mdx_downstream (Mascaret, rerun). v8p4 has no native 1D-2D coupling, so the
chain is driven by boundary-file exchange at the model cadence:

- mdx_upstream's downstream Q(t) (existing truth npz) replaces the template's
  synthetic entrance hydrograph in the 2D run's LIQUID BOUNDARIES file
  (boundary 2 = the 17-node SW entrance; stage at the exit boundary 1 stays
  clamped at Z=280 as in the template);
- the rerun gets an extra control section (CHAIN_EXIT) spanning the 7-node NE
  outflow, so flowrate.txt yields the exit Q(t) solver-natively;
- the exit Q(t) + exit stage Z(t) (mean over the exit nodes) become the
  downstream reach's upstream Q-Z loi; the reach is then rerun from its
  complete template project (gate schedule kept).

Documented v1 simplifications (stage feedback is future work): no stage
feedback from the 2D onto the upstream reach's downstream boundary, and the
2D exit stage is not influenced by the downstream reach (template Z=280).
mdx_upstream therefore needs NO rerun: under one-way Q coupling its solution
is unchanged.

Stages
------
    python scripts/couple_mdx_chain.py --stage 2d      # prep + run 2D (hours)
    python scripts/couple_mdx_chain.py --stage 1d      # prep + run 1D (minutes)
    python scripts/couple_mdx_chain.py --stage assemble  # coupled npz + QC
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

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from flow_mdk.utils.io import load_scenario, save_scenario  # noqa: E402

CHAIN = Path("data/real_cases/coupled_chain")
T2D_SRC = Path("data/real_cases/telemac2d_runs/mdx_2d")
MESH_NPZ = Path("data/real_cases/meshes_2d/mdx_2d.npz")
UPSTREAM_NPZ = Path("data/real_cases/scenarios_1d/mdx_upstream.npz")
IMAGE = "flow-mdk-telemac:v8p4r0p1"
NCFILES = ["geo.slf", "mdx_BC.cli", "old.slf", "source_discharge.qsl",
           "source_regions.qsl"]


# ---------------------------------------------------------------- stage 2d #
def stage_2d(args: argparse.Namespace) -> None:
    workdir = CHAIN / "mdx_2d_coupled"
    cas = workdir / "mdx_coupled.cas"
    if cas.exists() and not args.force:
        print(f"[2d] {cas} exists; use --force to rebuild (run res files kept)")
    else:
        workdir.mkdir(parents=True, exist_ok=True)
        for f in NCFILES:
            shutil.copy2(T2D_SRC / f, workdir / f)

        upstream = load_scenario(UPSTREAM_NPZ)
        times = upstream.times
        q_out = upstream.dynamic[:, -1, 1]  # Q at the downstream end section
        qsl_lines = [
            "#", "# COUPLED ENTRANCE: Q(2) = mdx_upstream downstream-end Q;",
            "# Z(1) kept at the template's constant 280 m (exit stage)",
            "#", "T       Q(2) Z(1)", "s       m3/s m      ",
        ]
        if times[0] > 1e-6:
            # the solver requires coverage from T=0 (PLANTE: OUT OF RANGE)
            qsl_lines.append(f"0.0 {q_out[0]:.3f} 280")
        for t, q in zip(times, q_out):
            qsl_lines.append(f"{t:.1f} {q:.3f} 280")
        # compilers require an EMPTY line at the end of the file (PLANTE hint)
        (workdir / "t2d_coupled.qsl").write_text(
            "\n".join(qsl_lines) + "\n\n", encoding="ascii")

        sections = (T2D_SRC / "sections.txt").read_text(encoding="utf-8")
        outflow = _cli_class(T2D_SRC / "mdx_BC.cli", "544")["544"]
        xy = _node_xy(T2D_SRC / "geo.slf")
        ends = [outflow[int(np.argmin(xy[outflow, 1]))],
                outflow[int(np.argmax(xy[outflow, 1]))]]
        # the template's sections.txt has NO trailing newline; the header's
        # first integer is the SECTION COUNT -> bump it for CHAIN_EXIT
        sections = sections.rstrip("\n") + f"\nCHAIN_EXIT FLOW\n{ends[0]} {ends[1]}\n"
        n_sec = int(sections.splitlines()[0].split()[0])
        sections = sections.replace(sections.splitlines()[0],
                                    f"{n_sec + 1} -1", 1)
        (workdir / "sections_coupled.txt").write_text(sections, encoding="ascii")

        cas_text = (T2D_SRC / "mdx.cas").read_text(encoding="utf-8")
        for old, new in [
            ("RESULTS FILE = 'res.slf'", "RESULTS FILE = 'res_coupled.slf'"),
            ("SECTIONS INPUT FILE = 'sections.txt'",
             "SECTIONS INPUT FILE = 'sections_coupled.txt'"),
            ("SECTIONS OUTPUT FILE = 'flowrate.txt'",
             "SECTIONS OUTPUT FILE = 'flowrate_coupled.txt'"),
            ("LIQUID BOUNDARIES FILE = 't2d_canal.qsl'",
             "LIQUID BOUNDARIES FILE = 't2d_coupled.qsl'"),
            ("TITLE = 'Baxter river tutorial1'",
             "TITLE = 'mdx_2d_coupled_chain_v1'"),
        ]:
            assert old in cas_text, f"cas pattern missing: {old}"
            cas_text = cas_text.replace(old, new)
        cas.write_text(cas_text, encoding="ascii")
        print(f"[2d] coupled workdir ready -> {workdir}")
        print(f"[2d] entrance Q: {q_out.min():.0f}..{q_out.max():.0f} m3/s "
              f"({len(times)} pts @ 1800s); exit section nodes {ends}")

    log = workdir / "run.log"
    if (workdir / "res_coupled.slf").exists() and not args.force:
        print("[2d] res_coupled.slf exists; skipping run")
        return
    print(f"[2d] launching TELEMAC-2D in {IMAGE} (ncsize={args.ncsize}); "
          f"log -> {log}")
    cmd = ["docker", "run", "--rm", "--shm-size=2g",
           "-v", f"{workdir.resolve()}:/work",
           IMAGE, "bash", "-lc",
           "export PATH=\"${HOMETEL}/builds/${USETELCFG}/bin:$PATH\" && "
           "cd /work && "
           "python3 ${HOMETEL}/scripts/python3/telemac2d.py mdx_coupled.cas "
           f"--ncsize={args.ncsize}"]
    t0 = time.perf_counter()
    with open(log, "w", encoding="utf-8") as fh:
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT)
    runtime = time.perf_counter() - t0
    if proc.returncode != 0 or not (workdir / "res_coupled.slf").exists():
        print(f"[2d] FAILED rc={proc.returncode} after {runtime/60:.0f} min "
              f"(see {log})")
        raise SystemExit(1)
    print(f"[2d] done in {runtime/60:.1f} min")


# ---------------------------------------------------------------- stage 1d #
def _read_exit_flux(listing: Path) -> np.ndarray:
    """(t, Q_exit) from the mass-balance blocks of the solver listing.

    The exit is liquid boundary 1 (NE, stage-clamped); its flux is printed
    solver-natively at every listing printout (600 s here), positive entering.
    """
    t, q, pending = [], [], None
    for line in listing.read_text(errors="replace").splitlines():
        m = re.search(r"FLUX BOUNDARY\s+1:\s*([-0-9.E+]+)", line)
        if m:
            pending = float(m.group(1))
            continue
        m = re.search(r"AT T =\s*([0-9.E+-]+)\s*S", line)
        if m and pending is not None:
            t.append(float(m.group(1)))
            q.append(-pending)  # exiting -> positive discharge downstream
            pending = None
    if not t:
        raise SystemExit(f"no FLUX BOUNDARY 1 blocks in {listing}")
    return np.column_stack([t, q])


def _build_downstream_project(scenario, proj: Path, q_series: np.ndarray,
                              duration: float = 86400.0) -> None:
    """Coupled downstream reach built from the validated zxh xcas recipe.

    The mdxDownStream template cannot run in our docker build (L8: its geo
    carries non-ASCII section names and the kernel aborts -- historically a
    segfault, with the strict-domain error 25 as one of its faces), so the
    reach is rebuilt from the npz geometry with exactly the machinery that
    produced the 117 real-master family scenarios: zxh xcas template patched
    to our geometry, upstream Q hydrogramme (the coupled 2D exit) + normal-
    depth tarage outflow, file-based initial line. The template's gate
    schedule (GATE.txt) is NOT carried over (the zxh xcas has no gate block)
    -- recorded v1 simplification.
    """
    from run_mascaret import (_fill_init_line, _normal_depth, _write_init_lig,
                              write_geometry, write_hydrograph, write_tarage)
    template_dir = REPO / "data/real_sources/zxh"
    if proj.exists():
        shutil.rmtree(proj)
    shutil.copytree(template_dir, proj,
                    ignore=shutil.ignore_patterns("*.ftl", "*.opt", "*.lis",
                                                  "*.rep"))
    for stale in proj.glob("zx*.loi"):
        stale.unlink()

    static = scenario.node_static
    z, width, strickler = static[:, 0], static[:, 1], static[:, 2]
    dx = scenario.edge_attr[0::2, 0]
    x = np.concatenate([[0.0], np.cumsum(dx)])
    n = len(x)
    mean_k = float(np.mean(strickler))
    slope = float((z[0] - z[-1]) / x[-1])
    dt = 10.0

    write_geometry(proj / "geometrie", x, z, width)
    write_hydrograph(proj / "hydrogramme.loi", q_series[:, 0], q_series[:, 1])
    q_ref = float(np.max(q_series[:, 1]))
    h_peak = _normal_depth(3.0 * q_ref, float(width[-1]), mean_k, slope)
    h_rating = np.linspace(0.01, h_peak + 2.0, 60)
    z_rating = z[-1] + h_rating
    q_rating = strickler[-1] * width[-1] * h_rating ** (5.0 / 3.0) * slope ** 0.5
    write_tarage(proj / "tarage.loi",
                 np.concatenate([[z[-1] - 2.0], z_rating]),
                 np.concatenate([[0.0], q_rating]))
    z_surf = _fill_init_line(z, width, mean_k, slope, float(q_series[0, 1]))
    _write_init_lig(proj / "init.lig", x, z_surf, np.full(n, float(q_series[0, 1])))

    text = (template_dir / "zx.xcas").read_text(encoding="ISO-8859-1",
                                                errors="replace")

    def sub(pattern: str, repl: str, count: int = 1) -> None:
        nonlocal text
        text, k = re.subn(pattern, repl, text, count=count, flags=re.S)
        if k != count:
            raise RuntimeError(f"template patch failed: {pattern[:50]}")

    sub(r"<fichMotsCles>[^<]*</fichMotsCles>", "<fichMotsCles>mascaret.xcas</fichMotsCles>")
    sub(r"<titreCalcul>[^<]*</titreCalcul>", "<titreCalcul>mdx chain coupled downstream v1</titreCalcul>")
    sub(r"<fichier>zx\.geo</fichier>", "<fichier>geometrie</fichier>")
    sub(r"<abscFin>[^<]*</abscFin>", f"<abscFin>{x[-1]:.3f}</abscFin>")
    sub(r"<critereArret>[^<]*</critereArret>", "<critereArret>1</critereArret>")
    sub(r"<pasTempsVar>[^<]*</pasTempsVar>", "<pasTempsVar>true</pasTempsVar>")
    sub(r"<pasTemps>[^<]*</pasTemps>", f"<pasTemps>{dt}</pasTemps>")
    sub(r"<tempsMax>[^<]*</tempsMax>", f"<tempsMax>{duration}</tempsMax>")
    sub(r"<nbPasTemps>[^<]*</nbPasTemps>", f"<nbPasTemps>{int(duration / dt)}</nbPasTemps>")
    sub(r"<numDerProf>[^<]*</numDerProf>", f"<numDerProf>{n}</numDerProf>")
    sub(r"<numDerProfPlage>[^<]*</numDerProfPlage>", f"<numDerProfPlage>{n}</numDerProfPlage>")
    sub(r"<pasEspacePlage>[^<]*</pasEspacePlage>",
        f"<pasEspacePlage>{x[-1] / (n - 1):.3f}</pasEspacePlage>")
    sub(r"<coefLitMin>[^<]*</coefLitMin>", f"<coefLitMin>{mean_k:.3f}</coefLitMin>")
    sub(r"<coefLitMaj>[^<]*</coefLitMaj>", f"<coefLitMaj>{mean_k:.3f}</coefLitMaj>")
    sub(r"<typeCond>[^<]*</typeCond>", "<typeCond>1 4</typeCond>")
    sub(r"<numLoi>[^<]*</numLoi>", "<numLoi>1 2</numLoi>")
    sub(r"<absDebZone>[^<]*</absDebZone>", "<absDebZone>0.000</absDebZone>")
    sub(r"<absFinZone>[^<]*</absFinZone>", f"<absFinZone>{x[-1]:.3f}</absFinZone>")
    sub(r"<parametresApportDeversoirs>.*?</parametresApportDeversoirs>",
        "<parametresApportDeversoirs/>")
    sub(r"<ligneEau>.*?</ligneEau>",
        "<ligneEau>\n        <LigEauInit>true</LigEauInit>\n"
        "        <modeEntree>1</modeEntree>\n"
        "        <fichLigEau>init.lig</fichLigEau>\n"
        "        <formatFichLig>2</formatFichLig>\n"
        "        <nbPts>-0</nbPts>\n      </ligneEau>")
    sub(r"<parametresLoisHydrauliques>.*?</parametresLoisHydrauliques>",
        "<parametresLoisHydrauliques>\n      <nb>2</nb>\n      <lois>\n"
        "        <structureParametresLoi>\n          <nom>loi_inflow</nom>\n"
        "          <type>1</type>\n          <donnees>\n"
        "            <modeEntree>1</modeEntree>\n"
        "            <fichier>hydrogramme.loi</fichier>\n          </donnees>\n"
        "        </structureParametresLoi>\n"
        "        <structureParametresLoi>\n          <nom>loi_downstream</nom>\n"
        "          <type>5</type>\n          <donnees>\n"
        "            <modeEntree>1</modeEntree>\n"
        "            <fichier>tarage.loi</fichier>\n          </donnees>\n"
        "        </structureParametresLoi>\n      </lois>\n"
        "    </parametresLoisHydrauliques>")
    sub(r"<fichResultat>[^<]*</fichResultat>", "<fichResultat>mascaret_ecr.opt</fichResultat>")
    sub(r"<fichListing>[^<]*</fichListing>", "<fichListing>mascaret.lis</fichListing>")
    sub(r"<fichRepriseEcr>[^<]*</fichRepriseEcr>", "<fichRepriseEcr>mascaret.rep</fichRepriseEcr>")
    out_every = max(1, int(round(600.0 / dt)))
    sub(r"<premPasTpsStock>[^<]*</premPasTpsStock>", "<premPasTpsStock>1</premPasTpsStock>")
    sub(r"<pasStock>[^<]*</pasStock>", f"<pasStock>{out_every}</pasStock>")
    (proj / "mascaret.xcas").write_text(text, encoding="ISO-8859-1")
    (proj / "FichierCas.txt").write_text("mascaret.xcas\n", encoding="ascii")


def stage_1d(args: argparse.Namespace) -> None:
    workdir = CHAIN / "mdx_2d_coupled"
    flow = _read_exit_flux(workdir / "run.log")

    # coupled exit series on the 600 s grid, constant tail over the 24 h
    # horizon (the chain itself is defined over the 2D's 15 h window)
    grid = np.arange(0.0, 54000.0 + 1e-6, 600.0)
    q = np.interp(grid, flow[:, 0], flow[:, 1])
    tail = np.arange(54000.0 + 600.0, 86400.0 + 1e-6, 600.0)
    q_series = np.column_stack([
        np.concatenate([grid, tail]),
        np.concatenate([q, np.full(len(tail), q[-1])]),
    ])

    proj = CHAIN / "mdx_downstream_coupled"
    xcas = proj / "mascaret.xcas"
    if xcas.exists() and not args.force:
        print(f"[1d] {proj} exists; use --force to rebuild")
    else:
        down = load_scenario(Path("data/real_cases/scenarios_1d/mdx_downstream.npz"))
        _build_downstream_project(down, proj, q_series)
        print(f"[1d] downstream project rebuilt from npz (gateless) -> {proj}; "
              f"exit Q {q.min():.0f}..{q.max():.0f} m3/s")

    opt = proj / "mascaret_ecr.opt"
    if opt.exists() and not args.force:
        print("[1d] mascaret_ecr.opt exists; skipping run")
        return
    from run_real_family import run_mascaret
    print(f"[1d] running Mascaret in {IMAGE} ...")
    runtime = run_mascaret(proj, "mascaret.xcas", image=IMAGE)
    print(f"[1d] done in {runtime:.0f}s -> {opt}")


# --------------------------------------------------------------- assemble  #
def stage_assemble(args: argparse.Namespace) -> None:
    from build_mdx_chain_graph import (HORIZON_S, TARGET_DT, common_static_1d,
                                       common_static_2d, resample)
    from flow_mdk.data.graph_coupled import (Interface, SubGraph,
                                             build_coupled_graph)
    from flow_mdk.utils.io import Scenario

    upstream = load_scenario(UPSTREAM_NPZ)

    # 1. attach the COUPLED 2D truth to a chain-local COPY of the mesh npz
    #    (the canonical data/real_cases/meshes_2d/mdx_2d.npz stays untouched)
    mesh_coupled_path = CHAIN / "mdx_2d_coupled.npz"
    if not mesh_coupled_path.exists() or args.force:
        shutil.copy2(MESH_NPZ, mesh_coupled_path)
    from ingest_telemac2d_truth import ingest_results
    qc2d = ingest_results(CHAIN / "mdx_2d_coupled" / "res_coupled.slf",
                          mesh_coupled_path,
                          listing=CHAIN / "mdx_2d_coupled" / "run.log",
                          solver_tag="coupled_chain_v1", force=True)
    mesh = load_scenario(mesh_coupled_path)
    print(f"[asm] 2D coupled truth: {qc2d['frames']} frames, "
          f"h_max {qc2d['h_max_m']:.2f} m, "
          f"volume err <= {qc2d.get('volume_rel_err_max')}")
    if qc2d.get("problems"):
        print(f"[asm] 2D QC PROBLEMS: {qc2d['problems']}")

    # 2. downstream truth from the new .opt, node order rebuilt the same way
    #    import_real_cases did: geo profiles matched to mesh sections by
    #    abscissa (profile x reconstructed from the npz edge dx chain)
    down = load_scenario(Path("data/real_cases/scenarios_1d/mdx_downstream.npz"))
    opt = _read_opt(CHAIN / "mdx_downstream_coupled" / "mascaret_ecr.opt")
    vi = {v.strip().upper(): i for i, v in enumerate(opt["variables"])}
    y_idx = next(i for k, i in vi.items() if k == "Y")
    q_idx = next(i for k, i in vi.items() if k == "Q")
    x_profile = np.concatenate([[0.0], np.cumsum(down.edge_attr[0::2, 0])])
    sec_absc = np.nan_to_num(opt["abscissa"], nan=np.inf).min(axis=0)
    sec_absc = np.where(np.isfinite(sec_absc), sec_absc, np.nan)
    sel = np.array([int(np.nanargmin(np.where(np.isfinite(sec_absc),
                                              np.abs(sec_absc - x), np.inf)))
                    for x in x_profile])
    mis = float(np.nanmax(np.abs(sec_absc[sel] - x_profile)))
    depth = opt["data"][:, :, y_idx][:, sel]
    q = opt["data"][:, :, q_idx][:, sel]
    down_coupled = Scenario(
        name="mdx_downstream_coupled", node_static=down.node_static,
        edge_index=down.edge_index, edge_attr=down.edge_attr,
        dynamic=np.stack([depth, q], axis=-1).astype(np.float32),
        wet=(depth > 1e-3).astype(np.uint8), times=opt["times"],
        meta={**down.meta, "solver": "coupled_chain_v1"})
    print(f"[asm] downstream coupled truth: {depth.shape[0]} frames, "
          f"profile/mesh abscissa mismatch {mis:.2f} m, "
          f"Q_in {q[:, 0].min():.0f}..{q[:, 0].max():.0f} m3/s")

    # 3. graph assembly on the common grid (same rules as the dry run)
    classes = _cli_class(T2D_SRC / "mdx_BC.cli", ("455", "544"))
    inflow, outflow = classes["455"], classes["544"]
    up_al, up_info = resample(upstream, TARGET_DT, HORIZON_S)
    mesh_al, mesh_info = resample(mesh, TARGET_DT, HORIZON_S)
    down_al, down_info = resample(down_coupled, TARGET_DT, HORIZON_S)

    subs = [
        SubGraph("mdx_upstream", "1d", common_static_1d(up_al.node_static),
                 up_al.edge_index, up_al.edge_attr),
        SubGraph("mdx_2d_coupled", "2d",
                 common_static_2d(mesh_al.node_static, inflow, outflow),
                 mesh_al.edge_index, mesh_al.edge_attr),
        SubGraph("mdx_downstream_coupled", "1d",
                 common_static_1d(down_al.node_static),
                 down_al.edge_index, down_al.edge_attr),
    ]
    coupled = build_coupled_graph(
        subs,
        [Interface(a=0, nodes_a=[upstream.node_static.shape[0] - 1], b=1,
                   nodes_b=inflow, kind="chain_to_mesh", length_m=25.0),
         Interface(a=1, nodes_a=outflow, b=2, nodes_b=[0],
                   kind="mesh_to_chain", length_m=25.0)],
        meta={"layout": "coupled_1d2d", "dynamic_vars": ["h", "Q_or_|q|"],
              "elevation_feature_idx": 0,
              "solver": "coupled_chain_v1"},
    )
    scenario = Scenario(
        name="mdx_chain_v1",
        node_static=coupled.node_static,
        edge_index=coupled.edge_index,
        edge_attr=coupled.edge_attr,
        dynamic=np.concatenate(
            [up_al.dynamic, mesh_al.dynamic, down_al.dynamic], axis=1),
        wet=np.concatenate([up_al.wet, mesh_al.wet, down_al.wet], axis=1),
        times=up_al.times,
        meta={**coupled.meta, "interfaces": coupled.interfaces,
              "node_offsets": coupled.node_offsets,
              "coupling": {
                  "scheme": "one-way Q chain (v1): upstream Q -> 2D entrance "
                            "(Z exit clamped 280) -> exit Q/Z -> downstream loi",
                  "no_stage_feedback": True,
                  "2d_ingest_qc": qc2d,
                  "abscissa_mismatch_m": mis,
                  "time_alignment": {"mdx_upstream": up_info, "mdx_2d": mesh_info,
                                     "mdx_downstream": down_info},
              }},
    )
    out = CHAIN / "mdx_chain_v1.npz"
    save_scenario(scenario, out)
    (CHAIN / "split.json").write_text(json.dumps(
        {"train": ["mdx_chain_v1"], "val": ["mdx_chain_v1"],
         "test": ["mdx_chain_v1"]}, indent=1), encoding="utf-8")
    print(f"[asm] COUPLED chain npz -> {out} "
          f"({scenario.num_nodes} nodes, {scenario.edge_index.shape[1]} edges, "
          f"{scenario.dynamic.shape[0]} frames)")


# ----------------------------------------------------------------- helpers #
def _cli_class(cli_path: Path, keys, all_classes: bool = False):
    """0-based node ids per .cli boundary class key ('455'/'544')."""
    out: dict[str, list[int]] = {}
    for line in cli_path.read_text(errors="replace").splitlines():
        t = line.split()
        if len(t) < 13:
            continue
        try:
            key, nod = f"{t[0]}{t[1]}{t[2]}", int(t[11])
        except ValueError:
            continue
        if all_classes or key in keys:
            out.setdefault(key, []).append(nod - 1)
    return out


def _node_xy(geo_slf: Path) -> np.ndarray:
    from selafin import Selafin
    geo = Selafin(geo_slf)
    return np.column_stack([geo.x, geo.y])


def _exit_stage(res_slf: Path) -> np.ndarray:
    """(t, mean stage over the 7 exit nodes) from the coupled results."""
    from selafin import Selafin
    res = Selafin(res_slf)
    vi = {v.strip().upper(): i for i, v in enumerate(res.variables)}
    s_idx = next((i for k, i in vi.items()
                  if "FREE SURFACE" in k or "SURFACE LIBRE" in k), None)
    if s_idx is None:  # fallback: stage = bottom + depth
        b_idx = next(i for k, i in vi.items() if k.startswith("BOTTOM"))
        h_idx = next(i for k, i in vi.items() if k.startswith("WATER DEPTH") or
                     k.startswith("HAUTEUR"))
        stage = (res.all_frames(res.variables[b_idx]) +
                 res.all_frames(res.variables[h_idx]))
    else:
        stage = res.all_frames(res.variables[s_idx])
    outflow = _cli_class(T2D_SRC / "mdx_BC.cli", "544")["544"]
    return np.column_stack([res.times, stage[:, outflow].mean(axis=1)])


def _read_opt(opt_path: Path) -> dict:
    from import_real_cases import parse_opthyca
    return parse_opthyca(opt_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=["2d", "1d", "assemble"])
    parser.add_argument("--ncsize", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    {"2d": stage_2d, "1d": stage_1d, "assemble": stage_assemble}[args.stage](args)


if __name__ == "__main__":
    main()
