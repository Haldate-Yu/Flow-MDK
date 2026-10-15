#!/usr/bin/env bash
# W1 · Card 1（plan/card1_wlev1_channel_fix.md）——水位通道修正后的再验证。
#
# 背景：论文全部已报告实验的配置为 elevation_feature_idx: 0（水位通道 = 面积 + h）。
# 合成域（均匀 100 m 网格）不受影响；真实网格（面积 2~879 m2）上方向门控一致率
# ~49%（近乎随机），即真实算例上方向门控实际未参与。本卡在修正通道（idx=1，
# w = 床面高程 + h）下重训关键臂并全链路重评，产出"方向机制在真实网格上生效"
# 的直接证据；同时补齐 all-dry 第二无技巧地板（此前只有 persist 地板）。
#
# 内容：
#   步骤 0  数据预检（verify_server_data.py，警告不阻断）
#   步骤 1  门控方向诊断（纯 CPU：复现 49% 并给出逐考卷反转占比）
#   步骤 2  无技巧地板：all-dry × 4 数据域 + persist × 2 考卷域（纯推理）
#   步骤 3  重训 4 臂 × 3 种子（flow_mdk / swegnn1x8 / ssgc / mdkoff）
#   步骤 4  合成域 test 评测（last + best 双协议）
#   步骤 5  大域 12.8 km 零样本评测（last + best）
#   步骤 6  真实考卷评测（H=8 与全时程，last + best）
#   步骤 7  生成 W1 对比矩阵（docs/wlev1_matrix.{md,csv}）
#
# 全程幂等：训练以 runs/<run>/config.yaml 存在为跳过条件，评测以目标 json
# 存在为跳过条件；中断后重跑自动续。
#
# 用法（服务器，A100）：
#   bash scripts/run_wlev1_card1.sh 2>&1 | tee data/wlev1_card1_$(date +%Y%m%d_%H%M%S).log
# 可选环境变量：
#   SEEDS="0 1 2"        参与种子（默认 0 1 2）
#   ARMS="flow_mdk ..."  参与臂（默认全部 4 臂）
#   SKIP_TRAIN=1         只做评测/地板/诊断（要求权重已就位）
set -eo pipefail
cd "$(dirname "$0")/.."

SEEDS=(${SEEDS:-0 1 2})
ALL_ARMS=("flow_mdk 2d_flow_mdk_wlev1" "swegnn1x8 2d_swegnn1x8_wlev1" \
          "ssgc 2d_ssgc_symmetric_wlev1" "mdkoff 2d_mdkoff_wlev1")
REQUESTED_ARMS=(${ARMS:-flow_mdk swegnn1x8 ssgc mdkoff})

FAMILY_ROOT="data/scenarios_2d_family"
LARGER_ROOT="data/scenarios_2d_larger"
EXAM_H8_ROOT="data/real_cases/exams_2d_h8"
EXAM_FULL_ROOT="data/real_cases/exams_2d"

twin_eval () {  # twin_dir run_dir checkpoint data_root
    local twin=$1 run_dir=$2 ckpt=$3 root=$4
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$ckpt" --split test --data-root "$root" 2>&1 | tail -1
}

floor_eval () {  # twin_dir config root
    local twin=$1 config=$2 root=$3
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$config" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint none --split test --data-root "$root" 2>&1 | tail -1
}

floor_eval_if_needed () {  # twin_dir config root（按目标 json 幂等）
    local twin=$1 config=$2 root=$3
    local leaf json
    leaf=$(basename "$root")
    json="$twin/eval_test_${leaf}.json"
    if [ -f "$json" ]; then
        echo "[skip] $json exists"
    else
        floor_eval "$twin" "$config" "$root"
    fi
}

# ---- 步骤 0：数据预检 -----------------------------------------------------
echo "=== [W1 步骤 0] 数据预检（警告不阻断） ==="
python scripts/verify_server_data.py 2>&1 | tee data/wlev1_verify_$(date +%m%d).log || \
    echo "[warn] 数据预检存在失败项，请人工核对上方日志后再继续"

# ---- 步骤 1：门控方向诊断（真实考卷，纯 CPU） ----------------------------
if [ ! -f docs/wlev1_gate_agreement.json ]; then
    echo "=== [W1 步骤 1] 门控方向诊断（面积通道污染 → 反转占比） ==="
    python scripts/diagnose_gate_agreement.py \
        --data-root "$EXAM_FULL_ROOT" --out docs/wlev1_gate_agreement.json
else
    echo "[skip] docs/wlev1_gate_agreement.json exists"
fi

# ---- 步骤 2：无技巧地板（all-dry × 4 域；persist × 2 考卷域） ------------
echo "=== [W1 步骤 2] 无技巧地板（纯推理） ==="
floor_eval_if_needed runs/W1_floor_alldry_2d_family configs/wlev1/2d_baseline_alldry.yaml "$FAMILY_ROOT"
floor_eval_if_needed runs/W1_floor_alldry_2d_larger configs/wlev1/2d_baseline_alldry.yaml "$LARGER_ROOT"
floor_eval_if_needed runs/W1_floor_alldry_exams_2d_h8 configs/wlev1/2d_baseline_alldry.yaml "$EXAM_H8_ROOT"
floor_eval_if_needed runs/W1_floor_alldry_exams_2d    configs/wlev1/2d_baseline_alldry.yaml "$EXAM_FULL_ROOT"
# persist 地板：合成域/大域已有 floor_persist_* 行；考卷两域此前缺失，补齐
if [ ! -f runs/W1_floor_persist_exams_2d_h8/eval_test_exams_2d_h8.json ]; then
    mkdir -p runs/W1_floor_persist_exams_2d_h8
    sed "s#^out_dir:.*#out_dir: runs/W1_floor_persist_exams_2d_h8#; s#^  arch: baseline_alldry#  arch: baseline_persistence#" \
        configs/wlev1/2d_baseline_alldry.yaml > runs/W1_floor_persist_exams_2d_h8/config.yaml
    python scripts/evaluate.py --config runs/W1_floor_persist_exams_2d_h8/config.yaml \
        --checkpoint none --split test --data-root "$EXAM_H8_ROOT" 2>&1 | tail -1
fi
if [ ! -f runs/W1_floor_persist_exams_2d/eval_test_exams_2d.json ]; then
    mkdir -p runs/W1_floor_persist_exams_2d
    sed "s#^out_dir:.*#out_dir: runs/W1_floor_persist_exams_2d#; s#^  arch: baseline_alldry#  arch: baseline_persistence#" \
        configs/wlev1/2d_baseline_alldry.yaml > runs/W1_floor_persist_exams_2d/config.yaml
    python scripts/evaluate.py --config runs/W1_floor_persist_exams_2d/config.yaml \
        --checkpoint none --split test --data-root "$EXAM_FULL_ROOT" 2>&1 | tail -1
fi

# ---- 步骤 3：重训 4 臂 × 3 种子 ------------------------------------------
for arm_spec in "${ALL_ARMS[@]}"; do
    arm=${arm_spec%% *}; cfg=${arm_spec#* }
    keep=0
    for a in "${REQUESTED_ARMS[@]}"; do
        if [ "$a" = "$arm" ]; then keep=1; fi
    done
    if [ "$keep" != "1" ]; then echo "[skip] arm $arm 不在本轮 ARMS 中"; continue; fi
    for seed in "${SEEDS[@]}"; do
        run=runs/W1_2d_${arm}_s${seed}
        if [ "${SKIP_TRAIN:-0}" = "1" ]; then
            echo "[skip] SKIP_TRAIN=1 -> $run"
        elif [ -f "$run/config.yaml" ] && [ -f "$run/history.json" ]; then
            # history.json 只在 train.py 的 fit() 完整结束后写出；
            # 被杀/中断的运行只有 config.yaml，会自动重训（幂等续跑）。
            echo "[skip] $run complete"
        else
            if [ -f "$run/config.yaml" ]; then
                echo "=== [W1 步骤 3] $run 不完整（缺 history.json），作废旧评测并重训 ==="
                rm -f "$run"/eval_test*.json
                rm -rf "runs/ptbest_W1_2d_${arm}_s${seed}"
            else
                echo "=== [W1 步骤 3] 训练 $arm s${seed} -> $run ==="
            fi
            python scripts/train.py --config "configs/wlev1/${cfg}.yaml" --set \
                out_dir=$run seed=${seed} train.early_stop_patience=99 2>&1 | tail -3
        fi
        # 步骤 4：合成域 test（last + best）
        if [ ! -f "$run/eval_test.json" ]; then
            echo "--- [W1 步骤 4] $arm s${seed} last.pt @ 2D test"
            python scripts/evaluate.py --config $run/config.yaml \
                --checkpoint $run/last.pt --split test 2>&1 | tail -1
        fi
        if [ -f "$run/best.pt" ] && [ ! -f runs/ptbest_W1_2d_${arm}_s${seed}/eval_test.json ]; then
            echo "--- [W1 步骤 4] $arm s${seed} best.pt @ 2D test"
            twin_eval runs/ptbest_W1_2d_${arm}_s${seed} "$run" "$run/best.pt" "$FAMILY_ROOT"
        fi
        # 步骤 5：大域零样本（last + best）
        if [ ! -f "$run/eval_test_scenarios_2d_larger.json" ]; then
            echo "--- [W1 步骤 5] $arm s${seed} last.pt @ 大域零样本"
            python scripts/evaluate.py --config $run/config.yaml \
                --checkpoint $run/last.pt --split test --data-root "$LARGER_ROOT" 2>&1 | tail -1
        fi
        if [ -f "$run/best.pt" ] && [ ! -f runs/ptbest_W1_2d_${arm}_s${seed}/eval_test_scenarios_2d_larger.json ]; then
            echo "--- [W1 步骤 5] $arm s${seed} best.pt @ 大域零样本"
            twin_eval runs/ptbest_W1_2d_${arm}_s${seed} "$run" "$run/best.pt" "$LARGER_ROOT"
        fi
        # 步骤 6：真实考卷 H=8 与全时程（last + best）
        for root in "$EXAM_H8_ROOT" "$EXAM_FULL_ROOT"; do
            leaf=$(basename "$root")
            if [ ! -f "$run/eval_test_${leaf}.json" ]; then
                echo "--- [W1 步骤 6] $arm s${seed} last.pt @ $leaf"
                python scripts/evaluate.py --config $run/config.yaml \
                    --checkpoint $run/last.pt --split test --data-root "$root" 2>&1 | tail -1
            fi
            if [ -f "$run/best.pt" ] && [ ! -f runs/ptbest_W1_2d_${arm}_s${seed}/eval_test_${leaf}.json ]; then
                echo "--- [W1 步骤 6] $arm s${seed} best.pt @ $leaf"
                twin_eval runs/ptbest_W1_2d_${arm}_s${seed} "$run" "$run/best.pt" "$root"
            fi
        done
    done
done

# ---- 步骤 7：W1 对比矩阵 --------------------------------------------------
echo "=== [W1 步骤 7] 生成对比矩阵 ==="
python scripts/build_wlev1_matrix.py

echo "W1_CARD1_DONE"
echo "  fetch（回传本地清单，详见实验卡 plan/card1_wlev1_channel_fix.md §6）:"
echo "    runs/results.csv"
echo "    runs/W1_2d_{flow_mdk,swegnn1x8,ssgc,mdkoff}_s*/  (config.yaml history.json last.pt best.pt eval_*.json)"
echo "    runs/ptbest_W1_2d_*/  (config.yaml eval_*.json)"
echo "    runs/W1_floor_alldry_*/ runs/W1_floor_persist_*/  (config.yaml eval_*.json)"
echo "    docs/wlev1_gate_agreement.json  docs/wlev1_matrix.md  docs/wlev1_matrix.csv"
echo "    data/wlev1_*.log"
