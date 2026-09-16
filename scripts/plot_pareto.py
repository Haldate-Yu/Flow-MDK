#!/usr/bin/env python
"""M5 Pareto assembly: accuracy x efficiency x complexity per model/domain.

Axes follow the PLAN M5 protocol:
- accuracy  : in-domain h-RMSE (1D A-test for the 1D panel, 2D family test for
              the 2D panel), mean over paper-budget seeds (runs/results.csv);
- efficiency: mean solver->surrogate speedup over the same eval scenarios
              (eval json `speedup`, i.e. TELEMAC wall time / rollout time);
- complexity: parameter count, counted from the seed-0 checkpoint.

    python scripts/plot_pareto.py    # -> docs/pareto_frontier.md + runs/pareto_frontier.png
"""

from __future__ import annotations

import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np  # noqa: E402
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from build_generalization_matrix import parse_run  # noqa: E402

PANELS = {
    "1D A-test": {
        "models": ("swegnn", "flow_mdk", "gcn", "gat"),
        "prefixes": ("MS4_partA_", "partA_paper_"),  # s0 lives under the stamped name
        "domain": ("data/scenarios_partA_v2", "test"),
    },
    "2D test": {
        "models": ("swegnn", "flow_mdk", "ssgc"),
        "prefixes": ("MS4_2d_",),
        "domain": ("data/scenarios_2d_family", "test"),
    },
}


def main() -> None:
    rows = list(csv.DictReader(open(REPO / "runs" / "results.csv", newline="",
                                    encoding="utf-8")))

    rmse = defaultdict(dict)   # (panel, model) -> {seed: h_rmse}
    speed = defaultdict(dict)  # (panel, model) -> {seed: mean speedup}
    for r in rows:
        if r["kind"] != "eval" or not r["rmse"]:
            continue
        parsed = parse_run(r["run"])
        if parsed is None or parsed[1] != "last":
            continue
        model, _, seed = parsed
        for panel, cfg in PANELS.items():
            if (r["data_root"], r["split"]) != cfg["domain"]:
                continue
            if model not in cfg["models"]:
                continue
            if not r["run"].startswith(cfg["prefixes"]):
                continue
            rmse[(panel, model)][seed] = float(r["rmse"].split(";")[0])
            rep = json.load(open(REPO / r["report"], encoding="utf-8"))
            sp = [s["speedup"] for s in rep if s.get("speedup")]
            if sp:
                speed[(panel, model)][seed] = st.mean(sp)

    table = []
    for panel, cfg in PANELS.items():
        for model in cfg["models"]:
            ckpt = REPO / "runs" / f"{cfg['prefixes'][0]}{model}_s0" / "last.pt"
            if not ckpt.exists():  # stamped s0 fallback (partA_paper_*)
                import glob
                cand = sorted(glob.glob(str(REPO / "runs" / f"{cfg['prefixes'][1] if len(cfg['prefixes']) > 1 else cfg['prefixes'][0]}{model}_*")))
                if not cand:
                    continue
                ckpt = Path(cand[0]) / "last.pt"
            if not ckpt.exists():
                continue
            state = __import__("torch").load(ckpt, map_location="cpu",
                                             weights_only=True)
            params = sum(v.numel() for v in state["model_state"].values())
            r_vals, s_vals = rmse.get((panel, model), {}), speed.get((panel, model), {})
            if not r_vals:
                continue
            table.append({
                "panel": panel, "model": model, "params_k": params / 1e3,
                "rmse_mean": st.mean(r_vals.values()),
                "rmse_std": st.stdev(r_vals.values()) if len(r_vals) > 1 else 0.0,
                "speedup_mean": st.mean(s_vals.values()) if s_vals else None,
                "speedup_std": st.stdev(s_vals.values()) if len(s_vals) > 1 else 0.0,
            })

    lines = [
        "# M5 Pareto · 精度–效率–复杂度（paper budget，registry + checkpoints 自动生成）",
        "",
        "> 生成：`python scripts/plot_pareto.py`。精度 = 域内 h-RMSE（跨种子 mean±std）；"
        "效率 = 对求解器的平均加速比（TELEMAC 耗时 / 代理 rollout 耗时，逐场景均值再跨种子均值）；"
        "复杂度 = seed-0 checkpoint 参数量。图：`runs/pareto_frontier.png`。",
        "",
    ]
    for panel in PANELS:
        lines += [f"## {panel}", "",
                  "| model | params (k) | h-RMSE (m) | speedup (×) |",
                  "|---|---|---|---|"]
        for t in [t for t in table if t["panel"] == panel]:
            sp = (f"{t['speedup_mean']:.0f}±{t['speedup_std']:.0f}"
                  if t["speedup_mean"] else "—")
            lines.append(f"| {t['model']} | {t['params_k']:.0f} | "
                         f"{t['rmse_mean']:.3f}±{t['rmse_std']:.3f} | {sp} |")
        lines.append("")

    fig, axes = plt.subplots(1, len(PANELS), figsize=(11, 4.4))
    for ax, panel in zip(np.atleast_1d(axes), PANELS):
        pts = [t for t in table if t["panel"] == panel]
        for t in pts:
            if t["speedup_mean"]:
                ax.scatter(t["speedup_mean"], t["rmse_mean"],
                           s=max(t["params_k"] / 8, 40), alpha=0.75)
                ax.annotate(f"{t['model']}\n({t['params_k']:.0f}k)",
                            (t["speedup_mean"], t["rmse_mean"]),
                            textcoords="offset points", xytext=(8, 4), fontsize=8)
        ax.set_xscale("log")
        ax.set_xlabel("speedup vs solver (×, log)")
        ax.set_ylabel("in-domain h-RMSE (m)")
        ax.set_title(panel)
        ax.grid(alpha=0.3)
    fig.tight_layout()
    out_png = REPO / "runs" / "pareto_frontier.png"
    fig.savefig(out_png, dpi=150)

    (REPO / "docs" / "pareto_frontier.md").write_text("\n".join(lines),
                                                      encoding="utf-8")
    print(f"[pareto] {len(table)} model-domain points")
    print(f"[pareto] wrote docs/pareto_frontier.md + {out_png}")


if __name__ == "__main__":
    main()
