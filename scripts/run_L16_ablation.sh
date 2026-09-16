#!/usr/bin/env bash
# L16 · -MDK ablation at matched depth (M5 baseline table closure).
#
# The E3/E5 headline comparison (flow_mdk 6L+MDK vs swegnn 2Lx8) confounds
# the MDK branch with depth/hops. This round runs the DEPTH-MATCHED ablation:
# the same 6L x 1-hop splitting layer with model.mdk.use=false — i.e. exactly
# the Flow-MDK harness minus the diffusion branch (config
# configs/1d_swegnn_baseline.yaml). Paired controls: E3 MS4_partA_flow_mdk_s*
# (1D) and E5 MS4_2d_flow_mdk_s* (2D) — same seeds, same budget, the ONLY
# difference is the mdk flag. 12 runs total (2 domains x 3 seeds... 6 runs).
#
#   1D: data/scenarios_partA_v2, A-test, G=64 150ep curriculum 15
#   2D: data/scenarios_2d_family, 2D test, same budget batch 8
#
# Judgment: if -MDK collapses to swegnn-2Lx8-level or worse (1D) / loses the
# x5 margin (2D), the gated-MDK branch (not depth) carries the advantage.
#
# Server usage (A100 GPU1; can run alongside round-1 leftovers):
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

train_arm () {  # domain seed
    local domain=$1 seed=$2
    local run split
    if [ "$domain" = partA ]; then
        run=runs/L16_mdkoff_partA_s${seed}; split=test
        local extra="data.root=data/scenarios_partA_v2"
    else
        run=runs/L16_mdkoff_2d_s${seed}; split=test
        local extra="data.name=2d_grid data.root=data/scenarios_2d_family train.batch_size=8"
    fi
    if [ -f "$run/config.yaml" ]; then echo "[skip] $run exists"; return; fi
    echo "=== [L16 -MDK ${domain} s${seed}] training -> $run ==="
    python scripts/train.py --config configs/1d_swegnn_baseline.yaml --set \
        out_dir=$run seed=${seed} train.early_stop_patience=99 ${extra} 2>&1 | tail -3
    python scripts/evaluate.py --config $run/config.yaml \
        --checkpoint $run/last.pt --split ${split} 2>&1 | tail -1
    twin_eval ptbest "$run" "$run/best.pt" --split ${split}
}

for seed in "${SEEDS[@]}"; do
    train_arm partA $seed
    train_arm 2d $seed
done
echo "L16_ABLATION_DONE"
