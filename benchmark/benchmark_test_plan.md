# IteraSim RAG Benchmark Test Plan
> Derived from: OpenFOAMGPT (Phys. Fluids 2025), MetaOpenFOAM, FoamGPT, Foam-Agent, ChatCFD
> Purpose: Evaluate IteraSim RAG across four performance tiers
> Scoring: ✅ Pass | ⚠️ Partial | ❌ Fail

---

## Evaluation Categories

| Category | Description | # Cases |
|---|---|---|
| A | Zero-Shot Prompting | 6 |
| B | Few-Shot Prompting | 4 |
| C | Alternate Conditions (BC / Mesh / Thermophysical / setFields) | 10 |
| D | Zero-Shot Turbulence Model Switching | 8 |

---

## Success Metrics (per case)

| Score | Meaning |
|---|---|
| 0 | Mesh generation fails (`blockMesh` / `snappyHexMesh` error) |
| 1 | Mesh OK, but solver fails on launch |
| 2 | Solver runs but does not converge to endTime |
| 3 | Runs to endTime — physically plausible fields |
| 4 | Runs + all user-specified parameters correctly set (gold standard) |

> **Pass threshold:** Score ≥ 3. Score 4 requires manual inspection.

---

## A. Zero-Shot Prompting

> **Protocol:** Single natural-language prompt only. No examples. No prior conversation. RAG enabled.
> **Goal:** Test whether IteraSim RAG can configure and run a complete OpenFOAM case from scratch with zero user guidance beyond the problem statement.

---

### A1 — Cavity Flow (Laminar, Incompressible)

**Physics:** Lid-driven cavity, laminar 2D incompressible  
**Solver:** `icoFoam`  
**Difficulty:** ⭐ (baseline)

**Prompt:**
```
Set up and run a 2D lid-driven cavity flow simulation in OpenFOAM.
The domain is a unit square. The top wall moves in the x-direction at
1 m/s. All other walls are stationary no-slip. The fluid is water.
Run until t = 0.5 s with deltaT = 0.005 s. Use icoFoam.
```

**Expected files:** `blockMeshDict`, `U`, `p`, `transportProperties`, `controlDict`, `fvSolution`, `fvSchemes`  
**Success criteria:** Score 4 — velocity = 1 m/s on top wall, zero on others, mesh 20×20×1  
**Key check:** `codedFixedValue` NOT used (fixedValue is correct here)

---

### A2 — PitzDaily (Turbulent, RANS)

**Physics:** Backward-facing step, turbulent incompressible  
**Solver:** `simpleFoam` + `kEpsilon`  
**Difficulty:** ⭐⭐

**Prompt:**
```
Set up a steady-state turbulent flow simulation through the PitzDaily
backward-facing step geometry in OpenFOAM. Use the k-epsilon
turbulence model with simpleFoam. Inlet velocity = 10 m/s.
Use the standard PitzDaily mesh from OpenFOAM tutorials.
```

**Expected files:** `U`, `p`, `k`, `epsilon`, `nut`, `turbulenceProperties`, `transportProperties`  
**Success criteria:** Score 3+ — residuals converge below 1e-4  
**Key check:** `turbulenceProperties` sets `RASModel kEpsilon;`

---

### A3 — Hotroom (Buoyancy-Driven Natural Convection)

**Physics:** Turbulent natural convection in a tall 2D cavity  
**Solver:** `buoyantBoussinesqSimpleFoam`  
**Difficulty:** ⭐⭐⭐

**Prompt:**
```
Simulate turbulent natural convection in a tall 2D rectangular cavity
using OpenFOAM. The bottom wall is heated (T = 320 K) and the top
wall is cold (T = 300 K). Left and right walls are adiabatic. Use the
k-epsilon turbulence model. Use buoyantBoussinesqSimpleFoam.
Reference temperature is 310 K. Fluid is air.
```

**Expected files:** `T`, `U`, `p_rgh`, `k`, `epsilon`, `nut`, `alphat`, `thermophysicalProperties`, `g`  
**Success criteria:** Score 3+ — temperature gradient established, buoyancy term active  
**Key check:** `g` vector set correctly as `(0 -9.81 0)`

---

### A4 — Dam Break (Multiphase VOF)

**Physics:** Free-surface dam break, laminar multiphase  
**Solver:** `interFoam`  
**Difficulty:** ⭐⭐⭐

**Prompt:**
```
Set up a 2D dam break simulation in OpenFOAM using the VOF
multiphase solver interFoam. The tank is a 2D square domain.
A column of water occupies the left third of the tank at t=0.
The top boundary is open (atmosphere). All other boundaries are walls.
There is a rectangular obstacle at the centre of the bottom wall.
Run for 1 second.
```

**Expected files:** `alpha.water`, `U`, `p_rgh`, `setFieldsDict`, `transportProperties`, `g`  
**Success criteria:** Score 3+ — `alpha.water` field initialised correctly, interface captured  
**Key check:** `setFieldsDict` uses `boxToCell` to initialise water region

---

### A5 — Particle Column (Multiphase Lagrangian MPPIC)

**Physics:** Particle-laden flow, MPPIC Lagrangian tracking  
**Solver:** `MPPICFoam`  
**Difficulty:** ⭐⭐⭐⭐

**Prompt:**
```
Set up a 2D particle column simulation in OpenFOAM using MPPICFoam.
The domain is a vertical rectangular column with an inlet at the top
and an outlet at the bottom. Fluid is air (incompressible).
Particles have diameter 1e-3 m, density 1000 kg/m³.
Include gravity. Particle-particle collisions should be modelled
using the MPPIC approach.
```

**Expected files:** `kinematicCloudProperties`, `U`, `p`, `cloudProperties`, `injectionModels`  
**Success criteria:** Score 2+ (high complexity — partial credit for correct cloud setup)  
**Key check:** `MPPICCloud` type, `packingModel` present

---

### A6 — Mixed Vessel (Rotating Geometry, MRF)

**Physics:** Rotating mixer, incompressible turbulent  
**Solver:** `pimpleFoam` + MRF zone  
**Difficulty:** ⭐⭐⭐⭐

**Prompt:**
```
Simulate flow in a 2D rotating mixer using OpenFOAM.
The outer cylindrical wall is stationary. The inner wall rotates at
10 rad/s about the z-axis. There are 4 rectangular baffles
on both inner and outer walls. Use pimpleFoam. The fluid is water.
Use the k-epsilon turbulence model.
```

**Expected files:** `MRFProperties`, `U`, `p`, `k`, `epsilon`, `nut`, `fvOptions`  
**Success criteria:** Score 3+ — MRF zone active, rotating frame velocity correctly set  
**Key check:** `MRFZoneList` with correct `omega`

---

## B. Few-Shot Prompting

> **Protocol:** Agent is given 1–2 completed example cases in context before the target prompt.
> **Goal:** Test whether IteraSim RAG can generalise from demonstrated examples to new configurations.

---

### B1 — Cavity → PitzDaily (Geometry Generalisation)

**Few-shot examples in context:** Cavity flow (complete setup)  
**Target task:** PitzDaily  
**Prompt:**
```
[Example: Here is a complete working cavity flow setup: ...]

Now set up the PitzDaily case using simpleFoam with k-epsilon.
Inlet velocity = 10 m/s. Use the same numerical scheme structure as
the cavity case but adapt for turbulent flow.
```
**Success criteria:** Score 4 — turbulence fields initialised, residuals < 1e-4  
**Key check:** `k` and `epsilon` boundary conditions consistent with inlet velocity

---

### B2 — PitzDaily → Hotroom (Solver Transfer)

**Few-shot examples in context:** PitzDaily (RANS, simpleFoam)  
**Target task:** Hotroom  
**Prompt:**
```
[Example: Here is a complete PitzDaily simpleFoam setup: ...]

Now set up a natural convection simulation in a tall heated cavity
using buoyantBoussinesqSimpleFoam. Bottom wall T = 330 K,
top wall T = 290 K, side walls adiabatic. Fluid is air.
```
**Success criteria:** Score 4 — `T` field, `alphat`, `p_rgh` all correct  
**Key check:** Boussinesq approximation `Pr` and `beta` set correctly

---

### B3 — Cavity → Unsteady Cavity (Time-stepping generalisation)

**Few-shot examples in context:** Steady cavity flow  
**Target task:** Unsteady cavity flow  
**Prompt:**
```
[Example: Steady cavity flow setup...]

Now modify this to run as a transient simulation using pimpleFoam.
The top wall velocity should be unsteady: U = 5*sin(2*pi*t/0.1) m/s.
Run for 0.5 seconds with deltaT = 0.001 s, writing every 0.05 s.
```
**Success criteria:** Score 4 — `codedFixedValue` used for unsteady BC  
**Key check:** `code` expression in `U` file matches sine wave formula

---

### B4 — Dam Break → Bubble Column (Multiphase Transfer)

**Few-shot examples in context:** Dam break (interFoam, VOF)  
**Target task:** 2D bubble column  
**Prompt:**
```
[Example: Dam break interFoam setup...]

Now set up a 2D bubble column simulation. Air bubbles are injected
from the bottom of a water-filled rectangular tank at a velocity of
0.1 m/s. Use interFoam with gravity. Domain: 0.1 m wide, 0.5 m tall.
```
**Success criteria:** Score 3+ — `alpha.air` initialised, inlet BC for air phase correct  
**Key check:** Phase inlet uses `inletOutlet` or `fixedValue` on `alpha.air`

---

## C. Alternate Conditions Testing
### (Inlet Velocity / Boundary Conditions / Mesh Resolution / Thermophysical / setFields)

> **Protocol:** Start from a working base case (score ≥ 3 from Category A).
> Then issue a **modification prompt** for a single parameter change.
> **Goal:** Test parameter-level control — can the agent correctly propagate a single change through all affected files?

---

### C1 — Cavity: Inlet Velocity Change

**Base case:** Cavity flow (A1)  
**Modification prompt:**
```
Increase the top wall velocity from 1 m/s to 5 m/s.
Update all relevant files.
```
**Files to check:** `U` (top wall fixedValue)  
**Success criteria:** `value uniform (5 0 0)` in `U`, no other files unnecessarily changed

---

### C2 — Cavity: Unsteady Sinusoidal BC

**Base case:** Cavity flow (A1)  
**Modification prompt:**
```
Change the top wall velocity to an unsteady condition:
U_x = 5 * sin(2*pi*t/0.1) m/s. The simulation should remain transient.
```
**Files to check:** `U` — must switch to `codedFixedValue`  
**Success criteria:** Score 4 — `codedFixedValue` with correct code expression  
**Key check:** `code` block compiles correctly in OpenFOAM

---

### C3 — PitzDaily: Mesh Refinement

**Base case:** PitzDaily (A2)  
**Modification prompt:**
```
Increase the mesh resolution by a factor of 2 in both x and y
directions. Update blockMeshDict accordingly.
```
**Files to check:** `blockMeshDict` — cell counts doubled  
**Success criteria:** Score 4 — cell count exactly doubled, hex vertices consistent

---

### C4 — Hotroom: Temperature Boundary Condition Change

**Base case:** Hotroom (A3)  
**Modification prompt:**
```
Change the hot wall temperature from 320 K to 350 K
and the cold wall temperature from 300 K to 280 K.
```
**Files to check:** `T` boundary conditions  
**Success criteria:** `fixedValue uniform 350` on bottom, `fixedValue uniform 280` on top

---

### C5 — Hotroom: Thermophysical Property Change

**Base case:** Hotroom (A3)  
**Modification prompt:**
```
Change the working fluid from air to water.
Update all relevant thermophysical properties including density,
dynamic viscosity, thermal conductivity, and specific heat.
```
**Files to check:** `thermophysicalProperties`, `transportProperties`  
**Success criteria:** `rho=1000`, `mu=1e-3`, `Cp=4182`, `kappa=0.6` (approximate)  
**Key check:** Prandtl number Pr = μCp/κ ≈ 6.99 (water at 300 K)

---

### C6 — Dam Break: setFields — Change Water Column Position

**Base case:** Dam break (A4)  
**Modification prompt:**
```
Move the initial water column from the left third of the tank
to the right third. Update setFieldsDict accordingly.
```
**Files to check:** `setFieldsDict` — `boxToCell` min/max coordinates  
**Success criteria:** `box (0.67 0 0) (1.0 0.33 0.1)` (or equivalent right third)

---

### C7 — Dam Break: Change Liquid from Water to Oil

**Base case:** Dam break (A4)  
**Modification prompt:**
```
Change the liquid from water to oil. Use density = 900 kg/m³
and kinematic viscosity = 1e-4 m²/s for the oil phase.
```
**Files to check:** `transportProperties` — `rho`, `nu` for phase1  
**Success criteria:** `rho 900`, `nu 1e-4` for liquid phase

---

### C8 — Particle Column: Change Particle Diameter and Density

**Base case:** Particle column (A5)  
**Modification prompt:**
```
Change the particle diameter from 1 mm to 0.5 mm
and the particle density from 1000 kg/m³ to 2500 kg/m³.
Update all relevant property files.
```
**Files to check:** `kinematicCloudProperties` — `d`, `rho`  
**Success criteria:** `d 5e-4`, `rho 2500` in cloud properties

---

### C9 — Mixed Vessel: Change Angular Velocity

**Base case:** Mixed vessel (A6)  
**Modification prompt:**
```
Change the inner wall rotation speed from 10 rad/s to 20 rad/s.
Update all relevant MRF settings.
```
**Files to check:** `MRFProperties` — `omega` value  
**Success criteria:** `omega 20` in MRF zone definition

---

### C10 — PitzDaily: endTime and Write Interval Change

**Base case:** PitzDaily (A2)  
**Modification prompt:**
```
Change the simulation endTime from 500 to 1000 iterations.
Write results every 100 iterations instead of every 50.
```
**Files to check:** `controlDict`  
**Success criteria:** `endTime 1000`, `writeInterval 100` in controlDict

---

## D. Zero-Shot Turbulence Model Switching

> **Protocol:** Start from a working RANS case (A2 PitzDaily or A3 Hotroom).
> Issue a **turbulence model swap prompt**. Agent must add/remove/modify all required BC fields
> and update `turbulenceProperties` without any example.
> **Goal:** Test physics reasoning — agent must know which fields each model requires.

---

### D1 — kEpsilon → RNG kEpsilon (PitzDaily)

**Base case:** PitzDaily with `kEpsilon`  
**Prompt:**
```
Switch the turbulence model from standard k-epsilon to
RNG k-epsilon. Update all relevant files.
```
**Files to check:** `turbulenceProperties` — `RASModel RNGkEpsilon`  
**Success criteria:** Score 4 — model name correct, no field changes needed (same fields)  
**Key check:** `RNGkEpsilon` not `rngkEpsilon` (case-sensitive)

---

### D2 — kEpsilon → kOmegaSST (PitzDaily)

**Base case:** PitzDaily with `kEpsilon`  
**Prompt:**
```
Switch the turbulence model from k-epsilon to k-omega SST.
Ensure all required boundary conditions and initial fields
are updated correctly.
```
**Files to check:** Remove `epsilon`, add `omega`; update `nut` BC to `nutLowReWallFunction`  
**Success criteria:** Score 4 — `omega` field present, `epsilon` removed or unused  
**Key check:** Wall function for `omega` = `omegaWallFunction`, not `epsilonWallFunction`

---

### D3 — kEpsilon → LRR Reynolds Stress Model (PitzDaily)

**Base case:** PitzDaily with `kEpsilon`  
**Prompt:**
```
Switch from k-epsilon to the Launder-Reece-Rodi (LRR)
Reynolds stress model. Add all required Reynolds stress
tensor components as new field files.
```
**Files to check:** Add `R` (Reynolds stress tensor), `epsilon` retained  
**Success criteria:** Score 3+ — `R` field with symmetric tensor IC, model name `LRR`  
**Key check:** This is the hardest RANS switch — `R` field must exist

---

### D4 — kEpsilon → kkLOmega (Three-equation model, PitzDaily)

**Base case:** PitzDaily with `kEpsilon`  
**Prompt:**
```
Switch the turbulence model to the three-equation eddy-viscosity model
k-kl-omega (kkLOmega). This model requires additional transport
equations. Update all boundary conditions and initial fields.
```
**Files to check:** `kl` field added, `omega` field, `turbulenceProperties`  
**Success criteria:** Score 2+ (rare/complex model — partial credit acceptable)  
**Key check:** `kkLOmega` model with `sigmaK`, `sigmaL` coefficients

---

### D5 — Laminar → kEpsilon (Cavity flow, adding turbulence)

**Base case:** Cavity flow (A1), laminar `icoFoam`  
**Prompt:**
```
Convert the cavity flow simulation from laminar icoFoam to turbulent
flow using simpleFoam with the k-epsilon RANS model.
Add all required turbulence files and update boundary conditions.
```
**Files to check:** Add `k`, `epsilon`, `nut`, `turbulenceProperties`; change solver to `simpleFoam`  
**Success criteria:** Score 4 — `k` and `epsilon` initialised, wall functions applied

---

### D6 — LES dynamicKEqn → Smagorinsky (Hotroom)

**Base case:** Hotroom (A3), `dynamicKEqn` LES  
**Prompt:**
```
Switch the LES turbulence model from dynamicKEqn to the standard
Smagorinsky model. Update turbulenceProperties and any
affected boundary conditions.
```
**Files to check:** `turbulenceProperties` — `LESModel Smagorinsky`  
**Success criteria:** Score 4 — Smagorinsky Cs coefficient present, no hanging `k` BC  
**Key check:** LES SGS model does not require `k` or `epsilon` BC — check these are removed

---

### D7 — RANS kEpsilon → kOmegaSST (Hotroom buoyancy case)

**Base case:** Hotroom (A3) with `kEpsilon`  
**Prompt:**
```
Switch the buoyantBoussinesqSimpleFoam hotroom simulation from
k-epsilon to k-omega SST turbulence model.
Ensure all wall functions and initial fields are consistent.
```
**Files to check:** `omega` field with `omegaWallFunction`, `nut` updated  
**Success criteria:** Score 4 — thermal diffusivity `alphat` retained correctly

---

### D8 — Laminar → kEpsilon (Mixed vessel — most complex)

**Base case:** Mixed vessel (A6), initial laminar  
**Prompt:**
```
Add turbulence to the rotating mixer simulation using the
k-epsilon model. Ensure turbulence boundary conditions are
consistent with the rotating MRF zone and the stationary outer wall.
```
**Files to check:** `k`, `epsilon`, `nut` with correct wall functions on MRF and fixed walls  
**Success criteria:** Score 3+ — MRF zone does not break turbulence field initialization  
**Key check:** `k` and `epsilon` must use correct wall functions on rotating inner wall

---

## Evaluation Summary Table (to fill after running)

| ID | Case | Category | Score (0-4) | Notes |
|---|---|---|---|---|
| A1 | Cavity Flow | Zero-shot | | |
| A2 | PitzDaily | Zero-shot | | |
| A3 | Hotroom | Zero-shot | | |
| A4 | Dam Break | Zero-shot | | |
| A5 | Particle Column | Zero-shot | | |
| A6 | Mixed Vessel | Zero-shot | | |
| B1 | Cavity→PitzDaily | Few-shot | | |
| B2 | PitzDaily→Hotroom | Few-shot | | |
| B3 | Cavity→Unsteady | Few-shot | | |
| B4 | DamBreak→Bubble | Few-shot | | |
| C1 | Cavity Velocity | Alt. Conditions | | |
| C2 | Cavity Unsteady BC | Alt. Conditions | | |
| C3 | PitzDaily Mesh | Alt. Conditions | | |
| C4 | Hotroom T-BC | Alt. Conditions | | |
| C5 | Hotroom Fluid | Alt. Conditions | | |
| C6 | DamBreak setFields | Alt. Conditions | | |
| C7 | DamBreak Liquid | Alt. Conditions | | |
| C8 | Particle Props | Alt. Conditions | | |
| C9 | MixedVessel RPM | Alt. Conditions | | |
| C10 | PitzDaily endTime | Alt. Conditions | | |
| D1 | kEps→RNG kEps | Turbulence | | |
| D2 | kEps→kOmegaSST | Turbulence | | |
| D3 | kEps→LRR | Turbulence | | |
| D4 | kEps→kkLOmega | Turbulence | | |
| D5 | Laminar→kEps | Turbulence | | |
| D6 | LES dynamicK→Smag | Turbulence | | |
| D7 | Hotroom kEps→kSST | Turbulence | | |
| D8 | MixedVessel+Turb | Turbulence | | |

---

## How to Run Each Test

```bash
# For each test case:
# 1. Send prompt to IteraSim RAG chat interface
# 2. Agent generates OpenFOAM case files
# 3. Run blockMesh (or snappyHexMesh) and check for errors
# 4. Run solver (e.g., simpleFoam, icoFoam)
# 5. Score the result using the 0-4 scale above

# Example validation script:
blockMesh > blockMesh.log 2>&1
if grep -q "FOAM FATAL ERROR" blockMesh.log; then echo "Score 0"; fi

simpleFoam > solver.log 2>&1
if grep -q "End" solver.log; then echo "Score >= 3"; fi

# Check residuals
grep "Ux" solver.log | tail -5
```

---

## Comparison Baseline (from literature)

| System | A (Zero-shot) | B (Few-shot) | C (Alt. Cond.) | D (Turbulence) |
|---|---|---|---|---|
| OpenFOAMGPT (GPT-4o, no RAG) | 1/6 | — | ~4/10 | ~4/8 |
| OpenFOAMGPT (o1, with RAG) | 6/6 | — | 10/10 | ~7/8 |
| MetaOpenFOAM | 6/8 | — | — | — |
| **IteraSim RAG (target)** | **6/6** | **4/4** | **9/10** | **7/8** |
