#!/usr/bin/env bash
# L3 PAPER-LEVEL ablation chain (L4, server): B1 -> B2 three-way ablation.
#
# Train SSGC (symmetric MDK, -定向性), SWE-GNN (-MDK) and Flow-MDK (hybrid)
# on the merged real-master families (B1: mdx+zxh+wqh) at the paper budget
# encoded in the configs (G=64, 150 epochs, batch 8, curriculum 15), then
# evaluate in-domain (B1 test) and on the B2 real historical exams.
# Timestamped run dirs + results.csv registry, mirroring
# scripts/run_partA_paper.sh.
#
# Server usage (A100 GPU1):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_L3_B1B2_paper.sh 2>&1 \
#       | tee data/L3_B1B2_paper_$(date +%Y%m%d_%H%M%S).log
set -e
cd "$(dirname "$0")/.."

STAMP=$(date +%Y%m%d_%H%M%S)
echo "run stamp: $STAMP (runs/L3_B1_paper_<name>_$STAMP, registry runs/results.csv)"

python scripts/make_family_all.py

COMMON="data.root=data/real_cases/family_all train.early_stop_patience=99"

train_and_eval () {
    local name=$1 config=$2
    local run_dir=runs/L3_B1_paper_${name}_${STAMP}
    echo "=== [L3:$name] training (paper settings from $config) -> $run_dir ==="
    python scripts/train.py --config "$config" --set \
        out_dir=$run_dir $COMMON 2>&1 | tail -3
    echo "=== [L3:$name] B1 in-domain (test split) ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test 2>&1 | tail -2
    echo "=== [L3:$name] B2 real historical exams (zero-shot) ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split val \
        --data-root data/real_cases/scenarios_1d 2>&1 | tail -7
}

train_and_eval swegnn configs/1d_swegnn_official.yaml
train_and_eval flow_mdk configs/1d_flow_mdk.yaml
train_and_eval ssgc configs/1d_ssgc_symmetric.yaml

echo "L3_PAPER_ABLATION_DONE"
