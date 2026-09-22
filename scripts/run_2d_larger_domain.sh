#!/usr/bin/env bash
# S2 · 二维更大域泛化集（12.8 km / 128×128 @ 100 m），对齐 SWE-GNN dataset 3。
#
# 为什么需要：范围收窄到「二维 + 耦合」后，「域尺寸泛化」这一轴完全缺位——
# SWE-GNN 有 dataset 3（12.8×12.8 km、g=128）作域尺寸泛化，我们没有；原版图里
# 这一轴由一维 A3 子集承担，而一维已移出正文，且一维子集不可挪用到二维。
#
# 最省版本（默认）：用 64×64（6.4 km）训练好的检查点在新域上做**零样本**评测，
# 不需要任何新训练——检验「训练域 6.4 km → 未见 12.8 km 域」的退化，口径与
# SWE-GNN dataset 3 一致。可选 TRAIN=1 再补一组在大域上训练的臂（见末尾）。
#
# 阶段
#   1. 生成 128×128 场景族（默认 24 个）；split-mode=generalization →
#      split.json 全部归 "test"，整根即泛化集，一次 evaluate 覆盖全部
#   2. 挂真值：逐个调用 run_telemac2d_docker.py（幂等：meta.solver != pending 则跳过）
#   3. 零样本评测：flow_mdk / swegnn / ssgc / gcn / gat × 3 种子 × last/best 双协议
#
# 成本估算：64×64 真值实测 73 s/场景 → 128×128 为 4 倍单元，估 5–10 min/场景
#           → 24 场景约 2–4 h CPU；评测约 1 h（无训练）。
#
# 服务器用法：
#   bash scripts/run_2d_larger_domain.sh 2>&1 | tee data/2d_larger_$(date +%m%d).log
# 可选（大域上训练一组臂，约 15 h A100）：
#   TRAIN=1 bash scripts/run_2d_larger_domain.sh
set -eo pipefail
cd "$(dirname "$0")/.."

NUM="${NUM:-24}"
ROOT="${ROOT:-data/scenarios_2d_larger}"
PREFIX="${PREFIX:-L2D}"
NCSIZE="${NCSIZE:-1}"
SEEDS=(${SEEDS:-0 1 2})
MODELS=(${MODELS:-flow_mdk swegnn ssgc gcn gat})   # U-Net 除外，见下

echo "=== 阶段 1/3：生成 ${NUM} 个 128×128 @ 100 m（12.8 km）场景 ==="
python scripts/generate_scenarios_2d_family.py \
    --num "${NUM}" --out "${ROOT}" --prefix "${PREFIX}" \
    --nx 128 --ny 128 --cell-size 100 --seed-base 500000 \
    --split-mode generalization

echo "=== 阶段 2/3：挂 TELEMAC-2D 真值（幂等，已完成场景自动跳过）==="
python - "${ROOT}" "${NCSIZE}" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

root, ncsize = Path(sys.argv[1]), sys.argv[2]
npzs = sorted(root.glob("*.npz"))
pending = []
for p in npzs:
    import numpy as np
    meta = json.loads(str(np.load(p, allow_pickle=True)["meta"]))
    if meta.get("solver") == "pending" or "runtime_s" not in meta:
        pending.append(p)
print(f"[truth] {len(npzs)} scenarios, {len(pending)} pending")
for i, p in enumerate(pending, 1):
    work = root / "_work" / p.stem
    print(f"[truth] ({i}/{len(pending)}) {p.stem} -> {work}")
    subprocess.run([sys.executable, "scripts/run_telemac2d_docker.py",
                    "--scenario", str(p), "--workdir", str(work),
                    "--ncsize", ncsize], check=True)
print("[truth] done")
PY

echo "=== 阶段 3/3：零样本评测（64×64 训练 → 12.8 km 域）==="
# U-Net 不能进这个根：128×128=16384 节点是它 64×64 网格的整数倍，
# 它不会像 65k 非结构网格那样报错，而是**静默 reshape**（batch=4）→ 结果无意义。
twin_eval () {  # prefix run_dir checkpoint
    local prefix=$1 run_dir=$2 ckpt=$3
    local twin=runs/${prefix}_${run_dir#runs/}
    mkdir -p "$twin"
    sed "s#^out_dir:.*#out_dir: $twin#" "$run_dir/config.yaml" > "$twin/config.yaml"
    python scripts/evaluate.py --config "$twin/config.yaml" \
        --checkpoint "$ckpt" --split test --data-root "${ROOT}" 2>&1 | tail -1
}

for model in "${MODELS[@]}"; do
    for seed in "${SEEDS[@]}"; do
        run=runs/MS4_2d_${model}_s${seed}
        [ -f "$run/last.pt" ] || { echo "[skip] $run not found"; continue; }
        echo "--- [larger-domain zero-shot] ${model} s${seed} last.pt"
        python scripts/evaluate.py --config $run/config.yaml \
            --checkpoint $run/last.pt --split test --data-root "${ROOT}" 2>&1 | tail -1
        if [ -f "runs/ptbest_MS4_2d_${model}_s${seed}/config.yaml" ]; then
            echo "--- [larger-domain zero-shot] ${model} s${seed} best.pt"
            twin_eval ptbest "$run" "$run/best.pt"
        fi
    done
done

if [ "${TRAIN:-0}" = "1" ]; then
    echo "=== 可选：在大域上训练一组臂（独立 root，避免污染泛化集）==="
    # 用 70-15-15 切分另建一根；泛化集 ROOT 保持「全部 test」不变。
    TRAIN_ROOT="${TRAIN_ROOT:-data/scenarios_2d_larger_train}"
    python scripts/generate_scenarios_2d_family.py \
        --num "${NUM}" --out "${TRAIN_ROOT}" --prefix "${PREFIX}" \
        --nx 128 --ny 128 --cell-size 100 --seed-base 500000
    python - "${TRAIN_ROOT}" "${NCSIZE}" <<'PY'
import json, subprocess, sys
from pathlib import Path
import numpy as np
root, ncsize = Path(sys.argv[1]), sys.argv[2]
for p in sorted(root.glob("*.npz")):
    meta = json.loads(str(np.load(p, allow_pickle=True)["meta"]))
    if meta.get("solver") == "pending" or "runtime_s" not in meta:
        subprocess.run([sys.executable, "scripts/run_telemac2d_docker.py",
                        "--scenario", str(p), "--workdir", str(root / "_work" / p.stem),
                        "--ncsize", ncsize], check=True)
PY
    for model in flow_mdk swegnn ssgc; do
        case $model in
            flow_mdk) base=configs/2d_flow_mdk.yaml ;;
            swegnn)   base=configs/2d_swegnn_2x8.yaml ;;
            ssgc)     base=configs/2d_ssgc_symmetric.yaml ;;
        esac
        for seed in "${SEEDS[@]}"; do
            run=runs/L2d_${model}_s${seed}
            [ -f "$run/last.pt" ] && { echo "[skip] $run done"; continue; }
            echo "=== [larger-domain train] ${model} s${seed} -> $run ==="
            python scripts/train.py --config "$base" --set \
                out_dir=$run data.name=2d_grid data.root="${TRAIN_ROOT}" seed=${seed} \
                train.max_epochs=150 train.curriculum_steps=15 train.batch_size=8 \
                train.early_stop_patience=99 2>&1 | tail -3
            python scripts/evaluate.py --config $run/config.yaml \
                --checkpoint $run/last.pt --split test 2>&1 | tail -1
            twin_eval ptbest "$run" "$run/best.pt"
        done
    done
fi

echo "2D_LARGER_DOMAIN_DONE"
