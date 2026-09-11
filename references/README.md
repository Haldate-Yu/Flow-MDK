# References / 背景文献

Flow-MDK 的方法基石与相关方向文献。文件按 `年份_第一作者_主题_来源/arXiv号` 命名。

## 方法基石（必读）

| 文件 | 论文 | 与本工作的关系 |
|---|---|---|
| `2021_Zhu_Koniusz_S2GC_Simple_Spectral_Graph_Convolution_ICLR_arXiv2002.07972.pdf` | **Simple Spectral Graph Convolution (S2GC)** (ICLR 2021, arXiv:2002.07972, Zhu & Koniusz) | **传播算子来源**。由 Markov Diffusion Kernel（Fouss et al., 2012 的改造）导出：对转移矩阵做 k = 0…K 步扩散矩阵的等权聚合 f(Λ) = (1/K)ΣΛ^k，k=0 恒等项限制 over-smoothing；即本方法"扩散分支"的理论基础（Flow-MDK 的 geometric 加权是其带 teleport 的推广，uniform 模式对应原文） |
| `2023_Bentivoglio_et_al_SWE-GNN_HESS27.pdf` | **Rapid spatio-temporal flood modelling via hydraulics-based graph neural networks** (HESS 27, 4227–4246, 2023) | **架构母本**。encoder–processor–decoder + 差值消息（近似黎曼求解器）+ 残差增量预测 + 递归多步损失 + 课程学习；本方法在其骨架上做 MDK 定向化与算子分裂改造 |

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

## 核心论点备忘（方法答辩用）

- SWE-GNN 自身消融（SWE-GNNng，去掉梯度项）掉到 GCN 水平 → 传播算子的物理结构是性能来源，不是 GNN 本身；
- 对称谱扩散（S^k 族）物理上对应扩散波体制，无法表达双曲激波/急流 → Flow-MDK 用**水力定向转移矩阵 + 算子分裂**补足方向性；
- SWE-GNN 用堆层匹配 CFL 感受野 → Flow-MDK 对应地用扩散长度 √(2DΔt) 匹配 MDK 级数截断。
