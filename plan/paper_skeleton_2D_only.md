# 论文骨架 · 纯二维版（round 7 定稿口径）

> 起草：2026-09-22。**范围决定**：正文只主张**二维**数据域；一维已留档（第二篇），
> 一二维耦合降为局限节一段（详见 §5 风险）。依据：`plan/update_progress_2026-09-22.md`
> 全部判决（§2.1–2.8）、`docs/generalization_matrix.csv`（1007 行 registry 重生成）、
> `05_文献解读/参考文献库核验_20260921.md`。
>
> 与 09-21 版（paper_skeleton_2D_coupled.md）的差别：**①** 官方深度基线改为 1×8
> （8 次消息传递），×9.6 头条退役；**②** 引入 persist/all-dry 平凡基线为第 0 行；
> **③** 耦合章撤出正文；**④** 补齐大域 12.8 km 零样本轴（S2+A2）。
>
> **口径纪律**：不得出现会被留档数据反驳的跨域泛化表述；`num_previous_steps=1`
> （=官方 previous_t: 2，已核对 14 份 results/ config）；主协议 last，best 仅作选点
> 治理讨论；耦合域结论不进正文。

---

## 0. 定位与对标基线

| 项 | SWE-GNN 原文（HESS 2023） | 本文（纯二维版） |
|---|---|---|
| 算例 | 130 次二维溃口模拟，6.4/12.8 km，64/128 网格 | 二维合成 **130**（6.4 km/64²，同域同网格）+ **大域 24**（12.8 km/128²，对齐其 dataset 3）+ 真实漫滩考卷 ×2 |
| 官方模型深度 | `n_GNN_layers:1, K:8` = **8 次消息传递**（E1–E5 五重证据） | 逐字对齐（1×8 臂 104k 参数 ≈ 官方 103.7k+192） |
| 基线 | CNN、GAT、GCN、SWE-GNN_ng（自身消融） | GCN / GAT / U-Net / SSGC / -MDK 消融臂 / **persist·all-dry 平凡基线** |
| 真实算例 | 无 | 真实漫滩考卷 ×2（零样本，H=8 + 全时程） |
| 机理归因 | 无 | 三分消融（定向/无分支/对称）双域复现 + 恒等映射证明 |
| 评测方法学 | 单次训练 | 三种子 × last/best(/ema) × 场景级配对检验 × no-skill 门槛 |

**核心差异点**：不是 SOTA 精度，而是 **①"基线没在做事"的方法学发现（no-skill 门槛）
② 干净的机制归因 ③ 域尺寸泛化轴 ④ 严格评测协议**。

## 1. 标题草案

1. *Flow-directed Markov diffusion kernels: the only surrogate that beats
   persistence in GNN flood modelling — a controlled attribution study on 2D
   shallow-water domains*
2. *What do GNN surrogates of shallow-water flows actually learn? Frozen
   baselines, no-skill floors, and a directed-diffusion operator that
   genuinely propagates water*
3. （稳重型）*Residual operator-splitting with directed Markov diffusion for
   deep GNN surrogates of two-dimensional shallow-water flows: accuracy,
   attribution, and evaluation pitfalls*

## 2. 目标期刊

| 期刊 | 契合度 | 备注 |
|---|---|---|
| **Environmental Modelling & Software**（主推） | 模型+基准+可复现+评测方法学正中 scope | elsarticle，8000–10000 词 |
| HESS（备选 1） | SWE-GNN 原刊，直接对话 | 需更强水文叙事 |
| Water Resources Research（备选 2） | 方法学批判角度亦可 | 需压缩机制章 |

## 3. 主张清单（claim → evidence，全部数字为已验证机器表值）

### C1′（二维主结果 · 换主轴）
**在二维淹没问题代理上，全域平均 RMSE 是被冻结预测系统性奖励的伪指标；官方深度的
SWE-GNN(1×8)、GCN、GAT、U-Net 与"冻结输入帧"无法区分，只有定向 MDK 扩散算子产出的
代理真正越过 no-skill 门槛，且该优势在 6.4→12.8 km 域尺寸轴上复现。**

证据（last 协议，20/24 test 场景，逐场景配对 Wilcoxon）：
- 2D 域内：flow_mdk **0.529** vs persist **0.716**（**18/20 胜，p=8.2e-05**；CSI 0.656
  vs 0.027 = **×24**）；swegnn(1×8) 0.745（10/20，p=0.45 无法区分）；gat 0.716（12/20，
  p=0.81）；gcn 0.871（**0/20，p=1.9e-06 显著更差**）；unet 4.654；ssgc 1.820。
- 大域零样本：flow_mdk **0.273** vs persist 0.351（**18/24，p=8.5e-04**；CSI 0.653 vs
  0.030 = **×22**）；swegnn(1×8) 0.357（14/24，p=0.97）；gat/gcn CSI 0.027/0.014。
- 恒等映射证明：GAT rollout 输出≈输入帧（预测场 95 帧 RMS 变化 0.0016 m vs 真值
  0.669 m；逐场景 RMSE 与 persist corr=1.000，偏差 ≤0.011 m）；**随机初始化模型与
  persist 逐场景差仅 +0.0015 m**（0.15%）——harness 按构造恒等于 persist，未训练即地板。
- 对官方深度基线的优势（双域双指标）：域内 RMSE ×1.41（KS p=9.6e-06）、大域 ×1.30
  （Wilcoxon p=2.3e-06，22/24）；CSI 域内 ×1.40（p=5.8e-10）、大域 ×1.37（24/24）。
  **best 协议差距收窄**（域内 ×1.15 p=0.081；CSI 甚至翻转 0.439 vs 0.535）——如实写，
  并归入 C4。

### C2′（真实迁移与全时程边界）
**合成→真实二维迁移在训练视野内成立（H=8），flow_mdk 最优且最稳；全时程视野外，
全部带残差增量 harness 的训练代理（含官方 1×8）真发散，vanilla 一族有界但峰值恒为
真值 0.5 倍——视野外没有可用的代理，发散是该训练协议下整个代理类别的性质。**

证据：H=8 best flow_mdk **2.471±0.101** 最优（swegnn(1×8) 2.680±0.428、ssgc 2.693、
gcn 3.627、gat 3.635；×1.085）；**last 协议 1×8 反超**（2.868 vs 3.004）→ 协议限定。
全时程轨迹（F10，探针节点）：真值涨至 17 m 后回落，flow_mdk 峰值 **9.55×** 真值、
**swegnn(1×8) 8.13×**、2×8 6.59×、ssgc 8.05×、-MDK 4.49× 单调放大（真发散）；
gcn/gat/persist 峰值比 0.507/0.508/0.508（冻结，无动力学）。**归因闭合**：-MDK 同样
发散 + 官方 1×8 同样发散 → 与 MDK 扩散分支、与残差增量解码、与具体模型均无关。

### C3′（耦合章 · 撤出正文，降为局限段）
一二维耦合家族（65 189 节点单图、20 场景）**可训可评、端到端管线可复现**，但
(a) 扩样后无臂优于冻结预测（nocons 0/5，CSI ×1.00）；(b) 定位出三个数据/目标缺陷
（下游 Mascaret 边界伪影、上游腿未随 q_scale 缩放、损失 99.1% 为流量）。**正文只在
局限节如实交代一段**，工件与缺陷文档留档（`plan/update_progress_2026-09-22.md`
§2.5–2.6、verify 脚本）。不给任何耦合精度主张。

### C4（评测与选点方法学）
**单种子结论不可信；选点治理可救回 ×2.7 且跨架构有效；选点器优化的 val loss 与
水印指标（CSI、no-skill 门槛）不同向。**
- E6 配方：flow_mdk best 4.811→**1.751**（×2.7，KS p=2.4e-11）；U-Net best 10.512→
  **0.915±0.236** 但 last/ema 恶化（4.654→13.903）→ patience 需按架构调。
- 协议翻转实证：官方 1×8 的 s1 best（0.973）**劣于** its last（0.525）；考卷上 1×8 的
  last 优于 flow_mdk 而 best 不然；2D 域内 best CSI 排序与 last 相反。
- 全时程平均 RMSE 奖励冻结预测（C1′ 证据 + F10 轨迹）——必须配 no-skill 门槛与
  轨迹级证据。

### C5（可复现基准）
真值管线 TELEMAC-2D（内核补丁 v8p4r0p1、两段式初始化、逐位复算校验、质量守恒
≤1e-15）；registry **1007 run**；同环境权威计时（L9，5 考卷）；代码/数据可获取；
**三域 persist/all-dry floor 入管线**（`evaluate.py --checkpoint none`）。

## 4. 表与图（资产状态，全部已生成/可生成）

| 编号 | 内容 | 资产 |
|---|---|---|
| T1 | 数据族汇总（2D 130 + 大域 24 + 考卷 2；真值管线 QC） | 待写（数据齐） |
| T2 | 二维主表（8 臂 + persist × last/best × 3 种子 + 场景胜率 + KS/Wilcoxon） | **数据齐**（matrix CSV） |
| T3 | 机制归因表（定向/无分支/对称 × 双域 + 官方 1×8 参照 + p 值） | **数据齐**（§2.8） |
| T4 | 考卷表（H=8 + 全时程 × 8 臂 + persist × 双协议） | **数据齐** |
| T5 | ~~耦合家族表~~ → 删除 | — |
| T6 | 加速比表（L9 权威计时 5 考卷 + pareto 参数量） | **数据齐** |
| F1 | 方法总览 | `fig2_方法架构.png` ✅ |
| F2 | 数据体系（二维版重绘） | ⚠ 需按 fig1 裁一维支路 |
| F3 | 二维主结果（域内 last/best + 大域 + persist 地板线） | **✅ `fig4_域内精度对比_2D版.png`** |
| F4 | 机制归因（三分 × 双域 + 官方 1×8 虚线） | **✅ `fig5_深度匹配消融_2D版.png`** |
| F5 | 二维评测矩阵热图（4 列 + persist 行） | **✅ `fig6_泛化矩阵_2D版.png`** |
| F6 | Pareto（参数–精度–加速，8 点） | **✅ `fig7_精度效率Pareto_2D版.png`** |
| F7 | ~~耦合链诊断~~ → 删除 | — |
| F8 | λ₀ 曲线 + 逐层 Dirichlet | `fig8_lambda0曲线.png` ✅ |
| F9 | 选点治理三协议（E6.1） | 🟡 待创建（数据齐） |
| F10 | 考卷全时程轨迹（7 臂 + persist 参照 + 官方 1×8） | **✅ 已更新**（B2 版） |

## 5. 审稿风险与预案

| 风险 | 预案 |
|---|---|
| "你们把基线饿死了（单帧输入）" | 与官方 previous_t=2 逐字对齐（14 份 results/ config 核对）；可选 A0′ p=8 防御实验 |
| "×1.3–1.4 优势太小" | 主动分账：机制归因（定向 vs 无分支 ×1.58/×1.56 双域）+ no-skill 门槛（基线全体 ≈ persist）才是主张；精度不是卖点 |
| "全时程你的方法也发散" | 如实承认并归因到代理类别（官方 1×8 同发散，F10）；主张收窄为"视野内预演 + 周期校正"运营边界 |
| "为什么没有一维/耦合？" | 范围声明 + 局限节一段（一维留档第二篇；耦合缺陷留档，耦合章撤出） |
| "best 协议 CSI 翻转" | 主动写进 C4：选点器优化 val loss 与 CSI 不同向——这本身是方法学贡献 |
| "为什么不对比 ResNet/国内同类（如童超 2025）？" | 类别已由 U-Net 覆盖：ResNet-18 与 U-Net 同属图像卷积模型，诊断出的失败根源（湿单元稀疏 + 单帧输入 + 平均指标）与骨干无关；童超 2025 口径不同（流量序列驱动、逐小时、单场景族 500 场），其 RMSE 0.0898 m 与本文数字不可并排比较——这本身即 C4"跨论文 RMSE 不可比"的例证，在相关工作正面引用。若投中文刊被点名，补一个 U-Net→ResNet-18 骨干变体臂（协议照抄，约 1 天）作 rebuttal |
| "persist 也算基线？" | 引 no-skill/climatology 惯例（预报验证学标准做法），harness 恒等构造 + 随机初始化演示支撑 |

## 6. 待办

1. F2 二维版数据体系图（fig1 裁剪）
2. F9 选点治理图（E6.1 数据在 registry）
3. B3 稿件（`02_稿件_二维版/`，与骨架同步）
4. 汇报 PPT（`04_汇报/FlowMDK_组内汇报_20260922_纯二维版.pptx`）
5. 引用复核报告更新（`05_文献解读/`，联网核对骨架引用条目）
