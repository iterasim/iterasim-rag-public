# FOAM FATAL probes for iteraSim RAG Reviewer-loop testing

Intentionally-broken OpenFOAM v2506 cases for measuring how quickly and
correctly the iteraSim RAG agent's Reviewer loop diagnoses and fixes a
broken run. Cases P1 and P2 are derived from the lid-driven cavity (fast
canonical solution); P3 is derived from `pitzDaily` (backward-facing
step + kOmegaSST); P4 is derived from the `flange` snappyHexMesh
tutorial.

## Probes

| Probe                | Failure class            | Broken file                     | What the agent must do                                                            |
|----------------------|--------------------------|---------------------------------|-----------------------------------------------------------------------------------|
| `case_dict_fix/`     | Runtime dictionary       | `constant/transportProperties`  | Add the missing `nu` entry, re-run `icoFoam`                                      |
| `case_mesh_fix/`     | Mesh definition          | `system/blockMeshDict`          | Add the two missing corner vertices, re-run `blockMesh` + `icoFoam`               |
| `case_turb_bc/`      | Turbulence BC mismatch   | `0.orig/omega`                  | Switch `omega` wall BC from `zeroGradient` back to `omegaWallFunction`            |
| `case_snappy_q/`     | snappyHexMesh cell qual. | `system/meshQualityDict`        | Relax the strict thresholds so snappy retains valid cells; re-run + `checkMesh`   |

Each probe subdirectory has:

- `0/` (or `0.orig/`), `constant/`, `system/`, `case.foam` — the OpenFOAM
  case, ready to load.
- `README.md` — probe-specific description, first-run log excerpt,
  ground-truth fix, and scoring criteria.
- `expected/` — the captured first-run log(s) and the canonical post-fix
  reference file(s) to diff the agent's output against.

## Failure modes covered

`case_dict_fix` and `case_mesh_fix` exercise the two most frequent
`FOAM FATAL` classes: a missing runtime-dictionary entry (`nu` in
`transportProperties`) and a truncated mesh-definition dictionary
(missing corner vertices in `blockMeshDict`).

`case_turb_bc` and `case_snappy_q` exercise two "runs-but-wrong" failure
modes that are diagnosed by inspecting the log rather than by a
`FOAM FATAL`:

- **case_turb_bc**: the closure is switched to `kOmegaSST` but the
  `omega` field retains a `zeroGradient` BC on both walls; the solver
  converges, but the log is dominated by `bounding omega, min: -763.5
  max: 78947` warnings, i.e. an unphysical wall-shear model.
- **case_snappy_q**: the `meshQualityDict` thresholds are set
  unreasonably strict (`maxNonOrtho 10`, `minTetQuality 0.5`, etc.),
  so snappyHexMesh completes but produces
  ~66k illegal faces and `checkMesh` reports `Failed 1 mesh checks`.

## Suggested test protocol

For each probe:

1. Load the case directory into the iteraSim RAG UI (or feed it to the
   agent via the `handle_universal_simulation_request` entry point).
2. Prompt with something minimal that mirrors a user's post-crash
   report, e.g.:
   - `case_dict_fix`: *"My icoFoam run just died with a FOAM FATAL.
     Please look at the case and fix it so it runs to endTime."*
   - `case_mesh_fix`: *"blockMesh fails on this case. Fix it so the
     mesh generates and icoFoam completes."*
   - `case_turb_bc`: *"simpleFoam converges but the log is full of
     'bounding omega' warnings. Fix it so the turbulence closure is
     consistent."*
   - `case_snappy_q`: *"snappyHexMesh completes but checkMesh reports
     illegal faces. Fix the case so the mesh passes checkMesh."*
3. Start a wall-clock timer at prompt submission.
4. Stop the timer when the agent reports success (or gives up).
5. Score against the criteria in the probe's `README.md`:
   - Diagnosis correct? (file identified)
   - Patch correct? (matches ground truth semantically)
   - Regeneration correct? (blockMesh / snappyHexMesh re-run as needed)
   - Verification correct? (final run reaches `endTime` without
     `FATAL`, or the mesh passes `checkMesh`)
6. Record: wall-clock, number of Reviewer iterations, whether the agent
   consulted the log or blindly guessed, and any wrong turns.

## Baseline reference numbers

- Unbroken lid-driven cavity: ~4 s (blockMesh ~0.2 s + icoFoam ~4 s).
- Unbroken pitzDaily kOmegaSST: ~5 s to 243 iterations
  (SIMPLE convergence).
- Unbroken flange snappyHexMesh: ~6 s.

Any wall-clock beyond ~1 minute for the Reviewer loop is dominated by
retrieval / reasoning, not by OpenFOAM itself.
