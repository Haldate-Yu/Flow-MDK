#!/usr/bin/env python
"""Import the real-basin Mascaret / TELEMAC-2D projects into Flow-MDK.

Real-case track (plan/PLAN.md 真实案例轨道). The source projects live in the
schinta basin-flood-prevention subsystem:

    <source>/telemac1d/{mdx,wqh,zxh}              single-basin 1D models
    <source>/telemac1d/{mdxUpStream,mdxDownStream}  coupled-case 1D legs
    <source>/telemac2d/{wqh,mdx}                  2D models (mdx = coupled)

This script reads them **in place** (raw files never enter the git repo) and
writes into ``data/real_cases/`` (git-ignored):

- ``inventory.json``          scale / BC / kernel metadata for every case
- ``scenarios_1d/<case>.npz`` 1D scenarios in the Flow-MDK schema, with REAL
                              ground truth parsed from the existing ``.opt``
                              (Optyca) result files
- ``meshes_2d/<case>.npz``    2D mesh graphs (dual graph from the triangle
                              connectivity; ground truth pending a solver run)

Usage
-----
    python scripts/import_real_cases.py --out data/real_cases
    python scripts/import_real_cases.py --source <path> --only mdx wqh
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flow_mdk.data.graph_1d import build_1d_graph  # noqa: E402
from flow_mdk.data.features import layouts_1d  # noqa: E402
from flow_mdk.utils.io import Scenario, save_scenario  # noqa: E402

DEFAULT_SOURCE = (
    r"D:\Projects\wzzhsl-rest-subsystems-xd\schinta-module-basin-flood-prevention"
    r"\schinta-module-basin-flood-prevention-start\src\main\resources\template"
)

CASES_1D = {
    # case name: (directory, geometry stem, role in the real-case track)
    # relative paths resolve under --source; absolute paths are used as-is;
    # wqh/zxh use the complete second-provider copies vendored into the repo
    # (data/real_sources/, resolved relative to the repository root)
    "mdx": ("telemac1d/mdx", "mdx", "single-basin 1D (考卷+母版)"),
    "wqh": ("data/real_sources/wqh", "wuqiao",
            "single-basin 1D — complete second-provider project (historical .opt, "
            "exact rerun reproduction); supersedes the incomplete template"),
    "zxh": ("data/real_sources/zxh", "zx",
            "single-basin 1D — complete second-provider project (full-horizon .opt, "
            "25 frames); supersedes the truncated-template copy"),
    "mdx_upstream": ("telemac1d/mdxUpStream", "ybs", "coupled 1D upstream leg"),
    "mdx_downstream": ("telemac1d/mdxDownStream", "xjz", "coupled 1D downstream leg"),
}
CASES_2D = {
    "wqh_2d": ("telemac2d/wqh", "wqh", "single-basin 2D"),
    "mdx_2d": ("telemac2d/mdx", "geo", "coupled 2D reach (mdxUpStream -> 2D -> mdxDownStream)"),
}


# --------------------------------------------------------------------- #
# Mascaret 1D parsing
# --------------------------------------------------------------------- #
def parse_geo(path: Path) -> list[dict]:
    """Parse a Mascaret .geo file into profiles.

    Point lines are ``X(transverse) Z(elevation) marker``; verified against
    the ZREF column of the companion .opt file.
    """
    profiles = []
    current = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("PROFIL"):
            parts = line.split()
            current = {
                "branch": parts[1], "name": parts[2],
                "abscissa": float(parts[3]), "x": [], "z": [],
            }
            profiles.append(current)
        elif current is not None and not line.startswith("#"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    current["x"].append(float(parts[0]))
                    current["z"].append(float(parts[1]))
                except ValueError:
                    pass
    for p in profiles:
        p["x"] = np.asarray(p["x"])
        p["z"] = np.asarray(p["z"])
        p["bed"] = float(p["z"].min())
        p["width"] = float(p["x"].max() - p["x"].min())
    return profiles


def parse_xcas(path: Path) -> dict:
    """Extract the steering metadata we need from a .xcas (ISO-8859-1 XML)."""
    text = path.read_text(encoding="ISO-8859-1", errors="replace")
    # Mascaret .xcas files are not always well-formed XML; pull fields by regex
    def grab(tag: str) -> str | None:
        m = re.search(rf"<{tag}>([^<]+)</{tag}>", text)
        return m.group(1).strip() if m else None

    out = {
        "kernel_code": grab("code"),
        "dt_s": grab("pasTemps"),
        "temps_max_s": grab("tempsMax"),
        "geo_file": grab("fichier"),
        "coef_lit_min": grab("coefLitMin"),
        "coef_lit_maj": grab("coefLitMaj"),
    }
    laws = re.findall(
        r"<structureParametresLoi>.*?<nom>([^<]+)</nom>.*?<type>(\d+)</type>"
        r".*?<fichier>([^<]+)</fichier>",
        text, re.S,
    )
    out["laws"] = [
        {"name": n, "type": int(t), "file": f.strip()} for n, t, f in laws
    ]
    return out


LAW_KINDS = {
    1: "hydrogramme_Q_t",
    2: "limnigramme_Z_t",
    3: "limni_2",
    4: "hydrogramme_Z",
    5: "Q_Z_ordinal",
    6: "Q_Z",
    7: "Z_Q",
    8: "tarage",
}


def parse_loi(path: Path) -> dict:
    """Boundary law: header comments declare the columns."""
    lines = path.read_text(encoding="ISO-8859-1", errors="replace").splitlines()
    name = next((l[2:].strip() for l in lines if l.startswith("# ")), path.stem)
    columns = next(
        (l[2:].strip() for l in lines if l.lower().startswith("# temps")),
        "",
    )
    return {"name": name, "columns": columns, "n_lines": len(lines)}


def parse_opthyca(path: Path) -> dict:
    """Parse a Mascaret Optyca ``.opt`` result file.

    Returns {"variables": [codes], "times": [...], "branch": [...],
    "section": [...], "data": [T, N, V] array aligned with the variable list}.
    """
    text = path.read_text(encoding="ISO-8859-1", errors="replace")
    variables, rows = [], []
    in_results = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("["):
            in_results = line == "[resultats]"
            continue
        if not in_results:
            parts = [p.strip().strip('"') for p in line.split(";")]
            if len(parts) >= 2:
                variables.append(parts[1])
            continue
        parts = [p.strip().strip('"') for p in line.split(";")]
        if len(parts) < 4:
            continue
        try:
            rows.append([float(p) for p in parts])
        except ValueError:
            continue

    rows = np.asarray(rows)
    # row layout: t ; branch ; section ; abscissa ; <variables...>
    times, branch, section, absc, data = (
        rows[:, 0], rows[:, 1], rows[:, 2], rows[:, 3], rows[:, 4:],
    )
    uniq_t = np.unique(times)
    uniq_s = np.unique(section)
    grid = np.full((uniq_t.size, uniq_s.size, len(variables)), np.nan)
    t_index = {t: i for i, t in enumerate(uniq_t)}
    s_index = {s: i for i, s in enumerate(uniq_s)}
    for r, t, b, s in zip(data, times, branch, section):
        grid[t_index[t], s_index[s], :] = r
    absc_grid = np.full((uniq_t.size, uniq_s.size), np.nan)
    for a, t, s in zip(absc, times, section):
        absc_grid[t_index[t], s_index[s]] = a
    return {
        "variables": variables, "times": uniq_t, "branches": np.unique(branch),
        "sections": uniq_s, "data": grid, "abscissa": absc_grid,
    }


def import_1d_case(case: str, folder: Path, stem: str, out_dir: Path) -> dict:
    geo = parse_geo(folder / f"{stem}.geo")
    xcas = parse_xcas(folder / f"{stem}.xcas")

    # order profiles by abscissa (single-branch models in this track)
    geo = sorted(geo, key=lambda p: p["abscissa"])
    n = len(geo)
    x = np.asarray([p["abscissa"] for p in geo])
    z = np.asarray([p["bed"] for p in geo])
    width = np.asarray([p["width"] for p in geo])
    strickler = float(xcas.get("coef_lit_min") or 30.0)

    edge_index, edge_attr = build_1d_graph(x, z, width)
    boundary_flag = np.zeros(n)
    boundary_flag[0], boundary_flag[-1] = 1.0, 2.0
    node_static = np.stack([z, width, np.full(n, strickler), boundary_flag], axis=1)

    entry = {
        "case": case, "kind": "1d", "folder": str(folder), "stem": stem,
        "num_sections": n, "reach_length_m": float(x[-1] - x[0]) if n else 0.0,
        "dt_s": xcas.get("dt_s"), "temps_max_s": xcas.get("temps_max_s"),
        "kernel_code": xcas.get("kernel_code"),
        "strickler_minor": xcas.get("coef_lit_min"),
        "laws": [
            {**parse_loi(folder / l["file"]), "xcas_type": l["type"],
             "kind": LAW_KINDS.get(l["type"], f"type{l['type']}")}
            for l in xcas["laws"] if (folder / l["file"]).exists()
        ],
        "has_gate_file": (folder / "GATE.txt").exists(),
        "has_opt_results": (folder / f"{stem}.opt").exists(),
        "profile_names_local": [p["name"] for p in geo],  # git-ignored inventory
    }

    opt_path = folder / f"{stem}.opt"
    if opt_path.exists():
        opt = parse_opthyca(opt_path)
        # The .opt reports results at PLANIMETRED MESH sections (often far
        # more numerous than the surveyed profiles). Map each .geo profile
        # onto the nearest mesh section by abscissa, and keep only those
        # columns so truth aligns with node_static.
        sec_absc = np.nan_to_num(opt["abscissa"], nan=np.inf).min(axis=0)
        sec_absc = np.where(np.isfinite(sec_absc), sec_absc, np.nan)
        valid = np.isfinite(sec_absc)
        sel = []
        for xv in x:
            j = int(np.nanargmin(np.where(valid, np.abs(sec_absc - xv), np.inf)))
            sel.append(j)
        sel = np.asarray(sel)
        mis = float(np.max(np.abs(sec_absc[sel] - x)))
        if mis > 1.0:
            print(f"  [warn] {case}: profile/mesh-section abscissa mismatch {mis:.2f} m")
        entry["opt_mesh_sections"] = int(valid.sum())
        entry["opt_geo_abscissa_max_diff_m"] = mis
        vi = {v: i for i, v in enumerate(opt["variables"])}
        depth_all = opt["data"][:, :, vi["Y"]]  # water depth [T, S_mesh]
        q_all = opt["data"][:, :, vi["Q"]]  # total discharge [T, S_mesh]
        depth, q = depth_all[:, sel], q_all[:, sel]
        times = opt["times"]

        # subsample by TIME to >= 10-minute frames, never below the raw
        # storage cadence (the .opt only stores every pasStockage seconds)
        raw_step = float(np.median(np.diff(times))) if times.size > 1 else 1.0
        period = max(600.0, raw_step)
        idx = [0]
        for i in range(1, times.size):
            if times[i] - times[idx[-1]] >= period - 1e-6:
                idx.append(i)
        idx = np.asarray(idx)
        dynamic = np.stack([depth[idx], q[idx]], axis=-1).astype(np.float32)
        wet = (dynamic[..., 0] > 1e-3).astype(np.uint8)
        times_out = times[idx]

        scenario = Scenario(
            name=case,
            node_static=node_static.astype(np.float32),
            edge_index=edge_index,
            edge_attr=edge_attr,
            dynamic=dynamic,
            wet=wet,
            times=times_out.astype(np.float64),
            meta={
                "layout": layouts_1d.name,
                "dynamic_vars": list(layouts_1d.dynamic_names),
                "elevation_feature_idx": layouts_1d.elevation_feature_idx,
                "solver": "mascaret_opt_replay",
                "source": str(folder),
                "runtime_s": None,  # real runtime not stored; from .lis in M1
                "origin": {"kernel": xcas.get("kernel_code"),
                           "dt_s": xcas.get("dt_s"),
                           "storage_period_s": raw_step,
                           "output_period_s": period},
                "boundary": {"upstream": "inflow_hydrograph",
                             "downstream": "Q_Z_rating"},
            },
        )
        out_path = save_scenario(scenario, out_dir / "scenarios_1d" / f"{case}.npz")
        entry["npz"] = str(out_path)
        entry["npz_frames"] = int(dynamic.shape[0])
        entry["depth_max_m"] = float(np.nanmax(dynamic[..., 0]))
        entry["q_max_m3s"] = float(np.nanmax(dynamic[..., 1]))
        entry["nan_fraction"] = float(np.isnan(dynamic).mean())
    else:
        # no stored results in the template: geometry-only scenario, truth
        # pending a Mascaret re-run (复算校验 step of the admission checklist)
        num_frames = 2
        scenario = Scenario(
            name=case,
            node_static=node_static.astype(np.float32),
            edge_index=edge_index,
            edge_attr=edge_attr,
            dynamic=np.zeros((num_frames, n, 2), dtype=np.float32),
            wet=np.zeros((num_frames, n), dtype=np.uint8),
            times=np.zeros(num_frames),
            meta={
                "layout": layouts_1d.name,
                "dynamic_vars": list(layouts_1d.dynamic_names),
                "elevation_feature_idx": layouts_1d.elevation_feature_idx,
                "solver": "pending_mascaret_rerun",
                "source": str(folder),
                "origin": {"kernel": xcas.get("kernel_code"), "dt_s": xcas.get("dt_s")},
            },
        )
        out_path = save_scenario(scenario, out_dir / "scenarios_1d" / f"{case}.npz")
        entry["npz"] = str(out_path)
        entry["npz_frames"] = 0
    return entry


# --------------------------------------------------------------------- #
# TELEMAC-2D parsing
# --------------------------------------------------------------------- #
def parse_cas(path: Path) -> dict:
    keys = {}
    for line in path.read_text(encoding="ISO-8859-1", errors="replace").splitlines():
        line = line.split("/")[0]
        if "=" in line and ":" not in line.split("=")[0]:
            k, _, v = line.partition("=")
            keys[k.strip().upper()] = v.strip().strip("'")
    return keys


def parse_cli(path: Path) -> dict:
    """Boundary conditions file: count liquid boundary node types."""
    n_lines, liquid = 0, {}
    for line in path.read_text(encoding="ISO-8859-1", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            n_lines += 1
            lihbor = parts[1]
            liquid[lihbor] = liquid.get(lihbor, 0) + 1
    return {"boundary_nodes": n_lines, "lihbor_counts": liquid}


def import_2d_case(case: str, folder: Path, geo_stem: str, cas_stem: Path | None,
                   out_dir: Path) -> dict:
    from selafin import Selafin

    geo_path = folder / f"{geo_stem}.slf"
    slf = Selafin(geo_path)
    ikle0 = slf.ikle - 1  # 0-based connectivity

    # dual graph from the triangle mesh: unique undirected edges -> both arcs
    edges = set()
    for tri in ikle0:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            i, j = int(tri[a]), int(tri[b])
            edges.add((min(i, j), max(i, j)))
    src, dst = [], []
    for i, j in sorted(edges):
        src += [i, j]
        dst += [j, i]
    edge_index = np.stack([src, dst]).astype(np.int64)

    # edge geometry: outward unit normal + shared-side length
    pts = np.stack([slf.x, slf.y], axis=1)
    i0, i1 = np.asarray([e[0] for e in sorted(edges)]), np.asarray([e[1] for e in sorted(edges)])
    vec = pts[i1] - pts[i0]
    length = np.linalg.norm(vec, axis=1)
    normal = vec / np.maximum(length, 1e-12)[:, None]
    edge_attr = np.concatenate(
        [np.stack([normal, -normal], axis=1).reshape(-1, 2),
         np.repeat(length, 2)[:, None]], axis=1
    ).astype(np.float32)

    # node statics: area (1/3 of adjacent triangle areas), elevation, friction
    tri_pts = pts[ikle0]
    cross2d = (
        (tri_pts[:, 1, 0] - tri_pts[:, 0, 0]) * (tri_pts[:, 2, 1] - tri_pts[:, 0, 1])
        - (tri_pts[:, 2, 0] - tri_pts[:, 0, 0]) * (tri_pts[:, 1, 1] - tri_pts[:, 0, 1])
    )
    cross = np.abs(cross2d) / 2.0  # triangle areas
    area = np.zeros(slf.npoin)
    for k in range(3):
        np.add.at(area, ikle0[:, k], cross / 3.0)
    bottom = slf.read_all()[slf.variables[0]][0]
    friction = slf.read_all()[slf.variables[1]][0]
    static = np.stack([area, bottom, friction], axis=1).astype(np.float32)

    n_frames = None
    truth = None
    entry = {
        "case": case, "kind": "2d", "folder": str(folder),
        "num_nodes": int(slf.npoin), "num_elements": int(slf.nelem),
        "num_arcs": int(edge_index.shape[1]),
        "extent": [float(slf.x.min()), float(slf.x.max()),
                   float(slf.y.min()), float(slf.y.max())],
        "geo_variables": slf.variables,
        "boundary": parse_cli(folder / f"{Path(cas_stem).stem}_BC.cli") if cas_stem and (folder / f"{Path(cas_stem).stem}_BC.cli").exists() else None,
    }
    if cas_stem and (folder / cas_stem).exists():
        cas = parse_cas(folder / cas_stem)
        entry["cas"] = {
            k: cas.get(k) for k in (
                "TIME STEP", "NUMBER OF TIME STEPS", "LAW OF BOTTOM FRICTION",
                "FRICTION COEFFICIENT", "PRESCRIBED ELEVATIONS",
                "PRESCRIBED FLOWRATES", "COMPUTATION CONTINUED",
                "INITIAL DEPTH", "TIDAL FLATS",
            ) if cas.get(k) is not None
        }
        sections = folder / "sections.txt"
        if sections.exists():
            names = [
                l.split()[0] for l in sections.read_text(errors="replace").splitlines()
                if l.strip() and not l.startswith("#") and not l[0].isdigit()
            ]
            entry["control_sections"] = names

    # store mesh npz (dual graph + statics; truth pending a solver run)
    num_frames = 1
    scenario = Scenario(
        name=case,
        node_static=static,
        edge_index=edge_index,
        edge_attr=edge_attr,
        dynamic=np.zeros((num_frames, slf.npoin, 2), dtype=np.float32),
        wet=np.zeros((num_frames, slf.npoin), dtype=np.uint8),
        times=np.zeros(1),
        meta={
            "layout": "2d_mesh", "dynamic_vars": ["h", "|q|"],
            "elevation_feature_idx": 1,
            "solver": "pending_telemac2d_run",
            "source": str(folder),
            "geometry_file": str(geo_path),
            "truth": truth,
        },
    )
    out_path = save_scenario(scenario, out_dir / "meshes_2d" / f"{case}.npz")
    entry["npz"] = str(out_path)
    return entry


# --------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--out", default="data/real_cases")
    parser.add_argument("--only", nargs="*", default=None,
                        help="import a subset of cases by name")
    args = parser.parse_args()

    source = Path(args.source)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    inventory: dict[str, dict] = {"source": str(source), "cases": {}}
    for case, (rel, stem, role) in CASES_1D.items():
        if args.only and case not in args.only:
            continue
        rel_path = Path(rel)
        if rel_path.is_absolute():
            folder = rel_path
        elif rel.startswith("data/"):
            folder = Path(__file__).resolve().parents[1] / rel_path  # repo-internal
        else:
            folder = source / rel
        if not folder.exists():
            print(f"[skip] {case}: folder missing")
            continue
        entry = import_1d_case(case, folder, stem, out_dir)
        entry["role"] = role
        inventory["cases"][case] = entry
        print(
            f"[1d] {case}: {entry['num_sections']} sections, "
            f"{entry.get('npz_frames', 0)} truth frames "
            f"(depth max {entry.get('depth_max_m', float('nan')):.2f} m, "
            f"Q max {entry.get('q_max_m3s', float('nan')):.1f} m3/s)"
        )

    for case, (rel, geo_stem, role) in CASES_2D.items():
        if args.only and case not in args.only:
            continue
        folder = source / rel
        if not folder.exists():
            print(f"[skip] {case}: folder missing")
            continue
        cas_stem = next((f.name for f in folder.glob("*.cas") if not f.stem.endswith("_sorted")), None)
        entry = import_2d_case(case, folder, geo_stem, cas_stem, out_dir)
        entry["role"] = role
        inventory["cases"][case] = entry
        print(
            f"[2d] {case}: {entry['num_nodes']} nodes, {entry['num_elements']} triangles, "
            f"{entry['num_arcs']} arcs"
        )

    inventory["coupled_chain"] = {
        "name": "mdx_coupled",
        "order": ["mdx_upstream (1D)", "mdx_2d (2D)", "mdx_downstream (1D)"],
        "note": "run order 1D upstream -> 2D -> 1D downstream; handoff series "
                "(Z, Q) come from each leg's .opt at the interface sections",
    }
    inv_path = out_dir / "inventory.json"
    inv_path.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"inventory written to {inv_path}")


if __name__ == "__main__":
    main()
