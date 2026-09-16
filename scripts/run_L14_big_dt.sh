#!/usr/bin/env bash
# L14 · big-dt trade-off experiment (PLAN M2 closure; SWE-GNN Fig. 8 analog).
#
# Question: as the model time step grows, does physics-matched MDK diffusion
# (K scaling with sqrt(dt)) keep the deep gated model stable where fixed
# per-hop message passing cannot? Control at dt x1 = the existing E3 runs
# (MS4_partA_{flow_mdk,swegnn}_{s0,s1,s2}, same configs/seeds/budget).
#
# Design (pre-registered):
#   dt multipliers m in {2, 3}  (m=4 kills 34 scenarios: only 96/130 have
#                               enough frames for H=8 windows)
#   arms per m:
#     flow_mdk  6L x 1 hop, K = ceil(K0*sqrt(m))  (K0=2 -> K=3 at m=2, K=4 at m=3)
#     swegnn    2L x 8 hops (official skeleton; per-hop receptive field fixed)
#   3 seeds each, paper budget verbatim (G=64, 150 epochs, curriculum 15,
#   batch 8), A-test eval with last.pt + best.pt (ptbest twin).
#
# Data: data/scenarios_partA_v2_dt{2,3} (built by scripts/subsample_scenarios_dt.py,
# frame-0 + every m-th frame; native dt ~600-870 s -> effective ~1.2-2.6 km..s
# scale x2/x3). Confound to note in judgment: windows per scenario shrink with
# m (p50 11 -> 4 at m=3), so training sees fewer samples.
#
# Server usage (A100 GPU1):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_L14_big_dt.sh 2>&1 \
#       | tee data/L14_big_dt_$(date +%Y%m%d_%H%M%S).log
set -e
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})
MULTS=(${MULTS:-2 3})
K0=2

twin_eval () {  # prefix run_dir checkpoint
    local prefix=$1 run_dir=$2 ckpt=$3
    local twin=runs/${prefix}_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$ckpt" --split test 2>&1 | tail -1
}

for m in "${MULTS[@]}"; do
  case $m in
    2) K=3 ;;  # ceil(2*sqrt(2)) = 3
    3) K=4 ;;  # ceil(2*sqrt(3)) = 4
    *) echo "unsupported multiplier $m (K mapping only pre-registered for 2,3)"; exit 1 ;;
  esac
  for seed in "${SEEDS[@]}"; do
    run=runs/L14_dt${m}_flow_mdk_K${K}_s${seed}
    if [ ! -f "$run/config.yaml" ]; then
      echo "=== [L14 dt x${m} flow_mdk K=${K} s${seed}] training -> $run ==="
      python scripts/train.py --config configs/1d_flow_mdk.yaml --set \
        out_dir=$run data.root=data/scenarios_partA_v2_dt${m} \
        model.mdk.num_steps=${K} seed=${seed} \
        train.early_stop_patience=99 2>&1 | tail -3
      python scripts/evaluate.py --config $run/config.yaml \
        --checkpoint $run/last.pt --split test 2>&1 | tail -1
      twin_eval ptbest "$run" "$run/best.pt"
    else
      echo "[skip] $run exists"
    fi

    run=runs/L14_dt${m}_swegnn_s${seed}
    if [ ! -f "$run/config.yaml" ]; then
      echo "=== [L14 dt x${m} swegnn s${seed}] training -> $run ==="
      python scripts/train.py --config configs/1d_swegnn_official.yaml --set \
        out_dir=$run data.root=data/scenarios_partA_v2_dt${m} \
        seed=${seed} train.early_stop_patience=99 2>&1 | tail -3
      python scripts/evaluate.py --config $run/config.yaml \
        --checkpoint $run/last.pt --split test 2>&1 | tail -1
      twin_eval ptbest "$run" "$run/best.pt"
    else
      echo "[skip] $run exists"
    fi
  done
done
echo "L14_BIG_DT_DONE"
