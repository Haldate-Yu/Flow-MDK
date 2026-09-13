#!/usr/bin/env bash
# L2: regime-aligned formal comparison — Part A v2 with full-SWE Mascaret
# truth (attached by scripts/run_partA_mascaret.py). Waits for the L1 batch
# marker, then trains the four architectures and evaluates in-domain
# (A1/A2/A3) and zero-shot on Part B (real families + real exams).
set -e
cd "$(dirname "$0")/.."

MARKER=data/partA_v2_mascaret_runs/_batch_done.json
for i in $(seq 1 360); do
    [ -f "$MARKER" ] && break
    sleep 60
done
[ -f "$MARKER" ] || { echo "L1 batch marker never appeared"; exit 1; }
echo "=== L1 batch report ==="
cat "$MARKER"

COMMON="data.root=data/scenarios_partA_v2 model.hidden_dim=32 train.max_epochs=40 train.curriculum_steps=4 train.early_stop_patience=99"

train_and_eval () {
    local name=$1 config=$2 extra=$3
    echo "=== [L2:$name] training ==="
    python scripts/train.py --config "$config" --set \
        out_dir=runs/L2_partA_$name $COMMON $extra 2>&1 | tail -3
    echo "=== [L2:$name] Part A v2 test (A1_test + A2 + A3) ==="
    python scripts/evaluate.py --config runs/L2_partA_$name/config.yaml \
        --checkpoint runs/L2_partA_$name/last.pt --split test 2>&1 | tail -2
    echo "=== [L2:$name] zero-shot family_mdx ==="
    python scripts/evaluate.py --config runs/L2_partA_$name/config.yaml \
        --checkpoint runs/L2_partA_$name/last.pt --split test \
        --data-root data/real_cases/family_mdx 2>&1 | tail -2
    echo "=== [L2:$name] zero-shot family_zxh ==="
    python scripts/evaluate.py --config runs/L2_partA_$name/config.yaml \
        --checkpoint runs/L2_partA_$name/last.pt --split test \
        --data-root data/real_cases/family_zxh 2>&1 | tail -2
    echo "=== [L2:$name] zero-shot family_wqh ==="
    python scripts/evaluate.py --config runs/L2_partA_$name/config.yaml \
        --checkpoint runs/L2_partA_$name/last.pt --split test \
        --data-root data/real_cases/family_wqh 2>&1 | tail -2
    echo "=== [L2:$name] zero-shot real exams (B2) ==="
    python scripts/evaluate.py --config runs/L2_partA_$name/config.yaml \
        --checkpoint runs/L2_partA_$name/last.pt --split val \
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

echo "L2_SWE_EXPERIMENTS_DONE"
