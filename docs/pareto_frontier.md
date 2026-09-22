# M5 Pareto · 精度–效率–复杂度（paper budget，registry + checkpoints 自动生成）

> 生成：`python scripts/plot_pareto.py`。精度 = 域内 h-RMSE（跨种子 mean±std）；效率 = 对求解器的平均加速比（TELEMAC 耗时 / 代理 rollout 耗时，逐场景均值再跨种子均值）；复杂度 = seed-0 checkpoint 参数量。图：`runs/pareto_frontier.png`。

## 1D A-test

| model | params (k) | h-RMSE (m) | speedup (×) |
|---|---|---|---|
| swegnn | 186 | 1.485±0.730 | 58±10 |
| flow_mdk | 343 | 5.040±3.195 | 40±20 |
| gcn | 34 | 12.383±19.915 | 63±42 |
| gat | 215 | 1.134±0.679 | 33±23 |

## 2D test

| model | params (k) | h-RMSE (m) | speedup (×) |
|---|---|---|---|
| swegnn | 186 | 5.060±6.600 | 533±4 |
| swegnn(1x8) | 104 | 0.745±0.365 | 627±249 |
| flow_mdk | 343 | 0.529±0.277 | 574±2 |
| ssgc | 343 | 1.820±1.573 | 623±5 |
| gcn | 34 | 0.871±0.206 | 142±88 |
| gat | 215 | 0.716±0.001 | 183±60 |
| flow_mdk(-MDK) | 342 | 0.835±0.641 | 478±451 |
| unet | 475 | 4.654±2.179 | 2409±227 |
