# 进展日志 · 2026-09-15

> 总览、里程碑状态与待办清单见 [`PLAN.md`](PLAN.md)。本日为主题日：**E2/E3/E4
> 服务器结果取回、入库与判决**——三种子复测推翻两条单种子结论，2D 论文预算
> 给出门控深传播的首个跨协议稳固优势，课题主张按证据最终收口。

## 一、runs 取回与入库

- 服务器取回 `runs_server_260914/`（78 MB）：新增 **49 个 run 目录**拷入 `runs/`——
  E3 多种子 `MS4_partA_{swegnn,flow_mdk,gcn,gat}_{s0,s1,s2}`（12）+
  `MS4_B1_{swegnn,flow_mdk,ssgc}_{s0,s1,s2}`（9）、E4 2D `MS4_2d_{swegnn,flow_mdk,ssgc}_s0`（3）、
  E2 探针 `L4probe_{lr,L3,es}`（3）+ 各自 best.pt 孪生 `ptbest_*`（20）+
  `M3_2d_smoke_{swegnn,flow_mdk}`（2）。19 个已存在目录跳过（与仓库逐字节一致）。
  1D 的 `MS4_*_s0` 为 09-13 论文 run 的副本（目录内 `_SEED0_SOURCE.txt` 标记，
  registry 行在原名下）。
- `runs/results.csv` 追加服务器 120 行（135→255，零冲突）：14 个 E3 训练 +
  3 个 E2 探针 + 3 个 2D run + 各 ptbest/smoke 评测行。
- `docs/L4_report.md` 重建为七分组机器报告（单种子 s0 × 2 + 多种子 × 2 + 2D +
  探针 + ptbest 大表），生成命令写入文件头。
- 工具修复：`summarize_runs.py` 的 fallback 标签补 `eval_<split>_test.json`
  解析（registry-less 的 s0 副本目录此前会把 A2/A3 评测列名为 `test:A2`）。

## 二、E2 · 防漂移探针（flow_mdk 论文配置，A-test）

| 探针 | 变更 | last h | best h |
|---|---|---|---|
| baseline（6L+MDK s0） | — | 1.417 | 2.865 |
| lr 减半 | lr 0.0035、decay 0.85@5ep | 8.499 | 17.014 |
| **3 层** | 深度减半 | **0.778** | 1.231 |
| 早停 patience=20 | — | 2.669 | 1.931 |

**结论**：漂移的现实治理杠杆是**降深度**（3 层 flow_mdk 直接进入浅层骨架的
0.72–0.78 档），动优化器（lr 减半全面恶化、慢退火在固定预算内欠训练）与
早停（ep32 于课程期 H=3 触发即停，与课程学习冲突）都不可用。6 层深传播在
合成 1D 无域内收益获得机制性支撑：深度是漂移的主载体。

## 三、E3 · 论文预算三种子（14 run 全部成功）

Part A（A-test，last/best，m）与 B1（域内）逐种子数字见
[`docs/results_partA_swe.md`](../docs/results_partA_swe.md) E3 节；要点：

| 域 | last.pt mean±std（swegnn / gat / gcn / flow_mdk） | best.pt mean±std |
|---|---|---|
| A-test | 1.49±0.73 / 1.13±0.68 / 12.38±19.92 / 5.04±3.20 | 1.79±1.31 / **0.87±0.10** / **0.78±0.03** / 4.81±2.52 |
| B1 | 1.25±0.78 / — / — / 1.39±0.99（ssgc 2.54±2.04） | 0.89±0.23 / — / — / **0.83±0.11**（ssgc 1.61±1.77） |

1. **种子方差碾压模型间距，1D 排序问题在当前配方下无解**：s0 的 GCN 35.4
   塌缩与 flow_mdk 1.42 都不具代表性（gcn s1/s2 = 0.74/1.03；flow_mdk s1/s2
   恶化到 6.25/7.46）。KS（合并种子）：A-test 上 flow_mdk 显著差于
   gat/swegnn（p~1e-30）；B1 三模型两两无显著差异（p≥0.06）。
2. **09-14 L4 单种子判决两条被推翻**：①「B1 真实家族域门控系全面占优
   （0.85 vs 2.15）」——swegnn s1/s2 同样落到 0.79/0.80，未复现；②「无门控
   模型被漂移同等压制」——gcn/gat 的 best.pt 跨种子稳定 0.74–0.93
   （±0.03/±0.10 全场最稳），其 val-best 选点（ep1–2）反而可靠。
3. 跨种子/跨协议仍稳固的只有：**B1 域内 flow_mdk 两种协议都稳定在 0.8 档**
   （best.pt 0.826±0.105，三模型方差最小）；以及 E2 的"深度=漂移主载体"。
   flow_mdk 的 val-best 选点在三种子上系统性失败（best.pt 4.81±2.52）——
   混合门控的 val 曲线本身不可信。
4. B2 考卷（真实历史事件）三模型 last.pt 无显著差异（KS p≥0.68）。

## 四、E4 · 2D 论文预算训练（MS4_2d，4096 节点合成网格，batch 8，2.4–6.0 h/run）

2D test（20 场景）h-RMSE（m）：

| 模型 | last.pt | best.pt | CSI@0.05（last） | 加速 |
|---|---|---|---|---|
| swegnn（2L×8 跳） | 1.818 | 1.044 | 0.459 | 216–808× |
| **flow_mdk（6L+MDK）** | **0.359** | **0.778** | 0.708 | 233–875× |
| ssgc（6L 对称） | 0.324 | 1.957 | 0.751 | 225–965× |

1. **首次 ×5 级模型分离，方向有利于门控系——2D 激波体制是深传播的正面
   战场**：预注册 last.pt 协议下 6 层门控模型大幅优于浅层 8 跳骨架；
   best.pt 下 flow_mdk 仍最优（0.778 vs 1.044）。**两种协议下 flow_mdk 均
   不劣于 swegnn**，1D 上从未出现过的跨协议稳固优势。
2. **定向 vs 对称在 2D 内部仍无一致优势**（last.pt ssgc 0.324 ≈ flow_mdk
   0.359，best.pt 反转）——与 1D 一致，收益属于"MDK 门控混合使深传播稳定"，
   不属于"水力定向"。09-14 定调（稳定深传播 + 基准 + 方法学）由此被 2D
   证据正面支持。
3. 机理信号干净：末层 Dirichlet 能量（逐边归一）swegnn 0.98 vs flow_mdk
   0.011 / ssgc 0.0035（**两个数量级**）；λ₀ 末层在 2D 保留 0.03–0.21（1D
   塌缩到 ~0.05）。新评测链（服务器同步 L5 后）全部带 `dirichlet` 字段。
4. 漂移跨维度存在（best epoch 10/15/11，val 漂移 2.3–2.7×），但 2D 的
   last.pt 受损者恰是 swegnn，flow_mdk 反而 last < best——协议之争不改变
   2D 的方向。
5. 局限：单种子、合成 4096 节点网格、未含真实 2D 工程。

## 五、课题走向（本日定调，接 09-14）

**主张收口为「MDK 门控混合 = 稳定深传播机制」**，三条证据腿全部到位：
① E2——1D 中深度是漂移主载体，3 层+MDK 与最优基线同档；② E3——1D 全部
模型排序信号对种子敏感（方法学卖点：诚实的多种子/双协议评测）；③ E4——
2D 激波体制中门控深传播 ×5 优势跨协议成立，且 Dirichlet/λ₀ 诊断给出机制
解释。"水力定向"在 1D/2D 均无一致优势，维持探索性对照。

## 六、遗留与下一步

1. **E5：2D 三种子 + 真实 2D 考卷**（把 E4 的单种子 ×5 钉死）：
   `SEEDS=1 2 bash scripts/run_M3_2d_paper.sh`（脚本已支持）；真实 2D
   （wqh_2d/mdx_2d 65k 节点）考卷接入需图分块或下采样。
2. **E6（可选）：best.pt 选点治理**——flow_mdk 的 val-best 系统性失败
   （E3），值得一个 val 平滑/EMA/后期快照集成探针；gcn/gat 的 ep1–2 val-best
   现象值得单独写进方法学讨论。
3. λ₀ 曲线图刷新到多种子/2D（`scripts/plot_mdk_lambda0.py`）。
4. 09-13 论文 s0 run 的 last.pt eval json 仍无 `dirichlet`（旧代码）——
   如需补齐用 ptbest 同款孪生目录重评，低优先。
5. L6（mdx 家族补 50）、L9（加速比基线补全）、L8 照旧挂起。

## 七、MS5 · E1 收官尝试完成（同日第二轮，服务器 ~1.5 h）

浅层多跳骨架 + MDK 混合（`configs/1d_swegnn_mdk.yaml` = 官方 2L×8 骨架 +
定向 MDK，唯一差异是 mdk 块；`run_MS5_shallow_mdk.sh`）3 个新鲜种子全部
跑完。A-test h-RMSE（last / best，m）：

| 种子 | last | best |
|---|---|---|
| s0 / s1 / s2 | 1.952 / 2.091 / 5.676 | 1.406 / 1.044 / 1.057 |
| **mean±std** | 3.239±2.111 | **1.169±0.206** |

1. **追平判据（预注册：best.pt 进入 gcn 0.777±0.032 档）未达成**——差基线
   约 1.5×，位于 GCN/GAT（0.78–0.87）与骨架 best.pt（1.79）之间。**E1 正式
   关闭：「调参让 flow_mdk 系在 1D 合成域达到最佳」在全部已测方向（lr/早停/
   降深度/骨架混合）内不可达。**
2. 浅层化是 MDK 系在 1D 的最优形态：best.pt 1.169±0.206 为全部 MDK 系配置
   中最优且跨种子最稳（6L 版 4.811±2.520），mean/方差双双优于无 MDK 同骨架
   （1.788±1.305）——E2 深度结论 +1；浅层下扩散分支的归纳偏置首次兑现为
   域内净收益。
3. 坏种子 s2 暴露漂移在零样本域被数量级放大（域内 5.68 → fam_mdx 350，
   ×123）——last.pt 零样本数字对坏种子极其脆弱，论文中零样本表必须配
   best.pt 对照或多种子。
4. 1D 域内排位定论：GCN/GAT（best.pt 0.78–0.87）> 浅层+MDK（1.17）≈ 3L+
   MDK > 其余。MDK 价值域 = B1 真实家族域（双协议 0.8 档）+ 2D 激波体制
   （E4 ×5），课题主张不变。
5. 工具修复：`summarize_runs.py` 的 `model_name` 剥离 `_s<seed>` 后缀——
   无模型子串的自定义臂名（如 MS5_partA_2x8mdk）此前不会跨种子折叠。
6. E5 进行中：`MS4_2d_swegnn_s1` 尚在训练（仅 checkpoint 无评测），本次
   未入库，等整批完成后随 E5 一起取回（含 ptbest 孪生与完整 registry 行）。

## 八、E6 · 选点治理：根因定位、三项训练侧改动与本地探针落定（同日第三轮）

1. **根因**：val_loss 按当前课程视野计算，跨 epoch 不可比；课程语义为每
   视野停 curriculum_steps 个 epoch（论文预算 H=8 于 ep106）——全部历史
   best.pt 均为 H=1 状态。三项改动入 `trainer.py`/`config.py`（默认关闭）：
   `val_horizon` / `early_stop_after_curriculum` / `ema_decay(+ema.pt)`。
2. **本地探针**（flow_mdk 6L × 4 臂 × 3 种子 = 12 run，A-test）：
   last 3.40±3.73 [0.93, 11.70] · best 2.95±2.00 · ema 2.19±1.08 [1.46, 4.34]。
   判读：①biased val-best 0/6 判死（base+ema 臂同轨迹全败，best 落 ep3–4
   H=1）；②val@H8 best 同轨迹 4/6 赢 last、选点语义修复但救不动 6L 漂移；
   ③EMA-from-init 同轨迹 2/6 但跨 run 最稳（方差压缩器）→ 课程期污染 →
   已补 `ema_after_curriculum`（E6.1，待服务器 run 验证）；④**混沌发现：
   同种子 epoch-1 即分叉（CUDA 非确定性），last.pt 是 12.5× 彩票——漂移
   体制下单 run 数字不可信，协议对照 + 多种子为必要条件**。
3. **E6 配方**（后续 run 默认）：val_horizon=H_max + ema_after_curriculum +
   早停门；best.pt 对照保留、ema.pt 第三协议。详见
   `docs/results_partA_swe.md` E6 节与 `scripts/run_E6_val_governance.sh`。
4. 花絮：base 臂期间 GPU 被其他负载挤占（33 个 CUDA 上下文、85–86°C 温度
   降频至 915 MHz），节奏 21→153 s/epoch；释放资源后恢复。
