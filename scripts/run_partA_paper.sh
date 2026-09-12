#!/usr/bin/env bash
# Part A PAPER-LEVEL experiment chain (L4, server).
#
# Unlike run_partA_experiments.sh (first-round regression: G=32 / 40 epochs /
# reduced depth), this script runs the paper settings already encoded in the
# configs verbatim — SWE-GNN official recipe (G=64, 2 layers x 8 hops, 150
# epochs, batch 8, curriculum 15) and Flow-MDK / GCN / GAT (G=64, 6 layers x
# 1 hop, same budget) — with only the evaluation-protocol override from
# PLAN M1: early stopping disabled (conflicts with curriculum), full
# 150-epoch budget, last.pt evaluated.
#
# Each invocation creates timestamped run directories
# (runs/partA_paper_<name>_<YYYYmmdd_HHMMSS>/) so repeated rounds never
# overwrite each other; every train/eval also appends one row to
# runs/results.csv (one row per result, see src/flow_mdk/utils/results_log.py).
#
# Server usage (A100 GPU1):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_partA_paper.sh 2>&1 \
#       | tee data/partA_paper_$(date +%Y%m%d_%H%M%S).log
set -e
cd "$(dirname "$0")/.."

STAMP=$(date +%Y%m%d_%H%M%S)
echo "run stamp: $STAMP (runs/partA_paper_<name>_$STAMP, registry runs/results.csv)"

COMMON="data.root=data/scenarios_partA_v2 train.early_stop_patience=99"

train_and_eval () {
    local name=$1 config=$2
    local run_dir=runs/partA_paper_${name}_${STAMP}
    echo "=== [$name] training (paper settings from $config) -> $run_dir ==="
    python scripts/train.py --config "$config" --set \
        out_dir=$run_dir $COMMON 2>&1 | tail -3
    echo "=== [$name] Part A test (A1+A2+A3, 50 scenarios) ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test 2>&1 | tail -2
    echo "=== [$name] Part A2 test (unseen hydrology) ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split A2_test 2>&1 | tail -2
    echo "=== [$name] Part A3 test (larger basins) ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split A3_test 2>&1 | tail -2
    echo "=== [$name] zero-shot family_mdx ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test \
        --data-root data/real_cases/family_mdx 2>&1 | tail -2
    echo "=== [$name] zero-shot family_zxh ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test \
        --data-root data/real_cases/family_zxh 2>&1 | tail -2
    echo "=== [$name] zero-shot family_wqh ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test \
        --data-root data/real_cases/family_wqh 2>&1 | tail -2
    echo "=== [$name] zero-shot real cases (B2 exam) ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split val \
        --data-root data/real_cases/scenarios_1d 2>&1 | tail -7
}

train_and_eval swegnn configs/1d_swegnn_official.yaml
train_and_eval flow_mdk configs/1d_flow_mdk.yaml
train_and_eval gcn configs/1d_baseline_gcn.yaml
train_and_eval gat configs/1d_baseline_gat.yaml

echo "PARTA_PAPER_EXPERIMENTS_DONE"
