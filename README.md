# Flow-MDK

**Flow-MDK** (Flow-directed **M**arkov **D**iffusion **K**ernel networks) is a graph-neural-network surrogate for shallow-water solvers, covering **1D river networks, 2D floodplains, and coupled 1D–2D systems**. It adapts the hydraulics-based architecture of [SWE-GNN (Bentivoglio et al., HESS 2023)](https://hess.copernicus.org/articles/27/4227/2023/) by replacing its symmetric message passing with a **flow-directed Markov Diffusion Kernel** [(S2GC, Zhu & Koniusz, ICLR 2021)](https://arxiv.org/abs/2002.07972) propagation scheme, combined with an **advection–diffusion operator splitting**: directional difference-based messages carry wave/advection dynamics, while the MDK filter carries diffusive backwater effects with a physically matched receptive field.

Key design choices:

- **Physics-matched propagation range** — the MDK series truncation is set by the physical diffusion length √(2DΔt), mirroring how SWE-GNN ties layer count to the CFL condition;
- **Directionality preserved** — a hydraulics-weighted (discharge / Froude) directed transition matrix replaces the symmetric normalized adjacency, enabling supercritical flow and advection-dominated regimes;
- **Dry/wet safety** — per-step renormalization as wet/dry edges evolve, and bias-free dynamic encoders so dry cells stay dry;
- **Three scenarios, one codebase** — heterographs with interface edges unify river chains (1D), 2D meshes, and coupled 1D–2D systems;
- **Residual spectral filtering** — the MDK filter acts on *increments*, not absolute states; the λ₀·I identity term caps smoothing depth (anti-over-smoothing by construction).

Training data are generated with **TELEMAC-MASCARET** (Mascaret 1D / TELEMAC-2D / coupled runs). Evaluation follows the SWE-GNN protocol: RMSE/MAE on water depth and unit discharge, CSI for inundation extent, computational speed-up, plus ablations isolating the MDK contribution (see [`plan/PLAN.md`](plan/PLAN.md)). Our backbone was verified line-by-line against the official SWE-GNN implementation ([comparison doc](docs/swe_gnn_official_comparison.md)).

> ⚠️ **Status: work in progress.** Roadmap and milestones: [`plan/PLAN.md`](plan/PLAN.md).
> Background reading: [`references/`](references/README.md) — S2GC/MDK, SWE-GNN, MeshGraphNets, PDE foundation models, LLM-agent workflows.

---

**中文说明**

**Flow-MDK** 是面向浅水方程求解器的图神经网络代理模型，统一支持**一维河网、二维漫滩及一二维耦合**三类场景。方法在 [SWE-GNN（Bentivoglio 等， HESS 2023）](https://hess.copernicus.org/articles/27/4227/2023/)的水力同构架构基础上，将对称消息传播替换为**水力定向的马尔可夫扩散核（MDK）**[（S2GC， Zhu & Koniusz， ICLR 2021）](https://arxiv.org/abs/2002.07972)，并采用**对流-扩散算子分裂**：有向差值消息承载波动/对流动力学，MDK 滤波承载扩散性回水效应。

核心设计：

- **传播范围物理匹配**——MDK 级数截断由扩散长度 √(2DΔt) 决定，对应 SWE-GNN 中层数与 CFL 的绑定关系；
- **保留方向性**——以流量/Froude 加权的有向转移矩阵替代对称邻接，可表达急流与对流主导体制；
- **干湿安全**——干湿边演化时逐步重归一化，动态 encoder 无偏置项，干断面恒不产流；
- **三类场景统一**——河网链、二维网格与耦合系统统一为含接口边的异构图；
- **残差式谱滤波**——MDK 滤波作用于增量而非状态本身，λ₀·I 恒等项限制平滑深度（结构上防 over-smoothing）。

训练数据由 **TELEMAC-MASCARET**（Mascaret 一维 / TELEMAC-2D / 耦合运行）批量生成；评测沿用 SWE-GNN 协议（水深与流量 RMSE/MAE、淹没范围 CSI、加速比），并设置消融实验隔离 MDK 的贡献。

> ⚠️ **项目进行中**，里程碑规划见 [`plan/PLAN.md`](plan/PLAN.md)；背景文献见 [`references/`](references/README.md)。

---

## Repository layout

```
Flow-MDK/
├── plan/PLAN.md            # roadmap & milestones
├── references/             # background papers (see references/README.md)
├── configs/                # experiment configs (Flow-MDK / SWE-GNN / SSGC ablations)
├── src/flow_mdk/
│   ├── layers/             # MDK propagation, ψ difference message, operator-split layer
│   ├── models/             # encoders (bias-free dynamic), processor, decoder, rollout wrapper
│   ├── baselines/          # comparison architectures (GCN / GAT / persistence; see its README)
│   ├── data/               # 1D chain / 2D dual graphs, features, npz dataset, dry-wet topology
│   ├── train/              # recursive multistep loss, curriculum, trainer
│   ├── eval/               # RMSE/MAE/CSI/KS, Dirichlet energy, rollout evaluation
│   ├── gen/                # scenario families + 1D diffusive-wave reference solver
│   └── utils/              # seeding, io (npz schema), logging
├── scripts/                # scenario generation, Mascaret/TELEMAC runners, train/evaluate CLI
├── docs/                   # real-case inventory & official-implementation comparison
├── tests/                  # unit + end-to-end smoke tests
├── third_party/telemac/    # how to link the local TELEMAC-MASCARET tree / docker image
└── data/                   # generated datasets & checkpoints (git-ignored)
```

## Quickstart

```bash
pip install -e .

# 1. generate the 1D scenario family (reference solver built in; >=50 scenarios)
python scripts/generate_scenarios_1d.py --out data/scenarios_1d --num 50 --jobs 1

# 2. train (Flow-MDK full model; swap the config for -MDK / -定向性 ablations)
python scripts/train.py --config configs/1d_flow_mdk.yaml

#    comparison baselines (GCN / GAT / persistence) share the same harness:
python scripts/train.py --config configs/1d_baseline_gcn.yaml

# 3. evaluate on the test split (RMSE / MAE / CSI / speed-up)
python scripts/evaluate.py --config runs/1d_flow_mdk/config.yaml \
    --checkpoint runs/1d_flow_mdk/best.pt

# 4. (M1) attach Mascaret ground truth via the local TELEMAC-MASCARET docker image
python scripts/run_mascaret.py --scenario data/scenarios_1d/1d_0000.npz \
    --workdir data/mascaret/1d_0000 --backend docker

# 5. import the real-basin projects (1D with .opt truth replay + 2D meshes)
python scripts/import_real_cases.py     # -> data/real_cases/ (git-ignored), see docs/real_cases.md
```

## Attribution

If you use this work, please also cite the two pillars it builds on:

- Bentivoglio, R., Isufi, E., Jonkman, S. N., Taormina, R.: *Rapid spatio-temporal flood modelling via hydraulics-based graph neural networks*, HESS, 27, 4227–4246, 2023.
- Zhu, H., Koniusz, P.: *Simple Spectral Graph Convolution*, ICLR, 2021 (arXiv:2002.07972).
