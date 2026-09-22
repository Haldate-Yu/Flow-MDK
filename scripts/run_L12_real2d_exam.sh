#!/usr/bin/env bash
# L12 remaining: real-2D exam — zero-shot transfer of the E4/E5 2D models
# (MS4_2d, 3 models x 3 seeds, last.pt + best.pt protocols) onto the real
# TELEMAC-2D projects (wqh_2d / mdx_2d), no retraining.
#
# Prereq: python scripts/build_real_2d_exam.py   (exam npz + split.json)
# Runs everywhere the checkpoints live (local 3060 or server A100); each
# eval rolls both scenarios to their full horizon (28/48 steps @ 1800 s).
#
# Usage: bash scripts/run_L12_real2d_exam.sh
set -euo pipefail
cd "$(dirname "$0")/.."

EXAM_ROOT="${EXAM_ROOT:-data/real_cases/exams_2d}"
STEPS="${STEPS:-48}"   # wqh_2d full horizon; mdx_2d caps itself at 28

for model in swegnn flow_mdk ssgc; do
  for seed in 0 1 2; do
    # swegnn = the official-depth 1x8 arm (MS4b_ prefix)
    run="MS4_2d_${model}_s${seed}"
    if [ "$model" = swegnn ]; then run="MS4b_2d_swegnn_s${seed}"; fi
    echo "=== [real2d exam] ${run}: last.pt ==="
    python scripts/evaluate.py \
      --config "runs/${run}/config.yaml" \
      --checkpoint "runs/${run}/last.pt" \
      --data-root "${EXAM_ROOT}" --split test --steps "${STEPS}"
    echo "=== [real2d exam] ${run}: best.pt ==="
    python scripts/evaluate.py \
      --config "runs/ptbest_${run}/config.yaml" \
      --checkpoint "runs/${run}/best.pt" \
      --data-root "${EXAM_ROOT}" --split test --steps "${STEPS}"
  done
done
echo "L12_REAL2D_EXAM_DONE"
