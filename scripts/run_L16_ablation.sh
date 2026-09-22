#!/usr/bin/env bash
# L16 · -MDK ablation at matched depth (M5 baseline table closure, 2D).
#
# The earlier headline comparison (flow_mdk 6L+MDK vs the retired 2x8-depth
# swegnn arm) confounded the MDK branch with depth/hops. This round runs the
# DEPTH-MATCHED ablation:
# the same 6L x 1-hop splitting layer with model.mdk.use=false — i.e. exactly
# the Flow-MDK harness minus the diffusion branch (config
# configs/2d_swegnn_baseline.yaml). Paired control: E5 MS4_2d_flow_mdk_s* —
# same seeds, same budget, the ONLY difference is the mdk flag.
#
#   2D: data/scenarios_2d_family, 2D test, G=64 150ep curriculum 15 batch 8
#
# Judgment: if -MDK loses the flow_mdk margin (2D: 0.529 vs 0.835 vs ssgc
# 1.820, all pairwise significant), the directed MDK branch — not depth —
# carries the advantage (paper slide "机制消融").
#
# Server usage (A100 GPU1):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_L16_ablation.sh 2>&1 \
#       | tee data/L16_ablation_$(date +%Y%m%d_%H%M%S).log
set -e
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})

twin_eval () {  # prefix run_dir checkpoint --split <split>
    local prefix=$1 run_dir=$2 ckpt=$3; shift 3
    local twin=runs/${prefix}_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$ckpt" "$@" 2>&1 | tail -1
}

for seed in "${SEEDS[@]}"; do
    run=runs/L16_mdkoff_2d_s${seed}
    if [ -f "$run/config.yaml" ]; then echo "[skip] $run exists"; continue; fi
    echo "=== [L16 -MDK 2D s${seed}] training -> $run ==="
    python scripts/train.py --config configs/2d_swegnn_baseline.yaml --set \
        out_dir=$run seed=${seed} train.early_stop_patience=99 2>&1 | tail -3
    python scripts/evaluate.py --config $run/config.yaml \
        --checkpoint $run/last.pt --split test 2>&1 | tail -1
    twin_eval ptbest "$run" "$run/best.pt" --split test
done
echo "L16_ABLATION_DONE"
