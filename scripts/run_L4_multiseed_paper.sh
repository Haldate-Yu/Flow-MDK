#!/usr/bin/env bash
# L4 multi-seed replication at the paper budget (E3, server).
#
# Seeds 1..N x {Part A: swegnn/flow_mdk/gcn/gat; B1->B2: swegnn/flow_mdk/ssgc}
# at exactly the single-seed L4 budget (G=64, 150 epochs, curriculum 15,
# early stop off, last.pt protocol). Run dirs end in _s<seed> with NO
# timestamp so scripts/summarize_runs.py folds them into mean±std per model
# (same convention as run_multiseed_local.sh); seed 0 is copied from the
# existing 2026-09-13 paper runs via copy_seed0.
#
#   python scripts/summarize_runs.py --prefix MS4_partA --prefix MS4_B1 --ks
#
# Every run also gets a best.pt control eval on the primary test split, into
# a ptbest_* twin dir (never overwrites the canonical last.pt eval jsons).
#
# Recipe override after the E2 probes, e.g.:
#   EXTRA="train.lr=0.0035 train.lr_decay=0.85 train.lr_step_epochs=5" \
#       bash scripts/run_L4_multiseed_paper.sh
#
# Server usage (A100 GPU1; ~0.5 h per run, ~7-9 h for the default 14):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_L4_multiseed_paper.sh 2>&1 \
#       | tee data/L4_multiseed_$(date +%Y%m%d_%H%M%S).log
set -e
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-1 2})

COMMON="train.early_stop_patience=99 ${EXTRA:-}"

best_eval () {  # run_dir [evaluate.py args...] -> eval best.pt in a twin dir
    local run_dir=$1; shift
    local twin=runs/ptbest_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$run_dir/best.pt" "$@" 2>&1 | tail -2
}

copy_seed0 () {  # latest 2026-09-13 paper run -> MS4 group seed-0 copy
    local dst=$1 src_glob=$2
    if [ ! -f "$dst/config.yaml" ]; then
        local src
        src=$(ls -d $src_glob 2>/dev/null | sort | tail -1)
        if [ -n "$src" ]; then
            cp -r "$src" "$dst"
            echo "seed-0 copy of $src (results.csv rows live under the original name)" \
                > "$dst/_SEED0_SOURCE.txt"
        else
            echo "[warn] no seed-0 source for $src_glob — summarize will show s1..N only"
        fi
    fi
}

train_and_eval_partA () {
    local seed=$1 name=$2 config=$3
    local run_dir=runs/MS4_partA_${name}_s${seed}
    if [ -f "$run_dir/config.yaml" ]; then echo "[skip] $run_dir exists"; return; fi
    echo "=== [partA s${seed}:${name}] training -> $run_dir ==="
    python scripts/train.py --config "$config" --set \
        out_dir=$run_dir data.root=data/scenarios_partA_v2 $COMMON \
        seed=$seed 2>&1 | tail -3
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split A2_test 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split A3_test 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test \
        --data-root data/real_cases/family_mdx 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test \
        --data-root data/real_cases/family_zxh 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test \
        --data-root data/real_cases/family_wqh 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split val \
        --data-root data/real_cases/scenarios_1d 2>&1 | tail -7
    best_eval $run_dir --split test
}

train_and_eval_B1 () {
    local seed=$1 name=$2 config=$3
    local run_dir=runs/MS4_B1_${name}_s${seed}
    if [ -f "$run_dir/config.yaml" ]; then echo "[skip] $run_dir exists"; return; fi
    echo "=== [B1 s${seed}:${name}] training -> $run_dir ==="
    python scripts/train.py --config "$config" --set \
        out_dir=$run_dir data.root=data/real_cases/family_all $COMMON \
        seed=$seed 2>&1 | tail -3
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test 2>&1 | tail -2
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split val \
        --data-root data/real_cases/scenarios_1d 2>&1 | tail -7
    best_eval $run_dir --split test
}

for seed in "${SEEDS[@]}"; do
    copy_seed0 runs/MS4_partA_swegnn_s0   "runs/partA_paper_swegnn_2026*"
    copy_seed0 runs/MS4_partA_flow_mdk_s0 "runs/partA_paper_flow_mdk_2026*"
    copy_seed0 runs/MS4_partA_gcn_s0      "runs/partA_paper_gcn_2026*"
    copy_seed0 runs/MS4_partA_gat_s0      "runs/partA_paper_gat_2026*"
    copy_seed0 runs/MS4_B1_swegnn_s0      "runs/L3_B1_paper_swegnn_2026*"
    copy_seed0 runs/MS4_B1_flow_mdk_s0    "runs/L3_B1_paper_flow_mdk_2026*"
    copy_seed0 runs/MS4_B1_ssgc_s0        "runs/L3_B1_paper_ssgc_2026*"

    train_and_eval_partA $seed swegnn   configs/1d_swegnn_official.yaml
    train_and_eval_partA $seed flow_mdk configs/1d_flow_mdk.yaml
    train_and_eval_partA $seed gcn      configs/1d_baseline_gcn.yaml
    train_and_eval_partA $seed gat      configs/1d_baseline_gat.yaml

    # family_all is derived from the three family_* dirs; rebuild once per round
    python scripts/make_family_all.py
    train_and_eval_B1 $seed swegnn   configs/1d_swegnn_official.yaml
    train_and_eval_B1 $seed flow_mdk configs/1d_flow_mdk.yaml
    train_and_eval_B1 $seed ssgc     configs/1d_ssgc_symmetric.yaml
done

echo "L4_MULTISEED_PAPER_DONE"
