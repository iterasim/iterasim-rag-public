# Canonical-Knowledge Layer — structure

This document describes the structure of the static
canonical-knowledge layer referred to as `cfd_knowledge` in the
paper. The full text of the layer is proprietary
(see [`README.md`](README.md) for the licensing note); the
section-level structure is released here so that referees and
independent implementers can reproduce the *shape* of the layer
without redistributing the exact text.

The layer is a hand-authored, versioned Python module that is
injected as system context into the Architect / InputWriter /
Reviewer agents at inference time. It is not retrieved from the
vector store: it is always present. Every entry below is a single
top-level string constant in the module.

## Guides shipped in the layer

| Guide constant                    | Approx. size (lines) | Purpose                                                                                                    |
|-----------------------------------|:--------------------:|------------------------------------------------------------------------------------------------------------|
| `SOLVER_SELECTION_GUIDE`          | 36                   | Decision tree from physics regime (incompressible / compressible / multiphase / buoyant / …) to solver.    |
| `GEOMETRY_MESH_GUIDE`             | 46                   | High-level mesh-generation strategy (blockMesh vs snappy vs external tool).                                |
| `BLOCKMESH_EXPERT`                | 45                   | Concrete `blockMeshDict` recipes (vertices, blocks, boundary block, gradings).                             |
| `TURBULENCE_GUIDE`                | 24                   | Turbulence-closure selection (k-epsilon vs k-omega SST vs LES) and matching wall-function pairs.           |
| `BC_REFERENCE`                    | 57                   | Boundary-condition catalogue by patch type × field (U, p, T, k, epsilon, omega, alpha).                    |
| `FVSCHEMES_GUIDE`                 | 53                   | Discretisation-scheme defaults per solver family.                                                          |
| `FVSOLUTION_GUIDE`                | 36                   | Linear-solver defaults (PCG/DIC, GAMG, smoothSolver, PBiCGStab) with typical tolerances and relaxations.   |
| `CONTROLDICT_GUIDE`               | 32                   | `controlDict` defaults (endTime, deltaT, writeControl, adjustTimeStep) per solver family.                  |
| `BENCHMARK_RECIPES`               | 309                  | Full example cases for the tutorial canon (cavity, pitzDaily, hotRoom, damBreak, particleColumn, mixerVessel, …). |
| `WORKSHOP_PATCH_DISCIPLINE`       | 67                   | House rules on patch naming, patch-type consistency, and cross-file consistency checks.                    |
| `GEOMETRY_PATTERNS`               | 20                   | Common geometry-generation patterns (block, wedge, curved boundary, features).                             |
| `BLOCKMESH_GENERATION_SYSTEM`     | 46                   | Prompt-side system message for automated `blockMesh` generation.                                           |
| `GMSH_GENERATION_SYSTEM`          | 47                   | Prompt-side system message for automated Gmsh geometry / meshing.                                          |
| `PARAVIEW_EXPERT`                 | 43                   | Post-processing recipes (slicing, iso-surfaces, integral quantities).                                      |
| `PYFOAM_EXPERT`                   | 35                   | Common PyFoam interactions (monitor residuals, restart from latest time).                                  |
| `FREECAD_WORKFLOW`                | 30                   | Geometry-to-STL export patterns from FreeCAD.                                                              |
| `GMSH_EXPERT`                     | 52                   | Gmsh scripting patterns (.geo file recipes).                                                               |

Total: **17 guides · 978 lines** of hand-authored expert text.

## How the layer enters the pipeline

At inference time each of the three agents receives:

1. The dynamically retrieved context block $\mathcal{X}_i$ produced
   by the three-stage retrieval pipeline (paper §II.C).
2. The canonical-knowledge layer above, concatenated in an order
   that depends on the agent's role (the Architect receives
   `SOLVER_SELECTION_GUIDE` and `TURBULENCE_GUIDE` first, the
   InputWriter receives all the `*_GUIDE` and `*_EXPERT` blocks
   relevant to the identified solver family, and the Reviewer
   receives `WORKSHOP_PATCH_DISCIPLINE` first).

The paper's ablation (§III.B, "--canonical" row) quantifies the
contribution of this layer: disabling it drops the overall
retrieval score from **75.6 %** to **25.5 %** on the same
benchmark, i.e. **−50.1 percentage points**. Together with the
multi-query expansion (**−49.7 percentage points**), these are the
two load-bearing components of the retrieval tier.

## Reproducing the layer

An independent implementer can reproduce the *shape* of the layer
by authoring one Python constant per row of the table above, using
the sizes as a target and the purpose column as a scope specifier.
An open-source reference implementation is planned for the
companion technical note.

For access to the full production text of the layer under an
academic collaboration or commercial licence, see the *"Access to
the RAG engine"* section of the top-level [`README.md`](README.md).
