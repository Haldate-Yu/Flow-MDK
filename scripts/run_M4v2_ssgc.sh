#!/usr/bin/env bash
# M4 v2 addendum: SSGC (symmetric-diffusion) arm on the coupled family.
#
# Round-6 gap closure. The M4 v2 formal round compared flow_mdk (main/nocons)
# against the SWE-GNN shallow skeleton only, so the directed-vs-symmetric
# question that E5/L16 settled on 2D was never closed on the coupling domain.
# This arm trains SSGC (same 6L x 1hop harness as flow_mdk, symmetric
# diffusion) at the verbatim M4 v2 recipe, giving the coupling verdict the
# same mechanism trio as the 2D verdict. Run dirs M4v2_ssgc_s<seed> fold
# alongside M4v2_{main,nocons}_flow_mdk_s<seed> and M4v2_swegnn_s<seed>:
#
#   python scripts/summarize_runs.py --prefix M4v2 --ks
#
# Recipe: verbatim run_M4_v2_family.sh (G=64, batch 4, 60 epochs, curriculum
# to H=8 in 5-epoch steps, val_horizon 8, early stop after curriculum, EMA
# 0.99 after curriculum — the v1 correction, not E61's 0.999) with K=4, the
# same physical mapping the main arm uses (dt_chain/dt_partA ~ 2.8, cf. L14
# dt x3 -> K4).
#
# BATCH 2 (round-6 OOM diagnosis, 2026-09-20): the shared A100 carried ~42 GiB
# of co-tenant allocations when this arm first ran; batch 4 peaked at 37.3 GiB
# and OOM'd on the next 382 MiB. Same failure mode as the round-5 swegnn arm
# (OOM at batch 4 -> retrained at batch 2, protocol disclosed in the paper and
# deck) — so this arm defaults to batch 2 under the same disclosure. Raise
# back with BATCH_SIZE=4 only on a verified-empty GPU.
#
# Per-run cost ~4-5 h on one A100 at batch 2 (~13-15 h for 3 seeds).
#
# Server usage (A100 GPU1):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_M4v2_ssgc.sh 2>&1 \
#       | tee data/M4v2_ssgc_$(date +%m%d).log
set -eo pipefail
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})
BATCH_SIZE="${BATCH_SIZE:-2}"
K_CHAIN=4

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

for seed in "${SEEDS[@]}"; do
    run=runs/M4v2_ssgc_s${seed}
    if [ -f "$run/last.pt" ]; then echo "[skip] $run done"; continue; fi
    echo "=== [M4v2 ssgc s${seed}] training -> $run ==="
    python scripts/train.py --config configs/1d_ssgc_symmetric.yaml --set \
        out_dir=$run data.root=data/real_cases/coupled_chain_family \
        data.name=1d_chain seed=${seed} \
        model.hidden_dim=64 train.batch_size=${BATCH_SIZE} \
        train.max_epochs=60 train.curriculum_steps=5 \
        train.early_stop_patience=99 \
        train.val_horizon=8 \
        train.early_stop_after_curriculum=true \
        train.ema_decay=0.99 train.ema_after_curriculum=true \
        model.mdk.num_steps=${K_CHAIN} 2>&1 | tail -3
    python scripts/evaluate.py --config $run/config.yaml \
        --checkpoint $run/last.pt --split test 2>&1 | tail -1
    twin_eval ptbest "$run" "$run/best.pt"
    if [ -f "$run/ema.pt" ]; then
        twin_eval ptema "$run" "$run/ema.pt"
    fi
done
echo "M4V2_SSGC_DONE"
