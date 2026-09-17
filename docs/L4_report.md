# L4 机器报告 · runs 汇总（summarize_runs.py 自动生成）

> 生成方式（在仓库根目录）：
>
>     python scripts/summarize_runs.py --prefix partA_paper --prefix L3_B1_paper --ks
>     python scripts/summarize_runs.py --prefix MS4_partA --prefix MS4_B1 --ks
>     python scripts/summarize_runs.py --prefix MS4_2d --ks --dirichlet
>     python scripts/summarize_runs.py --prefix L4probe --ks
>     python scripts/summarize_runs.py --prefix MS5_partA --ks
>     python scripts/summarize_runs.py --prefix L16_mdkoff_partA --ks
>     python scripts/summarize_runs.py --prefix L16_mdkoff_2d --ks --dirichlet
>     python scripts/summarize_runs.py --prefix E61b_partA_full --ks
>     python scripts/summarize_runs.py --prefix B1v2 --ks
>     python scripts/summarize_runs.py --prefix unet_2d --ks
>     python scripts/summarize_runs.py --prefix M4_chain_v1 --ks
>     python scripts/summarize_runs.py --prefix ptbest
>
> 分组：`partA_paper_*` / `L3_B1_paper_*` = 2026-09-13 论文预算单种子（s0）；
> `MS4_partA_*` / `MS4_B1_*` = E3 论文预算三种子（s0 为 09-13 run 的副本，见各目录
> `_SEED0_SOURCE.txt`，registry 行在原名下）；`MS4_2d_*` = E4/E5 2D 论文预算三种子（s0=09-14 E4，s1/s2=09-15 E5，已并入）；
> `L4probe_*` = E2 防漂移探针；`MS5_partA_2x8mdk` =
> MS5/E1 收官臂（浅层 2L×8 骨架 + 定向 MDK，3 新鲜种子）；
> `L16_mdkoff_partA_*` / `L16_mdkoff_2d_*` = L16 -MDK 深度匹配消融（2026-09-16 服务器）；
> `E61b_partA_full_*` = E6.1 配方验证（E6 recipe 论文预算，2026-09-16 服务器）；
> `B1v2_*` = B1 家族 v2 重训（130 场景敏感性检查，2026-09-17 服务器）；
> `unet_2d_*` = U-Net 2D 基线三种子（2026-09-17 服务器）；
> `M4_chain_v1_*` = M4 耦合链可行性三种子（单场景）；`ptbest_*` = best.pt
> 协议对照大表。人工判读见 [`results_partA_swe.md`](results_partA_swe.md) L4–E5/MS5/L14/L16/E6.1/B1v2/U-Net/M4 节。

# runs/partA_paper_*

Generated 2026-09-17 18:41 · metric: h RMSE · 4 runs

- **flow_mdk** — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=112 train=0.3h
- **gat** — arch=baseline_gat G=64 layers=6 hops=1 mdk=False epochs=100 train=0.3h
- **gcn** — arch=baseline_gcn G=64 layers=6 hops=1 mdk=False epochs=113 train=0.2h
- **swegnn** — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=102 train=0.3h

## h-RMSE by domain

| model | A2 | A-test | A3 | →B2 (val) | →family_mdx | →family_wqh | →family_zxh |
|---|---|---|---|---|---|---|---|
| flow_mdk | 1.264 | 1.417 | 1.326 | 2.424 | 2.280 | 0.827 | 0.684 |
| gat | 1.600 | 1.918 | 2.295 | 4.475 | 8.584 | 2.838 | 1.285 |
| gcn | 35.436 | 35.378 | 35.249 | 65.741 | 127.344 | 50.647 | 24.738 |
| swegnn | 0.682 | 0.722 | 0.774 | 2.456 | 3.018 | 0.603 | 0.285 |

## Zero-shot degradation (× vs in-domain)

| model | A-test | A3 | →B2 (val) | →family_mdx | →family_wqh | →family_zxh |
|---|---|---|---|---|---|---|
| flow_mdk | ×1.1 | ×1.0 | ×1.9 | ×1.8 | ×0.7 | ×0.5 |
| gat | ×1.2 | ×1.4 | ×2.8 | ×5.4 | ×1.8 | ×0.8 |
| gcn | ×1.0 | ×1.0 | ×1.9 | ×3.6 | ×1.4 | ×0.7 |
| swegnn | ×1.1 | ×1.1 | ×3.6 | ×4.4 | ×0.9 | ×0.4 |

## B2 per-exam (→B2 (val))

| exam | flow_mdk | gat | gcn | swegnn |
|---|---|---|---|---|
| mdx | 5.267 | 10.535 | 126.397 | 5.372 |
| mdx_downstream | 3.389 | 3.407 | 77.574 | 3.226 |
| mdx_upstream | 1.897 | 4.303 | 49.358 | 2.098 |
| wqh | 0.758 | 2.852 | 50.635 | 0.581 |
| zxh | 0.808 | 1.279 | 24.743 | 1.004 |

## KS tests (per-scenario RMSE distributions)

- A2: flow_mdk vs gat — D=0.632, p=0.000714 *
- A2: flow_mdk vs gcn — D=1.000, p=5.66e-11 *
- A2: flow_mdk vs swegnn — D=0.842, p=4.77e-07 *
- A2: gat vs gcn — D=1.000, p=5.66e-11 *
- A2: gat vs swegnn — D=1.000, p=5.66e-11 *
- A2: gcn vs swegnn — D=1.000, p=5.66e-11 *
- A-test: flow_mdk vs gat — D=0.612, p=6.8e-09 *
- A-test: flow_mdk vs gcn — D=1.000, p=7.85e-29 *
- A-test: flow_mdk vs swegnn — D=0.653, p=3.59e-10 *
- A-test: gat vs gcn — D=1.000, p=7.85e-29 *
- A-test: gat vs swegnn — D=0.939, p=1.19e-23 *
- A-test: gcn vs swegnn — D=1.000, p=7.85e-29 *
- A3: flow_mdk vs gat — D=0.700, p=0.0123 *
- A3: flow_mdk vs gcn — D=1.000, p=1.08e-05 *
- A3: flow_mdk vs swegnn — D=0.600, p=0.0524
- A3: gat vs gcn — D=1.000, p=1.08e-05 *
- A3: gat vs swegnn — D=1.000, p=1.08e-05 *
- A3: gcn vs swegnn — D=1.000, p=1.08e-05 *
- →B2 (val): flow_mdk vs gat — D=0.400, p=0.873
- →B2 (val): flow_mdk vs gcn — D=1.000, p=0.00794 *
- →B2 (val): flow_mdk vs swegnn — D=0.200, p=1
- →B2 (val): gat vs gcn — D=1.000, p=0.00794 *
- →B2 (val): gat vs swegnn — D=0.400, p=0.873
- →B2 (val): gcn vs swegnn — D=1.000, p=0.00794 *
- →family_mdx: flow_mdk vs gat — D=1.000, p=0.000583 *
- →family_mdx: flow_mdk vs gcn — D=1.000, p=0.000583 *
- →family_mdx: flow_mdk vs swegnn — D=1.000, p=0.000583 *
- →family_mdx: gat vs gcn — D=1.000, p=0.000583 *
- →family_mdx: gat vs swegnn — D=1.000, p=0.000583 *
- →family_mdx: gcn vs swegnn — D=1.000, p=0.000583 *
- →family_wqh: flow_mdk vs gat — D=1.000, p=0.00216 *
- →family_wqh: flow_mdk vs gcn — D=1.000, p=0.00216 *
- →family_wqh: flow_mdk vs swegnn — D=0.833, p=0.026 *
- →family_wqh: gat vs gcn — D=1.000, p=0.00216 *
- →family_wqh: gat vs swegnn — D=1.000, p=0.00216 *
- →family_wqh: gcn vs swegnn — D=1.000, p=0.00216 *
- →family_zxh: flow_mdk vs gat — D=1.000, p=0.00216 *
- →family_zxh: flow_mdk vs gcn — D=1.000, p=0.00216 *
- →family_zxh: flow_mdk vs swegnn — D=1.000, p=0.00216 *
- →family_zxh: gat vs gcn — D=1.000, p=0.00216 *
- →family_zxh: gat vs swegnn — D=1.000, p=0.00216 *
- →family_zxh: gcn vs swegnn — D=1.000, p=0.00216 *

---

# runs/L3_B1_paper_*

Generated 2026-09-17 18:41 · metric: h RMSE · 3 runs

- **flow_mdk** — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=112 train=0.6h
- **ssgc** — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=103 train=0.5h
- **swegnn** — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=114 train=0.6h

## h-RMSE by domain

| model | B1:test | →B2 (val) |
|---|---|---|
| flow_mdk | 0.875 | 1.621 |
| ssgc | 0.852 | 1.684 |
| swegnn | 2.150 | 2.583 |

## Zero-shot degradation (× vs in-domain)

| model | →B2 (val) |
|---|---|
| flow_mdk | ×1.9 |
| ssgc | ×2.0 |
| swegnn | ×1.2 |

## B2 per-exam (→B2 (val))

| exam | flow_mdk | ssgc | swegnn |
|---|---|---|---|
| mdx | 3.644 | 5.107 | 5.328 |
| mdx_downstream | 2.685 | 1.130 | 3.410 |
| mdx_upstream | 1.334 | 1.778 | 1.595 |
| wqh | 0.301 | 0.288 | 1.658 |
| zxh | 0.142 | 0.119 | 0.923 |

## KS tests (per-scenario RMSE distributions)

- B1:test: flow_mdk vs ssgc — D=0.211, p=0.808
- B1:test: flow_mdk vs swegnn — D=0.632, p=0.000714 *
- B1:test: ssgc vs swegnn — D=0.632, p=0.000714 *
- →B2 (val): flow_mdk vs ssgc — D=0.200, p=1
- →B2 (val): flow_mdk vs swegnn — D=0.400, p=0.873
- →B2 (val): ssgc vs swegnn — D=0.400, p=0.873

# runs/MS4_partA_*

Generated 2026-09-17 18:41 · metric: h RMSE · 12 runs

- **flow_mdk** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=112 (from config.yaml)
- **flow_mdk** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=112 train=0.3h
- **flow_mdk** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=114 train=0.5h
- **gat** (s0) — arch=baseline_gat G=64 layers=6 hops=1 mdk=False epochs=100 (from config.yaml)
- **gat** (s1) — arch=baseline_gat G=64 layers=6 hops=1 mdk=False epochs=100 train=0.2h
- **gat** (s2) — arch=baseline_gat G=64 layers=6 hops=1 mdk=False epochs=100 train=0.8h
- **gcn** (s0) — arch=baseline_gcn G=64 layers=6 hops=1 mdk=False epochs=113 (from config.yaml)
- **gcn** (s1) — arch=baseline_gcn G=64 layers=6 hops=1 mdk=False epochs=101 train=0.1h
- **gcn** (s2) — arch=baseline_gcn G=64 layers=6 hops=1 mdk=False epochs=100 train=0.4h
- **swegnn** (s0) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=102 (from config.yaml)
- **swegnn** (s1) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=112 train=0.4h
- **swegnn** (s2) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=112 train=0.5h

## h-RMSE by domain

| model | A-test | A2 | A3 | →B2 (val) | →family_mdx | →family_wqh | →family_zxh |
|---|---|---|---|---|---|---|---|
| flow_mdk | 5.040±3.195 | 5.140±3.420 | 4.764±3.056 | 7.832±4.978 | 14.598±12.424 | 6.864±6.864 | 4.498±3.636 |
| gat | 1.134±0.679 | 0.998±0.521 | 1.309±0.854 | 2.733±1.509 | 4.767±3.309 | 1.317±1.319 | 0.538±0.647 |
| gcn | 12.383±19.915 | 12.342±20.000 | 12.417±19.775 | 23.377±36.692 | 44.804±71.495 | 17.443±28.761 | 8.458±14.101 |
| swegnn | 1.485±0.730 | 1.360±0.654 | 2.086±1.155 | 12.117±11.194 | 26.377±20.807 | 12.604±10.871 | 3.860±3.345 |

## Zero-shot degradation (× vs in-domain)

| model | A2 | A3 | →B2 (val) | →family_mdx | →family_wqh | →family_zxh |
|---|---|---|---|---|---|---|
| flow_mdk | ×1.0 | ×0.9 | ×1.6 | ×2.9 | ×1.4 | ×0.9 |
| gat | ×0.9 | ×1.2 | ×2.4 | ×4.2 | ×1.2 | ×0.5 |
| gcn | ×1.0 | ×1.0 | ×1.9 | ×3.6 | ×1.4 | ×0.7 |
| swegnn | ×0.9 | ×1.4 | ×8.2 | ×17.8 | ×8.5 | ×2.6 |

## B2 per-exam (→B2 (val))

| exam | flow_mdk | gat | gcn | swegnn |
|---|---|---|---|---|
| mdx | 15.972 | 7.364 | 46.345 | 20.432 |
| mdx_downstream | 4.087 | 1.559 | 26.573 | 10.275 |
| mdx_upstream | 7.712 | 2.880 | 18.062 | 12.345 |
| wqh | 6.738 | 1.335 | 17.451 | 13.710 |
| zxh | 4.653 | 0.529 | 8.452 | 3.823 |

## KS tests (per-scenario RMSE distributions, pooled over seeds)

- A-test: flow_mdk vs gat — D=0.667, p=2.85e-31 *
- A-test: flow_mdk vs gcn — D=0.449, p=1.02e-13 *
- A-test: flow_mdk vs swegnn — D=0.653, p=6.67e-30 *
- A-test: gat vs gcn — D=0.333, p=1.25e-07 *
- A-test: gat vs swegnn — D=0.177, p=0.02 *
- A-test: gcn vs swegnn — D=0.333, p=1.25e-07 *
- A2: flow_mdk vs gat — D=0.667, p=2.61e-12 *
- A2: flow_mdk vs gcn — D=0.544, p=4.39e-08 *
- A2: flow_mdk vs swegnn — D=0.667, p=2.61e-12 *
- A2: gat vs gcn — D=0.333, p=0.00333 *
- A2: gat vs swegnn — D=0.298, p=0.0122 *
- A2: gcn vs swegnn — D=0.333, p=0.00333 *
- A3: flow_mdk vs gat — D=0.667, p=1.28e-06 *
- A3: flow_mdk vs gcn — D=0.433, p=0.00655 *
- A3: flow_mdk vs swegnn — D=0.600, p=2.37e-05 *
- A3: gat vs gcn — D=0.333, p=0.0709
- A3: gat vs swegnn — D=0.233, p=0.393
- A3: gcn vs swegnn — D=0.333, p=0.0709
- →B2 (val): flow_mdk vs gat — D=0.467, p=0.0755
- →B2 (val): flow_mdk vs gcn — D=0.333, p=0.386
- →B2 (val): flow_mdk vs swegnn — D=0.267, p=0.678
- →B2 (val): gat vs gcn — D=0.333, p=0.386
- →B2 (val): gat vs swegnn — D=0.467, p=0.0755
- →B2 (val): gcn vs swegnn — D=0.267, p=0.678
- →family_mdx: flow_mdk vs gat — D=0.571, p=0.00166 *
- →family_mdx: flow_mdk vs gcn — D=0.333, p=0.196
- →family_mdx: flow_mdk vs swegnn — D=0.619, p=0.000439 *
- →family_mdx: gat vs gcn — D=0.333, p=0.196
- →family_mdx: gat vs swegnn — D=0.667, p=0.0001 *
- →family_mdx: gcn vs swegnn — D=0.333, p=0.196
- →family_wqh: flow_mdk vs gat — D=0.667, p=0.000429 *
- →family_wqh: flow_mdk vs gcn — D=0.333, p=0.275
- →family_wqh: flow_mdk vs swegnn — D=0.500, p=0.0207 *
- →family_wqh: gat vs gcn — D=0.333, p=0.275
- →family_wqh: gat vs swegnn — D=0.667, p=0.000429 *
- →family_wqh: gcn vs swegnn — D=0.333, p=0.275
- →family_zxh: flow_mdk vs gat — D=0.667, p=0.000429 *
- →family_zxh: flow_mdk vs gcn — D=0.611, p=0.00184 *
- →family_zxh: flow_mdk vs swegnn — D=0.333, p=0.275
- →family_zxh: gat vs gcn — D=0.333, p=0.275
- →family_zxh: gat vs swegnn — D=0.667, p=0.000429 *
- →family_zxh: gcn vs swegnn — D=0.333, p=0.275

( · seeds s0/s1/s2; ± is the std of per-seed domain means)

---

# runs/MS4_B1_*

Generated 2026-09-17 18:41 · metric: h RMSE · 9 runs

- **flow_mdk** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=112 (from config.yaml)
- **flow_mdk** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=114 train=0.7h
- **flow_mdk** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=112 train=0.9h
- **ssgc** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=103 (from config.yaml)
- **ssgc** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=113 train=0.8h
- **ssgc** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=114 train=0.9h
- **swegnn** (s0) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=114 (from config.yaml)
- **swegnn** (s1) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=109 train=0.6h
- **swegnn** (s2) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=102 train=0.9h

## h-RMSE by domain

| model | B1:test | →B2 (val) |
|---|---|---|
| flow_mdk | 1.392±0.986 | 2.084±0.482 |
| ssgc | 2.540±2.042 | 3.575±1.750 |
| swegnn | 1.249±0.781 | 2.004±0.503 |

## Zero-shot degradation (× vs in-domain)

| model | →B2 (val) |
|---|---|
| flow_mdk | ×1.5 |
| ssgc | ×1.4 |
| swegnn | ×1.6 |

## B2 per-exam (→B2 (val))

| exam | flow_mdk | ssgc | swegnn |
|---|---|---|---|
| mdx | 4.537 | 7.059 | 5.069 |
| mdx_downstream | 4.059 | 8.599 | 2.119 |
| mdx_upstream | 1.393 | 1.823 | 1.731 |
| wqh | 0.344 | 0.319 | 0.737 |
| zxh | 0.086 | 0.076 | 0.365 |

## KS tests (per-scenario RMSE distributions, pooled over seeds)

- B1:test: flow_mdk vs ssgc — D=0.123, p=0.788
- B1:test: flow_mdk vs swegnn — D=0.211, p=0.16
- B1:test: ssgc vs swegnn — D=0.246, p=0.0639
- →B2 (val): flow_mdk vs ssgc — D=0.200, p=0.938
- →B2 (val): flow_mdk vs swegnn — D=0.133, p=1
- →B2 (val): ssgc vs swegnn — D=0.267, p=0.678

( · seeds s0/s1/s2; ± is the std of per-seed domain means)

# runs/MS4_2d_*

Generated 2026-09-17 18:41 · metric: h RMSE · 9 runs

- **flow_mdk** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=114 train=2.5h
- **flow_mdk** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=113 train=2.6h
- **flow_mdk** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=112 train=2.3h
- **ssgc** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=110 train=2.4h
- **ssgc** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=112 train=2.3h
- **ssgc** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=109 train=2.3h
- **swegnn** (s0) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=109 train=6.0h
- **swegnn** (s1) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=108 train=5.1h
- **swegnn** (s2) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=110 train=4.5h

## h-RMSE by domain

| model | scenarios_2d_family:test | exams_2d:test | exams_2d_h8:test |
|---|---|---|---|
| flow_mdk | 0.529±0.277 | 18.335±7.881 | 3.004±0.487 |
| ssgc | 1.820±1.573 | 17.930±4.707 | 3.180±1.016 |
| swegnn | 5.060±6.600 | 17.930±11.972 | 3.208±0.971 |

## Zero-shot degradation (× vs in-domain)

| model | exams_2d:test | exams_2d_h8:test |
|---|---|---|
| flow_mdk | ×34.7 | ×5.7 |
| ssgc | ×9.9 | ×1.7 |
| swegnn | ×3.5 | ×0.6 |

## KS tests (per-scenario RMSE distributions, pooled over seeds)

- scenarios_2d_family:test: flow_mdk vs ssgc — D=0.633, p=1.31e-11 *
- scenarios_2d_family:test: flow_mdk vs swegnn — D=0.550, p=1.1e-08 *
- scenarios_2d_family:test: ssgc vs swegnn — D=0.367, p=0.000557 *

## Mean last-layer Dirichlet energy (per edge, per step; L5 runs only)

| model | scenarios_2d_family:test | exams_2d:test | exams_2d_h8:test |
|---|---|---|---|
| flow_mdk | 0.0 | 17.0 | 15.1 |
| ssgc | 0.1 | 14.0 | 11.3 |
| swegnn | 3.6 | 92.1 | 58.1 |

( · seeds s0/s1/s2; ± is the std of per-seed domain means)

# runs/L4probe_*

Generated 2026-09-17 18:41 · metric: h RMSE · 3 runs

- **L4probe_es** — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=32 train=0.1h
- **L4probe_L3** — arch=flow_mdk G=64 layers=3 hops=1 mdk=True epochs=109 train=0.3h
- **L4probe_lr** — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=114 train=0.4h

## h-RMSE by domain

| model | A-test |
|---|---|
| L4probe_es | 2.669 |
| L4probe_L3 | 0.778 |
| L4probe_lr | 8.499 |

## KS tests (per-scenario RMSE distributions)

- A-test: L4probe_es vs L4probe_L3 — D=1.000, p=7.85e-29 *
- A-test: L4probe_es vs L4probe_lr — D=0.980, p=7.69e-27 *
- A-test: L4probe_L3 vs L4probe_lr — D=1.000, p=7.85e-29 *

# runs/MS5_partA_*

Generated 2026-09-17 18:42 · metric: h RMSE · 3 runs

- **MS5_partA_2x8mdk** (s0) — arch=flow_mdk G=64 layers=2 hops=8 mdk=True epochs=111 train=0.5h
- **MS5_partA_2x8mdk** (s1) — arch=flow_mdk G=64 layers=2 hops=8 mdk=True epochs=110 train=0.5h
- **MS5_partA_2x8mdk** (s2) — arch=flow_mdk G=64 layers=2 hops=8 mdk=True epochs=113 train=0.5h

## h-RMSE by domain

| model | A2 | A-test | A3 | →B2 (val) | →family_mdx | →family_wqh | →family_zxh |
|---|---|---|---|---|---|---|---|
| MS5_partA_2x8mdk | 2.411±0.372 | 3.239±2.111 | 4.812±5.098 | 45.508±68.084 | 124.199±195.929 | 23.767±33.793 | 30.058±48.270 |

## Zero-shot degradation (× vs in-domain)

| model | A-test | A3 | →B2 (val) | →family_mdx | →family_wqh | →family_zxh |
|---|---|---|---|---|---|---|
| MS5_partA_2x8mdk | ×1.3 | ×2.0 | ×18.9 | ×51.5 | ×9.9 | ×12.5 |

## B2 per-exam (→B2 (val))

| exam | MS5_partA_2x8mdk |
|---|---|
| mdx | 62.132 |
| mdx_downstream | 5.365 |
| mdx_upstream | 118.324 |
| wqh | 33.122 |
| zxh | 8.596 |

## KS tests (per-scenario RMSE distributions, pooled over seeds)

- (no domain with ≥2 models and ≥5 scenarios)

( · seeds s0/s1/s2; ± is the std of per-seed domain means)

# runs/L16_mdkoff_partA_*

Generated 2026-09-17 18:42 · metric: h RMSE · 3 runs

- **L16_mdkoff_partA** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=False epochs=112 train=0.4h
- **L16_mdkoff_partA** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=False epochs=111 train=0.2h
- **L16_mdkoff_partA** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=False epochs=112 train=0.4h

## h-RMSE by domain

| model | A-test |
|---|---|
| L16_mdkoff_partA | 17.183±22.847 |

## KS tests (per-scenario RMSE distributions, pooled over seeds)

- (no domain with ≥2 models and ≥5 scenarios)

( · seeds s0/s1/s2; ± is the std of per-seed domain means)

# runs/L16_mdkoff_2d_*

Generated 2026-09-17 18:42 · metric: h RMSE · 3 runs

- **L16_mdkoff_2d** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=False epochs=114 train=2.4h
- **L16_mdkoff_2d** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=False epochs=108 train=2.5h
- **L16_mdkoff_2d** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=False epochs=111 train=4.1h

## h-RMSE by domain

| model | scenarios_2d_family:test |
|---|---|
| L16_mdkoff_2d | 0.835±0.641 |

## KS tests (per-scenario RMSE distributions, pooled over seeds)

- (no domain with ≥2 models and ≥5 scenarios)

## Mean last-layer Dirichlet energy (per edge, per step; L5 runs only)

| model | scenarios_2d_family:test |
|---|---|
| L16_mdkoff_2d | 0.0 |

( · seeds s0/s1/s2; ± is the std of per-seed domain means)

# runs/E61b_partA_full_*

Generated 2026-09-17 18:43 · metric: h RMSE · 3 runs

- **E61b_partA_full** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=115 train=0.5h
- **E61b_partA_full** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=115 train=0.5h
- **E61b_partA_full** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=115 train=0.5h

## h-RMSE by domain

| model | A-test |
|---|---|
| E61b_partA_full | 3.758±2.544 |

## KS tests (per-scenario RMSE distributions, pooled over seeds)

- (no domain with ≥2 models and ≥5 scenarios)

( · seeds s0/s1/s2; ± is the std of per-seed domain means)

# runs/B1v2_*

Generated 2026-09-17 18:43 · metric: h RMSE · 9 runs

- **flow_mdk** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=113 train=1.1h
- **flow_mdk** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=114 train=1.0h
- **flow_mdk** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=109 train=0.8h
- **ssgc** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=104 train=0.8h
- **ssgc** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=100 train=0.7h
- **ssgc** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=100 train=0.7h
- **swegnn** (s0) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=103 train=1.3h
- **swegnn** (s1) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=101 train=0.7h
- **swegnn** (s2) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=113 train=0.8h

## h-RMSE by domain

| model | B1:test | →B2 (val) |
|---|---|---|
| flow_mdk | 2.051±1.834 | 2.674±1.407 |
| ssgc | 1.844±1.585 | 5.806±7.007 |
| swegnn | 2.154±1.102 | 2.562±0.690 |

## Zero-shot degradation (× vs in-domain)

| model | →B2 (val) |
|---|---|
| flow_mdk | ×1.3 |
| ssgc | ×3.1 |
| swegnn | ×1.2 |

## B2 per-exam (→B2 (val))

| exam | flow_mdk | ssgc | swegnn |
|---|---|---|---|
| mdx | 5.947 | 9.588 | 5.292 |
| mdx_downstream | 3.763 | 16.298 | 3.637 |
| mdx_upstream | 1.639 | 1.678 | 1.661 |
| wqh | 1.415 | 1.233 | 1.457 |
| zxh | 0.603 | 0.236 | 0.763 |

## KS tests (per-scenario RMSE distributions, pooled over seeds)

- B1:test: flow_mdk vs ssgc — D=0.159, p=0.408
- B1:test: flow_mdk vs swegnn — D=0.286, p=0.0113 *
- B1:test: ssgc vs swegnn — D=0.286, p=0.0113 *
- →B2 (val): flow_mdk vs ssgc — D=0.200, p=0.938
- →B2 (val): flow_mdk vs swegnn — D=0.200, p=0.938
- →B2 (val): ssgc vs swegnn — D=0.200, p=0.938

( · seeds s0/s1/s2; ± is the std of per-seed domain means)

# runs/unet_2d_*

Generated 2026-09-17 18:43 · metric: h RMSE · 3 runs

- **unet_2d** (s0) — arch=baseline_unet G=32 layers=6 hops=1 mdk=True epochs=109 train=1.1h
- **unet_2d** (s1) — arch=baseline_unet G=32 layers=6 hops=1 mdk=True epochs=113 train=0.7h
- **unet_2d** (s2) — arch=baseline_unet G=32 layers=6 hops=1 mdk=True epochs=113 train=0.7h

## h-RMSE by domain

| model | scenarios_2d_family:test |
|---|---|
| unet_2d | 4.654±2.179 |

## KS tests (per-scenario RMSE distributions, pooled over seeds)

- (no domain with ≥2 models and ≥5 scenarios)

( · seeds s0/s1/s2; ± is the std of per-seed domain means)

# runs/M4_chain_v1_*

Generated 2026-09-17 18:43 · metric: h RMSE · 3 runs

- **flow_mdk** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=60 train=0.3h
- **flow_mdk** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=60 train=0.4h
- **flow_mdk** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=60 train=0.5h

## h-RMSE by domain

| model | coupled_chain:test |
|---|---|
| flow_mdk | 1.644±0.189 |

## KS tests (per-scenario RMSE distributions, pooled over seeds)

- (no domain with ≥2 models and ≥5 scenarios)

( · seeds s0/s1/s2; ± is the std of per-seed domain means)

# runs/ptbest_*

Generated 2026-09-17 18:44 · metric: h RMSE · 92 runs

- **flow_mdk** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ssgc** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ssgc** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ssgc** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **swegnn** (s0) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **swegnn** (s1) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **swegnn** (s2) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **ptbest_E61_partA_full** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E61_partA_full** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E61_partA_full** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E61b_partA_full** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E61b_partA_full** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E61b_partA_full** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E6_partA_base** (s0) — arch=flow_mdk G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E6_partA_base** (s1) — arch=flow_mdk G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E6_partA_base** (s2) — arch=flow_mdk G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E6_partA_ema** (s0) — arch=flow_mdk G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E6_partA_ema** (s1) — arch=flow_mdk G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E6_partA_ema** (s2) — arch=flow_mdk G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E6_partA_full** (s0) — arch=flow_mdk G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E6_partA_full** (s1) — arch=flow_mdk G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E6_partA_full** (s2) — arch=flow_mdk G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E6_partA_valfix** (s0) — arch=flow_mdk G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E6_partA_valfix** (s1) — arch=flow_mdk G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_E6_partA_valfix** (s2) — arch=flow_mdk G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **swegnn** (s0) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **swegnn** (s1) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **swegnn** (s2) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **flow_mdk** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **swegnn** (s0) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **swegnn** (s1) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **swegnn** (s2) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **ptbest_L16_mdkoff_2d** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=False epochs=? (from config.yaml)
- **ptbest_L16_mdkoff_2d** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=False epochs=? (from config.yaml)
- **ptbest_L16_mdkoff_2d** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=False epochs=? (from config.yaml)
- **ptbest_L16_mdkoff_partA** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=False epochs=? (from config.yaml)
- **ptbest_L16_mdkoff_partA** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=False epochs=? (from config.yaml)
- **ptbest_L16_mdkoff_partA** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=False epochs=? (from config.yaml)
- **flow_mdk** — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ssgc** — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **swegnn** — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **ptbest_L4probe_es** — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_L4probe_L3** — arch=flow_mdk G=64 layers=3 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_L4probe_lr** — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ssgc** (s0) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ssgc** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ssgc** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **swegnn** (s0) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **swegnn** (s1) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **swegnn** (s2) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **flow_mdk** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ssgc** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ssgc** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **swegnn** (s1) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **swegnn** (s2) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **flow_mdk** (s1) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s2) — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **gat** (s1) — arch=baseline_gat G=64 layers=6 hops=1 mdk=False epochs=? (from config.yaml)
- **gat** (s2) — arch=baseline_gat G=64 layers=6 hops=1 mdk=False epochs=? (from config.yaml)
- **gcn** (s1) — arch=baseline_gcn G=64 layers=6 hops=1 mdk=False epochs=? (from config.yaml)
- **gcn** (s2) — arch=baseline_gcn G=64 layers=6 hops=1 mdk=False epochs=? (from config.yaml)
- **swegnn** (s1) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **swegnn** (s2) — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **ptbest_MS5_partA_2x8mdk** (s0) — arch=flow_mdk G=64 layers=2 hops=8 mdk=True epochs=? (from config.yaml)
- **ptbest_MS5_partA_2x8mdk** (s1) — arch=flow_mdk G=64 layers=2 hops=8 mdk=True epochs=? (from config.yaml)
- **ptbest_MS5_partA_2x8mdk** (s2) — arch=flow_mdk G=64 layers=2 hops=8 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s0) — arch=flow_mdk G=32 layers=3 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s1) — arch=flow_mdk G=32 layers=3 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** (s2) — arch=flow_mdk G=32 layers=3 hops=1 mdk=True epochs=? (from config.yaml)
- **flow_mdk** — arch=flow_mdk G=64 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **gat** — arch=baseline_gat G=64 layers=6 hops=1 mdk=False epochs=? (from config.yaml)
- **gcn** — arch=baseline_gcn G=64 layers=6 hops=1 mdk=False epochs=? (from config.yaml)
- **swegnn** — arch=flow_mdk G=64 layers=2 hops=8 mdk=False epochs=? (from config.yaml)
- **ptbest_unet_2d** (s0) — arch=baseline_unet G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_unet_2d** (s1) — arch=baseline_unet G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)
- **ptbest_unet_2d** (s2) — arch=baseline_unet G=32 layers=6 hops=1 mdk=True epochs=? (from config.yaml)

## h-RMSE by domain

| model | A-test | B1:test | scenarios_2d_family:test | →B2 (test) | coupled_chain:test | exams_2d:test | exams_2d_h8:test | scenarios_partA_v2_dt2:test | scenarios_partA_v2_dt3:test | →B2 (val) | →family_mdx |
|---|---|---|---|---|---|---|---|---|---|---|---|
| flow_mdk | 3.250±2.350 | 1.166±0.792 | 0.534±0.214 | — | 1.225±0.176 | 16.584±3.247 | 2.471±0.101 | 2.356±0.179 | 2.378±1.441 | 1.788±0.000 | 6.498±0.000 |
| ssgc | — | 1.344±1.166 | 1.288±0.721 | — | — | 11.073±1.356 | 2.693±0.464 | — | — | 2.847±0.000 | — |
| swegnn | 1.788±1.305 | 0.974±0.183 | 3.303±4.002 | — | — | 7.343±5.711 | 2.643±0.328 | 1.395±0.721 | 0.910±0.053 | 1.792±0.000 | 4.630±0.000 |
| ptbest_E61_partA_full | — | — | — | 10.650±7.811 | — | — | — | — | — | — | — |
| ptbest_E61b_partA_full | 1.751±1.417 | — | — | — | — | — | — | — | — | — | — |
| ptbest_E6_partA_base | 3.843±1.833 | — | — | — | — | — | — | — | — | — | — |
| ptbest_E6_partA_ema | 1.870±0.761 | — | — | — | — | — | — | — | — | — | — |
| ptbest_E6_partA_full | 2.002±0.900 | — | — | — | — | — | — | — | — | — | — |
| ptbest_E6_partA_valfix | 4.097±3.326 | — | — | — | — | — | — | — | — | — | — |
| ptbest_L16_mdkoff_2d | — | — | 0.622±0.343 | — | — | — | — | — | — | — | — |
| ptbest_L16_mdkoff_partA | 4.277±4.115 | — | — | — | — | — | — | — | — | — | — |
| ptbest_L4probe_es | 1.931 | — | — | — | — | — | — | — | — | — | — |
| ptbest_L4probe_L3 | 1.231 | — | — | — | — | — | — | — | — | — | — |
| ptbest_L4probe_lr | 17.014 | — | — | — | — | — | — | — | — | — | — |
| gat | 0.866±0.102 | — | — | — | — | — | — | — | — | — | 2.987±0.000 |
| gcn | 0.777±0.032 | — | — | — | — | — | — | — | — | — | 2.835±0.000 |
| ptbest_MS5_partA_2x8mdk | 1.169±0.206 | — | — | — | — | — | — | — | — | — | — |
| ptbest_smoke_E6 | 3.253 | — | — | — | — | — | — | — | — | — | — |
| ptbest_smoke_MS5_2x8mdk | 1.240 | — | — | — | — | — | — | — | — | — | — |
| ptbest_unet_2d | — | — | 10.512±11.780 | — | — | — | — | — | — | — | — |

## Zero-shot degradation (× vs in-domain)

| model | coupled_chain:test | exams_2d:test | exams_2d_h8:test | scenarios_partA_v2_dt2:test | scenarios_partA_v2_dt3:test | →B2 (val) | →family_mdx |
|---|---|---|---|---|---|---|---|
| flow_mdk | ×1.1 | ×14.2 | ×2.1 | ×2.0 | ×2.0 | ×1.5 | ×5.6 |
| ssgc | — | ×8.2 | ×2.0 | — | — | ×2.1 | — |
| swegnn | — | ×7.5 | ×2.7 | ×1.4 | ×0.9 | ×1.8 | ×4.8 |
| ptbest_E61_partA_full | — | — | — | — | — | — | — |
| ptbest_E61b_partA_full | — | — | — | — | — | — | — |
| ptbest_E6_partA_base | — | — | — | — | — | — | — |
| ptbest_E6_partA_ema | — | — | — | — | — | — | — |
| ptbest_E6_partA_full | — | — | — | — | — | — | — |
| ptbest_E6_partA_valfix | — | — | — | — | — | — | — |
| ptbest_L16_mdkoff_2d | — | — | — | — | — | — | — |
| ptbest_L16_mdkoff_partA | — | — | — | — | — | — | — |
| ptbest_L4probe_es | — | — | — | — | — | — | — |
| ptbest_L4probe_L3 | — | — | — | — | — | — | — |
| ptbest_L4probe_lr | — | — | — | — | — | — | — |
| gat | — | — | — | — | — | — | ×3.4 |
| gcn | — | — | — | — | — | — | ×3.7 |
| ptbest_MS5_partA_2x8mdk | — | — | — | — | — | — | — |
| ptbest_smoke_E6 | — | — | — | — | — | — | — |
| ptbest_smoke_MS5_2x8mdk | — | — | — | — | — | — | — |
| ptbest_unet_2d | — | — | — | — | — | — | — |

## B2 per-exam (→B2 (test))

| exam | flow_mdk | ssgc | swegnn | ptbest_E61_partA_full | ptbest_E61b_partA_full | ptbest_E6_partA_base | ptbest_E6_partA_ema | ptbest_E6_partA_full | ptbest_E6_partA_valfix | ptbest_L16_mdkoff_2d | ptbest_L16_mdkoff_partA | ptbest_L4probe_es | ptbest_L4probe_L3 | ptbest_L4probe_lr | gat | gcn | ptbest_MS5_partA_2x8mdk | ptbest_smoke_E6 | ptbest_smoke_MS5_2x8mdk | ptbest_unet_2d |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1d_0040 | — | — | — | 9.973 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 1d_0041 | — | — | — | 11.175 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 1d_0042 | — | — | — | 10.182 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 1d_0043 | — | — | — | 10.427 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 1d_0044 | — | — | — | 11.279 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 1d_0045 | — | — | — | 10.667 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 1d_0046 | — | — | — | 10.727 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 1d_0047 | — | — | — | 10.607 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 1d_0048 | — | — | — | 10.214 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| 1d_0049 | — | — | — | 11.244 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

( · seeds s0/s1/s2; ± is the std of per-seed domain means)

