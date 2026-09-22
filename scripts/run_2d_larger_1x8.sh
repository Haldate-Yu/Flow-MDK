#!/usr/bin/env bash
# A2 · 大域（12.8 km）零样本评测补齐：官方 1×8 SWE-GNN 臂 + -MDK 消融臂。
#
# 背景：S2 首轮评测（09-21 16:45）早于 1×8 重训完成（09-22 09:02），且
# run_2d_larger_domain.sh 硬编码 runs/MS4_2d_*——大域表因此缺 swegnn(1×8) 与
# -MDK 两行，恰是与 flow_mdk 对照最关键的两行。真值已挂好（24 场景 QC 全
# PASS），本脚本纯推理，A100 上 ~20 min；断点安全（json 存在即跳过）。
#
# 用法（服务器）：
#   bash scripts/run_2d_larger_1x8.sh 2>&1 | tee data/2d_larger_1x8_$(date +%m%d).log
# 可选：先复核 1×8 权重在 2D test 上与本轮记录一致（预期 last≈0.745 / best≈0.616；
# 会追加带新时间戳的 registry 行，属有意为之的验证记录）：
#   VERIFY=1 bash scripts/run_2d_larger_1x8.sh 2>&1 | tee ...
set -eo pipefail
cd "$(dirname "$0")/.."

ROOT="${ROOT:-data/scenarios_2d_larger}"
SEEDS=(${SEEDS:-0 1 2})

twin_eval () {  # twin_dir run_dir checkpoint data_root
    local twin=$1 run_dir=$2 ckpt=$3 root=$4
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$ckpt" --split test --data-root "$root" 2>&1 | tail -1
}

# ---- 步骤 0（可选）：1×8 权重完整性复核 --------------------------------
if [ "${VERIFY:-0}" = "1" ]; then
    for seed in "${SEEDS[@]}"; do
        run=runs/MS4b_2d_swegnn_s${seed}
        [ -f "$run/last.pt" ] || { echo "[skip] $run not found"; continue; }
        echo "--- [verify] swegnn(1x8) s${seed} last.pt on 2D test (expect ~0.745)"
        python scripts/evaluate.py --config $run/config.yaml --checkpoint $run/last.pt \
            --split test 2>&1 | tail -1
        echo "--- [verify] swegnn(1x8) s${seed} best.pt on 2D test (expect ~0.616)"
        twin_eval runs/ptbest_MS4b_2d_swegnn_s${seed} "$run" "$run/best.pt" data/scenarios_2d_family
    done
fi

# ---- 步骤 1：官方 1×8 臂 → 大域零样本 ----------------------------------
for seed in "${SEEDS[@]}"; do
    run=runs/MS4b_2d_swegnn_s${seed}
    [ -f "$run/last.pt" ] || { echo "[skip] $run not found"; continue; }
    if [ ! -f "$run/eval_test_scenarios_2d_larger.json" ]; then
        echo "--- [larger-domain zero-shot] swegnn(1x8) s${seed} last.pt"
        python scripts/evaluate.py --config $run/config.yaml --checkpoint $run/last.pt \
            --split test --data-root "${ROOT}" 2>&1 | tail -1
    else
        echo "[skip] $run/eval_test_scenarios_2d_larger.json exists"
    fi
    if [ -f "$run/best.pt" ] && [ ! -f "runs/ptbest_MS4b_2d_swegnn_s${seed}/eval_test_scenarios_2d_larger.json" ]; then
        echo "--- [larger-domain zero-shot] swegnn(1x8) s${seed} best.pt"
        twin_eval runs/ptbest_MS4b_2d_swegnn_s${seed} "$run" "$run/best.pt" "${ROOT}"
    fi
done

# ---- 步骤 2：-MDK（同 harness、无扩散分支）→ 大域零样本 ----------------
for seed in "${SEEDS[@]}"; do
    run=runs/L16_mdkoff_2d_s${seed}
    [ -f "$run/last.pt" ] || { echo "[skip] $run not found"; continue; }
    if [ ! -f "$run/eval_test_scenarios_2d_larger.json" ]; then
        echo "--- [larger-domain zero-shot] -MDK s${seed} last.pt"
        python scripts/evaluate.py --config $run/config.yaml --checkpoint $run/last.pt \
            --split test --data-root "${ROOT}" 2>&1 | tail -1
    fi
    if [ -f "$run/best.pt" ] && [ ! -f "runs/ptbest_L16_mdkoff_2d_s${seed}/eval_test_scenarios_2d_larger.json" ]; then
        echo "--- [larger-domain zero-shot] -MDK s${seed} best.pt"
        twin_eval runs/ptbest_L16_mdkoff_2d_s${seed} "$run" "$run/best.pt" "${ROOT}"
    fi
done

echo "2D_LARGER_1X8_DONE"
echo "  fetch: runs/MS4b_2d_swegnn_s*/eval_test_scenarios_2d_larger.json"
echo "         runs/ptbest_MS4b_2d_swegnn_s*/eval_test_scenarios_2d_larger.json"
echo "         runs/L16_mdkoff_2d_s*/eval_test_scenarios_2d_larger.json"
echo "         runs/ptbest_L16_mdkoff_2d_s*/eval_test_scenarios_2d_larger.json"
echo "         runs/results.csv   data/2d_larger_1x8_*.log"
