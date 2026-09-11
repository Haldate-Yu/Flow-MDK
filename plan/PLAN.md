# Flow-MDK 研发计划（PLAN）

> 目标：以 SWE-GNN（Bentivoglio et al., 2023）为骨架、以水力定向马尔可夫扩散核（MDK，S2GC/Zhu & Koniusz, ICLR 2021）为传播改造核心，构建覆盖 **1D / 2D / 1D-2D 耦合** 三类场景的浅水方程 GNN 代理模型，训练数据由本地 TELEMAC-MASCARET（`D:\tmp\telemac-wz-260529\telemac-mascaret`，镜像 `flow-mdk-telemac:v8p4r0`）批量生成。
>
> 另设**真实案例轨道**（贯穿 M1–M5，见专门章节）：以真实项目建模文件做效果检验与训练母版，核心产出为 synthetic→real 泛化 gap。
>
> 方法核心：**对流-扩散算子分裂** —— 有向差值消息（SWE-GNN 式）承载波动/对流动力学，水力定向 MDK 滤波承载扩散性回水效应；MDK 级数截断由物理扩散长度 √(2DΔt) 匹配；残差式滤波（作用于增量）+ λ₀·I 恒等项防 over-smoothing。

---

## 实验数据总体结构（两部分，2026-09-11 就绪）

| 部分 | 内容 | 真值来源 | 规模 |
|---|---|---|---|
| **A · 模拟数据**（对齐 SWE-GNN 协议） | 1D 场景族：几何（床面/宽度/糙率场）× 水情（陡峰/缓峰 γ 型过程线）随机采样，链式图 | 内置 1D 隐式扩散波参考解算器（Mascaret 接入后可替换） | 50 场景 × 49 帧（`data/scenarios_1d/`，split.json 60/20/20） |
| **B · 真实项目模拟数据** | B1 母版家族：真实几何（mdx 73 断面/46 km/闸门、zxh 23 断面）× 合成水情（糙率场 lognormal 分区扰动 + 全部入流律统一幅值/时间拉伸） | Mascaret docker 批跑（`scripts/run_real_family.py`，容错+合理性过滤） | **117 场景**（mdx 37 + zxh 40 + wqh 40，`data/real_cases/family_*/`，各含 split.json） |
| | B2 真实历史事件考卷：mdx（洪峰 707 m³/s 历史事件）、zxh、mdx_upstream/downstream（`.opt` 回放/复算） | 历史 `.opt` 或镜像复算 | 4 场景（`data/real_cases/scenarios_1d/`） |

评测对照结构：Part A 训练 → Part A 测试（合成域内）；Part A 训练 → B1/B2 零样本迁移
（**synthetic→real gap，论文核心**）；B1 训练 → B2 考卷（真实域内）。2D 部分沿用同一
两部分结构，随 M3 接入 TELEMAC-2D 后扩展。

---

## M0 · 环境与数据管线（预计 1–2 周）✅ 2026-09-11 完成

- [x] Python 环境：`torch` + `torch_geometric`（torch 2.11+cpu / PyG 2.7，本机 CPU；代码 device 自适应）
- [x] Mascaret 无头批量运行：docker 镜像 `flow-mdk-telemac:v8p4r0`（自 `D:\tmp\telemac-wz-260529` 构建）；独立启动器调通（`FichierCas.txt`/`Abaques.txt`/PATH/WORKDIR 要点记入 `scripts/run_real_family.py`）；TelApy 库亦已编译备用
- [x] 1D 场景族设计：糙率 K 场 lognormal 分区扰动、入流过程线族（γ 型陡峰/缓峰 + 双峰）、断面几何扰动（`src/flow_mdk/gen/scenarios_1d.py`）
- [x] 2D 场景族设计：Perlin 噪声 DEM + 参数化溃口边界（对齐 SWE-GNN 设定，`gen/scenarios_2d.py`）；真值待 TELEMAC-2D 复算（M3）
- [x] 数据格式约定：每场景 → `npz`（节点静态特征 + 动态特征序列 + 边几何 + 干湿序列 + 元数据），schema 见 `src/flow_mdk/utils/io.py`
- [x] 干湿判定与图拓扑快照存储（`data/topology.py`：wet 序列 + 边活动出现/消失记录）

**验收**：✅ 50 个 1D 场景（Part A）+ 真实母版家族 80 场景（Part B1）可一键复现生成，含 metadata；真实工况 5 个入库（Part B2，见真实案例轨道）。

## M1 · 一维基线复现（预计 2–3 周）◐ 进行中（管线就绪，训练待跑）

- [x] 链式图构建（断面=节点，`data/graph_1d.py`；异构拓扑批次用 `GroupedBatchSampler`）
- [x] SWE-GNN 架构 1D 移植：ψ 差值消息、残差增量预测、动态 encoder 无偏置 —— **已与官方仓库逐行对照并修正**（每层 K 跳、逐层激活、MLP 尾激活、RMSE 仅水区损失、梯度值裁剪；见 `docs/swe_gnn_official_comparison.md`），忠实复现配置 `configs/1d_swegnn_official.yaml`
- [x] 训练配方：递归多步损失（H=8，RMSE+γ 加权）、课程学习（H: 1→8，15 epoch/步）、ψ 输出归一化、末层 Tanh、`_mask_small_WD` 输出掩码
- [x] 评测脚本：RMSE/MAE（h, Q）+ CSI（0.05/0.3 m 两档）+ 加速比（`eval/` + `scripts/evaluate.py`）
- [x] 真实案例轨道（1D）：5 个真实 Mascaret 工程导入（`scripts/import_real_cases.py`）→ **mdx/zxh/ybs 完成复算校验**（偏差有因记档）→ 真实母版家族 80 场景批跑 → 零样本随行验证（待训练后执行，见 M5 前置）

**验收**：✅ 基线管线全链路收敛（首轮四模型对比 + A→B 零样本 gap 已产出，见 `docs/results_partA.md` 与 `datasets/runs/` 归档）；真实 1D 工程完成复算校验 ✅（详见 docs/real_cases.md）与首次零样本评估 ✅。剩余：更长预算收敛复测、B1 训练→B2 考卷的真实域内对比（转入 M2）。

## M2 · Flow-MDK 传播改造（预计 3–4 周，核心创新）

- [ ] 水力定向转移矩阵 P：以流量/Froude 加权（上游→下游），每步随干湿重归一化
- [ ] MDK 级数实现：Neumann 有限截断（或幂迭代近似），k 由扩散长度 √(2DΔt) 匹配
- [ ] 算子分裂：advective 分支（SWE-GNN 差值消息）+ diffusive 分支（MDK 滤波作用于增量），可学习混合系数
- [ ] λ₀·I 恒等项与平滑深度监控（Dirichlet 能量 / 表示相似度指标，量化 over-smoothing）
- [ ] 大 Δt 实验：层/k 与时间步的权衡曲线（对应 SWE-GNN Fig. 8）

**验收**：1D 上完成三方消融——**纯 SSGC（对称 MDK）vs 纯 SWE-GNN（无 MDK）vs Flow-MDK（混合）**，并给出各自适用体制（缓变/瞬变）的证据。

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
├── plan/PLAN.md          # 本文件
├── references/           # 背景文献（见 references/README.md）
├── src/flow_mdk/
│   ├── data/             # 图构建、数据集加载（1D 链 / 2D 网格 / 耦合异构）
│   ├── models/           # encoder/processor/decoder、MDK 层、算子分裂模块
│   ├── train/            # 训练循环、课程学习、损失
│   └── eval/             # 指标、消融、Pareto
├── scripts/              # TELEMAC-MASCARET 批跑、场景生成
└── data/                 # 生成的训练数据（git-ignored）
```
