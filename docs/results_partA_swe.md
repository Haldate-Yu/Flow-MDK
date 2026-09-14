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
- B2 加速比 19–206×（wqh/zxh/mdx_upstream 有参考耗时；mdx/mdx_downstream 待补，
  见 L9）。

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
   统一配方后才可下最终结论。
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

## 复现

```bash
# L1 真值批跑（幂等续跑）
python scripts/run_partA_mascaret.py --root data/scenarios_partA_v2 --all --workers 3
# L3 消融（B1 合并 + 三模型训练评测）
bash scripts/run_L3_B1B2_ablation.sh
# L2 正式对比（等待 L1 标记后自动执行）
bash scripts/run_L2_partA_swe.sh
```

结果归档：`runs/L2_partA_*/`、`runs/L3_B1_*/`（config/history/eval json）；批跑报告
`data/partA_v2_mascaret_runs/_batch_report.json`、逐场景日志 `batch_log.jsonl`。
