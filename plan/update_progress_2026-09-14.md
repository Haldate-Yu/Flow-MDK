# 进展日志 · 2026-09-14

> 总览、里程碑状态与待办清单见 [`PLAN.md`](PLAN.md)。本日为主题日：**L4 论文预算
> 结果取回、入库与判决**——服务器 7 个 paper run 归档入库，L2/L3 全部正式结论
> 落定，课题走向据此定调。

## 一、L4 runs 取回与入库

- 服务器取回 `runs_server/`（19 MB）：与仓库比对后，非 paper 目录
  （L2_partA_*/partA_*/L3_B1_*/smoke_gpu_paper）逐字节一致（仅 2 个 eval json 的
  `seconds/speedup` 计时字段不同——A100 vs 本机 3060 重评所致，仓库以本地版为准）；
  **新增 7 个论文预算 run** 拷入 `runs/`：
  `partA_paper_{swegnn,flow_mdk,gcn,gat}_20260913_202615`、
  `L3_B1_paper_{swegnn,flow_mdk,ssgc}_20260913_202721`。
- `runs/results.csv` 两机拼接合并（09-13 计划既定方案）：本地 80 行 + 服务器
  41 行 = 121 行，零冲突。
- 归档刷新（`scripts/archive_datasets.py`，9542 文件 / 7.55 GB）：paper runs 与
  昨日未及归档的 18 个多种子 run（MS_*）补入 `datasets/runs/`；顺带补上 M3 真值
  npz（`meshes_2d/{mdx,wqh}_2d.npz`，昨日 15:28 重摄取后归档未跟上，LFS 指针更新）。
- L4 报告一键生成：`python scripts/summarize_runs.py --prefix partA_paper
  --prefix L3_B1_paper --ks --out-md docs/L4_report.md`（结果与手工核对一致）；
  λ₀ 曲线 `runs/lambda0_curves_paper.png`。

## 二、L4 结果（详见 [`docs/results_partA_swe.md`](../docs/results_partA_swe.md) L4 节）

**Part A（合成 1D，G=64/150ep，A-test h-RMSE）**：swegnn（2L×8跳）**0.722** <
flow_mdk（6L+MDK）1.417 < gat 1.918 << gcn 35.38（塌缩为常数输出，逐场景
31.7–36.2 m）。A2/A3 同序。零样本：fam_mdx 上 flow_mdk 最优（2.28 vs 3.02），
fam_zxh/wqh 上 swegnn 最优。

**B1→B2（真实家族域）**：B1 域内 ssgc **0.852** ≈ flow_mdk 0.875（KS p=0.81）
<< swegnn 2.150（p≈7e-4）；B2 均值 flow_mdk **1.621** ≈ ssgc 1.684（p=1.0），
逐考卷 2:2 分胜负。

**共性诊断**：7 个 paper run 全部 best epoch 极早（4–14）且 val 漂移 2–4×；
λ₀ 末层持续收缩（0.4→0.05）；服务器代码早于 L5 提交，eval json 无 `dirichlet`
字段——checkpoint 已取回，best.pt 对照评估 + Dirichlet 富评本地可补。

## 三、判决（对照 L4 升级判据）

1. **主干稳定性（升级判据）✅ 通过（单种子抽样）**：flow_mdk 论文预算下无本地
   s1 型崩坏；崩坏转移到无门控的 6 层基线（GCN 塌缩、GAT 退化）——「深传播
   需要门控」叙事有了最硬的一条证据。
2. **合成 1D 域内：浅层 8 跳最优**，6 层+MDK 无域内收益；
3. **真实家族域（B1，论文核心域）：深层门控系全面占优**（0.85/0.87 vs 2.15）；
4. **定向 vs 对称仍无显著差异**（p=0.81 / p=1.0）——「水力定向 MDK 优于对称核」
   的核心假设在本地 3 种子 + 论文单种子下均无统计支持。
5. 评测协议（last.pt）下 best epoch 极早的现象值得单独排查（lr 日程 / rollout
   漂移），可能掩盖模型真实上限。

## 四、课题走向结论（本日定调）

**课题继续，主张调整。** 站得住的贡献三条腿：① 数据集与真值管线（Part A v2 +
真实家族 + 2D 管线，全部可复现）；② 训练漂移的量化与治理（best.pt/last.pt
协议对照 + λ₀/Dirichlet 诊断；无门控模型漂移后果更重）；③ 诚实的多种子/多
预算评测方法学。**「定向 MDK 显著优于
对称核」作为主卖点不成立，降级为探索性对照**；定向性的下一个、也是最后一个
主战场是 2D 激波体制（M3 已就位：真值管线 + pilot 20 场景全过，65k 节点训练
需服务器）。收口路径：

1. 论文预算 3 种子（A100 每 run 1–2 h，~7 run/种子，当日可完）——把 1/2/4 条
   结论钉死；同步补 best.pt 评估与 Dirichlet 富评。
2. M3 全速推进：2D 场景族扩到 130 + 65k 节点训练，验证体制分工在 2D 是否成立。
3. 论文骨架按 ①②③ 组织（HESS / EM&S 体量足够）；若 2D 中定向分支仍无优势，
   则以「稳定深传播 + 基准 + 方法学」成文，MDK 作为稳定化机制的一种实现。

## 五、遗留与下一步

1. **E2 防漂移探针**（升级为关键路径）：`scripts/run_L4_probes.sh`（lr 减半/
   3 层/早停三探针，A100 ~1 h）——E1 证明漂移是压在所有模型上的第一问题。
2. **E3 三种子论文预算**：`scripts/run_L4_multiseed_paper.sh`（默认 seed 1/2
   × 7 模型，`EXTRA=` 可携带 E2 定出的新配方；run 名 `_s<seed>` 结尾，
   summarize 自动折 mean±std，s0 由 2026-09-13 run 复制）。
3. **E4 2D 训练冒烟 ✅ 当日通过（服务器回报）**：`run_M3_2d_smoke.sh` 在同步
   src 后全绿——swegnn/flow_mdk 各 3 epoch 正常收敛（A100 42–50 / 23–27
   s/epoch @ batch 4×4096 节点），2D test（3 场景）h-RMSE 1.15/1.18 m，
   speedup 54–59×。**首次 2D 训练成立**；3 epoch 下 CSI 0.25–0.5、best@ep1
   均为欠训练表现，不作模型间比较。首次踩坑：服务器 src/scripts 版本不齐
   （L5 的 `RolloutReport.dirichlet` 字段缺失）→ 修复约定：**src/scripts/
   configs 永远打包同步**（服务器实际路径 `/data/ywh_data/Flow-MDK`）。
4. L9 加速比：本次 A100 eval 附带 `speedup` 94–316×（zxh 族），可入 M5 素材。
5. Dirichlet 富评（checkpoint 已取回，服务器 eval json 无 dirichlet 字段）。

## 六、E1 · best.pt 对照复评（同日追加，本机 3060，~5 min）

上节"主干稳定性判据通过 / GCN 塌缩"的表述**被当日 best.pt 对照部分推翻**，
结论已按证据改写（详见 `docs/results_partA_swe.md` L4/E1 节）。核心表：

| run | last h | best h | last CSI@.05 | best CSI@.05 |
|---|---|---|---|---|
| partA swegnn | **0.722** | 3.275 | 0.978 | 0.984 |
| partA flow_mdk | 1.417 | 2.865 | 0.400 | **0.984** |
| partA gcn | 35.378 | **0.740** | 0.984 | 0.946 |
| partA gat | 1.918 | **0.748** | 0.158 | 0.891 |
| B1 swegnn | 2.150 | 1.144 | 1.000 | 0.947 |
| B1 flow_mdk | 0.875 | **0.782** | 1.000 | 1.000 |
| B1 ssgc | **0.852** | 3.651 | 1.000 | 1.000 |

- **GCN"塌缩"是漂移伪影**：epoch-14 状态 0.740 与最优持平——"深传播需要
  门控"叙事在 best.pt 对照下不成立，收回；无门控模型漂移后果更重仍成立。
- **val-best 选点不可靠**：一半 run 的 val-best 落在课程学习期（欠训练，
  best.pt 反而更差）；两协议各有赢家 → 漂移治理才是第一优先级。
- **flow_mdk 的 CSI@0.05 0.400 也是漂移伪影**（best.pt 0.984）；B1 上
  flow_mdk best.pt 0.782 为全场最优——门控系在真实家族域的优势跨协议成立。
- 评测走 ptbest_* 孪生目录（`evaluate.py` 输出名只含 split+data-root，直评
  best.pt 会覆盖 last.pt 的 eval json），registry 行 checkpoint 字段可辨。

**对"调参能否反超"的更新**：反超概率未升（GCN best.pt 0.740 说明对手同样
被漂移压制、治理后同涨），追平（0.7–0.8）概率进一步上升；1D 域内是拥挤赛道，
区分度仍看稳定性 / 真实域 / 2D。
