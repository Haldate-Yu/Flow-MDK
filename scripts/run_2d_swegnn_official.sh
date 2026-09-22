#!/usr/bin/env bash
# 2D SWE-GNN arm at the **official depth** (1 outer layer x K=8 hops).
#
# Trains configs/2d_swegnn_official.yaml on data/scenarios_2d_family (the 130-
# scenario TELEMAC-2D family, 64x64 @ 100 m, 91/19/20 split) at the paper
# budget, and evaluates the same protocol as run_M3_2d_paper.sh:
#   last.pt  -> eval_test.json in the run dir            (--split test)
#   best.pt  -> twin dir runs/ptbest_MS4b_2d_swegnn_s*   (--split test)
#
# Every existing artifact is left alone: new run prefix MS4b_2d_*, new config
# file. The only intended difference from runs/MS4_2d_swegnn_s* is the depth
# (16 -> 8 message-passing hops per step); patience stays at the sibling arms'
# 99. For full paper fidelity (patience 30) run with:
#   EXTRA="train.early_stop_patience=30" bash scripts/run_2d_swegnn_official.sh
#
# Usage (server, one A100; ~1.5-2.5 h per seed with 8 hops instead of 16):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_2d_swegnn_official.sh 2>&1 \
#       | tee data/1x8_2d_$(date +%m%d).log
#
# Re-runs are safe: a run is skipped on its training artifact (last.pt), not on
# config.yaml, so a crashed run is retrained instead of silently counted.
#
# NOTE the registry/matrix whitelist: scripts/build_generalization_matrix.py
# matches `^MS4_2d_(swegnn|flow_mdk|ssgc|gcn|gat)_s\d+$` and scripts/
# plot_pareto.py uses prefixes ("MS4_2d_",). Rows from this script are
# therefore EXCLUDED from both until those two lines are extended with the new
# prefix — see plan/paper1x8_swegnn_runbook.md.
set -eo pipefail
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})
CONFIG=${CONFIG:-configs/2d_swegnn_official.yaml}
PREFIX=${PREFIX:-MS4b_2d_swegnn}
EXTRA=${EXTRA:-}
ROOT=data/scenarios_2d_family

echo "=== sanity: data root ==="
python - "$ROOT" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
split = json.loads((root / "split.json").read_text(encoding="utf-8"))
n = len(list(root.glob("*.npz")))
want = {"train": 91, "val": 19, "test": 20}
got = {k: len(v) for k, v in split.items()}
print(f"[guard] {root}: {n} npz, split {got}")
if got != want or n != 130:
    raise SystemExit(
        f"[guard] FATAL: expected 130 npz and split {want}; got {n} and {got}. "
        "This root is not the family the existing MS4_2d_* runs used - stop.")
PY

best_eval () {  # run_dir -> eval best.pt in a twin dir
    local run_dir=$1
    local twin=runs/ptbest_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$run_dir/best.pt" --split test 2>&1 | tail -2
}

for seed in "${SEEDS[@]}"; do
    run=runs/${PREFIX}_s${seed}
    if [ -f "$run/last.pt" ]; then echo "[skip] $run done"; continue; fi
    echo "=== [1x8 2D s${seed}] training -> $run ==="
    python scripts/train.py --config "$CONFIG" --set \
        out_dir=$run seed=${seed} ${EXTRA} 2>&1 | tail -3
    echo "=== [1x8 2D s${seed}] eval last.pt (2D test split) ==="
    python scripts/evaluate.py --config "$run/config.yaml" \
        --checkpoint "$run/last.pt" --split test 2>&1 | tail -2
    echo "=== [1x8 2D s${seed}] eval best.pt (protocol-drift control) ==="
    best_eval "$run"
done

echo "=== seed summary (KS needs >=5 scenarios per domain: this is seed spread) ==="
python scripts/summarize_runs.py --prefix "${PREFIX}" 2>&1 | tail -12 || true

echo "1X8_2D_SWEGNN_DONE"
for seed in "${SEEDS[@]}"; do echo "  fetch: runs/${PREFIX}_s${seed}  runs/ptbest_${PREFIX}_s${seed}"; done
