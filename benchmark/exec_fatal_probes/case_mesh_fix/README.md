# Probe: mesh-regeneration FOAM FATAL

**Base case**: lid-driven cavity (icoFoam), OpenFOAM v2506.
**Failure class**: mesh definition is malformed — the fix requires editing
`system/blockMeshDict` **and** re-running `blockMesh`.

## What is broken

`system/blockMeshDict` — the `vertices` list has been truncated to 6 entries
(indices 0..5). The `blocks` entry still references vertex indices 6 and 7,
so `blockMesh` FATALs before any mesh is produced.

## Expected FATAL message

```
--> FOAM FATAL IO ERROR: (openfoam-2506)
Point label (6) out of range 0..5 in block
hex (0 1 2 3 4 5 6 7) (20 20 1) grading (1(1) 1(1) 1(1))

file: system/blockMeshDict/blocks at line 43.

    From void Foam::blockDescriptor::check(const Foam::Istream&)
    in file blockDescriptor/blockDescriptor.C at line 101.
```

Full log captured at `expected/log.blockMesh.fatal`.

## Ground-truth fix

Restore the two missing corner vertices (top-back-right and top-back-left) to
the `vertices` list so it has 8 entries, indices 0..7:

```
(1 1 0.1)
(0 1 0.1)
```

The full corrected file is at `expected/blockMeshDict.fixed`. Any consistent
set of eight corner vertices defining a positive-volume hex block is
acceptable — the canonical cavity uses `scale 0.1;` and a unit cube.

## Success criteria for the agent

1. **Diagnosis** — the agent identifies `system/blockMeshDict` as the file at
   fault (not `constant/polyMesh/*`, which does not exist yet, and not any
   runtime dictionary).
2. **Patch** — the agent adds the two missing vertices *in the correct
   position within the vertices list* (indices 6 and 7 must correspond to
   the top-back-right and top-back-left corners) so that the hex block
   `(0 1 2 3 4 5 6 7)` refers to a positive-volume block.
3. **Regeneration** — the agent re-runs `blockMesh` after the patch (this
   distinguishes a mesh-fix from a runtime-dict fix).
4. **Verification** — `blockMesh` writes `constant/polyMesh/` and exits with
   `End`, and the subsequent `icoFoam` run reaches `endTime = 0.5` without a
   `FOAM FATAL`.

## How to run manually

```
source /usr/lib/openfoam/openfoam2506/etc/bashrc
blockMesh > log.blockMesh 2>&1
icoFoam   > log.icoFoam   2>&1
```

## Timing baseline (unbroken cavity, for reference)

- `blockMesh`: ~0.2 s
- `icoFoam` end-to-end: ~4 s

Because this probe requires an additional `blockMesh` re-run inside the
agent's Reviewer loop, expect a longer wall-clock than the dict-fix probe.
Any agent that needs > 90 s to resolve is losing time on
retrieval / reasoning, not on the OpenFOAM runs.
