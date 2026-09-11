"""Synthetic scenario generators (plan M0).

``scenarios_1d`` ships a lightweight *implicit diffusive-wave* reference
solver so the whole pipeline (generate -> dataset -> train -> evaluate) runs
end-to-end without TELEMAC. For the M1 milestone the same scenario families
are re-run through Mascaret (headless, docker or TelApy, see
``scripts/run_mascaret.py``); the reference solver is then demoted to a
sanity cross-check.
"""
