# Flow-MDK 研发计划（PLAN）

> 目标：以 SWE-GNN（Bentivoglio et al., 2023）为骨架、以水力定向马尔可夫扩散核（MDK，S2GC/Zhu & Koniusz, ICLR 2021）为传播改造核心，构建覆盖 **1D / 2D / 1D-2D 耦合** 三类场景的浅水方程 GNN 代理模型，训练数据由 TELEMAC-MASCARET 批量生成（v8p4r0 内核 + Flow-MDK 补丁；求解器镜像与自包含构建上下文随仓库分发：`datasets/docker_images/`、`datasets/telemac-mascaret-v8p4r0/`，内核改动见 `datasets/telemac-mascaret-v8p4r0/PATCHES.md`）。
>
> 另设**真实案例轨道**（贯穿 M1–M5，见专门章节）：以真实项目建模文件做效果检验与训练母版，核心产出为 synthetic→real 泛化 gap。
>
> 方法核心：**对流-扩散算子分裂** —— 有向差值消息（SWE-GNN 式）承载波动/对流动力学，水力定向 MDK 滤波承载扩散性回水效应；MDK 级数截断由物理扩散长度 √(2DΔt) 匹配；残差式滤波（作用于增量）+ λ₀·I 恒等项防 over-smoothing。
>
> 文档约定：本文件只维护**进度总览**（计划、当前状态、待办、日志索引）；每日进展
> 写入 `plan/update_progress_[yyyy-mm-dd].md`，会话结束前同步更新本文件的状态标记
> （✅/◐）、Backlog 与文末日志表。

---

## 实验数据总体结构（两部分）

| 部分 | 内容 | 真值来源 | 规模 |
|---|---|---|---|
| **A · 模拟数据 v2**（对齐 SWE-GNN 130 模拟协议） | **A1** 100 场景（随机几何×水情，60/20/20）+ **A2** 20 场景（训练范围外的未见水情：陡峰/大洪峰）+ **A3** 10 场景（更大流域：400 断面/40 km/16 h），链式图 | **Mascaret 全 SWE 真值已挂 128/130**（2026-09-12 两段式初始化 + 内核补丁 `v8p4r0p1`，见 `datasets/telemac-mascaret-v8p4r0/PATCHES.md`；4 例 s1geo 负索引干净报错——其中 2 例沿用早前通过的真值、2 例暂缺）；扩散波参考解留作交叉检验 | **有效 128 场景**（`data/scenarios_partA_v2/`，split.json 已过滤、A1_train 恢复 60/60 完整协议，原始 130 协议存 `split_full_protocol.json`）；v1 的 50 场景保留于 `data/scenarios_1d/` 作管线回归用 |
| **B · 真实项目模拟数据** | B1 母版家族：真实几何（mdx 73 断面/46 km/闸门、zxh 23 断面、wqh 27 断面）× 合成水情（糙率场 lognormal 分区扰动 + 全部入流律统一幅值/时间拉伸） | Mascaret docker 批跑（`scripts/run_real_family.py`，容错+合理性过滤） | **117 场景**（mdx 37 + zxh 40 + wqh 40，`data/real_cases/family_*/`，各含 split.json） |
| | B2 真实历史事件考卷：mdx（洪峰 707 m³/s 历史事件）、zxh、wqh、mdx_upstream/downstream（`.opt` 回放或复算） | 历史 `.opt` 或镜像复算（wqh/zxh 逐位复现） | 5 场景（`data/real_cases/scenarios_1d/`） |

评测对照结构：Part A 训练 → Part A 测试（合成域内，含 A2/A3 泛化子集）；Part A 训练
→ B1/B2 零样本迁移（**synthetic→real gap，论文核心**）；B1 训练 → B2 考卷（真实域内）。
2D 部分沿用同一两部分结构，随 M3 接入 TELEMAC-2D 后扩展。

### 算力可行性实测（2026-09-11）

- 本机 RTX 3060 6 GB（可用 ~4 GB）：**1D 论文级训练完全可行**（论文配置 G=64、
  2×8 跳、H=8 rollout 实测约 21 s/epoch@H=1，150 epochs 每模型 4–7 h）；
  CUDA torch 2.14.0+cu126 已装入活跃环境并验证。
- **2D 论文级（4096 节点 × batch 8）峰值显存 9.5 GB → 超出本机**（WDDM 共享内存
  兜底掉速 10 倍）；本仓库 65k 节点真实网格更需服务器。A100-80GB ×2 充裕
  （GPU0 被常驻服务占用，训练用 GPU1；执行手册 `docs/server_setup.md`）。

---

## M0 · 环境与数据管线（预计 1–2 周）✅ 2026-09-11 完成

- [x] Python 环境：torch（本机已升 CUDA 2.14.0+cu126，RTX 3060 训练可用；服务器 A100 建议 cu121）+ torch_geometric 2.7；代码 device 自适应
- [x] Mascaret 无头批量运行：docker 镜像 `flow-mdk-telemac:v8p4r0p1`（构建上下文随仓库分发：`datasets/telemac-mascaret-v8p4r0/`）；独立启动器调通（`FichierCas.txt`/`Abaques.txt`/PATH/WORKDIR 要点记入 `scripts/run_real_family.py`）；TelApy 库亦已编译备用
- [x] 1D 场景族设计：糙率 K 场 lognormal 分区扰动、入流过程线族（γ 型陡峰/缓峰 + 双峰）、断面几何扰动（`src/flow_mdk/gen/scenarios_1d.py`）
- [x] 2D 场景族设计：Perlin 噪声 DEM + 参数化溃口边界（对齐 SWE-GNN 设定，`gen/scenarios_2d.py`）；真值待 TELEMAC-2D 复算（M3）
- [x] 数据格式约定：每场景 → `npz`（节点静态特征 + 动态特征序列 + 边几何 + 干湿序列 + 元数据），schema 见 `src/flow_mdk/utils/io.py`
- [x] 干湿判定与图拓扑快照存储（`data/topology.py`：wet 序列 + 边活动出现/消失记录）

**验收**：✅ Part A v2 130 场景（论文协议对齐）+ 真实母版家族 117 场景可一键复现生成，含 metadata；真实工况 5 个入库（Part B2，见真实案例轨道）。

## M1 · 一维基线复现（预计 2–3 周）◐ 进行中（管线就绪，v1 首轮结果已产出）

- [x] 链式图构建（断面=节点，`data/graph_1d.py`；异构拓扑批次用 `GroupedBatchSampler`）
- [x] SWE-GNN 架构 1D 移植：ψ 差值消息、残差增量预测、动态 encoder 无偏置 —— **已与官方仓库逐行对照并修正**（每层 K 跳、逐层激活、MLP 尾激活、RMSE 仅水区损失、梯度值裁剪；见 `docs/swe_gnn_official_comparison.md`），忠实复现配置 `configs/1d_swegnn_official.yaml`
- [x] 训练配方：递归多步损失（H=8，RMSE+γ 加权）、课程学习（H: 1→8）、ψ 输出归一化、末层 Tanh、`_mask_small_WD` 输出掩码；**协议修正**：早停与课程学习冲突 → 跑满 epochs + 评 `last.pt`（SWE-GNN 150-epoch 预算逻辑）
- [x] 评测脚本：RMSE/MAE（h, Q）+ CSI（0.05/0.3 m 两档）+ 加速比（`eval/` + `scripts/evaluate.py`，支持 `--data-root` 跨域零样本评测）
- [x] 真实案例轨道（1D）：5 个真实 Mascaret 工程导入（`scripts/import_real_cases.py`）→ 复算校验 ✅（wqh/zxh 完整工程逐位复现 RMSE=0）→ 真实母版家族 117 场景批跑 ✅ → 首轮 A→B 零样本评估 ✅

**v1 首轮结果（40 epochs、G=32，详见 `docs/results_partA.md`）**：域内 GCN 2.56 m < GAT 4.81 < Flow-MDK 9.16 < SWE-GNN 15.17（水深 RMSE）——扩散波体制与 GCN 对称平滑匹配所致（体制错配，非 MDK 假设失败）。

**L2 体制对齐后正式对比（2026-09-12，Mascaret 全 SWE 干净真值 × 128 场景，同预算，详见 `docs/results_partA_swe.md`）**：域内 GCN 0.79 ≈ GAT 0.83 < **Flow-MDK 1.42** < SWE-GNN 4.50——**MDK 混合对本体骨架的拯救效应（×3.2）是稳健发现**；v1 的"体制错配"解释在动力波体制下不再成立，对称平滑基线在 1D 链式场景依然很强；fam_mdx 零样本 Flow-MDK 最优（2.63）且退化幅度（×1.8）小于 GCN（×3.9）。正式体制归属结论归 L4 论文预算。

**验收**：✅ 基线管线全链路收敛（首轮四模型对比 + A→B 零样本 gap 已产出，见 `docs/results_partA.md` 与 `datasets/runs/` 归档）；真实 1D 工程完成复算校验 ✅（详见 docs/real_cases.md）与首次零样本评估 ✅；论文级预算收敛复测（L4）✅ 2026-09-14 取回落定（见 M2）；B1→B2 考卷的真实域内对比完成（L3 + L4 复测）。

## M2 · Flow-MDK 传播改造（预计 3–4 周，核心创新）◐ 进行中（核心实现就绪；本地多种子 + L4 论文预算单种子已收口，待 3 种子论文预算钉死）

- [x] 水力定向转移矩阵 P：流量加权（|q| 端点均值）× 水面梯度方向门控（上游→下游，静水时双向各 0.5、陡梯度退化为纯下游），每步按湿区子图行归一化、干节点不中继（`layers/mdk.py`：`hydraulic_edge_weights`/`direction_gates`/`_normalize_weights`）
- [x] MDK 级数实现：geometric（S2GC）与 uniform（截断 Neumann）两种权重可选；截断阶数 K 由扩散长度匹配 K=⌈√(2DΔt)/dx̄⌉（`suggest_num_steps`）；纯 scatter 稀疏实现，不构造稠密矩阵
- [x] 算子分裂：advection 分支（ψ 差值消息逐跳，逐跳独立权重矩阵，对齐官方 filter_matrix）+ diffusion 分支（MDK 滤波作用于增量），per-channel 可学习混合门 α（另支持 fixed / diffusive-only）；`mdk.use=false` 时精确退化为官方 SWE-GNN 层（`layers/splitting.py`）
- [x] λ₀·I 恒等项与平滑深度监控 —— ✅ 2026-09-13 接入评测：λ₀ 逐 epoch 记录于 history.json（`trainer.py`）；Dirichlet 能量经 rollout forward hooks 逐层计算（逐边归一）写入 eval json（`eval/rollout.py` + `scripts/evaluate.py`）；曲线工具 `scripts/plot_mdk_lambda0.py`。首轮信号：flow_mdk 训练中末层 λ₀ 0.42→0.09 塌缩、GCN 逐层能量随深度增长（残差累积）。表示相似度指标未实现（可选项）
- [ ] 大 Δt 实验：层/k 与时间步的权衡曲线（对应 SWE-GNN Fig. 8）—— 未开始（无实验脚本）

**验收**：◐ 首轮达成（2026-09-12，本地预算 G=32/40ep，单种子）。三方消融（B1 合并训练 → B2 真实考卷）：SWE-GNN 1.67 / SSGC 1.83 / Flow-MDK 2.45（水深 RMSE 均值，m）——同量级，Flow-MDK 在 B1 域内欠拟合（1.95 vs 0.80），疑似预算不足；mdx/闸门耦合考卷上定向系（Flow-MDK/SSGC）占优、简单考卷（zxh/wqh）上 SWE-GNN 占优，体制分工初现端倪。**L4 论文预算复测（2026-09-14 落定，单种子，详见 `docs/results_partA_swe.md` L4 节与 `docs/L4_report.md`）**：①主干稳定性判据通过——flow_mdk 无本地 s1 型崩坏，崩坏转移到无门控 6 层基线（GCN 35.4 塌缩、GAT 1.92）；②合成 1D 域内浅层 8 跳最优（0.72 vs 1.42），真实家族域深层门控系全面占优（0.85/0.87 vs 2.15）；③定向 vs 对称仍无显著差异（B1 p=0.81、B2 p=1.0）——**MDK 定向优势假设至今无统计支持，降级为探索性对照**；④共性：best epoch 极早 + val 漂移 2–4×，best.pt 对照待查。剩余：3 种子论文预算、best.pt/Dirichlet 富评、2D 激波体制验证（M3）。

## M3 · 二维场景（预计 2–3 周）

- [ ] 对偶图构建（单元中心=节点），边特征（外法向、边长）
- [ ] 干湿边演化时的逐步重归一化；湿锋传播性质验证（干邻居 → 无传播）
- [ ] 与 SWE-GNN 论文同构的溃坝/漫滩验证（小规模复刻，检查方向性分支在激波体制的贡献）
- [ ] 真实案例轨道（2D/耦合）：导入 1 个真实 TELEMAC-2D（或 1D-2D 耦合）工程 → 复算校验 → 随行验证

**验收**：2D 缓变场景达基线精度；激波场景中定向分支 vs 扩散分支的分工可量化；真实 2D 工程完成复算校验与随行评估。

## M4 · 一二维耦合（预计 2–3 周）

- [ ] 异构图：河网链子图 + 网格子图 + 接口边（河段↔漫滩单元）
- [ ] 接口质量守恒：损失项或结构约束（接口边通量显式建模）
- [ ] Mascaret + TELEMAC-2D 耦合数据生成（复用本地源码树的耦合运行能力）

**验收**：耦合场景误差报告 + 接口水量守恒诊断（闭合误差 < 设定阈值）。

## M5 · 系统评测与论文（预计 2 周）

- [ ] 完整基线对比：GCN / GAT / U-Net / 纯 SWE-GNN / Flow-MDK 消融版
- [ ] Pareto 前沿（精度–速度–复杂度）+ KS 显著性检验（对齐 SWE-GNN 协议）
- [ ] 泛化矩阵：未见参数组合 / 未见几何 / 更大域 / 更长时程 / **synthetic→real 真实案例 gap（1D、2D 各一）**
- [ ] 论文初稿（候选期刊：HESS / EM&S / WRR）

## M6 ·（可选）Agent 集成

- [ ] MCP 工具封装：场景生成、Mascaret 批跑、训练、评测暴露给现有 HydroAgent 式编排
- [ ] 率定循环：LLM agent 粗搜（代理模型）+ Mascaret 精校（参考 HydroAgent-calibration 的 RL 思路）

---

## 真实案例轨道（贯穿 M1–M5）

真实项目建模文件承担**两个严格分开的角色**：

**角色一 · 考卷（效果检验，优先级最高）**
- 真实工程原样复算 → Mascaret / TELEMAC-2D 结果作为 ground truth；有实测站或淹没调查资料的，同时与观测比对（水文站 NSE/KGE，淹没范围 CSI）
- 切分纪律：leave-one-event-out（按历史洪水事件切分）；**同一真实案例（或同批事件）不得既进训练又当考卷**
- 核心产出：**synthetic→real 泛化 gap**——合成场景族训练后向真实几何/糙率场零样本迁移的误差增量，论文核心卖点

**角色二 · 母版（训练数据增强）**
- 以真实几何为母版做参数化扰动：糙率场缩放/分区调整、入流过程线缩放与整形、闸泵调度序列、（溃坝项目）溃口参数 → 生成"真实几何 × 合成水情"场景族
- 对标 SWE-GNN 的 Perlin DEM 思路，但几何真实性更高，训练覆盖更接近真实流态

**准入检查清单（纳入轨道前必须全部通过）**
- [x] 复算校验（2026-09-11，镜像 `flow-mdk-telemac:v8p4r0`）：`wqh`/`zxh`（第二提供方完整工程，已内化至 `data/real_sources/`）复算**逐位复现（RMSE=0）** ✅、`zxh`（旧模板）0.096 m / 6.7% ✅、`mdx_upstream` 0.282 m / 6.4% ✅；`mdx` 复算可运行但偏差 15.4%（历史计算含模板缺失的新安江 XAJ 水文输入，故保留历史 `.opt` 为考卷真值、模板复算仅作交叉验证）；`mdx_downstream` 复算段错误（待排查，真值保留历史 `.opt`）——`wqh` 经第二提供方补充完整工程后复算**逐位复现（RMSE=0）**
- [x] 保密脱敏：原始工程文件只留本地 `data/`（已 git-ignore）；仓库只放生成脚本与匿名化派生数据（断面脱敏、去项目名、坐标偏移）
- [x] 图规模盘点：登记断面数/支流级数（1D）、节点数（2D）；超出实验规模时启用图分块/多尺度策略
- [x] 边界与基面核查：`.geo` 断面高程与 `.opt` ZREF 交叉验证一致；2D 两套投影坐标在 M3 复算前统一确认

**数据接入**：M0 批量脚本增加"真实工程导入"入口（1D：steering/几何/初始水面线/边界水力条件文件；2D：`.cas` + SELAFIN 等），经 `sources/mascaret/ModulesAPI` 与顶层 `api/`（TelApy）驱动批跑。

**已入库工况（2026-09 登记自 schinta 流域防洪子系统模板，详见 docs/real_cases.md）**：

| 工况 | 类型 | 规模 | 真值 | 角色 |
|---|---|---|---|---|
| `mdx` | 1D 单流域 | 73 断面 / ~46 km / 闸门调度 | ✅ 历史 `.opt` 120 帧（洪峰 707 m³/s，水深最大 31.2 m） | 考卷 |
| `zxh` | 1D 单流域 | 23 断面 | ✅ 完整工程历史 `.opt` 24 帧（复算逐位复现 RMSE=0） | 母版（家族已建） |
| `wqh` | 1D 单流域 | 27 断面 | ✅ 历史 `.opt` 48 帧（复算逐位复现 RMSE=0） | 考卷+母版（家族已建） |
| `mdx_upstream` | 1D 耦合段 | 34 断面 | ✅ 镜像复算 48 帧（对历史偏差 6.4%） | 考卷（耦合链） |
| `mdx_downstream` | 1D 耦合段 | 29 断面 | ✅ 历史 `.opt` 72 帧（复算段错误待排查） | 考卷（耦合链） |
| `wqh_2d` | 2D 单流域 | 65,589 节点 / 130k 三角形 | ⏳ 待 TELEMAC-2D 复算（M3） | 待定 |
| `mdx_2d` | 2D 耦合段 | 65,126 节点 | ⏳ 待 TELEMAC-2D 复算（M3） | 考卷（耦合链） |

**母版家族（角色二，2026-09-11 生成并批跑完成）**：`family_mdx` **37/40** + `family_zxh`
**40/40**（完整工程母版重生成后零失败）+ `family_wqh` **40/40** 场景含 Mascaret 镜像真值（单场景 28–47 s）。扰动 = 糙率场 lognormal 分区缩放
（σ=0.2，patch 2 km，整体 0.8–1.25×）× 全部入流律（上游+区间入流）统一幅值缩放
0.5–2× 与时间拉伸 0.8–1.6×（保持流域水量事件一致性）。批跑含容错与物理合理性过滤
（拒收发散解）；22 个 zxh 失败均为 v8p4 求解器段错误（与扰动幅度无单调关系，已记档
`data/real_cases/family_*_run.log`），后续可通过调度系统重导出模板或升级内核解决。

耦合链：`mdx_upstream → mdx_2d → mdx_downstream`（运行顺序一维上游 → 二维 → 一维下游）。
导入入口：`python scripts/import_real_cases.py`（原始工程就地读取、不入库；派生数据进
git-ignored 的 `data/real_cases/`）。M1 的"真实 1D 工程"即 `mdx`，M3/M4 的真实 2D/耦合
即 `wqh_2d` / mdx 耦合链。

**随行安排**：M1 挂 1 个真实 1D 工程，M3 挂 1 个真实 2D（或耦合）工程；角色一与角色二使用的工程不可为同一个（或同批事件）。

---

## 风险与对策

| 风险 | 对策 |
|---|---|
| 对称扩散在双曲体制失真（激波抹平） | 定向分支兜底；仍不足则加大方向分支权重或改有向 Chebyshev 近似 |
| over-smoothing 随 k/层数增长 | λ₀·I 恒等项 + 残差式滤波 + Dirichlet 能量监控告警 |
| 大 Δt 训练不稳定 | 课程学习 + ψ 输出归一化 + 末层 Tanh（照搬 SWE-GNN 配方） |
| 干湿图拓扑随时间变化 | 每步重归一化 + 稀疏结构缓存；必要时冻结短时间窗内拓扑 |
| Mascaret 批量产数据慢 | 1D 小域先行；多进程批跑；2D 场景延后到 M3 阶段再扩 |
| 真实工程复算不过关（几何/基面/单位/糙率不一致） | 准入检查前置：复算对齐历史成果方可纳入轨道 |
| 真实项目数据保密 | 原始工程不入库（`data/` 已 git-ignore）；仓库只放脚本与匿名化派生数据 |
| 真实图规模远超实验规模 | 预留图分块/多尺度；小图训练 → 大图零样本（MeshGraphNets/SWE-GNN 先例） |

## 评测协议（对齐 SWE-GNN，便于直接对照发表）

- 变量精度：水深、单宽流量（1D 为流量）的全程多步 RMSE / MAE
- 范围识别：CSI（阈值 0.05 m / 0.3 m 两档；1D 用漫滩判别阈值）
- 效率：加速比 = TELEMAC-MASCARET 耗时 / 推理耗时（GPU、CPU 分开报告）
- 统计检验：KS 检验（p<0.05）判断模型间差异
- 消融清单：`-MDK`（退化为 SWE-GNN）、`-定向性`（退化为 SSGC/对称 MDK）、`-分裂`（纯 MDK 单分支）

## 目录规划

```
Flow-MDK/
├── plan/                 # PLAN.md（进度总览）+ update_progress_[yyyy-mm-dd].md（每日进展日志）
├── docs/                 # 真实算例清单、官方对照、结果报告、服务器手册
├── references/           # 背景文献（见 references/README.md）
├── configs/              # 实验配置（Flow-MDK / 忠实复现 / 消融 / 基线）
├── src/flow_mdk/
│   ├── layers/           # MDK 传播核、ψ 差值消息、算子分裂层
│   ├── models/           # encoder/processor/decoder、自回归 wrapper、模型工厂
│   ├── baselines/        # 对比架构（GCN / GAT / persistence）
│   ├── data/             # 图构建、特征约定、npz 数据集、干湿拓扑、分组批采样
│   ├── train/            # 递归多步损失、课程学习、训练器
│   ├── eval/             # 指标、rollout 评测、Dirichlet 能量
│   ├── gen/              # 合成场景族 + 1D 参考解算器 + 真实母版扰动族
│   └── utils/            # 种子、npz schema、日志
├── scripts/              # 生成/导入/复算/批跑/训练/评测/归档 CLI 与实验链
├── tests/                # 单元 + 端到端冒烟测试
├── datasets/             # 复现性归档（LFS：源码快照、raw datasets、算例、结果）
├── third_party/telemac/  # TELEMAC 源码/镜像接入说明
└── data/                 # 工作数据与原始工程副本（git-ignored）
```

## 待办与遗留项（Backlog）

| # | 事项 | 说明 / 方案 | 关联里程碑 |
|---|---|---|---|
| ~~L1~~ | ✅ **Part A v2 的 Mascaret 真值升级**（2026-09-12 完成 89/130） | 两段式初始化落地（SARAP 稳态 `.lig` → REZO，配方与坑位见 `docs/results_partA_swe.md`）；41 个失败场景转 L11；split 已过滤，原始 130 协议存 `split_full_protocol.json` | M1→M2 ✅ |
| ~~L2~~ | ✅ **体制对齐后的正式对比**（2026-09-12 本地预算完成，干净真值 × 128 场景重跑版） | 域内 GCN 0.79 ≈ GAT 0.83 < Flow-MDK 1.42 < SWE-GNN 4.50；**MDK 混合对本体骨架拯救 ×3.2（4/5 评测域成立）**、fam_mdx 零样本 Flow-MDK 最优（2.63，退化 ×1.8 < GCN ×3.9）。pre-patchfix 轮"Flow-MDK 域内最优"系污染真值+少 40% 数据的假象，已修正。**论文级预算结论归 L4** | M2 ✅（本地预算） |
| ~~L3~~ | ✅ **B1 训练 → B2 考卷消融**（2026-09-12 本地预算完成） | 三方消融首轮：SWE-GNN 1.67 / SSGC 1.83 / Flow-MDK 2.45，同量级无定论；Flow-MDK 域内欠拟合；体制分工初现端倪。**正式结论归 L4** | M2 ✅（本地预算） |
| ~~L4~~ | ✅ **论文级预算复测（服务器 A100，2026-09-13 跑 / 09-14 取回落定）** | G=64、150 epochs、单种子 seed=0，7 run 全部成功（Part A 四模型 + B1 三模型）。**判决**：①主干稳定性判据通过（flow_mdk 无崩坏；无门控 6 层 GCN 塌缩 35.4 m、GAT 1.92）；②合成 1D 域内 swegnn 2L×8 跳最优（0.72 vs flow_mdk 1.42），真实家族域深层门控系最优（ssgc 0.85 ≈ flow_mdk 0.87 << swegnn 2.15）；③定向 vs 对称无显著差异（KS p=0.81/p=1.0），**MDK 定向优势假设降级为探索性对照**；④共性 best epoch 极早（4–14）+ val 漂移 2–4×。报告 `docs/L4_report.md`（summarize_runs.py 一键生成）；λ₀ 曲线 `runs/lambda0_curves_paper.png`；runs 已入库归档。**剩余**：3 种子论文预算（收口）、best.pt 对照 + Dirichlet 富评（checkpoint 已取回，服务器 eval json 无 dirichlet 字段） | M2/M5 ◐ |
| ~~L5~~ | ✅ **over-smoothing 监控接入评测**（2026-09-13） | λ₀ 逐 epoch 已在 history.json；Dirichlet 能量经 rollout forward hooks 逐层计算（逐边归一）进 eval json（`eval/rollout.py`、`scripts/evaluate.py`）；曲线工具 `scripts/plot_mdk_lambda0.py`。首轮信号：flow_mdk 训练中末层 λ₀ 0.42→0.09 塌缩、GCN 逐层能量随深度增长。表示相似度指标未实现（可选，不再单列） | M2 ✅ |
| L6 | **mdx 家族补齐至 50**（可选） | 现 37 个（3 个段错误淘汰）；补采 13 个使三家族对称，总计 ~130 与论文对齐 | M2 前 |
| ~~L7a~~ | ✅ **真实 2D 工程真值（M3 开线，2026-09-13）** | `wqh_2d`/`mdx_2d` 全量重跑完成（telemac2d.py --ncsize=4，本机 docker；25h/15h 工况，151/91 帧 @ 600s），QC 通过（质量守恒 |ε|≤7.3e-15，深度/湿区/NaN 门控）；真值已挂 `meshes_2d/*.npz`（solver=telemac2d_docker_rerun）。**预期修正**：模板 old.slf 是单帧初始化快照而非历史结果档案——2D 无逐位复现校验，重跑即真值 + 物理门控。重跑工具 `ingest_telemac2d_truth.py` + 配方记档。L7 余项：合成 2D 场景族真值（需 `.cli` 生成器）+ 65k 节点训练（A100 + 图分块） | M3 ◐ |
| ~~L7b~~ | ✅ **合成 2D 场景族真值管线 + pilot（2026-09-13）** | 端到端管线当日打通（`run_telemac2d_docker.py` 重写：全墙 `.cli`（逐字克隆真实墙线）+ 单节点源区域入流（真实工程同款机制）+ 生产关键字 `.cas` + 自动摄取；`generate_scenarios_2d_family.py` 采样种子/溃口侧/流量/地形，70/15/15 split）。pilot 20 场景全过：97 帧、h_max 11.6–19.4 m、湿区终值 5–10%、体积守恒 |ε|≤3.3e-15、合计 24 min。扩到 50/130 场景纯参数化（~3 h）。调试坑位：Git Bash 改写 `-w /work`、源区域须在 cas 声明流量、qsl 需越界终点行、边基系统下 SUPG=0 | M3 ◐（训练待上） |
| L8 | **mdx_downstream 复算段错误排查** | 保留历史 `.opt` 为真值；需原调度系统重导出工程或 Fortran 级排查 | 低优先 |
| L9 | **加速比基线补全** | B2 场景的 `runtime_s` 需从历史 `.lis` 时间戳或复算实测补齐（当前仅家族场景有实测值） | M5 |
| L10 | **git 提交 09-11/09-12 改动** | wqh/zxh 内化、Part A v2、server runbook、L1 两段式真值管线、L2/L3 实验链与结果、进展日志待提交 | 流程 |
| L11 | **Part A v2 失败场景修复** | ✅ 2026-09-12 内核补丁后 126→128/130：根因为 v8p4 源码树本地魔改的 XAJ 侧向入流块在 `Q_XAJ.txt` 缺失时 `nlines/num_columns` 未定义 → 堆越界随机段错误（亦是真实家族 zxh 22 例段错误的根因）；补丁 + 备份 + 重建镜像 `flow-mdk-telemac:v8p4r0p1`，见 `datasets/telemac-mascaret-v8p4r0/PATCHES.md`。剩余 4 例为 `s1geo` 负索引（干涸极限工况，干净报错），低优先单独排查。**真实家族差异评估 ✅ 关闭（2026-09-13）**：117 场景（zxh 40 + mdx 37 + wqh 40）补丁内核 scratch 重跑全部成功，新旧真值**逐位一致**（max h-RMSE = 0.0，无一场景漂移）→ 已验证 B1/B2 真值不受内核缺陷影响，家族重跑不必要，L2/L3 结论在干净地基上成立；评估工具存档（`run_real_family.py --runs-root/--force` + `scripts/compare_family_truth.py`，报告在 `data/real_cases/_patchfix_diff/`）。衍生可选项：mdx 3 例被淘汰场景可在补丁内核下尝试复活（→ L6） | ✅ 关闭 |

## 进展日志

| 日期 | 文件 | 要点 |
|---|---|---|
| 2026-09-11 | [update_progress_2026-09-11.md](update_progress_2026-09-11.md) | 两轮会话：wqh/zxh 完整工程内化（复算逐位复现）、真实母版家族重建至 117 场景、Part A v2 130 场景扩建、CUDA 训练环境就绪、首轮四模型×四域评测与 A→B gap 量化、服务器 runbook、datasets 归档入库（LFS） |
| 2026-09-12 | [update_progress_2026-09-12.md](update_progress_2026-09-12.md) | L1–L3 本地推进：两段式初始化挂 Mascaret 全 SWE 真值；**内核源码级修复**（XAJ 魔改块未定义行为 + 上游 Q 边界垃圾 YFIX，备份/patch/镜像 `v8p4r0p1` 存档，真值 89→128/130，zxh 家族 22 例段错误同根因）；L2 四模型对比（干净真值重跑版：GCN 0.79 ≈ GAT 0.83 < Flow-MDK 1.42 < SWE-GNN 4.50，MDK 混合拯救本体 ×3.2 为稳健发现）；L3 三方消融首轮（B1→B2 同量级，待 L4 复测）；详见 `docs/results_partA_swe.md` |
| 2026-09-13 | [update_progress_2026-09-13.md](update_progress_2026-09-13.md) | 收尾/工具日：归档缺口补全（partA_v2 + L2/L3 runs + 最终权重入库，archive 脚本三处回归修复）；L5 监控接入评测（Dirichlet 进 eval json + λ₀ 曲线工具，flow_mdk 末层 λ₀ 塌缩信号）；L4 分析工具 `summarize_runs.py`（分组对比表/退化矩阵/KS，与手工表全对上）；L11 真值差异评估启动（117 场景补丁内核 scratch 重跑，冒烟逐位一致）；服务器 L4 同日开跑 |
| 2026-09-14 | [update_progress_2026-09-14.md](update_progress_2026-09-14.md) | **L4 落定日**：服务器 7 个 paper run 取回入库（results.csv 两机合并 121 行，归档刷新 9542 文件，MS_* 多种子 run 与 M3 真值 npz 顺带补档）；L4 判决——主干稳定性通过（GCN 塌缩 35.4 m 为反例）、合成 1D 域内浅层 8 跳最优（0.72 vs 1.42）、真实家族域深层门控系最优（0.85 vs 2.15）、定向 vs 对称仍无显著差异（p≥0.8）；**课题走向定调：继续，主张调整为「稳定深传播 + 基准 + 方法学」，定向性主战场移至 2D（M3）** |
