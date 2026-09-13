# 服务器实验执行流程（Remote Server Runbook）

本仓库所有实验均可在 Linux 服务器上复现。本文档按实际执行顺序组织：
**① 打包上传 → ② 环境搭建 → ③ 求解器镜像导入 → ④ 执行实验 → ⑤ 结果取回**。
所有路径均为仓库内相对路径；其他人拿到仓库（含 `data/` 工作数据）即可照做。

## 0. 服务器配置结论（2026-09-11 核对）

2× A100-SXM4-80GB（driver 535 / CUDA 12.2）：**完全满足论文级实验**。
论文用 V100-32GB；实测论文级 2D 配置（4096 节点 × batch 8、G=64、2×8 跳、
H=8 rollout）峰值显存约 9.5 GB。注意 GPU0 被常驻服务占用（约 76/80 GB），
**训练请用 GPU1**（空闲 ~65 GB）。所有训练/评测命令前加
`CUDA_VISIBLE_DEVICES=1`（torch 内编号随此变量重排，脚本内无需改动）：

```bash
export CUDA_VISIBLE_DEVICES=1   # 写入会话环境，后续命令全部生效
```

## 1. 打包与上传

训练需要**代码 + `data/` 工作数据**。`data/` 被 git-ignore，因此必须打包
**整个仓库文件夹**（不是 `git archive`），让以下目录随包上服务器：

| 必需目录 | 内容 |
|---|---|
| `data/scenarios_partA_v2/` | Part A v2：128 场景 npz + split.json（Mascaret SWE 真值） |
| `data/real_cases/` | Part B：三家族 117 场景 + 5 个真实考卷（`scenarios_1d/`） |
| `data/real_sources/` | wqh/zxh 完整工程模板（合成项目生成依赖） |
| `data/scenarios_1d/` | v1 回归集（可选） |

排除项：`data/partA_v2_mascaret_runs/`（Mascaret 工作目录，可重新生成）、
`runs/`（服务器自产，避免把本机半成品带上去）。

```bash
# 本机打包（~1.5 GB；加 --exclude='Flow-MDK/datasets' 可再省 4 GB，
# datasets/ 仅在服务器上需要重跑 Mascaret 批算 / 重建镜像时才需要）
cd /d/Projects && tar \
    --exclude='Flow-MDK/.git' \
    --exclude='Flow-MDK/data/partA_v2_mascaret_runs' \
    --exclude='Flow-MDK/runs' \
    --exclude='Flow-MDK/data/real_cases/mascaret_runs' \
    -czf flow_mdk_upload.tar.gz Flow-MDK

scp flow_mdk_upload.tar.gz yuwenhang@schinta:~/
```

```bash
# 服务器上解压
ssh yuwenhang@schinta
tar -xzf flow_mdk_upload.tar.gz && cd Flow-MDK
```

> 若走 Git LFS 方案（clone + `git lfs pull`）替代 tar：`datasets/` 下的
> 镜像与归档会自动就位，但仍需按 §3.2 从 `datasets/real_sources/` 恢复
> `data/real_sources/`（`data/` 永远不在 git 里）。

## 2. 环境搭建（虚拟环境）

服务器装有 Anaconda，建议新建独立环境专跑本实验：

```bash
conda create -n flowmdk python=3.10 -y
conda activate flowmdk
pip install -e .            # torch/torch_geometric 按平台自动装
# GPU 训练（A100 + driver 535 用 cu121：cu124/cu126 需 ≥550 驱动）：
pip install torch --index-url https://download.pytorch.org/whl/cu121 --upgrade
python -c "import torch; print(torch.cuda.is_available())"   # 应输出 True
```

（无 conda 可退回 `python -m venv .venv && source .venv/bin/activate`。）
以后每次登录服务器，先 `conda activate flowmdk` 再执行任何命令。

## 3. 求解器镜像导入（Mascaret 批跑/复算需要；纯训练评测可跳过）

### 3.1 加载预构建镜像（推荐，无需构建）

镜像随仓库分发（`datasets/docker_images/*.tar.gz`）：

```bash
cd ~/Flow-MDK
docker load < datasets/docker_images/telemac-debian_0.1.tar.gz    # 基础镜像
docker load < datasets/docker_images/flow-mdk-telemac_v8p4r0p1.tar.gz
docker images | grep telemac   # 确认 flow-mdk-telemac:v8p4r0p1 出现
```

**`v8p4r0p1` 是标准内核**（含 2026-09-12 Flow-MDK 补丁：XAJ 侧向入流未定义
行为 + 上游 Q 边界 YFIX 钳制；旧 `v8p4r0` 会随机段错误，仅作回档保留）。
改动详情与证据链：`datasets/telemac-mascaret-v8p4r0/PATCHES.md`。

### 3.2 恢复工作数据（仅 LFS/精简包方案需要）

```bash
mkdir -p data/real_sources
cp -r datasets/real_sources/wqh data/real_sources/
cp -r datasets/real_sources/zxh data/real_sources/
```

### 3.3 从源码重建（可选，镜像损坏或改内核时）

```bash
docker load < datasets/docker_images/telemac-debian_0.1.tar.gz
docker build -t flow-mdk-telemac:v8p4r0p1 datasets/telemac-mascaret-v8p4r0/   # ~20-40 min
```

## 4. 执行实验

**Part A 真值数据已随包就绪，无需重新生成**（`data/scenarios_partA_v2/`）。
若要从零重造真值：

```bash
python scripts/generate_partA_v2.py --out data/scenarios_partA_v2   # 扩散波参考解
python scripts/run_partA_mascaret.py --root data/scenarios_partA_v2 --all --workers 3
```

### 4.1 L2 · Part A 四模型正式对比（论文预算）

```bash
CUDA_VISIBLE_DEVICES=1 bash scripts/run_partA_paper.sh 2>&1 \
    | tee data/partA_paper_$(date +%Y%m%d_%H%M%S).log
```

四模型按 configs 内置论文设定训练（G=64、150 epochs、batch 8；SWE-GNN 2×8 跳
官方配方，Flow-MDK/GCN/GAT 6 层×1 跳），评测含 A1+A2+A3 test、A2/A3 泛化子集
单列、三家族与 B2 考卷零样本；每轮产生时间戳目录 `runs/partA_paper_<name>_<TS>/`
（互不覆盖）。

### 4.2 L3 · B1→B2 三方消融（论文预算）

```bash
CUDA_VISIBLE_DEVICES=1 bash scripts/run_L3_B1B2_paper.sh 2>&1 \
    | tee data/L3_B1B2_paper_$(date +%Y%m%d_%H%M%S).log
```

B1 = 三真实母版家族合并（脚本内自动构建 `data/real_cases/family_all/`），
B2 = 5 个真实考卷；三方消融 SSGC / SWE-GNN / Flow-MDK（configs 论文设定）。

### 4.3 单模型调试示例

```bash
CUDA_VISIBLE_DEVICES=1 python scripts/train.py --config configs/1d_swegnn_official.yaml \
    --set device=cuda out_dir=runs/debug_swegnn
python scripts/evaluate.py --config runs/debug_swegnn/config.yaml \
    --checkpoint runs/debug_swegnn/last.pt --split test \
    --data-root data/real_cases/family_wqh
```

### 4.4 时长预算（单卡 A100）

| 实验 | 脚本 | 预计时长 |
|---|---|---|
| L2 Part A 四模型（G=64, 150 epochs） | `run_partA_paper.sh` | 每模型 1–3 h，共 ~8 h |
| L3 三方消融（G=64, 150 epochs） | `run_L3_B1B2_paper.sh` | 每模型 1–2 h，共 ~4 h |
| A→B 零样本矩阵 | 各脚本内置 `evaluate.py` | 分钟级 |

GPU 显存：G=64、batch 8、100 节点图 ≈ 1–2 GB（A100 可再提 batch）。

## 5. 结果取回

跑完后取回 **`runs/`**（几十 MB，不含数据）：

```bash
cd ~/Flow-MDK && tar -czf flow_mdk_results_$(date +%Y%m%d).tar.gz runs/
# 本机：
scp yuwenhang@schinta:~/Flow-MDK/flow_mdk_results_*.tar.gz .
```

- `runs/partA_paper_<name>_<TS>/` 与 `runs/L3_B1_paper_<name>_<TS>/`：每实验的
  `config.yaml`（复现凭据）、`history.json`（逐 epoch 曲线）、`best.pt`/`last.pt`
  （权重）、`eval_*.json`（各域指标）。
- **`runs/results.csv` 是所有训练/评测的总登记表**（一行一次结果），取回后可直接
  用 pandas/Excel 横向对比各轮实验。
- 放回本机 `runs/` 后执行 `python scripts/archive_datasets.py` 刷新
  `datasets/runs/` 归档并随 LFS 同步。
