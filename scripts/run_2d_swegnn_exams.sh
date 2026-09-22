#!/usr/bin/env bash
# Real-2D exam pass for the 1x8 SWE-GNN arms (EVAL ONLY - no training path).
#
# Why a separate script: run_M3_2d_exams.sh hardcodes its arm list
# (gcn/gat/unet_e6/mdkoff) and would need editing; this one takes the run dirs
# from the environment instead, so it can score any checkpoint set without
# touching the original.
#
# Protocol is identical to L12 / run_M3_2d_baselines.sh / run_M3_2d_exams.sh:
#   data/real_cases/exams_2d      full horizon (--steps 48; mdx_2d caps itself
#                                 at 28 internally)
#   data/real_cases/exams_2d_h8   training-view horizon (--steps 8)
#   last.pt in-dir + best.pt via the runs/ptbest_* twin
# Evaluations are gated on the eval json, so re-running fills gaps only and
# never duplicates registry rows.
#
# Run this on the machine that HOLDS THE EXAM ROOTS (the roots are built
# locally by build_real_2d_exam.py and are not on the training server), after
# the new run dirs have been fetched from the server. Pure inference: 65k-node
# meshes fit the local 3060 unfragmented (L12 precedent).
#
# Usage:
#   bash scripts/run_2d_swegnn_exams.sh                     # the three 1x8 seeds
#   RUNS="runs/MS4_2d_swegnn_s0" bash scripts/run_2d_swegnn_exams.sh   # before/after control
set -eo pipefail
cd "$(dirname "$0")/.."

RUNS=(${RUNS:-runs/MS4b_2d_swegnn_s0 runs/MS4b_2d_swegnn_s1 runs/MS4b_2d_swegnn_s2})
EXAM_ROOTS=(data/real_cases/exams_2d data/real_cases/exams_2d_h8)
STEPS_LONG=48
STEPS_H8=8

exam_eval () {  # run_dir ckpt root steps label
    local run_dir=$1 ckpt=$2 root=$3 steps=$4 label=$5
    local json="${run_dir}/eval_test_$(basename "$root").json"
    if [ -f "$json" ]; then echo "[exam] skip ${label} (json exists)"; return 0; fi
    echo "--- [exam] ${label}"
    local out
    if out=$(python scripts/evaluate.py --config "${run_dir}/config.yaml" \
        --checkpoint "$ckpt" --data-root "$root" --split test --steps "$steps" 2>&1); then
        echo "$out" | tail -1
    else
        echo "$out" | tail -3
        echo "[exam] ${label}: FAILED - investigate (not a known structural rejection)"
    fi
}

for run in "${RUNS[@]}"; do
    if [ ! -f "$run/last.pt" ]; then echo "[exam] skip $run (not fetched/trained)"; continue; fi
    for root in "${EXAM_ROOTS[@]}"; do
        [ -d "$root" ] || { echo "[exam] skip ${root} (absent)"; continue; }
        steps=$STEPS_LONG
        [ "$root" = data/real_cases/exams_2d_h8 ] && steps=$STEPS_H8
        exam_eval "$run" "$run/last.pt" "$root" "$steps" "$(basename "$run") ${root} last.pt"
        best_twin="runs/ptbest_$(basename "$run")"
        [ -f "$best_twin/config.yaml" ] && [ -f "$run/best.pt" ] && \
            exam_eval "$best_twin" "$run/best.pt" "$root" "$steps" \
                      "$(basename "$run") ${root} best.pt"
    done
done
echo "1X8_2D_EXAMS_DONE"
