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
真实家族 + 2D 管线，全部可复现）；② 深传播稳定性（门控 vs 无门控深基线的对照 +
λ₀/Dirichlet 诊断）；③ 诚实的多种子/多预算评测方法学。**「定向 MDK 显著优于
对称核」作为主卖点不成立，降级为探索性对照**；定向性的下一个、也是最后一个
主战场是 2D 激波体制（M3 已就位：真值管线 + pilot 20 场景全过，65k 节点训练
需服务器）。收口路径：

1. 论文预算 3 种子（A100 每 run 1–2 h，~7 run/种子，当日可完）——把 1/2/4 条
   结论钉死；同步补 best.pt 评估与 Dirichlet 富评。
2. M3 全速推进：2D 场景族扩到 130 + 65k 节点训练，验证体制分工在 2D 是否成立。
3. 论文骨架按 ①②③ 组织（HESS / EM&S 体量足够）；若 2D 中定向分支仍无优势，
   则以「稳定深传播 + 基准 + 方法学」成文，MDK 作为稳定化机制的一种实现。

## 五、遗留与下一步

1. **服务器 3 种子论文预算**（决定性收口实验，判据同 L4）。
2. **best.pt 对照评估 + Dirichlet 富评**（7 个 checkpoint 本地/服务器均可，评价
   last.pt 协议是否低估模型上限）。
3. M3：2D 场景族扩容 + 训练接入（`run_telemac2d_docker.py` 管线已通）。
4. L9 加速比：本次 A100 eval 附带 `speedup` 94–316×（zxh 族），可入 M5 素材。
