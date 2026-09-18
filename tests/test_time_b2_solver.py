"""Tests for the L9 solver-timing portability preflight (round-4 lesson:
Windows-style ``meta['source']`` values neither resolve nor parse into
components on the Linux server, so the template lookup failed 4/5)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from time_b2_solver import _source_candidates, preflight_portable_sources  # noqa: E402


def _tiny_scenario(name: str, source: str):
    from flow_mdk.utils.io import Scenario
    n, t = 3, 2
    return Scenario(
        name=name,
        node_static=np.zeros((n, 2), dtype=np.float32),
        edge_index=np.array([[0, 1], [1, 2]], dtype=np.int64),
        edge_attr=np.zeros((2, 1), dtype=np.float32),
        dynamic=np.zeros((t, n, 2), dtype=np.float32),
        wet=np.ones((t, n), dtype=np.uint8),
        times=np.array([0.0, 60.0]),
        meta={"source": source},
    )


class TestSourceCandidates:
    def test_windows_absolute_external_paths_parse_to_flat_staging(self):
        # round-4 failure case: on Linux, Path(...).name of this is the whole
        # string, so the old fallback joined garbage
        raw = (r"D:\Projects\wzzhsl\schinta\src\main\resources"
               r"\template\telemac1d\mdx")
        cands = _source_candidates(raw)
        assert Path("data/real_sources/mdx") in cands
        # separators normalised so the as-is candidate is at least POSIX-safe
        assert cands[0].as_posix() == raw.replace("\\", "/")

    def test_backslash_repo_relative_parses_as_is(self):
        raw = r"data\real_sources\wqh"
        cands = _source_candidates(raw)
        assert cands[0] == Path("data/real_sources/wqh")

    def test_posix_relative_unchanged(self):
        assert _source_candidates("data/real_sources/zxh")[0] == \
            Path("data/real_sources/zxh")

    def test_foreign_posix_absolute_gets_basename_staging(self):
        cands = _source_candidates("/srv/import/telemac1d/mdxUpStream")
        assert Path("data/real_sources/mdxUpStream") in cands

    def test_repo_absolute_from_other_checkout_keeps_real_sources_tail(self):
        raw = r"D:\Projects\Flow-MDK\data\real_sources\wqh"
        cands = _source_candidates(raw)
        assert Path("data/real_sources/wqh") in cands

    def test_parent_preserving_staging_candidate(self):
        raw = r"D:\schinta\telemac1d\mdx"
        cands = _source_candidates(raw)
        assert Path("data/real_sources/telemac1d/mdx") in cands
        assert Path("data/real_sources/mdx") in cands


class TestPreflight:
    @pytest.fixture()
    def scenarios_root(self, tmp_path, monkeypatch):
        import time_b2_solver
        root = tmp_path / "scenarios_1d"
        root.mkdir()
        # the documented flat staging on the "server"
        for name in ("mdx", "mdxUpStream"):
            d = tmp_path / "data" / "real_sources" / name
            d.mkdir(parents=True)
            (d / f"{name}.xcas").write_text("<fichierCas/>")
        for name in ("wqh", "zxh"):
            d = tmp_path / "data" / "real_sources" / name
            d.mkdir(parents=True)
            (d / f"{name}.xcas").write_text("<fichierCas/>")
        monkeypatch.setattr(time_b2_solver, "SCENARIOS_1D", root)
        monkeypatch.setattr(time_b2_solver, "REPO", tmp_path)
        monkeypatch.chdir(tmp_path)
        return root

    def _save(self, root, case, source):
        from flow_mdk.utils.io import save_scenario
        save_scenario(_tiny_scenario(case, source), root / f"{case}.npz")

    def test_windows_external_source_resolves_to_staged_copy(
            self, scenarios_root):
        from flow_mdk.utils.io import load_scenario
        self._save(scenarios_root, "mdx",
                   r"D:\Projects\wzzhsl\telemac1d\mdx")
        preflight_portable_sources(["mdx"])
        assert load_scenario(
            scenarios_root / "mdx.npz").meta["source"] == \
            "data/real_sources/mdx"

    def test_backslash_relative_source_normalised_to_posix(
            self, scenarios_root):
        from flow_mdk.utils.io import load_scenario
        self._save(scenarios_root, "wqh", r"data\real_sources\wqh")
        preflight_portable_sources(["wqh"])
        assert load_scenario(
            scenarios_root / "wqh.npz").meta["source"] == \
            "data/real_sources/wqh"

    def test_missing_template_warns_not_crashes(self, scenarios_root, capsys):
        self._save(scenarios_root, "mdx_upstream", r"D:\gone\telemac1d\neverStaged")
        preflight_portable_sources(["mdx_upstream"])
        assert "WARNING" in capsys.readouterr().out

    def test_rebuild_only_case_skipped(self, scenarios_root, capsys):
        self._save(scenarios_root, "mdx_downstream", r"D:\gone\mdxDownStream")
        preflight_portable_sources(["mdx_downstream"])
        assert capsys.readouterr().out == ""
