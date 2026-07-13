# TESTS

This document lists every evaluation performed for the paper
**"IteraSim RAG: A Multi-Stage Retrieval-Augmented Agentic Back-End
for OpenFOAM-Based Computational Fluid Dynamics"** (submitted to
Computer Physics Communications, 2026), the prompt / input each
test received, the scoring
rule, and the recorded outcome, together with the artefact in this
repository that backs each number.

All results were produced against OpenFOAM v2506 (the target release
of the deployed IteraSim RAG back-end) and were captured on
2026-06-26 (retrieval tier) and 2026-07-05 (executability tier).

---

## 1. Retrieval-tier evaluation (28 cases)

**What it measures.** Whether the three-stage retrieval pipeline
(query expansion $\rightarrow$ RRF fusion $\rightarrow$ MMR
diversification), when driven by each benchmark prompt, returns a
context block that contains the physics and dictionary tags a
practitioner would need to write the case correctly.

**Prompt fed to the RAG back-end.** For each of the 28 benchmark
cases (A1..A6, B1..B4, C1..C10, D1..D8), the natural-language
prompt was taken verbatim from
`benchmark/benchmark_test_plan.md` (or equivalently
`benchmark/benchmark_queries.json`).  No agent orchestration or
tool use was invoked at this tier — the retrieval endpoint alone
was called, and its returned context block $\mathcal{X}_i$ was
scored.

**Scoring rule (Eq. (3) of the paper).**

$$
s_i = 0.80 \cdot \frac{\lvert T_i \cap \mathrm{tokens}(\mathcal{X}_i)\rvert}{\lvert T_i \rvert}
    + 0.20 \cdot \mathbb{1}[\mathrm{solver}_i \in \mathrm{tokens}(\mathcal{X}_i)]
$$

where $T_i = $ `expected_physics_tags` and $\mathrm{solver}_i =$
`expected_solver` for case $i$.  The 0.80 / 0.20 split favours
tag coverage while preserving a solver-identification term.

**Results.**

| Category | $n$ | Mean $\bar s$ | Median $s_{\mathrm{med}}$ | $n_\text{perfect}$ |
|----------|----|--------------|--------------------------|---------------------|
| A — Zero-shot            |  6 | 59.1 % | 70.2 %  | 0 |
| B — Few-shot             |  4 | 82.0 % | 80.0 %  | 1 |
| C — Alt. conditions      | 10 | 90.7 % | 100.0 % | 6 |
| D — Turbulence swap      |  8 | 74.1 % | 75.2 %  | 0 |
| **Overall**              | **28** | **77.9 %** | **79.1 %** | **7** |

Retrieval latency: median 2.09 s, p95 2.73 s, max 2.92 s
(single-threaded, sub-3 s across all 28 cases).

**Artefact.** The raw per-case scores and derived summary live at:

- `eval/results/reference_case_executability_28.json` (per-case
  executability data, see test 2)
- The retrieval-tier score file itself (`results.json`) is produced
  by the retrieval endpoint of the proprietary back-end and is not
  redistributed; the aggregate numbers above and the per-case
  breakdown in `paper_figures.py` are computed from it.

---

## 2. End-to-end executability, reference-case column (28 cases)

**What it measures.** Whether the *canonical* OpenFOAM tutorial
files for every benchmark case (built by hand from the standard
tutorial suite, **not** by any agent) can be meshed and run
through the target solver on OpenFOAM v2506, and whether the
resulting case exposes the tags the benchmark schema expects.
This establishes the *ceiling* of what the agent-driven column
can achieve.

**Input.** For each case in `benchmark/benchmark_queries.json`,
the harness copies the canonical case files, runs `blockMesh`
followed by the case-specific solver (`icoFoam`, `simpleFoam`,
`buoyantBoussinesqSimpleFoam`, `interFoam`, `MPPICFoam`), and
`setFields` where the multiphase configuration requires it.  No
natural-language prompt is used at this stage — this measures
the OpenFOAM toolchain alone, not the RAG agent.

**Scoring rule (five-point rubric).**

| Score | Meaning                                                                   |
|:----:|---------------------------------------------------------------------------|
| 0 | mesher (`blockMesh`, `snappyHexMesh`) fails or produces an invalid mesh      |
| 1 | mesh generates, but the solver aborts at initialisation with a `FOAM FATAL` |
| 2 | solver starts but exits with a `FOAM FATAL` before `endTime`                |
| 3 | solver runs to `endTime` without any `FATAL`                                |
| 4 | solver runs to `endTime` **and** every user-specified parameter tag is set  |

**Results.**

| Category | $n$ | Sum of scores | Reached `endTime` ($\ge 3$) | Elapsed |
|----------|-----|---------------|-----------------------------|--------|
| A | 6  | 20 / 24  | 6 / 6  | 70.3 s |
| B | 4  | 14 / 16  | 4 / 4  | 33.1 s |
| C | 10 | 34 / 40  | 10 / 10 | 97.9 s |
| D | 8  | 25 / 32  | 8 / 8  | 67.1 s |
| **Overall** | **28** | **93 / 112** | **28 / 28** | **268 s** |

The score-3 shortfalls are all due to benchmark-schema
`key_check` entries that the reference configuration does not
use by construction (e.g. cavity's `codedFixedValue` — the
correct BC is `fixedValue` for the lid-driven cavity;
mixerVessel's `MRFZoneList` — replaced by `MRFProperties` in
v2506).  These are schema artefacts, not physical failures.

**Wall-clock per case.**

| Case         | Solver                        | Elapsed |
|--------------|-------------------------------|--------|
| cavity          | `icoFoam`                          | 3.9 s |
| pitzDaily       | `simpleFoam`                       | 9.4 s |
| hotRoom         | `buoyantBoussinesqSimpleFoam`      | 10.6 s |
| damBreak        | `interFoam`                        | 9.2 s |
| particleColumn  | `MPPICFoam`                        | 31.6 s |
| mixerVessel     | `simpleFoam`                       | 5.6 s |
| **6-config sum** |                              | **70.3 s** |

**Artefacts.**

- `eval/results/reference_case_executability_28.json` — the full
  28-record per-case JSON: `case_id`, `solver`, `runs_subdir`,
  `score`, `elapsed_s`, `evidence.blockmesh_end`,
  `evidence.solver_ran_to_end`, `evidence.solver_fatal`,
  `evidence.log_tail`, `evidence.key_hits`, `evidence.key_misses`.
- `eval/run_baseline_executability.py` — the runner that
  produced this JSON.  Set the `<repo>` roots to your local
  paths, provide a working OpenFOAM v2506 install, and re-run.

---

## 3. End-to-end executability, agent-driven cavity (1 case)

**What it measures.** Whether the RAG orchestrator
(Architect $\rightarrow$ InputWriter $\rightarrow$ Reviewer),
given only the natural-language prompt, produces a case that
runs to `endTime` and reproduces the reference velocity field.

**Prompt.** `benchmark/exec_end_to_end/cavity/prompt.txt`
(the standard lid-driven cavity spec: unit square,
20$\times$20 mesh, moving lid at 1 m/s, `icoFoam`, endTime 0.5 s).

**Test protocol.**

1. Prompt is fed to the RAG orchestrator.
2. Generated case is written to `cavity_rag/`.
3. `blockMesh` and `icoFoam` are invoked.
4. Final-time velocity field is rendered next to the reference
   case (`eval/render_ref_vs_rag.py`).

**Result.** The two velocity-magnitude fields (agent-generated
vs canonical tutorial) are visually indistinguishable at
contouring resolution.  The RAG case ran to `endTime` without
any `FOAM FATAL` (see `cavity_rag/log.icoFoam`).

**Artefacts.**

- `benchmark/exec_end_to_end/cavity/prompt.txt`
- `benchmark/exec_end_to_end/cavity/reference_case/`
- `benchmark/exec_end_to_end/cavity/cavity_rag/` (includes
  `log.blockMesh`, `log.checkMesh`, `log.icoFoam`)
- `eval/render_ref_vs_rag.py` — reproduces the comparison figure
  as `fig_ref_vs_rag.pdf`.

---

## 4. Reviewer-loop FATAL probes P1 and P2 (measured)

**What it measures.** Whether the Reviewer agent, when handed a
broken OpenFOAM case and a minimal post-crash user message,
diagnoses and repairs the case within its ten-cycle loop bound.

### Probe P1 — runtime-dictionary FATAL (`case_dict_fix`)

- **Broken artefact.**  `constant/transportProperties` has the
  `nu` (kinematic viscosity) entry removed.
- **User prompt.**
  *"My icoFoam run just died with a FOAM FATAL. Please look at
  the case and fix it so it runs to endTime."*
- **Diagnostic sequence executed by the Reviewer**
  (from the run transcript):
  read `system/`, confirm solver from `controlDict`, invoke
  `Allrun` (which fails under the missing entry), re-run
  through internal `run_simulation_autonomous`, capture the
  FATAL, run substring extraction on `Entry 'nu' not found`.
- **Result.** A targeted patch is written to
  `constant/transportProperties` restoring
  `nu 1.5e-5;`; `icoFoam` re-run reaches `endTime` = 0.5 s with
  monotonically decreasing residuals.  **Diagnosed + repaired
  in a single Reviewer cycle.**

### Probe P2 — mesh-definition FATAL (`case_mesh_fix`)

- **Broken artefact.**  `system/blockMeshDict` has its
  `vertices` list truncated to six entries; the `blocks` entry
  still references eight vertices.
- **User prompt.**
  *"blockMesh fails on this case. Fix it so the mesh generates
  and icoFoam completes."*
- **Diagnostic sequence.**  Open `blockMeshDict`, localise the
  malformed `vertices` list, restore the two missing corner
  vertices via internal `edit_file`, re-run `blockMesh` then
  `checkMesh` (which reports `Mesh OK`), generate an `Allrun`
  and invoke `icoFoam`.
- **Result.** Solver reaches `endTime` without a `FATAL`; the
  recovered pressure field coincides with the canonical cavity
  reference to within numerical round-off.  **Diagnosed +
  repaired in a single Reviewer cycle.**

**Artefacts.**

- `benchmark/exec_fatal_probes/case_dict_fix/` — broken case,
  `expected/log.icoFoam.fatal`, `expected/transportProperties.fixed`.
- `benchmark/exec_fatal_probes/case_mesh_fix/` — broken case,
  `expected/log.blockMesh.fatal`, `expected/blockMeshDict.fixed`.

---

## 5. Reviewer-loop probes P3 and P4 (constructed; RAG evaluation deferred)

**Purpose.** Extend the probe taxonomy to two further
executability failure classes so that the Reviewer loop can be
exercised against a "runs but wrong" scenario and a mesh-quality
scenario in addition to the two `FOAM FATAL` classes above.

### Probe P3 — turbulence-BC mismatch (`case_turb_bc`)

- **Base case.** `pitzDaily` backward-facing step.
- **Corruption.** `constant/turbulenceProperties` is switched
  from `kEpsilon` to `kOmegaSST`, but the `omega` wall boundary
  condition in `0.orig/omega` is left as `zeroGradient` on both
  walls (the canonical `omegaWallFunction` is the reference
  fix).
- **Observed behaviour.** `simpleFoam` converges in 243
  iterations and does *not* emit a `FOAM FATAL`.  However the
  captured log contains 78 `bounding omega, min: -763.5
  max: 78947` warnings — negative $\omega$ values imply an
  unphysical wall-shear model.
- **Expected agent action.** Diagnose the `kOmegaSST` /
  `zeroGradient` mismatch from the log warnings, replace the
  wall BC with `omegaWallFunction`.
- **RAG evaluation.** Deferred to a companion technical note.

### Probe P4 — snappyHexMesh cell quality (`case_snappy_q`)

- **Base case.** `flange` snappyHexMesh tutorial.
- **Corruption.** `system/meshQualityDict` is seeded with
  over-strict thresholds: `maxNonOrtho 10`,
  `maxInternalSkewness 1`, `minTetQuality 0.5`, plus
  `minTwist / minDeterminant / minFaceWeight / minVolRatio`
  all set instead of $-1$.
- **Observed behaviour.** `snappyHexMesh` finishes with
  `Finished meshing with 66348 illegal faces`, and the
  subsequent `checkMesh -constant` reports
  `***Error in face pyramids: 6 faces are incorrectly
  oriented. Failed 1 mesh checks.`
- **Expected agent action.** Relax `meshQualityDict` back to
  the v2506 defaults (`#includeEtc
  "caseDicts/mesh/generation/meshQualityDict.cfg"`), re-run
  the mesher, confirm `checkMesh` passes.
- **RAG evaluation.** Deferred to a companion technical note.

**Artefacts.**

- `benchmark/exec_fatal_probes/case_turb_bc/` — broken case,
  `expected/log.simpleFoam.broken`, `expected/omega.fixed`.
- `benchmark/exec_fatal_probes/case_snappy_q/` — broken case,
  `expected/log.snappyHexMesh.broken`,
  `expected/log.checkMesh.broken`,
  `expected/meshQualityDict.fixed`.

---

## Reproducing the numbers

Every number in this document (retrieval means, per-category
executability sums, per-case elapsed times) can be reproduced from
the shipped artefacts:

```bash
# retrieval-tier: mean 77.9%, median 79.1%
python3 eval/paper_figures.py    # regenerates fig_retrieval_* PDFs

# executability-tier: 93/112, 268 s total
python3 -c "
import json
d = json.load(open('eval/results/reference_case_executability_28.json'))
from collections import defaultdict
cat = defaultdict(lambda: {'n':0,'sum':0,'t':0.0,'reached':0})
for r in d:
    c = cat[r['case_id'][0]]
    c['n'] += 1; c['sum'] += r['score']; c['t'] += r['elapsed_s']
    if r['score'] >= 3: c['reached'] += 1
for k in 'ABCD':
    v = cat[k]
    print(f'{k}: {v[\"sum\"]}/{v[\"n\"]*4}  {v[\"reached\"]}/{v[\"n\"]}  {v[\"t\"]:.1f}s')
"

# end-to-end cavity: render agent vs reference velocity fields
python3 eval/render_ref_vs_rag.py

# probe P1/P2: transcripts and expected diffs
cat benchmark/exec_fatal_probes/case_dict_fix/README.md
cat benchmark/exec_fatal_probes/case_mesh_fix/README.md

# probe P3/P4: broken cases + first-run captured logs + canonical fix
cat benchmark/exec_fatal_probes/case_turb_bc/README.md
cat benchmark/exec_fatal_probes/case_snappy_q/README.md
```

The IteraSim RAG back-end itself (the retrieval pipeline, router,
canonical knowledge layer, and Architect / InputWriter / Reviewer
orchestrator) is **not** shipped in this repository — see the
main [`README.md`](README.md) for licensing and academic
collaboration information.
