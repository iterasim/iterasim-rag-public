# Probe P3: turbulence-BC mismatch (`case_turb_bc`)

Base tutorial: 2D backward-facing step (`pitzDaily`, OpenFOAM v2506), run
under `simpleFoam` with an incompressible steady-state RAS closure.

## Ground-truth corruption

The canonical tutorial uses `RASModel kEpsilon` with `epsilonWallFunction`
on both walls.  The probe changes the closure to `kOmegaSST` in
`constant/turbulenceProperties` **but leaves the wall boundary condition
for `omega` as `zeroGradient`** on both walls.  The correct pairing for
`kOmegaSST` requires `omegaWallFunction` on any wall patch.

Broken file: `0.orig/omega` — `upperWall` and `lowerWall` set to
`zeroGradient` instead of `omegaWallFunction`.

Reference file: `expected/omega.fixed` — the canonical BC.

## First-run behaviour

The solver does **not** terminate with a `FOAM FATAL`.  `simpleFoam`
reports "SIMPLE solution converged in 243 iterations" and writes the
final field.  However, the log is dominated by

```
bounding omega, min: -763.495 max: 78946.7 average: 1912.19
```

warnings on almost every iteration (78 lines of `bounding omega` in the
captured log).  Negative and hugely-spiking `omega` values imply an
unphysical wall-shear model; the eddy viscosity computed on the walls is
therefore inconsistent with the k-omega SST formulation.

Captured first-run log: `expected/log.simpleFoam.broken`.

## What the agent must do

1. Recognise that the closure has been changed to `kOmegaSST` in
   `constant/turbulenceProperties`.
2. Recognise that `kOmegaSST` requires `omegaWallFunction` (or an
   equivalent low-Reynolds `omega` boundary condition) on wall patches
   — the solver log alone does **not** flag this as a `FOAM FATAL`, only
   as a `bounding omega` warning.
3. Restore the `upperWall` and `lowerWall` entries in `0.orig/omega`
   (and, if the agent uses `restore0Dir`, in `0/omega` as well) to
   `omegaWallFunction` with `value $internalField`.
4. Re-run `blockMesh` and `simpleFoam` and confirm that the `bounding
   omega` warnings disappear.

## Scoring criteria

- **Diagnosis correct?** The agent identifies the wall BC on `omega` as
  the fault (not the internal field, not `nut`, not the turbulence
  model itself).
- **Patch correct?** The final `omega` file matches `expected/omega.fixed`
  on `upperWall` and `lowerWall`.
- **Verification correct?** A re-run of `simpleFoam` shows no `bounding
  omega` warnings in the log.
