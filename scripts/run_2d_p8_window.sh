#!/usr/bin/env bash
# A0（防御性，可选）· 输入窗口对照：num_previous_steps 1 → 8（9 帧输入）。
#
# 问题：2D 域内 GCN/GAT 的 h-RMSE 与"冻结输入帧"无法区分（GAT 经 rollout 证实为
# 恒等映射，corr=1.000）。审稿人可质疑"单帧输入饿死了基线"。本实验给基线 9 帧
# 上下文重训，检验它们是否开始越过 persist：
#   - 仍越不过 → "基线没在做事"的主张稳固，饿死质疑关闭；
#   - 越过了   → 当前结论是协议伪影，C1 措辞必须限定（尽早知道越好）。
#
# 口径注意：官方 previous_t=2（我们 p=1 已逐字对齐）；p=8 超出官方口径，结论只
# 用于回应"饿死"质疑，不进主对照表。persist 基线随窗口变化（冻结第 p 帧），
# 对照时要按 p=8 重算 floor（本地 A4 管线会自动处理）。
#
# 用法（服务器；默认 GAT+GCN ×3 种子 ≈ 15–30 h；~2.5 h/种子/臂）：
#   CUDA_VISIBLE_DEVICES=0 bash scripts/run_2d_p8_window.sh 2>&1 | tee data/2d_p8_$(date +%m%d).log
#   ARMS="gat" bash ...                        # 只跑 GAT（最关键的恒等映射臂）
#   ARMS="gat gcn flow_mdk" bash ...           # 加 flow_mdk p=8（我们方法是否也受益）
set -eo pipefail
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})
ARMS=(${ARMS:-gat gcn})
COMMON="data.name=2d_grid data.root=data/scenarios_2d_family \
    train.max_epochs=150 train.curriculum_steps=15 train.batch_size=8 \
    train.early_stop_patience=99"

twin_eval () {  # twin_dir run_dir checkpoint data_root
    local twin=$1 run_dir=$2 ckpt=$3 root=$4
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$ckpt" --split test --data-root "$root" 2>&1 | tail -1
}

for arm in "${ARMS[@]}"; do
    case $arm in
        gcn)      base=configs/1d_baseline_gcn.yaml ;;
        gat)      base=configs/1d_baseline_gat.yaml ;;
        flow_mdk) base=configs/1d_flow_mdk.yaml ;;
        *) echo "unknown arm $arm"; exit 1 ;;
    esac
    for seed in "${SEEDS[@]}"; do
        run=runs/MS4c_2d_${arm}p8_s${seed}
        if [ ! -f "$run/last.pt" ]; then
            echo "=== [p8 ${arm} s${seed}] training -> $run ==="
            python scripts/train.py --config "$base" --set \
                out_dir=$run model.num_previous_steps=8 ${COMMON} seed=${seed} 2>&1 | tail -3
        else
            echo "[skip] $run done"
        fi
        # 2D test（域内：是否开始越过 persist）
        echo "--- [p8 ${arm} s${seed}] eval last.pt (2D test)"
        python scripts/evaluate.py --config $run/config.yaml --checkpoint $run/last.pt \
            --split test 2>&1 | tail -1
        echo "--- [p8 ${arm} s${seed}] eval best.pt (2D test)"
        twin_eval runs/ptbest_MS4c_2d_${arm}p8_s${seed} "$run" "$run/best.pt" data/scenarios_2d_family
        # 大域零样本（多帧是否同时修复 OOD 冻结）
        echo "--- [p8 ${arm} s${seed}] eval last.pt (larger domain)"
        python scripts/evaluate.py --config $run/config.yaml --checkpoint $run/last.pt \
            --split test --data-root data/scenarios_2d_larger 2>&1 | tail -1
        echo "--- [p8 ${arm} s${seed}] eval best.pt (larger domain)"
        twin_eval runs/ptbest_MS4c_2d_${arm}p8_s${seed} "$run" "$run/best.pt" data/scenarios_2d_larger
    done
done

echo "2D_P8_WINDOW_DONE"
echo "  fetch: runs/MS4c_2d_*p8_s*/ (config.yaml eval_*.json history.json; last/best.pt 可选)"
echo "         runs/ptbest_MS4c_2d_*p8_s*/  runs/results.csv  data/2d_p8_*.log"
