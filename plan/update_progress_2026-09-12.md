# 进展日志 · 2026-09-12

> 总览、里程碑状态与待办清单见 [`PLAN.md`](PLAN.md)。当日完成 L1（Part A v2 的
> Mascaret 全 SWE 真值，含**内核源码级修复**）、L2（四模型正式对比，干净真值重跑
> 版）、L3（B1→B2 三方消融首轮）。详细数字与配方：
> [`docs/results_partA_swe.md`](../docs/results_partA_swe.md)；
> 内核补丁证据链：[`datasets/telemac-mascaret-v8p4r0/PATCHES.md`](../datasets/telemac-mascaret-v8p4r0/PATCHES.md)。

## 一、L1 · Part A v2 的 Mascaret 全 SWE 真值

### 1.1 两段式初始化落地

- `scripts/run_partA_mascaret.py` 重写 + `scripts/run_mascaret.py` 扩展：
  SARAP 稳态内核（code 1，恒定基流 + 法线水深下游水位）预跑渐变流水面线 →
  写成 `init.lig`（permanent/LIDO 格式，`formatFichLig 2`）→ 瞬态内核（code 3，
  与真实工程一致）从该线起步；SARAP 遇床面干隆起按 1×/3×/9× 基流阶梯重试，
  仍失败退化为自下游向上回填的单调湿水面线。支持并发（`--workers`）、幂等续跑
  与 `--force` 全量重跑。
- 四个内核级配置坑位逐条查证 v8p4 源码/官方算例后确定（详见 results_partA_swe.md
  的配置表）：文件式初始线（键盘内联段错误）、下游法线水深称率曲线 Q(Z)
  （律 type 5 + `typeCond 1 4`，Test13 配方；表须下探床面以下 2 m）、变步长
  （固定 30 s 在全 SWE 核失稳；`<pasStock>` 单位是**步数**）、SARAP 需整块换用
  官方参数块（缺节点读空段错误）。

### 1.2 内核源码级修复（当日关键突破）

初版批跑 89/130，41 个失败对初始线/步长/床面形态/稳定化开关全部免疫——据此
怀疑内核本身。用仓库内构建上下文的源码在容器内编出带符号 debug 内核
（`-g -O0 -fbacktrace -fcheck=all`；`sources/mascaret/Makefile` 链接清单落后，
需手动补链接），拿到符号化崩溃点 `mascaret.f90:1021`（XAJ 侧向入流插值）：

- **主因**：源码树本地魔改的 XAJ（新安江）读取块无条件打开 `Q_XAJ.txt`/
  `X_XAJ.txt`，文件缺失时 `nlines`/`num_columns`（intent(out)）**从未赋值** →
  主循环以垃圾索引越界读堆 → 随机段错误，未崩溃时结果带微小数值污染。
- **次因**：上游 Q 强加边界在临界流附近把 `-床面高程` 当水深送进几何表查询
  （原有干净报错分支被注释）。
- **修复**：缺失分支定死空状态（等效无侧向入流）+ YFIX 回退当前节点实际水深。
  改动前备份 `backups/2026-09-12/mascaret.f90.orig`，补丁
  `flowmdk_kernel_patch_2026-09-12.patch`，重建镜像 **`flow-mdk-telemac:v8p4r0p1`**
  （原镜像保留可回档）。
- **验证**：已通过场景重跑 `.opt` **逐位一致**；全量重跑 **128/130 通过**
  （全部走上 SARAP 稳态初始化）；真实家族 zxh 22 例段错误确认为同根因（待决策
  重跑）。剩余 4 例为另一类独立缺陷（`s1geo` 几何表负索引，干涸极限工况，干净
  报错），低优先。
- **真值净化**：81/89 个原"通过"场景真值有 ≤0.16 m 级别修正 → 触发 L2 重跑。

## 二、L2 · 四模型正式对比（干净真值 × 128 场景，本地预算 G=32/40ep 单种子）

| 模型 | A-test h | → fam_mdx | → fam_zxh | → fam_wqh | → B2 考卷 |
|---|---|---|---|---|---|
| GCN | **0.794** | 3.099 | **0.212** | **0.651** | **1.935** |
| GAT | 0.827 | 3.462 | 0.284 | 0.796 | 2.064 |
| **Flow-MDK** | 1.422 | **2.629** | 0.632 | 0.929 | 2.260 |
| SWE-GNN | 4.496 | 3.697 | 0.581 | 1.102 | 3.474 |

- **稳健发现**：MDK 混合把自家骨架拯救 ×3.2（1.42 vs 4.50；5 个评测域中 4 个
  SWE-GNN 一致最差，唯一例外是最小流域 fam_zxh，各模型均 <0.7 m）。
- **诚实修正**：早先在污染真值 + 43 训练场景上得到的"体制翻转、Flow-MDK 域内
  最优 1.79"是数据假象（GCN 从 2.38 → 0.79 的跃升主要来自训练场景恢复完整
  60/60）；干净真值下对称平滑基线在 1D 链式场景依然很强。SWE-GNN 论文级配置
  （G=64、2×8 跳、150 epochs）的优势需要在 **L4 服务器论文预算**下复测才能
  与 GCN/GAT 公平对比——本地链为保持四模型同预算压低了所有配置。
- **synthetic→real gap**：域内→fam_mdx 零样本，Flow-MDK ×1.8 < GCN ×3.9 <
  GAT ×4.2（Flow-MDK 在最难考卷族上零样本最优且退化最缓）。

## 三、L3 · B1→B2 三方消融首轮（真实数据，本地预算）

B1 = 三真实母版家族合并（117 场景，81/17/19）→ B2 = 5 个真实考卷。水深 RMSE：

| 模型 | B1 域内 | mdx | mdx_up | mdx_dn | wqh | zxh | B2 均值 |
|---|---|---|---|---|---|---|---|
| SWE-GNN | 0.830 | 5.13 | 1.84 | **1.01** | 0.29 | 0.07 | **1.669** |
| SSGC | 0.798 | 3.95 | 1.19 | 3.56 | 0.38 | 0.06 | 1.826 |
| Flow-MDK | 1.954 | 4.88 | **1.25** | 3.56 | 1.65 | 0.90 | 2.448 |

本地预算下三方同量级，Flow-MDK 域内欠拟合（1.95 vs 0.80）；闸门/耦合链考卷上
定向系占优、简单考卷上 SWE-GNN 占优，体制分工初现端倪。**结论待 L4 论文预算
复测**（B1/B2 真值来自真实工程，未受内核污染影响，无需重跑）。

## 四、当日产出清单

| 产出 | 位置 |
|---|---|
| 内核补丁 + 备份 + patch 文件 + PATCHES.md | `datasets/telemac-mascaret-v8p4r0/` |
| 补丁镜像 `flow-mdk-telemac:v8p4r0p1` + tar 归档 | `datasets/docker_images/` |
| Part A v2 真值 128/130 + split 过滤（A1_train 60/60） | `data/scenarios_partA_v2/` |
| 实验脚本（本地链 + 论文预算链） | `run_partA_mascaret.py`、`run_L3_B1B2_ablation.sh`、`run_L2_partA_swe.sh`、`run_L3_B1B2_paper.sh`（新） |
| L2/L3 全部运行归档 + results.csv 登记 | `runs/L2_partA_*`、`runs/L3_B1_*` |
| 结果报告 / 服务器手册 / 数据归档说明 | `docs/results_partA_swe.md`、`docs/server_setup.md`（按打包→环境→镜像→执行→取回重写）、`datasets/README.md` |
| 可复现性清理 | 全仓移除个人机绝对路径引用；`import_real_cases.py` 默认源改 `datasets/real_projects`；三脚本默认镜像切 `v8p4r0p1` |

## 五、遗留与下一步

- **L4（服务器论文预算）——当前最重要**：本地 G=32/40ep 单种子只能用于管线
  验证与相对趋势，SWE-GNN 论文配置的优势、Flow-MDK 混合门控的收敛、三方消融的
  体制归属都必须在 A100 + G=64/150 epochs 下复测（脚本已备：
  `run_partA_paper.sh` + `run_L3_B1B2_paper.sh`，流程见 `docs/server_setup.md`）。
- **真实家族重跑决策**：zxh 22 例段错误与全家族微小污染可用补丁内核清除
  （~1–2 h），但会改动已验证的 B1/B2 真值管线——先做新旧真值差异评估再决定。
- 4 例 s1geo 负索引场景（低优先）；L5 over-smoothing 监控接入评测；L9 B2 加速比
  基线补全；L10 git 提交。
