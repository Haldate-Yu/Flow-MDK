# 服务器实验执行流程（Remote Server Runbook）

本仓库所有实验均可在 Linux 服务器上复现。数据与结果通过 `datasets/`
（Git LFS）同步。以下为从零到产出 Part A/B 结果的完整流程。

## 0. 前置条件

- Linux + Docker（复算/家族批跑需要）；NVIDIA GPU + driver ≥ 535（训练可选）
- Python ≥ 3.10；git-lfs ≥ 3.x（`git lfs install`）
- 仓库同步：`git clone <remote> && cd Flow-MDK && git lfs pull`
  （`datasets/` 约 3.3 GB，含 TELEMAC 源码快照、SWE-GNN 官方 raw_datasets、
  真实工程、全部 npz 与 Mascaret workdir）

## 1. 环境

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .            # torch/torch_geometric 按平台自动装
# GPU 训练（可选）：
pip install torch --index-url https://download.pytorch.org/whl/cu126 --upgrade
python -c "import torch; print(torch.cuda.is_available())"
```

## 2. 求解器镜像（仅 Mascaret 批跑/复算需要）

```bash
# datasets/telemac-mascaret-v8p4r0/ 内含源码快照与 docker/ 构建文件；
# docker/ 构建上下文需与源码树同级（见 third_party/telemac/README.md）：
cp -r datasets/telemac-mascaret-v8p4r0 /tmp/build/tree
cp datasets/telemac-mascaret-v8p4r0/docker/{Dockerfile,build.sh,entrypoint.sh,setenv.sh,systel.cfg} /tmp/build/
docker build -t flow-mdk-telemac:v8p4r0 /tmp/build        # 约 20-40 min
```

## 3. 数据生成（如需重新生成；`datasets/` 已含成品可跳过）

```bash
# Part A：合成 1D 场景族（参考解内置，无需 docker）
python scripts/generate_scenarios_1d.py --out data/scenarios_1d --num 50

# Part B：真实工况导入（wqh/zxh 完整工程已内置于 data/real_sources/；
# mdx/ybs/xjz 来自 schinta 模板，将 --source 指向 datasets/real_projects/）
python scripts/import_real_cases.py --source datasets/real_projects

# Part B 家族批跑（每场景 ~30-50 s，串行；GPU 与此无关）
python scripts/run_real_family.py --mode validate --case wqh
python scripts/run_real_family.py --mode family --family-dir data/real_cases/family_wqh
```

## 4. 训练 + 评测（一条链，见 `scripts/run_partA_experiments.sh`）

```bash
bash scripts/run_partA_experiments.sh          # 四模型：训练 + A test + B 零样本
# 单模型重跑示例（GPU 在 config.device 设 "cuda" 或 --set device=cuda）：
python scripts/train.py --config configs/1d_swegnn_official.yaml --set \
    out_dir=runs/partA_swegnn data.root=data/scenarios_1d device=cuda \
    train.max_epochs=150 train.curriculum_steps=4 train.early_stop_patience=99
python scripts/evaluate.py --config runs/partA_swegnn/config.yaml \
    --checkpoint runs/partA_swegnn/last.pt --split test \
    --data-root data/real_cases/family_wqh
```

GPU 显存预算：G=64、batch 8、100 节点图 ≈ 1-2 GB；4 GB 卡可将 batch 提到 16-32
或把 hidden_dim 提到 64（论文设定）。

## 5. 论文级预算建议（服务器）

| 实验 | 配置 | 预计时长（单卡） |
|---|---|---|
| Part A 四模型（论文设定 G=64, L=2×8/3, 150 epochs） | `configs/1d_swegnn_official.yaml` 等，`device=cuda` | 每模型 1-3 h |
| B1 训练 → B2 考卷（M2 主消融：SSGC / SWE-GNN / Flow-MDK） | `data.root=data/real_cases/family_*`，MDKConfig 开关见 `docs/results_partA.md` | 每模型 <1 h |
| A→B 零样本矩阵 | `scripts/evaluate.py --data-root ...` | 分钟级 |

结果全部落在 `runs/<name>/`（config/history/eval json/last.pt），随后
`python scripts/archive_datasets.py` 刷新 `datasets/runs/` 归档并随 LFS 同步。
