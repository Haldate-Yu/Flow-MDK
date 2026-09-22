#!/usr/bin/env bash
# M4 v3 · expanded coupled family (20 scenarios, split with a 5-scenario test
# set) — the S1 supplementary experiment for the narrowed 2D + coupled paper.
#
# Why: the M4 v2 family's test split has only 2 scenarios, so
# summarize_runs.py cannot run KS ("no domain with >=2 models and >=5
# scenarios") and every coupling comparison (×1.24/×1.36, directed-vs-symmetric
# closure, strongest-condition divergence) currently has NO significance
# support — while coupling is the paper's main novelty. See
# plan/supplementary_experiments_plan.md S1.
#
# Steps
#   1. grow the family 12 -> 20 with the SAME seed, so fam000-011 are
#      byte-identical and fam012-019 are appended (condition draws are keyed by
#      index since the 2026-09-21 fix) — 8 new scenarios, ~17 min CPU each;
#   2. hard gate: assert the 8 new condition draws are the expected ones
#      (a wrong draw means duplicate scenarios and an invalid test set);
#   3. flatten + split 13/2/5, keeping fam000 (v1 parity) and fam011 (strongest
#      draw) in test as the comparison anchors;
#   4. train × 3 seeds at the verbatim M4 v2 recipe, all arms at ONE batch size
#      (v2 mixed batch 4 and batch 2; a uniform M4v3 batch removes that
#      within-generation protocol mix);
#   5. eval last.pt (in-dir) + best.pt (ptbest twin) + ema.pt (ptema twin).
#
# Run dirs M4v3_<arm>_s<seed> sit next to the M4v2 arms and fold with
#   python scripts/summarize_runs.py --prefix M4v3 --ks
#
# Server usage (A100; batch 2 ≈ 4-5 h/run, batch 4 ≈ 2.5 h/run):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_M4v3_family.sh 2>&1 \
#       | tee data/M4v3_$(date +%m%d).log
#   split arms across GPUs with ARMS=..., e.g.
#   CUDA_VISIBLE_DEVICES=0 ARMS="swegnn" BATCH_SIZE=4 bash scripts/run_M4v3_family.sh
set -eo pipefail
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd "$(dirname "$0")/.."

FAMILY_NUM="${FAMILY_NUM:-20}"
SEEDS=(${SEEDS:-0 1 2})
# conservation arm (main) is optional: the penalty's negative result is already
# established on the v2 family; C3 needs the nocons / swegnn / ssgc trio.
ARMS=(${ARMS:-nocons swegnn ssgc})
BATCH_SIZE="${BATCH_SIZE:-2}"
K_CHAIN=4

# test spans the q_scale range (0.61 - 1.97) and keeps both anchors
TEST_NAMES="mdx_chain_fam000 mdx_chain_fam004 mdx_chain_fam011 mdx_chain_fam012 mdx_chain_fam015"
VAL_NAMES="mdx_chain_fam010 mdx_chain_fam014"

echo "=== step 1/3: grow the family to ${FAMILY_NUM} scenarios (idempotent) ==="
python scripts/build_coupled_family.py --num "${FAMILY_NUM}" --seed 11

echo "=== step 2/3: gate — the 8 new condition draws must be exactly these ==="
python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path("scripts").resolve()))
from build_coupled_family import _draw_conditions

EXPECTED = {  # precomputed from seed 11 (documented in supplementary_experiments_plan.md S1)
    12: (1.3305955442978417, 1.1868997575387104),
    13: (1.0299122825906721, 1.2732762431592348),
    14: (0.8529518475013709, 1.4417621470227868),
    15: (1.801000327763622, 0.9030077369822809),
    16: (1.2006098101074067, 1.0217159140269636),
    17: (0.6246754966028636, 1.5167554466002942),
    18: (1.144923038071753, 0.9181530399696753),
    19: (1.5100435359138662, 0.9617728222304306),
}
draws = _draw_conditions(11, 20)
bad = [(i, draws[i], exp) for i, exp in EXPECTED.items()
       if abs(draws[i][0] - exp[0]) > 1e-12 or abs(draws[i][1] - exp[1]) > 1e-12]
for i, got, exp in bad:
    print(f"[gate] fam{i:03d} MISMATCH got={got} expected={exp}")
if bad:
    raise SystemExit("[gate] FAILED — the draw stream is shifted; scenarios would be "
                     "duplicates of fam001+. Do NOT train on this family.")

# invariant that actually catches a shifted stream: new draws must be distinct
# from every existing scenario's conditions
existing = [draws[i] for i in range(1, 12)]
clash = [(i, draws[i]) for i in range(12, 20)
         if any(abs(draws[i][0] - q) < 1e-9 and abs(draws[i][1] - t) < 1e-9
                for q, t in existing)]
if clash:
    raise SystemExit(f"[gate] FAILED — new draws duplicate existing scenarios: {clash}")
print("[gate] OK — fam012-019 draws match the pre-registered values and are "
      "distinct from fam001-011")
PY

echo "=== step 3/3: flatten + split (5-scenario test set) ==="
python scripts/prepare_coupled_family_root.py --test ${TEST_NAMES} --val ${VAL_NAMES}

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
            main)   run=runs/M4v3_main_flow_mdk_s${seed}
                    base=configs/1d_flow_mdk.yaml
                    extra="model.mdk.num_steps=${K_CHAIN} train.interface_cons_weight=0.1" ;;
            nocons) run=runs/M4v3_nocons_flow_mdk_s${seed}
                    base=configs/1d_flow_mdk.yaml
                    extra="model.mdk.num_steps=${K_CHAIN}" ;;
            swegnn) run=runs/M4v3_swegnn_s${seed}
                    base=configs/1d_swegnn_official.yaml
                    extra="" ;;
            ssgc)   run=runs/M4v3_ssgc_s${seed}
                    base=configs/1d_ssgc_symmetric.yaml
                    extra="model.mdk.num_steps=${K_CHAIN}" ;;
            *) echo "unknown arm $arm"; exit 1 ;;
        esac
        # skip on the training artifact (a crashed run leaves config.yaml behind)
        if [ -f "$run/last.pt" ]; then echo "[skip] $run done"; continue; fi
        echo "=== [M4v3 ${arm} s${seed}] training -> $run (batch ${BATCH_SIZE}) ==="
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
echo "M4V3_FAMILY_DONE"
