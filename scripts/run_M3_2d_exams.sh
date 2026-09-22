#!/usr/bin/env bash
# Local backfill of the round-6 real-2D exam evals (G6/G7 checkpoints).
#
# Why this exists separately: run_M3_2d_baselines.sh trains on the A100, but
# the exam roots (data/real_cases/exams_2d, exams_2d_h8) are built locally by
# build_real_2d_exam.py. When they are absent on the server the exam pass there
# skips; run this on the machine that has the roots, after the round-6 run dirs
# and their ptbest_ twins are fetched. Eval only — no training path at all, so
# it can never start a 2D training job by accident.
#
# Protocol: identical to L12 and to the exam pass in run_M3_2d_baselines.sh —
# full horizon on exams_2d (--steps 48; mdx_2d caps itself at 28), training-view
# H=8 on exams_2d_h8 (--steps 8), last.pt in-dir plus best.pt via the ptbest
# twin. Evaluations are gated on the eval json, so re-running fills gaps only
# and never duplicates registry rows.
#
# Arms: gcn / gat / unet_e6 (round-6 baselines) and mdkoff (the L16 6L harness
# with mdk.use=false). mdkoff closes the mechanism trio on the real exams —
# directed (flow_mdk) / no diffusion branch (-MDK) / symmetric (ssgc) — which is
# what decides whether the full-horizon divergence comes from the MDK branch or
# from the splitting harness itself. Local checkpoints + local exam roots are
# sufficient: no server round-trip needed (3060 handles the 65k-node meshes).
#
# U-Net is structurally rejected by the 65 126-node unstructured roots
# (baselines/unet.py raises on any node count that is not a multiple of the
# 64x64 grid). That rejection is a reported result — the GNN structural
# advantage — so it is recorded and the pass continues rather than aborting.
#
# Usage:  bash scripts/run_M3_2d_exams.sh
#   65k-node inference fits the local 3060 unfragmented (L12 precedent);
#   expect a few minutes per eval.
set -eo pipefail
cd "$(dirname "$0")/.."

ARMS=(${ARMS:-gcn gat unet_e6 mdkoff})
SEEDS=(${SEEDS:-0 1 2})
EXAM_ROOTS=(data/real_cases/exams_2d data/real_cases/exams_2d_h8)

exam_eval () {  # run_dir ckpt root steps label -> distinguishes rejection from failure
    local run_dir=$1 ckpt=$2 root=$3 steps=$4 label=$5
    local json="${run_dir}/eval_test_$(basename "$root").json"
    if [ -f "$json" ]; then echo "[exam] skip ${label} (json exists)"; return 0; fi
    echo "--- [exam] ${label}"
    local out
    if out=$(python scripts/evaluate.py --config "${run_dir}/config.yaml" \
        --checkpoint "$ckpt" --data-root "$root" --split test --steps "$steps" 2>&1); then
        echo "$out" | tail -1
    else
        echo "$out" | tail -2
        if echo "$out" | grep -q "grid domains only"; then
            echo "[exam] ${label}: STRUCTURALLY REJECTED (grid CNN vs unstructured mesh) — expected, recorded as such"
        else
            echo "[exam] ${label}: FAILED — not the structural rejection, investigate"
        fi
    fi
}

for arm in "${ARMS[@]}"; do
    for seed in "${SEEDS[@]}"; do
        case $arm in
            gcn)     run=runs/MS4_2d_gcn_s${seed} ;;
            gat)     run=runs/MS4_2d_gat_s${seed} ;;
            unet_e6) run=runs/unet_2d_e6_s${seed} ;;
            # L16 深度匹配 -MDK 臂（6L 分裂层 harness，mdk.use=false）：补它的
            # 考卷评测后，机制三元组（定向 flow_mdk / 无扩散分支 -MDK / 对称
            # ssgc）在真实考卷上就齐了 —— 这是判定「全时程发散是 MDK 分支
            # 还是 harness 所致」的唯一缺环。纯推理，无训练路径。
            mdkoff)  run=runs/L16_mdkoff_2d_s${seed} ;;
            *) echo "unknown arm $arm"; exit 1 ;;
        esac
        [ -f "$run/last.pt" ] || { echo "[exam] skip ${run} (not fetched/trained)"; continue; }
        for i in "${!EXAM_ROOTS[@]}"; do
            root="${EXAM_ROOTS[$i]}"
            steps=48
            [ "$root" = data/real_cases/exams_2d_h8 ] && steps=8
            [ -d "$root" ] || { echo "[exam] skip ${root} (absent)"; continue; }
            exam_eval "$run" "$run/last.pt" "$root" "$steps" "$(basename "$run") ${root} last.pt"
            if [ "$arm" = unet_e6 ]; then
                echo "[exam] $(basename "$run"): grid-CNN excluded from the real roots (unet.py structural check) — remaining protocols skipped"
                break
            fi
            best_twin="runs/ptbest_$(basename "$run")"
            [ -f "$best_twin/config.yaml" ] && exam_eval "$best_twin" "$run/best.pt" "$root" "$steps" \
                "$(basename "$run") ${root} best.pt"
        done
    done
done
echo "M3_2D_EXAMS_DONE"
