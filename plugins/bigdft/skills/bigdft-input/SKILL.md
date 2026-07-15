---
name: bigdft-input
description: Generate BigDFT input files (YAML or Python). Guides the user through calculation type, system setup, DFT parameters, and advanced options. Use when preparing a BigDFT calculation.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# BigDFT Input File Generation

Help the user create a BigDFT input file. The input can be produced as a YAML file (`input.yaml`) for direct use by the `bigdft` executable, or as a Python script using `PyBigDFT.Inputfiles` and `PyBigDFT.InputActions`. **Ask each question one at a time.** Skip questions whose answers are obvious from context.

## Input File Format

BigDFT uses YAML input files with a one-to-one correspondence to Python dictionaries. The top-level keys are:

| Section | Purpose |
|---------|---------|
| `dft` | Core DFT parameters: grid, XC, convergence, spin |
| `posinp` | Atomic positions, unit cell, boundary conditions |
| `geopt` | Geometry optimization |
| `md` | Molecular dynamics |
| `kpt` | K-point sampling (periodic systems) |
| `mix` | SCF mixing / diagonalization |
| `output` | What to write to disk |
| `perf` | Performance tuning, linear scaling control |
| `lin_general` | Linear scaling general parameters |
| `lin_basis` | Linear scaling support function parameters |
| `lin_kernel` | Linear scaling density kernel parameters |
| `lin_basis_params` | Per-element support function parameters |
| `chess` | CheSS solver parameters (FOE, NTPoly) |
| `psolver` | Poisson solver, implicit solvent |
| `tddft` | Linear-response TDDFT |
| `sic` | Self-interaction correction |
| `mode` | Calculator backend (DFT, Lennard-Jones, SIRIUS, etc.) |
| `ig_occupation` | Atomic orbital occupancies for input guess |
| `psppar.<Element>` | Per-element pseudopotential data |

## Questions

### 1 -- Calculation type

```
What type of calculation do you want to run?
  1. Single-point energy
  2. Geometry optimization
  3. Molecular dynamics
  4. Band structure
  5. TDDFT (linear response)
  6. Other / custom
```

### 2 -- System definition

```
How would you like to define your system?
  1. Provide atomic positions inline (I'll help you format them)
  2. Use an existing XYZ or ASCII file (posinp.xyz / posinp.ascii)
  3. Use an existing YAML file as a starting point
  4. Build from PyBigDFT (Systems/Atoms API)
```

If they provide positions inline or an XYZ file, ask about boundary conditions:

```
What boundary conditions?
  1. Free (isolated molecule) -- no cell needed
  2. Periodic (bulk crystal) -- need unit cell vectors
  3. Surface (periodic in x,y; free in z) -- need cell
  4. Wire (periodic in z; free in x,y) -- need cell
```

For periodic systems, ask for unit cell vectors and whether positions are in reduced (fractional) or Cartesian coordinates.

### 3 -- Exchange-correlation functional

```
Which XC functional?
  1. LDA  (ixc: 1)
  2. PBE  (ixc: PBE)  [recommended default]
  3. PBE0 (hybrid, ixc: PBE0)
  4. HF   (Hartree-Fock, ixc: HF)
  5. Other (provide name or ABINIT ixc code)
```

If they choose PBE on a free-boundary system, ask:

```
Add Grimme D3 dispersion correction? (recommended for molecules)
```

### 4 -- Grid parameters

```
Grid spacing and extension:
  - hgrids: wavelet grid spacing in bohr (smaller = more accurate, more expensive)
    Typical: 0.35-0.45 for production, 0.5+ for quick tests
  - rmult: [coarse, fine] radii multipliers
    Typical: [5.0, 8.0] for production, [3.5, 4.5] for quick tests

Use defaults (hgrids=0.4, rmult=[5.0, 8.0]) or customize?
```

### 5 -- Spin and charge

Only ask if relevant (transition metals, radicals, charged systems):

```
System charge and spin:
  - Net charge (qcharge): 0 for neutral
  - Spin polarization (nspin): 1=none, 2=collinear, 4=non-collinear
  - Magnetic moment (mpol): total magnetic moment in Bohr magnetons
```

### 6 -- SCF parameters

For most users, defaults are fine. Only ask if they want to customize:

```
SCF convergence:
  - gnrm_cv: wavefunction gradient norm (default: 1e-4, use 1e-5 for forces)
  - itermax: max iterations (default: 50)
  - Scaling approach: cubic (default) or linear?
```

If linear scaling, ask about the method:
```
Linear scaling kernel method:
  1. DIAG (diagonalization, default)
  2. FOE (Fermi Operator Expansion -- true linear scaling)
  3. NTPoly (polynomial expansion via NTPoly library)
  4. DIRMIN (direct minimization)
```

### 7 -- Calculation-specific options

**For geometry optimization (type 2):**
```
Optimization method:
  1. FIRE (default, robust)
  2. SQNM (Stabilized Quasi-Newton, good for large systems)
  3. LBFGS (Limited-memory BFGS)
  4. DIIS
  5. Other
Max steps? (default: 50)
```

**For molecular dynamics (type 3):**
```
MD parameters:
  - Number of steps (mdsteps)
  - Time step in atomic units (default: 20.67 a.u. ~ 0.5 fs)
  - Initial temperature in K (default: 300)
  - Thermostat: none (NVE) or nose_hoover_chain (NVT)?
  - Wavefunction extrapolation: 0 (none), 2 (BOMD, recommended)
```

**For band structure (type 4):**
```
K-point setup:
  - Method: mpgrid (Monkhorst-Pack) or auto (by resolution)
  - For mpgrid: grid size [nx, ny, nz]
  - For auto: kptrlen (K-space resolution in bohr)
  - Band structure path: provide high-symmetry points or use defaults
```

**For TDDFT (type 5):**
```
TDDFT approach:
  1. TDA (Tamm-Dancoff approximation)
  2. full (full Casida)
How many virtual states? (default: 8)
```

### 8 -- Output options

```
What output do you need?
  - Write orbitals to disk? (format: binary, text, etsf)
  - Write charge density?
  - Cube files around Fermi level?
  - Verbosity level? (0-3, default: 2)
```

### 9 -- Pseudopotentials

```
Pseudopotentials:
  1. Use built-in HGH-K (default, no setup needed)
  2. Use built-in HGH-K with NLCC (set_psp_nlcc)
  3. Use Krack pseudopotentials (set_psp_krack, PBE or LDA)
  4. Use custom psppar files from a directory
```

### 10 -- Advanced options

Only ask if the user seems experienced or explicitly requests:

```
Any advanced options?
  - Implicit solvent (water, ethanol, mesitylene)
  - External electric field
  - GPU acceleration (CUDA or OpenCL)
  - K-point sampling for periodic systems
  - Custom per-element basis parameters (linear scaling)
  - Electronic temperature / smearing
  - Constrained DFT
```

## Output: YAML Format

After collecting answers, generate `input.yaml`. Use comments to explain non-obvious choices.

### Example: Simple Single-Point (Free BC, PBE)

```yaml
dft:
  hgrids: 0.4
  ixc: PBE
  rmult: [5.0, 8.0]
  gnrm_cv: 1.e-4
posinp:
  units: angstroem
  positions:
  - O: [0.000, 0.000, 0.119]
  - H: [0.000, 0.757, -0.476]
  - H: [0.000, -0.757, -0.476]
  properties:
    format: xyz
```

### Example: Geometry Optimization

```yaml
dft:
  hgrids: 0.4
  ixc: PBE
  rmult: [5.0, 8.0]
  gnrm_cv: 1.e-5      # tighter for force accuracy
geopt:
  method: FIRE
  ncount_cluster_x: 50
  betax: 4.0
  frac_fluct: 1.0
posinp:
  units: angstroem
  positions:
  - N: [0.0, 0.0, 0.0]
  - H: [0.0, 1.0, 0.0]
  - H: [-0.87, -0.5, 0.0]
  - H: [0.87, -0.5, 0.0]
```

### Example: Molecular Dynamics (NVT)

```yaml
dft:
  hgrids: 0.4
  ixc: PBE
  rmult: [6.0, 8.0]
  gnrm_cv: 5.e-2       # looser for MD
  itermax: 40
md:
  mdsteps: 1000
  timestep: 20.67       # ~0.5 fs
  temperature: 300.0
  thermostat: nose_hoover_chain
  print_frequency: 10
  wavefunction_extrapolation: 2
posinp: positions.xyz   # external file
```

### Example: Periodic Solid (Si Bulk)

```yaml
dft:
  rmult: [6.0, 8.0]
  ixc: PBE
kpt:
  method: mpgrid
  ngkpt: [4, 4, 4]
posinp:
  units: atomic
  cell: [10.261, 10.261, 10.261]
  positions:
  - Si: [0.0, 0.0, 0.0]
  - Si: [0.5, 0.5, 0.0]
  - Si: [0.5, 0.0, 0.5]
  - Si: [0.0, 0.5, 0.5]
  - Si: [0.25, 0.25, 0.25]
  - Si: [0.75, 0.75, 0.25]
  - Si: [0.75, 0.25, 0.75]
  - Si: [0.25, 0.75, 0.75]
  properties:
    reduced: Yes
```

### Example: Linear Scaling (Large System)

```yaml
dft:
  hgrids: 0.4
  rmult: [5.0, 7.0]
  gnrm_cv: 1.e-4
  itermax: 100
  inputpsiid: linear
  disablesym: Yes
lin_general:
  nit: [2, 3]
  rpnrm_cv: 1.e-6
lin_basis:
  idsx: [5, 0]
  gnrm_cv: [4.e-2, 1.e-2]
lin_kernel:
  linear_method: FOE
  rpnrm_cv: 1.e-8
lin_basis_params:
  C:
    ao_confinement: 2.7e-2
    confinement: 2.7e-2
    rloc: 4.7
    rloc_kernel: 8.0
    rloc_kernel_foe: 15.0
  H:
    nbasis: 1
    ao_confinement: 4.9e-2
    confinement: 4.9e-2
    rloc: 4.0
    rloc_kernel: 8.0
    rloc_kernel_foe: 15.0
chess:
  foe:
    ef_interpol_det: 1.e-12
    fscale: 5.e-2
posinp:
  units: angstroem
  positions:
  - C: [0.0, 0.0, 0.0]
  # ... more atoms
```

### Example: Spin-Polarized (Transition Metal)

```yaml
dft:
  ixc: PBE
  nspin: 2             # collinear spin
  mpol: 5              # magnetic moment in Bohr magnetons
  gnrm_cv: 5.e-4
  itermax: 20
  nrepmax: 2           # re-diagonalizations (or use 'accurate')
posinp:
  positions:
  - Mn: [0.0, 0.0, 0.0]
  - Mn: [0.0, 0.0, 5.0]
```

### Example: Non-Collinear Spin

```yaml
dft:
  nspin: 4             # non-collinear
  gnrm_cv: 5.e-4
  disablesym: Yes
```

### Example: Dispersion Correction

```yaml
dft:
  hgrids: 0.4
  ixc: PBE (ABINIT)    # ABINIT flavor needed for some dispersion
  dispersion: 5         # Grimme D3
  disablesym: Yes
```

### Example: Implicit Solvent

```yaml
dft:
  hgrids: 0.4
  ixc: PBE
psolver:
  environment:
    cavity: soft-sphere
    epsilon: 78.36       # water
    fact_rigid: 1.18
    delta: 0.625
    cavitation: Yes
    gammaS: 72.0
    alphaS: -60.5
    betaV: 0.0
    itermax: 20
    minres: 1.e-4
```

### Example: With Custom Pseudopotentials

```yaml
dft:
  ixc: PBE
psppar.O:
  Pseudopotential type: HGH-K + NLCC
  Atomic number: 8
  No. of Electrons: 6
  Pseudopotential XC: -101130
  Local Pseudo Potential (HGH convention):
    Rloc: 0.3455
    Coefficients (c1 .. c4): [-11.744, 1.907, 0.0, 0.0]
  Non Linear Core Correction term:
    Rcore: 0.345
    Core charge: 9.021
  NonLocal PSP Parameters:
  - Channel (l): 0
    Rloc: 0.368
    h_ij terms: [10.859, -0.430, 0.0, -2.129, 0.0, 0.0]
```

### Example: Atomic Occupation Control

```yaml
ig_occupation:
  Si:
    3s: 2.0
    3p: [0.667, 0.667, 0.667]
    3d: 0.0
```

### Example: GPU Acceleration

```yaml
perf:
  accel: OCLGPU         # OpenCL GPU acceleration
# or for CUDA:
psolver:
  setup:
    accel: CUDA
```

## Output: Python Format

If the user prefers Python, generate a script using PyBigDFT.

### Python Template

```python
from BigDFT.Inputfiles import Inputfile
from BigDFT import InputActions as A

# Create input
inp = Inputfile()

# FILL: Grid parameters
inp.set_hgrid(FILL)          # e.g. 0.4
inp.set_rmult(coarse=FILL, fine=FILL)  # e.g. 5.0, 8.0

# FILL: XC functional
inp.set_xc('FILL')           # e.g. 'PBE'

# FILL: SCF convergence
inp.set_scf_convergence(gnrm=FILL)  # e.g. 1e-4

# FILL: Calculation-specific setup
# For geometry optimization:
# inp.optimize_geometry(method='FIRE', nsteps=50)

# FILL: Optional features
# inp.spin_polarize(mpol=1)
# inp.charge(charge=-1)
# inp.set_dispersion_correction()
# inp.set_implicit_solvent(solvent='water')
# inp.apply_electric_field([0, 0, 1e-3])
# inp.set_electronic_temperature(kT=1e-3)
# inp.use_gpu_acceleration(flavour='CUDA')
# inp.set_kpt_mesh('mpgrid', ngkpt=[4, 4, 4])

# FILL: Pseudopotentials (optional)
# inp.set_psp_krack('PBE')
# inp.set_psp_nlcc()

# FILL: Output
# inp.write_orbitals_on_disk(format='binary')
# inp.write_density_on_disk()

# FILL: Linear scaling (if needed)
# inp.set_linear_scaling()
# inp.set_ntpoly(thresh_dens=1e-6, conv_dens=1e-4)

# Atomic positions
inp.set_atomic_positions(FILL)  # posinp dict or use Systems API

# Print resulting YAML
import yaml
print(yaml.dump(dict(inp), default_flow_style=False))
```

### Python Example: Full Workflow with SystemCalculator

**Always do a dry run first** to validate input and estimate memory before running the actual calculation. This catches errors like missing pseudopotentials, wrong atom counts, or insufficient memory before you wait in a queue.

```python
from BigDFT.Inputfiles import Inputfile
from BigDFT.Calculators import SystemCalculator

# Create input
inp = Inputfile()
inp.set_xc('PBE')
inp.set_hgrid(0.4)
inp.set_rmult(coarse=5.0, fine=8.0)
inp.set_scf_convergence(gnrm=1e-4)

# Positions
posinp = {
    'units': 'angstroem',
    'positions': [
        {'O': [0.0, 0.0, 0.119]},
        {'H': [0.0, 0.757, -0.476]},
        {'H': [0.0, -0.757, -0.476]},
    ]
}
inp.set_atomic_positions(posinp)

# Dry run first -- validates input, estimates memory, does NOT run the calculation
calc_dry = SystemCalculator(dry_run=True)
log_dry = calc_dry.run(input=inp, name='water', run_dir='.')
# log_dry.energy is NaN (no calculation performed)
# Check the Memory Consumption Report in log_dry.log

# If dry run succeeds, run for real
calc = SystemCalculator()
log = calc.run(input=inp, name='water', run_dir='.')
print('Energy:', log.energy)
print('Forces:', log.forces)
```

The dry run uses `bigdft-tool -a memory-estimation` internally. It parses the input, sets up the grid, and reports memory requirements without performing the SCF. This is especially important before submitting to HPC queues via RemoteManager.

### Python Example: Remove an Action

```python
from BigDFT import InputActions as A

# Add then remove geometry optimization
inp.optimize_geometry(method='FIRE', nsteps=50)
inp.remove(A.optimize_geometry)
```

## Variable Quick Reference

### dft Section

| Variable | Default | Description |
|----------|---------|-------------|
| `hgrids` | 0.45 | Grid spacing (bohr). Scalar or [hx, hy, hz]. |
| `rmult` | [5.0, 8.0] | [coarse, fine] radius multipliers |
| `ixc` | 1 (LDA) | XC functional. Use string names: PBE, LDA, HF, PBE0 |
| `gnrm_cv` | 1e-4 | SCF convergence (gradient norm). Use 1e-5 for forces. |
| `itermax` | 50 | Max wavefunction optimization steps per cycle (subspace diag at end) |
| `nrepmax` | 1 | Number of cycles (each = itermax optimization + subspace diag). See SCF cycle structure below. |
| `ncong` | 6 | CG preconditioning iterations |
| `idsx` | 6 | DIIS history length |
| `qcharge` | 0 | System charge |
| `nspin` | 1 | 1=unpolarized, 2=collinear, 4=non-collinear |
| `mpol` | 0 | Magnetic moment (Bohr magnetons) |
| `inputpsiid` | 0 | Input guess: 0=default, `linear`=linear scaling |
| `dispersion` | 0 | 0=none, 5=Grimme D3 |
| `elecfield` | [0,0,0] | Electric field (Ha/Bohr) |
| `output_denspot` | 0 | Output density: 0=none, 21=write after SCF |
| `norbv` | 0 | Virtual orbitals to compute |
| `nvirt` | 0 | Virtual orbitals to converge |
| `nplot` | 0 | Orbitals to plot as cube files |
| `disablesym` | No | Disable symmetry detection |
| `alpha_hf` | -1.0 | Exact exchange fraction (hybrids) |

### geopt Section

| Variable | Default | Description |
|----------|---------|-------------|
| `method` | none | FIRE, SQNM, LBFGS, BFGS, DIIS, SDCG, VSSD, PBFGS, NEB, SOCK, MD, LOOP |
| `ncount_cluster_x` | 50 | Max force evaluations |
| `betax` | 4.0 | Step size |
| `frac_fluct` | 1.0 | Force fluctuation fraction for convergence |
| `forcemax` | 0 | Max force criterion (Ha/Bohr) |
| `randdis` | 0 | Random displacement amplitude |
| `nhistx` | 10 | SQNM/SBFGS history length |
| `trustr` | 0.5 | Max single-atom displacement (SQNM) |

### md Section

| Variable | Default | Description |
|----------|---------|-------------|
| `mdsteps` | 0 | Number of MD steps |
| `timestep` | 20.67 | Time step in a.u. (20.67 ~ 0.5 fs) |
| `temperature` | 300 | Initial temperature (K) |
| `thermostat` | none | none (NVE) or nose_hoover_chain (NVT) |
| `print_frequency` | 1 | Energy output frequency |
| `wavefunction_extrapolation` | 0 | 0=none, 2=BOMD (recommended) |
| `nose_frequency` | 3000 | Thermostat frequency (cm^-1) |
| `nose_chain_length` | 3 | Nose-Hoover chain length |
| `restart_pos` / `restart_vel` / `restart_nose` | No | Restart flags |

### kpt Section

| Variable | Default | Description |
|----------|---------|-------------|
| `method` | manual | auto, mpgrid, manual |
| `ngkpt` | [1,1,1] | Monkhorst-Pack grid (with method: mpgrid) |
| `kptrlen` | 0 | K-space resolution in bohr (with method: auto) |
| `bands` | No | Band structure calculation |

### mix Section

| Variable | Default | Description |
|----------|---------|-------------|
| `iscf` | 0 | Mixing scheme. 0=direct minimization, 17=Pulay on density |
| `norbsempty` | 0 | Extra empty (virtual) bands to include. See SCF cycle structure below. |
| `tel` | 0 | Electronic temperature (Ha) for smearing |
| `rpnrm_cv` | 1e-4 | Residue convergence |
| `alphamix` | 0 | Mixing parameter |

### posinp Section

| Field | Description |
|-------|-------------|
| `units` | angstroem, atomic (bohr), or reduced (fractional) |
| `cell` | [a, b, c] for orthorhombic; omit for free BC |
| `abc` | Full cell vectors [[ax,ay,az],[bx,by,bz],[cx,cy,cz]] |
| `positions` | List of `{Element: [x, y, z]}` dicts |
| `properties.reduced` | Yes if using fractional coordinates |
| Can also be a string: filename of external XYZ/ASCII file |

### psolver.environment Section (Implicit Solvent)

| Variable | Default | Description |
|----------|---------|-------------|
| `cavity` | none | none, soft-sphere, sccs |
| `epsilon` | 78.36 | Dielectric constant (78.36=water, 24.85=ethanol) |
| `fact_rigid` | 1.12 | Cavity size multiplier |
| `delta` | 0.5 | Transition region amplitude |
| `gammaS` | 72.0 | Surface tension (dyn/cm) |
| `alphaS` | -22.0 | Repulsion free energy |
| `betaV` | -0.35 | Dispersion free energy (GPa) |

### chess Section

| Subsection | Key Variables |
|------------|---------------|
| `foe` | `fscale` (decay length), `eval_range_foe` (eigenvalue bounds), `accuracy_foe`, `ef_interpol_det` |
| `ntpoly` | `threshold_density`, `convergence_density`, `threshold_overlap`, `convergence_overlap`, `solver` |
| `lapack` | `blocksize_pdsyev`, `blocksize_pdgemm` |

### lin_general Section

| Variable | Default | Description |
|----------|---------|-------------|
| `hybrid` | No | Hybrid LS/CS mode |
| `nit` | [100, 100] | [low_accuracy, high_accuracy] iterations |
| `rpnrm_cv` | [1e-12, 1e-12] | Convergence thresholds |
| `calc_dipole` | No | Calculate dipole moment |
| `kernel_restart_mode` | 0 | Restart method (0=fresh, 1=from kernel, ...) |
| `extra_states` | 0 | Extra states for optimization |
| `charge_multipoles` | 0 | 0=no, 1=Loewdin, 11=Mulliken |

### lin_basis Section

| Variable | Default | Description |
|----------|---------|-------------|
| `nit` | [4, 5] | Support function optimization iterations |
| `idsx` | [6, 6] | DIIS history [low, high] |
| `gnrm_cv` | [1e-2, 1e-4] | Convergence [low, high] |
| `fix_basis` | 1e-10 | Fix SFs below this density change |

### lin_kernel Section

| Variable | Default | Description |
|----------|---------|-------------|
| `linear_method` | DIAG | DIAG, FOE, NTPOLY, DIRMIN |
| `nit` | [5, 5] | Kernel iterations [low, high] |
| `rpnrm_cv` | [1e-10, 1e-10] | Convergence [low, high] |
| `alphamix` | [0.5, 0.5] | Mixing parameter [low, high] |

### lin_basis_params Section (Per-Element)

| Variable | Default | Description |
|----------|---------|-------------|
| `nbasis` | 4 | Support functions per atom (1=s, 4=sp, 9=spd, 16=spdf) |
| `ao_confinement` | 8.3e-3 | Input guess confinement prefactor |
| `confinement` | [8.3e-3, 0.0] | Confinement [low, high accuracy] |
| `rloc` | [7.0, 7.0] | Localization radius [low, high] |
| `rloc_kernel` | 9.0 | Density kernel cutoff |
| `rloc_kernel_foe` | 14.0 | FOE matrix-vector cutoff |

Typical per-element values (for organic molecules with FOE):
- **C, N, O**: nbasis=4, ao_confinement=2.7e-2, rloc=4.7, rloc_kernel=8.0, rloc_kernel_foe=15.0
- **H**: nbasis=1, ao_confinement=4.9e-2, rloc=4.0, rloc_kernel=8.0, rloc_kernel_foe=15.0
- **Si**: nbasis=9, ao_confinement=4.0e-2, rloc=6.0, rloc_kernel=7.0, rloc_kernel_foe=20.0

## Profiles (Presets)

BigDFT supports importing profiles via the `import` key. Available built-in profiles:

| Profile | Purpose |
|---------|---------|
| `linear` | Basic linear scaling (PDoS, charge analysis, MD) |
| `linear_accurate` | High-accuracy linear scaling with FOE |
| `linear_moderate` | Balanced accuracy/speed |
| `linear_fast` | Speed over accuracy |
| `linear_fragments` | Fragment calculations |
| `linear_purify` | NTPoly purification instead of CheSS |
| `mixing` | Metallic systems with density mixing |

Usage in YAML:
```yaml
import: linear
```

Usage in Python:
```python
inp.load(profile='linear')
```

## SCF Cycle Structure: itermax, nrepmax, and Virtual Orbitals

BigDFT's SCF works in cycles. Understanding `itermax`, `nrepmax`, and `norbsempty` together is essential for hard-to-converge systems and for computing virtual orbitals.

### The basic loop

```
for irep = 1 to nrepmax:
    for iter = 1 to itermax:
        optimize wavefunctions (gradient descent / DIIS)
        check gnrm_cv convergence → break if converged
    end
    subspace diagonalization  ← reassigns occupations, mixes orbitals
end
```

Each **cycle** consists of up to `itermax` wavefunction optimization steps followed by a **subspace diagonalization**. The subspace diagonalization builds the Hamiltonian matrix in the current orbital basis, diagonalizes it, and reorders/mixes the orbitals by eigenvalue. This is where occupation numbers get properly assigned.

The process repeats for `nrepmax` cycles.

### Default behavior (no virtual orbitals)

By default, `norbsempty = 0` and `nrepmax = 1`. BigDFT only optimizes occupied orbitals, runs one cycle of up to `itermax` steps, does a final subspace diagonalization, and stops. This is sufficient for most ground-state calculations.

### Why you need virtual orbitals

There are two reasons to set `norbsempty > 0` in the `mix` section:

1. **Hard-to-converge systems** (near-degenerate HOMO-LUMO, metals, open-shell): Including extra virtual orbitals in the optimization lets the subspace diagonalization properly shuffle electrons between nearly degenerate levels. Without them, the optimizer can oscillate because it doesn't have room to move electrons into the right orbitals.

2. **You want to inspect virtual orbitals**: For post-processing (band gaps, spectral properties, etc.), you need unoccupied orbitals. Setting `norbsempty` produces them.

### Why nrepmax matters with virtuals

With virtual orbitals, `nrepmax > 1` is important because:
- After the first cycle's subspace diagonalization, occupation numbers may change (electrons move between orbitals that were near the Fermi level)
- The newly reordered orbitals need further optimization in the next cycle
- Each cycle refines both the orbitals and their occupations

For metallic or near-degenerate systems, use `nrepmax: accurate` (which auto-selects up to 10 cycles) or set it manually:

```yaml
dft:
  gnrm_cv: 1.e-5
  itermax: 50
  nrepmax: 5
mix:
  norbsempty: 10
  tel: 0.001       # small smearing helps convergence
```

### Example: Metallic system with smearing

```yaml
import: mixing
dft:
  ixc: PBE
  hgrids: 0.4
  itermax: 50
  nrepmax: 10
mix:
  iscf: 17          # Pulay mixing on density
  norbsempty: 20    # extra bands for the Fermi surface
  tel: 0.01         # electronic temperature for smearing
  alphamix: 0.5
```

### Example: Getting virtual orbitals for a molecule

```yaml
dft:
  ixc: PBE
  hgrids: 0.35
  gnrm_cv: 1.e-5
  itermax: 100
  nrepmax: 3          # enough cycles to settle occupations
mix:
  norbsempty: 5       # 5 virtual orbitals
```

## Notes

- For free boundary conditions (isolated molecules), omit `cell` and `kpt`.
- For periodic systems, always specify `cell` (or `abc`) and `kpt`.
- `gnrm_cv: accurate` is a valid shortcut that auto-selects a tight threshold.
- `nrepmax: accurate` auto-selects re-diagonalization count.
- `posinp` can be a string pointing to an external file: `posinp: myfile.xyz`
- Positions are formatted as `- Element: [x, y, z]` in YAML.
- Linear scaling (`inputpsiid: linear`) requires `disablesym: Yes` and per-element `lin_basis_params`.
- The `(ABINIT)` suffix on ixc (e.g., `PBE (ABINIT)`) selects the ABINIT flavor of the functional, needed for some features like dispersion.
- Units: BigDFT works internally in atomic units (bohr, hartree). Positions can use angstroem or atomic.
- Time unit: 1 a.u. of time ~ 0.02419 fs. A timestep of 20.67 a.u. ~ 0.5 fs.
- **Always validate with a dry run** (`SystemCalculator(dry_run=True)`) before submitting real calculations, especially on HPC systems. It catches input errors and estimates memory in seconds.
