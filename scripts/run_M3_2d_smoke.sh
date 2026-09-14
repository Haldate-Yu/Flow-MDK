#!/usr/bin/env bash
# M3 first 2D training smoke (E4, server).
#
# Pushes the synthetic 2D pilot (data/scenarios_2d: 20 scenarios, 64x64 grids
# @ 100 m, TELEMAC-2D truth, split.json 14/3/3) through the standard trainer —
# both the SWE-GNN skeleton and the MDK hybrid, 3 epochs each, batch 4
# (4 x 4096 nodes). The 2D graph/schema was unit-tested but never trained;
# run this BEFORE committing any long 2D budget and keep the log — a failure
# here is the deliverable (it names the wiring gap).
#
# Server usage (A100 GPU1):
#   CUDA_VISIBLE_DEVICES=1 bash scripts/run_M3_2d_smoke.sh 2>&1 \
#       | tee data/M3_2d_smoke_$(date +%Y%m%d_%H%M%S).log
set -e
cd "$(dirname "$0")/.."

smoke () {
    local name=$1 config=$2
    local run_dir=runs/M3_2d_smoke_${name}
    echo "=== [2D smoke:${name}] training (3 epochs) -> $run_dir ==="
    python scripts/train.py --config "$config" --set \
        out_dir=$run_dir data.name=2d_grid data.root=data/scenarios_2d \
        train.max_epochs=3 train.curriculum_steps=1 train.batch_size=4 \
        2>&1 | tail -5
    echo "=== [2D smoke:${name}] eval last.pt (2D test split) ==="
    python scripts/evaluate.py --config $run_dir/config.yaml \
        --checkpoint $run_dir/last.pt --split test 2>&1 | tail -2
}

smoke swegnn   configs/1d_swegnn_official.yaml
smoke flow_mdk configs/1d_flow_mdk.yaml

echo "M3_2D_SMOKE_DONE"
