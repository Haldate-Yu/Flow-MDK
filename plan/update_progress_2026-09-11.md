# 进展日志 · 2026-09-11

> 总览、里程碑状态与待办清单见 [`PLAN.md`](PLAN.md)。当日共两轮会话，以下为第二轮（EOD）
> 整理的完成事项；截至当日结束的遗留项状态以 PLAN.md「待办与遗留项」为准。

## 完成事项

- **wqh/zxh 完整工程内化**：第二提供方的完整工程（含启动文件、Abaques、历史
  `.opt`/`.lis`）复制到 `data/real_sources/{wqh,zxh}/`，导入脚本指向仓库内路径——
  流水线不再依赖仓库外数据源。两者复算校验均**逐位复现（RMSE=0）**。
- **家族重建**：`family_zxh` 基于完整母版重生成（40/40 零失败；旧母版仅 18/40），
  真实母版家族达 **117 场景**（mdx 37 + zxh 40 + wqh 40），各含 split。
- **Part A v2**：按论文 130 模拟协议扩建（`scripts/generate_partA_v2.py`），
  含 A2 未见水情、A3 大流域两个泛化子集与专用 split。
- **GPU 就绪**：CUDA torch 2.14.0+cu126 装入活跃环境；1D 论文级配置实测通过
  （2×8 跳、G=64、H=8 rollout ≈ 21 s/epoch@H=1）。
- **首轮正式结果**：四模型（SWE-GNN 忠实复现 / Flow-MDK / GCN / GAT）× 四域
  （A test、B1 mdx、B1 zxh、B2 真实考卷）完整评测，A→B gap 首次量化
  （`docs/results_partA.md`、`datasets/runs/` 归档）。
- **服务器 runbook**：`docs/server_setup.md`（单卡指定 CUDA_VISIBLE_DEVICES、
  上传/下载清单、A100+driver535 用 cu121 的版本说明）。
- **归档与提交**：`datasets/` 3.33 GB / 9146 文件入库（LFS 模式已配置）；
  代码与数据两个提交已入本地 git。

## 下次会话建议顺序

服务器跑 L4（上传→`CUDA_VISIBLE_DEVICES=1 bash scripts/run_partA_experiments.sh`
→ 取回 runs/）；本地并行做 L1（SARAP 两段式初始化）与 L3（B1→B2 消融）。
