# References / 背景文献

Flow-MDK 的方法基石与相关方向文献。文件按 `年份_第一作者_主题_来源/arXiv号` 命名。

## 方法基石（必读）

| 文件 | 论文 | 与本工作的关系 |
|---|---|---|
| `2021_Zhu_Koniusz_S2GC_Simple_Spectral_Graph_Convolution_ICLR_arXiv2002.07972.pdf` | **Simple Spectral Graph Convolution (S2GC)** (ICLR 2021, arXiv:2002.07972, Zhu & Koniusz) | **传播算子来源**。由 Markov Diffusion Kernel（Fouss et al., 2012 的改造）导出：对转移矩阵做 k = 0…K 步扩散矩阵的等权聚合 f(Λ) = (1/K)ΣΛ^k，k=0 恒等项限制 over-smoothing；即本方法"扩散分支"的理论基础（Flow-MDK 的 geometric 加权是其带 teleport 的推广，uniform 模式对应原文） |
| `2023_Bentivoglio_et_al_SWE-GNN_HESS27.pdf` | **Rapid spatio-temporal flood modelling via hydraulics-based graph neural networks** (HESS 27, 4227–4246, 2023) | **架构母本**。encoder–processor–decoder + 差值消息（近似黎曼求解器）+ 残差增量预测 + 递归多步损失 + 课程学习；本方法在其骨架上做 MDK 定向化与算子分裂改造 |
| `2025_Bentivoglio_et_al_mSWE-GNN_NHESS25.pdf` | **Multi-scale hydraulic graph neural networks for flood modelling** (NHESS 25, 335–351, 2025, doi:10.5194/nhess-25-335-2025, Bentivoglio, Isufi, Jonkman & Taormina) | **架构母本的多尺度后继**，同一课题组。针对 SWE-GNN 四点局限（无法表达传播速度差异、多层不稳定、不支持时变边界、需数值求解器提供初始条件）分别用 U-Net 式多分辨率池化/上采样、时变边界 ghost cell、以及旋转不变的输入构造来补；裸域 MAE 0.05 m（水深）/ 0.003 m²s⁻¹（单宽流量），荷兰 dike ring 15 案例在**仅 1 个微调样本**下 MAE 0.12 m、水深阈值 0.05 m 的 CSI 87.68%、加速 >700×。**注意其改进集中在分辨率、时变边界与数据效率三个维度，通量仍是"水头差 × 学习电导"的扩散型（达西）形式，没有物理导出的单侧/迎风结构**（代码核实见下），未触及 Flow-MDK 针对的双曲方向性 gap |

> 备注：早期文件曾误挂为 arXiv:2103.03222（一篇排队论论文），现已替换为正确的
> Zhu & Koniusz 原文（arXiv:2002.07972）。检索引擎对该标题常给出错误作者归属，
> 引用时以 ICLR 2021 官方页为准。

## GNN 物理模拟相关

| 文件 | 论文 | 说明 |
|---|---|---|
| `2021_Pfaff_et_al_MeshGraphNets_ICLR_arXiv2010.03409.pdf` | **Learning Mesh-Based Simulation with Graph Networks** (ICLR 2021) | 网格 GNN 模拟器奠基工作，SWE-GNN 的方法论源头 |
| `2025_Nayak_Goswami_GNS_vs_NeuralOperators_arXiv2509.06154.pdf` | **Data-Efficient Time-Dependent PDE Surrogates: Graph Neural Simulators vs. Neural Operators** (arXiv:2509.06154) | GNS 与 DeepONet/FNO 的系统基准（含 2D 浅水方程），选型参考 |
| `2026_Cardoso-Bihlo_AegirJAX_differentiable_SWE_arXiv2604.07129.pdf` | **A solver-in-the-loop framework for end-to-end differentiable coastal hydrodynamics** (arXiv:2604.07129) | 全可微浅水求解器 + 神经修正，反问题/参数优化方向的参照 |
| `2022_Bentivoglio_et_al_DL_flood_mapping_review_HESS26.pdf` | **Deep learning methods for flood mapping: a review** (HESS 26, 4345–4378, 2022) | 领域综述（58 篇），定位与 gap 分析用 |

## 大模型 / Agent 方向

| 文件 | 论文 | 说明 |
|---|---|---|
| `2024_Herde_et_al_Poseidon_Foundation_Models_PDEs_arXiv2405.19101.pdf` | **Poseidon: Efficient Foundation Models for PDEs** (arXiv:2405.19101) | PDE 基础模型路线参照：多尺度算子 transformer + 时间半群预训练；"一个模型覆盖多场景"的正确参照系（非 LLM） |
| `2025_Fan_et_al_ChatCFD_LLM_OpenFOAM_automation_arXiv2506.02019.pdf` | **ChatCFD: An LLM-Driven Agent for End-to-End CFD Automation** (arXiv:2506.02019) | LLM agent 编排数值求解器（OpenFOAM）的成熟范式，315 案例 82.1% 执行成功率；迁移到 TELEMAC-MASCARET 编排的模板 |
| `2026_Yang_et_al_HydroAgent_flood_forecasting_arXiv2607.23983.pdf` | **HydroAgent: Formalizing Forecaster Expertise into Skill-Orchestrated Flood Forecasting Workflows** (arXiv:2607.23983) | LLM agent + 规则约束的洪水预报编排工作流 |
| `2026_Li_et_al_HydroAgent_calibration_RL_arXiv2605.17792.pdf` | **HydroAgent: Closing the Gap Between Frontier LLMs and Human Experts in Hydrologic Model Calibration via Simulator-Grounded RL** (arXiv:2605.17792) | 以 NSE 为奖励信号对 LLM agent 做强化学习率定水文模型——率定循环自动化（糙率调参可直接借鉴）的直接先例 |

> 注意：两篇 HydroAgent 是不同工作（预报编排 vs 模型率定），引用时勿混淆。

## 外部代码快照（`third_party/`，不入 git）

上游代码只作**对读**用，不 vendor 进版本库（`.gitignore` 已忽略，理由同
`third_party/telemac/README.md`）。已落地的：

| 路径 | 来源 | 内容 |
|---|---|---|
| `third_party/mSWE-GNN/` | <https://github.com/RBTV1/mSWE-GNN>（MIT）。本地快照 `main@529bb92`（2025-10-28，84 MB 压缩 / 90 MB 展开）；与论文归档版 Zenodo `10.5281/zenodo.14673842`（tag `1.0`）**逐文本文件 diff 全同**，可放心用它对读论文 | `models/gnn.py`（`GNN` / `MSGNN` / `SWEGNN`）、`training/`、`config.yaml`、Pareto front 的 16 个 `.h5` 权重（K2–K5 × F16–F64）+ `finetuned_dk15.h5` |

论文原始数据（~3.9 GB，CC-BY-4.0，需自行下单）：
<https://doi.org/10.5281/zenodo.13326595> —
`raw_datasets_mesh.zip` 2.95 GB（多尺度网格训练/测试集）、`raw_datasets_dk15.zip` 0.99 GB（dike ring 15 真实案例）。

### 代码核实：mSWE-GNN 的传播算子是什么

`models/gnn.py:352` 的 `SWEGNN` 即论文 Eq. (3)–(4)；v1.0（论文归档）与 main 逐行一致：

```
w_ij = ψ(x_s_i, x_s_j, x_d_i, x_d_j, e_ij) / ‖·‖      # 逐弧学习电导（归一化，NaN→0）
x'_i = x_i + Σ_{j∈N(i)} w_ij ⊙ (x_j − x_i)            # 通量 = 电导 ⊙ 水头差
```

**是梯度驱动（达西/菲克型）通量**：传输方向由水头差的符号隐含给出，量级由学到的电导给出；
没有单侧/特征线结构，也没有动量或对流项。论文自己的措辞是 "hydraulic gradient-like term"
起 "physical constraint that allows water to propagate only from nodes which already have
water" 的作用 —— 这是**干湿约束**，不是迎风。

**但不是各向同性**（此处更正本文档前一版的说法）：GNN 走的是**对偶（网格单元）图**，
`database/graph_creation.py:1564` `data.edge_index = mesh.dual_edge_index`，而
`dual_edge_index` 被 `to_undirected` 转过（`:701`/`:730`/`:772`，`:1397` 注释明写
"dual_edge_index is converted to undirected"）⇒ **每条边的两个方向都是独立存在的弧**。
ψ 的输入是**有序**拼接 `cat([x_s[row], x_s[col], x_t[row], x_t[col], e])`（`:209`），
scatter 到 `col`（= 接收节点），故 i→j 与 j→i 拿到的是不同输入向量 ⇒ `w_ij ≠ w_ji` 一般成立。
算子是**学到的有向（非对称）图拉普拉斯** —— 方向偏置在结构上是允许的。前一版写的
"对称拼接 / 各向同性扩散"不成立，已更正。

**论文层面未把方向性作为设计轴**：全文（连字归一化后检索）`upwind` / `one-sided` /
`isotropy` / `anisotropy` / `symmetry` 提及次数均为 **0**；摘要列的四点局限是传播速度差异、
多层不稳定、时变边界、初始条件；消融 §4.3 只有多尺度模块、解码器、旋转不变性三组。

`upwind_mode`（`gnn.py:365/376/431`，开启后把负梯度置零、退化为单侧）是仓库里**唯一**的显式
单侧机制：v1.0 与 main 都在，**默认 `False`，全仓库无任何配置/脚本/notebook 给它传值**
（对 v1.0 全部 20 个文本文件 grep，仅 `models/gnn.py` 命中）。与 2023 版 SWE-GNN
（`datasets/swegnn-official/`）逐行 diff：两者 `SWEGNN` 实现相同，mSWE-GNN 唯一新增的算子级
参数就是 `upwind_mode` —— 作者加了迎风开关，但没有使用。

**Flow-MDK 的定向性对照**（`src/flow_mdk/layers/mdk.py`）：

| 机制 | mSWE-GNN | Flow-MDK |
|---|---|---|
| 弧方向 | 无显式规则，全靠学习电导（可非对称） | `direction_gates:74` `g = sigmoid(β(w_src − w_dst))`，按**水面坡度符号**抑制上坡弧；静水退化为两向 0.5 |
| 边权 | ψ 从节点/边特征学出 | `hydraulic_edge_weights:60` `(\|q_src\|+\|q_dst\|)/2`（discharge）或 uniform |
| 传播矩阵 | 差值消息累加后再乘 W | **上游→下游行随机 P**，每步在湿子图上重归一化，加 λ₀·I |
| 分支 | 单支差值消息 | 算子分裂（可学习 α 混合 MDK 与差值分支） |

消融开关：`directed=False` → 对称 MDK = SSGC（`-定向性`）；`mixing="diffusive-only"`
（`-分裂`）；`use=False`（`-MDK`）。

> **更正一处混读**：末节备忘里"对称谱扩散（S^k 族）"指的是 **S2GC/SSGC/MDK 这条本仓库
> 自己的扩散分支**（其对称消融就是 `-定向性` 臂），不是 SWE-GNN；项目
> `docs/swe_gnn_official_comparison.md` §5 对官方 SWE-GNN 的定性是"差值消息分支"。
> 此前把两者混为一谈是误读。

**结论**：mSWE-GNN 的改进集中在多分辨率、时变边界、旋转不变性；它**没有**引入由水力状态
导出的定向（单侧/迎风）通量，算子仍是水头差驱动的学习电导扩散。本工作的差异化成立，但正确
表述是"缺**物理导出的单侧/迎风通量**"，**不是**"缺非对称权重"，也**不是**"算子各向同性"。
训练是否自发学到有用的非对称性，本仓库未验证（需 Zenodo 数据做前向对照）。

对读直接用 `models/gnn.py`。关键超参：`K=4, hid_features=64, mlp_layers=3, with_gradient=True,
with_filter_matrix=True, learned_residuals=True, rollout_steps=6, previous_t=3,
curriculum_epoch=20, batch_size=4`；`MSGNN.intra_scale_gnn` 则是 `with_gradient=False,
with_filter_matrix=False`（对应论文 §2.2.2 跨尺度算子去掉边特征与梯度项）。

> 记号差异（良性）：论文 Eq. (3) 写作 ψ(h_si, h_sj, h_di, h_dj)（**接收节点在前**），代码拼接
> 顺序是 `[row, col]` 且 scatter 到 `col`，即接收节点在**后**；两个仓库都如此，属记号互换
> （首层 Linear 可置换），不影响容量。`docs/swe_gnn_official_comparison.md` §1 记的是论文记号。

> 注意 mSWE-GNN 与 Flow-MDK 的 `swegnn_official` 系列 config 不是一回事：
> 后者是**本项目按 SWE-GNN 论文设置重实现的对照臂**，不含多尺度池化与 ghost cell。

## 核心论点备忘（方法答辩用）

- SWE-GNN 自身消融（SWE-GNNng，去掉梯度项）掉到 GCN 水平 → 传播算子的物理结构是性能来源，不是 GNN 本身；
- 对称谱扩散（S^k 族）物理上对应扩散波体制，无法表达双曲激波/急流 → Flow-MDK 用**水力定向转移矩阵 + 算子分裂**补足方向性；
- SWE-GNN 用堆层匹配 CFL 感受野 → Flow-MDK 对应地用扩散长度 √(2DΔt) 匹配 MDK 级数截断。
- mSWE-GNN（NHESS 2025）是这条线的 SOTA 后继，改进集中在多分辨率 / 时变边界 / 旋转不变性；
  其通量是"水头差 × 学习电导"的扩散型（达西）形式，**没有**物理导出的单侧/迎风结构，
  且仓库里唯一显式的迎风开关 `upwind_mode` 从未启用（见上"代码核实"）→ 对照最新工作，
  "缺物理导出的定向通量"仍是未解决的 gap，这是本工作最稳的差异化立足点。
  注意措辞：别把它说成"各向同性"（每弧权重可非对称），也别把多尺度改进误读成方向性补足；
  "对称谱扩散"那条说的是本仓库自己的 SSGC/MDK 分支，与它无关。
