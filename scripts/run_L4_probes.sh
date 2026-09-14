#!/usr/bin/env bash
# L4 drift probes (E2, server): all 7 paper runs peak at epoch 4-14 then the
# val loss drifts 2-4x by the end of the 150-epoch budget, while the protocol
# evaluates last.pt. Three single-seed probes on the Part A chain (flow_mdk,
# the model the protocol hurts most), each evaluated on BOTH checkpoints —
#   probe_lr — lr 0.007 -> 0.0035, faster decay (0.9/7ep -> 0.85/5ep)
#   probe_L3 — 6 layers -> 3 (the depth that scored 0.77 in the G=32 multiseed)
#   probe_es — val-based early stopping (patience 20) instead of the fixed budget
# Optional extra model overrides, e.g. physics-matched MDK truncation:
#   EXTRA="model.mdk.num_steps=4" bash scripts/run_L4_probes.sh
#
# best.pt evals go to a ptbest_* twin dir (out_dir rewritten) so the canonical
# last.pt eval jsons are never overwritten; compare via runs/results.csv rows
# (checkpoint field ends in best.pt).
#
# Server usage (A100 GPU1, ~1 h total):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_L4_probes.sh 2>&1 \
#       | tee data/L4_probes_$(date +%Y%m%d_%H%M%S).log
set -e
cd "$(dirname "$0")/.."

STAMP=$(date +%Y%m%d_%H%M%S)

best_eval () {  # run_dir [evaluate.py args...] -> eval best.pt in a twin dir
    local run_dir=$1; shift
    local twin=runs/ptbest_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$run_dir/best.pt" "$@" 2>&1 | tail -2
}

probe () {
    local name=$1; shift
    local run_dir=runs/L4probe_${name}
    echo "=== [probe:$name] training ($*) -> $run_dir ==="
    python scripts/train.py --config configs/1d_flow_mdk.yaml --set \
        out_dir=$run_dir data.root=data/scenarios_partA_v2 \
        train.early_stop_patience=99 seed=0 ${EXTRA:-} "$@" 2>&1 | tail -3
    echo "=== [probe:$name] eval last.pt (A-test, protocol) ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test 2>&1 | tail -2
    echo "=== [probe:$name] eval best.pt (A-test, protocol-drift control) ==="
    best_eval $run_dir --split test
}

probe lr  train.lr=0.0035 train.lr_decay=0.85 train.lr_step_epochs=5
probe L3  model.num_message_passing_layers=3
probe es  train.early_stop_patience=20

echo "L4_PROBES_DONE (stamp $STAMP)"
