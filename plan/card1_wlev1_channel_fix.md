# 卡 1 · 水位通道修正（W1）再验证实验

- **立卡**：2026-10-13；**状态**：待服务器执行
- **执行文件**：`scripts/run_wlev1_card1.sh`（幂等，中断重跑自动续）
- **预计算力**：12 个训练任务（4 臂 × 3 种子，G=64 / 150 epoch / curriculum 15 /
  batch 8，与 9 月 MS4 轮同配方）+ 纯推理评测约 100 次 + 1 次纯 CPU 诊断。
  训练耗时与 MS4 轮同量级（见 `runs/results.csv` 中 MS4_2d_* 的 train_seconds）。

## 1. 背景

论文全部已报告实验的配置为 `elevation_feature_idx: 0`，即水位通道 = **面积 + h**
（论文 2.2/4.4 节已如实记录）：

- 合成域（均匀 100 m 网格）：面积项为每运行常数，**论文全部主结果不受影响**；
- 真实网格（面积 2~879 m²，CV 1.29）：面积差均方根 21 m²，比湿边真实水位差大
  3~14 倍，方向门控与真实水面坡降一致率仅 ~49%（近乎随机）——真实算例上方向
  门控实际未参与，真实算例结果反映的是其余组件（残差式算子分裂、有界感受野
  扩散、恒等通道）的贡献。

本卡在修正通道（`elevation_feature_idx: 1`，`w = 床面高程 + h`）下重训关键臂并
全链路重评，把"方向机制在真实网格上生效"从预期变成结果；同时补齐协议里声明
但从未计算过的 **all-dry 第二无技巧地板**（`runs/results.csv` 此前只有
persist 地板行）。

## 2. 代码改动（均已入库，见 §5 同步）

| 文件 | 改动 |
|---|---|
| `configs/wlev1/2d_flow_mdk_wlev1.yaml` | 新增：`elevation_feature_idx: 1`，其余与 `2d_flow_mdk.yaml` 一致 |
| `configs/wlev1/2d_swegnn1x8_wlev1.yaml` | 新增：官方 1×8 SWE-GNN 臂的修正版 |
| `configs/wlev1/2d_ssgc_symmetric_wlev1.yaml` | 新增：对称扩散消融的修正版 |
| `configs/wlev1/2d_mdkoff_wlev1.yaml` | 新增：-MDK 消融的修正版 |
| `configs/wlev1/2d_baseline_alldry.yaml` | 新增：all-dry 地板（新基线 `baseline_alldry`） |
| `src/flow_mdk/baselines/alldry.py` | 新增：全干参照（ΔU = −U_t，恒零场） |
| `src/flow_mdk/baselines/__init__.py`、`models/factory.py` | 注册 `baseline_alldry` |
| `scripts/diagnose_gate_agreement.py` | 新增：真实网格门控方向诊断（纯 CPU） |
| `scripts/run_wlev1_card1.sh` | 新增：本卡服务器编排（幂等） |
| `scripts/build_wlev1_matrix.py` | 新增：W1 vs 旧臂对比矩阵（`docs/wlev1_matrix.{md,csv}`） |

旧配置一律不改——旧检查点保持可复现。注意：`train.py`/`evaluate.py` 的数据集侧
自 2d-only 分支（09-22）起已硬编码 `elev_idx=1`，本卡把**模型侧**（滚动刷新与
门控）经配置对齐到同一语义，两侧从此一致。

## 3. 实验臂与数据域

| 臂 | 配置 | 运行名 | 种子 |
|---|---|---|---|
| 定向扩散（本文） | `2d_flow_mdk_wlev1` | `W1_2d_flow_mdk_s{0,1,2}` | 0 1 2 |
| SWE-GNN 官方 1×8 | `2d_swegnn1x8_wlev1` | `W1_2d_swegnn1x8_s{0,1,2}` | 0 1 2 |
| 对称扩散（消融） | `2d_ssgc_symmetric_wlev1` | `W1_2d_ssgc_s{0,1,2}` | 0 1 2 |
| -MDK（消融） | `2d_mdkoff_wlev1` | `W1_2d_mdkoff_s{0,1,2}` | 0 1 2 |

GCN/GAT/U-Net 属背景基线，不进本卡（若审稿需要，另立卡 2 照抄协议即可）。
地板（与通道无关，无参数不读特征）：persist 沿用旧行 + 新增考卷两域；
all-dry 新增 4 域（`W1_floor_alldry_*`）。

数据域：`data/scenarios_2d_family`（域内 91/19/20）、`data/scenarios_2d_larger`
（大域 24 零样本）、`data/real_cases/exams_2d_h8`（考卷 H=8）、
`data/real_cases/exams_2d`（考卷全时程）。

## 4. 预登记判据（执行前锁定，回传后按此判读）

| # | 判据 | 通过条件 |
|---|---|---|
| C-A | 诊断复现 | `docs/wlev1_gate_agreement.json`：mdx 反转占比 ≈ 51%（即旧文一致率 49%）；两考卷合计反转占比 > 30% 即确认污染量级 |
| C-B | 域内非退化 | W1 flow_mdk 域内 last 三种子均值 < 0.716（persist 地板）且与 0.529 同量级（≤ 0.65）；三臂排序保持 定向 < mdkoff < 对称 |
| C-C | 真实考卷主判据（**本卡主目标**） | W1 flow_mdk 考卷 H=8（best 协议，即部署检查点口径）RMSE ≤ 2.471 m 且 CSI 不低于旧值——即使持平，结论也从"门控未参与的保守估计"升级为"修正后门控生效且无害"；若改善，则为方向机制的直接真实网格证据 |
| C-D | 地板补齐 | all-dry 四域 RMSE 入表，并指认每个域的绑定地板（min(persist, all-dry)）；重点看大域与考卷上 all-dry 是否低于 persist |
| C-E | 对 SWE-GNN 优势复现 | W1 口径下 flow_mdk 对 swegnn1x8 的优势方向与旧轮一致（域内与大域） |

判读纪律：检验单元为场景、误差先对 3 种子取平均（与 3.3 节口径一致）；臂级
结论仍受种子方差限制，判读时按 4.2 节的口径如实报告。

## 5. 上传服务器（同步清单）

优先走 git（服务器有仓库权限时）：

```bash
# 本地（D:\Projects\Flow-MDK，分支 2d-only）
git add configs/wlev1 src/flow_mdk/baselines/alldry.py src/flow_mdk/baselines/__init__.py \
        src/flow_mdk/models/factory.py scripts/diagnose_gate_agreement.py \
        scripts/run_wlev1_card1.sh scripts/build_wlev1_matrix.py \
        plan/card1_wlev1_channel_fix.md
git commit -m "feat: W1 card1 - corrected water-level channel (elev idx=1) re-validation + all-dry floor"
git push origin 2d-only
# 服务器
git fetch origin && git checkout 2d-only && git pull origin 2d-only
```

无 git 通道时按原样上传以下文件（相对仓库根）：

```
configs/wlev1/2d_flow_mdk_wlev1.yaml
configs/wlev1/2d_swegnn1x8_wlev1.yaml
configs/wlev1/2d_ssgc_symmetric_wlev1.yaml
configs/wlev1/2d_mdkoff_wlev1.yaml
configs/wlev1/2d_baseline_alldry.yaml
src/flow_mdk/baselines/alldry.py
src/flow_mdk/baselines/__init__.py
src/flow_mdk/models/factory.py
scripts/diagnose_gate_agreement.py
scripts/run_wlev1_card1.sh
scripts/build_wlev1_matrix.py
plan/card1_wlev1_channel_fix.md
```

## 6. 服务器执行

```bash
cd <仓库根>
CUDA_VISIBLE_DEVICES=0 bash scripts/run_wlev1_card1.sh 2>&1 \
    | tee data/wlev1_card1_$(date +%Y%m%d_%H%M%S).log
```

- 首日先只跑步骤 0–2（诊断 + 地板，纯 CPU/纯推理，约 10 分钟）确认环境与
  诊断数字，再放训练：`ARMS="flow_mdk" SEEDS="0" bash ...` 冒烟后放开。
- 全程幂等：中断/断点后直接重跑同一条命令。

## 7. 回传本地（同步清单）

```text
runs/results.csv                                   # registry（覆盖本地前先备份）
runs/W1_2d_flow_mdk_s0..2/                         # config.yaml history.json
runs/W1_2d_swegnn1x8_s0..2/                        #   last.pt best.pt
runs/W1_2d_ssgc_s0..2/                             #   eval_test.json
runs/W1_2d_mdkoff_s0..2/                           #   eval_test_scenarios_2d_larger.json
                                                   #   eval_test_exams_2d_h8.json
                                                   #   eval_test_exams_2d.json
runs/ptbest_W1_2d_*_s0..2/                         # config.yaml eval_*.json
runs/W1_floor_alldry_2d_family/  _2d_larger/  _exams_2d_h8/  _exams_2d/
runs/W1_floor_persist_exams_2d_h8/  _exams_2d/
docs/wlev1_gate_agreement.json
docs/wlev1_matrix.md   docs/wlev1_matrix.csv
data/wlev1_card1_*.log   data/wlev1_verify_*.log
```

检查点（last.pt/best.pt）务必回传：本地后续要做考卷轨迹图（F10 同款）与
逐场景配对检验，都依赖权重与 eval json 同在。

## 8. 回传后的本地处理（后续卡）

1. `python scripts/build_wlev1_matrix.py --registry runs/results.csv` 复核矩阵；
2. 逐场景配对 Wilcoxon（W1 flow_mdk vs persist / vs all-dry / vs W1 swegnn1x8，
   域内与大域），补臂级 Welch（n=3 口径如实报告）；
3. 考卷轨迹复刻（`analyze_exam_trajectories.py`，W1 checkpoint）；
4. 按 §4 判据出卡 1 结论，回写论文 4.4/5.3 与交底书实施例的对应表述。

## 9. 风险与回退

- **域内语义微移**：修正后合成域门控从"水深梯度"变为真实水面坡降（合成床面
  起伏 3.7 m），域内数字可能小幅移动。若 C-B 不达标（>0.716 或排序破坏），
  这本身是"通道语义在合成域亦有影响"的发现，如实报告并触发判读会议，
  论文主表是否切换到 W1 口径届时再定。
- **与旧数字并置**：`(w1)` 与 `(idx0)` 两代结果在 `docs/wlev1_matrix` 中分列，
  不合并、不混排；论文最终采用哪一代口径，按 C-B/C-C 判据结果决定。
- **算力不足**：优先级顺序为 flow_mdk > swegnn1x8 > mdkoff > ssgc；地板与
  诊断不占 GPU，任何情况下先跑。
