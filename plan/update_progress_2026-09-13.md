# 进展日志 · 2026-09-13

> 总览、里程碑状态与待办清单见 [`PLAN.md`](PLAN.md)。本日为收尾/工具日：仓库
> 归档补全、L5 监控接入、L4 分析工具、L11 真值差异评估启动；服务器 L4 论文
> 预算训练同步进行中。

## 一、仓库归档补全（接 09-12 遗留）

- 排查发现 README "archive refresh pending" 备注过时：117 场景家族与 B2 考卷
  实际早已入库，真实缺口为 `partA_v2`（130 npz + 3 json，4.5 MB）与 L2/L3 run
  归档；v1 run 的 `.pt` 停在训练中途（归档早于 18:50/18:57 的 checkpoint），
  本次一并修正为最终权重。
- `scripts/archive_datasets.py` 修复三处回归后才可重跑：swegnn/real_projects/
  telemac/docker_images 改为「就地计数」（datasets/ 内即正本，不重拷、MANIFEST
  行不丢）；`repo`/`origin` 写固定标签（不再写回本机绝对路径）；新增 `partA_v2`
  条目与缺失的 `validation_wqh.json`。
- 归档刷新提交（9330 文件 / 7.45 GB；LFS 增量 ~10 MB）。

## 二、L5 · over-smoothing 监控接入评测 ✅

- `eval/rollout.py`：`attach_dirichlet_monitor()` 用 forward hooks 在传播层上
  逐层记录 Dirichlet 能量（逐边归一、rollout 步均值），Flow-MDK 系
  （`processor.layers`）与 GCN/GAT 基线（`convs`）两条路径通吃；
  `scripts/evaluate.py` 将其写入 eval json（`dirichlet` 字段，旧 json 兼容）。
- `scripts/plot_mdk_lambda0.py`（新）：history.json 的 λ₀ 日志 → 曲线 PNG/CSV
  + 首/末 epoch 表。
- 首轮冒烟信号：`L2_partA_flow_mdk` 末层 λ₀ 训练中 0.42→0.09（MDK 深层平滑
  加深的直接证据）；GCN 逐层能量 1e5→2e8 随深度增长（残差累积，无塌缩）。
- 表示相似度指标未实现（可选项，不再单列待办）。服务器 L4 返回的 checkpoint
  可用新代码事后富评，无需重训。

## 三、L4 分析工具 · summarize_runs.py

- `--prefix` 分组（L2/L3 链永不并表）→ 域内/零样本 RMSE 表、退化倍数矩阵、
  B2 逐考卷表、逐场景 RMSE 的两两 KS 检验、（L5 runs）末层 Dirichlet 能量。
- 域标签取自 results.csv 登记行；早于登记表功能的 run 回退 config.yaml 取
  data.root/架构/epoch。in-domain 按 data_root 相等判定（A2/A3 单独 eval 的
  标签前缀会误判，已避开）。
- 数字与 `docs/results_partA_swe.md` 手工表全部对上（A-test 0.794/0.827/
  1.422/4.496；B1 0.830/0.798/1.954；B2 均值 1.669/1.826/2.448）。

## 四、L11 · 真实家族补丁内核真值差异评估（启动）

- 工具：`run_real_family.py` 增 `--runs-root`（workdir 重定向，不碰已验证
  workdir）与 `--force`（仅限 scratch 副本使用）；`scripts/compare_family_truth.py`
  （新）逐场景 h/Q-RMSE、max|dh|、bias 对比 + verdict，以 scratch 的
  run_report.json 为"实际跑过"的权威（scratch npz 本是字节副本，npz 自身
  无法区分未跑/跑过）。
- 冒烟：zxh_fam000 补丁内核重跑与验证真值**逐位一致**（h-RMSE 精确 0.0）。
- **全量结果（当日批跑完成）：117/117 场景重跑成功、新旧真值逐位一致**
  （zxh 40 + mdx 37 + wqh 40，max h-RMSE = 0.0，max|dh| = 0.0，零失败）。
  已验证的 B1/B2 真值不受内核缺陷影响——真实家族在旧内核下侥幸全部命中
  良性堆布局（对比 Part A 的 81/89 场景 ≤0.16 m 修正，污染是堆布局依赖的
  偶然事件）；家族重跑不必要，**L11 关闭**，L2/L3 结论在干净地基上成立。
  衍生可选项：mdx 3 例被淘汰场景可在补丁内核下尝试复活（L6）。

## 五、多种子复制（三线之三，当日完成）

`run_multiseed_local.sh`：种子 0/1/2 × {Part A: swegnn/flow_mdk/gcn；B1→B2:
swegnn/flow_mdk/ssgc}，预算与单种子链完全一致（G=32/40ep），18 个 run 零失败。

**Part A（A-test h-RMSE，逐种子）**：

| 模型 | s0 | s1 | s2 | mean±std |
|---|---|---|---|---|
| gcn | 0.79 | 1.01 | 0.75 | **0.85±0.14** |
| flow_mdk | 1.42 | **5.91** | 0.77 | 2.70±2.80 |
| swegnn | 4.50 | 1.23 | 4.26 | 3.33±1.82 |

- **GCN 域内优势跨种子稳固**（0.75–1.01）；flow_mdk 呈双峰：s2 追平 GCN
  （0.77 vs 0.75，架构能力存在）、s1 崩坏（5.91）——**种子方差本身成为主要
  发现**。swegnn 同样不稳定。
- 单种子版的 ×3.2 拯救效应**未跨种子复现**（按种子配对 s1 反转）；fam_mdx
  零样本"Flow-MDK 最优"也未复现（s1/s2 = 11.2/11.7 vs gcn 2.5–3.8）。
- **λ₀ 诊断**：三个种子的门控轨迹几乎相同（末层 0.42→0.09–0.14）→ 不稳定
  不在 MDK 门控，而在 flow_mdk/swegnn **共享的 ψ 差值消息主干**；GCN 是唯一
  稳定模型。MDK 既非病因也非解药；落点好的种子与 GCN 竞争力相当。

**B1→B2（定向性问题，三种子）**：

| 模型 | B1 域内 | →B2 均值 | mdx_upstream |
|---|---|---|---|
| swegnn | 0.915±0.081 | **1.690±0.031** | 1.765 |
| ssgc | 0.962±0.309 | 1.803±0.122 | 1.706 |
| flow_mdk | 1.210±0.647 | 2.090±0.351 | **1.353** |

- 定向性仍未赢过对称核（SSGC）；唯一持久的定向信号是 mdx_upstream（耦合链
  考卷）flow_mdk 三种子均值最优。
- 判决树位置更新：本地预算下介于"中间"与"最坏"之间。**决定性实验升级为
  "论文预算下主干能否稳定"**——L4（单种子）给一个抽样；建议 L4 后服务器补
  3 种子 × 论文预算（A100 每 run 1–2 h）。
- 无论架构结论如何都稳固的贡献：数据集 + 内核修复 + 诚实的多种子评测方法
  （方差表本身即发现）。

## 六、M3 开线 · 真实 2D 工程真值（下午续）

- **模板完整度超预期**：`datasets/real_projects/telemac2d/{wqh,mdx}` 渲染版
  `.cas` + 边界 `.cli` + 几何 + 源项全部齐备（`.ftl` 仅 3 个时间占位符），
  镜像内 `telemac2d` 二进制现成——L7 所虑的 `.cli` 生成只是合成场景族的事。
- **预期修正**：模板 `old.slf` 是单帧初始化快照而非历史结果档案 → 2D 无
  1D 式逐位复现校验；定位改为**重跑即真值 + 物理门控**（质量守恒、深度/
  湿区/NaN）。
- 冒烟（20 步）两工程均一次通过；全量真值当日完成：

| 工程 | 工况 | 帧 @ 600s | h 范围 m | q_max m/s | 湿区 | 体积守恒 \|ε\| |
|---|---|---|---|---|---|---|
| wqh_2d | 25 h（5s×18000 步） | 151 | 0–19.6 | 39.9 | 0.26→0.46 | 7.3e-15 |
| mdx_2d | 15 h（2s×27000 步） | 91 | 0–17.0 | 17.9 | 0.34→0.39 | 5.4e-15 |

- 配方：`telemac2d.py --ncsize=4`（本机 docker，单工程 ~1.5 h）；摄取
  `scripts/ingest_telemac2d_truth.py`（WATER DEPTH + (U,V)→|q| 挂 npz，
  solver 翻转 `telemac2d_docker_rerun`，QC 报告存 `telemac2d_runs/*/`）。
  B2 的 mdx_upstream/downstream 仍是独立 1D 腿；真耦合（M4）未动。

## 七、与服务器 L4 的衔接

- 服务器训练进行中；其 history.json 自带 mdk_lambda0（trainer 已记录），
  eval 时将带 dirichlet 字段（若服务器代码为本次更新后版本；否则取回后本地
  富评）。
- runs/ 取回后：`python scripts/summarize_runs.py --prefix partA_paper
  --prefix L3_B1_paper --ks --out-md docs/L4_report.md` 一条命令出报告；
  两机 results.csv 直接拼接合并（时间戳目录不撞名）。

## 八、遗留与下一步

1. ~~L11 verdict~~ ✅ 当日关闭：三家族真值逐位一致，B1 无需重训。
2. **L4 报告**（runs/ 取回后）：summarize 出表 → 复测 L2/L3 结论 → 更新
   docs 结果报告与 PLAN。
3. **多种子**（本日启动，后台）：MS_partA / MS_B1 三种子组完成后出
   mean±std 结论（关键判据：GCN 域内优势与 Flow-MDK/SSGC 差距是否跨种子
   稳定）。
4. L6（mdx 补 3 例被淘汰场景——补丁内核下可能复活）已无决策障碍，可选。
5. L9（B2 加速比基线）仍待补；L10 提交事项本日已全部完成（待推送）。
