#!/usr/bin/env bash
# M4 training round 1: coupled mdx chain (single-scenario feasibility).
#
# Data: data/real_cases/coupled_chain/mdx_chain_v1.npz (65,189 nodes,
# 389,928 edges, 31 frames @ 1800 s, one-way Q coupled truth — see
# scripts/couple_mdx_chain.py). split.json sets train/val/test ALL to the
# single scenario ON PURPOSE: this is a capability round (can the gated
# model learn the coupled chain at all?), not a generalization claim —
# metrics are overfit checks.
#
# Protocol: flow_mdk 6L + MDK, G=64, batch 4 (65k-node graphs; raise to 8
# only if memory allows), H=8 curriculum in 5-epoch steps (40 epochs to
# complete) + E6 recipe as the default (val_horizon=8, gated early stop,
# EMA after curriculum). Eval last/best/ema on the same scenario.
#
# Note: MDK K stays at the 1D paper value 2 (feasibility round; physics-
# matching K to the chain's dx/dt is a v2 question).
#
# Server usage (A100 GPU1):
#   CUDA_VISIBLE_DEVICES=1 BATCH_SIZE=4 bash scripts/run_M4_coupled_v1.sh 2>&1 \
#       | tee data/M4_coupled_v1_$(date +%m%d).log
set -e
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0})
BATCH_SIZE="${BATCH_SIZE:-4}"

twin_eval () {  # prefix run_dir checkpoint
    local prefix=$1 run_dir=$2 ckpt=$3
    local twin=runs/${prefix}_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$ckpt" --split test 2>&1 | tail -1
}

for seed in "${SEEDS[@]}"; do
    run=runs/M4_chain_v1_flow_mdk_s${seed}
    if [ -f "$run/config.yaml" ]; then echo "[skip] $run exists"; continue; fi
    echo "=== [M4 chain v1 s${seed}] training -> $run ==="
    python scripts/train.py --config configs/1d_flow_mdk.yaml --set \
        out_dir=$run data.root=data/real_cases/coupled_chain \
        data.name=1d_chain seed=${seed} \
        model.hidden_dim=64 train.batch_size=${BATCH_SIZE} \
        train.max_epochs=60 train.curriculum_steps=5 \
        train.early_stop_patience=99 \
        train.val_horizon=8 \
        train.early_stop_after_curriculum=true \
        train.ema_decay=0.999 train.ema_after_curriculum=true 2>&1 | tail -3
    python scripts/evaluate.py --config $run/config.yaml \
        --checkpoint $run/last.pt --split test 2>&1 | tail -1
    twin_eval ptbest "$run" "$run/best.pt"
    if [ -f "$run/ema.pt" ]; then
        twin_eval ptema "$run" "$run/ema.pt"
    fi
done
echo "M4_CHAIN_V1_DONE"
