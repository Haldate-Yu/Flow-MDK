# Flow-MDK vs 官方 SWE-GNN 实现 — 逐项对照

> 官方仓库：<https://github.com/RBTV1/SWE-GNN-paper-repository->（论文 Code availability 一节指定；
> Zenodo: 10.5281/zenodo.10214840）。仓库内归档副本：`datasets/swegnn-official/`。
> 对照日期：2026-09-11。官方关键文件：`models/gnn.py`、`models/models.py`、`training/train.py`、
> `training/loss.py`、`utils/dataset.py`、`database/graph_creation.py`、`config.yaml`。

## 结论摘要

架构骨架、消息函数、训练配方与数据生成方法全部对上。对照中发现 **6 处本仓库与官方代码的偏差**，
已全部修正（见 §3）；另有 2 处官方代码与官方论文文字不一致，我们选择跟随**代码**（见 §4），
以及 1 处论文文字与代码不一致但我们跟随论文（见 §5）。

## 1. 与官方一致的部分（逐项核对 ✓）

| 项目 | 官方（代码） | 本仓库 | 状态 |
|---|---|---|---|
| 总体结构 | encoder–processor–decoder，残差增量预测 `U_{t+1} = U_t + Φ(·)` | 同 | ✓ |
| 编码器 | 三个独立 MLP（静态 bias=True / **动态 bias=False** / 边 bias=True），2 层 Linear + PReLU，G=64 | 同 | ✓ |
| ψ 消息输入 | `[hs_i, hs_j, hd_i, hd_j, e_ij]`（5G）→ MLP(hidden 2G) → G（`edge_mlp`） | 同 | ✓ |
| ψ 输出归一化 | `w_ij / ‖w_ij‖`，NaN→0（官方）vs `+eps` 再除（本仓库），效果等价 | 等价 | ✓ |
| 差值消息 | `(hd_j − hd_i) ⊙ w_ij`，scatter 求和到目标节点，**W 作用于聚合之后** | 同 | ✓ |
| 干湿消息过滤 | 官方按 running 状态非零过滤边；本仓库干-干边差值恒为 0（无偏置动态路径），数学等价 | 等价 | ✓ |
| 水位静态特征 | `with_WL=True`：WL = DEM + 最新帧 h，每步重算 | 同（attach/refresh） | ✓ |
| 动态变量 | `(h, |q|)`，`|q| = |v|·h`；窗口 `[static…, dyn(t−p…t)]`，2 帧（previous_t=2 ⇔ 本文 p=1） | 同 | ✓ |
| 边特征 | `(length, normal_x, normal_y)`，网格 4 邻接双向弧，normal=中心距单位向量 | 同 | ✓ |
| 静态特征 | DEM + slope_x + slope_y（官方 config 关闭 area；本仓库 1D/2D 布局另含面积/糙率，按 config 可选） | 超集 | ✓ |
| 特征缩放 | 官方 scalers=null 不做归一化 | 不做归一化 | ✓ |
| 训练 | Adam + StepLR(×0.9/7ep)；H=8 递归 rollout 损失；课程学习 15ep/步；γ_q=3；batch 8；早停 | 同 | ✓ |
| 输出掩码 | `_mask_small_WD`：深度 <1mm 置零、干节点流量置零（每步） | 已补齐（`mask_small_depth`） | ✓（修正后） |
| 损失形式 | 逐步 `Σ_o γ_o·RMSE_o(仅水区)`，对 H 步取均值 | 已对齐（原为加权 MSE 全域） | ✓（修正后） |
| 梯度裁剪 | `clip_grad_value_(0.5)` | 已对齐（原为 norm 裁剪） | ✓（修正后） |
| 2D 数据生成 | `nx.grid_2d_graph` DiGraph（双向弧）；Delft3D-FM 30min 原始输出按 `temporal_res/30` 抽帧；`overview.csv` 记录求解耗时做加速比分母 | 同构（npz schema + meta.runtime_s） | ✓ |

## 2. 官方代码的关键结构事实（此前论文文字未覆盖）

官方 `SWEGNN` 层（`models/gnn.py:156`）**每层内部做 K=8 跳**，每跳一个独立无偏置
Linear（`filter_matrix[k]`），消息始终在 running 状态上重算：

```
out = W_0 x_t                       # 层入口提升（filter_matrix[0]）
for k in 1..K:
    mask 边（running 非零端点）
    w_ij = normalize(ψ(x_s_i, x_s_j, out_i, out_j, e_ij))
    out = out + W_k · Σ_j (out_j − out_i) ⊙ w_ij
```

`config.yaml` 中 `K: 8`（注释 "num GNN layers"）+ 外层 `n_GNN_layers=2`（默认值）⇒
**每个模型步共 16 次消息传递**。论文正文"L 层匹配 CFL 感受野"对应的就是这个内层 K。
本仓库的 `hops_per_layer` + `num_message_passing_layers` 即按此语义实现
（忠实复现配置：`configs/1d_swegnn_official.yaml`，2 层 × 8 hops）。

## 3. 本仓库已修正的偏差

1. **每层跳数**：原实现每层 1 跳 × 6 层；官方为 8 跳 × 2 层（每跳独立 W）。
   → 新增 `ModelConfig.hops_per_layer`，`OperatorSplitLayer` 内循环 + 每跳 Linear。
2. **层间激活**：原实现层间无激活；官方每层输出后都有激活。
   → 新增 `hidden_activation`（默认 PReLU，忠实复现配置用 Tanh 与官方一致）。
3. **MLP 尾激活**：官方 `make_mlp` 在最后一个 Linear 后也接 PReLU（编码器/ψ/解码器均是）。
   → `make_mlp(activate_output=True)` 已对齐。无偏置路径 PReLU(0)=0，干节点不变性保持。
4. **损失函数**：原为加权 MSE（全域、均方）；官方为 **RMSE**（开方）+ **仅水区掩码**
   （pred 或 truth 非零的节点）+ 变量加权**点积**（非均值）。
   → `train/loss.py` 已重写，含全干窗口回退（官方用 time_start=1 规避，我们用回退更稳）。
5. **输出掩码**：官方每步 `_mask_small_WD`（|h|<1mm→0；h==0 处 q→0），训练反馈与 rollout 一致。
   → `models/base.apply_small_depth_mask`，`ModelConfig.mask_small_depth=True`；
   `clamp_depth` 改为默认 False（官方无此操作，属我们的可选安全项）。
6. **训练超参**：官方代码 lr=**0.007**（论文文字写 0.005）、patience=30、梯度**值**裁剪 0.5。
   → `TrainConfig` 已对齐（lr、patience、grad_clip_value）。

## 4. 官方论文 vs 官方代码不一致处（我们跟随代码）

| 项 | 论文文字 | 官方代码 | 本仓库取值 |
|---|---|---|---|
| 学习率 | 0.005 | `lr_info.learning_rate: 0.007` | 0.007（忠实复现配置） |
| Tanh 位置 | 仅第 L 层输出 | `gnn_activation: 'tanh'` 且**每层**输出后都激活 | 忠实复现配置取"每层 Tanh"；默认配置取论文文字（层间 PReLU + 末层 Tanh） |
| GCN 基线传播 | `I − D^-1/2 A D^-1/2`（归一化拉普拉斯，带负号） | 仓库未含 GCN 对照代码（只有 ChebConv/TAGConv/GAT 分支） | `baseline_gcn` 用标准 Kipf 归一化，此差异记录在案 |

## 5. 本仓库相对官方的**有意差异**（即 Flow-MDK 的贡献点）

- **MDK 扩散分支**：官方只有差值消息分支；本仓库每层增加水力定向 MDK 滤波
  （作用于层增量、λ₀·I 恒等项、干湿重归一化），可学习 α 混合。
- **1D 支持**：官方仅 2D 网格（Delft3D-FM）；本仓库统一 1D 链 / 2D 网格 / 耦合接口。
- **干湿拓扑显式记录**：官方无；本仓库存储 wet 序列与边活动转移（M0 计划项）。
- **TELEMAC-MASCARET 数据源**：官方用 Delft3D-FM；本仓库按计划用 Mascaret/TELEMAC-2D
  （另有内置 1D 扩散波参考解算器用于管线自检）。

## 6. 官方数据生成要点（`database/` + `raw_datasets/`）

- 原始数据：`DEM_{i}.txt`（第三列高程）、`WD/VX/VY_{i}.txt`（[N×T]，30 min 分辨率）；
  Delft3D-FM 计算时长记录在 `overview.csv`（seed, grid 100m, 64×64, 48h, 耗时）。
- 单位流量 `|q| = |v|·h` 在原始分辨率计算后再抽帧（本仓库生成器直接输出 Q/|q|，语义一致）。
- `add_dry_bed_condition`：窗口前补 `previous_t−1` 帧全零（干床）；`time_start=1` 跳过全干首帧。
- 切分：train 80 / val 25%×train / test 10（数据集 1）；测试集 2/3 为变边界与更大域。

> 官方原始数据已下载至 `D:\tmp\swegnn-official\raw_datasets\`（DEM/VX/VY/WD 各 131 个文件），
> 可用于后续 2D 管线的格式对照与 2D 交叉验证（M3）。
