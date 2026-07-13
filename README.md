# IteraSim RAG — Benchmark & Evaluation Kit

Companion evaluation artefacts for the paper

> **IteraSim RAG: A Multi-Stage Retrieval-Augmented Agentic Assistant
> for OpenFOAM-Based Computational Fluid Dynamics.**
> P. Kumar *et al.*, submitted to *Physics of Fluids*, 2026.

This repository ships **only the benchmark and evaluation code** needed
to reproduce the retrieval-tier numbers reported in the paper and to
run the Reviewer-loop `FOAM FATAL` probes against any RAG back-end.

> **The IteraSim RAG engine itself — the multi-stage retrieval
> pipeline, the dual-mode router, the Architect–InputWriter–Reviewer
> orchestrator, the canonical knowledge layer and the ingestion
> pipeline — is proprietary to IteraSim and is *not* part of this
> release.** It is available for academic collaboration and commercial
> licensing on request; see [Access to the RAG engine](#access-to-the-rag-engine).

The manuscript itself (LaTeX source, figures) is *not* included in this
repository; it is distributed through the journal channel.

## Repository layout

```
iterasim-rag-public/
├── README.md              this file
├── TESTS.md               every test performed for the paper: prompts, scoring rules, results
├── CANONICAL_LAYER.md     structural map of the canonical-knowledge layer (17 guides, 978 lines)
├── LICENSE                MIT for the artefacts released here
├── .gitignore
│
├── benchmark/
│   ├── benchmark_test_plan.md         28-case natural-language prompts
│   ├── benchmark_queries.json         machine-readable case metadata (36 = 28 scored + 8 Category E)
│   ├── parse_benchmark.py             plan  →  JSON parser
│   ├── exec_fatal_probes/             Reviewer-loop probes
│   │   ├── README.md
│   │   ├── case_dict_fix/             runtime-dictionary FATAL          (measured)
│   │   ├── case_mesh_fix/             mesh-definition FATAL             (measured)
│   │   ├── case_turb_bc/              kOmegaSST + zeroGradient omega    (constructed)
│   │   └── case_snappy_q/             snappyHexMesh strict quality gates (constructed)
│   └── exec_end_to_end/               end-to-end reference-vs-RAG case
│       └── cavity/
│           ├── prompt.txt             the natural-language prompt
│           ├── reference_case/        canonical OpenFOAM tutorial
│           └── cavity_rag/            RAG-generated case + run logs
│
└── eval/
    ├── paper_figures.py               figure-regeneration script (config-driven)
    ├── make_per_case_table.py         per-case LaTeX table generator
    ├── render_ref_vs_rag.py           reference-vs-RAG cavity comparison
    ├── run_baseline_executability.py  28-case reference-case exec runner (0-4 rubric)
    └── results/
        ├── reference_case_executability_28.json    captured scores + log tails for all 28 cases
        ├── ablation_leave_one_out.json              5-config leave-one-out ablation on retrieval
        └── ablation_summary.md                      human-readable ablation table
```

## What is **not** in this repository

The following components are the commercial IP of IteraSim:

- `rag_engine.py` — three-stage retrieval pipeline (query expansion, RRF, MMR) and the deterministic dual-mode router.
- `agent.py`, `sim_planner.py`, `sim_reviewer.py`, `mesh_agent.py` — the Architect–InputWriter–Reviewer orchestrator.
- `cfd_knowledge.py` — canonical knowledge layer contents (solver-selection decision trees, turbulence-closure guides, boundary-condition selectors, discretisation defaults, meshing recipes).
- `ingest_all_v2.py`, `ingest_*.py` — corpus ingestion pipeline.
- `universal_workflow.py` — end-to-end DevOps pipeline that drives meshing, execution and monitoring.
- Vector database contents and ingested knowledge corpus.
- Internal system prompts of the three agents.
- Desktop GUI / floating chat panel that wraps the back-end.

The paper describes each of these components at the level required to
understand and replicate the *methodology*, but this repository ships
neither the source code nor the trained/prompt-tuned weights.

## Using the benchmark against your own RAG back-end

1. **Parse the benchmark** into per-case JSON records:

   ```bash
   python3 benchmark/parse_benchmark.py
   ```

   Writes `benchmark/benchmark_queries.json`. Each record has the
   fields `case_id`, `category`, `title`, `query`, `expected_solver`,
   `expected_files`, `expected_key_checks`, `expected_physics_tags`.

   > **Note on Category E.** The file holds **36** records: the **28
   > scored cases** of Categories A–D (6 / 4 / 10 / 8), plus **8
   > Category E** diagnostic queries (solver divergence, alpha/k
   > bounding, `checkMesh` interpretation, `snappyHexMesh` layer
   > coverage, y+ verification, log reading). Category E exercises the
   > *troubleshooting* path rather than case setup. **It is not scored
   > anywhere in the paper** — every number reported there comes from
   > the 28 cases of Categories A–D. Category E is shipped for
   > community use and for the companion technical note. Filter on
   > `category` if you want to reproduce the paper exactly.

2. **Send each query to your RAG back-end** and collect the returned
   context block $\mathcal{X}_i$ as free text.

3. **Score each case** using Eq. (3) of the paper — the composite
   tag-coverage rubric:

   $$s_i = 0.80 \cdot \frac{|T_i \cap \mathrm{tokens}(\mathcal{X}_i)|}{|T_i|} + 0.20 \cdot \mathbb{1}[\mathrm{solver}_i \in \mathrm{tokens}(\mathcal{X}_i)]$$

   where $T_i$ is `expected_physics_tags` and $\mathrm{solver}_i$ is
   `expected_solver`.

4. **Regenerate the paper figures** from your scored JSON:

   ```bash
   python3 eval/paper_figures.py
   ```

   `paper_figures.py` reads a single `CONFIG` dict at the top; edit
   `output_dir`, `dpi`, `font_family` or the category colour palette to
   match your target medium.

## Running the Reviewer-loop probes

Four ready-to-run OpenFOAM v2306+ cases live in
`benchmark/exec_fatal_probes/`, covering the four executability-tier
failure classes of the paper:

| Probe            | Broken file                       | What the agent must do                                                          |
|------------------|-----------------------------------|---------------------------------------------------------------------------------|
| `case_dict_fix`  | `constant/transportProperties`    | restore the missing `nu` entry, re-run `icoFoam`                                |
| `case_mesh_fix`  | `system/blockMeshDict`            | restore the two missing corner vertices, re-run `blockMesh` + `icoFoam`         |
| `case_turb_bc`   | `0.orig/omega` (kOmegaSST closure) | replace `zeroGradient` on the walls with `omegaWallFunction`, re-run `simpleFoam` |
| `case_snappy_q`  | `system/meshQualityDict`          | relax the over-strict quality gates back to the v2506 defaults, re-run snappyHexMesh + `checkMesh` |

Each probe directory ships the corrupted case (`0/` or `0.orig/`,
`constant/`, `system/`), an `expected/` folder with the first-run log
excerpt and the canonical post-fix reference file for diff-based
scoring, and a `README.md` describing the failure, the ground-truth
fix and the scoring criteria.

## Reference-case executability (Table III of the paper)

`eval/run_baseline_executability.py` walks every case in
`benchmark/benchmark_queries.json`, meshes and runs the canonical
OpenFOAM v2506 tutorial for that case, and scores each run on the
0–4 rubric introduced in Sec. III of the paper (0 = mesh fails,
1 = init FATAL, 2 = mid-run FATAL, 3 = runs to `endTime`,
4 = runs to `endTime` and every user-specified parameter tag is
set). The captured per-case scores and log tails from the run that
populated the `reference-case` column of Table III are shipped at
`eval/results/reference_case_executability_28.json` (28 case records
covering categories A–D).

## End-to-end reference-vs-RAG kit

`benchmark/exec_end_to_end/cavity/` ships the natural-language
prompt used to drive the RAG back-end, the canonical OpenFOAM
lid-driven cavity reference case, and the case actually generated by
IteraSim RAG together with its solver logs. From the top of the
repository:

```bash
cd benchmark/exec_end_to_end/cavity/cavity_rag && ./Allrun
python3 ../../../eval/render_ref_vs_rag.py
```

reproduces the reference-vs-RAG velocity-field figure shown in the
paper (`fig_ref_vs_rag.pdf`).

## Access to the RAG engine

The full IteraSim RAG stack (multi-stage retrieval pipeline, dual-mode
router, canonical knowledge layer, agent orchestrator, ingestion
pipeline) is available under:

- **Academic collaboration** — case-by-case, with a short problem statement.
- **Commercial licence** — per-seat, per-project, or platform-integration terms.
- **Hosted API** — time-limited API keys for academic evaluation.

Contact: **pratyush.ethz@gmail.com** (Pratyush Kumar, IteraSim).

## Citation

```bibtex
@article{KumarIteraSim2026,
  author  = {Kumar, P. and others},
  title   = {{IteraSim RAG}: A Multi-Stage Retrieval-Augmented Agentic
             Assistant for {OpenFOAM}-Based Computational Fluid Dynamics},
  journal = {Physics of Fluids},
  year    = {2026},
  note    = {Submitted}
}
```

## License

Artefacts in this repository (benchmark specification, FATAL probes,
scoring scripts, figure regenerators) are released under the **MIT
License** — see `LICENSE`.

The IteraSim RAG engine and its associated knowledge assets are **not**
covered by this license and remain the property of IteraSim.
