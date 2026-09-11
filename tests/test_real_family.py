"""Tests for the real-master scenario family generator."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture(scope="module")
def master(tmp_path_factory):
    """A tiny synthetic master with replayed truth."""
    from flow_mdk.gen.scenarios_1d import Scenario1DParams, generate_1d_scenario
    from flow_mdk.utils.io import save_scenario

    root = tmp_path_factory.mktemp("masters")
    sc = generate_1d_scenario(
        Scenario1DParams(num_sections=20, length=4000.0, duration=4 * 3600,
                         dt=30.0, dt_out=600.0, q_peak=100.0, seed=5),
        "mast",
    )
    sc.meta["solver"] = "mascaret_opt_replay"  # pretend replayed truth
    sc.meta["source"] = str(root)
    save_scenario(sc, root / "mast.npz")
    # a minimal Mascaret-like project so the patch helpers have real blocks
    (root / "proj").mkdir()
    (root / "proj" / "mast.xcas").write_text(
        "<fichierCas>\n  <parametresCalage>\n    <frottement>\n"
        "      <loi>1</loi>\n      <nbZone>1</nbZone>\n"
        "      <numBranche>1</numBranche>\n      <absDebZone>0.0</absDebZone>\n"
        "      <absFinZone>4000.0</absFinZone>\n      <coefLitMin>30.0</coefLitMin>\n"
        "      <coefLitMaj>30.0</coefLitMaj>\n    </frottement>\n"
        "  </parametresCalage>\n  <parametresLoisHydrauliques>\n    <nb>1</nb>\n"
        "    <lois>\n      <structureParametresLoi>\n        <nom>loi_inflow</nom>\n"
        "        <type>1</type>\n        <donnees>\n"
        "          <fichier>inflow.loi</fichier>\n        </donnees>\n"
        "      </structureParametresLoi>\n    </lois>\n"
        "  </parametresLoisHydrauliques>\n</fichierCas>",
        encoding="ISO-8859-1",
    )
    (root / "proj" / "inflow.loi").write_text(
        "# Temps (s) Debit\n         S\n 0.0 5.0\n", encoding="ISO-8859-1"
    )
    sc.meta["source"] = str(root / "proj")
    save_scenario(sc, root / "mast.npz")
    return root


def test_family_generation(master, tmp_path):
    from flow_mdk.gen.scenarios_real import RealFamilyParams, generate_real_family

    scenarios = generate_real_family(
        RealFamilyParams(master="mast", master_root=str(master), num_scenarios=5,
                         seed=3), out_dir=tmp_path,
    )
    assert len(scenarios) == 5
    for sc in scenarios:
        assert sc.meta["solver"] == "pending_mascaret_rerun"
        assert "mascaret_patch" in sc.meta
        assert sc.meta["mascaret_patch"]["master_stem"] == "mast"
    # roughness fields differ across scenarios and from the base
    ks = np.stack([sc.node_static[:, 2] for sc in scenarios])
    assert ks.std(axis=0).mean() > 0
    # inflow laws differ across scenarios
    qs = np.stack([sc.dynamic[:, 0, 1] for sc in scenarios])
    assert qs.std(axis=0).max() > 0
    # non-negative hydrographs
    assert (qs >= 0).all()


def test_friction_patch_and_law_patch(master, tmp_path):
    from flow_mdk.gen.scenarios_real import (
        RealFamilyParams,
        generate_real_family,
        materialise_mascaret_project,
    )

    scenarios = generate_real_family(
        RealFamilyParams(master="mast", master_root=str(master), num_scenarios=2,
                         seed=1), out_dir=tmp_path,
    )
    workdir = tmp_path / "proj_run"
    xcas = materialise_mascaret_project(scenarios[0], workdir)
    text = xcas.read_text(encoding="ISO-8859-1", errors="replace")
    assert "<nbZone>" in text and "coefLitMin" in text
    # inflow law overwritten with the perturbed series
    laws = list(workdir.glob("*.loi"))
    assert any("perturbed inflow" in p.read_text(encoding="ISO-8859-1") for p in laws)
