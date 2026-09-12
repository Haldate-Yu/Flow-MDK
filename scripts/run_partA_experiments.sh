#!/usr/bin/env bash
# Part A experiment chain (first-round regression: G=32 / 40 epochs):
# train 4 architectures on the synthetic family, then evaluate in-domain
# (Part A test) and zero-shot on Part B (real-master families + real
# historical cases). Each invocation creates timestamped run directories
# (runs/partA_<name>_<YYYYmmdd_HHMMSS>/) so repeated rounds never overwrite
# each other; every train/eval appends one row to runs/results.csv.
# For the paper-level chain see run_partA_paper.sh.
set -e
cd "$(dirname "$0")/.."

STAMP=$(date +%Y%m%d_%H%M%S)
echo "run stamp: $STAMP (runs/partA_<name>_$STAMP, registry runs/results.csv)"

COMMON="data.root=data/scenarios_partA_v2 model.hidden_dim=32 train.max_epochs=40 train.curriculum_steps=4 train.early_stop_patience=99"

train_and_eval () {
    local name=$1 config=$2 extra=$3
    local run_dir=runs/partA_${name}_${STAMP}
    echo "=== [$name] training ==="
    python scripts/train.py --config "$config" --set \
        out_dir=$run_dir $COMMON $extra 2>&1 | tail -3
    echo "=== [$name] Part A test ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test 2>&1 | tail -2
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
    echo "=== [$name] zero-shot real cases ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split val \
        --data-root data/real_cases/scenarios_1d 2>&1 | tail -7
}

train_and_eval swegnn configs/1d_swegnn_official.yaml \
    "model.num_message_passing_layers=2 model.hops_per_layer=2"
train_and_eval flow_mdk configs/1d_flow_mdk.yaml \
    "model.num_message_passing_layers=3 model.hops_per_layer=1"
train_and_eval gcn configs/1d_baseline_gcn.yaml \
    "model.num_message_passing_layers=3"
train_and_eval gat configs/1d_baseline_gat.yaml \
    "model.num_message_passing_layers=3"

echo "PARTA_EXPERIMENTS_DONE"
