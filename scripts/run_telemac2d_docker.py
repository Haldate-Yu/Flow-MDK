#!/usr/bin/env python
"""TELEMAC-2D ground-truth runner for 2D scenarios (scaffolded for M3).

Generates the TELEMAC-2D project for a Perlin-DEM scenario:

- geometry SELAFIN (``geo_*.slf``) from the structured grid, written in the
  layout observed in the v8p4 tree (validated by ``scripts/selafin.py``
  round-trip against ``examples/telemac2d/*/geo_*.slf``);
- steering ``.cas`` template with the breach inflow;
- runs the solver inside the TELEMAC image (docker) and converts the
  result SELAFIN back onto the scenario npz.

TODO(M3): boundary-conditions ``.cli`` generation (breach nodes as flow
boundaries, far-field walls) and end-to-end validation against the image —
M0/M1 concentrate on the 1D track.
"""

from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.utils.io import load_scenario  # noqa: E402

TELEMAC_IMAGE = os.environ.get("FLOW_MDK_TELEMAC_IMAGE", "telemac-debian:0.1")


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
        rec(b"MAILLAGE".ljust(32))
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


CAS_TEMPLATE = """\
 / steered by Flow-MDK (TODO(M3): validate all keywords against v8p4)
PRESET COMPUTATION : 2
GEOMETRY FILE FOR TELEMAC2D : 'geo_{name}.slf'
BOUNDARY CONDITIONS FILE : 'bc_{name}.cli'  / TODO(M3): generated
TIME STEP : {dt}
NUMBER OF TIME STEPS : {n_steps}
GRAPHIC PRINTOUT PERIOD : {print_period}
MASS-BALANCE : YES
INITIAL CONDITIONS : ZERO DEPTH
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, help="2D scenario .npz")
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--image", default=TELEMAC_IMAGE)
    parser.add_argument("--files-only", action="store_true",
                        help="write the project without running docker")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    grid = scenario.meta["grid"]
    nx, ny, cell = grid["nx"], grid["ny"], grid["cell_size"]
    ikle, ipobo = build_triangles(nx, ny)
    xs = (np.arange(nx) + 0.5) * cell
    ys = (np.arange(ny) + 0.5) * cell
    xx, yy = np.meshgrid(xs, ys, indexing="ij")
    bottom = scenario.node_static[:, 1]

    write_geometry_selafin(
        workdir / f"geo_{scenario.name}.slf",
        ikle, ipobo, xx.ravel(), yy.ravel(), bottom,
    )
    dt = scenario.meta["dt_out"] / 10.0
    n_steps = int(scenario.times[-1] / dt)
    cas = workdir / f"t2d_{scenario.name}.cas"
    cas.write_text(
        CAS_TEMPLATE.format(name=scenario.name, dt=dt, n_steps=n_steps,
                            print_period=max(1, int(round(scenario.meta["dt_out"] / dt)))),
        encoding="ascii",
    )
    print(f"TELEMAC-2D project written to {workdir} (.cas + geometry .slf)")
    print("TODO(M3): generate bc_{name}.cli and run the image end-to-end")

    if not args.files_only:
        cmd = [
            "docker", "run", "--rm", "-v", f"{workdir.resolve()}:/work", "-w", "/work",
            args.image, "bash", "-lc",
            "source /etc/profile.d/setenv.sh && telemac2d.py "
            f"t2d_{scenario.name}.cas --ncsize=1",
        ]
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
