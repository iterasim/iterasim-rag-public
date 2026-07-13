# Probe: dictionary-parameter FOAM FATAL

**Base case**: lid-driven cavity (icoFoam), OpenFOAM v2506.
**Failure class**: runtime dictionary is missing a required entry — no mesh change needed.

## What is broken

`constant/transportProperties` — the kinematic viscosity entry `nu` has been removed.
`blockMesh` succeeds; `icoFoam` FATALs at start-up while reading transport properties.

## Expected FATAL message

```
--> FOAM FATAL IO ERROR: (openfoam-2506)
Entry 'nu' not found in dictionary
"constant/transportProperties"

file: constant/transportProperties
```

Full log captured at `expected/log.icoFoam.fatal`.

## Ground-truth fix

Add the missing entry back to `constant/transportProperties`:

```
nu              0.01;
```

The canonical, working version is at `expected/transportProperties.fixed` — diff
whatever the agent writes against it.

## Success criteria for the agent

1. **Diagnosis** — the agent identifies `constant/transportProperties` as the file
   at fault (not `controlDict`, not `fvSolution`).
2. **Patch** — the agent writes an `nu` entry with:
   - correct name (`nu`, lower-case);
   - correct value (`0.01` reproduces the reference; any positive scalar ≥ 1e-4
     is physically defensible for a lid-driven cavity, but `0.01` is the
     benchmark ground truth).
3. **Verification** — after the patch, `blockMesh` + `icoFoam` runs to
   `endTime = 0.5` without a `FOAM FATAL` line and produces a `log.icoFoam`
   ending with `End`.

## How to run manually

```
source /usr/lib/openfoam/openfoam2506/etc/bashrc
blockMesh > log.blockMesh 2>&1
icoFoam   > log.icoFoam   2>&1
```

## Timing baseline (unbroken cavity, for reference)

- `blockMesh`: ~0.2 s
- `icoFoam` end-to-end: ~4 s

Any agent that needs > 60 s of wall-clock to resolve this after receiving the
FATAL log is losing time on retrieval / reasoning, not on the OpenFOAM run.
