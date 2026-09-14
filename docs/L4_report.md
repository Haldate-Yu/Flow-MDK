# runs/partA_paper_*

Generated 2026-09-14 08:39 · metric: h RMSE · 4 runs

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

Generated 2026-09-14 08:39 · metric: h RMSE · 3 runs

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
