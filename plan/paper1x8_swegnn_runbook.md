# 1×8 SWE-GNN 补充臂 · 运行手册（仅 2D + 一二维耦合）

> 起草 2026-09-21。目的：把 SWE-GNN 基线对齐到**官方保存的深度配置**，看结论是否变化。
> 新增文件全部是新文件，**没有覆盖任何既有配置或脚本**；既有 `MS4_2d_*` / `M4v2_*` 工件不动。

---

## 1 改动：只有一个变量

| | 官方仓库保存的最优模型 | 我们现有 swegnn 臂 | 本补充臂 |
|---|---|---|---|
| 深度 | `n_GNN_layers: 1` + `K: 8` = **8 次消息传递/步** | `num_message_passing_layers: 2` + `hops_per_layer: 8` = **16 次/步** | **8 次/步** |

其余键逐字保持与各臂现有 run 相同（hidden 64、每层 tanh、lr 0.007/×0.9/7ep、H=8、γ=(1,3)、仅水区掩码、按值裁剪 0.5、batch、课程步长、E6 选点治理、EMA 0.99），所以结果是**单变量对照**。

### 1.1 证据链：为什么 1×8 是论文模型（2026-09-21 复核，五条独立证据）

**E1 · 论文文本**。式 (9) 把处理器定义为**单链**：`h^(0)=h_d·W^(0)`，ℓ=1..L−1 逐层更新，`h^(L)=tanh(…W^(L))` —— 共 **L+1 个矩阵**，**Tanh 只在 L 层末出现一次**，全文没有"第二个外层 block"的概念。§5.1："all hyperparameter searches resulted in similar best configurations, i.e. **L = 8 GNN layers** and an embedding size of G = 64"；表 A1 的搜索超参名就叫 "Number of GNN layers (L)"，范围 1..9，最优 8。L=8 ⇒ W^(0)..W^(8) = **9 个矩阵**。

**E2 · 官方保存的 11 份实验 config**（vendored 副本 = 上游，已交叉验证）。`results/best_models/{,SWEGNN,SWEGNN_ng,GAT,GNN_L}/config.yaml`、`results/Pareto_front/`、`results/training_strategy/*/`：**全部 `n_GNN_layers: 1`、`K: 8`**。`results/GNN_layers_temporal_res/{30,60,90,120}/`：全部 `n_GNN_layers: 1` 而 **K = 2/8/8/8** —— 即图 8 的横坐标"number of GNN layers"就是 K，外层数固定为 1。

**E3 · 论文权重结构（决定性）**。直接加载 `results/best_models/SWEGNN/SWEGNN.h5`（README 明言"used for the paper's results"）：
- `gnn_processor` 只有 **1 个 block**（只有 `gnn_processor.0.*`，无 `.1.*`）；
- `filter_matrix.0 … filter_matrix.8` = **9 个 (64,64) 无偏置矩阵** ↔ 式 (9) 的 W^(0)..W^(8)、L=8；
- `edge_mlp` 为 320→128→64 ↔ ψ: R^5G→R^2G→R^G；
- 键集合与图 8 扫参目录的 `GNN_8.h5` **完全一致**；扫参模型 `GNN_N.h5` 恰有 **N+1 个 filter_matrix**（N=1/2/4/8/12 → 2/3/5/9/13），文件尺寸每加一"层"恰好 +16,765 B ≈ 一个 64×64 float32 矩阵 —— "N 层"严格等于一个 block 内 N 跳。

**E4 · 参数恒等式**（从权重直接数出的官方总参数 = **103,690**）：

| 部件 | 官方 SWEGNN.h5 | 本仓库新臂 1×8 | 旧臂 2×8 |
|---|---|---|---|
| 处理器 | 86,210（ψ 49,346 + 9×4,096） | **86,210（逐参数相同）** | 168,324（**1.95×**） |
| 静态编码器 | 4,482（输入 4 通道） | 4,674（输入 7 通道，+192） | 4,674 |
| 动态/边编码器、解码器 | 4,354 / 4,418 / 4,226 | 4,354 / 4,418 / 4,226（相同） | 同左 |
| **总计** | **103,690** | **103,882 = 103,690 + 192** | 185,996 |

+192 = 静态特征多 3 个通道（area、manning、入流标记；前两个为常数）在第一层 Linear 的权重差 —— 数据层共享布局，正文披露即可。

**E5 · 上游交叉验证**。GitHub 上游 `results/best_models/SWEGNN/config.yaml` = `n_GNN_layers: 1, K: 8`（vendored 副本忠实）；上游**根 config.yaml 不含 `n_GNN_layers` 键** —— 见下条，这正是当初误读的来源。

**结构映射（新臂 ↔ 官方块）**：`processor.lift` ↔ `filter_matrix[0]`（入口 W⁽⁰⁾）；`hop_linears[0..7]` ↔ `filter_matrix[1..8]`；每跳用同一 ψ 在当前状态上重算消息 ↔ 官方块内复用 `edge_mlp`；`mdk.use=false` 时层输出 = 跳链结果；`is_last` → 单次 Tanh ↔ 官方 `n_GNN_layers=1` 的每块一次 Tanh。消息传递次数 8 ↔ 8。

### 1.2 为什么之前的配置是 2×8（根因，留档）

1. **上游根 config.yaml 本身不含 `n_GNN_layers`**：直接 `python main.py` 会吃到类默认值 `n_GNN_layers=2`，训练出 16 跳模型 —— 上游仓库自己埋的坑（出厂可运行配置 ≠ 论文模型）。
2. 2026-09-11 的 `docs/swe_gnn_official_comparison.md` §2 以"类默认值 + 根 config"为据，得出"官方 = 2×8 = 16 次消息传递"，并把忠实复现配置定为 2 层×8 跳。
3. 该文档**没有核对** `results/` 下 11 份实验 config（全部 `n_GNN_layers: 1`）、**没有打开** checkpoint 数 `filter_matrix`（9 个）、也没有用式 (9) 的 W^(0..L) 计数与"单次 Tanh 在 L 层末"做交叉验证。

定性：旧 2×8 臂忠实复现的是"官方代码以出厂默认运行"的形态，不是论文报告的模型；论文全部数字（表 2/3、图 6–10）来自 1×8。正文披露建议写明这一点（含"官方根 config 直接跑会得到 2×8"的说明），以备审稿人对照官方仓库。

**刻意没改的两件事（都写进了配置注释）**：

1. **`early_stop_patience` 保持 99**（= 兄弟臂 `run_M3_2d_paper.sh` 传给所有 2D 臂的值）。论文自己的值是 30；要完全照搬官方协议就跑
   `EXTRA="train.early_stop_patience=30" bash scripts/run_2d_swegnn_official.sh`。
   默认不开启是因为：只给 swegnn 换成 30 会让它的训练预算短于 flow_mdk/ssgc，对照不再干净。
2. **静态特征不动**（我们 2D 是 7 通道：area / elevation / slope_x / slope_y / manning / 入流标记 + 水位；官方只有 DEM + 双向坡降 + 水位）。这属于**数据层共享布局**（`src/flow_mdk/data/features.py` 的 2D layout），不是单臂可开关的键——去掉它意味着所有 2D 臂都要重训。做法是**在正文披露口径差异**，而不是在这里削基线。（顺带一提：入流标记这一通道官方模型是没有的，它可以削弱"未见溃口位置"的难度，这句披露对我们反而有利。）

---

## 2 新增文件清单

| 文件 | 作用 | 跑在哪 |
|---|---|---|
| `configs/2d_swegnn_official.yaml` | 2D 家族的单变量配置（1×8） | 服务器 |
| `configs/coupled_swegnn_official.yaml` | 耦合家族的单变量配置（1×8） | 服务器 |
| `scripts/run_2d_swegnn_official.sh` | 2D 训练 + test 双协议评测 → `runs/MS4b_2d_swegnn_s*` | 服务器 |
| `scripts/run_coupled_swegnn_official.sh` | 耦合训练 + test/best/ema 三协议评测 → `runs/M4v2b_swegnn_s*` | 服务器 |
| `scripts/run_2d_swegnn_exams.sh` | 真实二维考卷评测（**纯推理**，无训练路径） | **本机**（考卷根在本机） |
| `plan/paper1x8_swegnn_runbook.md` | 本文件 | 参考 |

---

## 3 上传到服务器的清单

**必传（4 个文件）**：

```
configs/2d_swegnn_official.yaml
configs/coupled_swegnn_official.yaml
scripts/run_2d_swegnn_official.sh
scripts/run_coupled_swegnn_official.sh
```

**数据不用传**——两套数据都已在服务器上（round 5/6 就是在服务器训的）。上服务器后先核验：

```bash
# 2D 家族：应为 130 个 npz 与 91/19/20 切分（脚本里也有同样的硬门禁）
ls data/scenarios_2d_family/*.npz | wc -l
python -c "import json;print({k:len(v) for k,v in json.load(open('data/scenarios_2d_family/split.json')).items()})"

# 耦合链根：12 个（若 S1 已扩样则是 20 个，两者都可以）
ls -d data/real_cases/coupled_chain/mdx_chain_fam* | wc -l
```

**条件上传**：仅当服务器上 `data/scenarios_2d_family/` 已被清理时才需要从本地/归档补
（本地该目录 130 个 npz 齐全）：

```bash
tar czf scenarios_2d_family.tgz data/scenarios_2d_family   # 本地打包 → 服务器解包
```

**不要传**：`data/real_cases/exams_2d*`（本机构建、本机评测用）、`data/real_cases/coupled_chain_family*`（脚本会在服务器重建）。

> 耦合数据的一个便利点：新脚本用**独立根** `data/real_cases/coupled_chain_family_v2`（npz 是指向同一批文件的符号链接），并把 `split.json` 钉死为 v2 的 9/1/2。所以既不用碰共享根、也**与 S1/M4v3 无先后顺序要求**；即使链根已经被扩到 20 个场景，多出来的 fam012–019 会被自动忽略（`train.py` 只读 `split.json` 里的名单）。

---

## 4 服务器执行

```bash
# 2D（约 1.5–2.5 h/种子；8 跳比 16 跳轻一半）
CUDA_VISIBLE_DEVICES=1 bash scripts/run_2d_swegnn_official.sh 2>&1 \
    | tee data/1x8_2d_$(date +%m%d).log

# 耦合（约 1 h/种子）
CUDA_VISIBLE_DEVICES=0 bash scripts/run_coupled_swegnn_official.sh 2>&1 \
    | tee data/1x8_coupled_$(date +%m%d).log
```

两条可并行分卡跑；都支持断点续跑（跳过判据是 `last.pt`，崩溃留下的 `config.yaml` 不会造成假跳过）。

**降险建议**：先只跑 2D 单种子 —— `SEEDS="0" bash scripts/run_2d_swegnn_official.sh`（~2 h），看 `MS4b_2d_swegnn_s0` 的 2D test RMSE/CSI 与相对 `flow_mdk` 的倍数变化；若变化 <20–30%，再决定是不是要把 3 种子和耦合一起跑完。

**与 S2 的顺序**：S2（128×128 大域零样本评测）要**在本批 2D 重训完成之后**跑，否则它评的还是旧的 2×8 权重（`run_2d_larger_domain.sh` 按 run 目录枚举）。

---

## 5 从服务器取回清单

```
runs/MS4b_2d_swegnn_s{0,1,2}/            含 config.yaml, last.pt, best.pt, history.json, eval_test.json
runs/ptbest_MS4b_2d_swegnn_s{0,1,2}/     含 config.yaml + eval_test.json（best.pt 的控制评测）
runs/M4v2b_swegnn_s{0,1,2}/              含 config.yaml, last.pt, best.pt, ema.pt, history.json, eval_test.json
runs/ptbest_M4v2b_swegnn_s{0,1,2}/
runs/ptema_M4v2b_swegnn_s{0,1,2}/        ← 只在 ema.pt 存在时才生成
runs/results.csv                          registry 追加行（本地保留合并）
data/1x8_2d_*.log  data/1x8_coupled_*.log 运行日志（脚本用 tee 落在 data/）
```

示例（按需改路径/别名）：

```bash
for s in 0 1 2; do
  rsync -av "SERVER:Flow-MDK/runs/MS4b_2d_swegnn_s$s"      ./runs/
  rsync -av "SERVER:Flow-MDK/runs/ptbest_MS4b_2d_swegnn_s$s" ./runs/
  rsync -av "SERVER:Flow-MDK/runs/M4v2b_swegnn_s$s"        ./runs/
  rsync -av "SERVER:Flow-MDK/runs/ptbest_M4v2b_swegnn_s$s" ./runs/
  rsync -av "SERVER:Flow-MDK/runs/ptema_M4v2b_swegnn_s$s"  ./runs/
done
rsync -av SERVER:Flow-MDK/runs/results.csv ./runs/
```

**不要拉**：真值数据（2D 家族真值本地已有；耦合真值由服务器脚本重建）。

---

## 6 拉回之后的本地步骤

1. **真实二维考卷零样本评测**（纯推理，本机 3060，~1 h）：

   ```bash
   bash scripts/run_2d_swegnn_exams.sh
   ```
   产出 `runs/MS4b_2d_swegnn_s*/eval_test_exams_2d{,_h8}.json` 与 best twin 的同名 json。
   想做前后对照可带上旧臂：`RUNS="runs/MS4_2d_swegnn_s0" bash scripts/run_2d_swegnn_exams.sh`。

2. **S3 全时程轨迹证据重算**（新旧基线并列最直观）：

   ```bash
   python scripts/analyze_exam_trajectories.py --scenario mdx_2d \
     --out runs/exam_trajectories_mdx_2d_1x8.png --refresh \
     --runs "flow_mdk（定向）=runs/MS4_2d_flow_mdk_s0" \
            "swegnn（官方1x8）=runs/MS4b_2d_swegnn_s0" \
            "swegnn（旧2x8）=runs/MS4_2d_swegnn_s0" \
            "ssgc（对称）=runs/MS4_2d_ssgc_s0" \
            "-MDK（无扩散分支）=runs/L16_mdkoff_2d_s0" \
            "gcn（vanilla）=runs/MS4_2d_gcn_s0" \
            "gat（vanilla）=runs/MS4_2d_gat_s0"
   ```

3. **主表 / 方差的汇总**：`python scripts/summarize_runs.py --prefix MS4b_2d --ks`（耦合用 `--prefix M4v2b`）。

4. **两处白名单（不做则新臂被静默排除 —— 这正是 B1 v1/v2 踩过的坑）**：

   - `scripts/build_generalization_matrix.py` 的 `FAMILIES`（约 73 行）加一行，建议**两代分列**而不是并入原模型名：
     ```python
     (re.compile(r"^MS4b_2d_(swegnn)_s\d+$"), "swegnn(1x8)"),
     ```
   - `scripts/plot_pareto.py` 的 2D 面板（约 41 行）：`"prefixes": ("MS4_2d_", "MS4b_2d_")`，并在同面板 `"models"` 里加上 `"swegnn(1x8)"`。
     （`plot_pareto.py` 是从 `build_generalization_matrix` 导入 `parse_run` 的，所以模型名映射只要改前者。）

   改完重跑：`python scripts/build_generalization_matrix.py` 与 `python scripts/plot_pareto.py`。

---

## 7 陷阱清单

| # | 陷阱 | 为什么 / 已如何处理 |
|---|---|---|
| 1 | **必须用新 run 前缀** | 两个训练脚本都以 `last.pt` 存在作为跳过判据；沿用旧名会直接跳过。本套用 `MS4b_2d_*` / `M4v2b_*`。 |
| 2 | **耦合切分会被覆写** | `prepare_coupled_family_root.py` 会重写根的 `split.json`，且默认 train = "链根里所有 fam* 减去 test/val"。新脚本因此使用**独立根 + 钉死 9/1/2**，不再受 S1 扩样影响。 |
| 3 | **`data.name` 不能改** | 耦合臂沿用 `1d_chain`；`train.py` 用名字前缀决定高程通道索引（1d→0，否则→1）。改成别的值会静默破坏 rollout 中的水位刷新。 |
| 4 | **白名单静默排除** | 见 §6.4；不改的话 `results.csv` 里有行，但矩阵/Pareto 里不出现。 |
| 5 | **不要在共享耦合根上跑本例** | 会破坏 S1 需要的 13/2/5 切分（独立根已规避）。 |
| 6 | **2D 的 batch 8 无 OOM 风险** | 8 跳比 16 跳轻，显存低于既有的 swegnn run。 |
| 7 | **EMA 评测依赖 `ema.pt`** | 脚本已做存在性判断，缺失就跳过 `ptema` 而不是报错。 |

---

## 8 预算

| 阶段 | 耗时 |
|---|---|
| 2D 训练 3 种子（8 跳） | ~5–8 h（现 16 跳为 15.5 h） |
| 耦合训练 3 种子（8 跳） | ~3 h（现为 6 h） |
| 本机考卷评测（2 装置 × 双协议 × 3 种子） | ~1 h |
| 轨迹重算 + 汇总 + 图表白名单重生成 | ~1–1.5 h |
| **合计** | **训练 ~10–11 h GPU + 本地 ~2.5 h** |
| （降险）仅 2D 单种子 | 训练 ~2 h + 本地 ~0.5 h |
