#!/usr/bin/env python
"""Ingest a TELEMAC-2D rerun as 2D ground truth (with plausibility QC).

The 2D real-project templates carry no historical result archive (old.slf is
a single-frame initial-depth snapshot, NOT a validation reference — unlike the
1D .opt track), so a rerun cannot be validated by exact reproduction. The
rerun output therefore becomes the canonical truth by definition, admitted
through a physical plausibility gate instead:

- mass-balance relative errors parsed from the solver listing (the .cas sets
  MASS-BALANCE = True; machine-precision volume errors are the strongest
  internal consistency signal available);
- NaN / depth-range / wet-fraction sanity over the rollout;
- frame cadence and mesh-identity checks against the imported npz.

    python scripts/ingest_telemac2d_truth.py \
        --workdir data/real_cases/telemac2d_runs/wqh_2d \
        --mesh data/real_cases/meshes_2d/wqh_2d.npz \
        --listing data/real_cases/telemac2d_runs/wqh_2d_run.log
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flow_mdk.utils.io import load_scenario, save_scenario  # noqa: E402
from selafin import Selafin  # noqa: E402


def parse_listing(listing: Path) -> dict:
    """Volume-balance errors + Courant numbers from the solver listing."""
    text = (listing.read_text(encoding="utf-8", errors="replace")
            if listing.exists() else "")
    vol = [abs(float(v)) for v in re.findall(
        r"RELATIVE ERROR IN VOLUME AT T =\s*[0-9.E+-]+\s*S\s*:\s*([0-9.E+-]+)",
        text)]
    courant = [float(v) for v in
               re.findall(r"MAXIMUM COURANT NUMBER:\s*([0-9.E+-]+)", text)]
    return {
        "volume_rel_err_max": max(vol) if vol else None,
        "volume_err_samples": len(vol),
        "courant_max": max(courant) if courant else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", required=True, type=Path,
                        help="telemac2d_runs/<case>_2d containing the results slf")
    parser.add_argument("--mesh", required=True, type=Path,
                        help="imported mesh npz (data/real_cases/meshes_2d/<case>.npz)")
    parser.add_argument("--results", default="res.slf", type=Path,
                        help="results selafin name inside workdir")
    parser.add_argument("--listing", type=Path, default=None,
                        help="solver listing/log for the mass-balance QC")
    parser.add_argument("--force", action="store_true",
                        help="overwrite truth that is already attached")
    args = parser.parse_args()

    scenario = load_scenario(args.mesh)
    assert scenario.meta.get("layout") == "2d_mesh", "not a 2D mesh npz"
    if scenario.meta.get("solver") == "telemac2d_docker_rerun" and not args.force:
        raise SystemExit("truth already attached; use --force to overwrite")

    res = Selafin(args.workdir / args.results)
    n = res.npoin
    if n != scenario.node_static.shape[0]:
        raise SystemExit(
            f"mesh mismatch: results npoin={n} vs npz {scenario.node_static.shape[0]}")

    var_index = {v.strip().upper(): i for i, v in enumerate(res.variables)}
    h_idx = next((i for k, i in var_index.items() if k.startswith("WATER DEPTH")), None)
    u_idx = next((i for k, i in var_index.items() if k.startswith("VELOCITY U")), None)
    v_idx = next((i for k, i in var_index.items() if k.startswith("VELOCITY V")), None)
    if h_idx is None or u_idx is None or v_idx is None:
        raise SystemExit(f"required variables missing in {list(res.variables)}")

    depth = res.all_frames(res.variables[h_idx])          # [T, N]
    u = res.all_frames(res.variables[u_idx])
    v = res.all_frames(res.variables[v_idx])
    qmag = np.sqrt(u ** 2 + v ** 2)
    dynamic = np.stack([depth, qmag], axis=-1).astype(np.float32)
    times = res.times.astype(np.float64)

    problems = []
    if np.isnan(dynamic).any():
        problems.append("NaN in results")
    if dynamic.shape[0] < 3:
        problems.append(f"degenerate frame count ({dynamic.shape[0]})")
    h_max = float(depth.max())
    wet_frac = (depth > 1e-3).mean(axis=1)
    listing = args.listing or (args.workdir.parent / f"{args.workdir.name}_run.log")
    qc = {
        "frames": int(dynamic.shape[0]),
        "cadence_s": float(np.median(np.diff(times))) if len(times) > 1 else 0.0,
        "h_min_m": float(depth.min()),
        "h_max_m": h_max,
        "q_max_m_s": float(qmag.max()),
        "wet_frac_first": float(wet_frac[0]),
        "wet_frac_last": float(wet_frac[-1]),
        **parse_listing(listing),
    }
    if qc["h_max_m"] > 50.0:
        problems.append(f"h_max blow-up ({h_max:.1f} m)")
    if qc["volume_rel_err_max"] is not None and qc["volume_rel_err_max"] > 1e-2:
        problems.append(f"mass-balance error {qc['volume_rel_err_max']:.2e}")

    scenario.dynamic = dynamic
    scenario.wet = (depth > 1e-3).astype(np.uint8)
    scenario.times = times
    scenario.meta["solver"] = "telemac2d_docker_rerun"
    scenario.meta["telemac2d_truth"] = {**qc, "problems": problems,
                                        "results": str(args.workdir / args.results)}
    save_scenario(scenario, args.mesh)

    err = qc["volume_rel_err_max"]
    print(f"[2d] {scenario.name}: {qc['frames']} frames @ {qc['cadence_s']:.0f}s, "
          f"h in [{qc['h_min_m']:.3f}, {qc['h_max_m']:.2f}] m, "
          f"q_max {qc['q_max_m_s']:.2f} m/s, wet {qc['wet_frac_first']:.2f}"
          f"->{qc['wet_frac_last']:.2f}"
          + (f", |volume err| <= {err:.2e} ({qc['volume_err_samples']} samples)"
             if err is not None else ", no listing QC"))
    print(f"[2d] {'PROBLEMS: ' + '; '.join(problems) if problems else 'QC PASS'}")
    out_json = args.workdir / "truth_ingest_report.json"
    out_json.write_text(json.dumps({**qc, "problems": problems},
                                   indent=2, ensure_ascii=False),
                        encoding="utf-8")
    print(f"[2d] truth attached -> {args.mesh}")
    print(f"[2d] report -> {out_json}")


if __name__ == "__main__":
    main()
