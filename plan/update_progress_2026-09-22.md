# 进展日志 · 2026-09-22（round 7：1×8 校正 + S2 大域 + 平凡基线复核）

> 工件取回 `G:\实验\FlowMDK\runs_server_260922_v1`（runs 731 行 registry + 41 份日志）。
> 本文档 = 对这批结果的分析判决 + 下一步计划。**范围：正文只主张二维 + 一二维耦合。**
>
> **一句话结论**：S1 仍在跑（唯一未完成项）；S2 与 1×8 臂已完成，但**两条都暴露了新的
> 尺度问题**——1×8 校正把 2D 的 ×9.6 头条打掉（官方 SWE-GNN 1×8 只落后 ×1.41），
> 而把「不做任何事」的平凡基线加进来后，**2D 域内除 flow_mdk 外全部基线（含官方
> 1×8、GCN、GAT、U-Net）都不优于冻结预测，GAT 经直接 rollout 证实就是恒等映射**。
> 这对论文是**换主轴**级别的发现，不是坏消息（见 §三）。

---

## 〇、状态盘点

| 项 | 状态 | 说明 |
|---|---|---|
| S1 耦合扩样（`run_M4v3_family.sh`） | ⛔ **已停（2026-09-22 用户停跑）** | `nocons` ×3 种子已完成；`swegnn s0` 于 09-22 08:19 重启（09-21 轮 batch-4 OOM 中断），无 eval json；`swegnn s1/s2` + `ssgc` ×3 **未开始**。按 1.7–3.5 h/种子估，**剩余约 20 h**（ARMS 默认 `nocons swegnn ssgc`） |
| S2 大域（`run_2d_larger_domain.sh`） | ✅ 已完成 + A2 补评闭合（§2.8） | 24 场景真值全部 QC PASS（8.3–8.6 min/场景，volume err ≤2.6e-15）；评测跑了，但**用的是被取代的 2×8 swegnn 权重**（见 §二.3） |
| 1×8 SWE-GNN 补充臂 | ✅ 完成 | 2D：`MS4b_2d_swegnn_s{0,1,2}`；耦合：`M4v2b_swegnn_s{0,1,2}`（三协议齐） |
| 1×8 真实考卷评测 | ❌ 未做 | 本机 `run_2d_swegnn_exams.sh`（纯推理）未跑；本地 registry 无 `MS4b` 行 |
| S3 轨迹证据（含 1×8） | ❌ 未重跑 | 需 `--refresh` 并把 1×8 与平凡基线并入 |
| 数据工件取回 | ❌ **缺** | 下载包**只有 runs/ 与日志**，无 `data/`。`data/scenarios_2d_larger/`（24 npz+split+meta）与 `data/real_cases/coupled_chain/`（8 新场景）**仅存于服务器** |
| registry 合并 / 白名单 | ❌ 未做 | 本地 902 行，下载包 731 行，需按 (timestamp,kind,run,split,checkpoint,data_root) 去重联合；`build_generalization_matrix.py` / `plot_pareto.py` 白名单未加新臂 |

---

## 一、S1 已出的耦合数（口径已就位）

M4v3 在**扩展后的 20 场景家族、5 场景测试集**上（test = fam000 / fam004 / fam011 / fam012 / fam015）：

| 臂 | last | best | ema |
|---|---|---|---|
| `nocons`（flow_mdk，无守恒罚项） | 1.476±0.411 | 1.608±0.394 | 1.477±0.411 |
| `swegnn` / `ssgc` | ⏳ 待跑 | ⏳ | ⏳ |

对照 v2 的 2 场景测试集（`nocons` 1.419 / 1.202 / 1.157）：**last/ema 同档，但 best 从 1.202 升到 1.608**。
→ 原「best 1.202」是小样本（2 场景）的乐观产物，扩样后不再成立。这一点必须改写 C3 的 best 数字。

门禁与切分均正常：`[gate] OK — fam012-019 draws match the pre-registered values`，split 13/2/5，
`fam011`（最强工况 Q×1.97）仍是最难场景（nocons s0 h-RMSE 1.915）。

### 1.1 ⚠️ 但把 persist 基线放进来后，耦合的结论被推翻（2026-09-22 当日补算）

数据取回后立即用项目自身 rollout 路径算出该域平凡基线（详见 §二.5）：

| | persist（冻结输入帧） |
|---|---|
| 耦合 v3 · 5 场景 | h-RMSE **1.4493±0.4072**，CSI@0.05 **0.8820±0.0201** |
| `nocons` 实际 | h-RMSE 1.4762（**+0.0268，0/5 场景胜**，Wilcoxon p=0.0625），CSI 0.8784（**×1.00**） |

→ **在扩展后的测试集上，flow_mdk 与"什么都不做"无法区分，且名义上更差。** v2 的 2 场景集上
还有 RMSE 优势（−0.133），扩样后消失。§三 将说明这对 C3 意味着什么。

---

## 二、五条判决（都是尺度问题，都改变正文）

### 2.1 1×8 校正：×9.6 头条不成立，但"机制"主张反而更干净

官方仓库保存的最优模型是 `n_GNN_layers: 1` + `K: 8` = **8 次消息传递**；我们此前跑的是
2×8 = 16 次（根因：上游根 config 不含该键，吃类默认值 2）。补齐 1×8 后，2D 家族域内
（20 test 场景，逐场景误差已跨 3 种子平均，KS 为场景级）：

| model | last | best | CSI@0.05 (last) |
|---|---|---|---|
| **flow_mdk** | **0.529±0.154** | **0.534±0.088** | **0.656** |
| gat | 0.716±0.205 | 0.740±0.207 | 0.034 |
| **swegnn(1×8，官方)** | **0.745±0.092** | **0.616±0.081** | 0.468 |
| -MDK（同 harness 无扩散分支） | 0.835±0.108 | 0.622±0.028 | 0.511 |
| gcn | 0.871±0.186 | 0.806±0.182 | 0.023 |
| ssgc | 1.820±0.115 | 1.288±0.061 | 0.437 |
| unet | 4.654 | 10.512 | 0.033 |
| unet(e6) | 13.903 | 0.915 | 0.031 |
| swegnn(2×8，旧臂) | 5.061±0.905 | 3.303±2.123 | 0.367 |

- **flow_mdk vs 官方 1×8**：`last` **×1.41**（KS p=9.6e-06，显著）；`best` **×1.15**（p=0.081，**不显著**）。
- **`-MDK` ≈ 官方 1×8**（best 0.622 vs 0.616，p=0.175 ns；CSI 0.511 vs 0.468）→ 独立复现
  「我们的残差 harness 不含扩散分支时 ≈ 官方浅层 SWE-GNN」。**L16 的「harness ×5.3–6.1」
  必须撤回**——那个倍数来自 2×8 臂的不稳定，不是 harness 的功劳。
- **但三分机制排序完好且更干净**：定向 < 无分支 < 对称，在 `last` 上 RMSE（0.529 < 0.835 < 1.820，全 p<0.001）
  与 CSI（0.656 > 0.511 > 0.437）**两个指标都成立**。在 `best` 上 CSI 排序翻转为 -MDK > flow_mdk。
- 1×8 臂自身协议漂移明显（s1：last 0.525 但 best 0.974，best 反而更差），是 C4 的新素材。

**判决**：可写的是「×1.41（last，显著）／×1.15（best，不显著）」，**不可再写 ×9.6／×8.8**。
C1、F3/F4/F5/F6 与摘要里的那四个数字全部要重写。

### 2.2 加进「不做任何事」的基线后，2D 域内的对比尺度被彻底改写

由于所有 2D 臂的 `num_previous_steps = 1`（输入窗口 = 帧 0–1），我用**完全相同的窗口**
从真值算出平凡基线（`data/scenarios_2d_family`，20 test 场景，H=1，95 帧）：

| 平凡基线 | h-RMSE | CSI@0.05 |
|---|---|---|
| persist（冻结第 1 帧） | **0.7156±0.2112** | 0.0273 |
| 全干（预测 h≡0） | 0.7461 | 0.0000 |
| 真值全局 RMS(h) | 0.7461 | — |

（湿单元占比仅 **3.6%**，故"均值 RMSE"被干单元稀释——这正是下面现象的量纲来源。）

逐场景**配对**检验（seed 平均，last 协议）：

| model | mean h-RMSE | 优于 persist 的场景数 | Wilcoxon p | 判定 |
|---|---|---|---|---|
| **flow_mdk** | **0.5288** | **18/20** | **8.2e-05** | **唯一显著优于"不做"** |
| gat | 0.7158 | 12/20 | 0.81 | 与 persist 无法区分 |
| swegnn(1×8) | 0.7446 | 10/20 | 0.45 | 与 persist 无法区分 |
| -MDK | 0.8349 | 4/20 | 1.0e-03 | 显著差于 persist |
| gcn | 0.8708 | **0/20** | 1.9e-06 | 显著差于 persist |
| swegnn(2×8) | 5.0605 | 0/20 | 1.9e-06 | 显著差于 persist |

**并且把 GAT 的退化直接证死了**（本机用下载包权重跑真实 rollout，场景 `T2D_110`）：

```
MS4_2d_gat_s0/last.pt :  预测场在 95 帧内的 RMS 变化 = 0.00157 m   ← 真值 0.6685 m
                         预测首帧 vs 输入帧 的 RMS 差 = 0.000028 m
```

**GAT 输出的就是输入帧本身（恒等映射），全程没有预测。** 它的逐场景 RMSE 与 persist 的
相关系数 **corr = 1.000、最大偏差 0.011 m** ——这解释了它反常的 ±0.001 种子方差。
GCN 同样退化（corr=1.000，误差恒为 persist 的 **1.217 倍**），U-Net 亦然（CSI 0.033）。

CSI 独立印证同一件事：域内 last 上 flow_mdk 0.656 vs persist 0.027（**×24**），
而 gat 0.034 / gcn 0.023 / unet 0.033 与 persist **同档**。

**判决**：原 C1 的「对 6 层 vanilla GCN/GAT 只领先 ×1.35–1.65」是在跟**不会预测的模型**比。
正确写法是把 persist/all-dry 列为第 0 行基线，并指出**只有 flow_mdk 越过它**。

### 2.3 S2 大域：结论有价值，但必须重跑评测 + 归一化口径

大域（128×128 @ 100 m = 12.8 km，24 场景，零样本）实测 RMSE / **CSI**：

| model | last RMSE | best RMSE | **CSI@0.05 (last)** |
|---|---|---|---|
| flow_mdk | 0.273±0.169 | 0.268±0.130 | **0.653** |
| gat | 0.370±0.033 | 0.386±0.061 | **0.027** |
| gcn | 0.564±0.230 | 0.507±0.168 | **0.014** |
| ssgc | 0.914±0.801 | 0.648±0.377 | 0.438 |
| swegnn(2×8) | 2.384±3.088 | 1.708±2.098 | 0.390 |

两个必须修的问题：

1. **口径过期（runbook §124 的警告被踩了）**：`run_2d_larger_domain.sh` 硬编码
   `runs/MS4_2d_${model}_s${seed}`，`MODELS` 里没有 1×8 臂。S2 于 09-21 16:45 跑完，
   而 1×8 的 2D 训练 09-22 09:02 才结束 → **大域表里没有官方 1×8 基线**。
2. **RMSE 跨域不可直接比**：单元数 ×4、干单元占比不同，0.273（12.8 km）与 0.529（6.4 km）
   不是同一把尺子；只能用**模型间比值**或换指标。

**CSI 在这里给出了决定性对照**：大域上 flow_mdk CSI 0.653 而 gat 0.027 / gcn 0.014——
**vanilla 基线的低 RMSE 在域尺寸轴上被独立复现为"冻结预测"**。这给 C4（平均 RMSE 奖励
冻结预测）添了**第二个独立证据，且是在全新轴上**；同时 flow_mdk 对 2×8 的 RMSE 优势
（×8.7）在换用正确基线前不能对外写。

### 2.4 三个域的平凡基线（2026-09-22 数据取回后补算，harness 产出）

数据取回后用**项目自身的 rollout 路径**（`flow_mdk.models.factory` 的 `baseline_persistence` 臂）
在三个域上跑出 floor，与手算值**逐位一致**（双向验证通过）：

| 域 | persist h-RMSE | persist CSI@0.05 | 全干 h-RMSE | 真值 RMS | 湿单元占比 |
|---|---|---|---|---|---|
| 2D 家族 64×64（20 场景） | **0.7156±0.2112** | **0.0273±0.0090** | 0.7461 | 0.7461 | 3.6% |
| 2D 大域 128×128（24 场景） | **0.3507±0.0963** | **0.0300±0.0084** | 0.3660 | 0.3660 | **0.84%** |
| 耦合 v3（5 场景） | **1.4493±0.4072** | **0.8820±0.0201** | 3.6189 | 3.6189 | 38.5% |

全部模型的判定（逐场景配对，`last` 协议，n=场景数）：

| 域 | model | h-RMSE | 优于 persist | Wilcoxon | CSI | CSI/persist |
|---|---|---|---|---|---|---|
| 2D 64×64 | **flow_mdk** | **0.5288** | **18/20** | **8.2e-05** | **0.656** | **×24.0** |
| | gat | 0.7158 | 12/20 | 0.81 | 0.034 | ×1.25 |
| | swegnn(1×8) | 0.7446 | 10/20 | 0.45 | 0.468 | ×17.2 |
| | -MDK | 0.8349 | 4/20 | 1.0e-03 | 0.511 | ×18.7 |
| | gcn | 0.8708 | **0/20** | 1.9e-06 | 0.023 | ×0.84 |
| 2D 128×128（零样本） | **flow_mdk** | **0.2735** | **18/24** | **8.5e-04** | **0.653** | **×21.8** |
| | gat | 0.3698 | **0/24** | 1.2e-07 | 0.027 | ×0.90 |
| | gcn | 0.5640 | 0/24 | 1.2e-07 | 0.014 | ×0.47 |
| | ssgc | 0.9139 | 0/24 | 1.2e-07 | 0.438 | ×14.6 |
| | swegnn(2×8) | 2.3837 | 0/24 | 1.2e-07 | 0.390 | ×13.0 |
| 耦合 v3 | nocons(flow_mdk) | 1.4762 | **0/5** | 6.3e-02 | 0.878 | **×1.00** |
| 耦合 v2 | main / nocons / ssgc | 1.404 / 1.419 / 1.459 | 2/2 · 1/2 · 2/2 | — | 0.686 / 0.571 / 0.678 | ×0.78 / ×0.65 / ×0.77 |
| 耦合 v2 | swegnn(2×8) / swegnn(1×8) | 1.5725 / 1.5957 | 0/2 | — | 0.873 / 0.870 | **×1.00 / ×0.99** |

**读法（三条）**：

1. **只有 flow_mdk 越过 no-skill 门槛**，且在两个二维域上一致（18/20 与 18/24，p≈1e-4），
   CSI 为 persist 的 **×22–24**。其余每个臂至少在 RMSE 上不优于冻结预测。
2. **GAT 是二次独立复现的"冻结预测"**：域内 corr=1.000、最大偏差 0.011 m；
   大域上 0/24 胜、CSI ×0.90（≈与 persist 同值）。GCN/U-Net 更差（CSI 低于 persist）。
3. **耦合域上 sweep 系（1×8 与 2×8）恰好等于 persist**（CSI ×1.00 / ×0.99，RMSE 差 +3%），
   说明该臂学成了恒等映射；而 flow_mdk 在扩样后连 RMSE 优势也没了（0/5，CSI ×1.00）。

**附带一个免费的机理演示（可写进正文）**：harness 是"恒等 + 学习增量"结构（`decoder.py`
标题即 "residual increment prediction"），bias-free 解码器在初始化时输出≈0 → 未训练的模型
**按构造就等于 persist**。实测印证：一个**随机初始化**的 flow_mdk 在 T2D_110–116 上的
逐场景 h-RMSE 与 persist floor 的差是 **+0.0015 m（7 个场景全部在 +0.0014…+0.0016）**，
即 0.15% 量级。这条同时（a）证明训练后的臂落到 persist 水平等于"学到的增量≈0"，
（b）从完全不同的一条代码路径（模型前向 vs 解析冻结帧）**独立校验了 floor 的计算**。

### 2.5 根因定位：耦合臂的损失函数 99% 是流量，且真值有一个坏节点

§1.1 的"耦合域全员退化到 persist"不是架构性质，是被两件事造成的，都有量化证据。

**(a) 目标函数与实际报告的指标错位（跨域配置不一致）。** 损失是物理单位下的逐变量 RMSE 加权和
（`train/loss.py`：`loss_t = Σ_o γ_o·RMSE_o`，`γ=(1,3)`，docstring 写的是 "water depth, then
**discharge/unit-discharge**"）。但两个域的第二个通道量纲完全不同：

| 域 | 通道 2 是什么 | 量级 | 1·RMSE_h | 3·RMSE_ch2 | **h 在目标里的占比** |
|---|---|---|---|---|---|
| 2D 家族 | 流速 (m/s) | O(0.01–1) | 1.166 | 0.011 | **99.0%** |
| 耦合家族 | 1D 是 Q(m³/s)、2D 是 \|q\|(m²/s) | O(0.01–2×10⁴) | 0.808 | **86.1** | **0.9%** |

即 `γ=(1,3)` 是从官方 SWE-GNN 搬来的（其第二变量是**单位宽流量**），套到耦合图上后
**损失 99.1% 由流量主导，而论文报告的指标是 h-RMSE**——1D 真实河网域（第二通道同为 Q）同理。
这解释了为什么 2D 臂能把 h 学好（目标就是 h），而耦合臂的 h 几乎没被优化。

**(b) 真值里有一个坏节点，进一步放大了 (a)。** 下游 1D 链的第 2 个节点
（全局索引 `node_offsets[2]+1 = 65161`）在通道 2 上是垃圾值：

- 该节点 t=8 时为 **−15017**，而 28 个邻居都在 592–1841 m³/s；最坏 −18859。
- 全时程负值占比 3.34% ≈ 1/29 节点；上游链与 2D 网格**负值占比均为 0**。
- **20 个场景全部存在**（下游 \|Q\| 峰值 19 540–20 722，而入口入流峰值仅 664 m³/s，即 30×）。
- 该节点的 h 通道正常（0.94 m）——只有通道 2 坏。

**根因已定位到求解侧（2026-09-22 追加）**：解析原始 `mdx_downstream_coupled/mascaret_ecr.opt`
（Optyca 结果文件，3112 帧 × 29 断面）后确认，**下游第 2 断面（sec1，紧贴入流边界）的原始 Q
序列本身就含 −20039.5**，其余断面全时程在 [−208, 2291]；fam011/fam015（q_scale 1.80/1.97 两个
最强工况）在 **sec3 还有第二处伪影**（−3070/−3303），即伪影随入流强度增长。`.rep` 的稳态块
（QMIN 行）同样显示 sec1 = −9955。→ **缺陷在 Mascaret 下游求解设置**（边界断面数值伪影，
疑似初始条件/入流边界/隐式参数问题），**不在 npz 装配、不在家族构建器**。修复应改
`mdx_downstream_coupled` 工程的 `.xcas/.lig`（A6）。

→ 这一个节点把通道 2 的动态范围拉到 ±2×10⁴，既污染编码器输入，又在"99% 是 Q"的损失里
成为主导项。**耦合族的真值需要 QC 与重装**（在 `couple_mdx_chain.py` / 下游 1D 装配段）。

**服务器端验证脚本**：`scripts/verify_server_data.py`（A1–A7 + B/C/D 四段，纯 CPU ~2 min；
重建/重训前先跑，任何一项翻绿/翻红都直接决定 A6/A7 的范围）。

**(c) 训练史佐证。** 耦合臂 train_loss 60 轮只降 9%（22.6→20.7），而 2D 臂 114 轮降 58%
（0.0315→0.0131）。按同一损失口径，**恒等预测在耦合训练集上的损失是 86.9 (H=1)/169.2 (H=8)**，
模型却是 22——说明模型在训练集上比恒等好 4–8 倍，**不是没拟合上**；问题在于该目标
（实质是 Q）与论文报告的 h 不是同一个量。

**(d) q_scale 从未作用到上游 1D 腿（家族设计缺陷，2026-09-22 追加核实）。** 全部 20 个场景的
上游 1D 腿（34 节点，两个通道）**逐字节相同**（fam000 vs fam011 vs fam005 `array_equal=True`，
通道 2 峰值比 1.000），尽管 fam011 的 q_scale=1.97。根因在 `build_coupled_family.py`：
扰动入流律只写进 2D 入口边界（`q_p = q_out * q_scale`），上游 1D 腿复用基准场景装配、从不重跑。
后果有三：① 图内部物理不一致——1D 腿报基准流量、2D 腿在 1.97× 洪水；② 上游 34 节点
（含 target）在测试集里的取值**训练时逐字见过**（该腿上的记忆化是合法的）；③ "最强工况
fam011"的难度差异只存在于 2D 腿。下游腿不受影响（随 2D 出口变化，已核实 fam000≠fam011）。

**因此 §3.2 的处置要改**：不是"输入窗口不够"（A0 降级为次要），而是
**先修真值坏节点 + 把 h 的权重调到与报告口径一致，再重训耦合臂**。


### 2.6 两处口径核对（一处是虚惊，一处是真缺陷）

**(a) `previous_t` 虚惊 —— 记录以免后人重复踩坑。** 我一度以为官方 SWE-GNN 的输入窗口是
`previous_t: 3` 而我们是 1（即又一个 `n_GNN_layers` 式的误读）。核对
`datasets/swegnn-official/results/**/config.yaml` 全部 **14 份**后确认：**全部是 `previous_t: 2`**，
**只有仓库根 `config.yaml` 是 3** —— 与 runbook §1.2 记录的 `n_GNN_layers` 踩坑完全同型。
我们的 `num_previous_steps: 1` ↔ 官方 `previous_t: 2`（harness 实际送入
`dynamic[:num_previous_steps+1]` = 2 帧，且 `base.py:72` 把 2 帧全部展平喂入编码器，未被浪费），
config 里的注释是对的。**结论：无 previous_t 口径缺口；教训是永远读 `results/` 而不是根 config。**

**(b) 真缺陷：`baseline_persistence` 臂从未被跑过，且跑不起来。** `src/flow_mdk/models/factory.py`
早就注册了 `baseline_persistence`（`src/flow_mdk/baselines/persistence.py`，零参数），其 docstring
明确写着它存在的意义是"metric calibration (CSI / RMSE floors)…**a trained surrogate must beat it**"。
但 registry 里 **0 行**——这条不变量从未被检查，而一检查就发现**大多数臂违反它**。
另：`eval/rollout.py:106` 的 `next(model.parameters())` 对零参数模型抛 `StopIteration`，
必须显式传 `device` 才能跑（补 A4 时要一并修）。

---


原主轴「我们的方法比 SWE-GNN 准 ×9.6」已经不可写。但把平凡基线加进来之后，得到一条
**更硬、更可证伪、更少被审稿人一句话打掉**的主轴：

> **在淹没问题代理上，"全域平均 RMSE"是被冻结预测系统性奖励的伪指标：官方 SWE-GNN(1×8)、
> GCN、GAT、U-Net 在二维域内与"冻结输入帧"无法区分（GAT 经 rollout 证实为恒等映射，
> RMSE 逐场景 corr=1.000）；只有定向 MDK 扩散算子产出的代理真正越过不该被越过的
> no-skill 门槛（RMSE −26%，CSI ×24），并在耦合与真实考卷上维持该优势。**

这条主轴的资产是现成的：C4 的指标批判 + S3 轨迹证据 + 新增的 persist 基线对照，
三处独立指向同一结论，而且**把"我们比基线好多少"从 ×9.6 的脆弱主张，换成"基线根本没在做事"
的可复现事实**。代价是必须如实写出 flow_mdk 的绝对精度也不高（0.529 vs 真值 RMS 0.746）。

**必须在正文如实交代的两处不利事实**（不藏）：
1. `best` 协议上官方 1×8 的 CSI（0.535）**优于** flow_mdk（0.439）——2D 的"最优"是协议依赖的。
   可辩护的写法：`last` 为主协议（不依赖 val 选点），`best` 的翻转本身作为 C4 的证据
   （选择器优化 val loss，与 CSI 不同向）。
2. 耦合域上 flow_mdk 的 CSI（0.72）**低于** persist（0.89）——它改善了深度值但发了更多虚警。

---

### 2.7 B1/B2 结果（2026-09-22 本机补齐，A4/A5 同日完成）

**A4/A5 落地**：`rollout.py` 零参数缺陷已修、`evaluate.py` 支持 `--checkpoint none`；
四条 persist floor 行入 registry（2D 家族 **0.7156** / 大域 **0.3507** / 耦合 v3 **1.4492**，
与手算逐位一致；v2 根本地没有，跳过）；registry 合并 **967 行**（904∪731，去重 63 行新增）；
矩阵/pareto 白名单加 `MS4b_2d_swegnn`→swegnn(1x8)、`M4v2b`、`M4v3`、`floor_persist_*`，
新增「2D →大域 12.8km 零样本」「耦合家族 v3」两列并重生成（`docs/generalization_matrix.md`
145 格、`docs/pareto_frontier.md` 12 点——pareto 顺带复核参数恒等式：swegnn(1x8) 104k
≈ 官方 103.7k+192 ✓）。

**B1 · 1×8 真实考卷（12 项评测，3060）**：

| 口径 | swegnn(1×8) | 对照 |
|---|---|---|
| H=8 best | **2.680±0.428** | flow_mdk 2.471±0.101（×1.085）；旧 2×8 2.643±0.328（持平） |
| H=8 last | 2.868±0.068 | flow_mdk 3.004±0.487 → **1×8 反超 flow_mdk 的 last** |
| 全时程 best | 5.948±2.966 | flow_mdk 16.584±3.247 / 旧 2×8 7.343（数值有界假象，见 B2） |
| 全时程 last | 11.382±8.763 | 同上 |

→ 训练视野内 flow_mdk 仍最优但差距收窄到 **×1.085**；且 1×8 的 last（2.868）**低于**
flow_mdk 的 last（3.004）——考卷上"last 协议谁最优"发生翻转，与域内的方向相反。
1×8 的种子方差（±0.428）大于 flow_mdk（±0.101），协议漂移更重（C4 素材）。

**B2 · 轨迹重算（7 臂 + persist 参照线，mdx_2d 探针节点）**：

| 臂 | 末步 RMSE (m) | 峰值/真值 | 判定 |
|---|---|---|---|
| flow_mdk（定向） | 32.20 | 9.55 | 真发散 |
| **swegnn（官方 1×8）** | **24.61** | **8.13** | **真发散（新证据）** |
| swegnn（旧 2×8） | 21.29 | 6.59 | 真发散 |
| ssgc（对称） | 14.87 | 8.05 | 真发散 |
| MDKoff（无扩散分支） | 9.28 | 4.49 | 真发散 |
| gcn / gat（vanilla） | 0.49 / 0.55 | 0.507 / 0.508 | 冻结 |
| **persist（冻结输入帧）** | **0.98** | **0.508** | 冻结（按定义） |

**新发现：官方 1×8 臂同样发散（峰值 8.13× 真值）**——此前轨迹证据只覆盖 2×8 旧臂，
"发散属 MDK 系"的说法不成立：**全部带残差增量 harness 的训练代理在视野外都发散**，
vanilla/persist 一族有界但峰值恒为 0.5×（gcn/gat 与 persist 的峰值比逐位一致 = 恒等映射
的又一印证）。C2 的结论因此更干净也更诚实：**视野外没有可用的代理（发散的与无动力学的
各占一边）**，且这是整个代理类别在该训练协议下的性质，不是本文方法的特有缺陷。

产物：`runs/exam_trajectories_mdx_2d_1x8.png` + 缓存 `runs/exam_trajectories_mdx_2d_1x8.npz`
（脚本已支持 `persist` 参照线；探针节点 42293/42725/42294）。

---

### 2.8 A2 大域补评结果（2026-09-22 服务器执行，`runs_server_260922_v2` 已同步入仓）

`VERIFY=1` 权重复核**通过**：1×8 权重在服务器重评 2D test 得 last 1.163/0.525/0.547、
best 0.477/0.973/0.397，与原记录逐位吻合（差 <0.5%，GPU 非确定性量级）→ 取回的 1×8
权重无损。两遍评测行并存（①与①′并发抢跑，json 门未拦住；无害，矩阵按种子取末值）。

**大域 12.8 km 零样本补齐后的完整表（三种子平均，n=24 逐场景配对 Wilcoxon）**：

| arm | last h-RMSE | best h-RMSE | last CSI |
|---|---|---|---|
| **flow_mdk** | **0.273±0.169** | **0.268±0.130** | **0.653** |
| swegnn(1×8，官方) | 0.357±0.174 | 0.312±0.166 | 0.476 |
| gat | 0.370±0.033 | 0.386±0.061 | 0.027 |
| flow_mdk(-MDK) | 0.426±0.310 | 0.313±0.182 | 0.524 |
| gcn | 0.564±0.230 | 0.507±0.168 | 0.014 |
| ssgc | 0.914±0.801 | 0.648±0.377 | 0.438 |

- **flow_mdk vs swegnn(1×8)**：RMSE **×1.304**（Wilcoxon p=2.3e-06，22/24 场景胜）；
  CSI **×1.37**（p=1.2e-07，24/24）→ **两个指标、两种协议全部显著**。
- **机制排序在域尺寸轴上复现**：定向 0.273 < 无分支(-MDK) 0.426 < 对称(ssgc) 0.914
  （flow_mdk vs -MDK ×1.557，p=1.2e-07，24/24）。
- **②档主张的最终形态**：域内 ×1.41（last，KS p=9.6e-06）+ 大域 ×1.30（Wilcoxon p=2.3e-06）
  ——两个二维域、两种协议上 flow_mdk 均显著优于官方深度的 SWE-GNN；`best` 协议差距收窄
  （域内 ×1.15 ns、大域 ×1.17）但 CSI 大域上仍 24/24 显著。×9.6 时代的头条数字正式退役，
  替换为这组可复现的跨域显著结果。
- 大域上 persist floor 0.351：swegnn(1×8) last 0.357 **仍不优于冻结预测**（0/24 胜，
  与域内一致），flow_mdk 18/24（p=8.5e-04）——"唯一越过 no-skill 门槛"在尺寸轴上再次成立。

同步记录：12 份大域 eval json 入 `runs/`、registry 合并 **1007 行**（979∪759）、
`data/2d_larger_1x8_0922.log` 入档、矩阵重生成（大域列填齐）。

---

## 三、这对论文意味着什么（建议：换主轴 + 耦合章降级）

### 3.1 二维章：换主轴，不是降级

原主轴「我们的方法比 SWE-GNN 准 ×9.6」已经不可写。但把平凡基线加进来之后，得到一条
**更硬、更可证伪、更少被审稿人一句话打掉**的主轴：

> **在淹没问题代理上，"全域平均 RMSE"是被冻结预测系统性奖励的伪指标：官方 SWE-GNN(1×8)、
> GCN、GAT、U-Net 在二维域内与"冻结输入帧"无法区分（GAT 经 rollout 证实为恒等映射，
> RMSE 逐场景 corr=1.000）；只有定向 MDK 扩散算子产出的代理真正越过不该被越过的
> no-skill 门槛（RMSE −26%，CSI ×24），并在域尺寸轴（6.4 km → 12.8 km 零样本）上
> 复现同一结论（18/24 胜、CSI ×22，其余臂 0/24 胜）。**

这条主轴的资产是现成的：C4 的指标批判 + S3 轨迹证据 + 新增的三域 floor 对照，
**四处独立指向同一结论**，而且把"我们比基线好多少"从 ×9.6 的脆弱主张，换成"基线根本没在做事"
的可复现事实。代价是必须如实写出 flow_mdk 的绝对精度也不高（0.529 vs 真值 RMS 0.746）。

**必须在正文如实交代的两处不利事实**（不藏）：
1. `best` 协议上官方 1×8 的 CSI（0.535）**优于** flow_mdk（0.439）——2D 的"最优"是协议依赖的。
   可辩护的写法：`last` 为主协议（不依赖 val 选点），`best` 的翻转本身作为 C4 的证据
   （选择器优化 val loss，与 CSI 不同向）。
2. 该域湿单元仅 3.6%（大域 0.84%），平均 RMSE 的量纲被干单元主导——这既是 C4 的论据，
   也意味着"绝对 RMSE 数字"不适合当卖点，CSI 与 no-skill 门槛才是。

### 3.2 耦合章：必须从"方法优势"降级

耦合是收窄后本文**唯一的新颖点**，但现在的证据是：

- 扩样后 flow_mdk **0/5 场景优于 persist**（p=0.0625，方向不利），CSI **×1.00**；
- swegnn（1×8 与 2×8）**恰好等于 persist**（CSI ×0.99/×1.00）——该臂学成恒等映射；
- ssgc/main 在 RMSE 上略优（−0.09/−0.15）但 CSI 反而更差（×0.77/×0.78，虚警增多）。

→ **在耦合域上没有任何臂展示了超过"冻结预测"泛化能力的技能**，此前 C3 的
「×1.24 / ×1.36 优势」与「定向 vs 对称空白闭合」都是在比一组**都不做事的模型**。
按预注册判据（S1 的验收三条），这属于**应降级写法**的情形。

**建议处置（依据 §2.5 的根因，按优先级）**：

1. **先修数据（A6，两项缺陷一并修）**：下游链坏节点（65161 通道 2 垃圾值）+ 上游 1D 腿未随
   q_scale 缩放（§2.5(d)）——前者污染损失与编码器输入，后者使家族的场景多样性只在 2D 腿上存在、
   且上游腿存在训练集记忆通道。在真值未修之前，耦合族上的任何训练结论都不该采信。
2. **再修目标（A7）**：把耦合臂的 `var_weights` 调到与**报告口径一致**（h 与 Q 各自按其尺度归一
   后再加权，而不是原始 m³/s 直接进加权和）。同时把 `max_epochs` 提到与 2D 同档（60 → 150）。
   **判据**：5 场景测试集上 h-RMSE 是否落到 persist（1.4493）以下、且 CSI 是否仍不低于 persist。
3. **A0（输入窗口）降为次要**：§2.5(c) 显示模型在训练集上远比恒等好，问题不在信息量。
   但 A7 通过后仍值得各补一组 `num_previous_steps=8`，因为耦合域真值在预测窗内只变化 1.2–1.9 m
   （场 RMS 3.6 m），时序上下文是否必要仍需一个直接对照。
4. **无论 A6/A7/A0 结果如何**，正文必须把 persist 列为第 0 行基线（A4），并如实报告
   "耦合域上所有臂 ≈ 或劣于冻结预测"。
5. 若 A6+A7+A0 都救不回，C3 改为 **工程可行性 + 数据/方法学贡献**（异构单图 65 189 节点可训可评、
   一二维接口守恒、真实链端到端可跑），**不宣称精度优势**；耦合的精度主张移出摘要。


---

## 四、下一步计划

### A. 阻断性（2026-09-22 二维-only 判定后修订）

| # | 状态 | 任务 | 说明 |
|---|---|---|---|
| **A2** | 🔴 **必跑（脚本就绪）** | 大域补齐官方 1×8 与 -MDK 两行零样本评测 | `scripts/run_2d_larger_1x8.sh`（纯推理 ~20 min；`VERIFY=1` 可先复核 1×8 权重）。大域表现有行缺与 flow_mdk 对照最关键的两臂 |
| **A0′** | 🟡 可选防御（脚本就绪） | 输入窗口 1→8 对照（GAT/GCN 重训） | `scripts/run_2d_p8_window.sh`（~15–30 h）。回应"单帧输入饿死基线"的审稿质疑；结论不进主表 |
| **A4** | ⬜ 本地待做 | persist/all-dry floor 固化进评测管线 | 三域 floor 已验证（0.7156 / 0.3507 / 1.4493）；顺带修 `eval/rollout.py:106` 零参数模型 `StopIteration` |
| **A5** | ⬜ 本地待做 | registry 合并（902∪731→964）+ 矩阵/Pareto 白名单加 `MS4b`/`M4v2b` | 防 B1 v1/v2 式静默排除 |
| ~~A1~~ | ⛔ 已停 | ~~S1 跑完~~ | 用户 09-22 停跑（旧真值+旧损失上继续跑为负期望价值） |
| ~~A6~~ | ⛔ 已取消 | ~~耦合真值重建~~ | 缺陷全在耦合族；2D 三根为纯 TELEMAC-2D（B/C/D 验证全绿）。修复方案留档给第二篇 |
| ~~A7~~ | ⛔ 已取消 | ~~耦合目标口径对齐 + 重训~~ | 同上 |
| ~~A3~~ | ✅ 已完成 | ~~取回数据工件~~ | md5 服务器↔本地逐文件一致（verify 脚本 09-22 双端核验） |

### B. 紧接着（写正文前）

| # | 任务 | 成本 | 说明 |
|---|---|---|---|
| **B1** | 本机跑 1×8 真实考卷评测 `bash scripts/run_2d_swegnn_exams.sh` | ~1 h（3060，纯推理） | C2/F10 的考卷表里 swegnn 仍是 2×8 |
| **B2** | 重跑 S3 轨迹分析（`analyze_exam_trajectories.py --refresh`），**把 1×8 与 persist 基线并入同一张图** | ~1 h | 轨迹图是"基线没在做事"的最直观证据 |
| **B3** | 重写 C1–C4 措辞 + 重生成 F3/F4/F5/F6/F10（含 persist 对照列/线） | ~1 天 | **先做 A4**，否则图里没有参照系 |

### C. 可选 / 需拍板

- **C1（建议暂不做）2D 家族的 `num_previous_steps` 从 1 提到 8**：所有臂同为 1 帧输入是
  同一口径（公平），persist 也在同窗口下算。提到 8 要重训全部主臂（3–6.5 h/种子 × 多臂），
  收益不明。**建议：正文披露"单帧输入"口径即可**。
- **C2 是否把 `main`（守恒罚项）臂并入 M4v3**：v2 已确立负结果，重跑增益有限。
  仅在 A1 的预注册判据不通过、需要更多臂支撑时再补。
- **C3 S4 第三例真实二维工程**：依赖数据可得性，不阻塞。
- **C4 「选择器与 CSI 不同向」能否量化**：需要中间 epoch 检查点，现只有 best/last/ema
  → 要么重训存 ckpt（~1 种子即可），要么按现象+定性写。

### D. 建议执行顺序（二维-only 终版）

```
✅ 已完成（2026-09-22 本机）：A4 floor 入管线 → A5 registry 967 行 + 白名单 → B1 1×8 考卷 12 项 → B2 轨迹（§2.7）
```

```bash
# 以下仍待服务器执行（用户停跑 S1 后的剩余项）：
上传  ：考卷根 exams_2d{,_h8}（2×32 MB）+ 4 个脚本（A2/B1/B2/A0′，见 §七 服务器执行清单）
✅ A2 大域补评 + VERIFY 复核（服务器，09-22，§2.8）→ ✅ B1/B2（本机，§2.7）→ [可选] A0′（p=8 窗口，GAT 优先 ~8–10 h）
取回  ：§七 的 rsync 清单（含 registry）
本地  ：A4（floor 入管线）→ A5（registry 合并 + 白名单）→ B3（图表重生成 + persist 并入）
✅ 写作已交付（2026-09-22）：paper_skeleton_2D_only.md（repo + 论文目录）、
     02_稿件_二维版/99_全文初稿_二维版.md、引用核验报告（15 条，2 处更正）、
     04_汇报/FlowMDK_组内汇报_20260922_纯二维版.pptx、03_图表 二维版图件 5 张
```

---

## 七、服务器执行清单（B1/B2 最终于本机完成，见 §2.7；本清单仅剩 A2/A0′）

> 前置一次性上传（~100 MB + 4 个脚本），之后按 Phase 1→3 顺序执行（合计 GPU ~1 h），
> Phase 4 可选过夜。每阶段前 `nvidia-smi` 确认卡空。全部脚本断点安全（json/last.pt 存在即跳过）。

```bash
# ---------- Phase 0 · 一次性上传 ----------
tar czf exams_2d_roots.tgz data/real_cases/exams_2d data/real_cases/exams_2d_h8
rsync -av exams_2d_roots.tgz SERVER:Flow-MDK/data/real_cases/
rsync -av scripts/run_2d_larger_1x8.sh scripts/run_2d_swegnn_exams.sh          scripts/analyze_exam_trajectories.py scripts/run_2d_p8_window.sh          SERVER:Flow-MDK/scripts/
# 服务器上解包：
#   cd ~/Flow-MDK/data/real_cases && tar xzf exams_2d_roots.tgz && rm exams_2d_roots.tgz

# ---------- Phase 1 · A2 大域补评（必跑，~20 min）----------
bash scripts/run_2d_larger_1x8.sh 2>&1 | tee data/2d_larger_1x8_$(date +%m%d).log
# 判据：swegnn(1x8) 24 场景 h-RMSE / CSI vs flow_mdk 0.2735 / 0.653
# （VERIFY=1 前缀可先复核 1×8 权重：2D test 应复现 last≈0.745 / best≈0.616）

# ---------- Phase 2 · B1 1×8 真实考卷（必跑，~15 min）----------
bash scripts/run_2d_swegnn_exams.sh 2>&1 | tee data/1x8_exams_$(date +%m%d).log
# 判据：vs flow_mdk H=8 best 2.471±0.101；vs 旧 2×8 swegnn 2.643

# ---------- Phase 3 · B2 轨迹重算（推荐，~30 min）----------
python -c "import matplotlib" 2>/dev/null || pip install matplotlib
python scripts/analyze_exam_trajectories.py --scenario mdx_2d   --out runs/exam_trajectories_mdx_2d_1x8.png   --runs "flow_mdk=runs/MS4_2d_flow_mdk_s0"          "swegnn(1x8)=runs/MS4b_2d_swegnn_s0"          "swegnn(2x8)=runs/MS4_2d_swegnn_s0"          "ssgc=runs/MS4_2d_ssgc_s0"          "-MDK=runs/L16_mdkoff_2d_s0"          "gcn=runs/MS4_2d_gcn_s0"          "gat=runs/MS4_2d_gat_s0" 2>&1 | tee data/s3_1x8_$(date +%m%d).log
# 注：服务器若无中文字体，png 图注会显示方框——不影响判读；缓存
# runs/exam_trajectories_mdx_2d_1x8.npz 是真正产物，终版图在本地由缓存重绘。

# ---------- Phase 4 · A0′ p=8 窗口（可选，过夜）----------
CUDA_VISIBLE_DEVICES=0 ARMS="gat" bash scripts/run_2d_p8_window.sh 2>&1     | tee data/2d_p8_$(date +%m%d).log

# ---------- Phase 5 · 取回 ----------
for s in 0 1 2; do
  rsync -av "SERVER:Flow-MDK/runs/MS4b_2d_swegnn_s$s/" "./runs/MS4b_2d_swegnn_s$s/"
  rsync -av "SERVER:Flow-MDK/runs/ptbest_MS4b_2d_swegnn_s$s/" "./runs/ptbest_MS4b_2d_swegnn_s$s/"
  rsync -av "SERVER:Flow-MDK/runs/L16_mdkoff_2d_s$s/" "./runs/L16_mdkoff_2d_s$s/"
  rsync -av "SERVER:Flow-MDK/runs/ptbest_L16_mdkoff_2d_s$s/" "./runs/ptbest_L16_mdkoff_2d_s$s/"
done
rsync -av SERVER:Flow-MDK/runs/exam_trajectories_mdx_2d_1x8.npz          SERVER:Flow-MDK/runs/exam_trajectories_mdx_2d_1x8.png ./runs/
rsync -av SERVER:Flow-MDK/runs/results.csv ./runs/
rsync -av SERVER:Flow-MDK/data/2d_larger_1x8_*.log SERVER:Flow-MDK/data/1x8_exams_*.log          SERVER:Flow-MDK/data/s3_1x8_*.log ./data/
# （Phase 4 若跑了，另取 runs/MS4c_2d_*p8_s*/ 的 config/eval/history + ptbest 孪生 + results.csv）
```

---

## 五、风险与交接

1. ~~服务器数据未归档~~ **✅ 已解除**（2026-09-22 数据已落地本地，见 A3）。
   剩余归档动作：把 `scenarios_2d_larger/` 与扩展后的 `coupled_chain/` 补进
   `datasets/`（Git LFS）并更新 `datasets/MANIFEST.json`，否则仍只在工作目录里。
2. **M4v3 与 M4v2 共用 `data/real_cases/coupled_chain_family` 根，`split.json` 已被覆写为 13/2/5**。
   已知陷阱（规划时留档）：M4v2 的 run json 与 registry 行不可变、结论不受影响；但**日后不要**拿
   M4v2 的 run 对该根跑 `evaluate.py --split test`（会静默按 5 场景算，与记录值不可比）。
   **本次已规避**：本地新根 `coupled_chain_family_v3` 是独立目录，旧根未被改动。
3. **S1 的 `swegnn` 臂两次被 OOM 打断**（round 5、round 6 首轮、09-21 轮）。重启前务必
   `nvidia-smi` 确认卡空；`swegnn` 臂显存最高，千万别与 S2 的 `TRAIN=1` 同时跑。
   A0 若要上卡，需与 A1 排开。
4. **本机 GPU 残留进程**（2026-09-22 实际操作教训）：中断后台任务时若只 kill 了 shell 外壳，
   `python` 子进程会成为孤儿并继续占满本机 3060（实测 GPU 100%、3.7 GB 未释放）。做 B1
   （1×8 真实考卷评测）前先 `nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv`
   确认；必要时用 `powershell Get-CimInstance Win32_Process -Filter "Name='python.exe'"`
   查命令行再 `taskkill //PID <pid> //F`。

5. **口径纪律**：`num_previous_steps=1`（= 官方 `previous_t: 2`，已核对无缺口）、
   湿单元占比 3.6%（2D 64×64）/0.84%（大域）/38.5%（耦合）、
   `-MDK` 与 `swegnn(2×8)` 同为消融/旧臂——这些都要在数据与设置节披露。
6. 本轮分析脚本（`data/` 已 gitignore，A4 落地后即可删）：
   `_scratch_analyze_260922.py`（registry 汇总）、`_scratch_ks_260922.py`（场景级 KS）、
   `_scratch_baselines_260922.py`（三域平凡基线 + 配对检验）、
   `_scratch_run_persistence.py`（用项目自身 `baseline_persistence` 臂复算 floor）。

---

## 六、取回清单（A3 细化，体积为本地同类工件的实测值）

> **状态 2026-09-22：用户已取回全量**（`scenarios_2d_larger/` 918 MB 含 `_work/`；
> `coupled_chain/` 4.7 GB 含各场景 TELEMAC 工作目录）。比按需取多约 5 GB，但换来完整自足，
> 无需再挑——下面的清单保留为"若需重取/换机器"的参考。

**1. `data/scenarios_2d_larger/` —— 必须取，且很小**

| 取 | 不取 |
|---|---|
| `L2D_*.npz`（24 个）、`split.json`、`family_meta.json` | **`_work/`（TELEMAC 工作目录，占绝大部分体积，可重生成）** |

体积：64×64 家族实测 0.29 MB/场景、压缩比 14.1×；128×128（节点×4、边×4）外推 ≈1.1 MB/场景
→ **24 场景 ≈ 26 MB**。这是本轮"最划算"的取回项。

**2. `data/real_cases/coupled_chain/` 的 8 个新场景 —— 必须取，但要挑着取**

单个场景目录实测 **219 MB**，构成如下：

| 内容 | 体积/场景 | 处理 | 理由 |
|---|---|---|---|
| `mdx_chain_famXXX.npz` | **10.6 MB** | **取**（8 个 ≈ 85 MB） | 训练/评测用的最终工件，5 场景测试集（含 fam012/015）本地复现的前提 |
| `mdx_2d_coupled.npz` | 25.6 MB | 建议取（8 个 ≈ 205 MB） | 该场景 2D 支路的真值，单独重生成需 ~17 min CPU；取回后归档自足 |
| `mdx_2d_coupled/` | 169 MB | **不取** | TELEMAC 工作目录（.slf/.res/.cas 等中间件） |
| `mdx_downstream_coupled/` | 16 MB | **不取** | 同上（下游 1D 工作目录） |

另需 `coupled_chain/coupled_family_report.json`（合并后应为 20 条）与 `coupled_chain/split.json`
（现为 13/2/5）。**注意**：本地 `coupled_chain_family/` 目前只有 12 个真实文件拷贝，
取回后需重跑一次
`python scripts/prepare_coupled_family_root.py --test ... --val ...` 把 fam012–019 链进来
（或在本地手动补齐）。**不要**在服务器上重跑该脚本（会再次覆写共享根的 split.json）。

**3. 不必取**

- `data/scenarios_2d_family/`（130 场景，本地齐全，且 S1/M4v3 未改动它）；
- 原有 12 个耦合场景与 `mdx_2d_coupled*`（本地已有 3.0 GB 全量；S1 的 RNG 修复保证 i≤11
  的抽样值不变，可抽查一个 checksum 确认）；
- `data/real_cases/exams_2d*`（本机考卷根，本就只在本机）；
- TELEMAC 镜像与内核（已在 `datasets/telemac-mascaret-v8p4r0`，7.5 GB LFS）。

**4. S1 跑完后还要补一次 `runs/`**

本次下载包抓取于 09-22 09:31，`M4v3_swegnn_s0` 当时无 eval json、`swegnn s1/s2` 与 `ssgc`
完全不存在。S1 收尾后需再取：`runs/M4v3_{swegnn,ssgc}_s{0,1,2}` + 对应 `ptbest_*`/`ptema_*`
孪生 + `runs/results.csv` + `data/M4v3_*.log`（每臂约 5 MB，可忽略体积）。

**5. 归档去向**：`/data/` 与 `/runs/` 均被 gitignore；仓内归档走 **`datasets/`（Git LFS）**，
现有先例 `datasets/runs`、`datasets/partB_real_cases`、`datasets/partA_v2`。新增的
大域族与扩展后的耦合族应各补一条 LFS 归档并更新 `datasets/MANIFEST.json`。
