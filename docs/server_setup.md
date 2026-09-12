# 服务器实验执行流程（Remote Server Runbook）

本仓库所有实验均可在 Linux 服务器上复现。数据与结果通过 `datasets/`
（Git LFS）同步。以下为从零到产出 Part A/B 结果的完整流程。

## 0. 服务器配置结论（2026-09-11 核对）

2× A100-SXM4-80GB（driver 535 / CUDA 12.2）：**完全满足论文级实验**。
论文用 V100-32GB；实测论文级 2D 配置（4096 节点 × batch 8、G=64、2×8 跳、
H=8 rollout）峰值显存约 9.5 GB，本机 6.4 GB 卡放不下（WDDM 共享内存兜底掉速
10 倍），A100 上 batch 可开到 32+。注意 GPU0 被常驻服务占用（约 76/80 GB），
**训练请用 GPU1**（空闲 ~65 GB）。

## 0.1 指定单卡执行

所有训练/评测命令前加 `CUDA_VISIBLE_DEVICES`（torch 内编号随此变量重排，
脚本内 `device=cuda` 无需改动）：

```bash
CUDA_VISIBLE_DEVICES=1 python scripts/train.py --config configs/1d_flow_mdk.yaml --set device=cuda
# 或写入环境变量后整个会话生效：
export CUDA_VISIBLE_DEVICES=1
```

跑满 GPU1 的示例（其空闲显存可支持更大 batch / hidden_dim）：

```bash
CUDA_VISIBLE_DEVICES=1 python scripts/train.py --config configs/1d_swegnn_official.yaml \
    --set device=cuda data.root=data/scenarios_partA_v2 \
    model.hidden_dim=64 train.batch_size=32 \
    train.max_epochs=150 train.curriculum_steps=4 train.early_stop_patience=99
```

## 0.2 上传哪些文件（打包清单）

训练只需**代码 + data/ 工作数据**；`datasets/`（3.3 GB）仅在服务器上要重跑
Mascaret 批算时才需要。二选一：

```bash
# 方案 1（推荐，~1.5 GB）：代码 + 训练数据，不含 LFS 归档
# runs/ 一并排除：服务器自产 runs/（避免本机训练正在写 runs/ 时打包读到半成品）
cd /d/Projects && tar --exclude='Flow-MDK/.git' --exclude='Flow-MDK/datasets' \
    --exclude='Flow-MDK/data/partA_v2_mascaret_runs' \
    --exclude='Flow-MDK/runs' \
    -czf flow_mdk_upload.tar.gz Flow-MDK

# 方案 2（全量 ~7 GB）：连 datasets/ 一起带上——含求解器源码构建上下文与
# 预构建镜像 tar（docker_images/），服务器上 docker load 即用，无需本机另行导出
tar --exclude='Flow-MDK/.git' -czf flow_mdk_full.tar.gz Flow-MDK
```

上传：`scp flow_mdk_upload.tar.gz yuwenhang@schinta:~/` 后
`tar -xzf flow_mdk_upload.tar.gz`。

## 0.3 下载哪些文件（结果回收）

跑完后只需取回 **`runs/`**（很小，几十 MB）：

```bash
cd ~/Flow-MDK && tar -czf flow_mdk_results.tar.gz runs/
scp flow_mdk_results.tar.gz 本机:...
```

`runs/<name>/` 内含每实验的 `config.yaml`（复现凭据）、`history.json`
（逐 epoch 曲线）、`best.pt`/`last.pt`（权重）、`eval_*.json`（各域指标）。
取回后放回本机 `runs/`，再 `python scripts/archive_datasets.py` 刷新
`datasets/runs/` 归档。

## 0.4 torch 版本注意（driver 535 / CUDA 12.2）

A100（sm80）+ driver 535：**装 cu121 轮子最稳**（cu124/cu126 需要 ≥550 驱动
才能保证全部特性）：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121 --upgrade
```

## 1. 环境

- Linux + Docker（复算/家族批跑需要）；NVIDIA GPU + driver ≥ 535
- Python ≥ 3.10；git-lfs ≥ 3.x（`git lfs install`，仅 LFS 同步方案需要）
- 本仓库 tar 包方案（§0.2 方案 1）无需 git-lfs

服务器装有 Anaconda，**建议新建独立 conda 环境专跑本实验**（与服务器其他项目隔离）：

```bash
conda create -n flowmdk python=3.10 -y
conda activate flowmdk
pip install -e .            # torch/torch_geometric 按平台自动装
# GPU 训练（A100 + driver 535 用 cu121，见 §0.4）：
pip install torch --index-url https://download.pytorch.org/whl/cu121 --upgrade
python -c "import torch; print(torch.cuda.is_available())"   # 应输出 True
```

以后每次登录服务器，先 `conda activate flowmdk` 再执行任何训练/评测命令。
（如无 conda 可退回 `python -m venv .venv && source .venv/bin/activate`。）

## 2. 求解器镜像（仅 Mascaret 批跑/复算需要）

**镜像已随仓库分发**（`datasets/docker_images/*.tar.gz`，Git LFS）——上传整个
仓库文件夹后服务器上只需 `docker load`，无需任何构建：

```bash
cd ~/Flow-MDK
docker load < datasets/docker_images/telemac-debian_0.1.tar.gz    # 基础镜像
docker load < datasets/docker_images/flow-mdk-telemac_v8p4r0.tar.gz
docker images | grep telemac    # 确认 flow-mdk-telemac:v8p4r0 出现
```

如需从源码重建（如镜像损坏或要改构建）：`datasets/telemac-mascaret-v8p4r0/`
现在是**自包含构建上下文**（Dockerfile、构建脚本、`dependencies/`、源码树
`telemac-mascaret/` 全在上下文根），加载基础镜像 tar 后直接相对路径构建，
不再需要复制到 /tmp：

```bash
docker load < datasets/docker_images/telemac-debian_0.1.tar.gz
docker build -t flow-mdk-telemac:v8p4r0 datasets/telemac-mascaret-v8p4r0/   # ~20-40 min
```

（上下文中的源码树已剪去 examples/notebooks/builds——均非 `compile_telemac.py`
的输入；来源映射见 `scripts/archive_datasets.py`。）

> 注意：仓库快照**缺** `dependencies/`（Dockerfile `ADD` 的 JDK 8 压缩包）与
> 基础镜像 `telemac-debian:0.1` 的 DockerfileBase（上游以 tar 分发、无构建
> 文件）——所以旧版"从快照直接 build"走不通；现两者均已入库（dependencies/
> 在上下文内，基础镜像在 docker_images/）。

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
    out_dir=runs/partA_swegnn data.root=data/scenarios_partA_v2 device=cuda \
    train.max_epochs=150 train.curriculum_steps=4 train.early_stop_patience=99
python scripts/evaluate.py --config runs/partA_swegnn/config.yaml \
    --checkpoint runs/partA_swegnn/last.pt --split test \
    --data-root data/real_cases/family_wqh
```

> **L4 论文级预算直接跑 `scripts/run_partA_paper.sh`**（无需改任何脚本）：
> 四模型按 configs 内置的论文设定训练（G=64、150 epochs、batch 8；SWE-GNN
> 2 层×8 跳官方配方，Flow-MDK/GCN/GAT 6 层×1 跳），评测含 A1+A2+A3 test、
> A2/A3 泛化子集单列、三家族与真实考卷零样本；结果落 `runs/partA_paper_<name>/`
>（与首轮回归链 `run_partA_experiments.sh`（G=32 / 40 epochs）的
> `runs/partA_<name>/` 互不覆盖）。

GPU 显存预算：G=64、batch 8、100 节点图 ≈ 1-2 GB；4 GB 卡可将 batch 提到 16-32
或把 hidden_dim 提到 64（论文设定）。

## 5. 论文级预算建议（服务器）

| 实验 | 配置 | 预计时长（单卡） |
|---|---|---|
| Part A 四模型（论文设定 G=64, L=2×8/3, 150 epochs） | `bash scripts/run_partA_paper.sh`（configs 内置论文设定） | 每模型 1-3 h |
| B1 训练 → B2 考卷（M2 主消融：SSGC / SWE-GNN / Flow-MDK） | `data.root=data/real_cases/family_*`，MDKConfig 开关见 `docs/results_partA.md` | 每模型 <1 h |
| A→B 零样本矩阵 | `scripts/evaluate.py --data-root ...` | 分钟级 |

结果全部落在 `runs/<name>/`（config/history/eval json/last.pt），随后
`python scripts/archive_datasets.py` 刷新 `datasets/runs/` 归档并随 LFS 同步。
