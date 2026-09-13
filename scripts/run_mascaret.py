#!/usr/bin/env python
"""Headless Mascaret batch runner (plan M0/M1).

Generates a Mascaret project (geometry, boundary laws, .xcas steering) from
a 1D scenario, runs it through one of two backends and parses the Optyca
result file back into a scenario .npz with ground truth attached.

Backends
--------
- ``docker``: runs the binary inside the TELEMAC-MASCARET image built from
  the self-contained context ``datasets/telemac-mascaret-v8p4r0/`` (base
  image ``telemac-debian:0.1``; see ``third_party/telemac/README.md``).
  Requires Docker.
- ``telapy``: in-process execution through the TelApy Fortran API
  (``telemac-mascaret/scripts/python3/telapy``); requires the compiled
  shared library on the loader path.

Status: the file templates mirror ``examples/mascaret/1_Steady_Kernel`` of
the v8p4 tree; the docker/telapy round-trip must be validated against the
local image in M1 (run ``--check`` for a one-section smoke test).

Examples
--------
    python scripts/run_mascaret.py --scenario data/scenarios_1d/1d_0000.npz \\
        --workdir data/mascaret/1d_0000 --backend docker
"""

from __future__ import annotations

import argparse
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flow_mdk.utils.io import Scenario, load_scenario, save_scenario  # noqa: E402

TELEMAC_IMAGE = os.environ.get("FLOW_MDK_TELEMAC_IMAGE", "telemac-debian:0.1")


# --------------------------------------------------------------------- #
# project file generation
# --------------------------------------------------------------------- #
def write_geometry(path: Path, x: np.ndarray, z: np.ndarray, width: np.ndarray) -> None:
    """Mascaret geometry file: one trapezoidal PROFILE per section.

    Line format follows the real project files (verified against the .opt
    ZREF column): ``PROFIL <branch> <name> <abscissa>`` then points
    ``X(transverse) Z(elevation) marker``.
    """
    lines = []
    for i, (xi, zi, wi) in enumerate(zip(x, z, width)):
        ext = max(2.0, 0.5 * wi)  # vertical wall extension above the bed
        name = f"P{i:04d}"
        lines.append(f"PROFIL Bief_1 {name} {xi:.3f}")
        lines.append(f"0.000 {zi + ext:.3f} B")
        lines.append(f"0.000 {zi:.3f} B")
        lines.append(f"{wi:.3f} {zi:.3f} B")
        lines.append(f"{wi:.3f} {zi + ext:.3f} B")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def write_hydrograph(path: Path, times: np.ndarray, q: np.ndarray) -> None:
    lines = ["# inflow hydrograph", "# Temps (s) Debit", "         S"]
    lines += [f"{t:.1f} {v:.4f}" for t, v in zip(times, q)]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def write_limnigramme(path: Path, times: np.ndarray, stage: np.ndarray) -> None:
    lines = ["# downstream stage law", "# Temps (s) Cote", "         S"]
    lines += [f"{t:.1f} {v:.4f}" for t, v in zip(times, stage)]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def write_tarage(path: Path, stage: np.ndarray, q: np.ndarray) -> None:
    """Rating curve law (Mascaret loi type 5, Q=f(Z); 'Cote Debit' columns,
    as in examples/mascaret/Test13/rezo.xcas)."""
    lines = ["# normal-depth rating curve", "# Cote Debit"]
    lines += [f"{zv:.4f} {qv:.4f}" for zv, qv in zip(stage, q)]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def write_xcas(
    path: Path,
    duration: float,
    dt: float,
    n_sections: int,
    reach_length: float,
    strickler: float,
    out_prefix: str,
) -> None:
    """Steering file mirroring the v8p4 example (transient Rezo kernel)."""
    n_steps = int(math.ceil(duration / dt))
    xml = f"""<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE fichierCas SYSTEM "mascaret-1.0.dtd">
<fichierCas>
  <parametresCas>
    <parametresGeneraux>
      <versionCode>3</versionCode>
      <code>1</code>
      <fichMotsCles>{out_prefix}.xcas</fichMotsCles>
      <presenceCasiers>false</presenceCasiers>
    </parametresGeneraux>
    <parametresModelePhysique>
      <perteChargeConf>false</perteChargeConf>
      <compositionLits>1</compositionLits>
      <debordelement>
        <litMajeur>false</litMajeur>
        <zoneStock>false</zoneStock>
      </debordelement>
    </parametresModelePhysique>
    <parametresNumeriques>
      <calcOndeSubmersion>true</calcOndeSubmersion>
      <froudeLimCondLim>1000.0</froudeLimCondLim>
      <hauteurEauMini>0.005</hauteurEauMini>
    </parametresNumeriques>
    <parametresTemporels>
      <pasTemps>{dt}</pasTemps>
      <tempsInit>0.0</tempsInit>
      <critereArret>2</critereArret>
      <nbPasTemps>{n_steps}</nbPasTemps>
      <tempsMax>{duration}</tempsMax>
      <pasTempsVar>true</pasTempsVar>
      <nbCourant>0.8</nbCourant>
    </parametresTemporels>
    <parametresGeometrieReseau>
      <geometrie>
        <fichier>geometrie</fichier>
        <format>2</format>
        <profilsAbscAbsolu>true</profilsAbscAbsolu>
      </geometrie>
      <listeBranches>
        <nb>1</nb>
        <numeros>1</numeros>
        <abscDebut>0.0</abscDebut>
        <abscFin>{reach_length}</abscFin>
        <numExtremDebut>1</numExtremDebut>
        <numExtremFin>2</numExtremFin>
      </listeBranches>
      <listeNoeuds>
        <nb>0</nb>
        <noeuds/>
      </listeNoeuds>
      <extrLibres>
        <nb>2</nb>
        <num>1 2</num>
        <numExtrem>1 2</numExtrem>
        <noms>
          <string>limite1</string>
          <string>limite2</string>
        </noms>
        <typeCond>1 2</typeCond>
        <numLoi>1 2</numLoi>
      </extrLibres>
    </parametresGeometrieReseau>
    <parametresConfluents>
      <nbConfluents>0</nbConfluents>
      <confluents/>
    </parametresConfluents>
    <parametresPlanimetrageMaillage>
      <methodeMaillage>5</methodeMaillage>
      <planim>
        <nbPas>101</nbPas>
        <nbZones>1</nbZones>
        <valeursPas>1.0</valeursPas>
        <num1erProf>1</num1erProf>
        <numDerProf>{n_sections}</numDerProf>
      </planim>
      <maillage>
        <modeSaisie>2</modeSaisie>
        <sauvMaillage>false</sauvMaillage>
        <maillageClavier>
          <nbSections>0</nbSections>
          <nbPlages>1</nbPlages>
          <num1erProfPlage>1</num1erProfPlage>
          <numDerProfPlage>{n_sections}</numDerProfPlage>
          <pasEspacePlage>{reach_length / (n_sections - 1)}</pasEspacePlage>
          <nbZones>0</nbZones>
        </maillageClavier>
      </maillage>
    </parametresPlanimetrageMaillage>
    <parametresSingularite>
      <nbSeuils>0</nbSeuils>
    </parametresSingularite>
    <parametresApportDeversoirs/>
    <parametresCalage>
      <frottement>
        <loi>1</loi>
        <nbZone>1</nbZone>
        <numBranche>1</numBranche>
        <absDebZone>0.0</absDebZone>
        <absFinZone>{reach_length}</absFinZone>
        <coefLitMin>{strickler}</coefLitMin>
        <coefLitMaj>{strickler}</coefLitMaj>
      </frottement>
      <zoneStockage>
        <nbProfils>0</nbProfils>
        <numProfil>-0</numProfil>
        <limGauchLitMaj>-0</limGauchLitMaj>
        <limDroitLitMaj>-0</limDroitLitMaj>
      </zoneStockage>
    </parametresCalage>
    <parametresLoisHydrauliques>
      <nb>2</nb>
      <lois>
        <structureParametresLoi>
          <nom>loi_1_hydrogramme</nom>
          <type>1</type>
          <donnees>
            <modeEntree>1</modeEntree>
            <fichier>hydrogramme.loi</fichier>
          </donnees>
        </structureParametresLoi>
        <structureParametresLoi>
          <nom>loi_2_limnigramme</nom>
          <type>2</type>
          <donnees>
            <modeEntree>1</modeEntree>
            <fichier>limnigramme.loi</fichier>
          </donnees>
        </structureParametresLoi>
      </lois>
    </parametresLoisHydrauliques>
    <parametresConditionsInitiales>
      <repriseEtude>
        <repriseCalcul>false</repriseCalcul>
      </repriseEtude>
      <ligneEau>
        <LigEauInit>false</LigEauInit>
      </ligneEau>
    </parametresConditionsInitiales>
    <parametresImpressionResultats>
      <titreCalcul>Flow-MDK synthetic scenario</titreCalcul>
      <impression>
        <impressionCalcul>false</impressionCalcul>
      </impression>
      <pasStockage>
        <premPasTpsStock>1</premPasTpsStock>
        <pasStock>{max(1, int(round(dt)))}</pasStock>
        <pasImpression>1000</pasImpression>
      </pasStockage>
      <resultats>
        <fichResultat>{out_prefix}_ecr.opt</fichResultat>
        <postProcesseur>2</postProcesseur>
      </resultats>
      <listing>
        <fichListing>{out_prefix}.lis</fichListing>
      </listing>
      <fichReprise>
        <fichRepriseEcr>{out_prefix}_ecr.rep</fichRepriseEcr>
      </fichReprise>
      <rubens>
        <ecartInterBranch>1.0</ecartInterBranch>
      </rubens>
      <stockage>
        <stockage2D>false</stockage2D>
      </stockage>
    </parametresImpressionResultats>
  </parametresCas>
</fichierCas>
"""
    path.write_text(xml, encoding="ISO-8859-1")


def _normal_depth(q: float, width: float, strickler: float, slope: float) -> float:
    """Rectangular-channel normal depth from Manning-Strickler (iterative)."""
    h = 0.5
    for _ in range(40):
        q_h = strickler * width * h ** (5.0 / 3.0) * slope ** 0.5
        h *= min(max((q / q_h) ** 0.6, 0.5), 2.0)
    return h


def _fill_init_line(z: np.ndarray, width: np.ndarray, mean_k: float,
                    slope: float, q_base: float) -> np.ndarray:
    """Wet monotone init line: normal depth at the outlet, then filled from
    downstream upwards so every section stays above its bed. Bed-form humps
    that poke above the base-flow stage would otherwise leave negative
    depths on the init line and crash the transient kernel."""
    h = _normal_depth(q_base, float(np.mean(width)), mean_k, slope)
    z_surf = np.empty_like(z)
    z_surf[-1] = z[-1] + h
    for i in range(len(z) - 2, -1, -1):
        z_surf[i] = max(z[i] + h, z_surf[i + 1])
    return z_surf


def _write_init_lig(path: Path, x: np.ndarray, z_surf: np.ndarray, q: np.ndarray) -> None:
    """Initial water line in the Mascaret permanent/LIDO listing format.

    This is ``formatFichLig 2`` — the layout of
    ``examples/mascaret/1_Steady_Kernel/init.lig``: a header whose IMAX line
    is read with ``(2(8X,I5))`` followed by X / Z / Q value blocks and
    ``FIN`` (LEC_LIGNE_LIDO). Mascaret interpolates the line onto the
    computation mesh, so the sections only have to span the reach.
    """
    n = len(x)
    lines = [
        "RESULTATS CALCUL,DATE :  Flow-MDK initial water line",
        "FICHIER RESULTAT MASCARET",
        "------------------------------------------------------------------------",
        f" IMAX  ={n:5d} NBBIEF=    1",
        f" I1,I2 =    1     {n}",
    ]

    def block(header: str, values: np.ndarray) -> None:
        lines.append(header)
        for i in range(0, len(values), 5):
            lines.append("".join(f"{v:14.3f}" for v in values[i:i + 5]))

    block("X", x)
    block("Z", z_surf)
    block("Q", q)
    lines.append("FIN")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def build_project_from_template(scenario: Scenario, workdir: Path,
                                template_dir: Path | None = None,
                                steady: bool = False,
                                steady_q: float | None = None) -> Path:
    """Synthetic-scenario project built from a *known-good* real xcas.

    Hand-written steering files miss mandatory elements (e.g.
    parametresGeneraux/sauveModele — pretrait.f90 aborts on them), so we copy
    the validated zxh project and patch the scenario-specific fields:
    geometry, branch extent, mesh, time controls, friction, the two boundary
    laws (inflow hydrogramme + downstream limnigramme) and output names.

    ``steady=True`` produces the SARAP steady-kernel project of the two-stage
    initialisation (plan L1, mirroring examples/mascaret/1_Steady_Kernel):
    code 1, constant ``steady_q`` inflow + normal-depth downstream stage, two
    1 s steps. The transient project (``steady=False``, code 3) starts from
    the ``init.lig`` water line — the SARAP profile when driven through
    scripts/run_partA_mascaret.py, else the fill line written here.
    """
    repo = Path(__file__).resolve().parents[1]
    template_dir = Path(template_dir or repo / "data/real_sources/zxh")
    if workdir.exists():
        shutil.rmtree(workdir)
    shutil.copytree(template_dir, workdir,
                    ignore=shutil.ignore_patterns("*.ftl", "*.opt", "*.lis", "*.rep"))
    for stale in workdir.glob("zx*.loi"):
        stale.unlink()

    static = scenario.node_static
    z, width, strickler = static[:, 0], static[:, 1], static[:, 2]
    dx = scenario.edge_attr[0::2, 0]
    x = np.concatenate([[0.0], np.cumsum(dx)])
    n = len(x)
    mean_k = float(np.mean(strickler))

    meta = scenario.meta
    sp = meta.get("solver_params") or meta["geometry"]  # synthetic scenarios carry both
    dt = float(sp["dt"])
    duration = float(sp["duration"])
    from flow_mdk.gen.scenarios_1d import hydrograph
    class _Params:
        q_base = float(sp.get("q_base", 5.0))  # generator default when unstored
        q_peak = float(sp.get("q_peak", 1.0))
        time_to_peak = float(sp.get("time_to_peak", 3600.0))
        peak_sharpness = float(sp.get("peak_sharpness", 3.0))
        slope = float(meta["geometry"]["slope"])

    params_like = _Params()
    q_base = params_like.q_base
    q_steady = float(steady_q) if steady_q is not None else q_base

    def normal_stage(q: float) -> float:
        return float(z[-1] + _normal_depth(q, float(width[-1]), mean_k, params_like.slope))

    stem = "sarap" if steady else "mascaret"
    write_geometry(workdir / "geometrie", x, z, width)
    if steady:
        write_hydrograph(workdir / "hydrogramme_steady.loi",
                         np.array([0.0, 1.0]), np.array([q_steady, q_steady]))
        write_limnigramme(workdir / "limnigramme_steady.loi",
                          np.array([0.0, 1.0]),
                          np.array([normal_stage(q_steady)] * 2))
    else:
        q_coarse = np.arange(0.0, duration + 1e-9, 60.0)
        q_in = hydrograph(q_coarse, params_like)
        write_hydrograph(workdir / "hydrogramme.loi", q_coarse, q_in)
        # downstream free outflow: normal-depth rating curve Q(Z) (loi type 5).
        # A stage-imposed law is ill-posed where the outlet flow is locally
        # supercritical (bed-form humps push Fr > 1) and the kernel aborts;
        # the rating matches the reference solver's normal-depth outflow.
        # The table spans far below the bed and above any event stage —
        # dry-front states evaluate the law at negative depths, and an
        # out-of-range interpolation aborts the kernel.
        q_ref = max(float(np.max(q_in)), q_base)
        h_peak = _normal_depth(3.0 * q_ref, float(width[-1]), mean_k,
                               params_like.slope)
        h_rating = np.linspace(0.01, h_peak + 2.0, 60)
        z_rating = z[-1] + h_rating
        q_rating = strickler[-1] * width[-1] * h_rating ** (5.0 / 3.0) \
            * params_like.slope ** 0.5
        z_table = np.concatenate([[z[-1] - 2.0], z_rating])
        q_table = np.concatenate([[0.0], q_rating])
        write_tarage(workdir / "tarage.loi", z_table, q_table)
    # uniform-depth initial water line (fallback / standalone use); the SARAP
    # steady profile overwrites it in the two-stage flow
    z_surf = _fill_init_line(z, width, mean_k, params_like.slope, q_base)
    _write_init_lig(workdir / "init.lig", x, z_surf, np.full(n, q_base))

    xcas = workdir / f"{stem}.xcas"
    text = (template_dir / "zx.xcas").read_text(encoding="ISO-8859-1", errors="replace")

    def sub(pattern: str, repl: str, count: int = 1) -> None:
        nonlocal text
        text, k = re.subn(pattern, repl, text, count=count, flags=re.S)
        if k != count:
            raise RuntimeError(f"template patch failed: {pattern[:50]}")

    sub(r"<fichMotsCles>[^<]*</fichMotsCles>", f"<fichMotsCles>{stem}.xcas</fichMotsCles>")
    sub(r"<titreCalcul>[^<]*</titreCalcul>",
        f"<titreCalcul>Flow-MDK synthetic {scenario.name}{' steady' if steady else ''}</titreCalcul>")
    sub(r"<fichier>zx\.geo</fichier>", "<fichier>geometrie</fichier>")
    sub(r"<abscFin>[^<]*</abscFin>", f"<abscFin>{x[-1]:.3f}</abscFin>")
    if steady:
        # SARAP: steady kernel, quasi-static two-step run (official example)
        sub(r"<code>[^<]*</code>", "<code>1</code>")
        sub(r"<critereArret>[^<]*</critereArret>", "<critereArret>2</critereArret>")
        sub(r"<pasTemps>[^<]*</pasTemps>", "<pasTemps>1.0</pasTemps>")
        sub(r"<tempsMax>[^<]*</tempsMax>", "<tempsMax>1.0</tempsMax>")
        sub(r"<nbPasTemps>[^<]*</nbPasTemps>", "<nbPasTemps>2</nbPasTemps>")
        # the steady kernel reads numerical/physical parameters the zx
        # template (a transient project) does not carry; xcasReader returns
        # an empty string for the missing nodes and the run segfaults, so
        # install the official 1_Steady_Kernel blocks wholesale
        sub(r"<parametresModelePhysique>.*?</parametresModelePhysique>",
            "<parametresModelePhysique>\n"
            "      <perteChargeConf>false</perteChargeConf>\n"
            "      <compositionLits>1</compositionLits>\n"
            "      <conservFrotVertical>false</conservFrotVertical>\n"
            "      <elevCoteArrivFront>0.05</elevCoteArrivFront>\n"
            "      <interpolLinStrickler>false</interpolLinStrickler>\n"
            "      <debordement>\n"
            "        <litMajeur>false</litMajeur>\n"
            "        <zoneStock>false</zoneStock>\n"
            "      </debordement>\n"
            "    </parametresModelePhysique>")
        sub(r"<parametresNumeriques>.*?</parametresNumeriques>",
            "<parametresNumeriques>\n"
            "      <calcOndeSubmersion>false</calcOndeSubmersion>\n"
            "      <decentrement>false</decentrement>\n"
            "      <froudeLimCondLim>1000.0</froudeLimCondLim>\n"
            "      <traitImplicitFrot>false</traitImplicitFrot>\n"
            "      <hauteurEauMini>0.005</hauteurEauMini>\n"
            "      <implicitNoyauTrans>false</implicitNoyauTrans>\n"
            "      <optimisNoyauTrans>false</optimisNoyauTrans>\n"
            "      <perteChargeAutoElargissement>false</perteChargeAutoElargissement>\n"
            "      <termesNonHydrostatiques>false</termesNonHydrostatiques>\n"
            "      <apportDebit>0</apportDebit>\n"
            "      <attenuationConvection>false</attenuationConvection>\n"
            "    </parametresNumeriques>")
    else:
        # variable time step capped by Courant 0.8 (nbCourant comes from the
        # template), stopped at the event duration (critereArret 1 =
        # tempsMax); the fixed 30 s step of the diffusive reference is
        # unstable in the full-SWE kernel
        sub(r"<critereArret>[^<]*</critereArret>", "<critereArret>1</critereArret>")
        sub(r"<pasTempsVar>[^<]*</pasTempsVar>", "<pasTempsVar>true</pasTempsVar>")
        # 10 s initial step (variable stepping then follows Courant 0.8);
        # the diffusive reference's 30 s step is fragile at start-up
        sub(r"<pasTemps>[^<]*</pasTemps>", f"<pasTemps>{min(dt, 10.0)}</pasTemps>")
        sub(r"<tempsMax>[^<]*</tempsMax>", f"<tempsMax>{duration}</tempsMax>")
        sub(r"<nbPasTemps>[^<]*</nbPasTemps>",
            f"<nbPasTemps>{int(duration / dt)}</nbPasTemps>")
    sub(r"<numDerProf>[^<]*</numDerProf>", f"<numDerProf>{n}</numDerProf>")
    sub(r"<numDerProfPlage>[^<]*</numDerProfPlage>", f"<numDerProfPlage>{n}</numDerProfPlage>")
    sub(r"<pasEspacePlage>[^<]*</pasEspacePlage>",
        f"<pasEspacePlage>{x[-1] / (n - 1):.3f}</pasEspacePlage>")
    sub(r"<coefLitMin>[^<]*</coefLitMin>", f"<coefLitMin>{float(np.mean(strickler)):.3f}</coefLitMin>")
    sub(r"<coefLitMaj>[^<]*</coefLitMaj>", f"<coefLitMaj>{float(np.mean(strickler)):.3f}</coefLitMaj>")
    if steady:
        sub(r"<typeCond>[^<]*</typeCond>", "<typeCond>1 2</typeCond>")
    else:
        # downstream = rating curve (boundary condition type 4, cf. Test13)
        sub(r"<typeCond>[^<]*</typeCond>", "<typeCond>1 4</typeCond>")
    sub(r"<numLoi>[^<]*</numLoi>", "<numLoi>1 2</numLoi>")
    # friction zone must lie within the synthetic reach (template reach is longer)
    sub(r"<absDebZone>[^<]*</absDebZone>", "<absDebZone>0.000</absDebZone>")
    sub(r"<absFinZone>[^<]*</absFinZone>", f"<absFinZone>{x[-1]:.3f}</absFinZone>")
    # no lateral inflow singularities in synthetic scenarios: empty the whole
    # apports/deversoirs block (the zx template carries 4 lateral Q apports)
    sub(r"<parametresApportDeversoirs>.*?</parametresApportDeversoirs>",
        "<parametresApportDeversoirs/>")
    # initial water line: file-based (modeEntree 1). Keyboard-mode inline
    # lines (modeEntree 2) segfault the v8p4 kernel and the unsteady kernels
    # refuse to start without a line at all (err 349). The SARAP steady stage
    # keeps LigEauInit false (as in the official 1_Steady_Kernel example).
    if steady:
        sub(r"<ligneEau>.*?</ligneEau>",
            "<ligneEau>\n        <LigEauInit>false</LigEauInit>\n      </ligneEau>")
    else:
        sub(r"<ligneEau>.*?</ligneEau>",
            "<ligneEau>\n"
            "        <LigEauInit>true</LigEauInit>\n"
            "        <modeEntree>1</modeEntree>\n"
            "        <fichLigEau>init.lig</fichLigEau>\n"
            "        <formatFichLig>2</formatFichLig>\n"
            "        <nbPts>-0</nbPts>\n"
            "      </ligneEau>")
    # wholesale replacement of the laws block with our two boundary laws
    hydro_law = "hydrogramme_steady.loi" if steady else "hydrogramme.loi"
    if steady:
        stage_law_type, stage_law_file = 2, "limnigramme_steady.loi"
    else:
        stage_law_type, stage_law_file = 5, "tarage.loi"
    sub(r"<parametresLoisHydrauliques>.*?</parametresLoisHydrauliques>",
        "<parametresLoisHydrauliques>\n      <nb>2</nb>\n      <lois>\n"
        "        <structureParametresLoi>\n          <nom>loi_inflow</nom>\n"
        "          <type>1</type>\n          <donnees>\n"
        "            <modeEntree>1</modeEntree>\n"
        f"            <fichier>{hydro_law}</fichier>\n          </donnees>\n"
        "        </structureParametresLoi>\n"
        "        <structureParametresLoi>\n          <nom>loi_downstream</nom>\n"
        f"          <type>{stage_law_type}</type>\n          <donnees>\n"
        "            <modeEntree>1</modeEntree>\n"
        f"            <fichier>{stage_law_file}</fichier>\n          </donnees>\n"
        "        </structureParametresLoi>\n      </lois>\n"
        "    </parametresLoisHydrauliques>")
    sub(r"<fichResultat>[^<]*</fichResultat>", f"<fichResultat>{stem}_ecr.opt</fichResultat>")
    sub(r"<fichListing>[^<]*</fichListing>", f"<fichListing>{stem}.lis</fichListing>")
    sub(r"<fichRepriseEcr>[^<]*</fichRepriseEcr>", f"<fichRepriseEcr>{stem}.rep</fichRepriseEcr>")
    if steady:
        sub(r"<premPasTpsStock>[^<]*</premPasTpsStock>", "<premPasTpsStock>1</premPasTpsStock>")
        sub(r"<pasStock>[^<]*</pasStock>", "<pasStock>1</pasStock>")
    else:
        # ~10-minute output cadence; <pasStock> counts TIME STEPS, not seconds
        out_every = max(1, int(round(600.0 / dt)))
        sub(r"<premPasTpsStock>[^<]*</premPasTpsStock>", "<premPasTpsStock>1</premPasTpsStock>")
        sub(r"<pasStock>[^<]*</pasStock>", f"<pasStock>{out_every}</pasStock>")
    xcas.write_text(text, encoding="ISO-8859-1")
    return xcas


# --------------------------------------------------------------------- #
# backends
# --------------------------------------------------------------------- #
def run_docker(workdir: Path, image: str) -> None:
    workdir = workdir.resolve()
    cmd = [
        "docker", "run", "--rm", "-v", f"{workdir}:/work", "-w", "/work",
        image, "bash", "-lc", "source /etc/profile.d/setenv.sh && mascaret mascaret.xcas",
    ]
    subprocess.run(cmd, check=True)


def run_telapy(workdir: Path) -> None:
    try:
        from telapy.mascaret import Mascaret  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "telapy is not importable; activate the TELEMAC python environment "
            "(telemac-mascaret/scripts/python3) or use --backend docker"
        ) from exc
    workdir = workdir.resolve()
    mascot = Mascaret(str(workdir / "mascaret.xcas"))
    mascot.run_all()
    mascot.delete(True)


# --------------------------------------------------------------------- #
# Optyca result parsing (column layout validated in M1)
# --------------------------------------------------------------------- #
def parse_opthyca(path: Path) -> dict:
    """Parse the .opt (Optyca) output into per-time-stamp section tables.

    Returns {"times": [...], "absc": [...], "z": [...], "q": [...]} where
    each entry is a list over (time, section) pairs in file order.
    """
    times, absc, z, q = [], [], [], []
    for line in path.read_text(encoding="ISO-8859-1", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        try:
            values = [float(p) for p in parts]
        except ValueError:
            continue  # header / section markers
        if len(values) >= 6:
            times.append(values[0])
            absc.append(values[2])
            z.append(values[3])
            q.append(values[5])
    return {"times": times, "absc": absc, "z": z, "q": q}


def attach_truth(scenario_path: Path, workdir: Path) -> Scenario:
    """Convert a parsed .opt into the scenario's dynamic arrays (M1 hook)."""
    scenario = load_scenario(scenario_path)
    result = parse_opthyca(workdir / "mascaret_ecr.opt")
    scenario.meta["solver"] = "mascaret_rezo"
    scenario.meta["mascaret"] = {
        "workdir": str(workdir),
        "raw_frames": len(result["times"]),
        "note": "gridding onto scenario sections is completed in M1",
    }
    save_scenario(scenario, scenario_path)
    return scenario


# --------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, help="1D scenario .npz")
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--backend", choices=("docker", "telapy", "files-only"),
                        default="files-only")
    parser.add_argument("--image", default=TELEMAC_IMAGE)
    parser.add_argument("--check", action="store_true",
                        help="generate a one-section smoke project and exit")
    args = parser.parse_args()

    workdir = Path(args.workdir)
    if args.check:
        from flow_mdk.gen.scenarios_1d import Scenario1DParams, generate_1d_scenario

        scenario = generate_1d_scenario(
            Scenario1DParams(num_sections=5, duration=600.0, dt=10.0, seed=0), "check"
        )
    else:
        scenario = load_scenario(args.scenario)

    xcas = build_project_from_template(scenario, workdir)
    print(f"project written to {workdir} ({xcas.name})")

    if args.backend == "docker":
        run_docker(workdir, args.image)
        if not args.check:
            attach_truth(Path(args.scenario), workdir)
            print("mascaret run finished; truth attached")
        else:
            print("mascaret run finished (check project)")
    elif args.backend == "telapy":
        run_telapy(workdir)
        print("mascaret run finished (telapy)")
    else:
        print("files-only mode: run manually inside the telemac image with")
        print(f"  docker run --rm -v {workdir.resolve()}:/work -w /work {args.image} mascaret mascaret.xcas")


if __name__ == "__main__":
    main()
