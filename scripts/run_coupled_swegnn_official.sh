#!/usr/bin/env bash
# Coupled 1D-2D SWE-GNN arm at the **official depth** (1 outer layer x K=8 hops).
#
# Trains configs/coupled_swegnn_official.yaml on the 12-scenario coupled family
# at the coupled round's budget (60 epochs, curriculum 5, batch 2, E6 selection
# governance + EMA 0.99) and evaluates the same three protocols as
# run_M4_v2_family.sh:
#   last.pt -> run dir          (--split test)   test = fam000 + fam011
#   best.pt -> runs/ptbest_M4v2b_swegnn_s*       (twin dir)
#   ema.pt  -> runs/ptema_M4v2b_swegnn_s*        (twin dir)
#
# The only intended difference from runs/M4v2_swegnn_s* is the depth
# (16 -> 8 message-passing hops per step). For full paper fidelity
# (patience 30) run with:  EXTRA="train.early_stop_patience=30" bash ...
#
# ── Data root: dedicated, split-pinned (do not "simplify" this) ────────────
# The v2 arms all trained on data/real_cases/coupled_chain_family with a 9/1/2
# split. That shared root is ALSO the one the S1/M4v3 expansion rewrites
# (prepare_coupled_family_root.py overwrites split.json, and its default train
# list is "every fam* in the chain root minus test/val" — after an expansion
# that silently becomes 17 scenarios). So this script builds a DEDICATED root
# (…_family_v2, symlinks to the same npz) and then pins its split.json to the
# canonical 9/1/2. Consequences:
#   * no ordering constraint against S1 — both can run whenever;
#   * the run is comparable with the existing M4v2 arms (same 12 scenarios,
#     same split, same data bytes).
# Pre-existing extra npz in the root (e.g. fam012+) are ignored, because
# scripts/train.py reads the split.json name lists.
#
# Usage (server, one A100; ~1 h per seed with 8 hops instead of 16):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_coupled_swegnn_official.sh 2>&1 \
#       | tee data/1x8_coupled_$(date +%m%d).log
set -eo pipefail
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})
CONFIG=${CONFIG:-configs/coupled_swegnn_official.yaml}
PREFIX=${PREFIX:-M4v2b_swegnn}
EXTRA=${EXTRA:-}
BATCH_SIZE=${BATCH_SIZE:-2}          # keep 2: the M4v2 swegnn arm ran at 2 (batch-4 OOM)
CHAIN_ROOT=data/real_cases/coupled_chain
FAMILY_ROOT=${FAMILY_ROOT:-data/real_cases/coupled_chain_family_v2}

echo "=== prep: dedicated v2 family root + pinned split ==="
if [ -n "${SKIP_PREP:-}" ]; then
    echo "[prep] SKIP_PREP set - reusing $FAMILY_ROOT as is"
else
    python scripts/prepare_coupled_family_root.py \
        --chain-root "$CHAIN_ROOT" --family-root "$FAMILY_ROOT"
fi

python - "$FAMILY_ROOT" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
train = [f"mdx_chain_fam{i:03d}" for i in range(1, 10)]   # 001..009
val   = ["mdx_chain_fam010"]
test  = ["mdx_chain_fam000", "mdx_chain_fam011"]           # v1 parity + strongest draw
need  = train + val + test
missing = [n for n in need if not (root / f"{n}.npz").exists()]
if missing:
    raise SystemExit(f"[guard] FATAL: missing scenarios in {root}: {missing}")
(root / "split.json").write_text(
    json.dumps({"train": train, "val": val, "test": test}, indent=1), encoding="utf-8")
extra = sorted(p.stem for p in root.glob("*.npz") if p.stem not in need)
print(f"[guard] {root}: split pinned to train {len(train)} / val {len(val)} / test {len(test)}")
if extra:
    print(f"[guard] {len(extra)} extra npz present and ignored by split.json: {extra}")
PY

if [ -n "${PREP_ONLY:-}" ]; then
    echo "[prep] PREP_ONLY set - data root ready and split pinned; stopping before training"
    echo "[prep] verify: cat $FAMILY_ROOT/split.json  (expect train 9 / val 1 / test 2)"
    exit 0
fi

twin_eval () {  # prefix run_dir checkpoint
    local prefix=$1 run_dir=$2 ckpt=$3
    local twin=runs/${prefix}_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$ckpt" --split test 2>&1 | tail -1
}

for seed in "${SEEDS[@]}"; do
    run=runs/${PREFIX}_s${seed}
    if [ -f "$run/last.pt" ]; then echo "[skip] $run done"; continue; fi
    echo "=== [1x8 coupled s${seed}] training -> $run ==="
    python scripts/train.py --config "$CONFIG" --set \
        out_dir=$run seed=${seed} train.batch_size=${BATCH_SIZE} ${EXTRA} 2>&1 | tail -3
    echo "=== [1x8 coupled s${seed}] eval last.pt (test split) ==="
    python scripts/evaluate.py --config "$run/config.yaml" \
        --checkpoint "$run/last.pt" --split test 2>&1 | tail -1
    twin_eval ptbest "$run" "$run/best.pt"
    if [ -f "$run/ema.pt" ]; then
        twin_eval ptema "$run" "$run/ema.pt"
    fi
done

echo "1X8_COUPLED_SWEGNN_DONE"
for seed in "${SEEDS[@]}"; do
    echo "  fetch: runs/${PREFIX}_s${seed}  runs/ptbest_${PREFIX}_s${seed}  runs/ptema_${PREFIX}_s${seed}"
done
