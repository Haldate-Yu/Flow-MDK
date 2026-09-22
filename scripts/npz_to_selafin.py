#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""水动力场 npz → SELAFIN (.slf) 转换器（供 QGIS-MDAL/BLUE KENUE 渲染）。

用法（仓库根目录）：
    # 耦合链场景（2D 段切片 + geo.slf 网格）：
    python scripts/npz_to_selafin.py --npz data/real_cases/coupled_chain/mdx_chain_fam011/mdx_chain_fam011.npz \
        --out "G:/论文/260918-FlowMDK/03_图表/渲染数据/fam011_真值.slf"
    # 合成 2D 家族场景（结构网格自动构网）：
    python scripts/npz_to_selafin.py --npz data/scenarios_2d_family/T2D_000.npz \
        --out "G:/论文/260918-FlowMDK/03_图表/渲染数据/T2D_000_真值.slf"
    # 模型预测场：把 rollout 存成同布局 npz（dynamic [T, N, 2]）后同命令。

输出变量：WATER DEPTH (m)、MODULUS OF VELOCITY (m/s)；写入后回读校验。
布局镜像 v8p4 写法（geo.slf 实测）：title(80) / counts(2i) / 变量名(32B×n) /
params(10i) / mesh(4i) / IKLE / IPOBO / X / Y；正文 = 逐时刻 float32 时间 +
逐变量帧。
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

from selafin import Selafin  # noqa: E402
from flow_mdk.utils.io import load_scenario  # noqa: E402

DEFAULT_GEO = Path(
    r"D:/Projects/wzzhsl-rest-subsystems-xd/schinta-module-basin-flood-prevention"
    r"/schinta-module-basin-flood-prevention-start/src/main/resources/template"
    r"/telemac2d/mdx/geo.slf")


def write_selafin(out: Path, title: bytes, var_names: list[tuple[str, str]],
                  times: np.ndarray, x: np.ndarray, y: np.ndarray,
                  ikle: np.ndarray, ipobo: np.ndarray,
                  frames: np.ndarray) -> None:
    """frames: [T, NV, NPOIN] float32；经典大端 SELAFIN（v8p4 紧凑头）。"""
    nelem, ndp = ikle.shape
    npoin = x.size
    with open(out, "wb") as fh:
        def rec(data: bytes) -> None:
            fh.write(struct.pack(">i", len(data)))
            fh.write(data)
            fh.write(struct.pack(">i", len(data)))

        rec(title.ljust(80)[:80])
        rec(struct.pack(">2i", len(var_names), 0))
        for name, unit in var_names:
            rec(name.ljust(16).encode("ascii") + unit.ljust(16).encode("ascii"))
        rec(struct.pack(">10i", 1, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        rec(struct.pack(">4i", nelem, npoin, ndp, 1))
        rec(np.ascontiguousarray(ikle, dtype=">i4").tobytes())
        rec(np.ascontiguousarray(ipobo, dtype=">i4").tobytes())
        rec(np.ascontiguousarray(x, dtype=">f4").tobytes())
        rec(np.ascontiguousarray(y, dtype=">f4").tobytes())
        for t in range(frames.shape[0]):
            rec(struct.pack(">f", float(times[t])))
            for v in range(frames.shape[1]):
                rec(np.ascontiguousarray(frames[t, v], dtype=">f4").tobytes())


def chain_mesh_and_fields(npz_path: Path, leg: int, mesh_slf: Path):
    """耦合链：2D 段切片 + geo.slf 网格（节点顺序摄取时保持一致）。"""
    geo = Selafin(mesh_slf)
    sc = load_scenario(npz_path)
    off = sc.meta["node_offsets"]
    a, b = off[leg], off[leg + 1]
    if b - a != geo.npoin:
        raise SystemExit(f"2D 段节点数 {b - a} != 几何 npoin {geo.npoin}——顺序不一致，先核对")
    dyn = sc.dynamic[:, a:b, :]
    return geo.x, geo.y, geo.ikle.astype(np.int64), geo.ipobo.astype(np.int64), dyn


def synthetic_mesh_and_fields(npz_path: Path):
    """合成 2D 家族：结构网格坐标/三角剖分由 meta['grid'] 确定性重建。"""
    from flow_mdk.data.graph_2d import build_2d_grid_graph
    sc = load_scenario(npz_path)
    g = sc.meta["grid"]
    _, _, centers = build_2d_grid_graph(g["nx"], g["ny"],
                                        g["cell_size"], g["cell_size"],
                                        g.get("connectivity", 4))
    x, y = centers[:, 0].astype(np.float64), centers[:, 1].astype(np.float64)
    nx, ny = g["nx"], g["ny"]
    nid = lambda i, j: i * ny + j  # noqa: E731
    tri = []
    for i in range(nx - 1):
        for j in range(ny - 1):
            a, b, c, d = nid(i, j), nid(i + 1, j), nid(i + 1, j + 1), nid(i, j + 1)
            tri += [[a, b, c], [a, c, d]]
    ikle = np.array(tri, dtype=np.int64)
    ipobo = np.zeros(x.size, dtype=np.int64)
    border = ([nid(0, j) for j in range(ny)] + [nid(nx - 1, j) for j in range(ny)]
              + [nid(i, 0) for i in range(nx)] + [nid(i, ny - 1) for i in range(nx)])
    ipobo[border] = 1
    return x, y, ikle, ipobo, sc.dynamic


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npz", required=True, help="场数据 npz（耦合链或合成 2D 场景）")
    ap.add_argument("--mesh-slf", default=str(DEFAULT_GEO),
                    help="TELEMAC 几何模板（仅耦合链路径需要）")
    ap.add_argument("--out", required=True, help="输出 .slf 路径")
    ap.add_argument("--leg", type=int, default=1, help="耦合链 2D 子图序号（默认 1）")
    args = ap.parse_args()

    probe = load_scenario(args.npz)
    if probe.meta.get("layout") == "2d_grid":
        x, y, ikle, ipobo, dyn = synthetic_mesh_and_fields(Path(args.npz))
    else:
        x, y, ikle, ipobo, dyn = chain_mesh_and_fields(Path(args.npz), args.leg,
                                                       Path(args.mesh_slf))

    frames = np.stack([dyn[:, :, 0], np.abs(dyn[:, :, 1])], axis=1).astype(np.float32)
    times = probe.times.astype(np.float32)

    write_selafin(Path(args.out), b"SERAFIN",
                  [("WATER DEPTH", "M"), ("MODULUS OF VELOCITY", "M/S")],
                  times, x, y, ikle, ipobo, frames)

    back = Selafin(args.out)
    assert back.npoin == x.size and back.nelem == ikle.shape[0], "网格头不一致"
    for sl in (0, 1):
        got = back.all_frames(back.variables[sl])
        assert np.allclose(got, frames[:, sl], atol=1e-5), f"变量 {sl} 回读不一致"
    print(f"[slf] {args.out}: {back.ntimes} 帧 × {back.nbvars} 变量 × "
          f"{back.npoin} 节点 / {back.nelem} 单元，回读一致")


if __name__ == "__main__":
    main()
