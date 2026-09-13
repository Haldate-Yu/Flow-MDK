#!/usr/bin/env bash
# Multi-seed replication of the L2/L3 local-budget chains.
#
# Puts error bars on the key comparisons before the L4 paper-budget verdict:
# Part A (in-domain + zero-shot) and the B1->B2 directionality question
# (Flow-MDK vs SSGC), each at exactly the single-seed chains' budget
# (G=32, 40 epochs, curriculum 4, early stop off). Seeds 1..N train fresh;
# seed 0 reuses the original runs via lightweight copies (the eval jsons,
# config and history are what the summarizer reads), so the MS_* groups are
# complete for scripts/summarize_runs.py.
#
#   bash scripts/run_multiseed_local.sh              # seeds 1 2
#   SEEDS="1 2 3" bash scripts/run_multiseed_local.sh
#
# After completion:
#   python scripts/summarize_runs.py --prefix MS_partA --prefix MS_B1 --ks
set -e
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-1 2})

copy_seed0 () {  # src single-seed run dir -> MS group seed-0 copy
    local src=$1 dst=$2
    if [ -d "$src" ] && [ ! -f "$dst/config.yaml" ]; then
        cp -r "$src" "$dst"
        echo "seed-0 copy of $src (results.csv rows live under the original name)" \
            > "$dst/_SEED0_SOURCE.txt"
    fi
}

train_eval_partA () {
    local seed=$1 name=$2 config=$3 extra=$4
    local out=runs/MS_partA_${name}_s${seed}
    if [ -f "$out/config.yaml" ]; then echo "[skip] $out exists"; return; fi
    echo "=== [MS partA s${seed} ${name}] training ==="
    python scripts/train.py --config "$config" --set \
        out_dir=$out data.root=data/scenarios_partA_v2 \
        model.hidden_dim=32 train.max_epochs=40 train.curriculum_steps=4 \
        train.early_stop_patience=99 seed=$seed $extra 2>&1 | tail -2
    python scripts/evaluate.py --config $out/config.yaml \
        --checkpoint $out/last.pt --split test 2>&1 | tail -1
    for fam in mdx zxh wqh; do
        python scripts/evaluate.py --config $out/config.yaml \
            --checkpoint $out/last.pt --split test \
            --data-root data/real_cases/family_${fam} 2>&1 | tail -1
    done
    python scripts/evaluate.py --config $out/config.yaml \
        --checkpoint $out/last.pt --split val \
        --data-root data/real_cases/scenarios_1d 2>&1 | tail -1
}

train_eval_B1 () {
    local seed=$1 name=$2 config=$3 extra=$4
    local out=runs/MS_B1_${name}_s${seed}
    if [ -f "$out/config.yaml" ]; then echo "[skip] $out exists"; return; fi
    echo "=== [MS B1 s${seed} ${name}] training ==="
    python scripts/train.py --config "$config" --set \
        out_dir=$out data.root=data/real_cases/family_all \
        model.hidden_dim=32 train.max_epochs=40 train.curriculum_steps=4 \
        train.early_stop_patience=99 seed=$seed $extra 2>&1 | tail -2
    python scripts/evaluate.py --config $out/config.yaml \
        --checkpoint $out/last.pt --split test 2>&1 | tail -1
    python scripts/evaluate.py --config $out/config.yaml \
        --checkpoint $out/last.pt --split val \
        --data-root data/real_cases/scenarios_1d 2>&1 | tail -1
}

# seed-0 slots from the original single-seed chains
for m in swegnn flow_mdk gcn; do copy_seed0 runs/L2_partA_$m runs/MS_partA_${m}_s0; done
for m in swegnn flow_mdk ssgc; do copy_seed0 runs/L3_B1_$m runs/MS_B1_${m}_s0; done

for seed in "${SEEDS[@]}"; do
    # Part A: the rescue (flow_mdk vs swegnn) + in-domain GCN strength
    train_eval_partA $seed swegnn configs/1d_swegnn_official.yaml \
        "model.num_message_passing_layers=2 model.hops_per_layer=2"
    train_eval_partA $seed flow_mdk configs/1d_flow_mdk.yaml \
        "model.num_message_passing_layers=3 model.hops_per_layer=1"
    train_eval_partA $seed gcn configs/1d_baseline_gcn.yaml \
        "model.num_message_passing_layers=3"
    # B1 -> B2: the directionality question (flow_mdk vs ssgc)
    train_eval_B1 $seed swegnn configs/1d_swegnn_official.yaml \
        "model.num_message_passing_layers=2 model.hops_per_layer=2"
    train_eval_B1 $seed flow_mdk configs/1d_flow_mdk.yaml \
        "model.num_message_passing_layers=3 model.hops_per_layer=1"
    train_eval_B1 $seed ssgc configs/1d_ssgc_symmetric.yaml \
        "model.num_message_passing_layers=3 model.hops_per_layer=1"
done

echo "MULTISEED_DONE"
