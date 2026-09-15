#!/usr/bin/env bash
# MS5 / E1 final attempt: shallow multi-hop skeleton + MDK mixing, paper
# budget, 3 fresh seeds (Part A synthetic 1D).
#
# Arm: configs/1d_swegnn_mdk.yaml = official SWE-GNN skeleton (2L x 8 hops,
# tanh, per-hop weights) + directed MDK diffusion branch. Question: does MDK
# mixing on the drift-resistant shallow skeleton reach the gcn/gat best.pt
# band (0.777±0.032 / 0.866±0.102, MS4 E3 reference) — i.e. can Flow-MDK be
# tuned to parity/best on 1D synthetic — without the 6-layer drift penalty?
#
# All three seeds are FRESH runs (this architecture has no prior run, so
# unlike run_L4_multiseed_paper.sh there is no seed-0 copy). Run dirs end in
# _s<seed> so scripts/summarize_runs.py folds mean±std; every run gets the
# full MS4_partA eval set (A-test/A2/A3 + 3 zero-shot families + B2 exam) and
# a ptbest_* twin for the best.pt protocol control:
#
#   python scripts/summarize_runs.py --prefix MS5_partA --ks
#
# Judgment protocol (pre-registered): headline = A-test last.pt mean±std vs
# MS4 (swegnn 1.485±0.730 / gat 1.134±0.679 / gcn 12.383±19.915 /
# flow_mdk 5.040±3.195); parity claim = best.pt within ~0.8 band of
# gcn 0.777±0.032. Do NOT set EXTRA recipe overrides — comparability with
# the MS4 reference table requires the identical official recipe.
#
# Server usage (A100 GPU1; ~0.5-0.7 h per run, ~2 h for 3 seeds):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_MS5_shallow_mdk.sh 2>&1 \
#       | tee data/MS5_shallow_mdk_$(date +%Y%m%d_%H%M%S).log
set -e
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})

COMMON="data.root=data/scenarios_partA_v2 train.early_stop_patience=99 ${EXTRA:-}"

best_eval () {  # run_dir [evaluate.py args...] -> eval best.pt in a twin dir
    local run_dir=$1; shift
    local twin=runs/ptbest_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$run_dir/best.pt" "$@" 2>&1 | tail -2
}

for seed in "${SEEDS[@]}"; do
    run_dir=runs/MS5_partA_2x8mdk_s${seed}
    if [ -f "$run_dir/config.yaml" ]; then echo "[skip] $run_dir exists"; continue; fi
    echo "=== [s${seed}:2x8mdk] training (paper settings from configs/1d_swegnn_mdk.yaml) -> $run_dir ==="
    python scripts/train.py --config configs/1d_swegnn_mdk.yaml --set \
        out_dir=$run_dir $COMMON seed=$seed 2>&1 | tail -3
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split A2_test 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split A3_test 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test \
        --data-root data/real_cases/family_mdx 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test \
        --data-root data/real_cases/family_zxh 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test \
        --data-root data/real_cases/family_wqh 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split val \
        --data-root data/real_cases/scenarios_1d 2>&1 | tail -7
    best_eval $run_dir --split test
done

echo "MS5_SHALLOW_MDK_DONE"
