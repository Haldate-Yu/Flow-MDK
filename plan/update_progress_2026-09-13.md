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

## 五、与服务器 L4 的衔接

- 服务器训练进行中；其 history.json 自带 mdk_lambda0（trainer 已记录），
  eval 时将带 dirichlet 字段（若服务器代码为本次更新后版本；否则取回后本地
  富评）。
- runs/ 取回后：`python scripts/summarize_runs.py --prefix partA_paper
  --prefix L3_B1_paper --ks --out-md docs/L4_report.md` 一条命令出报告；
  两机 results.csv 直接拼接合并（时间戳目录不撞名）。

## 六、遗留与下一步

1. ~~L11 verdict~~ ✅ 当日关闭：三家族真值逐位一致，B1 无需重训。
2. **L4 报告**（runs/ 取回后）：summarize 出表 → 复测 L2/L3 结论 → 更新
   docs 结果报告与 PLAN。
3. **多种子**（本日启动，后台）：MS_partA / MS_B1 三种子组完成后出
   mean±std 结论（关键判据：GCN 域内优势与 Flow-MDK/SSGC 差距是否跨种子
   稳定）。
4. L6（mdx 补 3 例被淘汰场景——补丁内核下可能复活）已无决策障碍，可选。
5. L9（B2 加速比基线）仍待补；L10 提交事项本日已全部完成（待推送）。
