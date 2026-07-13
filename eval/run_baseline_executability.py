#!/usr/bin/env python3
"""
Baseline executability harness.

For each benchmark case in Category A (6 zero-shot reference cases), copy the
gold-standard case from <repo>/runs/
into a fresh work dir, run blockMesh + the target solver, and score 0-4 per
the benchmark_test_plan.md rubric.

This measures the *ceiling* of what IteraSim-LLM could achieve if it perfectly
reproduces the reference cases. The agent-driven number (what IteraSim-LLM
actually achieves from a natural-language prompt) will be reported separately.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path("<repo>")
BENCHMARK = REPO_ROOT / "backend" / "rag_evaluation" / "benchmark_queries.json"
RESULTS_ROOT = REPO_ROOT / "backend" / "rag_evaluation" / "results"
RUNS_ROOT = Path("<repo>/runs")
WORK_ROOT = Path("/tmp/iterasim_exec_baseline")
OF_BASHRC = "/usr/lib/openfoam/openfoam2506/etc/bashrc"

# case_id → (runs/<subdir>, solver_binary, needs_setFields)
# For B/C/D cases we test the underlying *base* configuration; the modification
# is applied by the agent (not measured here). This gives the executability
# ceiling: does the benchmark's physical envelope hold on OpenFOAM v2506?
CASE_MAP = {
    # ── Category A: zero-shot reference cases (measured directly)
    "A1": ("cavity",          "icoFoam",                     False),
    "A2": ("pitzDaily",       "simpleFoam",                  False),
    "A3": ("hotRoom",         "buoyantBoussinesqSimpleFoam", False),
    "A4": ("damBreak",        "interFoam",                   True),
    "A5": ("particleColumn",  "MPPICFoam",                   False),
    "A6": ("mixerVessel",     "simpleFoam",                  False),
    # ── Category B: few-shot cases → base is the case they set up
    "B1": ("pitzDaily",       "simpleFoam",                  False),
    "B2": ("hotRoom",         "buoyantBoussinesqSimpleFoam", False),
    "B3": ("cavity",          "icoFoam",                     False),  # base cavity; mod → pimpleFoam
    "B4": ("damBreak",        "interFoam",                   True),   # base damBreak; mod → bubble column
    # ── Category C: parameter modifications on a specific base case
    "C1":  ("cavity",         "icoFoam",                     False),
    "C2":  ("cavity",         "icoFoam",                     False),  # unsteady mod
    "C3":  ("cavity",         "icoFoam",                     False),  # mesh 2x
    "C4":  ("hotRoom",        "buoyantBoussinesqSimpleFoam", False),
    "C5":  ("hotRoom",        "buoyantBoussinesqSimpleFoam", False),  # air→water
    "C6":  ("damBreak",       "interFoam",                   True),
    "C7":  ("damBreak",       "interFoam",                   True),   # water→oil
    "C8":  ("particleColumn", "MPPICFoam",                   False),
    "C9":  ("mixerVessel",    "simpleFoam",                  False),
    "C10": ("pitzDaily",      "simpleFoam",                  False),
    # ── Category D: zero-shot turbulence swaps → base is pitzDaily unless noted
    "D1": ("pitzDaily",       "simpleFoam",                  False),
    "D2": ("pitzDaily",       "simpleFoam",                  False),
    "D3": ("pitzDaily",       "simpleFoam",                  False),
    "D4": ("pitzDaily",       "simpleFoam",                  False),
    "D5": ("cavity",          "icoFoam",                     False),  # laminar → turbulent cavity
    "D6": ("pitzDaily",       "simpleFoam",                  False),  # LES swap; base is RANS pitzDaily
    "D7": ("hotRoom",         "buoyantBoussinesqSimpleFoam", False),
    "D8": ("mixerVessel",     "simpleFoam",                  False),
}


def sh(cmd: str, cwd: Path, timeout: int = 600) -> tuple[int, str]:
    """Run a bash command with OpenFOAM env sourced. Returns (exit_code, combined_output)."""
    wrapped = f"source {OF_BASHRC} 2>/dev/null; cd '{cwd}' && {cmd}"
    try:
        res = subprocess.run(
            ["bash", "-c", wrapped],
            capture_output=True, text=True, timeout=timeout,
        )
        return res.returncode, (res.stdout or "") + (res.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"


def prep_case(runs_subdir: str, work_dir: Path) -> bool:
    """Copy 0/, constant/, system/ from runs/<subdir>/ into work_dir. Returns True on success."""
    src = RUNS_ROOT / runs_subdir
    if not src.is_dir():
        print(f"    ERROR: source case missing: {src}")
        return False
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("0", "0.orig", "constant", "system"):
        s = src / sub
        if s.is_dir():
            shutil.copytree(s, work_dir / sub)
    # If only 0.orig exists, copy it to 0 (OpenFOAM convention)
    if not (work_dir / "0").is_dir() and (work_dir / "0.orig").is_dir():
        shutil.copytree(work_dir / "0.orig", work_dir / "0")
    return (work_dir / "system").is_dir() and (work_dir / "constant").is_dir()


def score(work_dir: Path, solver: str, expected_key_checks: list[str]) -> tuple[int, dict]:
    """Apply 0-4 rubric via filesystem inspection."""
    ev: dict = {}
    poly = work_dir / "constant" / "polyMesh"
    ev["mesh_files"] = poly.is_dir() and any(poly.iterdir())

    bm_log = work_dir / "log.blockMesh"
    if bm_log.is_file():
        bm = bm_log.read_text(errors="ignore")
        ev["blockmesh_end"] = "End" in bm and "FOAM FATAL" not in bm
    else:
        ev["blockmesh_end"] = None

    if not ev["mesh_files"]:
        return 0, ev

    sv_log = work_dir / f"log.{solver}"
    if not sv_log.is_file():
        return 1, ev
    sv = sv_log.read_text(errors="ignore")
    ev["solver_ran_to_end"] = ("End" in sv) and ("FOAM FATAL" not in sv) and ("FOAM exiting" not in sv)
    ev["solver_fatal"] = "FOAM FATAL" in sv or "FOAM exiting" in sv
    ev["log_tail"] = sv[-500:]

    if not ev["solver_ran_to_end"]:
        return 2, ev

    # Score 3: solver ran end-to-end. Check for score 4 via expected_key_checks.
    # NOTE: cavity's benchmark uses 'codedfixedvalue' as a NEGATIVE check
    # (must NOT appear); we don't distinguish here — key_hits/misses reported.
    key_hits, key_misses = [], []
    for key in expected_key_checks:
        kl = key.lower()
        found = False
        for root, _, files in os.walk(work_dir):
            for name in files:
                if name.lower() == kl:
                    found = True
                    break
                try:
                    if kl in (Path(root) / name).read_text(errors="ignore").lower():
                        found = True
                        break
                except Exception:
                    pass
            if found:
                break
        (key_hits if found else key_misses).append(key)
    ev["key_hits"] = key_hits
    ev["key_misses"] = key_misses
    return (4 if not key_misses else 3), ev


def run_one(case_id: str, expected_key_checks: list[str]) -> dict:
    runs_subdir, solver, needs_setfields = CASE_MAP[case_id]
    work = WORK_ROOT / case_id
    print(f"\n──── {case_id} ({runs_subdir}, solver={solver}) ────")

    if not prep_case(runs_subdir, work):
        return {"case_id": case_id, "score": 0, "error": "prep_failed"}

    t0 = time.time()

    bm_code, bm_out = sh("blockMesh > log.blockMesh 2>&1", work, timeout=180)
    print(f"    blockMesh exit={bm_code}")
    if bm_code != 0:
        print(f"    blockMesh output tail: {bm_out[-300:]}")

    if needs_setfields and (work / "system" / "setFieldsDict").is_file():
        sf_code, _ = sh("setFields > log.setFields 2>&1", work, timeout=60)
        print(f"    setFields exit={sf_code}")

    sv_code, sv_out = sh(f"{solver} > log.{solver} 2>&1", work, timeout=600)
    print(f"    {solver} exit={sv_code}")
    if sv_code != 0:
        print(f"    solver output tail: {sv_out[-300:]}")

    elapsed = time.time() - t0
    s, ev = score(work, solver, expected_key_checks)
    print(f"    SCORE: {s}/4  ({elapsed:.1f}s)")
    if ev.get("key_misses"):
        print(f"    key_misses: {ev['key_misses']}")

    return {
        "case_id": case_id,
        "solver": solver,
        "runs_subdir": runs_subdir,
        "score": s,
        "elapsed_s": round(elapsed, 1),
        "evidence": ev,
    }


def main():
    with open(BENCHMARK) as f:
        benchmark = json.load(f)
    lookup = {c["case_id"]: c for c in benchmark}

    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = RESULTS_ROOT / f"baseline_exec_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Cache base-case results so we don't rerun the same OpenFOAM run 10x
    # for e.g. C1-C3 which all share `cavity`.
    base_cache: dict[str, dict] = {}

    def get_or_run(case_id: str) -> dict:
        runs_subdir, solver, _ = CASE_MAP[case_id]
        key = (runs_subdir, solver)
        if key in base_cache:
            cached = dict(base_cache[key])
            cached["case_id"] = case_id
            cached["from_cache"] = True
            return cached
        r = run_one(case_id, lookup[case_id].get("expected_key_checks", []))
        base_cache[key] = r
        return r

    results = []
    for case_id in CASE_MAP.keys():
        results.append(get_or_run(case_id))

    (out_dir / "results.json").write_text(json.dumps(results, indent=2))

    def cat_summary(letter: str) -> tuple[int, int, int, int]:
        cat = [r for r in results if r["case_id"].startswith(letter)]
        total = sum(r.get("score", 0) for r in cat)
        passing = sum(1 for r in cat if r.get("score", 0) >= 3)
        return len(cat), passing, total, 4 * len(cat)

    print("\n" + "=" * 60)
    print("BASELINE EXECUTABILITY SUMMARY (all 28 cases)")
    print("=" * 60)
    for r in results:
        cache_mark = "  (cached)" if r.get("from_cache") else ""
        print(f"  {r['case_id']:<4}  score={r.get('score', 0)}/4  ({r.get('elapsed_s', '-')}s)  {r.get('runs_subdir', '')}{cache_mark}")

    print("\n  Per-category:")
    for cat in "ABCD":
        n, p, t, mx = cat_summary(cat)
        print(f"    Category {cat}:  {p}/{n} pass @>=3   aggregate {t}/{mx}")
    total = sum(r.get("score", 0) for r in results)
    passing = sum(1 for r in results if r.get("score", 0) >= 3)
    print(f"\n  Overall: {passing}/{len(results)} pass @>=3   aggregate {total}/{4*len(results)}")
    print(f"\n  Wrote: {out_dir/'results.json'}")


if __name__ == "__main__":
    main()
