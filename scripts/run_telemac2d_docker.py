#!/usr/bin/env python
"""TELEMAC-2D ground-truth runner for synthetic 2D scenarios (M3).

End-to-end for one scenario npz from ``gen/scenarios_2d.py`` (structured
grid, dry start, breach inflow):

- geometry SELAFIN (``geo_<name>.slf``) in the v8p4 layout, bottom variable
  named ``BOTTOM`` as the solver expects (verified against the real wqh.slf);
- walls-only boundary ``.cli``: every boundary node clones the wall line of
  the real wqh_BC.cli verbatim (all lines identical -> order-independent),
  inflow does NOT go through the boundary;
- inflow as a TELEMAC source point instead: one interior node adjacent to
  the breach border, via ``source_regions.qsl`` (single-node polygon) +
  ``source.qsl`` (constant discharge) — the same mechanism the real
  projects use, and it keeps the .cli trivially correct;
- steering ``.cas`` with the production keyword set of the real wqh project
  (tidal flats, scheme 14, mass lumping, ...) at Manning n from the scenario;
- runs the image (``telemac2d.py``, serial by default — a 64x64 grid is
  small and parallelism happens across scenarios), then ingests the result
  onto the scenario npz with the plausibility QC of
  ``ingest_telemac2d_truth.ingest_results``.

    python scripts/run_telemac2d_docker.py --scenario data/scenarios_2d/T2D_000.npz \
        --workdir data/scenarios_2d_runs/T2D_000
"""

from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flow_mdk.utils.io import load_scenario  # noqa: E402
from ingest_telemac2d_truth import ingest_results  # noqa: E402

TELEMAC_IMAGE = os.environ.get("FLOW_MDK_TELEMAC_IMAGE", "flow-mdk-telemac:v8p4r0p1")

# verbatim wall line of the real wqh_BC.cli (LIHBOR=2 IHBOR=2 LITBOR=2 ...),
# with the trailing node id and boundary index substituted
WALL_LINE = ("2 2 2  0.000 0.000 0.000 0.000  2  0.000 0.000 0.000  "
             "{node:10d}  {idx:10d}   # ")


def write_geometry_selafin(
    path: Path,
    ikle: np.ndarray,  # [nelem, 3] 1-based triangle connectivity
    ipobo: np.ndarray,  # [npoin]
    x: np.ndarray,
    y: np.ndarray,
    bottom: np.ndarray,
) -> None:
    """Geometry-only SELAFIN in the v8p4 observed layout."""
    title = f"FLOW-MDK GEOMETRY {path.stem}".ljust(80)
    with open(path, "wb") as fh:
        def rec(payload: bytes) -> None:
            fh.write(struct.pack(">i", len(payload)))
            fh.write(payload)
            fh.write(struct.pack(">i", len(payload)))

        rec(title.encode("ascii"))
        rec(struct.pack(">2i", 1, 0))  # nbvar, nbvar_units
        rec(b"BOTTOM          m".ljust(32))  # name the solver resolves
        rec(struct.pack(">10i", 1, 0, 0, 0, 0, 0, 0, 0, 0, 1))
        rec(struct.pack(">6i", 1900, 1, 1, 0, 0, 0))  # date record
        nelem, npoin, ndp = ikle.shape[0], x.size, 3
        rec(struct.pack(">4i", nelem, npoin, ndp, 1))
        rec(ikle.astype(">i4").tobytes())
        rec(ipobo.astype(">i4").tobytes())
        rec(x.astype(">f4").tobytes())
        rec(y.astype(">f4").tobytes())
        # v8p4 layout: one float32 time marker (0.0) then the MAILLAGE frame
        rec(struct.pack(">f", 0.0))
        rec(bottom.astype(">f4").tobytes())


def build_triangles(nx: int, ny: int) -> tuple[np.ndarray, np.ndarray]:
    """Split each grid cell into 2 triangles; 1-based connectivity + ipobo."""
    def nid(i: int, j: int) -> int:
        return i * ny + j + 1  # 1-based

    tris, ipobo = [], np.zeros(nx * ny, dtype=np.int64)
    for i in range(nx - 1):
        for j in range(ny - 1):
            a, b, c, d = nid(i, j), nid(i + 1, j), nid(i + 1, j + 1), nid(i, j + 1)
            tris.append([a, b, c])
            tris.append([a, c, d])
    for j in range(ny):
        ipobo[nid(0, j) - 1] = 1
        ipobo[nid(nx - 1, j) - 1] = 1
    for i in range(nx):
        ipobo[nid(i, 0) - 1] = 1
        ipobo[nid(i, ny - 1) - 1] = 1
    return np.asarray(tris, dtype=np.int64), ipobo


def source_node(meta: dict) -> tuple[int, float, float]:
    """Interior node adjacent to the breach border + its (x, y) [m]."""
    grid = meta["grid"]
    nx, ny, cell = grid["nx"], grid["ny"], grid["cell_size"]
    side = meta["boundary"]["side"]
    j0 = ny // 2
    i0 = nx // 2
    if side == "west":
        node, i, j = 1 * ny + j0, 1, j0
    elif side == "east":
        node, i, j = (nx - 2) * ny + j0, nx - 2, j0
    elif side == "south":
        node, i, j = i0 * ny + 1, i0, 1
    elif side == "north":
        node, i, j = i0 * ny + (ny - 2), i0, ny - 2
    else:
        raise ValueError(f"unknown breach side {side}")
    return node, (i + 0.5) * cell, (j + 0.5) * cell


def write_source_files(workdir: Path, x: float, y: float, discharge: float,
                       cell: float) -> None:
    """Single-node source region + constant-discharge time series.

    The qsl needs a row beyond the simulated duration, otherwise the first
    interpolation step aborts with OUT OF RANGE (real projects carry a
    trailing 100000 s row for the same reason).
    """
    pad = 0.4 * cell  # square enclosing exactly the one grid node
    (workdir / "source_regions.qsl").write_text(
        f"X(1) Y(1)\n{x - pad:.3f} {y - pad:.3f}\n{x + pad:.3f} {y - pad:.3f}\n"
        f"{x + pad:.3f} {y + pad:.3f}\n{x - pad:.3f} {y + pad:.3f}\n# #\n",
        encoding="ascii")
    (workdir / "source.qsl").write_text(
        "T Q(1)\ns m3/s\n0.0  %.6f\n1.0E+09  %.6f\n" % (discharge, discharge),
        encoding="ascii")


def write_boundary_cli(path: Path, ipobo: np.ndarray) -> None:
    """Walls-only .cli: one verbatim wall line per boundary node."""
    nodes = np.nonzero(ipobo)[0] + 1  # 1-based node ids, ascending
    lines = [WALL_LINE.format(node=int(n), idx=k + 1)
             for k, n in enumerate(nodes)]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


CAS_TEMPLATE = """\
 / steered by Flow-MDK (M3 synthetic family; keyword set mirrors the real
 / production wqh project on the same v8p4 solver)
TITLE = 'flow-mdk 2D {name}'
GEOMETRY FILE = 'geo_{name}.slf'
BOUNDARY CONDITIONS FILE = 'bc_{name}.cli'
INITIAL CONDITIONS = 'ZERO DEPTH'
TIME STEP = {dt}
NUMBER OF TIME STEPS = {n_steps}
GRAPHIC PRINTOUT PERIOD = {print_period}
LISTING PRINTOUT PERIOD = {print_period}
VARIABLES FOR GRAPHIC PRINTOUTS = 'U,V,S,B,H,F'
RESULTS FILE = 'res_{name}.slf'
MASS-BALANCE = YES
TIDAL FLATS = YES
OPTION FOR THE TREATMENT OF TIDAL FLATS = 1
TREATMENT OF NEGATIVE DEPTHS = 2
FREE SURFACE GRADIENT COMPATIBILITY = 0.9
CONTINUITY CORRECTION = YES
TYPE OF ADVECTION = 1;5
SUPG OPTION = 0;0
H CLIPPING = NO
MASS-LUMPING ON H = 1.
LAW OF BOTTOM FRICTION = 3
FRICTION COEFFICIENT = {manning}
SCHEME FOR ADVECTION OF VELOCITIES = 14
SCHEME OPTION FOR ADVECTION OF VELOCITIES = 1
IMPLICITATION FOR DEPTH = 1
IMPLICITATION FOR VELOCITY = 0.55
TURBULENCE MODEL = 1
VELOCITY DIFFUSIVITY = 1.E-6
TREATMENT OF THE LINEAR SYSTEM = 2
SOLVER = 1
SOLVER ACCURACY = 1.E-5
SOURCES FILE = 'source.qsl'
SOURCE REGIONS DATA FILE = 'source_regions.qsl'
MAXIMUM NUMBER OF POINTS FOR SOURCES REGIONS = 99999
WATER DISCHARGE OF SOURCES = {discharge}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, help="2D scenario .npz")
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--image", default=TELEMAC_IMAGE)
    parser.add_argument("--ncsize", type=int, default=1,
                        help="MPI ranks (a 64x64 grid runs serial in minutes)")
    parser.add_argument("--dt", type=float, default=5.0,
                        help="solver time step [s] (Courant-safe at 100 m cells)")
    parser.add_argument("--files-only", action="store_true",
                        help="write the project without running docker")
    parser.add_argument("--force", action="store_true",
                        help="rerun even if the scenario already carries truth")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    if (scenario.meta.get("solver") == "telemac2d_docker_rerun"
            and not args.force):
        print(f"[t2d] {scenario.name}: truth already attached, skip")
        return
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    grid = scenario.meta["grid"]
    nx, ny, cell = grid["nx"], grid["ny"], grid["cell_size"]
    ikle, ipobo = build_triangles(nx, ny)
    xs = (np.arange(nx) + 0.5) * cell
    ys = (np.arange(ny) + 0.5) * cell
    xx, yy = np.meshgrid(xs, ys, indexing="ij")
    bottom = scenario.node_static[:, 1]

    name = scenario.name
    write_geometry_selafin(
        workdir / f"geo_{name}.slf",
        ikle, ipobo, xx.ravel(), yy.ravel(), bottom,
    )
    write_boundary_cli(workdir / f"bc_{name}.cli", ipobo)
    node, sx, sy = source_node(scenario.meta)
    write_source_files(workdir, sx, sy,
                       scenario.meta["boundary"]["discharge"], cell)

    dt = args.dt
    n_steps = int(round(scenario.times[-1] / dt))
    print_period = max(1, int(round(scenario.meta["dt_out"] / dt)))
    cas = workdir / f"t2d_{name}.cas"
    cas.write_text(
        CAS_TEMPLATE.format(name=name, dt=dt, n_steps=n_steps,
                            print_period=print_period,
                            manning=float(scenario.node_static[0, 4]),
                            discharge=scenario.meta["boundary"]["discharge"]),
        encoding="ascii")
    print(f"[t2d] {name}: project written ({n_steps} steps @ {dt}s, "
          f"source node {node} @ ({sx:.0f},{sy:.0f}), Q="
          f"{scenario.meta['boundary']['discharge']} m3/s)")
    if args.files_only:
        return

    log = workdir / "run.log"
    t0 = time.perf_counter()
    cmd = [
        "docker", "run", "--rm", "-v", f"{workdir.resolve()}:/work",
        args.image, "bash", "-lc",
        "export PATH=\"${HOMETEL}/builds/${USETELCFG}/bin:$PATH\" && "
        "cd /work && "
        f"python3 ${{HOMETEL}}/scripts/python3/telemac2d.py t2d_{name}.cas "
        f"--ncsize={args.ncsize}",
    ]
    with open(log, "w", encoding="utf-8") as fh:
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT)
    runtime = time.perf_counter() - t0
    if proc.returncode != 0 or not (workdir / f"res_{name}.slf").exists():
        print(f"[t2d] {name}: FAILED (rc={proc.returncode}, log -> {log})")
        raise SystemExit(1)

    qc = ingest_results(workdir / f"res_{name}.slf", Path(args.scenario),
                        listing=log, force=True)
    # ingest_results re-loads and saves the scenario from disk; re-load here
    # before patching runtime, or the stale zero-dynamic object would clobber
    # the attached truth
    from flow_mdk.utils.io import load_scenario as _reload, save_scenario
    fresh = _reload(Path(args.scenario))
    fresh.meta["runtime_s"] = runtime
    save_scenario(fresh, Path(args.scenario))
    problems = qc["problems"]
    print(f"[t2d] {name}: {qc['frames']} frames, {runtime / 60:.1f} min, "
          f"h_max {qc['h_max_m']:.2f} m, wet {qc['wet_frac_first']:.2f}"
          f"->{qc['wet_frac_last']:.2f}"
          + (f", |volume err| <= {qc['volume_rel_err_max']:.2e}"
             if qc["volume_rel_err_max"] is not None else "")
          + f" -> {'QC PASS' if not problems else 'QC FAIL: ' + '; '.join(problems)}")


if __name__ == "__main__":
    main()
