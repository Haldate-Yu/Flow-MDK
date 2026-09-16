#!/usr/bin/env bash
# E6.1 · server validation of the E6 recipe (val governance) at paper budget.
#
# The E6 recipe was derived and tuned on local 3060 probes (G=32, 40 epochs,
# see docs/results_partA_swe.md E6). This round validates it at the paper
# budget on flow_mdk 6L — the drift carrier — with the SAME seeds as the E3
# controls (MS4_partA_flow_mdk_s{0,1,2}, identical config/budget, old
# recipe): the only difference is the recipe, so the comparison is paired.
#
# Recipe flags (all added 2026-09-15, default off):
#   train.val_horizon=8                    val loss always at full horizon
#                                          (fixes best.pt semantics)
#   train.early_stop_after_curriculum=true train.early_stop_patience=10
#                                          early stop only after curriculum
#                                          reaches H=8 (~ep 106)
#   train.ema_decay=0.999                  per-optimizer-step weight EMA
#   train.ema_after_curriculum=true        EMA starts at curriculum end
#                                          (E6.1; 0.999 tuned for the ~400-700
#                                          post-curriculum optimizer steps of
#                                          the paper budget; local probe used
#                                          0.995 at G=32/40ep)
#
# Each seed evals three checkpoint protocols: last.pt (in-dir), best.pt
# (ptbest twin), ema.pt (ptema twin). Judgment vs controls: valfix semantics
# should make best.pt reach/exceed control band cross-seed; ema.pt should be
# the most stable third protocol; early stop must not fire before ep 106.
#
# Server usage (A100 GPU1):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_E61_recipe_validation.sh 2>&1 \
#       | tee data/E61_recipe_$(date +%Y%m%d_%H%M%S).log
set -e
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})
EMA_DECAY="${EMA_DECAY:-0.999}"

twin_eval () {  # prefix run_dir checkpoint
    local prefix=$1 run_dir=$2 ckpt=$3
    local twin=runs/${prefix}_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$ckpt" --split test 2>&1 | tail -1
}

for seed in "${SEEDS[@]}"; do
    # E61b: the first round (E61_*) missed the data.root override and trained
    # on the deprecated scenarios_1d v1 family — not comparable with the E3
    # partA_v2 controls; those runs stay in the registry as the scenarios_1d
    # variant. This round runs the pre-registered partA_v2 pairing.
    run=runs/E61b_partA_full_s${seed}
    if [ -f "$run/config.yaml" ]; then echo "[skip] $run exists"; continue; fi
    echo "=== [E6.1 full s${seed}] training (paper budget + E6 recipe) -> $run ==="
    python scripts/train.py --config configs/1d_flow_mdk.yaml --set \
        out_dir=$run seed=${seed} \
        data.root=data/scenarios_partA_v2 \
        train.val_horizon=8 \
        train.early_stop_after_curriculum=true \
        train.early_stop_patience=10 \
        train.ema_decay=${EMA_DECAY} \
        train.ema_after_curriculum=true 2>&1 | tail -3
    python scripts/evaluate.py --config $run/config.yaml \
        --checkpoint $run/last.pt --split test 2>&1 | tail -1
    twin_eval ptbest "$run" "$run/best.pt"
    if [ -f "$run/ema.pt" ]; then
        twin_eval ptema "$run" "$run/ema.pt"
    else
        echo "[warn] $run/ema.pt missing — EMA flag not effective?"
    fi
done
echo "E61_RECIPE_VALIDATION_DONE"
