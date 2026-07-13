# Probe P4: snappyHexMesh cell-quality (`case_snappy_q`)

Base tutorial: flange snappyHexMesh case (`mesh/snappyHexMesh/flange`,
adapted for OpenFOAM v2506), meshing a rigid flange surface embedded in
a rectangular block.

## Ground-truth corruption

The canonical tutorial pairs `system/snappyHexMeshDict` with a
`system/meshQualityDict` that includes the standard v2506 defaults
(`maxNonOrtho 65`, `minTetQuality 1e-9`, ...).  Under those thresholds
snappy produces a mesh that passes `checkMesh`.

The probe replaces `system/meshQualityDict` with unreasonably strict
thresholds:

- `maxNonOrtho 10`  (canonical: 65)
- `maxInternalSkewness 1`  (canonical: 4)
- `minTetQuality 0.5`  (canonical: 1e-9)
- `minTwist 0.05`, `minDeterminant 0.001`, `minFaceWeight 0.05`,
  `minVolRatio 0.01` (canonical: `-1` = disabled)

Broken file: `system/meshQualityDict`.

Reference file: `expected/meshQualityDict.fixed` — the canonical
`#includeEtc "caseDicts/mesh/generation/meshQualityDict.cfg"` shim.

Refinement remains at the tutorial default `level (2 2)` on the flange
surface, so the mesh is not intrinsically bad — it is only the quality
gates that cause the failure.

## First-run behaviour

The solver toolchain is `blockMesh` → `surfaceFeatureExtract` →
`snappyHexMesh` → `checkMesh`.  `snappyHexMesh` reaches the end of the
snap stage and reports:

```
Finished meshing with 66348 illegal faces (concave, zero area or negative
cell pyramid volume)
Finished meshing in = 6.32 s.
```

It exits `0`, so there is no `FOAM FATAL`.  However the subsequent
`checkMesh -constant` reports:

```
    Mesh non-orthogonality Max: 50.5237 average: 10.7581
 ***Error in face pyramids: 6 faces are incorrectly oriented.
    Max skewness = 3.4415 OK.
Failed 1 mesh checks.
```

Captured first-run logs: `expected/log.snappyHexMesh.broken`,
`expected/log.checkMesh.broken`.

## What the agent must do

1. Read `log.snappyHexMesh` and notice the "Finished meshing with N
   illegal faces" message together with the strict quality thresholds
   in `system/meshQualityDict`.
2. Recognise that the corrupted `meshQualityDict` (max non-orthogonality
   10\deg, no tolerance for skew/twist/det) is far too strict for
   snappy to keep the flange transition cells.
3. Relax the thresholds to the OpenFOAM v2506 defaults — the simplest
   form is `#includeEtc "caseDicts/mesh/generation/meshQualityDict.cfg"`
   as in `expected/meshQualityDict.fixed`.
4. Re-run `blockMesh`, `surfaceFeatureExtract`, `snappyHexMesh` and
   `checkMesh` and confirm the mesh is now reported as `Mesh OK`.

## Scoring criteria

- **Diagnosis correct?** The agent identifies `system/meshQualityDict`
  as the fault, not the STL, not `snappyHexMeshDict`, not `blockMeshDict`.
- **Patch correct?** The final `meshQualityDict` matches the canonical
  v2506 default (equivalent to `expected/meshQualityDict.fixed`).
- **Verification correct?** A re-run of the meshing toolchain reports
  `Mesh OK` from `checkMesh` at the constant time.
