# TELEMAC-MASCARET integration

The training ground truth is produced by the **local TELEMAC-MASCARET
source tree**. The full tree (~1.9 GB) deliberately stays *outside* the
repository — it is either referenced in place or consumed through the
prebuilt Docker image.

## Source tree (local reference)

- Path used during development: `D:\tmp\telemac-wz-260529\telemac-mascaret`
  (override with the `FLOW_MDK_TELEMAC_ROOT` environment variable).
- Key subpaths:
  - `sources/mascaret` — 1D kernel Fortran sources (~9 MB, the only part
    worth vendoring if a self-contained repo is ever needed);
  - `sources/api` + `scripts/python3/telapy` — the TelApy API used for
    headless in-process runs;
  - `examples/mascaret` — reference projects (`.xcas` steering, `geometrie`,
    `.loi` laws) that our `scripts/run_mascaret.py` templates mirror;
  - `examples/telemac2d` — 2D reference cases (used to validate
    `scripts/selafin.py`).

To vendor a minimal copy into this repository (git-ignored) instead:

```bash
mkdir -p third_party/telemac-mascaret
cp -r "$FLOW_MDK_TELEMAC_ROOT/sources/mascaret" third_party/telemac-mascaret/
cp -r "$FLOW_MDK_TELEMAC_ROOT/sources/api"      third_party/telemac-mascaret/
cp -r "$FLOW_MDK_TELEMAC_ROOT/scripts/python3"  third_party/telemac-mascaret/
cp -r "$FLOW_MDK_TELEMAC_ROOT/examples/mascaret" third_party/telemac-mascaret/
```

## Docker image

The working image (`flow-mdk-telemac:v8p4r0`, built FROM
`telemac-debian:0.1`) is **archived inside the repository** — no access to
this local tree is needed to reproduce it:

- `datasets/docker_images/telemac-debian_0.1.tar.gz` — base image
  (`docker load` first);
- `datasets/docker_images/flow-mdk-telemac_v8p4r0.tar.gz` — ready-to-run
  solver image;
- `datasets/telemac-mascaret-v8p4r0/` — self-contained build context
  (Dockerfile + build scripts + `dependencies/` + solver source tree in
  `telemac-mascaret/`), buildable directly after loading the base image:

  ```bash
  docker load < datasets/docker_images/telemac-debian_0.1.tar.gz
  docker build -t flow-mdk-telemac:v8p4r0 datasets/telemac-mascaret-v8p4r0/   # ~20-40 min
  ```

The context is the pruned tree (examples/notebooks/builds excluded — they are
not inputs of `compile_telemac.py`); `scripts/archive_datasets.py` regenerates
it from the local tree.

The upstream base image was never built from a Dockerfile here — it was
loaded from `D:\tmp\telemac-wz-260529\telemac-debian.tar`, now archived as
`datasets/docker_images/telemac-debian_0.1.tar.gz` (see above).

Then run scenarios headlessly:

```bash
# 1D: Mascaret project generation + run + result parsing
python scripts/run_mascaret.py --scenario data/scenarios_1d/1d_0000.npz \
    --workdir data/mascaret/1d_0000 --backend docker

# 2D (M3): TELEMAC-2D project generation
python scripts/run_telemac2d_docker.py --scenario data/scenarios_2d/2d_0000.npz \
    --workdir data/telemac2d/2d_0000
```

The image name can be overridden with `FLOW_MDK_TELEMAC_IMAGE`.

## Validation status

| Piece | Status |
|---|---|
| `scripts/selafin.py` reader | validated against 4 v8p4 example files |
| Mascaret file templates (`.xcas`, `geometrie`, `.loi`) | mirrored from the v8p4 example; binary round-trip to be validated in M1 |
| TelApy in-process backend | scaffolded; needs the compiled shared library |
| TELEMAC-2D geometry writer + `.cas` | scaffolded; `.cli` boundary file and run validation due in M3 |
