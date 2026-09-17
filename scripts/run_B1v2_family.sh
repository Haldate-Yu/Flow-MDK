#!/usr/bin/env bash
# B1v2 · B1 retrain on the family-v2 merged root (130 scenarios, round 3).
#
# L6 grew family_mdx 37 -> 50 (extend_family.py, seed 545); family_all was
# rebuilt at 130 scenarios to match the SWE-GNN 130-simulation protocol. The
# E3 main-table B1 runs (MS4_B1_*) trained on the 117-scenario family and
# stay untouched; this arm retrains the same three models at the same paper
# budget on family v2 under NEW names so both generations remain comparable.
#
#   summarise:  python scripts/summarize_runs.py --prefix B1v2 --ks
#
# Server usage (A100 GPU1; ~0.4-0.5 h per 1D run, ~4-6 h total):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_B1v2_family.sh 2>&1 \
#       | tee data/B1v2_$(date +%m%d).log
set -e
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})
COMMON="train.early_stop_patience=99"

best_eval () {  # run_dir -> ptbest twin eval on the B1 test split
    local run_dir=$1
    local twin=runs/ptbest_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$run_dir/best.pt" --split test 2>&1 | tail -1
}

train_and_eval () {
    local seed=$1 name=$2 config=$3
    local run_dir=runs/B1v2_${name}_s${seed}
    if [ -f "$run_dir/config.yaml" ]; then echo "[skip] $run_dir exists"; return; fi
    echo "=== [B1v2 s${seed}:${name}] training -> $run_dir ==="
    python scripts/train.py --config "$config" --set \
        out_dir=$run_dir data.root=data/real_cases/family_all $COMMON \
        seed=$seed 2>&1 | tail -3
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test 2>&1 | tail -1
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split val \
        --data-root data/real_cases/scenarios_1d 2>&1 | tail -1
    best_eval $run_dir
}

# family_all is derived from the three family_* dirs; rebuild for the v2 root
python scripts/make_family_all.py

for seed in "${SEEDS[@]}"; do
    train_and_eval $seed swegnn   configs/1d_swegnn_official.yaml
    train_and_eval $seed flow_mdk configs/1d_flow_mdk.yaml
    train_and_eval $seed ssgc     configs/1d_ssgc_symmetric.yaml
done

echo "B1V2_FAMILY_DONE"
