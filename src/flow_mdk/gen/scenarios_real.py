"""Real-master scenario family: 真实几何 × 合成水情 (plan 真实案例轨道 角色二).

The master scenario (imported from a real Mascaret project, see
``scripts/import_real_cases.py``) contributes the *fixed* geometry (bed,
widths, reach layout, gate schedules). Two families of perturbations are
applied (plan M0/M1):

- **roughness-field perturbation**: lognormal patch scaling of the Strickler
  coefficient, optionally split into zones for the Mascaret friction block;
- **inflow-hydrograph reshaping**: magnitude scaling, time-to-peak shift and
  gamma-shape deformation of the master's upstream boundary law (extracted
  from the master's replayed ``.opt``), with optional secondary peaks.

Generated scenarios carry ``meta["solver"] = "pending_mascaret_rerun"`` plus
a ``meta["mascaret_patch"]`` block describing exactly how to materialise a
runnable Mascaret project (see ``scripts/run_real_family.py``).
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from flow_mdk.utils.io import Scenario, load_scenario, save_scenario

__all__ = ["RealFamilyParams", "generate_real_family", "materialise_mascaret_project"]


@dataclass
class RealFamilyParams:
    master: str  # scenario name inside master_root (e.g. "mdx")
    master_root: str = "data/real_cases/scenarios_1d"
    num_scenarios: int = 40
    seed: int = 7
    # roughness-field perturbation (lognormal patches on Strickler K)
    strickler_rel_std: float = 0.2
    strickler_patch_scale_m: float = 2000.0
    strickler_uniform_range: tuple[float, float] = (0.8, 1.25)
    # inflow-hydrograph reshaping
    q_scale_range: tuple[float, float] = (0.5, 2.0)
    # stretch lower-bounded at 0.8: faster floods combined with gate schedules
    # drove the Mascaret solver into non-physical states in early trials
    time_stretch_range: tuple[float, float] = (0.8, 1.6)
    secondary_peak_prob: float = 0.35
    dt_out: float = 600.0


def _perturb_strickler(k_base: np.ndarray, x: np.ndarray, params: RealFamilyParams,
                       rng: np.random.Generator) -> np.ndarray:
    """Lognormal patch scaling + uniform level shift of the Strickler field."""
    scale = rng.uniform(*params.strickler_uniform_range)
    if params.strickler_rel_std <= 0 or params.strickler_patch_scale_m <= 0:
        return k_base * scale
    centers = np.arange(0.0, x[-1] + 1.0, params.strickler_patch_scale_m)
    weights = np.exp(
        -0.5 * ((x[:, None] - centers[None, :]) / params.strickler_patch_scale_m) ** 2
    )
    weights /= weights.sum(axis=1, keepdims=True)
    factors = np.exp(rng.normal(0.0, params.strickler_rel_std, centers.size))
    return k_base * scale * np.exp(weights @ np.log(factors))


def _reshaped_hydrograph(
    t_master: np.ndarray,
    q_master: np.ndarray,
    t_out: np.ndarray,
    params: RealFamilyParams,
    rng: np.random.Generator,
) -> np.ndarray:
    """Scale / stretch / reshape the master inflow law.

    The master series is treated as the sum of gamma-shaped peaks: each peak
    is re-scaled in magnitude and stretched in time; an optional secondary
    peak is added at a random phase.
    """
    q = np.asarray(q_master, dtype=float)
    t_m = np.asarray(t_master, dtype=float)
    scale = rng.uniform(*params.q_scale_range)
    stretch = rng.uniform(*params.time_stretch_range)
    # time warp on the master grid: new(t) = master(t / stretch); stretch > 1
    # slows the flood. Beyond the master horizon the law holds the tail.
    q_out = scale * np.interp(t_m / stretch, t_m, q, left=q[0], right=q[-1])
    if rng.random() < params.secondary_peak_prob:
        peak_t = float(t_m[np.argmax(q)])
        peak_q = float(q.max())
        t_p = peak_t * rng.uniform(0.4, 0.9)
        sharp = rng.uniform(1.5, 4.0)
        secondary = (
            peak_q
            * rng.uniform(0.2, 0.6)
            * np.power(np.clip(t_m / t_p, 0.0, None) * np.exp(1.0 - t_m / t_p), sharp)
        )
        # switch the secondary peak off before the main flood arrives
        secondary *= np.clip((peak_t * 0.5 - t_m) / (peak_t * 0.5), 0.0, 1.0)
        q_out = np.maximum(q_out, secondary)
    q_out = np.maximum(q_out, 0.0)
    return np.interp(np.asarray(t_out, dtype=float), t_m, q_out)


def generate_real_family(params: RealFamilyParams, out_dir: str | Path) -> list[Scenario]:
    """Sample the family and write pending-truth npz scenarios."""
    master = load_scenario(Path(params.master_root) / f"{params.master}.npz")
    if master.meta.get("solver") not in ("mascaret_opt_replay", "mascaret_docker_rerun"):
        raise ValueError(
            f"master {params.master} has no replayed truth; run the import/rerun first"
        )
    rng = np.random.default_rng(params.seed)

    z = master.node_static[:, 0]
    width = master.node_static[:, 1]
    k_base = master.node_static[:, 2]
    boundary = master.node_static[:, 3]
    edge_index, edge_attr = master.edge_index, master.edge_attr
    x = np.concatenate([[0.0], np.cumsum(edge_attr[0::2, 0])])

    # master inflow law from the replayed boundary node; the perturbed law
    # must cover the FULL simulation horizon declared in the master .xcas
    # (a law shorter than tempsMax aborts the Mascaret run)
    t_master = master.times
    q_master = master.dynamic[:, 0, 1]
    t_max = float(t_master[-1])
    sim_horizon = t_max
    xcas = next(
        (p for p in Path(master.meta.get("source", "")).glob("*.xcas")
         if not p.name.endswith(".ftl")),
        None,
    )
    if xcas is not None:
        m = re.search(r"<tempsMax>([^<]+)</tempsMax>", xcas.read_text(encoding="ISO-8859-1",
                                                                   errors="replace"))
        if m:
            sim_horizon = max(t_max, float(m.group(1)))

    out = Path(out_dir) / f"family_{params.master}"
    scenarios = []
    for i in range(params.num_scenarios):
        k_field = _perturb_strickler(k_base, x, params, rng)
        t_fine = np.arange(0.0, sim_horizon + 1e-9, params.dt_out)
        q_in = _reshaped_hydrograph(t_master, q_master, t_fine, params, rng)
        frame_idx = np.searchsorted(t_master, t_fine)
        frame_idx = np.clip(frame_idx, 0, master.num_steps - 1)
        # truth pending: reuse the master's dynamics as a placeholder shape
        dynamic = master.dynamic[frame_idx].astype(np.float32).copy()
        dynamic[:, 0, 1] = q_in.astype(np.float32)  # upstream law visible in data

        # every scenario samples its own scale/stretch; the SAME factors are
        # applied to ALL type-1 inflow laws (upstream + lateral singularities)
        # so the hydrological event stays coherent across the basin
        q_scale = float(rng.uniform(*params.q_scale_range))
        time_stretch = float(rng.uniform(*params.time_stretch_range))

        static = np.stack([z, width, k_field, boundary], axis=1).astype(np.float32)
        scenario = Scenario(
            name=f"{params.master}_fam{i:03d}",
            node_static=static,
            edge_index=edge_index,
            edge_attr=edge_attr,
            dynamic=dynamic,
            wet=master.wet[frame_idx].copy(),
            times=t_fine,
            meta={
                "layout": master.meta["layout"],
                "dynamic_vars": master.meta["dynamic_vars"],
                "elevation_feature_idx": master.meta["elevation_feature_idx"],
                "solver": "pending_mascaret_rerun",
                "master": params.master,
                "family": {
                    "seed": int(params.seed),
                    "index": i,
                    "q_scale": q_scale,
                    "time_stretch": time_stretch,
                    "strickler_field": k_field.tolist(),
                },
                "mascaret_patch": {
                    "master_project": str(master.meta.get("source", "")),
                    "master_stem": _master_stem(master),
                    "q_scale": q_scale,
                    "time_stretch": time_stretch,
                    "sim_horizon_s": sim_horizon,
                    "strickler_x_m": x.tolist(),
                    "strickler_k": k_field.tolist(),
                },
            },
        )
        path = save_scenario(scenario, out / f"{scenario.name}.npz")
        scenarios.append(scenario)
    return scenarios


def _master_stem(master: Scenario) -> str:
    """Mascaret file stem of the master project (from import metadata)."""
    source = master.meta.get("source", "")
    geo = Path(source) / "*.geo"
    # import stored the source folder; the stem equals the folder's xcas name
    candidates = list(Path(source).glob("*.xcas"))
    candidates = [c for c in candidates if not c.name.endswith(".ftl")]
    if candidates:
        return candidates[0].stem
    raise FileNotFoundError(f"no .xcas under {source} ({geo})")


# --------------------------------------------------------------------- #
# Mascaret project materialisation (used by scripts/run_real_family.py)
# --------------------------------------------------------------------- #
def _patch_xcas_friction(xcas_path: Path, x: np.ndarray, k_field: np.ndarray) -> None:
    """Rewrite the ``parametresCalage`` friction block with per-segment zones.

    Multi-zone blocks list the per-zone values space-separated inside each
    tag (see examples/mascaret/Test15), NOT as repeated blocks.
    """
    n_zones = min(8, max(1, x.size // 8))
    edges = np.linspace(0, x[-1], n_zones + 1)
    # the npz abscissas come from float32 edge accumulation and can overshoot
    # the branch end declared in the .xcas by rounding (~1 mm) — Mascaret
    # rejects zones outside the reach, so clamp to the declared abscFin
    xcas_text = xcas_path.read_text(encoding="ISO-8859-1", errors="replace")
    m_abs = re.search(r"<abscFin>([^<]+)</abscFin>", xcas_text)
    if m_abs:
        edges = np.clip(edges, 0.0, float(m_abs.group(1)))
        edges[-1] = float(m_abs.group(1))
    k_zones = [
        float(np.mean(k_field[(x >= edges[i]) & (x <= edges[i + 1])]))
        for i in range(n_zones)
    ]

    def join(values) -> str:
        return " ".join(f"{v:.3f}" for v in values)

    replacement = (
        "<frottement>\n"
        "        <loi>1</loi>\n"
        f"        <nbZone>{n_zones}</nbZone>\n"
        f"        <numBranche>{' '.join(['1'] * n_zones)}</numBranche>\n"
        f"        <absDebZone>{join(edges[:-1])}</absDebZone>\n"
        f"        <absFinZone>{join(edges[1:])}</absFinZone>\n"
        f"        <coefLitMin>{join(k_zones)}</coefLitMin>\n"
        f"        <coefLitMaj>{join(k_zones)}</coefLitMaj>\n"
        "      </frottement>"
    )
    text = xcas_path.read_text(encoding="ISO-8859-1", errors="replace")
    pattern = re.compile(r"<frottement>.*?</frottement>", re.S)
    text, n = pattern.subn(replacement, text, count=1)
    if n != 1:
        raise RuntimeError(f"friction block not found in {xcas_path}")
    xcas_path.write_text(text, encoding="ISO-8859-1")



def _patch_all_inflow_laws(folder: Path, stem: str, patch: dict) -> list[str]:
    """Rescale + time-warp EVERY hydrogramme law of the project.

    Real basins carry several inflow singularities (upstream + laterals,
    historically rendered from XAJ hydrology); applying one shared
    (scale, stretch) pair keeps the event coherent across the basin.
    Returns the list of rewritten law files.
    """
    xcas = folder / f"{stem}.xcas"
    text = xcas.read_text(encoding="ISO-8859-1", errors="replace")
    laws = re.findall(
        r"<structureParametresLoi>.*?<nom>([^<]+)</nom>.*?<type>(\d+)</type>"
        r".*?<fichier>([^<]+)</fichier>",
        text, re.S,
    )
    inflow = [f.strip() for n, t, f in laws if int(t) == 1]
    if not inflow:
        raise RuntimeError(f"no hydrogramme law found in {xcas}")
    scale = float(patch["q_scale"])
    stretch = float(patch["time_stretch"])
    horizon = float(patch["sim_horizon_s"])
    touched = []
    for name in inflow:
        law_path = folder / name
        t_old, q_old = _read_law_series(law_path)
        # identical transformation on every inflow law keeps the basin-wide
        # hydrological event coherent (upstream + lateral singularities)
        dt_law = max(float(np.median(np.diff(t_old))) if t_old.size > 1 else 600.0, 1.0)
        t_new = np.arange(0.0, horizon + 1e-9, dt_law)
        # the law MUST reach the simulation horizon (Mascaret aborts otherwise)
        if t_new[-1] < horizon - 1e-6:
            t_new = np.append(t_new, horizon)
        q_new = scale * np.interp(t_new / stretch, t_old, q_old,
                                  left=q_old[0], right=q_old[-1])
        rows = "\n".join(f"{t:.1f} {v:.4f}" for t, v in zip(t_new, q_new))
        law_path.write_text(
            f"# perturbed inflow (Flow-MDK real-master family, "
            f"scale={scale:.3f}, stretch={stretch:.3f})\n"
            f"# Temps (s) Debit\n         S\n{rows}\n",
            encoding="ISO-8859-1",
        )
        touched.append(name)
    return touched


def _read_law_series(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read a Q(t) law file: rows after the 'S' marker are ``t q``."""
    times, values = [], []
    started = False
    for line in path.read_text(encoding="ISO-8859-1", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("S"):
            started = True
            continue
        if not started:
            continue
        parts = s.split()
        if len(parts) >= 2:
            try:
                times.append(float(parts[0]))
                values.append(float(parts[1]))
            except ValueError:
                continue
    if not times:
        raise RuntimeError(f"no series found in law file {path}")
    return np.asarray(times), np.asarray(values)


def materialise_mascaret_project(scenario: Scenario, workdir: Path) -> Path:
    """Copy the master project into ``workdir`` and apply the family patch."""
    patch = scenario.meta["mascaret_patch"]
    master_dir = Path(patch["master_project"])
    stem = patch["master_stem"]
    if workdir.exists():
        shutil.rmtree(workdir)
    shutil.copytree(master_dir, workdir, ignore=shutil.ignore_patterns("*.opt", "*.lis"))
    _patch_xcas_friction(workdir / f"{stem}.xcas", np.asarray(patch["strickler_x_m"]),
                         np.asarray(patch["strickler_k"]))
    _patch_all_inflow_laws(workdir, stem, patch)
    return workdir / f"{stem}.xcas"
