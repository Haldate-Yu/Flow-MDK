#!/usr/bin/env python
"""Summarise experiment runs into the L2/L3 comparison tables (L4 tooling).

Reads run directories (eval_*.json + runs/results.csv rows) and emits the
markdown tables used in docs/results_partA_swe.md and the upcoming L4
report: in-domain RMSE, the A->B zero-shot matrix with degradation factors,
the B2 per-exam breakdown, pairwise KS tests on per-scenario errors, and —
for runs evaluated with the L5 monitor — the mean Dirichlet energy.

    python scripts/summarize_runs.py --prefix L2_partA
    python scripts/summarize_runs.py --prefix L3_B1_paper --out-md docs/L4_L3.md
    python scripts/summarize_runs.py runs/L2_partA_swegnn runs/L2_partA_gcn

Each --prefix forms its own summary group (L2 and L3 chains must never be
merged into one table: their trainings differ). Within a group, domain
labels come from the results.csv registry (split + data_root per eval row);
runs without registry rows fall back to parsing the eval filename. The
in-domain domain is the eval whose data_root matches the training row;
every other domain is reported as zero-shot with its degradation factor
relative to it.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.eval.metrics import ks_test  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
MODELS = ("swegnn", "flow_mdk", "gcn", "gat", "ssgc", "persistence")
TIMESTAMP_RE = re.compile(r"_\d{8}_\d{6}$")


def domain_label(data_root: str, split: str) -> str:
    name = Path(data_root).name
    if name == "scenarios_partA_v2":
        return {"test": "A-test", "A2_test": "A2", "A3_test": "A3",
                "val": "A-val", "train": "A-train"}.get(split, f"A:{split}")
    if name == "family_all":
        return f"B1:{split}"
    if name.startswith("family_"):
        return f"→{name}"
    if name == "scenarios_1d":
        return f"→B2 ({split})"
    return f"{name}:{split}"


def model_name(run_dir: Path) -> str:
    name = TIMESTAMP_RE.sub("", run_dir.name)
    for m in sorted(MODELS, key=len, reverse=True):
        if m in name:
            return m
    return name


def fallback_label(json_name: str) -> str:
    m = re.match(r"eval_([a-zA-Z0-9]+)_(.+)\.json$", json_name)
    if m:
        return domain_label(m.group(2), m.group(1))
    m = re.match(r"eval_(.+)\.json$", json_name)
    return m.group(1) if m else json_name


def read_run_config(run: Path) -> dict:
    """Fallback source of truth for runs predating the results registry."""
    path = run / "config.yaml"
    if not path.exists():
        return {}
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def run_epochs(run: Path) -> str:
    history = run / "history.json"
    if history.exists():
        try:
            return str(len(json.loads(history.read_text(encoding="utf-8"))))
        except Exception:
            pass
    return "?"


def load_registry() -> dict[str, list[dict]]:
    """run dir name -> registry rows (train row first, then eval rows)."""
    path = REPO / "runs" / "results.csv"
    registry: dict[str, list[dict]] = {}
    if not path.exists():
        return registry
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out = (row.get("out_dir") or "").replace("\\", "/")
            if not out:
                continue
            registry.setdefault(Path(out).name, []).append(row)
    for rows in registry.values():
        rows.sort(key=lambda r: r.get("kind") != "eval")
    return registry


def collect_runs(args: argparse.Namespace) -> list[tuple[str, list[Path]]]:
    groups: list[tuple[str, list[Path]]] = []
    if args.runs:
        dirs = []
        seen: set[str] = set()
        for d in map(Path, args.runs):
            if d.name not in seen and any(d.glob("eval_*.json")):
                seen.add(d.name)
                dirs.append(d)
        if dirs:
            groups.append(("selected runs", dirs))
    for prefix in args.prefix:
        dirs = sorted(
            d for d in (REPO / "runs").glob(f"{prefix}_*")
            if d.is_dir() and any(d.glob("eval_*.json"))
        )
        if dirs:
            groups.append((f"runs/{prefix}_*", dirs))
    return groups


def summarize_group(title: str, run_dirs: list[Path], registry: dict,
                    idx: int, fmt, args: argparse.Namespace) -> list[str]:
    lines: list[str] = []
    add = lines.append
    add(f"# {title}")
    add(f"\nGenerated {time.strftime('%Y-%m-%d %H:%M')} · "
        f"metric: {'Q' if idx else 'h'} RMSE · {len(run_dirs)} runs\n")

    # per run: model -> seed -> domain -> entry dict
    runs_data: list[dict] = []
    for run in run_dirs:
        rows = registry.get(run.name, [])
        train_row = next((r for r in rows if r["kind"] == "train"), None)
        eval_rows = [r for r in rows if r["kind"] == "eval"]
        cfg = read_run_config(run)
        cfg_root = Path(((cfg.get("data") or {}).get("root")) or "").name
        budget = None
        if train_row:
            sec = train_row.get("train_seconds")
            budget = (
                f"arch={train_row.get('arch', '?')} G={train_row.get('hidden_dim', '?')} "
                f"layers={train_row.get('num_layers', '?')} hops={train_row.get('hops_per_layer', '?')} "
                f"mdk={train_row.get('mdk_use', '?')} epochs={train_row.get('epochs_run', '?')}"
                + (f" train={float(sec) / 3600:.1f}h" if sec else "")
            )
        elif cfg:
            mcfg = cfg.get("model") or {}
            budget = (
                f"arch={mcfg.get('arch', '?')} G={mcfg.get('hidden_dim', '?')} "
                f"layers={mcfg.get('num_message_passing_layers', '?')} "
                f"hops={mcfg.get('hops_per_layer', '?')} "
                f"mdk={(mcfg.get('mdk') or {}).get('use', '?')} "
                f"epochs={run_epochs(run)} (from config.yaml)"
            )
        labels: dict[str, str] = {}
        for r in eval_rows:
            if r.get("report"):
                labels[Path(r["report"]).name] = domain_label(
                    r.get("data_root", "?"), r.get("split", "?"))
        per_domain: dict[str, dict] = {}
        for json_path in sorted(run.glob("eval_*.json")):
            entries = json.loads(json_path.read_text(encoding="utf-8"))
            if not entries:
                continue
            row = next((r for r in eval_rows
                        if r.get("report")
                        and Path(r["report"]).name == json_path.name), None)
            if row:
                label = domain_label(row.get("data_root", "?"), row.get("split", "?"))
                root_name = Path(row["data_root"]).name
            elif json_path.name == "eval_test.json" and cfg_root:
                # registry-less run: the in-domain eval is the bare test split
                label = domain_label(cfg_root, "test")
                root_name = cfg_root
            else:
                label = fallback_label(json_path.name)
                root_name = ""
            energies = [e["dirichlet"][-1] for e in entries if e.get("dirichlet")]
            per_domain[label] = {
                "n": len(entries),
                "mean": float(np.mean([e["rmse"][idx] for e in entries])),
                "std": 0.0,
                "values": {e["scenario"]: e["rmse"][idx] for e in entries},
                "dirichlet": float(np.mean(energies)) if energies else None,
                "root": root_name,
            }
        train_root = (Path(train_row.get("data_root", "?")).name
                      if train_row else cfg_root)
        in_domain = next((label for label, entry in per_domain.items()
                          if entry["root"] and entry["root"] == train_root), None)
        seed = None
        m = re.search(r"_s(\d+)$", run.name)
        if m:
            seed = int(m.group(1))
        runs_data.append({"dir": run.name, "model": model_name(run), "seed": seed,
                          "domains": per_domain, "budget": budget,
                          "in_domain": in_domain})

    aggregate = any(r["seed"] is not None for r in runs_data)
    models = list(dict.fromkeys(r["model"] for r in runs_data))
    for r in runs_data:
        if r["budget"]:
            tag = f" (s{r['seed']})" if r["seed"] is not None else ""
            add(f"- **{r['model']}**{tag} — {r['budget']}")
    add("")

    # fold runs of the same model: seed -> mean±std, per-scenario mean
    data: dict[str, dict[str, dict]] = {}
    seeds_of: dict[str, list[int]] = {}
    in_domain: dict[str, str] = {}
    for r in runs_data:
        data.setdefault(r["model"], {})
        if r["seed"] is not None:
            seeds_of.setdefault(r["model"], []).append(r["seed"])
        if r["in_domain"] and r["model"] not in in_domain:
            in_domain[r["model"]] = r["in_domain"]
        for label, entry in r["domains"].items():
            data[r["model"]].setdefault(label, []).append(entry)
    for model, domains in data.items():
        for label, entries in domains.items():
            means = [e["mean"] for e in entries]
            values: dict[str, list[float]] = {}
            for e in entries:
                for s, v in e["values"].items():
                    values.setdefault(s, []).append(v)
            energies = [e["dirichlet"] for e in entries if e["dirichlet"] is not None]
            data[model][label] = {
                "n": entries[0]["n"],
                "mean": float(np.mean(means)),
                "std": float(np.std(means, ddof=1)) if len(means) > 1 else 0.0,
                "values": {s: float(np.mean(v)) for s, v in values.items()},
                "dirichlet": float(np.mean(energies)) if energies else None,
                "root": next((e["root"] for e in entries if e["root"]), ""),
                "pooled": [v for e in entries for v in e["values"].values()],
            }
    seeds_note = ""
    if aggregate:
        seed_strs = ["/".join(f"s{s}" for s in sorted(set(v))) for v in seeds_of.values()]
        seeds_note = f" · seeds {seed_strs[0]}" if seed_strs else ""

    def cell(name: str, d: str) -> str:
        entry = data[name].get(d)
        if not entry:
            return "—"
        if aggregate and seeds_of.get(name) and len(seeds_of[name]) > 1:
            return f"{fmt(entry['mean'])}±{entry['std']:.3f}"
        return fmt(entry["mean"])

    domains = sorted({d for per in data.values() for d in per},
                     key=lambda d: (0 if d in in_domain.values() else 1, d))

    add(f"## {'Q' if idx else 'h'}-RMSE by domain\n")
    add("| model | " + " | ".join(domains) + " |")
    add("|---|" + "---|" * len(domains))
    for name in models:
        add(f"| {name} | " + " | ".join(cell(name, d) for d in domains) + " |")

    in_labels = set(in_domain.values())
    degrade = [d for d in domains if d not in in_labels
               and any(in_domain.get(m) and d in data[m] for m in models)]
    if degrade:
        add("\n## Zero-shot degradation (× vs in-domain)\n")
        add("| model | " + " | ".join(degrade) + " |")
        add("|---|" + "---|" * len(degrade))
        for name in models:
            base = in_domain.get(name)
            cells = []
            for d in degrade:
                if not base or d == base or d not in data[name] or base not in data[name]:
                    cells.append("—")
                else:
                    cells.append(f"×{data[name][d]['mean'] / data[name][base]['mean']:.1f}")
            add(f"| {name} | " + " | ".join(cells) + " |")

    b2 = next((d for d in domains if d.startswith("→B2")), None)
    if b2:
        exams = sorted({s for m in models if b2 in data[m]
                        for s in data[m][b2]["values"]})
        if exams:
            add(f"\n## B2 per-exam ({b2})\n")
            add("| exam | " + " | ".join(models) + " |")
            add("|---|" + "---|" * len(models))
            for exam in exams:
                cells = [fmt(data[m][b2]["values"][exam])
                         if exam in data[m].get(b2, {"values": {}})["values"] else "—"
                         for m in models]
                add(f"| {exam} | " + " | ".join(cells) + " |")

    if args.ks:
        ks_head = "\n## KS tests (per-scenario RMSE distributions"
        if aggregate:
            ks_head += ", pooled over seeds"
        add(ks_head + ")\n")
        produced = False
        for d in domains:
            present = [m for m in models if d in data[m] and data[m][d]["n"] >= 5]
            for i, a in enumerate(present):
                for b in present[i + 1:]:
                    sa = np.array(data[a][d]["pooled"])
                    sb = np.array(data[b][d]["pooled"])
                    try:
                        stat, p = ks_test(sa, sb)
                    except RuntimeError as exc:
                        add(f"- {d}: {exc}")
                        continue
                    produced = True
                    flag = " *" if p < 0.05 else ""
                    add(f"- {d}: {a} vs {b} — D={stat:.3f}, p={p:.3g}{flag}")
        if not produced:
            add("- (no domain with ≥2 models and ≥5 scenarios)")

    if args.dirichlet:
        add("\n## Mean last-layer Dirichlet energy (per edge, per step; L5 runs only)\n")
        add("| model | " + " | ".join(domains) + " |")
        add("|---|" + "---|" * len(domains))
        for name in models:
            cells = [f"{data[name][d]['dirichlet']:.1f}"
                     if d in data[name] and data[name][d]["dirichlet"] is not None else "—"
                     for d in domains]
            add(f"| {name} | " + " | ".join(cells) + " |")

    if seeds_note:
        add(f"\n({seeds_note}; ± is the std of per-seed domain means)")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="*", help="run directories")
    parser.add_argument("--prefix", action="append", default=[],
                        help="discover runs/<prefix>_* as one summary group (repeatable)")
    parser.add_argument("--metric", choices=("h", "q"), default="h",
                        help="headline metric: h or Q RMSE (default h)")
    parser.add_argument("--ks", action="store_true",
                        help="pairwise KS tests on per-scenario RMSE")
    parser.add_argument("--dirichlet", action="store_true",
                        help="table of mean last-layer Dirichlet energy (L5 runs)")
    parser.add_argument("--out-md", type=Path, default=None,
                        help="also write the report as markdown")
    args = parser.parse_args()

    groups = collect_runs(args)
    if not groups:
        raise SystemExit("no runs given/found")
    registry = load_registry()
    idx = 1 if args.metric == "q" else 0
    fmt = (lambda v: f"{v:.1f}") if idx else (lambda v: f"{v:.3f}")

    out: list[str] = []
    for title, run_dirs in groups:
        if out:
            out.append("\n---\n")
        out += summarize_group(title, run_dirs, registry, idx, fmt, args)
    report = "\n".join(out) + "\n"
    print(report)
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(report, encoding="utf-8")
        print(f"written -> {args.out_md}")


if __name__ == "__main__":
    main()
