# Datasets / 数据归档

Everything needed to reproduce the Flow-MDK experiments, archived in one
place and ready for Git LFS sync (patterns in `.gitattributes`; run
`scripts/archive_datasets.py` to refresh). Per-file provenance and sizes:
`MANIFEST.json` (add `--hash` for sha256).

| directory | content | origin | size |
|---|---|---|---|
| `telemac-mascaret-v8p4r0/` | **self-contained docker build context**: solver source tree (`telemac-mascaret/`, examples/notebooks/builds excluded) + `Dockerfile` + build scripts + `dependencies/` (JDK 8, timezone) at context root | `D:\tmp\telemac-wz-260529` | ~460 MB |
| `docker_images/` | prebuilt solver images (`docker load < *.tar.gz`): `telemac-debian_0.1` (base, needed before building the context) + `flow-mdk-telemac_v8p4r0` (ready-to-run) | local docker (`docker save`) | ~2.5 GB |
| `swegnn-official/` | official SWE-GNN repo (RBTV1/SWE-GNN-paper-repository-) **incl. `raw_datasets/`** — 130 Delft3D-FM simulations used in the SWE-GNN paper | github / Zenodo 10214840 + 7764418 | ~2 GB |
| `real_projects/` | raw real-basin project templates: `telemac1d/{mdx,wqh,zxh,mdxUpStream,mdxDownStream}`, `telemac2d/{wqh,mdx}` | schinta basin-flood-prevention subsystem | ~61 MB |
| `partA_synthetic/` | 50 generated 1D scenarios (`*.npz`) + `split.json` + `stats.json` — geometry × hydrology random family, diffusive-wave reference truth | `scripts/generate_scenarios_1d.py` | ~10 MB |
| `partB_family_mdx/` | 37 real-master scenarios (mdx geometry × synthetic hydrology) + splits + `mascaret_runs/` (per-scenario workdirs with `.opt` results; `.lis` listings excluded as regenerable) | `flow_mdk/gen/scenarios_real.py` + `scripts/run_real_family.py` | ~0.6 GB |
| `partB_family_zxh/` | 18 real-master scenarios (zxh geometry), same pipeline | idem | ~0.3 GB |
| `partB_real_cases/` | imported real cases (`scenarios_1d/*.npz`), 2D meshes (`meshes_2d/*.npz`), `inventory.json`, validation reports | `scripts/import_real_cases.py` | ~10 MB |
| `runs/` | training/evaluation results: `config.yaml`, `history.json`, `best.pt`, `eval_*.json` per experiment | `scripts/train.py` / `scripts/evaluate.py` | small |

Reproduction chain:

```bash
# solver — either load the prebuilt images (recommended):
docker load < datasets/docker_images/telemac-debian_0.1.tar.gz
docker load < datasets/docker_images/flow-mdk-telemac_v8p4r0.tar.gz
#   ...or load the base image only and rebuild the solver image from the
#   self-contained context (Dockerfile expects ./telemac-mascaret + ./dependencies):
docker load < datasets/docker_images/telemac-debian_0.1.tar.gz
docker build -t flow-mdk-telemac:v8p4r0 datasets/telemac-mascaret-v8p4r0/   # ~20-40 min

# Part A
python scripts/generate_scenarios_1d.py --out data/scenarios_1d --num 50
python scripts/train.py --config configs/<experiment>.yaml

# Part B
python scripts/import_real_cases.py                 # raw projects -> scenarios/meshes
python scripts/run_real_family.py --mode validate --case mdx
python scripts/gen_real_family (see gen/scenarios_real.py)
python scripts/run_real_family.py --mode family --family-dir data/real_cases/family_mdx
```

Confidentiality: `real_projects/` contains the original basin models
(river names, coordinates) — intended for the private collaboration remote
only, not for public release. Derived npz datasets carry generic hydraulic
features only.
