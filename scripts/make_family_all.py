#!/usr/bin/env python
"""Merge the three real-master families into one B1 training root (L3).

Each family ships its own split.json; the merged root concatenates the
splits (train/val/test) and copies the scenario npz files under
``data/real_cases/family_all/`` so a single training run covers all
real-geometry masters (mdx / zxh / wqh, 117 scenarios).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path("data/real_cases")
OUT = ROOT / "family_all"
FAMILIES = ("family_mdx", "family_zxh", "family_wqh")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    merged = {"train": [], "val": [], "test": []}
    seen = set()
    for fam in FAMILIES:
        split = json.loads((ROOT / fam / "split.json").read_text(encoding="utf-8"))
        for key in ("train", "val", "test"):
            for name in split[key]:
                if name in seen:
                    raise SystemExit(f"duplicate scenario name across families: {name}")
                seen.add(name)
                src = ROOT / fam / f"{name}.npz"
                shutil.copy2(src, OUT / f"{name}.npz")
                merged[key].append(name)
    (OUT / "split.json").write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print({k: len(v) for k, v in merged.items()}, "->", OUT)


if __name__ == "__main__":
    main()
