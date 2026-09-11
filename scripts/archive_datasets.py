#!/usr/bin/env python
"""Archive every dataset needed for reproducibility into ``datasets/``.

Layout (see datasets/README.md):

    datasets/
    ├── telemac-mascaret-v8p4r0/   solver source snapshot + docker build files
    ├── swegnn-official/           official SWE-GNN code + raw datasets (130 sims)
    ├── real_projects/             raw schinta basin templates (1D x5, 2D x2)
    ├── partA_synthetic/           generated scenario family (50 npz + splits)
    ├── partB_family_mdx/          real-master family (npz + splits + Mascaret workdirs)
    ├── partB_family_zxh/
    ├── partB_real_cases/          imported real cases, meshes, inventory, validation
    ├── runs/                      training/evaluation results (config, history, ckpt)
    └── MANIFEST.json              sha256 + size + role of every archived file

Process data policy: per-scenario Mascaret workdirs are archived WITHOUT the
``.lis`` listing (regenerable by re-running; the ``.opt`` result files and all
inputs are kept).

Usage
-----
    python scripts/archive_datasets.py [--hash] [--skip-big]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
OUT = REPO / "datasets"

SOURCES = {
    "telemac-mascaret-v8p4r0": {
        "origin": r"D:\tmp\telemac-wz-260529\telemac-mascaret",
        "role": "TELEMAC-MASCARET v8p4r0 solver source snapshot (examples excluded, 1.4 GB regenerable from the upstream tree)",
        "subdirs": ["sources", "scripts", "configs", "documentation"],
        "files": ["LICENSE.txt", "NEWS.txt", "README.txt", "REQUIREMENTS.txt"],
        "extra_files": {
            "docker/Dockerfile": r"D:\tmp\telemac-wz-260529\Dockerfile",
            "docker/build.sh": r"D:\tmp\telemac-wz-260529\build.sh",
            "docker/entrypoint.sh": r"D:\tmp\telemac-wz-260529\entrypoint.sh",
            "docker/setenv.sh": r"D:\tmp\telemac-wz-260529\setenv.sh",
            "docker/systel.cfg": r"D:\tmp\telemac-wz-260529\systel.cfg",
        },
    },
    "swegnn-official": {
        "origin": r"D:\tmp\swegnn-official",
        "role": "Official SWE-GNN repository (RBTV1/SWE-GNN-paper-repository-) incl. raw_datasets (130 Delft3D-FM simulations)",
        "subdirs": ["models", "training", "utils", "database", "raw_datasets", "results"],
        "files": ["README.md", "config.yaml", "main.py", "requirements.txt", "LICENSE"],
    },
    "real_projects": {
        "origin": r"D:\Projects\wzzhsl-rest-subsystems-xd\schinta-module-basin-flood-prevention"
                  r"\schinta-module-basin-flood-prevention-start\src\main\resources\template",
        "role": "Raw real-basin Mascaret / TELEMAC-2D project templates (mdx/wqh/zxh 1D, "
                "mdxUpStream/mdxDownStream coupled legs, wqh/mdx 2D)",
        "subdirs": ["telemac1d", "telemac2d"],
        "files": [],
    },
    "real_sources": {
        "origin": str(REPO / "data" / "real_sources"),
        "role": "Complete second-provider 1D projects vendored into the repo "
                "(wqh + zxh): launcher files, Abaques, historical .opt/.lis — "
                "both validated by exact rerun reproduction (RMSE=0)",
        "subdirs": ["wqh", "zxh"],
        "files": [],
    },
}


def copy_tree(src: Path, dst: Path, skip_names: tuple[str, ...] = ()) -> int:
    n = 0
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in skip_names:
            continue
        target = dst / item.name
        if item.is_dir():
            n += copy_tree(item, target, skip_names)
        else:
            shutil.copy2(item, target)
            n += 1
    return n


def archive_workdir(src: Path, dst: Path) -> int:
    """Mascaret run workdir without the regenerable .lis listing."""
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for item in src.iterdir():
        if item.suffix == ".lis":
            continue
        if item.is_file():
            shutil.copy2(item, dst / item.name)
            n += 1
    return n


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hash", action="store_true", help="compute sha256 in the manifest")
    parser.add_argument("--skip-big", action="store_true",
                        help="skip swegnn-official raw_datasets (2 GB)")
    args = parser.parse_args()

    if OUT.exists():
        print(f"datasets/ already exists — refreshing in place")
    OUT.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"created": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "repo": str(REPO), "items": {}}

    # 1. external sources --------------------------------------------------
    for name, spec in SOURCES.items():
        origin = Path(spec["origin"])
        if not origin.exists():
            print(f"[skip] {name}: origin missing {origin}")
            continue
        dst = OUT / name
        n = 0
        for sub in spec.get("subdirs", []):
            if args.skip_big and sub == "raw_datasets":
                print(f"[skip-big] {name}/{sub}")
                continue
            if (origin / sub).exists():
                n += copy_tree(origin / sub, dst / sub)
        for fname in spec.get("files", []):
            if any(c in fname for c in "*?["):
                matches = sorted(origin.glob(fname))
            else:
                matches = [origin / fname] if (origin / fname).exists() else []
            for m in matches:
                dst.mkdir(parents=True, exist_ok=True)
                shutil.copy2(m, dst / m.name)
                n += 1
        for rel, src in spec.get("extra_files", {}).items():
            src = Path(src)
            if src.exists():
                (dst / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst / rel)
                n += 1
        manifest["items"][name] = {"role": spec["role"], "origin": str(origin),
                                   "files": n}
        print(f"[ok] {name}: {n} files")

    # 2. generated datasets ------------------------------------------------
    gen_specs = {
        "partA_synthetic": {
            "role": "Part A: synthetic 1D scenario family (SWE-GNN-style), "
                    "diffusive-wave reference truth",
            "copy": [(DATA / "scenarios_1d", ".", None)],
        },
        "partB_family_mdx": {
            "role": "Part B1: real-master family (mdx geometry x synthetic hydrology), "
                    "Mascaret docker truth",
            "copy": [(DATA / "real_cases/family_mdx", ".", None)],
            "workdirs": (DATA / "real_cases/mascaret_runs", "mdx_fam*"),
        },
        "partB_family_zxh": {
            "role": "Part B1: real-master family (zxh geometry x synthetic hydrology), "
                    "Mascaret docker truth",
            "copy": [(DATA / "real_cases/family_zxh", ".", None)],
            "workdirs": (DATA / "real_cases/mascaret_runs", "zxh_fam*"),
        },
        "partB_family_wqh": {
            "role": "Part B1: real-master family (complete wqh geometry x synthetic "
                    "hydrology), Mascaret docker truth (40/40 succeeded)",
            "copy": [(DATA / "real_cases/family_wqh", ".", None)],
            "workdirs": (DATA / "real_cases/mascaret_runs", "wqh_fam*"),
        },
        "partB_real_cases": {
            "role": "Part B2: imported real cases (history .opt replay / rerun truth) "
                    "+ 2D meshes + inventory + validation reports",
            "copy": [(DATA / "real_cases/scenarios_1d", "scenarios_1d", None),
                     (DATA / "real_cases/meshes_2d", "meshes_2d", None),
                     (DATA / "real_cases/inventory.json", "inventory.json", None),
                     (DATA / "real_cases/validation_mdx.json", "validation_mdx.json", None),
                     (DATA / "real_cases/validation_zxh.json", "validation_zxh.json", None),
                     (DATA / "real_cases/validation_mdx_upstream.json",
                      "validation_mdx_upstream.json", None),
                     (DATA / "real_cases/family_summary.json", "family_summary.json", None)],
        },
    }
    for name, spec in gen_specs.items():
        dst = OUT / name
        n = 0
        for src, rel, _ in spec.get("copy", []):
            src = Path(src)
            if not src.exists():
                continue
            target = dst / rel
            if src.is_dir():
                n += copy_tree(src, target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
                n += 1
        wd_spec = spec.get("workdirs")
        if wd_spec:
            root, pattern = wd_spec
            for workdir in sorted(Path(root).glob(pattern)):
                n += archive_workdir(workdir, dst / "mascaret_runs" / workdir.name)
        manifest["items"][name] = {"role": spec["role"], "files": n}
        print(f"[ok] {name}: {n} files")

    # 3. training results --------------------------------------------------
    runs_dst = OUT / "runs"
    n = 0
    if (REPO / "runs").exists():
        for run_dir in sorted((REPO / "runs").iterdir()):
            if not run_dir.is_dir():
                continue
            n += copy_tree(run_dir, runs_dst / run_dir.name)
    manifest["items"]["runs"] = {
        "role": "training/evaluation results (configs, history, metrics, checkpoints)",
        "files": n,
    }
    print(f"[ok] runs: {n} files")

    # 4. manifest -----------------------------------------------------------
    if args.hash:
        print("hashing (this can take a while for the 2 GB raw datasets) ...")
        for root, _, files in OUT.walk():
            for f in files:
                p = Path(root) / f
                rel = str(p.relative_to(OUT))
                manifest["items"].setdefault("_sha256", {})[rel] = {
                    "sha256": sha256(p), "bytes": p.stat().st_size,
                }
    manifest["totals"] = {
        "files": sum(v.get("files", 0) for k, v in manifest["items"].items()
                     if not k.startswith("_")),
        "bytes": sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()),
    }
    (OUT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"manifest -> {OUT / 'MANIFEST.json'} "
          f"({manifest['totals']['files']} files, "
          f"{manifest['totals']['bytes'] / 1e9:.2f} GB)")


if __name__ == "__main__":
    main()
