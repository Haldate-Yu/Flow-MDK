#!/usr/bin/env bash
# Part A experiment chain: train 4 architectures on the synthetic family,
# then evaluate in-domain (Part A test) and zero-shot on Part B
# (real-master families + real historical cases). Results -> runs/<name>/
set -e
cd "$(dirname "$0")/.."

COMMON="data.root=data/scenarios_1d model.hidden_dim=32 train.max_epochs=40 train.curriculum_steps=4 train.early_stop_patience=99"

train_and_eval () {
    local name=$1 config=$2 extra=$3
    echo "=== [$name] training ==="
    python scripts/train.py --config "$config" --set \
        out_dir=runs/partA_$name $COMMON $extra 2>&1 | tail -3
    echo "=== [$name] Part A test ==="
    python scripts/evaluate.py --config runs/partA_$name/config.yaml \
        --checkpoint runs/partA_$name/last.pt --split test 2>&1 | tail -2
    echo "=== [$name] zero-shot family_mdx ==="
    python scripts/evaluate.py --config runs/partA_$name/config.yaml \
        --checkpoint runs/partA_$name/last.pt --split test \
        --data-root data/real_cases/family_mdx 2>&1 | tail -2
    echo "=== [$name] zero-shot family_zxh ==="
    python scripts/evaluate.py --config runs/partA_$name/config.yaml \
        --checkpoint runs/partA_$name/last.pt --split test \
        --data-root data/real_cases/family_zxh 2>&1 | tail -2
    echo "=== [$name] zero-shot real cases ==="
    python scripts/evaluate.py --config runs/partA_$name/config.yaml \
        --checkpoint runs/partA_$name/last.pt --split val \
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
