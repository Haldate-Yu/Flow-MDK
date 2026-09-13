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
