#!/usr/bin/env bash
# L9 · solver-runtime baselines for the ->B2 speedup cells (server round 3).
#
# The ->B2 speedup = solver runtime / proxy rollout time; 4 of the 5 B2
# exam cells were None (no measured solver baseline) and the 3 rerun-truth
# runtimes were measured on the local 3060 host while the rollout times
# came from this server. This round re-times all 5 B2 cases HERE (same
# environment as the inference timing), then refreshes every ->B2 (val)
# eval so the speedup cells fill in.
#
# Prerequisites (docs/server_setup.md):
#   - solver image imported: docker load < datasets/docker_images/flow-mdk-telemac_v8p4r0p1.tar.gz
#   - real sources restored: datasets/real_sources/{wqh,zxh} per §3.2
#   - data/real_cases/scenarios_1d/ synced (the 5 exam npz)
#
# Routes (scripts/time_b2_solver.py):
#   wqh / zxh / mdx_upstream  -> validated full rerun (runtime + truth refresh)
#   mdx                       -> timing-only scratch rerun (historical .opt
#                                truth untouched; 15.4% template deviation known)
#   mdx_downstream            -> npz-geometry rebuild timing (L8-safe; truth
#                                untouched)
#
# Server usage:
#   bash scripts/run_L9_speedup_baselines.sh 2>&1 | tee data/L9_speedup_$(date +%m%d).log
set -e
cd "$(dirname "$0")/.."

echo "=== step 1: time the 5 B2 solver baselines ==="
python scripts/time_b2_solver.py --all

echo "=== step 2: refresh ->B2 (val) evals to fill the speedup cells ==="
shopt -s nullglob
for j in runs/*/eval_val_scenarios_1d.json; do
    d=$(dirname "$j"); run=$(basename "$d")
    case "$run" in
        ptbest_*) base=${run#ptbest_}; ckpt=runs/$base/best.pt ;;
        ptema_*)  base=${run#ptema_};  ckpt=runs/$base/ema.pt ;;
        *)        base=$run;           ckpt=runs/$base/last.pt ;;
    esac
    if [ ! -f "$ckpt" ]; then echo "[skip] $ckpt missing"; continue; fi
    echo "--- ->B2 eval: $run"
    python scripts/evaluate.py --config "$d/config.yaml" --checkpoint "$ckpt" \
        --split val --data-root data/real_cases/scenarios_1d 2>&1 | tail -1
done

echo "L9_SPEEDUP_BASELINES_DONE"
