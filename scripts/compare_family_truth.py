#!/usr/bin/env python
"""Compare family truths: validated original vs patched-kernel scratch rerun.

Decision tool for the pending L11 follow-up: the 2026-09-12 kernel patches
(XAJ undefined state + upstream-Q YFIX, see
datasets/telemac-mascaret-v8p4r0/PATCHES.md) removed random SIGSEGVs but
may also have shifted truths that the *unpatched* kernel produced without
crashing (silent out-of-bounds reads). This script quantifies the drift
between the validated family npz and a scratch rerun produced with
``run_real_family.py --mode family --force --runs-root <scratch>`` on a
COPY of the family:

    python scripts/compare_family_truth.py \
        --ref data/real_cases/family_zxh \
        --new data/real_cases/_patchfix_diff/family_zxh

Verdict rule: every compared scenario within --tol-h (default 2 cm RMSE)
means the patched kernel reproduces the validated truth and the family
rerun is unnecessary; anything above it goes into the decision list.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.utils.io import load_scenario  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, type=Path,
                        help="validated family dir (untouched)")
    parser.add_argument("--new", required=True, type=Path,
                        help="scratch rerun dir (patched kernel)")
    parser.add_argument("--tol-h", type=float, default=0.02,
                        help="h-RMSE tolerance in m for 'unchanged' (default 0.02)")
    parser.add_argument("--out-json", type=Path, default=None,
                        help="write the full comparison report (default: "
                             "<new>/truth_diff_report.json)")
    args = parser.parse_args()

    # The scratch npz start as byte copies of the validated family, so the
    # npz alone cannot tell "rerun" from "not yet rerun". The runner's
    # run_report.json (statuses of the scenarios it actually computed) is
    # the authority; scenarios absent from it are reported as not_rerun.
    rerun_status: dict[str, str] | None = None
    report_path = args.new / "run_report.json"
    if report_path.exists():
        try:
            rerun_status = {
                r["scenario"]: r.get("status", "?")
                for r in json.loads(report_path.read_text(encoding="utf-8"))
            }
        except (json.JSONDecodeError, KeyError):
            rerun_status = None

    rows = []
    for ref_path in sorted(args.ref.glob("*.npz")):
        new_path = args.new / ref_path.name
        if not new_path.exists():
            rows.append({"scenario": ref_path.stem, "status": "not_rerun"})
            continue
        if rerun_status is not None:
            status = rerun_status.get(ref_path.stem)
            if status is None:
                rows.append({"scenario": ref_path.stem, "status": "not_rerun"})
                continue
            if status != "ok":
                rows.append({"scenario": ref_path.stem, "status": f"rerun_{status}"})
                continue
        ref = load_scenario(ref_path)
        new = load_scenario(new_path)
        entry = {
            "scenario": ref.name,
            "frames_ref": int(ref.dynamic.shape[0]),
            "frames_new": int(new.dynamic.shape[0]),
        }
        n = min(ref.dynamic.shape[0], new.dynamic.shape[0])
        if ref.dynamic.shape[1:] != new.dynamic.shape[1:]:
            entry["status"] = "shape_mismatch"
            rows.append(entry)
            continue
        dh = new.dynamic[:n, :, 0] - ref.dynamic[:n, :, 0]
        dq = new.dynamic[:n, :, 1] - ref.dynamic[:n, :, 1]
        h_rmse = float(np.sqrt((dh ** 2).mean()))
        entry.update({
            "status": "ok",
            "h_rmse_m": h_rmse,
            "q_rmse_m3s": float(np.sqrt((dq ** 2).mean())),
            "h_max_abs_diff_m": float(np.abs(dh).max()),
            "h_bias_m": float(dh.mean()),
        })
        rows.append(entry)

    compared = [r for r in rows if r["status"] == "ok"]
    drift = [r for r in compared if r["h_rmse_m"] > args.tol_h]
    missing = [r for r in rows if r["status"] != "ok"]

    lines = [
        f"# Truth diff — {args.ref.name} vs patched-kernel rerun",
        f"\nGenerated {time.strftime('%Y-%m-%d %H:%M')} · "
        f"tolerance h-RMSE {args.tol_h * 100:.1f} cm",
        f"\n| scenario | frames (ref/new) | h-RMSE m | max|dh| m | h bias m | Q-RMSE m³/s |",
        "|---|---|---|---|---|---|",
    ]
    for r in compared:
        lines.append(
            f"| {r['scenario']} | {r['frames_ref']}/{r['frames_new']} "
            f"| {r['h_rmse_m']:.4f} | {r['h_max_abs_diff_m']:.4f} "
            f"| {r['h_bias_m']:+.4f} | {r['q_rmse_m3s']:.2f} |")
    for r in missing:
        lines.append(f"| {r['scenario']} | — | {r['status']} | — | — | — |")

    lines.append("")
    if compared:
        vals = [r["h_rmse_m"] for r in compared]
        lines.append(
            f"Compared {len(compared)} scenarios: h-RMSE max {max(vals):.4f} m, "
            f"median {float(np.median(vals)):.4f} m; {len(drift)} above tolerance."
        )
    if drift:
        lines.append(
            "\n**Verdict: DRIFT DETECTED** — the patched kernel changes the "
            "validated truth beyond tolerance for: "
            + ", ".join(r["scenario"] for r in drift)
            + "\n\nDecision required: either keep the validated truths (B1/B2 "
            "results stand) or rerun the family with the patched kernel and "
            "retrain (see PLAN L11)."
        )
    elif missing:
        lines.append(
            "\n**Verdict: INCOMPLETE** — rerun has not covered every scenario "
            "yet; no drift beyond tolerance among the compared ones."
        )
    else:
        lines.append(
            "\n**Verdict: TRUTH UNCHANGED** — the patched kernel reproduces "
            "the validated truth within tolerance; the family rerun is "
            "unnecessary and B1/B2 results stand."
        )

    report = "\n".join(lines) + "\n"
    print(report)
    out = args.out_json or (args.new / "truth_diff_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ref": str(args.ref), "new": str(args.new),
        "tol_h_m": args.tol_h, "rows": rows,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"report -> {out}")


if __name__ == "__main__":
    main()
