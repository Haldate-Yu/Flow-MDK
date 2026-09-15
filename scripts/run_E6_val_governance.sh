#!/usr/bin/env bash
# E6 validation-governance probes (local 3060, flow_mdk 6L, local budget:
# G=32, 40 epochs, curriculum 4, early stop off — the same recipe as the
# MS_partA control runs, where flow_mdk val drifts 4.4-5.1x and every
# val-best checkpoint lands mid-curriculum at H=1).
#
# Arms (3 fresh seeds each, run dirs E6_partA_<arm>_s<seed>):
#   base    (no flags)                     — architecture-matched control
#   valfix  train.val_horizon=8            — fixed-horizon validation only
#   ema     train.ema_decay=0.995          — per-step weight EMA only
#   full    val_horizon=8 + gated early stop (patience 10, never fires before
#           H=8) + ema_decay=0.995         — combined E6 recipe
# (The legacy 3-layer MS_partA_flow_mdk runs are NOT architecture-matched;
# they remain in the registry but are not the probe control.)
#
# Each arm evals A-test with last.pt (in-dir), best.pt (ptbest_* twin) and,
# for EMA arms, ema.pt (ptema_* twin). Judgment: per arm x seed A-test
# h-RMSE per checkpoint protocol + best/stop epochs; the E6 recipe is
# validated if valfix/full best.pt reaches the control band with
# cross-seed stability, and ema.pt beats control last.pt.
#
#   bash scripts/run_E6_val_governance.sh 2>&1 \
#       | tee data/E6_val_governance_$(date +%Y%m%d_%H%M%S).log
set -e
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})
BASE="data.root=data/scenarios_partA_v2 model.hidden_dim=32 train.max_epochs=40 train.curriculum_steps=4 train.early_stop_patience=99"

twin_eval () {  # prefix run_dir checkpoint [evaluate.py args...]
    local prefix=$1 run_dir=$2 ckpt=$3; shift 3
    local twin=runs/${prefix}_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$ckpt" "$@" 2>&1 | tail -1
}

# control best.pt twins (never evaluated in the MS round)
for seed in "${SEEDS[@]}"; do
    run=runs/MS_partA_flow_mdk_s${seed}
    if [ -f "$run/best.pt" ] && [ ! -f "runs/ptbest_MS_partA_flow_mdk_s${seed}/eval_test.json" ]; then
        echo "=== [control s${seed}] best.pt twin eval ==="
        twin_eval ptbest "$run" "$run/best.pt" --split test
    fi
done

train_arm () {
    local arm=$1 seed=$2; shift 2
    local run_dir=runs/E6_partA_${arm}_s${seed}
    if [ -f "$run_dir/config.yaml" ]; then echo "[skip] $run_dir exists"; return; fi
    echo "=== [E6 ${arm} s${seed}] training -> $run_dir ==="
    python scripts/train.py --config configs/1d_flow_mdk.yaml --set \
        out_dir=$run_dir $BASE seed=$seed "$@" 2>&1 | tail -3
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test 2>&1 | tail -1
    twin_eval ptbest "$run_dir" "$run_dir/best.pt" --split test
    if [ -f "$run_dir/ema.pt" ]; then
        twin_eval ptema "$run_dir" "$run_dir/ema.pt" --split test
    fi
}

for seed in "${SEEDS[@]}"; do
    train_arm base   $seed
    train_arm valfix $seed train.val_horizon=8
    train_arm ema    $seed train.ema_decay=0.995
    train_arm full   $seed train.val_horizon=8 \
        train.early_stop_after_curriculum=true train.early_stop_patience=10 \
        train.ema_decay=0.995
done

echo "E6_VAL_GOVERNANCE_DONE"
