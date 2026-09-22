#!/usr/bin/env bash
# M3 2D addendum: vanilla-GNN baselines + U-Net E6-recipe repair (round 6).
#
# Two closures on the synthetic 2D family (data/scenarios_2d_family):
#
#   gcn/gat   — the vanilla message-passing rows. The E5 main table has no
#               vanilla GNN baseline (U-Net covers the CNN side, SSGC the
#               symmetric side), and reviewers ask for one. OLD recipe (no E6
#               flags) so the rows are protocol-comparable with the E5 table.
#               Run dirs MS4_2d_gcn_s<seed> / MS4_2d_gat_s<seed> fold into the
#               existing MS4_2d_* summary family.
#
#   unet_e6   — U-Net retrained under the E6 selection governance. The
#               round-3 U-Net best.pt (10.5±11.8) was unreliable — trained
#               before the E6 recipe existed, drift pathology cross-architecture.
#               Run dirs unet_2d_e6_s<seed> sit next to the round-3
#               unet_2d_s<seed> rows (both fold by model name in summarize).
#
# Real-2D exam evals run for every arm after training (L12 protocol, dual
# protocol last.pt/best.pt, full horizon + H=8 training view). U-Net is
# structurally rejected by the 65 126-node unstructured exam roots — that is a
# reported result (GNN structural advantage), so the rejection is recorded and
# the pass continues; it must not abort the arm. Exam evals are gated on the
# eval json, so re-running backfills only what is missing.
#
#   python scripts/summarize_runs.py --prefix MS4_2d --prefix unet_2d --ks
#
# Recipe: verbatim run_M3_2d_paper.sh COMMON (150 epochs, curriculum 15,
# batch 8, early_stop_patience=99) for gcn/gat; the E6 flags for unet_e6
# follow run_E61_recipe_validation.sh (val_horizon 8, early stop after
# curriculum with patience 10, EMA after curriculum, decay 0.999 at this
# 150-epoch budget — M4's 0.99 correction was for 60-epoch budgets).
#
# Per-run cost ~1.5-2.5 h on one A100 (~13-20 h for the default 9 runs;
# split arms across GPUs or run overnight).
#
# Server usage (A100 GPU1):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_M3_2d_baselines.sh 2>&1 \
#       | tee data/M3_2d_baselines_$(date +%m%d).log
# or split arms:
#   CUDA_VISIBLE_DEVICES=0 ARMS="gcn gat" bash scripts/run_M3_2d_baselines.sh
#   CUDA_VISIBLE_DEVICES=1 ARMS="unet_e6" bash scripts/run_M3_2d_baselines.sh
set -eo pipefail
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})
ARMS=(${ARMS:-gcn gat unet_e6})
EMA_DECAY="${EMA_DECAY:-0.999}"

COMMON="data.name=2d_grid data.root=data/scenarios_2d_family \
    train.max_epochs=150 train.curriculum_steps=15 train.batch_size=8 \
    train.early_stop_patience=99"

twin_eval () {  # prefix run_dir checkpoint [extra evaluate.py args]
    local prefix=$1 run_dir=$2 ckpt=$3; shift 3
    local twin=runs/${prefix}_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$ckpt" "$@" 2>&1 | tail -1
}

for arm in "${ARMS[@]}"; do
    for seed in "${SEEDS[@]}"; do
        case $arm in
            gcn)     run=runs/MS4_2d_gcn_s${seed}
                     base=configs/1d_baseline_gcn.yaml
                     extra="" ;;
            gat)     run=runs/MS4_2d_gat_s${seed}
                     base=configs/1d_baseline_gat.yaml
                     extra="" ;;
            unet_e6) run=runs/unet_2d_e6_s${seed}
                     base=configs/2d_baseline_unet.yaml
                     extra="train.val_horizon=8 train.early_stop_after_curriculum=true train.early_stop_patience=10 train.ema_decay=${EMA_DECAY} train.ema_after_curriculum=true" ;;
            *) echo "unknown arm $arm"; exit 1 ;;
        esac
        # artifact-based skip (round-5 lesson): a crashed run leaves config.yaml
        # behind and must be retrained
        if [ -f "$run/last.pt" ]; then echo "[skip] $run done"; continue; fi
        echo "=== [2D ${arm} s${seed}] training -> $run ==="
        python scripts/train.py --config "$base" --set \
            out_dir=$run ${COMMON} seed=${seed} ${extra} 2>&1 | tail -3
        python scripts/evaluate.py --config $run/config.yaml \
            --checkpoint $run/last.pt --split test 2>&1 | tail -1
        twin_eval ptbest "$run" "$run/best.pt" --split test
        if [ -f "$run/ema.pt" ]; then
            twin_eval ptema "$run" "$run/ema.pt" --split test
        fi
    done
done

# ------------------------------------------------------- real-2D exams ----
# Zero-shot exam evals (L12 protocol: full horizon on exams_2d, training-view
# H=8 on exams_2d_h8; last.pt in-dir + best.pt via the ptbest twin). Kept out
# of the training loop and gated on the checkpoint alone, so re-running this
# script backfills exam rows for runs that were already trained.
#
# U-Net is structurally excluded from these roots: baselines/unet.py raises
# when the node count is not a multiple of the 64x64 grid and the exams are
# 65 126-node unstructured meshes. That rejection is itself a reported result
# (GNN structural advantage, deck slide 11), so it is attempted once per run
# and recorded rather than treated as a script failure.
EXAM_ROOTS=(data/real_cases/exams_2d data/real_cases/exams_2d_h8)

exam_eval () {  # run_dir ckpt root steps label -> distinguishes rejection from failure
    local run_dir=$1 ckpt=$2 root=$3 steps=$4 label=$5
    local json="runs/$(basename "$run_dir")/eval_test_$(basename "$root").json"
    if [ -f "$json" ]; then echo "[exam] skip ${label} (json exists)"; return 0; fi
    echo "--- [exam] ${label}"
    local out
    if out=$(python scripts/evaluate.py --config "$run_dir/config.yaml" \
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
        esac
        [ -f "$run/last.pt" ] || { echo "[exam] skip ${run} (not trained)"; continue; }
        for i in "${!EXAM_ROOTS[@]}"; do
            root="${EXAM_ROOTS[$i]}"
            steps=48; [ "$root" = data/real_cases/exams_2d_h8 ] && steps=8
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
echo "M3_2D_BASELINES_DONE"
