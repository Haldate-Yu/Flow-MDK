#!/usr/bin/env python
"""Top up a real-master family to a target size (L6).

Extends a family with fresh scenario indices beyond the current maximum,
using a NEW seed (default: recorded family seed + 1) — the original RNG
stream is NOT replayable (the 2026-09-11 batch ran a pre-bootstrap working
tree, and the stored draws don't reproduce against the committed generator;
verified empirically), so eliminated indices are permanently retired rather
than revived. Each scenario is an independent parameter draw, so a fresh
seed has no statistical cost.

Existing npz files (truth attached) are never touched. Idempotent: rerun
after a batch with failures to top up again from the next free index.

Usage (repo root):

    python scripts/extend_family.py --family family_mdx --target 50
    python scripts/run_real_family.py --mode family --family-dir data/real_cases/family_mdx
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.gen.scenarios_real import RealFamilyParams, generate_real_family
from flow_mdk.utils.io import load_scenario

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "data" / "real_cases"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True, help="family dir name, e.g. family_mdx")
    parser.add_argument("--target", type=int, required=True, help="desired valid-scenario count")
    parser.add_argument("--seed", type=int, default=None,
                        help="extension seed (default: recorded family seed + 1)")
    args = parser.parse_args()

    family_dir = ROOT / args.family
    master = family_dir.name.removeprefix("family_")
    indices = sorted(
        int(m.group(1)) for p in family_dir.glob("*.npz")
        if (m := re.search(r"_fam(\d+)$", p.stem))
    )
    if not indices:
        raise SystemExit(f"no scenarios in {family_dir}")
    seed = args.seed
    if seed is None:
        seed = load_scenario(family_dir / f"{master}_fam{indices[0]:03d}.npz").meta["family"]["seed"] + 1

    deficit = args.target - len(indices)
    if deficit <= 0:
        print(f"[extend] {args.family}: {len(indices)} scenarios, target {args.target} reached")
        return
    start = indices[-1] + 1
    total = start + deficit
    print(f"[extend] {args.family}: {len(indices)} present, adding indices "
          f"{start}-{total - 1} (seed {seed}) ...")

    moved = []
    with tempfile.TemporaryDirectory() as tmp:
        generate_real_family(
            RealFamilyParams(master=master, num_scenarios=total, seed=seed),
            tmp,
        )
        replay_dir = Path(tmp) / f"family_{master}"
        for idx in range(start, total):
            src = replay_dir / f"{master}_fam{idx:03d}.npz"
            dst = family_dir / src.name
            if dst.exists():
                continue
            shutil.move(str(src), str(dst))
            moved.append(idx)
    print(f"[extend] moved {len(moved)} pending scenarios: "
          f"{moved[0]}-{moved[-1]}" if moved else "[extend] nothing to move")

    (family_dir / "extend_log.json").write_text(json.dumps({
        "family": args.family, "extension_seed": seed,
        "moved": moved, "present_before": len(indices), "target": args.target,
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
