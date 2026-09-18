#!/usr/bin/env bash
# M4 v2 formal round: coupled-family training (12 scenarios, round 5).
#
# Data: data/real_cases/coupled_chain/mdx_chain_fam{000..011}/ built on this
# server by `python scripts/build_coupled_family.py --num 12 --seed 11`
# (round 4, 12/12 ok). scripts/prepare_coupled_family_root.py flattens them
# into data/real_cases/coupled_chain_family/ with a 9/1/2 split (fam000 =
# v1-parity draw and fam011 = strongest draw -> test; fam010 -> val) without
# touching the v1 root.
#
# Arms (ARMS env, default all three):
#   main    flow_mdk 6L, K=4, interface flux-continuity loss ON
#   nocons  flow_mdk 6L, K=4, conservation loss OFF (ablation)
#   swegnn  2L x 8 hops baseline control (SWE-GNN-faithful skeleton)
#
# K=4 follows the L14 operational mapping K = ceil(K0*sqrt(m)) with
# m = dt_chain / dt_partA = 1800/647 ~ 2.8 (same as L14's dt x3 -> K4);
# the mixed 1D/2D edge-resolution caveat is logged in the progress notes.
# Conservation loss (main arm): train.interface_cons_weight=0.1; the term
# is a training-only regulariser (val stays the pure data loss) and its
# per-node boundary length ell is auto-calibrated from the scenario truth.
#
# Recipe: v1 feasibility protocol (G=64, batch 4, curriculum to H=8 in
# 5-epoch steps, E6 selection governance) with the two M4 fixes from the
# v1 round: ema_decay 0.999 -> 0.99 (0.999 diverged h at 60-epoch budgets).
#
# Per-run cost estimate: ~2.5 h on one A100 (60 ep x ~50 batches of 4 x 65k
# nodes) -> ~7.5 h per arm for 3 seeds. Split arms across GPUs with e.g.
#   CUDA_VISIBLE_DEVICES=1 ARMS="main nocons" bash scripts/run_M4_v2_family.sh
#   CUDA_VISIBLE_DEVICES=0 ARMS="swegnn"     bash scripts/run_M4_v2_family.sh
# or run everything serially on one GPU overnight.
# pipefail: without it the `| tail` pipelines swallow training failures
# (round-5 lesson: three OOM crashes ran straight through as "success")
set -eo pipefail
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})
ARMS=(${ARMS:-main nocons swegnn})
BATCH_SIZE="${BATCH_SIZE:-4}"
K_CHAIN=4
CONS_WEIGHT=0.1

echo "=== prep: flatten family root + split ==="
python scripts/prepare_coupled_family_root.py

twin_eval () {  # prefix run_dir checkpoint
    local prefix=$1 run_dir=$2 ckpt=$3
    local twin=runs/${prefix}_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$ckpt" --split test 2>&1 | tail -1
}

for arm in "${ARMS[@]}"; do
    for seed in "${SEEDS[@]}"; do
        case $arm in
            main)   run=runs/M4v2_main_flow_mdk_s${seed}
                    base=configs/1d_flow_mdk.yaml
                    extra="model.mdk.num_steps=${K_CHAIN} train.interface_cons_weight=${CONS_WEIGHT}" ;;
            nocons) run=runs/M4v2_nocons_flow_mdk_s${seed}
                    base=configs/1d_flow_mdk.yaml
                    extra="model.mdk.num_steps=${K_CHAIN}" ;;
            swegnn) run=runs/M4v2_swegnn_s${seed}
                    base=configs/1d_swegnn_official.yaml
                    extra="" ;;
            *) echo "unknown arm $arm"; exit 1 ;;
        esac
        # skip on the training ARTIFACT, not config.yaml: a crashed run leaves
        # config.yaml behind (stamped pre-training) and must be retrained
        if [ -f "$run/last.pt" ]; then echo "[skip] $run done"; continue; fi
        echo "=== [M4v2 ${arm} s${seed}] training -> $run ==="
        python scripts/train.py --config "$base" --set \
            out_dir=$run data.root=data/real_cases/coupled_chain_family \
            data.name=1d_chain seed=${seed} \
            model.hidden_dim=64 train.batch_size=${BATCH_SIZE} \
            train.max_epochs=60 train.curriculum_steps=5 \
            train.early_stop_patience=99 \
            train.val_horizon=8 \
            train.early_stop_after_curriculum=true \
            train.ema_decay=0.99 train.ema_after_curriculum=true \
            ${extra} 2>&1 | tail -3
        python scripts/evaluate.py --config $run/config.yaml \
            --checkpoint $run/last.pt --split test 2>&1 | tail -1
        twin_eval ptbest "$run" "$run/best.pt"
        if [ -f "$run/ema.pt" ]; then
            twin_eval ptema "$run" "$run/ema.pt"
        fi
    done
done
echo "M4_V2_FAMILY_DONE"
