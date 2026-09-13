# Datasets / 数据归档

Everything needed to reproduce the Flow-MDK experiments, archived in one
place and ready for Git LFS sync (patterns in `.gitattributes`; run
`scripts/archive_datasets.py` to refresh). Per-file provenance and sizes:
`MANIFEST.json` (add `--hash` for sha256).

| directory | content | origin | size |
|---|---|---|---|
| `telemac-mascaret-v8p4r0/` | **self-contained docker build context**: solver source tree (`telemac-mascaret/`, examples/notebooks/builds excluded) + `Dockerfile` + build scripts + `dependencies/` (JDK 8, timezone) at context root. The source carries the Flow-MDK kernel patches — see `PATCHES.md` in that directory | TELEMAC-MASCARET v8p4r0 release tree | ~460 MB |
| `docker_images/` | prebuilt solver images (`docker load < *.tar.gz`): `telemac-debian_0.1` (base, needed before building the context) + `flow-mdk-telemac_v8p4r0` (original) + `flow-mdk-telemac_v8p4r0p1` (**patched kernel — the standard for all truth generation**) | local docker (`docker save`) | ~3.9 GB |
| `swegnn-official/` | official SWE-GNN repo (RBTV1/SWE-GNN-paper-repository-) **incl. `raw_datasets/`** — 130 Delft3D-FM simulations used in the SWE-GNN paper | github / Zenodo 10214840 + 7764418 | ~2 GB |
| `real_projects/` | raw real-basin project templates: `telemac1d/{mdx,wqh,zxh,mdxUpStream,mdxDownStream}`, `telemac2d/{wqh,mdx}` (import fallback: `scripts/import_real_cases.py --source datasets/real_projects`) | schinta basin-flood-prevention subsystem (internal; path not vendored) | ~61 MB |
| `real_sources/` | complete second-provider 1D projects (`wqh/`, `zxh/`) with launch files, Abaques and historical `.opt`/`.lis` — the templates all synthetic-project generation starts from (restore into `data/real_sources/`) | second provider, vendored at import time | ~5 MB |
| `partA_synthetic/` | 50 generated 1D scenarios (`*.npz`) + `split.json` + `stats.json` — geometry × hydrology random family, diffusive-wave reference truth (v1 pipeline-regression set) | `scripts/generate_scenarios_1d.py` | ~10 MB |
| `partA_v2/` | 130 paper-protocol scenarios (A1 100 + A2 unseen-hydrology 20 + A3 large-domain 10), Mascaret full-SWE truth attached on 128/130 (`split.json` filtered to the valid set; original 130-scenario protocol kept in `split_full_protocol.json`; the 4 `s1geo`-failure scenarios keep their diffusive reference) | `scripts/generate_partA_v2.py` + `scripts/run_partA_mascaret.py` | ~5 MB |
| `partB_family_mdx/` | 37 real-master scenarios (mdx geometry × synthetic hydrology) + splits + `mascaret_runs/` (per-scenario workdirs with `.opt` results; `.lis` listings excluded as regenerable) | `flow_mdk/gen/scenarios_real.py` + `scripts/run_real_family.py` | ~0.6 GB |
| `partB_family_zxh/` | 40 real-master scenarios (zxh geometry, rebuilt from the complete vendored master), same pipeline | idem | ~0.3 GB |
| `partB_real_cases/` | imported real cases (`scenarios_1d/*.npz`), 2D meshes (`meshes_2d/*.npz`), `inventory.json`, validation reports | `scripts/import_real_cases.py` | ~10 MB |
| `runs/` | training/evaluation results: `config.yaml`, `history.json`, `best.pt`, `eval_*.json` per experiment; `results.csv` = append-only registry of every run | `scripts/train.py` / `scripts/evaluate.py` | small |

> **Archive state (2026-09-13)**: refreshed — `partA_v2/` and the L2/L3 run
> archive are in, `docker_images/` carries the patched `v8p4r0p1` image, and
> the v1 run dirs hold the final (post-training) checkpoints.
> `telemac-mascaret-v8p4r0/` and `docker_images/` are maintained in place
> (kernel patches are applied directly to the vendored tree, see
> `telemac-mascaret-v8p4r0/PATCHES.md`): re-running
> `python scripts/archive_datasets.py` counts them into `MANIFEST.json` but
> never re-copies them.

Reproduction chain:

```bash
# solver — either load the prebuilt images (recommended):
docker load < datasets/docker_images/telemac-debian_0.1.tar.gz
docker load < datasets/docker_images/flow-mdk-telemac_v8p4r0p1.tar.gz
#   ...or load the base image only and rebuild the patched solver image from
#   the self-contained context (Dockerfile expects ./telemac-mascaret +
#   ./dependencies):
docker load < datasets/docker_images/telemac-debian_0.1.tar.gz
docker build -t flow-mdk-telemac:v8p4r0p1 datasets/telemac-mascaret-v8p4r0/   # ~20-40 min

# Part A v2 (canonical training set: 128 scenarios with Mascaret SWE truth).
#   data/scenarios_partA_v2/ ships with the working bundle; regenerate from
#   scratch with:
python scripts/generate_partA_v2.py --out data/scenarios_partA_v2     # diffusive reference
python scripts/run_partA_mascaret.py --root data/scenarios_partA_v2 --all --workers 3

# Part A v1 (pipeline-regression set)
python scripts/generate_scenarios_1d.py --out data/scenarios_1d --num 50

# Part B
python scripts/import_real_cases.py                 # raw projects -> scenarios/meshes
python scripts/run_real_family.py --mode validate --case mdx
python scripts/run_real_family.py --mode family --family-dir data/real_cases/family_mdx

# Training / evaluation
python scripts/train.py --config configs/<experiment>.yaml
```

Confidentiality: `real_projects/` contains the original basin models
(river names, coordinates) — intended for the private collaboration remote
only, not for public release. Derived npz datasets carry generic hydraulic
features only.
