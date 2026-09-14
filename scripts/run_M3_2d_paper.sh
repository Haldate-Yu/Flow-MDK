#!/usr/bin/env bash
# M3 2D paper-budget training (server, after the 130-scenario family sync).
#
# Trains the three core models on the synthetic 2D family
# (data/scenarios_2d_family: 130 TELEMAC-2D scenarios, 64x64 @ 100 m,
# 70/15/15 split) at the 1D paper budget (G=64, 150 epochs, curriculum 15,
# early stop off). Models: swegnn (2Lx8hop skeleton), flow_mdk (6L+MDK),
# ssgc (symmetric MDK) — the directed-vs-symmetric question on 2D is the
# M3 headline, so ssgc is in from the start.
#
# Run dirs end in _s<seed> so scripts/summarize_runs.py folds seeds into
# mean±std (convention shared with run_L4_multiseed_paper.sh); default is a
# single seed-0 round. best.pt gets a ptbest_* twin-dir control eval.
#
#   python scripts/summarize_runs.py --prefix MS4_2d --ks
#
# Recipe override once the E2 drift probes settle, e.g.:
#   EXTRA="train.lr=0.0035 train.lr_decay=0.85 train.lr_step_epochs=5" bash ...
#
# Server usage (A100 GPU1; E4 smoke measured 23-50 s/epoch at batch 4, so
# budget ~2-4 h per model at batch 8):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_M3_2d_paper.sh 2>&1 \
#       | tee data/M3_2d_paper_$(date +%Y%m%d_%H%M%S).log
set -e
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0})

COMMON="data.name=2d_grid data.root=data/scenarios_2d_family \
    train.max_epochs=150 train.curriculum_steps=15 train.batch_size=8 \
    train.early_stop_patience=99 ${EXTRA:-}"

best_eval () {  # run_dir [evaluate.py args...] -> eval best.pt in a twin dir
    local run_dir=$1; shift
    local twin=runs/ptbest_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$run_dir/best.pt" "$@" 2>&1 | tail -2
}

train_and_eval_2d () {
    local seed=$1 name=$2 config=$3
    local run_dir=runs/MS4_2d_${name}_s${seed}
    if [ -f "$run_dir/config.yaml" ]; then echo "[skip] $run_dir exists"; return; fi
    echo "=== [2D s${seed}:${name}] training -> $run_dir ==="
    python scripts/train.py --config "$config" --set \
        out_dir=$run_dir $COMMON seed=$seed 2>&1 | tail -3
    echo "=== [2D s${seed}:${name}] eval last.pt (2D test split) ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test 2>&1 | tail -2
    echo "=== [2D s${seed}:${name}] eval best.pt (protocol-drift control) ==="
    best_eval $run_dir --split test
}

for seed in "${SEEDS[@]}"; do
    train_and_eval_2d $seed swegnn   configs/1d_swegnn_official.yaml
    train_and_eval_2d $seed flow_mdk configs/1d_flow_mdk.yaml
    train_and_eval_2d $seed ssgc     configs/1d_ssgc_symmetric.yaml
done

echo "M3_2D_PAPER_DONE"
