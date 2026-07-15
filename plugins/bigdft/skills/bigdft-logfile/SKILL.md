---
name: bigdft-logfile
description: Parse and analyze BigDFT logfile output. Extract energies, forces, eigenvalues, convergence data, and other properties. Use when the user wants to read or analyze BigDFT calculation results.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# BigDFT Logfile Analysis

Help the user load, query, and analyze BigDFT logfile output using the `BigDFT.Logfiles.Logfile` class. BigDFT writes output in YAML format, and the Logfile class parses it into accessible Python attributes.

## Loading Logfiles

```python
from BigDFT.Logfiles import Logfile

# From a YAML file
log = Logfile('log-calculation.yaml')

# From multiple files (same run)
log = Logfile('log-part1.yaml', 'log-part2.yaml')

# From a tar archive
log = Logfile(archive='results.tgz')
log = Logfile(archive='results.tgz', member='log-specific.yaml')

# From a pre-parsed dictionary
log = Logfile(dictionary=my_dict)

# From a list of dicts (multi-step: geopt, MD)
log = Logfile(dictionary=[dict1, dict2, dict3])

# Load multiple logfiles at once
logs = Logfiles.get_logs(['log-run1.yaml', 'log-run2.yaml'])
```

## Extracting Data

All properties are accessed as attributes. They return `None` if not present in the logfile.

### Energies

```python
log.energy              # Total energy (Hartree) -- the most common query
log.hartree_energy      # Hartree (electrostatic) energy component
log.XC_energy           # Exchange-correlation energy
log.trVxc               # Trace of V_xc
log.ionic_energy        # Ion-ion interaction energy
log.trH                 # Trace of KH (linear scaling)
log.fermi_level         # Fermi energy / chemical potential
```

### Forces

```python
log.forces              # List of force dicts: [{'Element': [fx, fy, fz]}, ...]
log.forcemax            # Maximum force magnitude (Ha/Bohr)
log.forcemax_cv         # Force convergence criterion
log.force_fluct         # Force fluctuation threshold
```

For periodic systems with k-points, forces are stored in `log.astruct['forces']` instead.

### Structure

```python
log.astruct             # Atomic structure dict with 'cell', 'positions', 'forces'
log.nat                 # Number of atoms
log.symmetry            # Space group
log.data_directory      # Path to data directory
log.posinp_file         # Source position file
```

### Electronic Structure

```python
log.evals               # Eigenvalues as list of BandArray objects
log.fermi_level         # Fermi level
log.number_of_orbitals  # Total KS orbitals
log.magnetization       # Total magnetization
```

### DFT Parameters (read back from logfile)

```python
log.grid_spacing        # hgrids value
log.rmult               # [coarse, fine] multipliers
log.XC_parameter        # Exchange-correlation ID (ixc)
log.spin_polarization   # nspin value
log.total_magn_moment   # mpol value
log.system_charge       # qcharge value
log.gnrm_cv             # Wavefunction convergence criterion
```

### K-points (Periodic Systems)

```python
log.kpts                # List of k-point dicts with 'Rc', 'Bz', 'Wgt' keys
log.kpt_mesh            # Monkhorst-Pack grid [nx, ny, nz]
log.nkpt                # Number of k-points (derived)
```

### Electrostatics

```python
log.dipole              # Electric dipole moment (AU)
log.electrostatic_multipoles  # Multipole coefficients
log.pressure            # Pressure (GPa)
log.stress_tensor       # Stress tensor (Ha/Bohr^3)
```

### Memory and Performance

```python
log.memory              # Dict of memory info by category
log.get_performance_info()  # Dict with Hostname, MPI, OMP, Walltime, Memory, etc.
```

### Raw Dictionary Access

The full YAML output is available as a dictionary:

```python
log.log                 # Complete logfile as dict
log.log['dft']          # DFT input section
log.log['Energy (Hartree)']  # Direct key access
```

## Multi-Step Logfiles (Geometry Optimization, MD)

When a logfile contains multiple documents (geometry optimization steps, MD frames), the Logfile object acts as a container:

```python
log = Logfile('geopt-output.yaml')

# Number of steps
n = len(log)             # 0 for single-point, >0 for multi-step

# Access individual steps
first = log[0]           # Logfile object for first step
last = log[-1]           # Last step
best = log[log.reference_log]  # Step with lowest energy

# Iterate
for step in log:
    print(step.energy, step.forcemax)

# Collect data across steps
energies = [step.energy for step in log]
forces = [step.forcemax for step in log]
```

## Convergence Analysis

### SCF Convergence

```python
from BigDFT.Logfiles import find_iterations, get_scf_curves

# Get iteration data
iters = find_iterations(log.log)

# Get plottable curves
curves = get_scf_curves(iters)
# curves['wfn'] = {'x': [...], 'y': [...]}  -- wavefunction residue
# curves['rho'] = {'x': [...], 'y': [...]}  -- density residue
# curves['outer'] = {'x': [...], 'y': [...]}  -- outer loop residue

# Quick plot
ax = log.SCF_convergence()
```

### Geometry Optimization Convergence

```python
# Plot energy vs max force (multi-step logfiles only)
ax = log.geopt_plot()
```

### Check Convergence

```python
log.check_convergence()        # True if BigDFT infocode == 0
log.check_convergence_cdft()   # For constrained DFT

# Get final convergence quality
from BigDFT.Logfiles import get_convergence_quality
quality = get_convergence_quality(log.log)
```

### Intermediate Energies

```python
# All energy values during SCF
intermediate = log.get_intermediate_energies()
```

## Density of States

```python
# Get DoS object
dos = log.get_dos()
dos = log.get_dos(sigma=0.1)  # With broadening

# Plot
ax = dos.plot()
```

## Band Structure (Periodic Systems)

```python
bz = log.get_brillouin_zone()
ax = bz.plot(npts=300)
```

## Creating Systems from Logfiles

```python
from BigDFT.Systems import system_from_log

# Each atom as its own fragment
sys = system_from_log(log, fragmentation='atomic')

# All atoms in one fragment
sys = system_from_log(log, fragmentation='full')

# Use fragmentation from the logfile (if defined in posinp)
sys = system_from_log(log)

# Transfer forces and multipoles to system
sys.set_logfile_info(log)    # sets forces, multipoles, and electrons
# Or individually:
sys.set_atom_forces(log)
sys.set_atom_multipoles(log)
sys.set_electrons_from_log(log)
```

## Detecting Calculation Type

```python
log.get_is_linear()     # True if linear scaling calculation
```

## Exporting

```python
# To JSON
log.to_json('output.json')

# Summary of physical quantities
summary = log.get_summary()  # List of dicts with property names and values
```

## Energies Class (Low-Level)

For parsing energy components from text logfiles or with unit conversion:

```python
from BigDFT.Logfiles import Energies

e = Energies('log-file.yaml', units='kcal/mol')
print(e.Etot, e.Eion, e.Ebs, e.Eh, e.EVxc, e.EXC)
print(e.sanity_error)  # Should be near zero
```

## Common Recipes

### Compare Energies Across Runs

```python
logs = [Logfile(f) for f in ['log-run1.yaml', 'log-run2.yaml', 'log-run3.yaml']]
for log in logs:
    print(f"E = {log.energy:.6f} Ha, Fmax = {log.forcemax:.4f} Ha/Bohr")
```

### Convergence Study (Grid Spacing)

```python
import matplotlib.pyplot as plt

hgrids = []
energies = []
for log in logs:
    hgrids.append(log.grid_spacing)
    energies.append(log.energy)

plt.plot(hgrids, energies, 'o-')
plt.xlabel('hgrids (bohr)')
plt.ylabel('Energy (Ha)')
```

### Extract Eigenvalue Gap

```python
evals = log.evals[0]  # First k-point (or only one)
# evals contains BandArray with orbital energies
fermi = log.fermi_level
```

### Geometry Optimization Trajectory

```python
from BigDFT.Systems import system_from_log

log = Logfile('geopt.yaml')
trajectory = []
for step in log:
    sys = system_from_log(step, fragmentation='full')
    trajectory.append(sys)
    print(f"E={step.energy:.6f}  Fmax={step.forcemax:.4f}")
```

### Access Timing Data

```python
perf = log.get_performance_info()
print(f"Walltime: {perf['Walltime']:.1f} s")
print(f"MPI tasks: {perf['MPI']}, OMP threads: {perf['OMP']}")
print(f"Memory peak: {perf['Mem']:.0f} MB")
print(f"CPU hours: {perf['CPUhours']:.2f}")
```

## Notes

- Logfile output is YAML format. The `Logfile` class uses `futile.YamlIO.load()` internally.
- Energy is always in Hartree, forces in Ha/Bohr, positions follow the units in the input.
- For multi-step logfiles (geopt, MD), `len(log)` returns the number of steps. For single-point calculations, `len(log)` returns 0.
- The `reference_log` attribute on multi-step logfiles points to the index of the lowest-energy step.
- Properties that don't exist in the logfile return `None` (no error).
- The `log.log` dictionary gives direct access to the raw YAML structure for anything not covered by named attributes.
- `find_iterations()` handles both cubic and linear scaling convergence data automatically.
- To create an `Inputfile` from a logfile (for restarts): `Inputfile.from_log(log)`.
