#!/usr/bin/env bash
# A4 · persistence floor rows for the 2D domains (the no-skill reference).
#
# Persistence = freeze the last input frame and copy it forward: zero
# parameters, zero training. Evaluated through evaluate.py --checkpoint none
# (skips weight loading; the round-7 fix that made parameter-free arms
# evaluatable). Every predictive arm must beat this floor before its RMSE
# numbers mean anything — the paper's no-skill gate (slides "no-skill 地板").
#
# Produces one floor run dir per data root, named floor_persist_* so
# scripts/build_generalization_matrix.py folds them into the persist(floor)
# rows:
#   runs/floor_persist_2d          <- data/scenarios_2d_family  (test, 20 scenarios)
#   runs/floor_persist_2d_larger   <- data/scenarios_2d_larger  (all-test, 24 scenarios)
#   runs/floor_persist_exams_2d    <- data/real_cases/exams_2d      (full horizon)
#   runs/floor_persist_exams_2d_h8 <- data/real_cases/exams_2d_h8   (H=8 training view)
#
# Usage:
#   bash scripts/run_2d_persistence_floor.sh
#   ROOTS="data/scenarios_2d_family" bash scripts/run_2d_persistence_floor.sh
set -eo pipefail
cd "$(dirname "$0")/.."

BASE=configs/2d_baseline_persistence.yaml

# root|floor-run-name|steps
ROOTS=(${ROOTS:-\
"data/scenarios_2d_family|floor_persist_2d|0" \
"data/scenarios_2d_larger|floor_persist_2d_larger|0" \
"data/real_cases/exams_2d|floor_persist_exams_2d|48" \
"data/real_cases/exams_2d_h8|floor_persist_exams_2d_h8|8"})

for entry in "${ROOTS[@]}"; do
    IFS='|' read -r root name steps <<< "$entry"
    [ -d "$root" ] || { echo "[skip] $root (absent)"; continue; }
    # each floor root gets its own run dir, so eval_test.json inside is
    # unambiguous (evaluate.py only adds a root-name suffix under --data-root)
    json="runs/${name}/eval_test.json"
    if [ -f "$json" ]; then echo "[skip] $json exists"; continue; fi
    echo "=== [floor] ${name} <- ${root} ==="
    mkdir -p "runs/${name}"
    # dedicated config copy: out_dir -> the floor run dir, data.root -> this root
    sed -e "s#^out_dir:.*#out_dir: runs/${name}#" \
        -e "s#^  root:.*#  root: ${root}#" "$BASE" > "runs/${name}/config.yaml"
    extra=""
    [ "$steps" != 0 ] && extra="--steps ${steps}"
    python scripts/evaluate.py --config "runs/${name}/config.yaml" \
        --checkpoint none --split test ${extra} 2>&1 | tail -1
done
echo "2D_PERSISTENCE_FLOOR_DONE"
