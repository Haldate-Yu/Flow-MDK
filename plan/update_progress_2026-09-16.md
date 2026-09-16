# 进展日志 · 2026-09-16

> 总览、里程碑状态与待办清单见 [`PLAN.md`](PLAN.md)。本日为 **E5 收口日**：
> 服务器 2D 三种子整批取回、入库与判决——E4 的 ×5 优势三种子钉死，flow_mdk
> 成为唯一跨协议/跨种子稳固的模型，M2 证据链全部收口。

## 一、runs 取回与入库

- 服务器取回 `runs_server_260916_v1/`：新增 **12 个 run 目录**拷入 `runs/`——
  E5 2D 三种子 `MS4_2d_{swegnn,flow_mdk,ssgc}_{s1,s2}`（6，各含 config/history/
  eval json/双 checkpoint）+ `ptbest_*` best.pt 协议对照孪生（6，各含 config/
  eval json）。19 个已存在目录跳过；2 个 zxh eval json 差异为仓库版更新
  （本地补算过 Dirichlet 字段），保留仓库版未覆盖。
- `runs/results.csv` 追加服务器 18 行（333→351，零冲突，按时间戳归并排序）：
  6 个 E5 训练 + 6 个 last.pt 评测 + 6 个 ptbest 评测。
- E5 整批于服务器 09-15 14:44 开跑、09-16 04:46 完成（`M3_2D_PAPER_DONE`），
  训练 swegnn 4.5–5.1 h/run、门控系 2.3–2.6 h/run，合计 ~19 h wall。
- 报告刷新：`docs/L4_report.md` 全部八分组重新生成（MS4_2d 组并入 s1/s2，
  3→9 runs，并首次带 `--dirichlet` 表）；`summarize_runs.py` 无需改动
  （`_s<seed>` 折叠已在 09-15 修好）。

## 二、E5 · 2D 三种子判决（MS4_2d s1/s2，配方同 E4）

2D test h-RMSE（m，per-seed 与 mean±std；s0 列即 E4）：

| 模型 | last.pt（s0/s1/s2） | last mean±std | best.pt（s0/s1/s2） | best mean±std |
|---|---|---|---|---|
| swegnn（2L×8 跳） | 1.818 / 12.655 / 0.708 | 5.060±6.600 | 1.044 / 7.925 / 0.941 | 3.303±4.002 |
| **flow_mdk（6L+MDK）** | **0.359 / 0.849 / 0.379** | **0.529±0.277** | **0.778 / 0.452 / 0.373** | **0.534±0.214** |
| ssgc（6L 对称） | 0.324 / 3.460 / 1.676 | 1.820±1.573 | 1.957 / 0.525 / 1.382 | 1.288±0.721 |

KS（逐场景，合并三种子）全部显著：last.pt flow_mdk vs ssgc p=1.3e-11 /
vs swegnn p=1.1e-08 / ssgc vs swegnn p=5.6e-04；best.pt 对应 p=6.1e-13 /
2.2e-22 / 2.6e-04。CSI@0.05（last 均值）flow_mdk 0.656 vs ssgc 0.437 vs
swegnn 0.367。要点：

1. **E4 的 ×5 优势三种子钉死，flow_mdk = 唯一跨协议/跨种子稳固的模型**：
   双协议均值、中位数、KS 全部最优，last≈best（0.529 vs 0.534）——数字对
   选点协议免疫；6 个 run 全落 0.36–0.85 m（跨度 2.4×），ssgc 10.7×、
   swegnn 17.9×。
2. **E4 单种子「ssgc ≈ flow_mdk」不复现**：ssgc s1/s2 恶化到 3.46/1.68，
   best.pt 反转消失。定向 vs 对称在多种子下偏向定向版（仍非逐种子干净
   扫掠，s0 last ssgc 更优）——表述收口为「**定向门控 = 门控系中唯一跨
   种子/跨协议稳固的形态**」；课题主张不变，定向性从「探索性对照」升级为
   「2D 域内稳定性优势」。
3. **swegnn s1 是坏种子而非选点问题**（best.pt 同差 7.92，val 平台 0.0181
   vs 门控系 0.0155–0.0164）——浅层多跳骨架在 2D 的训练成功率本身不稳；
   E4 单种子 1.818 恰在三种子中位。E6「单 run 数字不可信」在 2D 同样成立，
   只是 last.pt 受损者恰为无门控基线。
4. 机理信号随种子保持：末层 Dirichlet 能量（合并均值）swegnn 3.61 vs
   flow_mdk 0.013 / ssgc 0.062，约两个数量级分离不变。
5. 剩余局限收窄为一条：合成 4096 节点网格、无真实 2D 考卷（wqh_2d/mdx_2d
   65k 节点需图分块/下采样，L12 剩余项）。

详见 [`docs/results_partA_swe.md`](../docs/results_partA_swe.md) E5 节与
`docs/L4_report.md` MS4_2d/ptbest 节。

## 三、课题状态与下一步

- **M2 证据链全部收口**（E1–E6 + 2D 三种子），主张「MDK 门控混合 = 稳定
  深传播机制」三条证据腿均为多种子稳固结论；M2 仅剩大 Δt 权衡实验（可选
  排期）。M3 剩真实 2D 考卷一项。
- 下一步优先级（建议）：
  1. **L12 剩余：真实 2D 考卷接入**（论文核心卖点 synthetic→real gap 的
     2D 腿）——wqh_2d/mdx_2d 65k 节点，先做零样本评测（E4/E5 已训 9 个
     2D模型直接考，无需重训），图分块或子采样推理；再决定是否需要小规模
     fine-tune。
  2. **大 Δt 实验（M2 收口）**：层/k 与时间步权衡曲线（SWE-GNN Fig.8
     同构），1D 小域即可，脚本待写。
  3. **E6.1 服务器验证**：`ema_after_curriculum` 尚无服务器 run 验证，
     搭下一批训练顺带开一臂。
  4. 之后进入 M4（1D-2D 耦合异构图）或 M5 论文骨架（Pareto/KS/泛化矩阵
     工具链已备）。
- 照旧挂起：L6（mdx 家族补 50）、L9（加速比基线补全）、L8（mdx_downstream
  排查）、λ₀ 曲线图多种子刷新（低优先）。
