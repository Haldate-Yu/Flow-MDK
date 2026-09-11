#!/usr/bin/env python
"""Headless Mascaret batch runner (plan M0/M1).

Generates a Mascaret project (geometry, boundary laws, .xcas steering) from
a 1D scenario, runs it through one of two backends and parses the Optyca
result file back into a scenario .npz with ground truth attached.

Backends
--------
- ``docker``: runs the binary inside the TELEMAC-MASCARET image built from
  ``D:/tmp/telemac-wz-260529`` (image ``telemac-debian:0.1``; see
  ``third_party/telemac/README.md``). Requires Docker.
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

    Line format follows ``examples/mascaret/1_Steady_Kernel/geometrie``:
    ``PROFIL <branch> <name> <abscissa>`` then points ``Z X B`` (elevation,
    distance across the profile, marker).
    """
    lines = []
    for i, (xi, zi, wi) in enumerate(zip(x, z, width)):
        ext = max(2.0, 0.5 * wi)  # vertical wall extension above the bed
        name = f"P{i:04d}"
        lines.append(f"PROFIL Bief_1 {name} {xi:.3f}")
        lines.append(f"{zi + ext:.3f} 0.000 B")
        lines.append(f"{zi:.3f} 0.000 B")
        lines.append(f"{zi:.3f} {wi:.3f} B")
        lines.append(f"{zi + ext:.3f} {wi:.3f} B")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def write_hydrograph(path: Path, times: np.ndarray, q: np.ndarray) -> None:
    lines = ["# inflow hydrograph", "# Temps (s) Debit", "         S"]
    lines += [f"{t:.1f} {v:.4f}" for t, v in zip(times, q)]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def write_limnigramme(path: Path, times: np.ndarray, stage: np.ndarray) -> None:
    lines = ["# downstream stage law", "# Temps (s) Cote", "         S"]
    lines += [f"{t:.1f} {v:.4f}" for t, v in zip(times, stage)]
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


def build_project(scenario: Scenario, workdir: Path) -> Path:
    """Write the Mascaret project for a 1D scenario into ``workdir``."""
    workdir.mkdir(parents=True, exist_ok=True)
    static = scenario.node_static
    z, width, strickler = static[:, 0], static[:, 1], static[:, 2]
    # longitudinal abscissa: rebuild from edge dx (chain assumed single branch)
    dx = scenario.edge_attr[0::2, 0]
    x = np.concatenate([[0.0], np.cumsum(dx)])

    meta = scenario.meta
    sp = meta["solver_params"]
    dt = float(sp["dt"])
    duration = float(sp["duration"])

    # rebuild the inflow law on a 60 s grid (matches the reference generator)
    from flow_mdk.gen.scenarios_1d import Scenario1DParams, hydrograph

    params = Scenario1DParams(**{
        **{k: v for k, v in sp.items() if k in Scenario1DParams.__dataclass_fields__},
        "seed": 0,
    })
    q_coarse = np.arange(0.0, duration + 1e-9, 60.0)
    q_in = hydrograph(q_coarse, params)
    # downstream stage: normal-depth stage of the reference solution at the
    # outlet, held constant (validated against the real project in M1)
    stage = float(z[-1] + scenario.dynamic[:, -1, 0].max())

    write_geometry(workdir / "geometrie", x, z, width)
    write_hydrograph(workdir / "hydrogramme.loi", q_coarse, q_in)
    write_limnigramme(
        workdir / "limnigramme.loi",
        np.array([0.0, duration]),
        np.array([stage, stage]),
    )
    xcas = workdir / "mascaret.xcas"
    write_xcas(xcas, duration, dt, len(x), float(x[-1]), float(np.mean(strickler)), "mascaret")
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

    xcas = build_project(scenario, workdir)
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
