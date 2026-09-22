#!/usr/bin/env python
"""Flatten the coupled family into a training-ready data root (M4 v2).

``build_coupled_family.py`` writes each scenario into its own subdirectory
(``coupled_chain/mdx_chain_famXXX/mdx_chain_famXXX.npz``) while the training
pipeline's ``ScenarioStore`` loads flat ``<root>/<name>.npz`` paths. This
script materialises a dedicated family root — symlinks where the OS allows,
copies otherwise — WITHOUT touching the v1 root (``coupled_chain/`` keeps
its own ``split.json`` and single-scenario layout):

    data/real_cases/coupled_chain_family/
        mdx_chain_fam000.npz ... mdx_chain_fam011.npz
        split.json   train: fam001-009 · val: fam010 · test: fam000, fam011

fam000 is the baseline-parity draw (byte-identical qsl to v1, proven at
round-4 prep), so it goes to test for direct comparison with the v1
feasibility runs; fam011 (strongest draw, q_scale 1.97) joins it. Idempotent.

    python scripts/prepare_coupled_family_root.py
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

CHAIN = Path("data/real_cases/coupled_chain")
FAMILY = Path("data/real_cases/coupled_chain_family")

# Default (M4 v2, 12 scenarios): deterministic 9/1/2 over the sorted family,
# fam000 (v1 parity) + fam011 (strongest draw) as the test pair. Override with
# --test/--val for the expanded family (S1) — see run_M4v3_family.sh.
TEST = ["mdx_chain_fam000", "mdx_chain_fam011"]
VAL = ["mdx_chain_fam010"]
KS_MIN_TEST = 5   # summarize_runs.py needs >=5 scenarios in a domain for KS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chain-root", type=Path, default=CHAIN)
    parser.add_argument("--family-root", type=Path, default=FAMILY)
    parser.add_argument("--test", nargs="*", default=None,
                        help="override the test split (scenario names)")
    parser.add_argument("--val", nargs="*", default=None,
                        help="override the val split (scenario names)")
    args = parser.parse_args()
    test = list(TEST if args.test is None else args.test)
    val = list(VAL if args.val is None else args.val)

    fam_dirs = sorted(args.chain_root.glob("mdx_chain_fam*"))
    fams = [d.name for d in fam_dirs if (d / f"{d.name}.npz").exists()]
    if not fams:
        raise SystemExit(
            f"no family npz under {args.chain_root}/mdx_chain_fam*/ — run "
            "scripts/build_coupled_family.py on the server first")
    missing = [f for f in (*test, *val) if f not in fams]
    if missing:
        raise SystemExit(f"expected scenarios missing from the family: {missing}")
    if len(test) < KS_MIN_TEST:
        print(f"[famroot] NOTE: test split has {len(test)} scenario(s); "
              f"summarize_runs.py needs >= {KS_MIN_TEST} for KS tests "
              f"(coupling conclusions will have no significance support)")

    args.family_root.mkdir(parents=True, exist_ok=True)
    linked = copied = kept = 0
    for name in fams:
        src = args.chain_root / name / f"{name}.npz"
        dst = args.family_root / f"{name}.npz"
        if dst.exists() or dst.is_symlink():
            kept += 1
            continue
        try:
            # RELATIVE link target: the family root stays portable if the
            # repo tree is moved or rsynced (no machine-specific paths)
            os.symlink(os.path.relpath(src, args.family_root), dst)
            linked += 1
        except FileExistsError:
            kept += 1  # concurrent prep instance already linked it
        except OSError:  # Windows without symlink privilege: copy (~16 MB each)
            shutil.copyfile(src, dst)
            copied += 1

    split = {
        "train": [f for f in fams if f not in (*test, *val)],
        "val": val,
        "test": test,
    }
    split_path = args.family_root / "split.json"
    split_path.write_text(json.dumps(split, indent=1), encoding="utf-8")

    print(f"[famroot] family scenarios: {len(fams)} "
          f"(train {len(split['train'])} / val {len(val)} / test {len(test)})")
    print(f"[famroot] links: {linked} new, {copied} copied, {kept} kept -> "
          f"{args.family_root}")
    print(f"[famroot] split.json -> {split_path}")
    if len(fams) != len(split["train"]) + len(val) + len(test):
        print(f"[famroot] WARNING: {len(fams)} family scenarios but the split "
              f"covers {len(split['train']) + len(val) + len(test)}")


if __name__ == "__main__":
    main()
