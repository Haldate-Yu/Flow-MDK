#!/usr/bin/env bash
# B1v2 baseline completion: GCN / GAT / shallow-2x8+MDK on the real-1D family.
#
# Round-6 gap closure. The B1 arm was originally designed as a three-model
# mechanism ablation (run_B1v2_family.sh: swegnn / flow_mdk / ssgc), so the
# vanilla baselines that anchor the Part A ranking (GCN/GAT — E3 shows their
# best.pt is the most seed-stable of all models) and the shallow-MDK form
# (MS5) were never trained on the real family, while paper_architecture_plan
# 5.1 promises six baselines and the B1 table claims the "unique dual-protocol
# stable 0.8-band" result. This arm trains the three missing models on the
# SAME family_all v2 root at the SAME paper budget, so summarize folds all
# six arms into one table:
#
#   python scripts/summarize_runs.py --prefix B1v2 --ks
#
# Recipe: verbatim run_B1v2_family.sh (paper budget from the configs — 150
# epochs, curriculum, batch 8 — plus early_stop_patience=99); evals are
# last.pt on the B1 test split, last.pt on the real-case val root
# (B2-adjacent transfer), and the ptbest twin for best.pt. Skip is
# artifact-based (last.pt) per the round-5 lesson: a crashed run leaves
# config.yaml behind and must be retrained.
#
# Per-run cost ~0.4-0.5 h on one A100 (~4-5 h for the default 9 runs).
#
# Server usage (A100 GPU1):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_B1v2_baselines.sh 2>&1 \
#       | tee data/B1v2_baselines_$(date +%m%d).log
# or split arms across GPUs:
#   CUDA_VISIBLE_DEVICES=1 ARMS="gcn gat" bash scripts/run_B1v2_baselines.sh
#   CUDA_VISIBLE_DEVICES=0 ARMS="2x8mdk"  bash scripts/run_B1v2_baselines.sh
set -eo pipefail
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})
ARMS=(${ARMS:-gcn gat 2x8mdk})
COMMON="train.early_stop_patience=99"

eval_real_val () {  # run_dir -> last.pt on the real-case val root
    local run_dir=$1
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split val \
        --data-root data/real_cases/scenarios_1d 2>&1 | tail -1
}

best_eval () {  # run_dir -> ptbest twin eval on the B1 test split
    local run_dir=$1
    local twin=runs/ptbest_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$run_dir/best.pt" --split test 2>&1 | tail -1
}

# family_all is derived from the three family_* dirs; rebuild for the v2 root
python scripts/make_family_all.py

for arm in "${ARMS[@]}"; do
    case $arm in
        gcn)    base=configs/1d_baseline_gcn.yaml ;;
        gat)    base=configs/1d_baseline_gat.yaml ;;
        2x8mdk) base=configs/1d_swegnn_mdk.yaml ;;
        *) echo "unknown arm $arm"; exit 1 ;;
    esac
    for seed in "${SEEDS[@]}"; do
        run=runs/B1v2_${arm}_s${seed}
        if [ -f "$run/last.pt" ]; then echo "[skip] $run done"; continue; fi
        echo "=== [B1v2 ${arm} s${seed}] training -> $run ==="
        python scripts/train.py --config "$base" --set \
            out_dir=$run data.root=data/real_cases/family_all $COMMON \
            seed=$seed 2>&1 | tail -3
        python scripts/evaluate.py --config $run/config.yaml \
            --checkpoint $run/last.pt --split test 2>&1 | tail -1
        eval_real_val $run
        best_eval $run
    done
done
echo "B1V2_BASELINES_DONE"
