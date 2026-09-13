#!/usr/bin/env python
"""Archive every dataset needed for reproducibility into ``datasets/``.

Layout (see datasets/README.md):

    datasets/
    ├── telemac-mascaret-v8p4r0/   self-contained docker build context (solver tree + Dockerfile + dependencies)
    ├── docker_images/             prebuilt solver images, docker-loadable (.tar.gz)
    ├── swegnn-official/           official SWE-GNN code + raw datasets (130 sims)
    ├── real_projects/             raw schinta basin templates (1D x5, 2D x2)
    ├── partA_synthetic/           generated scenario family (50 npz + splits)
    ├── partA_v2/                  paper-protocol family (130 npz, Mascaret full-SWE truth)
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
    "real_sources": {
        "origin": REPO / "data" / "real_sources",
        "origin_label": "data/real_sources (repo working copy)",
        "role": "Complete second-provider 1D projects vendored into the repo "
                "(wqh + zxh): launcher files, Abaques, historical .opt/.lis — "
                "both validated by exact rerun reproduction (RMSE=0)",
        "subdirs": ["wqh", "zxh"],
        "files": [],
    },
}

# Items vendored under datasets/ with no local staging copy any more: the
# tree in datasets/ IS the canonical copy (kernel patches are applied in
# place — see telemac-mascaret-v8p4r0/PATCHES.md). The archiver only counts
# their files into MANIFEST.json, it never re-copies them.
IN_PLACE = {
    "swegnn-official": {
        "origin": "github RBTV1/SWE-GNN-paper-repository- + Zenodo 10214840/7764418",
        "role": "Official SWE-GNN repository (RBTV1/SWE-GNN-paper-repository-) incl. raw_datasets (130 Delft3D-FM simulations)",
    },
    "real_projects": {
        "origin": "schinta basin-flood-prevention subsystem (internal project; path not vendored)"
                  r"\schinta-module-basin-flood-prevention-start\src\main\resources\template",
        "role": "Raw real-basin Mascaret / TELEMAC-2D project templates (mdx/wqh/zxh 1D, "
                "mdxUpStream/mdxDownStream coupled legs, wqh/mdx 2D)",
    },
    "telemac-mascaret-v8p4r0": {
        "origin": "TELEMAC-MASCARET v8p4r0 release tree (sources/ vendored; examples/notebooks/builds pruned)",
        "role": "TELEMAC-MASCARET v8p4r0 self-contained docker build context: "
                "solver source tree (examples/notebooks/builds excluded — not "
                "needed by compile_telemac) + Dockerfile + build scripts + "
                "dependencies (JDK 8, timezone). Carries the Flow-MDK kernel "
                "patches (see PATCHES.md there). docker build directly from "
                "this directory after loading the base image "
                "(datasets/docker_images/telemac-debian_0.1.tar.gz)",
    },
    "docker_images": {
        "origin": "local docker (docker save); telemac-debian base image from the upstream tar distribution",
        "role": "Prebuilt solver docker images, docker-loadable tar.gz: "
                "telemac-debian_0.1 (base) + flow-mdk-telemac_v8p4r0 (original) "
                "+ flow-mdk-telemac_v8p4r0p1 (patched kernel — the standard for "
                "all truth generation)",
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
                      "repo": "Flow-MDK repository root", "items": {}}

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
        for rel, src in spec.get("extra_dirs", {}).items():
            src = Path(src)
            if src.exists():
                n += copy_tree(src, dst / rel)
        manifest["items"][name] = {"role": spec["role"],
                                   "origin": spec.get("origin_label", str(origin)),
                                   "files": n}
        print(f"[ok] {name}: {n} files")

    # 1b. items maintained in place under datasets/ -------------------------
    for name, spec in IN_PLACE.items():
        dst = OUT / name
        n = sum(1 for p in dst.rglob("*") if p.is_file())
        if n == 0:
            print(f"[warn] {name}: 0 files — is the LFS checkout complete?")
        manifest["items"][name] = {"role": spec["role"], "origin": spec["origin"],
                                   "files": n}
        print(f"[in-place] {name}: {n} files")

    # 2. generated datasets ------------------------------------------------
    gen_specs = {
        "partA_synthetic": {
            "role": "Part A: synthetic 1D scenario family (SWE-GNN-style), "
                    "diffusive-wave reference truth",
            "copy": [(DATA / "scenarios_1d", ".", None)],
        },
        "partA_v2": {
            "role": "Part A v2: paper-protocol synthetic family (A1 100 + A2 20 "
                    "unseen hydrology + A3 10 large-domain), Mascaret full-SWE "
                    "truth attached (128/130 valid; split.json filtered, original "
                    "130-scenario protocol kept in split_full_protocol.json; the "
                    "4 s1geo-failure scenarios keep their diffusive reference)",
            "copy": [(DATA / "scenarios_partA_v2", ".", None)],
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
                     (DATA / "real_cases/validation_wqh.json", "validation_wqh.json", None),
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
            if run_dir.is_file():
                # top-level files: the results registry (runs/results.csv)
                shutil.copy2(run_dir, runs_dst / run_dir.name)
                n += 1
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
