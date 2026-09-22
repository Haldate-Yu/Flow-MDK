"""S3 · 真实考卷的全时程轨迹证据（诊断：发散 vs 饱和欠反应）。

背景：round 6 的判决「MDK 系（含浅层骨架）在全时程发散，vanilla GCN/GAT 有界」
原先只有**场景级 RMSE 汇总**支撑。RMSE 无法区分两种完全不同的情形：

  (a) 真发散——预测单调漂移/指数放大，最终远离真值；
  (b) 饱和欠反应——输出近乎不动，误差虽小但属于"没在算动力学"。

本脚本逐时步保存探针节点的水深序列并画轨迹，把判断依据落到曲线本身；
同时打印末步误差与「预测峰值/真值峰值」比：比值 >>1 = 发散，≈0.5 = 明显压低。

首次运行会把 rollout 序列缓存到 `<--out 同名>.npz`，改图/改口径时用 --refresh 强制重算。

用法（本机 3060 可行，65k 节点无需分块）：

    python scripts/analyze_exam_trajectories.py \
        --scenario mdx_2d --out runs/exam_trajectories_mdx_2d.png
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.config import load_config  # noqa: E402
from flow_mdk.eval.rollout import load_model, rollout_scenario  # noqa: E402
from flow_mdk.utils.io import load_scenario  # noqa: E402
from flow_mdk.utils.seed import get_device  # noqa: E402

DEFAULT_RUNS = [
    ("flow_mdk（定向）", "runs/MS4_2d_flow_mdk_s0"),
    ("swegnn（官方1×8）", "runs/MS4b_2d_swegnn_s0"),
    ("ssgc（对称）", "runs/MS4_2d_ssgc_s0"),
    ("-MDK（无扩散分支）", "runs/L16_mdkoff_2d_s0"),
    ("gcn（vanilla）", "runs/MS4_2d_gcn_s0"),
    ("gat（vanilla）", "runs/MS4_2d_gat_s0"),
]
CACHE_KEYS = ("truth", "probes", "metrics")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="data/real_cases/exams_2d")
    ap.add_argument("--scenario", default="mdx_2d")
    ap.add_argument("--out", default="runs/exam_trajectories.png")
    ap.add_argument("--probes", type=int, default=3,
                    help="探针节点数（按真值水深时间变幅取最活跃的节点）")
    ap.add_argument("--runs", nargs="*", default=None,
                    help='覆盖默认对比臂，形如 "label=runs/xxx_s0"')
    ap.add_argument("--refresh", action="store_true",
                    help="忽略缓存，重新 rollout")
    ap.add_argument("--no-persist", action="store_true",
                    help="不画 persist（冻结输入帧）参照线")
    args = ap.parse_args()

    runs = DEFAULT_RUNS
    if args.runs:
        runs = []
        for item in args.runs:
            label, _, path = item.partition("=")
            runs.append((label or path, path))

    cache = Path(args.out).with_suffix(".npz")
    if cache.exists() and not args.refresh:
        z = np.load(cache, allow_pickle=True)
        series = {k: z[k] for k in z.files if k not in CACHE_KEYS}
        truth = z["truth"]
        probes = [int(i) for i in z["probes"]]
        metrics = json.loads(str(z["metrics"]))
        print(f"[S3] cache hit -> {cache}（{len(series)} arms；--refresh 可强制重算）")
        _report(metrics)
        _plot(series, truth, probes, args.scenario, args.out)
        return

    npz = Path(args.root) / f"{args.scenario}.npz"
    if not npz.exists():
        raise SystemExit(f"[S3] exam scenario not found: {npz}")
    scen = load_scenario(npz)

    truth_all = scen.dynamic[..., 0]                       # [T, N]
    span = truth_all.max(axis=0) - truth_all.min(axis=0)
    wet = truth_all.max(axis=0) > 0.05
    order = np.argsort(np.where(wet, span, -1.0))[::-1]
    probes = [int(i) for i in order[: args.probes]]
    print(f"[S3] scenario={args.scenario} nodes={scen.node_static.shape[0]} "
          f"steps={scen.num_steps}")
    print(f"[S3] probe nodes (by truth depth span): {probes}")
    print(f"[S3] truth depth span at probes: "
          f"{[round(float(span[p]), 3) for p in probes]}")

    device = get_device("cuda" if _cuda() else "cpu")
    series: dict[str, np.ndarray] = {}
    metrics: list[list] = []
    truth = None
    H = 1  # 全部考卷臂 num_previous_steps=1；persist = 冻结末输入帧
    if not args.no_persist:
        anchor = scen.dynamic[H][:, 0]
        n_rows = truth_all.shape[0] - H - 1
        series["persist（冻结输入帧）"] = np.repeat(
            anchor[probes][None, :], n_rows, axis=0)
        print(f"[S3] persist 参照线已加入（冻结第 {H} 帧, {n_rows} 步）")
    for label, run_dir in runs:
        cfg_path, ckpt = Path(run_dir) / "config.yaml", Path(run_dir) / "last.pt"
        if not cfg_path.exists() or not ckpt.exists():
            print(f"[S3] skip {label}: missing {run_dir}")
            continue
        config = load_config(cfg_path)
        elev_idx = 0 if config.data.name.startswith("1d") else 1
        model = load_model(config, scen.node_static.shape[1] + 1,
                           scen.edge_attr.shape[1], ckpt, device)
        report = rollout_scenario(model, scen, scen.num_steps, elev_idx, device)
        pred, tru = report.prediction[..., 0], report.truth[..., 0]   # [T, N]
        truth = tru
        series[label] = pred[:, probes]
        metrics.append([label,
                        float(np.sqrt(np.mean((pred[-1] - tru[-1]) ** 2))),
                        float(pred.max() / max(tru.max(), 1e-6)),
                        float(tru.max())])
        print(f"[S3] {label}: rollout {pred.shape[0]} steps, {report.seconds:.1f}s")

    if truth is None:
        raise SystemExit("[S3] no run produced a rollout — check --runs")
    if not args.no_persist and "persist（冻结输入帧）" in series:
        ps = series["persist（冻结输入帧）"]
        metrics.append(["persist（冻结输入帧）",
                        float(np.sqrt(np.mean((ps[-1] - truth[-1][probes]) ** 2))),
                        float(ps.max() / max(truth.max(), 1e-6)),
                        float(truth.max())])

    payload = {k: v for k, v in series.items()}
    payload["truth"], payload["probes"] = truth, np.array(probes)
    payload["metrics"] = json.dumps(metrics, ensure_ascii=False)
    np.savez_compressed(cache, **payload)
    print(f"[S3] cached -> {cache}")

    _report(metrics)
    _plot(series, truth, probes, args.scenario, args.out)


def _report(metrics: list) -> None:
    """末步 RMSE + 全局峰值比：>2 = 发散；<0.7 = 明显压低（欠反应）。"""
    print(f"\n{'arm':22s} {'末步 RMSE (m)':>14s} {'预测峰值/真值峰值':>18s} "
          f"{'真值峰值 (m)':>12s}  判定")
    print("-" * 92)
    for label, final_rmse, ratio, peak_true in metrics:
        print(f"{label:22s} {final_rmse:14.3f} {ratio:18.3f} {peak_true:12.2f}  "
              f"{_verdict(ratio)}")
    print("\n判读：峰值比 >2 表示预测单调放大（真发散）；≈0.5 表示峰值被压低到一半"
          "（欠反应）——后者即使 RMSE 小也不等于「跟得住」，而是输出近乎恒定，"
          "在真值大部分时间平稳时会被平均指标奖励。")


def _verdict(ratio: float) -> str:
    if ratio > 2.0:
        return "发散（峰值远超真值）"
    if ratio < 0.7:
        return "压低（峰值明显不足，欠反应）"
    return "量级正常"


def _cuda() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:  # noqa: BLE001
        return False


def _plot(series, truth, probes, scenario, out_path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei",
                                       "Noto Sans CJK SC", "WenQuanYi Zen Hei",
                                       "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    n = len(probes)
    fig, axes = plt.subplots(1, n, figsize=(4.8 * n, 3.8), squeeze=False)
    t = np.arange(truth.shape[0])
    colors = ["C3", "C0", "C2", "C1", "C4", "C5"]
    for k, node in enumerate(probes):
        ax = axes[0][k]
        ax.plot(t, truth[:, node], "k-", lw=2.4, label="TELEMAC-2D（真值）")
        for (label, _), c in zip(series.items(), colors):
            ax.plot(t, series[label][:, k], "--", lw=1.4, color=c, label=label)
        ax.set_title(f"节点 {node}", fontsize=10)
        ax.set_xlabel("rollout 步")
        if k == 0:
            ax.set_ylabel("水深 (m)")
        ax.grid(alpha=0.25)
    axes[0][-1].legend(fontsize=7, loc="upper left", framealpha=0.9)
    fig.suptitle(f"真实考卷 {scenario}：全时程水深轨迹（探针节点）"
                 f"——真值涨落后的回落 vs 各代理的外推行为", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    print(f"[S3] figure -> {out_path}")


if __name__ == "__main__":
    main()
