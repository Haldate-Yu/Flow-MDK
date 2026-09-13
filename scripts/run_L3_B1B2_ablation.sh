#!/usr/bin/env bash
# L3 (plan M2 core): B1 -> B2 three-way ablation on real Mascaret data.
# Train SSGC (symmetric MDK, -directionality), SWE-GNN (-MDK) and Flow-MDK
# (hybrid) on the merged real-master families (B1: mdx+zxh+wqh, 117
# scenarios), then evaluate in-domain (B1 test) and on the B2 real
# historical exams. Local budget matches the Part A chain (G=32, 40
# epochs); the paper-budget rerun happens on the server (L4).
set -e
cd "$(dirname "$0")/.."

python scripts/make_family_all.py

COMMON="data.root=data/real_cases/family_all model.hidden_dim=32 train.max_epochs=40 train.curriculum_steps=4 train.early_stop_patience=99"

train_and_eval () {
    local name=$1 config=$2 extra=$3
    echo "=== [L3:$name] training ==="
    python scripts/train.py --config "$config" --set \
        out_dir=runs/L3_B1_$name $COMMON $extra 2>&1 | tail -3
    echo "=== [L3:$name] B1 in-domain (test split) ==="
    python scripts/evaluate.py --config runs/L3_B1_$name/config.yaml \
        --checkpoint runs/L3_B1_$name/last.pt --split test 2>&1 | tail -2
    echo "=== [L3:$name] B2 real historical exams (zero-shot) ==="
    python scripts/evaluate.py --config runs/L3_B1_$name/config.yaml \
        --checkpoint runs/L3_B1_$name/last.pt --split val \
        --data-root data/real_cases/scenarios_1d 2>&1 | tail -7
}

train_and_eval swegnn configs/1d_swegnn_official.yaml \
    "model.num_message_passing_layers=2 model.hops_per_layer=2"
train_and_eval flow_mdk configs/1d_flow_mdk.yaml \
    "model.num_message_passing_layers=3 model.hops_per_layer=1"
train_and_eval ssgc configs/1d_ssgc_symmetric.yaml \
    "model.num_message_passing_layers=3 model.hops_per_layer=1"

echo "L3_ABLATION_DONE"
