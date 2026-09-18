# 结果报告 · Part A v2（Mascaret 全 SWE 真值）与 B1→B2 消融（L1/L2/L3，2026-09-12）

> 本地预算：`hidden_dim=32, 40 epochs, curriculum_steps=4`（与首轮 v1 对比同预算，便于
> 前后对照）。论文级预算（G=64、150 epochs、A100）转服务器复测，见 PLAN 待办 L4。
> 单种子（seed=0），所有结论均为初步。

## L1 · Part A v2 的 Mascaret 真值升级

**实现**（`scripts/run_partA_mascaret.py` + `scripts/run_mascaret.py`）：
官方 `1_Steady_Kernel` 两段式初始化——

1. SARAP 稳态内核（code 1，恒定基流 + 法线水深下游水位）计算渐变流水面线；
   干涸床面隆起时按 1×/3×/9× 基流阶梯加大稳态流量重试（事件本身会淹没隆起，
   湿初始化只影响预热时段）；
2. 稳态剖面写成 `init.lig`（permanent/LIDO 格式，formatFichLig 2）→ 瞬态内核
   （code 3，与真实工程一致）从该线起步；SARAP 三档均失败时退化为自下游向上
   回填的单调湿水面线（fill line）。

**关键配置发现**（逐条查证 v8p4 源码/官方算例后确定）：

| 要素 | 配置 | 依据 |
|---|---|---|
| 初始水面线 | 文件式 `modeEntree 1` + `formatFichLig 2` | 键盘内联（modeEntree 2）段错误；瞬态内核无初始线报 err 349 |
| 下游边界 | 法线水深称率曲线 Q(Z)（律 type 5 + `typeCond 1 4`，Test13 配方） | 强加水位于局部急流断面不适定（初始回显 Fr≈1.3）；称率表须下探到床面以下 2 m，否则干锋期插值越界中止 |
| 时间步 | `pasTempsVar true` + `nbCourant 0.8` + `critereArret 1`（tempsMax） | 固定 30 s 步长（扩散波参考解的步长）在全 SWE 核失稳；`pasStock` 单位是步数不是秒 |
| SARAP 参数块 | 整块换用官方 `parametresNumeriques`/`parametresModelePhysique` | 瞬态模板缺稳态内核必读节点 → xcasReader 读空 → 段错误 |

**产出**：初版两段式批跑 89/130；随后对 Mascaret 源码做**内核级修复**后全量重跑达
**128/130**（`run_partA_mascaret.py --force`，全部走上 SARAP 稳态初始化）。修复内容
（详见 `datasets/telemac-mascaret-v8p4r0/PATCHES.md`，含备份与 patch 文件，镜像
`flow-mdk-telemac:v8p4r0p1`）：

- **XAJ 侧向入流块的未定义行为（主因）**：源码树本地魔改的 XAJ 读取在
  `Q_XAJ.txt`/`X_XAJ.txt` 缺失时 `nlines`/`num_columns`（intent(out)）未赋值，
  主循环以垃圾索引越界读堆 → 随机段错误（41 例失败的根因，也是真实家族 zxh
  22 例段错误的根因）。带符号 debug 内核定位到 `mascaret.f90:1021` 后修复为
  确定性空表；81/89 个原通过场景的真值因此有 ≤0.16 m 级别的去污染修正。
- **上游 Q 强加边界的垃圾 YFIX（次因）**：临界流附近把 `-床面高程` 当水深送进
  几何表查询（原有干净报错分支被注释），钳制为当前节点实际水深。

真值与扩散波参考解交叉验证（A1_001）：无系统偏差（bias +0.03 m），全 SWE 峰值更高
符合体制差异；补丁内核对已通过场景输出**逐位一致**（回归验证）。剩余 4 例
（A1_017/A1_067/A2_006/A2_008）为另一类独立缺陷（`s1geo` 几何表负索引，干涸极限
工况，干净运行时报错），低优先单独排查。split 已过滤为 128 场景（A1_train 60/60
恢复完整协议；原始 130 协议存 `split_full_protocol.json`）。

> 注：本文件的 L2 表格基于**补丁后 128 场景干净真值**的重跑结果（早先 89 场景
> 版本的结果在 git 历史与 `data/L2_partA_swe_experiments_pre-patchfix.log`）。

## L2 · 体制对齐后的正式对比（Part A v2 训练 → 域内 + 零样本 Part B）

水深 RMSE（m）；补丁内核干净真值、128 场景（A1_train 恢复完整 60/20/20 协议）；
A-test = A1_test+A2+A3（49 场景）；零样本 = Part A 模型直接推理真实几何场景族与
B2 真实考卷。

| 模型 | A-test h | A-test Q | → fam_mdx | → fam_zxh | → fam_wqh | → B2 考卷 |
|---|---|---|---|---|---|---|
| GCN | **0.794** | **39.2** | 3.099 | **0.212** | **0.651** | **1.935** |
| GAT | 0.827 | 46.1 | 3.462 | 0.284 | 0.796 | 2.064 |
| **Flow-MDK** | 1.422 | 52.1 | **2.629** | 0.632 | 0.929 | 2.260 |
| SWE-GNN | 4.496 | 103.1 | 3.697 | 0.581 | 1.102 | 3.474 |

**本地预算下的结论（单种子，待 L4 复测）**：

1. **MDK 混合对本体的拯救效应是最稳健的发现**：同一骨架下 Flow-MDK 1.42 m vs
   SWE-GNN 4.50 m（×3.2）。SWE-GNN 在 5 个评测域中的 4 个（合成域内、fam_mdx、
   fam_wqh、B2 考卷）一致最差；混合分支在这些域带来 ×2–3 的改善（唯一例外是最小
   流域 fam_zxh，各模型都 <0.7 m、混合门控略逊于本体，量级上无实际差异）。
2. **域内 GCN/GAT 仍占优**（0.79/0.83）——v1 的"扩散波体制体制错配"解释在该体制下
   不再成立，对称平滑在 1D 链式场景 + 本预算下就是很强的基线；早先 pre-patchfix
   轮"Flow-MDK 域内最优（1.79）"的判断是污染真值 + 少 40% 训练数据的联合假象
   （GCN 从 2.38 → 0.79 的跃升主要来自 +39 个训练场景）。
3. **synthetic→real gap**：fam_mdx（最难的闸门大流域考卷族）上 Flow-MDK 零样本最优
   （2.63），且其域内→零样本退化（1.42→2.63，×1.8）小于 GCN（0.79→3.10，×3.9）；
   GCN 域内精度最高但 gap 更陡。B2 考卷 GCN 仍最优。
4. 正式的体制归属结论（缓变/瞬变分工）需要论文级预算（L4）——Flow-MDK 的混合
   门控在该预算下大概率仍未收敛（B1 域内已观察到同样的欠拟合模式）。

## L3 · B1 训练 → B2 考卷三方消融（真实 Mascaret 数据）

B1 = 三真实母版家族合并（`data/real_cases/family_all/`，81/17/19 split）；
B2 = 5 个真实历史考卷。水深 RMSE（m）：

| 模型 | B1 域内 h | mdx | mdx_upstream | mdx_downstream | wqh | zxh | B2 均值 |
|---|---|---|---|---|---|---|---|
| SWE-GNN（-MDK） | 0.830 | 5.13 | 1.84 | **1.01** | 0.29 | 0.07 | **1.669** |
| SSGC（对称 MDK） | 0.798 | 3.95 | 1.19 | 3.56 | 0.38 | 0.06 | 1.826 |
| Flow-MDK（混合） | 1.954 | 4.88 | **1.25** | 3.56 | 1.65 | 0.90 | 2.448 |

**初步解读（需论文预算复测确认）**：
- 本地预算下三方同量级，未见清晰的定向性收益排序；Flow-MDK 域内（B1）明显欠拟合
  （1.95 vs 0.8），疑似 40 epochs 对混合门控参数不够。
- mdx / mdx_upstream（闸门调度 + 耦合链考卷）上 Flow-MDK/SSGC 占优，简单考卷
  （zxh/wqh）上 SWE-GNN 占优——体制分工初现端倪。
- 全部考卷 CSI≈1.0（1D 链式场景湿区判别几乎无难度，区分度在水量精度上）。
- B2 加速比：全部 5 考卷已有时效（19–206×，round 4 刷新后全 eval 范围
  10–510×；mdx/mdx_downstream 初期缺格已于 L9 补齐，4 例现用本地保守
  口径，见 L9）。

## L4 · 论文预算复测（服务器 A100，2026-09-13 跑、09-14 取回）

> `hidden_dim=64, max_epochs=150, batch=8, lr=0.007`，单种子 seed=0，评 `last.pt`
> （SWE-GNN 预算协议）。架构：swegnn = 忠实 SWE-GNN（2 层×8 跳，MDK 关），
> flow_mdk / ssgc / gcn / gat = 6 层×1 跳（前者 MDK 定向开 / 关）。完整机器表
> （含 KS 检验）见 [`L4_report.md`](L4_report.md)；run 归档 `runs/partA_paper_20260913_*`、
> `runs/L3_B1_paper_20260913_*`。

### Part A（合成 1D 链，训练 → A-test/A2/A3 + 零样本 B）

水深 RMSE（m）：

| 模型 | A-test | A2 | A3 | →fam_mdx | →fam_zxh | →fam_wqh | →B2 均值 |
|---|---|---|---|---|---|---|---|
| swegnn（2L×8 跳） | **0.722** | **0.682** | **0.774** | 3.018 | **0.285** | **0.603** | 2.456 |
| flow_mdk（6L+MDK） | 1.417 | 1.264 | 1.326 | **2.280** | 0.684 | 0.827 | **2.424** |
| gat（6L） | 1.918 | 1.600 | 2.295 | 8.584 | 1.285 | 2.838 | 4.475 |
| gcn（6L） | 35.38 † | 35.44 † | 35.25 † | 127.3 † | 24.7 † | 50.6 † | 65.7 † |

† 6 层 GCN 按 last.pt 协议塌缩为常数型输出（逐场景 RMSE 31.7–36.2 m、跨域
24.7–127 m，best_epoch=14/113）——**但 best.pt 对照（下节）显示其 epoch-14 状态
0.740 m 与最优模型持平：塌缩是训练漂移所致，而非 6 层 GCN 架构无能**。

### B1（真实家族合并）→ B2 考卷

| 模型 | B1 域内 h | mdx | mdx_upstream | mdx_downstream | wqh | zxh | B2 均值 |
|---|---|---|---|---|---|---|---|
| flow_mdk | 0.875 | **3.64** | **1.33** | 2.69 | 0.30 | 0.14 | **1.621** |
| ssgc | **0.852** | 5.11 | 1.78 | **1.13** | **0.29** | **0.12** | 1.684 |
| swegnn | 2.150 | 5.33 | 1.60 | 3.41 | 1.66 | 0.92 | 2.583 |

### 判读（对照 L4 升级判据与 L2/L3 本地结论）

1. **漂移是主导现象，且与架构无关**：7 个 paper run 全部 best epoch 极早
   （4–14）+ val 漂移 2–4×。last.pt 协议下基线受损最重（GCN 35.4、GAT 1.92），
   但其 best.pt 状态均达 0.74 水平（见下节）——"深传播需要门控"的叙事在
   best.pt 对照下**不成立**，当前证据只支持"当前训练配方会让所有模型漂移，
   无门控模型漂移后果更重"。
2. **val-best 选点不可靠**：partA 的 swegnn/flow_mdk 与 B1 的 ssgc 的 val-best
   落在课程学习期内（欠训练，best.pt 反而更差）；partA 的 GCN/GAT 与 B1 的
   flow_mdk/swegnn 的 val-best 则显著更好。两协议各有赢家 → 漂移治理（E2）
   是当前第一优先级，checkpoint 协议之争是它的下游问题。
3. **合成 1D 域内：浅层 8 跳 SWE-GNN（last.pt 0.72）仍是正式对比中最优**；
   flow_mdk last.pt 1.42 但 best.pt CSI@0.05 0.984（last.pt 0.400 是漂移伪影）。
4. **真实家族域（B1，论文核心域）：深层门控系占优**（last.pt：ssgc 0.852 ≈
   flow_mdk 0.875 << swegnn 2.150，KS p≈7e-4）；best.pt 下 flow_mdk 0.782 为
   全场最优，但 ssgc best.pt 3.65（ep4 欠训练）——排序对协议敏感，3 种子+
   统一配方后才可下最终结论。**（E3 三种子后记：此条未复现，见 E3 节——
   swegnn s1/s2 在 B1 域内同样落到 0.79/0.80。）**
5. **定向（flow_mdk）vs 对称（ssgc）仍无显著差异**：last.pt B1 p=0.81、B2
   p=1.0，逐考卷 2:2 分胜负。**"水力定向 MDK 优于对称核"的核心假设至今
   （本地 3 种子 + 论文单种子）无统计支持。**
6. 其余信号保留：fam_mdx（最难闸门族）零样本 flow_mdk 最优（2.28 vs 3.02，
   与 L2 单种子方向一致但本地多种子未复现，权重存疑）；λ₀ 末层持续收缩
   （0.4→0.05，曲线 `runs/lambda0_curves_paper.png`）；Dirichlet 富评仍待做
   （服务器 eval json 无 dirichlet 字段，checkpoint 已取回）。

### E1 · best.pt 对照复评（2026-09-14 当日补做，本机 3060）

`evaluate.py --checkpoint best.pt`（ptbest_* 孪生目录，不覆盖 last.pt 报告）：

| run | last h | best h | last CSI@.05 | best CSI@.05 |
|---|---|---|---|---|
| partA swegnn | **0.722** | 3.275 | 0.978 | 0.984 |
| partA flow_mdk | 1.417 | 2.865 | 0.400 | **0.984** |
| partA gcn | 35.378 | **0.740** | 0.984 | 0.946 |
| partA gat | 1.918 | **0.748** | 0.158 | 0.891 |
| B1 swegnn | 2.150 | 1.144 | 1.000 | 0.947 |
| B1 flow_mdk | 0.875 | **0.782** | 1.000 | 1.000 |
| B1 ssgc | **0.852** | 3.651 | 1.000 | 1.000 |

**判读**：① last.pt 下 GCN 的"塌缩"与 flow_mdk 的"CSI 缺陷"均为漂移伪影；
② val-best 选点一半情形落在课程学习期（欠训练），不可作为协议替代；③ B1 上
flow_mdk best.pt 0.782 为全场最优——门控系在真实家族域的优势跨协议成立；
④ **结论：当前配方（lr=0.007, decay 0.9/7ep）的训练漂移是压在所有模型上的
第一问题，E2 防漂移探针升级为关键路径**；漂移治理后各模型在 partA 大概率
收敛到 0.7–0.8 区间（反超存疑、追平大概率），区分度仍看稳定性/真实域/2D。

零样本域与 B2 考卷的 best.pt 补充对照（同日补齐，h-RMSE m）：

| run | fam_mdx last | fam_mdx best | B2 均值 last | B2 均值 best |
|---|---|---|---|---|
| partA swegnn | 3.018 | 4.63 | — | — |
| partA flow_mdk | **2.280** | 6.50 | — | — |
| partA gcn | 127.3 | **2.835** | — | — |
| partA gat | 8.584 | 2.987 | — | — |
| B1 swegnn | — | — | 2.583 | 1.792 |
| B1 flow_mdk | — | — | **1.621** | 1.788 |
| B1 ssgc | — | — | 1.684 | 2.847 |

→ fam_mdx 的"Flow-MDK 零样本最优"同样**只在 last.pt 下成立**（best.pt 下
GCN 2.84 反超，flow_mdk 6.50——其 val-best 在课程期、零样本欠训练）；B2 均值
在两协议下 flow_mdk/ssgc 互有胜负。**至此所有"模型排序"类信号都被证明对
checkpoint 协议敏感，唯一跨协议稳固的是 B1 真实家族域上门控系（flow_mdk/
ssgc）优于浅层 swegnn——漂移治理（E2）是恢复可信排序的前提。**

**E3 三种子后记（2026-09-15）**：上一句"唯一跨协议稳固"的判断也被三种子
复测部分推翻——B1 域内 swegnn 的 s1/s2 与门控系同档（见 E3 节）；E3 之后
仍然稳固的只有两条：**①所有 1D 排序信号对种子同样敏感（方差 > 模型间距）；
②B1 域内 flow_mdk 是唯一在两种协议下都稳定在 0.8 档的模型**（last 1.39±0.99 /
best 0.826±0.105，后者为三模型中方差最小）。

## E2 · 防漂移探针（2026-09-14 服务器，`run_L4_probes.sh`）

三个探针均为 flow_mdk 论文配置（6L+MDK，seed 0）的单变量变体，A-test 评
last.pt 与 best.pt（baseline = partA_paper_flow_mdk s0）：

| 探针 | 变更 | last h | best h | 判读 |
|---|---|---|---|---|
| baseline | — | 1.417 | 2.865 | 6 层+MDK 参照 |
| `L4probe_lr` | lr 减半 0.0035、decay 0.85@5ep | 8.499 | 17.014 | 慢退火在 150ep 固定预算内欠训练，全面恶化 |
| `L4probe_L3` | 3 层（深度减半） | **0.778** | 1.231 | **与浅层 8 跳骨架（s0 0.722）同档** |
| `L4probe_es` | 早停 patience=20 | 2.669 | 1.931 | ep32 于课程期 H=3 触发即停——早停与课程学习冲突，不可用 |

**判读**：①漂移的现实治理杠杆是**降深度**，不是动优化器——3 层 flow_mdk
直接进入 0.78 档，而 lr/早停两个"训练配方"探针都恶化；"6 层深传播在合成 1D
无域内收益"的 L4 判读由此获得机制性支撑（深度是漂移的主载体）。②best.pt
排序与 last.pt 一致，protocol 之争不改变本节结论。③一个 6 层混合模型要吃到
深传播收益，需要的是防漂移的结构/训练手段（见 E4 的 2D 正面结果），不是更
保守的 lr。

## E3 · 论文预算三种子复测（2026-09-14 服务器，`run_L4_multiseed_paper.sh`）

14 个 run（Part A 四模型 × seed 1/2 + B1 三模型 × seed 1/2，s0 由 09-13 论文
run 副本并入；`runs/MS4_partA_*`、`runs/MS4_B1_*`）。逐种子 A-test / B1 域内
h-RMSE（last.pt / best.pt，m）：

**Part A（合成 1D，A-test）**

| 模型 | s0 | s1 | s2 | last mean±std | best mean±std |
|---|---|---|---|---|---|
| swegnn | 0.722 / 3.275 | 2.177 / 1.257 | 1.557 / 0.833 | 1.485±0.730 | 1.788±1.305 |
| gat | 1.918 / 0.748 | 0.750 / 0.924 | 0.735 / 0.927 | 1.134±0.679 | **0.866±0.102** |
| gcn | 35.378 / 0.740 | 0.738 / 0.794 | 1.034 / 0.796 | 12.383±19.915 | **0.777±0.032** |
| flow_mdk | 1.417 / 2.865 | 6.246 / 7.657 | 7.456 / 3.911 | 5.040±3.195 | 4.811±2.520 |

**B1（真实家族域内）→ B2（零样本）**

| 模型 | B1 s0 | B1 s1 | B1 s2 | B1 last mean±std | B1 best mean±std | B2 last mean±std |
|---|---|---|---|---|---|---|
| swegnn | 2.150 / 1.144 | 0.792 / 0.815 | 0.803 / 0.699 | 1.249±0.781 | 0.886±0.231 | 2.004±0.503 |
| flow_mdk | 0.875 / 0.782 | 2.528 / 0.750 | 0.772 / 0.945 | 1.392±0.986 | **0.826±0.105** | 2.084±0.482 |
| ssgc | 0.852 / 3.651 | 4.809 / 0.507 | 1.958 / 0.681 | 2.540±2.042 | 1.613±1.767 | 3.575±1.750 |

**判读（对照 09-14 L4 单种子判决）**：

1. **种子方差碾压模型间距，1D 排序问题在当前配方下无解**。last.pt 下 s0 的
   两个"戏剧性"结果——GCN 35.4 塌缩、flow_mdk 1.42——都不具代表性（gcn
   s1/s2 为 0.74/1.03，flow_mdk s1/s2 恶化到 6.25/7.46）。合并种子 KS 检验：
   A-test 上 flow_mdk 显著差于 gat/swegnn（p~1e-30），B1 上三模型两两无显著
   差异（p≥0.06）。
2. **B1"门控系全面占优"未复现**：swegnn 的 s1/s2 在真实家族域同样落到
   0.79/0.80（s0 的 2.15 是坏种子）。B1 域内跨协议仍稳的只剩一条：
   **flow_mdk 是唯一两种协议都稳定在 0.8 档的模型**（best.pt 0.826±0.105 为
   三模型方差最小）；ssgc 的 best.pt 均值被 s0 欠训练（ep4）拖垮。
3. **E1 的"反超/追平"预测部分修正**：gcn/gat 的 best.pt 跨种子稳定在
   0.74–0.93（±0.03/±0.10，全场最稳）——无门控基线并没有被漂移同等压制，
   它们的 val-best 选点（ep1–2）反而稳；**"治理后各模型收敛到 0.7–0.8"对
   基线成立、对 6 层混合模型不成立**（flow_mdk best.pt 4.81±2.52，其 val-best
   选点在三种子上系统性失败）。
4. val-best 选点不可靠的机制清单再加一条：gcn/gat 的 val-best 落在 ep1–2
   （课程期 H≤2）却给出全场最好的 best.pt——课程期欠训练 ≠ 8 步 rollout 差，
   E1 的"课程期=欠训练"归因对短 horizon 种子不成立；漂移与选点问题只能
   逐模型实证，无捷径。
5. B2 考卷（真实历史事件）三模型 last.pt 无显著差异（KS p≥0.68），均值
   swegnn 2.00 ≈ flow_mdk 2.08 < ssgc 3.58。

## E4 · 2D 论文预算训练（2026-09-14 服务器，`run_M3_2d_paper.sh`）

MS4_2d 组：swegnn（2L×8 跳）/ flow_mdk（6L+MDK）/ ssgc（6L 对称 MDK），
G=64、150ep、batch 8 × 4096 节点合成网格（`data/scenarios_2d_family`，E4 扩容
130 场景，test 20 场景），seed 0，训练 2.4–6.0 h/run。2D test h-RMSE（m）：

| 模型 | last.pt | best.pt | CSI@0.05（last/best） | 推理加速 |
|---|---|---|---|---|
| swegnn（2L×8 跳） | 1.818 | 1.044 | 0.459 / 0.312 | 216–808× |
| **flow_mdk（6L+MDK）** | **0.359** | **0.778** | **0.708** / 0.408 | 233–875× |
| ssgc（6L 对称） | **0.324** | 1.957 | **0.751** / 0.239 | 225–965× |

**判读**：

1. **首次出现 ×5 级模型分离，方向有利于门控系——2D 激波体制是深传播的
   正面战场**。预注册 last.pt 协议下 6 层门控模型（flow_mdk 0.359 / ssgc
   0.324）大幅优于浅层 8 跳骨架 swegnn（1.818）；best.pt 对照下 flow_mdk
   仍最优（0.778 vs 1.044），ssgc 反转（1.957）。**两种协议下 flow_mdk 均
   不劣于 swegnn**——这是 1D 上从未出现过的跨协议稳固优势。
2. **定向 vs 对称在 2D 内部仍无一致优势**：last.pt ssgc 0.324 ≈ flow_mdk
   0.359，best.pt 反转（0.778 vs 1.957）。与 1D 结论一致：**收益属于
   "MDK 门控混合使深传播稳定"，不属于"水力定向"本身**——课题主张维持
   09-14 定调（稳定深传播 + 基准 + 方法学，定向性为探索性对照）。
3. 机理信号干净：末层 Dirichlet 能量（逐边归一，L5 监控）swegnn 0.98 vs
   flow_mdk 0.011 / ssgc 0.0035——**两个数量级分离**；λ₀ 末层在 2D 保留
   0.03–0.21（1D 上收缩到 ~0.05）。浅层多跳骨架在 2D 激波体制下的表示能量
   远高于 MDK 滤波链。
4. 漂移现象跨维度存在（best epoch 10/15/11，val 漂移 2.3–2.7×），但 2D 的
   last.pt 受损者恰好是 swegnn（last 1.82 > best 1.04），flow_mdk 反而
   last < best——协议之争在 2D 不改变"门控系占优"的方向。
5. 局限：单种子、合成 4096 节点网格、未含真实 2D 工程（65k 节点）。E4 后续：
   2D 三种子（`run_M3_2d_paper.sh` 已支持 `_s<seed>` 命名与 EXTRA 钩子）+
   定向消融（directed on/off 已由 flow_mdk/ssgc 覆盖）+ 真实 2D 考卷接入。
   → 单种子局限已由 E5 收口（见下节），真实 2D 考卷仍待接入。

## E5 · 2D 三种子复测（2026-09-15 服务器开跑、09-16 取回落定，`run_M3_2d_paper.sh`）

`SEEDS=1 2` 补齐 MS4_2d 的 s1/s2（三模型 × 2 新鲜种子，配方与 E4 完全一致；
swegnn 4.5–5.1 h/run、门控系 2.3–2.6 h/run，整批 ~19 h）。2D test h-RMSE
（m；s0 列即 E4，± 为跨种子样本 std）：

| 模型 | last.pt（s0/s1/s2） | last mean±std | best.pt（s0/s1/s2） | best mean±std |
|---|---|---|---|---|
| swegnn（2L×8 跳） | 1.818 / 12.655 / 0.708 | 5.060±6.600 | 1.044 / 7.925 / 0.941 | 3.303±4.002 |
| **flow_mdk（6L+MDK）** | **0.359 / 0.849 / 0.379** | **0.529±0.277** | **0.778 / 0.452 / 0.373** | **0.534±0.214** |
| ssgc（6L 对称） | 0.324 / 3.460 / 1.676 | 1.820±1.573 | 1.957 / 0.525 / 1.382 | 1.288±0.721 |

KS 检验（逐场景 RMSE，合并三种子，全部显著）：last.pt 下 flow_mdk vs ssgc
D=0.633 p=1.3e-11、flow_mdk vs swegnn D=0.550 p=1.1e-08、ssgc vs swegnn
D=0.367 p=5.6e-04；best.pt 下 flow_mdk vs ssgc D=0.667 p=6.1e-13、
flow_mdk vs swegnn D=0.850 p=2.2e-22、ssgc vs swegnn D=0.383 p=2.6e-04。
CSI@0.05（last，三种子均值）flow_mdk 0.656 vs ssgc 0.437 vs swegnn 0.367。

**判读**：

1. **E4 的优势三种子钉死，且 flow_mdk 升级为「唯一跨协议/跨种子稳固的
   模型」**：两种协议下均值、中位数、KS 全部最优，last≈best（0.529 vs
   0.534）——数字对选点协议免疫；全部 6 个 flow_mdk run 落在 0.36–0.85 m
   （max/min = 2.4×），ssgc 跨度 10.7×、swegnn 17.9×。
2. **E4 单种子的「ssgc ≈ flow_mdk」不复现**：ssgc s1/s2 恶化到 3.46/1.68，
   best.pt 的反转也不再出现。定向 vs 对称的天平在多种子下明确偏向定向版
   （两种协议 KS 均显著），但仍非逐种子干净扫掠（s0 last ssgc 0.324 更优）——
   表述收口为「**定向门控 = 门控系中唯一跨种子/跨协议稳固的形态**」。课题主张
   不变（MDK 门控混合 = 稳定深传播机制），定向性从「探索性对照」升级为
   「2D 域内稳定性优势」。
3. **swegnn s1 是坏种子而非选点问题**：best.pt 同样差（7.92），val 平台
   0.0181（门控系 0.0155–0.0164）——浅层多跳骨架在 2D 的训练成功率本身
   不稳；E4 单种子 1.818 恰落在三种子分布中位。±6.6 的种子方差再次印证
   E6「单 run 数字不可信」在 2D 同样成立，只是 2D 的 last.pt 受损者恰好是
   无门控基线而非 flow_mdk。
4. 机理信号随种子保持：末层 Dirichlet 能量（逐边归一，三种子合并均值）
   swegnn 3.61 vs flow_mdk 0.013 / ssgc 0.062——约两个数量级分离不变
   （L4 报告 MS4_2d 节）。
5. 剩余局限收窄为一条：合成 4096 节点网格、无真实 2D 考卷（L12 剩余项，
   wqh_2d/mdx_2d 65k 节点需图分块/下采样）。

## MS5 · E1 收官尝试：浅层多跳骨架 + MDK 混合（2026-09-15）

E2/E3 之后唯一未测且有机制理由的 1D 配置：官方 SWE-GNN 骨架（2L×8 跳、tanh）
+ 定向 MDK 分支（`configs/1d_swegnn_mdk.yaml`，与骨架唯一差异是 mdk 块；脚本
`run_MS5_shallow_mdk.sh`）。3 个新鲜种子 × 论文预算，判读协议预注册：headline
= A-test last.pt mean±std 对照 MS4 表；**追平判据 = best.pt 进入 gcn
0.777±0.032 档**。A-test h-RMSE（m，last / best）：

| 种子 | last | best |
|---|---|---|
| s0 | 1.952 | 1.406 |
| s1 | 2.091 | 1.044 |
| s2 | 5.676 | 1.057 |
| **mean±std** | 3.239±2.111 | **1.169±0.206** |

对照（MS4/E3 参考表）：gcn 12.38±19.92 / **0.777±0.032**，gat 1.13±0.68 /
0.87±0.10，swegnn 1.49±0.73 / 1.79±1.31，flow_mdk(6L) 5.04±3.20 / 4.81±2.52；
E2 3L 探针 0.778 / 1.231（单种子）。

**判读（E1 至此正式关闭）**：

1. **追平判据未达成，"调参达到最佳"不可达**：best.pt 1.169±0.206 位于
   GCN/GAT 基线档（0.78–0.87）与骨架 best.pt 均值（1.79）之间，差基线约
   1.5×。测试过的全部方向——lr 减半、早停、降深度（3L/浅层骨架混合）——
   无一进入 0.8 档。1D 合成域内排位定论：**GCN/GAT（best.pt 0.78–0.87）>
   浅层+MDK（1.17）≈ 3L+MDK > 其余**；对称平滑基线在合成 1D 域内就是最强。
2. **浅层化是 MDK 系在 1D 的最优形态，且 MDK 分支在浅层骨架上是净收益**：
   best.pt 1.169±0.206 为全部 MDK 系配置中最优、跨种子最稳（6L flow_mdk
   4.811±2.520）——E2"深度=漂移主载体"再获一发确认；mean 与方差双双优于
   无 MDK 的同骨架 best.pt（1.788±1.305）。与 6 层时"MDK 无域内收益"并不
   矛盾：浅层下漂移不再是主导误差源，扩散分支的归纳偏置才得以兑现。
3. 排序对协议敏感的规律在 MS5 内部同样成立：last.pt 下骨架占优（1.49 vs
   3.24，被 s2 坏种子主导）、best.pt 下本臂占优——再次确认两协议各有赢家。
   s2 还暴露**漂移在零样本域被数量级放大**（域内 5.68 → fam_mdx 350、B2
   124，退化 ×123）：last.pt 评测的零样本数字对坏种子极其脆弱。
4. MDK 系的价值域就此完全划清：**合成 1D 域内不占优（本文给出最优配置后
   仍差基线 1.5×）；真实家族域 B1 双协议 0.8 档（E3）；2D 激波体制 ×5 且跨
   协议稳固（E4）**——与"MDK 门控混合 = 稳定深传播机制、主战场在真实域/2D"
   的课题主张自洽。

## E6 · 选点治理探针（2026-09-15，本机 3060，`run_E6_val_governance.sh`）

**根因定位**：`val_loss` 按当前课程视野计算（`trainer.py`），跨 epoch 不可
比；`HorizonScheduler` 每个视野停 curriculum_steps 个 epoch（论文预算下
H=8 于 epoch 106 才达到）——**L4/MS4/MS5 全部 best.pt 均为 H=1 状态**，
biased val-best 的失效是结构性的。三项训练侧治理已实施（默认关闭）：
`train.val_horizon`（固定视野验证）、`train.early_stop_after_curriculum`
（早停门）、`train.ema_decay`（逐步权重 EMA，存 ema.pt）。

探针：flow_mdk 6L、本地预算（G=32/40ep/课程 4）× 4 臂 × 3 种子 = 12 run；
A-test h-RMSE（last / best / ema，m）：

| 臂 | s0 | s1 | s2 |
|---|---|---|---|
| base（无旗标对照） | 1.316 / 2.414 / — | 1.207 / 5.910 / — | 3.138 / 3.206 / — |
| valfix（val_horizon=8） | 3.632 / **1.681** / — | 11.695 / **7.891** / — | **1.785** / 2.721 / — |
| ema（ema_decay=0.995） | **0.934** / 1.675 / 1.636 | **1.044** / 1.226 / 1.459 | **1.514** / 2.710 / 2.166 |
| full（组合配方） | 10.647 / **3.006** / 4.336 | 2.349 / **1.266** / 1.663 | **1.553** / 1.734 / 1.866 |

协议池统计：last **3.40±3.73**（[0.93, 11.70]，n=12）· best 2.95±2.00（n=12）·
ema **2.19±1.08**（[1.46, 4.34]，n=6）。

**判读**：

1. **biased val-best 正式判死**：同轨迹内 0/6 赢 last（base + ema 臂），
   val-best 无一例外落在 ep3–4（H=1）——本地预算完整复现论文预算的 E1/MS5
   机制。官方 SWE-GNN 配方的"150 epochs + val 选点"在该训练动态下不可用。
2. **val_horizon 修复选点语义但只是部分解药**：val@H8 best 同轨迹 4/6 赢
   last，选点从 ep3（H=1）搬到 ep13–37 的真实全视野状态；但救不动 6 层
   架构本身的漂移（valfix s1 的 7.89）。
3. **EMA 是方差压缩器而非均值冠军**：同轨迹 2/6 赢 last（last 偶有 0.93 的
   好签），但跨 run 最稳（±1.08 vs last ±3.73，把 12.5× 彩票区间压到
   [1.46, 4.34]）。EMA-from-init 被课程期权重污染——已实施
   `ema_after_curriculum`（课程达到 H_max 才开始平均）待下一轮 run 验证。
4. **混沌发现（方法学核心）**：同种子各臂在 epoch 1 训练损失即分叉
   （14.430 vs 14.458 vs 14.478，CUDA 非确定性算子）× 漂移放大 ⇒ last.pt
   是 [0.93, 11.70] 的彩票。**漂移体制下任何单 run 数字都不可信，协议对照
   （last/best/ema）与多种子是必要条件**——这直接写进论文的方法学主张。

**E6 配方（后续 run 默认）**：`val_horizon=horizon_max` +
`ema_after_curriculum=true`（decay ~0.995–0.999，按每 epoch 步数量级调）+
`early_stop_after_curriculum=true`；best.pt 对照保留、ema.pt 作为第三协议
一并评测。**生效范围：E7 起的全部新 run；E5 全批维持旧配方**——多种子
折叠要求同种子同配方，E5 的 s1/s2 必须与 s0（旧配方）可比。

## L12 · 真实 2D 考卷：E4/E5 模型零样本迁移（2026-09-16，本机 3060，`run_L12_real2d_exam.sh`）

真实 TELEMAC-2D 工程 wqh_2d（65,589 节点 / 25 h）与 mdx_2d（65,126 节点 /
15 h）作为考卷，E4/E5 训练的 9 个 2D run（3 模型 × 3 种子）直接零样本评测，
不重训。考卷构建（`scripts/build_real_2d_exam.py`）：帧距降采样到训练
Δt=1800 s（600 s 真值每 3 帧取 1；wqh 151→51、mdx 91→31 帧）；静态特征
对齐到合成 6 列布局——[面积, 床面高程（移局部基准）, 坡度×2（对偶图逐节点
最小二乘）, Manning n, 入流边界 breach 标记（.cli 解析，wqh 20 / mdx 24
节点）]；真值本身不动。登记的未调整域差距：|q| 真实 ~1–8 m/s vs 合成
≤0.035 m/s（约 2 个数量级）、床面起伏 262 m vs 3.7 m、非结构三角形 vs
均匀 100 m 网格。**双协议评测**（E6 方法学纪律的零样本版）：H=8（训练
视野，4 h rollout）与全时程（24 h rollout）。

h-RMSE（m，3 种子 mean±std；每格 = mdx_2d / wqh_2d）：

| 模型 | H=8 best.pt | H=8 last.pt | 全时程 best.pt | 全时程 last.pt |
|---|---|---|---|---|
| swegnn（2L×8 跳） | 2.36±0.16 / 2.93±0.49 | 2.94±1.08 / 3.48±0.87 | 5.52±3.76 / 9.16±7.69 | 13.14±8.71 / 22.72±15.24 |
| **flow_mdk（6L+MDK）** | **2.05±0.06 / 2.90±0.21** | 2.51±0.58 / 3.50±0.42 | 8.87±1.32 / 24.30±5.21 | 10.80±6.42 / 25.87±9.34 |
| ssgc（6L 对称） | 2.06±0.31 / 3.33±0.65 | 2.84±1.07 / 3.52±0.96 | 6.78±1.02 / 15.36±1.71 | 10.88±4.18 / 24.98±5.56 |

CSI@0.05（H=8 best）：flow_mdk 0.86/0.81 ≈ ssgc 0.86/0.81 > swegnn
0.82/0.76；全时程全体跌至 0.46–0.64。

**判读**：

1. **训练视野内零样本迁移成立**：H=8 下全体模型 h-RMSE 2.0–3.5 m
   （h_max 17–19.6 m 的 12–19%）、CSI 0.69–0.88——合成域训练的模型在
   真实工程网格上直接可用（短时程）。相对合成域内（flow_mdk best 0.534）
   退化 ×4–5.5，远小于 1D 轨道的 fam_mdx 零样本（×1.8）但属可用量级。
2. **flow_mdk 再次是最稳的**：best.pt 双考卷最优（mdx 2.05±0.06 全场
   最小方差）且 last≈best 模式在零样本下保持；1D B1 域内「双协议稳定
   0.8 档」的格局在 2D 真实域以「best.pt 2–3 m 档 + 跨种子最稳」复现。
   域差距压制了模型间距（三模型同档），但稳定性排序不变。
3. **全时程外推（24 h）全体发散**：last.pt 10–39 m、best.pt 5–24 m，
   相对 H=8 恶化 ×4–10——自回归漂移在分布外域被放大（E6 结论的零样本
   版），且 |q| 输入差距使误差逐帧复合。**长时程零样本不可用；泛化矩阵
   的零样本格必须配训练视野对照，否则数字无意义。** 与 1D 侧 MS5 发现
   （坏种子零样本 ×123 放大）互为印证。
4. 补齐路径（未排期，供 M5 讨论）：2D 真实母版家族（真实几何 × 合成水情
   批跑 TELEMAC-2D，单场景小时级）做 B1 式域内微调；或特征空间对齐
   （|q| 对数域/标准化、地形归一）后再零样本。1D 侧先例：B1 家族
   微调把 flow_mdk 域内稳定在 0.8 档。

## L14 · 大 Δt 权衡实验（2026-09-16 服务器，`run_L14_big_dt.sh`，M2 收口）

层/k 与时间步的权衡（SWE-GNN Fig.8 同构）：帧距 ×2/×3（`subsample_scenarios_dt.py`
从 partA_v2 派生，×4 弃用——96/130 场景帧数不足），flow_mdk 6L×1hop 的 MDK
截断 K 按 √m 物理匹配（K0=2 → 3/4）vs swegnn 2L×8（感受野固定），3 种子，
A-test last/best 双协议。对照 = E3 的 dt×1 同种子 run。已知混杂：dt 每升
一档训练窗口数减半（p50 11→4），Δt 大档在更少数据上训练。

A-test h-RMSE（m，3 种子 mean±std）：

| 档位 | flow_mdk last | flow_mdk best | swegnn last | swegnn best |
|---|---|---|---|---|
| dt×1（K=2 / 8 跳） | 5.040±3.195 | 4.811±2.520 | 1.485±0.730 | 1.788±1.305 |
| dt×2（K=3） | **2.678±2.104** | **2.356±0.179** | **1.342±0.476** | 1.395±0.721 |
| dt×3（K=4） | 4.026±2.084 | 2.378±1.441 | 2.284±1.321 | **0.910±0.053** |

**判读**：

1. **1D 域内排位对 Δt 稳健**：swegnn 三档全优（best 0.91–1.79），MDK 系在
   1D 域内不占优的结论对 Δt 稳健——「层/k–Δt 权衡」的交叉点在 1D 未出现。
2. **但 flow_mdk 的相对差距随 Δt 收窄**：last.pt 比值 3.4×→2.0×→1.8×；
   且 flow_mdk dt×2 best（2.36±0.18，全场方差最小）显著优于自身 dt×1
   （4.81±2.52）——H=8 物理视野翻倍的更难任务上反而更好，物理匹配 K
   生效；K=4 无失稳（√m 缩放的深传播本身稳定）。
3. swegnn dt×3 best 0.910±0.053 为全场最稳单元格；固定感受野骨架对时间
   分辨率粗化不敏感。
4. **M2 大 Δt 实验收口**：深传播的正面战场在 2D 激波体制（E4/E5），1D
   合成域内不复现——MDK 价值域结论（真实域 + 2D）第三次独立确认。

**E6.1 状态更正**：round 1 的 E61 三 run 因编排脚本漏传 `data.root` 而训练在
旧 v1 数据集（scenarios_1d）上，与 E3 控制（partA_v2）不可比，预注册判决
无效——runs 留档为 scenarios_1d 变体（last 15.2/170.8/10.9，best
4.3/19.4/8.2，ema≈last：EMA-after-curriculum 在漂移持续时跟随漂移，未起
压缩器作用）。修复后以 E61b 臂名重跑（partA_v2 + 全配方），判决见 E6.1 节。

## L16 · -MDK 深度匹配消融（2026-09-16 服务器，`run_L16_ablation.sh`，M5 基线表收口）

E3/E5 主表把 flow_mdk（6L×1hop+MDK）与 swegnn（2L×8 跳）对比，深度与 hops
混杂。本轮跑**深度匹配 -MDK 臂**：同一 6L×1hop 分裂层 harness、`mdk.use=false`
（与 flow_mdk 唯一差异 = MDK 旗标），1D/2D × 3 种子；成对控制 = E3
`MS4_partA_flow_mdk_s*` / E5 `MS4_2d_flow_mdk_s*` 同种子同预算。

h-RMSE（m，3 种子 mean±std；2D test / A-test）：

| 对比 | flow_mdk（控制） | **L16 -MDK（6L×1hop）** | ssgc（6L 对称） | swegnn（2L×8） |
|---|---|---|---|---|
| **2D last** | **0.529±0.277** | 0.835±0.641 | 1.820±1.573 | 5.060±6.600 |
| **2D best** | **0.534±0.214** | 0.622±0.343 | 1.288±0.721 | 3.303±4.002 |
| 1D last | 5.040±3.195 | 17.183±22.847 | — | 1.485±0.730 |
| 1D best | 4.811±2.520 | 4.277±4.115 | — | 1.788±1.305 |

KS（逐场景合并三种子）全部显著：2D flow_mdk vs -MDK p=4.6e-03 / -MDK vs
ssgc p=3.5e-07 / flow_mdk vs ssgc p=1.3e-11；1D flow_mdk vs -MDK p=4.2e-12。

**判读**：

1. **2D ×5 优势须重新归因：主载体是深度匹配的深传播 harness，MDK 分支
   提供显著但次级的增益**。深度匹配 -MDK 臂独自拿到对 swegnn 的大部分
   优势（last ×6.1、best ×5.3），MDK 分支在其上再加 last ×1.6 / best
   ×1.2（均 KS 显著、双协议同向）——「MDK 分支单独承载 ×5」的朴素读法
   不成立，论文表述收口为「**残差式深传播 harness ×6 + 定向 MDK 扩散
   分支 ×1.2–1.6（稳定器：方差 0.641→0.277）**」。
2. **匹配深度下的三分排序：定向 MDK（0.529）< 无扩散分支（0.835）<
   对称扩散 ssgc（1.820），全部 KS 显著**——对称扩散在 2D 深度 6 是净
   伤害（over-smoothing），定向门控是唯一在深传播上有正增益的扩散形态；
   「定向 vs 对称」从 E5 的「偏向定向版」收紧为「定向是唯一可用形态」。
3. **1D 域内 -MDK 同样崩**（17.2±22.8，s0 43.29 单种子发散）且不优于
   flow_mdk 控制——1D 排位结论（浅层最优）不因去掉 MDK 而改变，1D 的
   flow_mdk 劣势不能归咎 MDK 分支（去掉它并不更好），体制问题在骨架
   与任务本身；1D last.pt 的方差（±22.8）再次演示单种子结论不可信。
4. **M5 基线表收口**：主表 5 模型 × 3 种子 + 深度匹配消融臂齐备；剩余
   可选项（U-Net、-分裂臂）维持不做。-MDK 臂 2D Dirichlet 能量 = 0.0
   （无扩散分支，监控自洽）。

## E6.1 · E6 配方服务器验证（2026-09-16 服务器，`run_E61_recipe_validation.sh`，E61b 轮）

E6 配方（val_horizon=8 固定语义 + 课程后早停 patience=10 + EMA-after-
curriculum 0.999）在本地 3060 探针（G=32/40ep）上导出，本轮在**论文预算**
（G=64/150ep）× flow_mdk 6L（漂移主载体）× E3 同种子上验证；三检查点协议
（last/best/ema）齐评。round 1（E61）因 data.root 漏传作废（见 L14 节末），
E61b 为修正轮。

A-test h-RMSE（m，3 种子 mean±std）：

| 协议 | E61b（E6 配方） | E3 控制（旧配方） |
|---|---|---|
| last.pt | 3.758±2.544 | 5.040±3.195 |
| best.pt | **1.751±1.417** | 4.811±2.520 |
| ema.pt | 1.936±0.909（方差最小） | （无此协议） |

KS（逐场景合并三种子）全部显著：E61b vs 控制 p=2.4e-11（更优方向）、
E61b vs L16 -MDK p=3.3e-06。

**判读**：

1. **配方在论文预算下成立**：best.pt 4.811→1.751（×2.7）、last.pt
   5.040→3.758，KS 显著——E6 本地探针的三项训练侧改动在真实预算复现；
   ema.pt 以最小方差（±0.91）成为最稳协议，本地结论「EMA = 方差压缩器」
   成立（round 1 的「ema 跟随漂移」是 scenarios_1d 域的假象）。
2. **漂移本体未被治理，治理的是选点**：val@H8 自 best（ep 17–45）到早停
   （ep 115）恶化 ×1.1–1.9（25.6–29.5 → 32.2–48.6；旧配方的「2–4× 漂移」
   是 ramping-horizon 语义，不可直接比），test 侧 last 仍差 best ×2.1——
   配方让 best/ema 可靠，未阻止缓慢漂移；「漂移根因」仍开放（E2 已锁定
   深度载体，机制解释未完成）。
3. **best epoch（17/23/45）全部落在课程期内**——val_horizon=8 语义下
   val-best 落课程期的 E6 已知病理在论文预算复现：best.pt 是「课程期
   欠训练但漂移未起」的窗口，ema.pt（课程后启动）语义更干净。
4. **决策开放**：论文主 run 是否整体切换 E6 配方（换取 best/ema 可靠 +
   最小方差协议）vs 维持旧配方可比性——主表数字量级不变（排序不变），
   倾向主表维持 E3/E5 旧配方 + 方法学节单列 E6.1 作为选点治理证据；
   见 PLAN 待办。

## M4 · 耦合链可行性训练（2026-09-16/17 服务器，`run_M4_coupled_v1.sh`，单场景能力验证轮，3 种子）

`mdx_chain_v1.npz`（65,189 节点 / 389,928 边 / 31 帧 @1800s，单向 Q 耦合
真值，见 `couple_mdx_chain.py`）上端到端训练：split 有意全指到单场景
（能力验证而非泛化主张），flow_mdk 6L×1hop G=64 batch 4、60 epochs、E6
配方、K=2（1D 论文值，物理匹配留 v2）。round 1（s0）服务器评测因
evaluate.py 布局探测 bug 全挂（已修，本机补评）；round 3（09-17）补
s1/s2，服务器评测直接成功（修复已同步）。

**训练**：三种子全部成功（~18–29 s/epoch，65k 节点耦合图 batch 4 无
OOM、内核零改动）——**管线能力验证通过且跨种子稳固**。

**评测**（h-RMSE m / Q-RMSE m³/s，3 种子）：

| 协议 | h-RMSE（s0/s1/s2） | mean±std | Q-RMSE（s0/s1/s2） |
|---|---|---|---|
| best.pt | 1.110 / 1.137 / 1.428 | **1.225±0.176** | 49.9 / 36.8 / 39.5 |
| last.pt | 1.735 / 1.770 / 1.427 | 1.644±0.189 | 213.3 / 32.5 / 38.1 |
| ema.pt | 2.794 / 1.095 / 1.844 | 1.911±0.852 | 43.9 / **31.8** / 43.3 |

**判读**：

1. **可行性 ✅ 且三种子稳固**：best.pt 1.225±0.176（跨度 1.29×，与 E5
   flow_mdk 2D 的稳固度同档）——1D-2D 耦合单图（异构 1D 链 + 65k 节点
   2D 网格 + 接口边）可训、可评、跨种子可复现，M4 最大的工程不确定性
   消除；量级对照链内 2D 段 h_max 11.6–19.4 m 可用但粗糙。
2. **漂移种子依赖**：s0 漂移（val 43→238，last 差 best ×1.56/×4.3），
   s1/s2 平稳（best ep 53/31，val 末端≈best）——单场景过拟合设定下
   漂移可发生非必发生，与 E6.1「漂移是训练动力学」一致且给了它种子
   维度的细化；ema 在 h 上 s0 发散（0.999 decay 对 60ep 短预算过大），
   Q 上三种子最稳（31.8–43.9）——短预算臂应配 0.99 档。
3. 正式轮待办不变：接口边通量守恒损失项、闸门调度、K=√(2DΔt)/dx̄
   物理匹配、多场景耦合家族（M4 v2）。

### M4 v2 · 耦合家族批跑（2026-09-17/18 服务器，`build_coupled_family.py --num 12 --seed 11`，✅ 12/12）

参数化耦合家族生成器落地后的首轮服务器批跑：每场景扰动入链流量律
（q_scale ∈ 0.61–1.97 × t_stretch ∈ 0.82–1.54，B1 家族同款协议；
fam000 = 基线对拍 draw）→ 2D 重跑 → 下游重建 → 组装链 npz（v1 同款
规则，扰动参数入 meta）。

- **12/12 全部成功**（`mdx_chain_fam000–011.npz`，每场景 ~17.5 min、
  65,189 节点 / 31 帧；fam000 等价性在 round-4 prep 已逐字节证明）；
  逐场景 report → `data/real_cases/coupled_chain/coupled_family_report.json`
  （服务器端工件，下次取回）。
- 物理量级合理：链 2D 真值 h_max 11.14–12.62 m（fam011 最强工况
  q_scale 1.97），出口 Q 356–2203 m³/s 覆盖 v1 范围——家族多样性
  达设计意图。
- **M4 v2 正式训练的数据就绪**：训练腿（flow_mdk × 3 种子 + 接口守恒
  损失 + K 物理匹配）为 round 5 服务器主任务。

### M4 v2 · 正式轮准备（2026-09-18 本地实现，round 5 执行）

- **接口通量守恒损失项**（`train.interface_cons_weight`，main 臂 0.1）：
  候选恒等式逐一验证后取**界面通量形式**——储量恒等式在 1800s 子采样
  帧不闭合（Z=280 出流边界符号通量未保留，残差~通量量级）；
  `Q_chain_exit = Σ_v |q|_v·ℓ_v` 成立（入口段总长真值反推 ~336 m，跨步
  CV 14%），且损失为**预测侧自洽约束**（真值只标定 ℓ 不进损失）。
  `extract_interfaces` 湿步中位数自动标定、无信号界面（出流侧 |q|≈0）
  自动跳过；**仅训练侧启用**，val 纯数据损失保跨臂可比。
- **K=4**：ceil(2·√(1800/647)) ≈ 3.3 → 4，与 L14 的 dt×3→K4 同款
  √m 映射（混合 1D/2D 边缘分辨率下 dx̄ 修正不唯一，记档为限定）。
- **家族数据根**：`prepare_coupled_family_root.py` 平铺 + split 9/1/2
  （test = fam000 v1 对拍 + fam011 最强工况；val = fam010）；v1 根不动。
- **`run_M4_v2_family.sh` 三臂 × 3 种子**：main（K=4 + cons 0.1）/
  nocons（K=4，守恒消融）/ swegnn（official 2L×8 对照）；E6 配方 +
  ema 0.99（v1 短预算修正）。预算 ~2.5 h/run A100。

## B1v2 · 家族 v2 重训（2026-09-17 服务器，`run_B1v2_family.sh`，L6 敏感性检查）

L6 把 mdx 家族补齐到 50、family_all 重建为 **130 场景**（89/20/21，对齐
SWE-GNN 协议）后，E3 的 B1 主表（117 场景代，`MS4_B1_*`）是否仍然成立？
本轮以同预算（G=64/150ep/curriculum 15/last.pt 协议）重训三模型 × 3
种子（新臂名 `B1v2_*`，旧代原样保留）：

B1 域内 h-RMSE（m，3 种子 mean±std；括号 = E3 117 场景代数字）：

| 模型 | B1v2 last | B1v2 best | →B2 last |
|---|---|---|---|
| swegnn | 2.154±1.102（1.249±0.781） | 1.063±0.084（0.886±0.231） | 2.562±0.690（1.715±0.064*） |
| flow_mdk | 2.051±1.834（1.392±0.986） | 1.507±1.099（0.826±0.105） | 2.674±1.407（2.315±0.381） |
| ssgc | 1.844±1.585（3.383±2.016*） | 1.075±0.247（0.594±0.124*） | 5.806±7.007（4.520±0.872*） |

*E3 代 ssgc 与 swegnn 的 →B2 数字为 s1/s2 两种子（s0 行在 L3 原名下，
见 `docs/results_partA_swe.md` E3 节）。

**判读**：

1. **排序不变，量级整体偏高一档、方差更大**：v2 代的 best.pt 排序
   swegnn（1.06）≈ ssgc（1.08）< flow_mdk（1.51），与 E3「best.pt 下
   gcn/gat 稳、门控系 B1 域内 flow_mdk 双协议 0.8 档」相比，flow_mdk 的
   B1 优势未复现（s1 best 2.77 劣于 last 0.88 的反转种子）；B1 域本就是
   漂移最重的域（E3），+10% 场景把这点放大了。
2. **结论按「敏感性检查」记档而非新主表**：B1 主表维持 E3（117 场景代）
   ——v2 未带来改善，重训的目的是协议对齐论证而非刷新数字；论文表述 =
   「家族扩至 130 场景（对齐 SWE-GNN 协议）后重训，域内排位与结论不变，
   B1 域漂移敏感性随数据量略增」——这本身是诚实评测方法学的一节素材。
3. B1v2 代不进泛化矩阵主行（避免同域两代混淆），数字以本节与
   `docs/L4_report.md` B1v2 分组为准。

## U-Net · 2D 网格 CNN 基线（2026-09-17 服务器，`run_unet_2d.sh`，M5 基线表收口）

SWE-GNN 原文对比集的最后一个缺口：`baseline_unet`（通道缩放 U-Net，
base=32 ≈ 0.47M 参数，64×64 网格两级池化 + 跳连，共享自回归残差
harness，E5 同预算）三种子：

2D test h-RMSE（m，3 种子）：

| 协议 | U-Net | （对照）flow_mdk | （对照）swegnn |
|---|---|---|---|
| last.pt | **4.654±2.179** | 0.529±0.277 | 5.060±6.600 |
| best.pt | 10.512±11.780 | 0.534±0.214 | 3.303±4.002 |

**判读**：

1. **域内 U-Net 落 swegnn 一档**（last 4.65 vs 5.06），门控深传播对
   CNN 基线的优势（×8.8）与对浅层 GNN 的 ×5/×9.6 并立——M5 基线表
   五模型收口（GCN/GAT/swegnn/ssgc/U-Net + 消融臂）。
2. **best.pt 不可靠（10.5±11.8，s1 反转 24.0）**：U-Net 未配 E6 配方，
   漂移/选点病理在 CNN 上同样出现——与 E6.1「选点治理跨架构必要」一致。
3. **真实考卷零样本 = 架构性不可迁移（不测即结论）**：wqh_2d/mdx_2d
   为 65,126 节点非结构三角网格，U-Net 绑定 64×64 训练网格（模型侧
   保护检查拒绝非网格节点数）——网格 CNN 被锁死在训练网格上，GNN 天然
   持有图结构（L12 已证 65k 非网格零样本 H=8 视野 2.0–3.5 m）。泛化
   矩阵真实考卷格留空并注明；SWE-GNN 原文的 U-Net 对比同样仅域内，
   口径一致。这是 GNN 对 CNN 的结构性优势，论文直接引用。

## L9 · 加速比基线（2026-09-17/18 服务器两轮 + 本地，`run_L9_speedup_baselines.sh`，5/5 格已填、4 例口径待服务器权威化）

三条计时路线 + →B2 评测刷新二合一。**服务器 round 3（09-17 上午）**：
→B2 (val) eval 全量刷新（推理耗时 = A100 权威值），求解器计时 **1/5 成功**
（mdx_downstream npz 重建路线 12.7 s）——4 例失败根因 = 场景
`meta['source']` 存的是导入机器的绝对路径。**服务器 round 4（09-17 晚，
模板 scp 后重跑）**：preflight 修复**仍失败 4/5**——根因细化：存的是
Windows 风格路径，在 Linux 上既不解析也不拆组件——`D:\...\mdx` 的
`Path.name` 是整个字符串、`data\real_sources\wqh` 是单个组件，旧回退
`data/real_sources / src.name` 拼出 `data/real_sources/D:\...\mdx` 与
`data/real_sources\data\real_sources\wqh` 两种垃圾路径。mdx_downstream
重计 **13.2 s**（服务器权威，覆盖 12.7）；step 2 的 47 条 →B2 评测再次
全量刷新入库（registry 621→668）。

**已修（2026-09-18 本地）**：`time_b2_solver.py` 重写可移植性预处理——
分隔符归一化（反斜杠→POSIX）+ 候选列表（原值 / 仓库相对 /
`data/real_sources/<名>` 平铺 / 保留父目录四层）+ 存储统一 `as_posix()`；
mdx_downstream 路线不读 source、跳过 preflight。10 项单测
（`tests/test_time_b2_solver.py`，含 round-4 两个失败场景的复现用例）；
本地 5 例 npz meta 已就地归一化。**待办（round 5 服务器）**：同步修复后
脚本重跑 `time_b2_solver.py --all` + step 2，4 例换服务器权威计时。

**已确立的数字与口径（round 4 刷新后）**：

- **→B2 speedup 五格全部有值**，口径混合如实记档：mdx_downstream 用
  服务器 runtime（**13.2 s**，权威）；其余 4 例暂用本地 WSL2 runtime
  （mdx 48.7 s / mdx_upstream 23.4 s / wqh 22.5 s / zxh 30.8 s，偏慢
  → speedup 偏保守，`runtime_source` 标签区分）。
- round 4 刷新的推理耗时比 round 3 又低 17–29%（同 checkpoint 同数据，
  A100 状态更优；B1v2 flow_mdk s0 实测：mdx 1.67→**1.39 s**、
  mdx_downstream 0.74→**0.53 s**、wqh 0.46→**0.34 s**、zxh 0.22→
  **0.16 s**）。RMSE/MAE/CSI 逐位不变（仅 Dirichlet 能量有 ~1e-7 浮点
  噪声），L4_report/Pareto 无需重生成。
- 全 47 条刷新 eval 的 speedup 范围（混合口径）：mdx 11–66× /
  mdx_downstream 13–132× / mdx_upstream 23–190× / wqh 10–178× /
  zxh 65–510×；代表 run（partA_paper flow_mdk s0）：mdx 34.5× /
  downstream 24.5× / upstream 64.6× / wqh 63.3× / zxh 183.9×。
- **本地 vs 服务器求解器耗时差 ~4.5×**（mdx_downstream：本地 56.6 s vs
  服务器 13.2 s；WSL2 docker 慢得多）——4 例本地口径格是保守下界，
  服务器补跑后预计再抬 3–4 倍。

## 复现

```bash
# L1 真值批跑（幂等续跑）
python scripts/run_partA_mascaret.py --root data/scenarios_partA_v2 --all --workers 3
# L3 消融（B1 合并 + 三模型训练评测）
bash scripts/run_L3_B1B2_ablation.sh
# L2 正式对比（等待 L1 标记后自动执行）
bash scripts/run_L2_partA_swe.sh
# L4 论文预算单种子（Part A 四模型 + B1 三模型，2026-09-13 服务器）
bash scripts/run_partA_paper.sh && bash scripts/run_L3_B1B2_paper.sh
# E2 防漂移探针（lr/3层/早停）
bash scripts/run_L4_probes.sh
# E3 论文预算三种子（s1/s2 训练，s0 复制 09-13 run）
bash scripts/run_L4_multiseed_paper.sh
# E4 2D 论文预算（MS4_2d 组，支持 EXTRA 配方覆盖）
bash scripts/run_M3_2d_paper.sh
# E5 2D 三种子（s1/s2 补齐，s0 复用 E4 run）
SEEDS=1 2 bash scripts/run_M3_2d_paper.sh
# MS5 / E1 收官臂（浅层 2L×8 骨架 + MDK，3 新鲜种子）
bash scripts/run_MS5_shallow_mdk.sh
# L12 真实 2D 考卷（构建考卷 npz + 9 run × last/best 双协议零样本评测）
python scripts/build_real_2d_exam.py
bash scripts/run_L12_real2d_exam.sh
# L12 对照协议（训练视野 H=8，输出 eval_test_exams_2d_h8.json）
EXAM_ROOT=data/real_cases/exams_2d_h8 STEPS=8 bash scripts/run_L12_real2d_exam.sh
# L14 大 Δt 权衡（dt ×2/×3 数据根 + K 物理匹配臂）
python scripts/subsample_scenarios_dt.py --src data/scenarios_partA_v2 --dst data/scenarios_partA_v2_dt2 --stride 2
python scripts/subsample_scenarios_dt.py --src data/scenarios_partA_v2 --dst data/scenarios_partA_v2_dt3 --stride 3
bash scripts/run_L14_big_dt.sh
# E6.1 配方服务器验证（E61b = partA_v2 修正轮）
bash scripts/run_E61_recipe_validation.sh
# L16 -MDK 深度匹配消融（1D/2D × 3 种子）
bash scripts/run_L16_ablation.sh
# M4 耦合链可行性训练（mdx_chain_v1，单场景能力验证轮；评测本机补跑）
bash scripts/run_M4_coupled_v1.sh
python scripts/evaluate.py --config runs/M4_chain_v1_flow_mdk_s0/config.yaml --checkpoint runs/M4_chain_v1_flow_mdk_s0/last.pt --split test
python scripts/evaluate.py --config runs/ptbest_M4_chain_v1_flow_mdk_s0/config.yaml --checkpoint runs/M4_chain_v1_flow_mdk_s0/best.pt --split test
python scripts/evaluate.py --config runs/ptema_M4_chain_v1_flow_mdk_s0/config.yaml --checkpoint runs/M4_chain_v1_flow_mdk_s0/ema.pt --split test
# M4 v2 耦合家族批跑（参数化：q_scale × t_stretch 扰动入链流量律；服务器纯 CPU）
python scripts/build_coupled_family.py --num 12 --seed 11
# M4 v2 正式训练（家族 12 场景三臂 × 3 种子；先平铺 + split，再训练）
python scripts/prepare_coupled_family_root.py
bash scripts/run_M4_v2_family.sh   # ARMS/SEEDS/BATCH_SIZE 可覆盖；~2.5h/run A100
# L9 求解器计时（round 5 服务器：同步修复后的 time_b2_solver.py，模板已在 data/real_sources/）
python scripts/time_b2_solver.py --all
# 汇总报告（docs/L4_report.md 的十四个分组）
python scripts/summarize_runs.py --prefix partA_paper --prefix L3_B1_paper --ks
python scripts/summarize_runs.py --prefix MS4_partA --prefix MS4_B1 --ks
python scripts/summarize_runs.py --prefix MS4_2d --ks --dirichlet
python scripts/summarize_runs.py --prefix L4probe --ks
python scripts/summarize_runs.py --prefix MS5_partA --ks
python scripts/summarize_runs.py --prefix L16_mdkoff_partA --ks
python scripts/summarize_runs.py --prefix L16_mdkoff_2d --ks --dirichlet
python scripts/summarize_runs.py --prefix E61b_partA_full --ks
python scripts/summarize_runs.py --prefix B1v2 --ks
python scripts/summarize_runs.py --prefix unet_2d --ks
python scripts/summarize_runs.py --prefix M4_chain_v1 --ks
python scripts/summarize_runs.py --prefix ptbest
```

结果归档：`runs/L2_partA_*/`、`runs/L3_B1_*/`、`runs/partA_paper_*`、
`runs/L3_B1_paper_*`、`runs/MS4_*`、`runs/L4probe_*`、`runs/L14_*`、
`runs/L16_mdkoff_*`、`runs/E61b_*`、`runs/M4_chain_v1_*`、`runs/ptbest_*`
（config/history/eval json + 双 checkpoint；best.pt 对照在 ptbest_* 孪生目录）；
批跑报告 `data/partA_v2_mascaret_runs/_batch_report.json`、逐场景日志
`batch_log.jsonl`。
