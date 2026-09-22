#!/usr/bin/env python
"""Server-side data verification before any rebuild/retrain (2D roots).

Run on the server (pure CPU, ~1-2 min):

    python scripts/verify_server_data.py 2>&1 | tee data/verify_data_$(date +%m%d).log

Checks:
  [B] 2D family root (130 npz, split 91/19/20)
  [C] larger-domain root (24 npz, all-test)
  [D] run-config / registry sanity for the 2D arms (MS4_2d, MS4b, L16_mdkoff_2d)
  md5 tables for every npz (paste back for local-vs-server diff)

Exit code = number of hard failures (missing files/roots).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

FAILS: list[str] = []


def head(txt: str) -> None:
    print(f"\n{'=' * 78}\n{txt}\n{'=' * 78}")


def verdict(tag: str, ok: bool | None, msg: str) -> None:
    label = "OK     " if ok is True else ("DEFECT " if ok is False else "INFO   ")
    print(f"  [{label}] {tag}: {msg}")
    if ok is False:
        FAILS.append(f"{tag}: {msg}")


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


# ------------------------------------------------------------- B/C. 2D roots
def check_grid_root(root: Path, expect_n: int, expect_split: dict[str, int] | None,
                    label: str, tag: str = "B") -> None:
    head(f"[{tag}] {label}  root={root}")
    if not root.is_dir():
        verdict(label, False, "目录不存在")
        return
    npzs = sorted(root.glob("*.npz"))
    verdict("数量", len(npzs) == expect_n, f"{len(npzs)}/{expect_n} npz")
    sp = root / "split.json"
    if sp.is_file():
        split = json.loads(sp.read_text(encoding="utf-8"))
        sizes = {k: len(v) for k, v in split.items()}
        ok = expect_split is None or sizes == expect_split
        verdict("切分", ok, f"{sizes}" + (f"（预期 {expect_split}）" if expect_split and not ok else ""))
    else:
        verdict("切分", False, "split.json 缺失")
    if expect_n <= 30:
        print("  -- md5 --")
        for p in npzs:
            print(f"    {md5(p)}  {p.name}")


# ------------------------------------------------------------------- D. runs
def check_runs(runs: Path) -> None:
    head(f"[D] 训练协议 sanity  root={runs}")
    want = {
        "MS4_2d_flow_mdk_s0": {"model.num_message_passing_layers": "6",
                               "model.mdk.use": "true", "model.mdk.directed": "true",
                               "data.root": "data/scenarios_2d_family"},
        "MS4b_2d_swegnn_s0": {"model.num_message_passing_layers": "1", "model.hops_per_layer": "8",
                              "model.mdk.use": "false", "data.root": "data/scenarios_2d_family"},
        "L16_mdkoff_2d_s0": {"model.num_message_passing_layers": "6",
                             "model.mdk.use": "false",
                             "data.root": "data/scenarios_2d_family"},
    }
    for run, keys in want.items():
        cfg = runs / run / "config.yaml"
        if not cfg.is_file():
            verdict(run, False, "config.yaml 缺失")
            continue
        text = cfg.read_text(encoding="utf-8")
        flat: dict[str, str] = {}
        stack: list[tuple[int, str]] = []
        for line in text.splitlines():
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            stripped = line.strip()
            if stripped.startswith("-"):
                # list item: its keyless parent owns a list, not a dict — pop it
                stack = [(i, kk) for i, kk in stack if i < indent]
                continue
            k, _, v = stripped.partition(":")
            if not v.strip():
                stack = [(i, kk) for i, kk in stack if i < indent]
                stack.append((indent, k))
                continue
            path = ".".join(kk for _, kk in stack) + ("." if stack else "") + k
            flat[path] = v.strip()
        bad = []
        for k, v in keys.items():
            actual = flat.get(k, "<缺>")
            if str(actual).lower() != v.lower():
                bad.append(f"{k}={actual}(预期{v})")
        verdict(run, not bad, "; ".join(bad) if bad else "关键键位全部符合")
    csv = runs / "results.csv"
    if csv.is_file():
        lines = csv.read_text(encoding="utf-8").splitlines()
        n = len(lines) - 1
        counts = {p: sum(1 for l in lines if f",{p}" in l) for p in ("MS4_2d_", "MS4b_2d", "L16_mdkoff_2d")}
        verdict("registry", None, f"{n} 行; MS4_2d={counts['MS4_2d_']} MS4b={counts['MS4b_2d']} L16_mdkoff_2d={counts['L16_mdkoff_2d']}")
    else:
        verdict("registry", False, "results.csv 缺失")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--2d-root", dest="root2d", default="data/scenarios_2d_family")
    ap.add_argument("--larger-root", default="data/scenarios_2d_larger")
    ap.add_argument("--runs", default="runs")
    args = ap.parse_args()

    print(f"verify_server_data @ {Path.cwd()}")
    check_grid_root(Path(args.root2d), 130, {"train": 91, "val": 19, "test": 20}, "2D 家族 64x64", tag="B")
    check_grid_root(Path(args.larger_root), 24, {"test": 24}, "2D 大域 128x128", tag="C")
    check_runs(Path(args.runs))

    head("汇总")
    if FAILS:
        print(f"硬失败 {len(FAILS)} 项：")
        for f in FAILS:
            print(f"  - {f}")
    else:
        print("无硬失败。")
    sys.exit(len(FAILS))


if __name__ == "__main__":
    main()
