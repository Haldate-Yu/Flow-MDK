# 进展日志 · 2026-09-18

> 总览、里程碑状态与待办清单见 [`PLAN.md`](PLAN.md)。本日为 **round 4
> 取回日**：无新训练 run——纯数据生产轮按计划落地，**M4 v2 耦合家族
> 12/12 构建成功**（正式训练数据就绪），L9 修复轮再次失败但根因彻底
> 定位并已在本地修复。主线判定不变：**M5 论文初稿是唯一主线**。

## 一、runs 取回与入库（`runs_server_260918_v1`）

- **无新训练 run 目录**；入库内容 = ①40 个 `eval_val_scenarios_1d.json`
  （→B2 val 评测，L9 step 2 服务器重评）拷入 `runs/`；②registry 合并
  47 行（**621→668**，按时间戳归并零冲突）。
- 刷新 eval 的实质变化**仅限计时字段**：推理 `seconds` 比 round 3 再降
  17–29%（B1v2 flow_mdk s0：mdx 1.67→1.39 s、downstream 0.74→0.53 s、
  zxh 0.22→0.16 s）、`speedup` 相应上调；RMSE/MAE/CSI 逐位不变，
  Dirichlet 仅 ~1e-7 浮点噪声 → **L4_report / Pareto / 泛化矩阵无需
  重生成**（已重跑 `plot_pareto.py` 验证幂等无变化）。
- 勘误记档：drop 里另有 2 个文件（`L2_partA_{gcn,swegnn}/eval_test_
  family_zxh.json`）与仓库不一致——系**服务器侧旧副本**（09-13 01:06，
  早于 L5 Dirichlet 接入），仓库版（09-13 11:04）更新且 RMSE 一致，
  保留仓库版不覆盖；服务器 runs/ 目录与本地存在少量历史漂移，无害。

## 二、M4 v2 · 耦合家族批跑判决（✅ 12/12，正式训练数据就绪）

`build_coupled_family.py --num 12 --seed 11` 服务器纯 CPU 批跑（09-17
23:13 收工，~3.5 h）：

- **12/12 全部成功**：`mdx_chain_fam000–011.npz`，每场景 ~17.5 min
  （下游重建 7–10 s + 2D 重跑 + 组装），65,189 节点 / 31 帧，fam000 =
  基线对拍 draw（等价性已在 round-4 prep 逐字节证明）。
- **扰动空间覆盖设计意图**：q_scale 0.61–1.97 × t_stretch 0.82–1.54
  （B1 家族同款协议）；链 2D 真值 h_max 11.14–12.62 m（最强工况
  fam011：q_scale 1.97），出口 Q 356–2203 m³/s 覆盖 v1 范围。
- **工件在服务器端**：`data/real_cases/coupled_chain/mdx_chain_fam*/
  *.npz` + 逐场景 report（`coupled_family_report.json`）——**下次取回
  时顺带 scp report json**（小文件，本地核验用；npz 留服务器供训练）。
- **缺口**：家族无 `split.json`（v1 脚本只写过单场景全 split 版）——
  round 5 训练前需补（建议 9/1/2，fam000 基线对拍放 test 便于与 v1
  直连对照）。

## 三、L9 · 修复轮判决（5/5 格已填；4 例口径待服务器权威化；本地已修）

服务器 round 4（09-17 19:35–19:40，模板 scp 后重跑 `run_L9_speedup_
baselines.sh`）：

1. **step 1 仍失败 4/5**——preflight 修复不彻底，根因细化：存的是
   Windows 风格路径，在 Linux 上**既不解析也不拆组件**——
   `Path.name` 对 `D:\...\telemac1d\mdx` 返回整个字符串、
   `data\real_sources\wqh` 是单个组件，旧回退 `data/real_sources /
   src.name` 拼出 `data/real_sources/D:\...\mdx` 与
   `data/real_sources/data\real_sources\wqh` 两类垃圾路径（日志逐条
   印证）。仅 mdx_downstream 成功（npz 重建路线不读 source）：
   **13.2 s**（服务器权威，覆盖 round 3 的 12.7 s）。
2. **step 2 全量成功**：47 条 →B2 (val) eval 刷新（见第一节）。
3. **speedup 五格全部有值**，混合口径如实记档：mdx_downstream =
   服务器 13.2 s（权威）；mdx 48.7 / mdx_upstream 23.4 / wqh 22.5 /
   zxh 30.8 = 本地 WSL2 计时（保守下界，本地比服务器慢 ~4.5×，即这
   4 格的 speedup 被低估约 4.5×；`runtime_source` 标签区分）。全 47
   条 eval 范围：mdx 11–66× / downstream 13–132× / upstream 23–190× /
   wqh 10–178× / zxh 65–510×。
4. **本地修复（本日）**：`time_b2_solver.py` 预处理重写——分隔符
   归一化（`\`→`/`）+ 四层候选（原值 / 仓库相对 / `data/real_sources/
   <名>` 平铺 / 保留父目录）+ 存储统一 `as_posix()` + 无需 source 的
   case（mdx_downstream）跳过 preflight；新增
   `tests/test_time_b2_solver.py` **10 项单测**（含 round-4 两个失败
   场景复现用例），全套 54 项通过；本地 5 例 npz meta 已就地归一化
   （wqh/zxh → `data/real_sources/*` POSIX 相对，mdx/upstream → 前斜杠
   绝对）。**round 5 服务器只需同步脚本重跑**，模板已就位。

## 四、课题状态

- **M1/M2/M3 ✅；M5 实验腿全部闭合**（主表 + 消融 + U-Net + 泛化矩阵
  + Pareto + 方法学三件套），L9 效率表 5/5 格有值（4 例保守）——
  **论文初稿仍是唯一主线，且不再有任何阻塞项**。
- **M4 ◐**：数据骨架 + v1 真值 + 可行性三种子 + **v2 家族 12 场景 ✅**；
  剩 = 接口守恒损失 + K 物理匹配两项代码 + split + round 5 训练。

## 五、下一步（round 5 规划，建议优先级）

1. **M5 论文初稿（最高优先，本地，不依赖 round 5）**：结构 + F1–F7
   图表清单落地；主张口径 = 深传播 harness 主载体 + 定向 MDK 稳定增量
   （L16）+ 定向唯一可用形态；1D 诚实排位；方法学节（E6/E6.1 选点治理
   + 单种子不可信）；U-Net 行 + 泛化矩阵留空注记；效率表引 L9 现值
   （4 例标保守下界，round 5 后换权威值，写作不受阻）。
2. **M4 v2 正式训练轮（round 5 服务器主任务）**，本地先行三件事：
   - **split.json**（9/1/2，fam000 入 test）；
   - **接口边通量守恒损失项**（v1 链接口边簿记已有，损失项设计 =
     1D 末端 Q 与 2D 入口通量的质量失衡惩罚，需核对 npz 的
     `edge_flow` 接口边真值可用性）；
   - **K=√(2DΔt)/dx̄ 物理匹配**（链家族 Δt=1800 s 固定，dx̄ 从图几何
     计算；替代 v1 的 K=2 论文缺省）；
   - 训练配方沿用 v1 可行性轮 + 短预算修正（ema 0.999→0.99）+
     E6 选点治理；臂 = flow_mdk × 3 种子（swegnn/ssgc 耦合对照为
     可选扩展，v1 只有 flow_mdk）。
3. **L9 收口（round 5 顺带，~30 min）**：同步修复后
   `time_b2_solver.py` → 服务器重跑 `--all` + step 2 → 4 例换权威
   计时、效率表定稿。
4. 取回清单：`coupled_family_report.json` + M4 v2 训练 runs + L9
   权威计时；照旧挂起 L6/2D 真实母版微调（可选）。

## 六、round 5 准备落地（同日第十轮：M4 v2 训练臂三件套全部实现）

1. **接口边通量守恒损失项**（`train.interface_cons_weight`，默认 0 关闭）：
   - **设计探索如实记档**：储量恒等式（Σ A_v·Δh/Δt = Q_in − Q_out）在
     1800s 子采样帧上**不闭合**（残差与通量同量级——2D 出流 Z=280 边界
     的符号通量未保留进 npz，无法复算 Solver 内部账目）；界面通量恒等式
     `Q_chain_exit = Σ_v |q|_v·ℓ_v` **可用**：入口段总长从真值反推
     L≈336 m（跨步 CV 14%），且该损失是**预测侧自洽约束**（比较模型
     自己的 1D 侧 Q 与 2D 侧 |q| 通量，真值只标定 ℓ 不进损失项），真值
     噪声不产生偏置。出流界面（mesh→chain）边界节点 |q|≈0 无信号，
     自动跳过——守恒项单侧生效，如实记档。
   - 实现：`extract_interfaces`（dataset.py）逐场景自动标定 ℓ（湿步
     中位数、无信号/湿步不足自动跳过）；collate 统一性检查（混合 split
     自动禁用）；`multistep_rollout_loss` 每步对 mask 后状态加罚；
     **仅训练侧启用**（val 保持纯数据损失，best.pt 选择跨臂可比）。
   - 测试：10 项新单测（ℓ 恢复、真值零罚、逐 item 索引、混合禁用、
     端到端冒烟、真实链标定门限），全套 64 项通过；真实 v1 链标定
     ℓ=19.79 m/节点（=336 m/17，与 25 m 占位几何量级相容）。
2. **家族数据根** `prepare_coupled_family_root.py`：把服务器端逐场景
   子目录平铺为 `coupled_chain_family/*.npz`（符号链接/拷贝幂等）+
   写 split.json（**9/1/2：train fam001–009 / val fam010 / test
   fam000+fam011**——fam000 为 v1 对拍 draw 入 test 直连 v1 可行性轮，
   fam011 最强工况 q_scale 1.97 同入 test）。v1 根不动。
3. **训练脚本** `run_M4_v2_family.sh`：三臂 × 3 种子——
   `main`（flow_mdk **K=4** + cons 0.1）/ `nocons`（K=4 消融）/ `swegnn`
   （official 2L×8 对照）；E6 配方（val_horizon=8 + 课程后早停 + EMA）+
   **ema 0.99**（v1 短预算修正）。K=4 = ceil(2·√(1800/647)) ≈ L14 的
   m=3→K4 同款映射（混合 1D/2D 边缘分辨率的 dx̄ 限定如实记档）；swegnn
   臂用 `1d_swegnn_official.yaml`（先误指 baseline 6L -MDK，已修正）。
   预算 ~2.5 h/run（A100，60 ep × ~50 batch），9 run 串行 ~22 h，可
   ARMS/SEEDS 分 GPU 并行。
4. **服务器执行序**：L9 重跑（快）→ M4 v2 三臂（长）；同步清单 =
   time_b2_solver.py（上轮修复）+ 本轮 scripts/prepare_coupled_family_
   root.py、scripts/run_M4_v2_family.sh + src/flow_mdk/{config,data/
   dataset,train/loss,train/trainer}。

## 七、round 5 执行发现（main/nocons 完成，swegnn OOM 三连——脚本两处修复）

- **swegnn 臂 batch 4 在 65k 节点耦合图上 OOM**（单进程 torch 已分配
  55.3 GiB 时再要 382 MiB 失败，卡上另有 ~22 GiB 其他租户）：2L×8 =
  16 跳消息传递，逐跳激活沿**边维**（389,928 × batch）堆积——E5 时代
  swegnn 只训过 4k 节点合成网格，这是该骨架第一次上 65k 节点图，
  激活足迹是 flow_mdk（6 跳 + MDK 稀疏扩散）的数倍。**处置：swegnn 臂
  `BATCH_SIZE=2` 重跑**（激活减半 ~28–30 GiB，余量充足）——协议混杂
  如实记档：swegnn 对照 batch 2 vs main/nocons batch 4（同 lr 下基线
  略吃亏，方向对 flow_mdk 有利，论文 M4 节必须披露）；60 ep × 99 步
  wall-clock 与 batch 4 基本持平。
- **`run_M4_v2_family.sh` 两处修复**：①`set -eo pipefail`——原
  `set -e` 管不住 `| tail` 管道，训练 OOM 后仍继续跑 eval 并「成功」
  跑完三个种子；②跳过条件从 `config.yaml` 存在改为 **`last.pt` 存在**
  ——崩溃的 run 只留 config.yaml（训练前 stamp），按旧条件会被误跳，
  现在自愈重跑，**无需手动清理服务器上的三个失败目录**。同批附带
  prepare 脚本 symlink 竞态加固（FileExistsError 容忍，并发启动安全）。
