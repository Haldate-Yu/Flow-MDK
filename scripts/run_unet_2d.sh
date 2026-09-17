#!/usr/bin/env bash
# U-Net 2D baseline at the E5 paper budget, 3 seeds (round 3, M5 baseline
# table). configs/2d_baseline_unet.yaml mirrors the MS4_2d_* budget exactly
# (G-equivalent width 32 -> ~0.47M params, batch 8, H=8 curriculum 15,
# 150 epochs); only the processor differs (CNN on the 64x64 grid vs
# message passing). Run dirs unet_2d_s<seed> fold by model name in
# summarize_runs.py.
#
#   summarise:  python scripts/summarize_runs.py --prefix unet_2d --ks
#
# If the L12 real-2D exam roots are present, the zero-shot dual-protocol
# evals run too (full-horizon on exams_2d + training-view H=8 on exams_2d_h8);
# otherwise they are skipped (run them locally after fetch, as in L12).
#
# Server usage (A100 GPU1; ~1.5-2.5 h per run, ~5-8 h total):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_unet_2d.sh 2>&1 \
#       | tee data/unet_2d_$(date +%m%d).log
set -e
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})

best_eval () {  # run_dir [evaluate.py args...] -> ptbest twin eval
    local run_dir=$1; shift
    local twin=runs/ptbest_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$run_dir/best.pt" "$@" 2>&1 | tail -1
}

for seed in "${SEEDS[@]}"; do
    run=runs/unet_2d_s${seed}
    if [ -f "$run/config.yaml" ]; then echo "[skip] $run exists"; continue; fi
    echo "=== [unet_2d s${seed}] training -> $run ==="
    python scripts/train.py --config configs/2d_baseline_unet.yaml --set \
        out_dir=$run seed=${seed} 2>&1 | tail -3
    python scripts/evaluate.py --config $run/config.yaml \
        --checkpoint $run/last.pt --split test 2>&1 | tail -1
    best_eval $run --split test

    if [ -d data/real_cases/exams_2d ]; then
        echo "--- [unet_2d s${seed}] L12 zero-shot exams (full horizon)"
        python scripts/evaluate.py --config $run/config.yaml \
            --checkpoint $run/last.pt --split test \
            --data-root data/real_cases/exams_2d 2>&1 | tail -1
    fi
    if [ -d data/real_cases/exams_2d_h8 ]; then
        echo "--- [unet_2d s${seed}] L12 zero-shot exams (H=8 training view)"
        python scripts/evaluate.py --config $run/config.yaml \
            --checkpoint $run/last.pt --split test --steps 8 \
            --data-root data/real_cases/exams_2d_h8 2>&1 | tail -1
    fi
done

echo "UNET_2D_DONE"
