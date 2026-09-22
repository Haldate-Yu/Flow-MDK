# Flow-MDK（纯二维版）

**Flow-MDK** (Flow-directed **M**arkov **D**iffusion **K**ernel networks) is a graph-neural-network surrogate for **two-dimensional shallow-water (flood) solvers**. It adapts the hydraulics-based architecture of [SWE-GNN (Bentivoglio et al., HESS 2023)](https://hess.copernicus.org/articles/27/4227/2023/) by replacing its symmetric message passing with a **flow-directed Markov Diffusion Kernel** [(S2GC, Zhu & Koniusz, ICLR 2021)](https://arxiv.org/abs/2002.07972) propagation scheme, combined with an **advection–diffusion operator splitting**: directional difference-based messages carry wave/advection dynamics, while the MDK filter carries diffusive backwater effects with a physically matched receptive field.

> **Scope of this branch (`2d-only`)**: only the 2D data domain — the synthetic
> breach family (130 scenarios, 6.4 km / 64×64), the 12.8 km / 128×128
> larger-domain zero-shot set (24 scenarios), and the two real TELEMAC-2D exam
> cases (`wqh_2d`, `mdx_2d`). The 1D-river and coupled 1D–2D tracks live on the
> `main` branch; the claims, arms and protocol here are exactly those of the
> pure-2D paper deck (组内汇报 2026-09-22 纯二维 v2) and
> [`plan/paper_skeleton_2D_only.md`](plan/paper_skeleton_2D_only.md).

Key design choices:

- **Physics-matched propagation range** — the MDK series truncation is set by the physical diffusion length √(2DΔt), mirroring how SWE-GNN ties layer count to the CFL condition;
- **Directionality preserved** — a hydraulics-weighted (discharge) directed transition matrix replaces the symmetric normalized adjacency; dry cells never relay diffusion;
- **Dry/wet safety** — per-step renormalization as wet/dry edges evolve, and bias-free dynamic encoders so dry cells stay dry;
- **Residual spectral filtering** — the MDK filter acts on *increments*, not absolute states; the λ₀·I identity term caps smoothing depth (anti-over-smoothing by construction), so the untrained model starts exactly at the persistence floor.

Ground truth is generated with **TELEMAC-2D** (docker, `datasets/telemac-mascaret-v8p4r0/`). Evaluation follows the SWE-GNN protocol — RMSE/MAE on water depth and unit discharge, wet-cell CSI, speed-up — extended with the forecast-verification **no-skill gate**: every arm is compared against a zero-parameter **persistence floor** (freeze the last input frame). Arms on this branch: Flow-MDK, SWE-GNN (official 1×8 depth + legacy 2×8), GCN, GAT, U-Net, SSGC (symmetric-MDK ablation), the depth-matched -MDK ablation, and persistence.

**中文说明**

**Flow-MDK** 是面向**二维浅水（溃水/漫滩）求解器**的图神经网络代理模型。方法在 [SWE-GNN（Bentivoglio 等，HESS 2023）](https://hess.copernicus.org/articles/27/4227/2023/)的水力同构架构基础上，将对称消息传播替换为**水力定向的马尔可夫扩散核（MDK）**[（S2GC，Zhu & Koniusz，ICLR 2021）](https://arxiv.org/abs/2002.07972)，并采用**对流-扩散算子分裂**：有向差值消息承载波动/对流动力学，MDK 滤波承载扩散性回水效应。

> **本分支（`2d-only`）范围**：仅保留二维数据域——合成溃口家族 130 场景（6.4 km / 64×64）、
> 12.8 km / 128×128 大域零样本集 24 场景、真实 TELEMAC-2D 考卷 2 例（`wqh_2d`、`mdx_2d`）。
> 一维河网与一二维耦合轨道留在 `main` 分支；本分支的主张、对比臂与评测协议与
> 纯二维汇报 PPT（2026-09-22 v2）及 [`plan/paper_skeleton_2D_only.md`](plan/paper_skeleton_2D_only.md) 严格一致。

核心设计：

- **传播范围物理匹配**——MDK 级数截断由扩散长度 √(2DΔt) 决定，对应 SWE-GNN 中层数与 CFL 的绑定关系；
- **保留方向性**——以流量加权的有向转移矩阵替代对称邻接，干节点不中继扩散；
- **干湿安全**——干湿边演化时逐步重归一化，动态 encoder 无偏置项，干单元恒不产流；
- **残差式谱滤波**——MDK 滤波作用于增量而非状态本身，λ₀·I 恒等项限制平滑深度（未训练即等于 persistence 地板）。

真值由 **TELEMAC-2D**（docker）批量生成；评测沿用 SWE-GNN 协议（水深与单宽流量 RMSE/MAE、湿区 CSI、加速比），并引入预报验证学的 **no-skill 门槛**：所有臂与零参数 **persistence 地板**（冻结末一帧输入）配对比较。本分支八条臂：Flow-MDK、SWE-GNN（官方 1×8 深度 + 旧 2×8）、GCN、GAT、U-Net、SSGC（对称消融）、-MDK 深度匹配消融、persistence 地板。

---

## Repository layout

```
Flow-MDK/
├── plan/paper_skeleton_2D_only.md   # paper skeleton (the scope definition of this branch)
├── references/                      # background papers (see references/README.md)
├── configs/2d_*.yaml                # one config per arm (all arms share the harness)
├── src/flow_mdk/
│   ├── layers/                      # MDK propagation, ψ difference message, operator-split layer
│   ├── models/                      # encoders (bias-free dynamic), processor, decoder, rollout wrapper
│   ├── baselines/                   # GCN / GAT / U-Net / persistence (see its README)
│   ├── data/                        # 2D dual graph, features, npz dataset, dry-wet topology
│   ├── train/                       # recursive multistep loss, curriculum, trainer
│   ├── eval/                        # RMSE/MAE/CSI, Dirichlet energy, rollout evaluation
│   ├── gen/                         # 2D Perlin-DEM scenario family
│   └── utils/                       # seeding, io (npz schema), logging
├── scripts/                         # scenario generation, TELEMAC-2D runner, train/evaluate CLI,
│                                    #   2D experiment runners, exam builders, rendering exports
├── docs/                            # experiment records (generalization matrix, pareto, partA log)
├── tests/                           # unit + 2D end-to-end smoke tests
├── third_party/telemac/             # how to link the local TELEMAC-MASCARET tree / docker image
└── data/                            # generated datasets & checkpoints (git-ignored)
```

## Quickstart

```bash
pip install -e .

# 1. generate the synthetic 2D breach family (TELEMAC-2D truth attached per scenario)
python scripts/generate_scenarios_2d_family.py --out data/scenarios_2d_family --num 130 \
    --nx 64 --ny 64 --cell-size 100 --split-mode paper
python scripts/run_telemac2d_docker.py --scenario data/scenarios_2d_family/T2D_000.npz \
    --workdir data/scenarios_2d_family/_work/T2D_000

# 2. train an arm (swap the config for swegnn / ssgc / gcn / gat / unet / -MDK ablation)
python scripts/train.py --config configs/2d_flow_mdk.yaml

# 3. evaluate on the test split (RMSE / MAE / CSI / speed-up)
python scripts/evaluate.py --config runs/2d_flow_mdk/config.yaml \
    --checkpoint runs/2d_flow_mdk/last.pt --split test

# 4. persistence floor rows (no-skill reference; all three 2D roots)
bash scripts/run_2d_persistence_floor.sh

# 5. larger-domain zero-shot set (12.8 km / 128×128, 24 scenarios, truth + eval)
bash scripts/run_2d_larger_domain.sh

# 6. real-2D exam roots + zero-shot evals (training view H=8 and full horizon)
python scripts/build_real_2d_exam.py
bash scripts/run_M3_2d_exams.sh
```

## Data roots (git-ignored; produced by the scripts above)

| root | content | used for |
|---|---|---|
| `data/scenarios_2d_family` | 130 scenarios, 64×64 @ 100 m, split 91/19/20 | in-domain training + test |
| `data/scenarios_2d_larger` | 24 scenarios, 128×128 @ 100 m, all-test | zero-shot domain-size axis |
| `data/real_cases/exams_2d` / `_h8` | `wqh_2d` + `mdx_2d` (65,126-node unstructured meshes) | zero-shot real transfer |

## Attribution

If you use this work, please also cite the two pillars it builds on:

- Bentivoglio, R., Isufi, E., Jonkman, S. N., Taormina, R.: *Rapid spatio-temporal flood modelling via hydraulics-based graph neural networks*, HESS, 27, 4227–4246, 2023.
- Zhu, H., Koniusz, P.: *Simple Spectral Graph Convolution*, ICLR, 2021 (arXiv:2002.07972).
