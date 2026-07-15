---
name: bigdft-systems
description: Build and manipulate atomic systems with PyBigDFT's Atom, Fragment, and System classes. Covers structure creation, coordinate handling, I/O, fragmentation, and analysis. Use when constructing or modifying molecular/periodic structures for BigDFT.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# PyBigDFT Systems, Fragments, and Atoms

Help the user build and manipulate atomic structures using PyBigDFT's three-level hierarchy:

```
System (dict of fragments)
  └── Fragment (list of atoms)
        └── Atom (dict of properties)
```

- **Atom** -- single atom with symbol, position, and optional properties (charge, force, etc.)
- **Fragment** -- ordered list of atoms (a molecule, residue, or arbitrary group)
- **System** -- named collection of fragments with an optional unit cell

All three behave like Python containers: Atom is a `MutableMapping` (dict-like), Fragment is a `MutableSequence` (list-like), System is a `MutableMapping` (dict-like).

## Creating Atoms

```python
from BigDFT.Atoms import Atom

# From element key with coordinates
at = Atom({'C': [0.0, 0.0, 0.0], 'units': 'angstroem'})

# From sym + r
at = Atom({'sym': 'O', 'r': [0.0, 0.0, 0.119], 'units': 'angstroem'})

# Default units are bohr
at = Atom({'sym': 'H', 'r': [1.43, 0.0, -0.95]})

# With additional properties
at = Atom({'sym': 'Fe', 'r': [0, 0, 0], 'units': 'bohr', 'nzion': 16.0})
```

### Atom Properties

```python
at.sym                  # Element symbol (str)
at.atomic_number        # Atomic number (int)
at.atomic_weight        # Atomic weight (float)
at.nel                  # Valence electrons (float, from nzion or defaults)

# Position (with unit conversion)
pos = at.get_position('bohr')        # In bohr
pos = at.get_position('angstroem')   # In angstrom
pos = at.get_position('reduced', cell=cell)  # Fractional coordinates

# Set position
at.set_position([1.0, 2.0, 3.0], units='angstroem')

# Forces
f = at.get_force()
at.set_force([0.01, -0.02, 0.0])

# Multipoles (from post-processing)
at.q0                   # Monopole charge (float or None)
at.q1                   # Dipole vector (array or None)

# Special flags
at.is_link              # QM/MM link atom (bool)
at.is_ghost             # Ghost atom for BSSE (bool)
```

### Atom as Dictionary

```python
at['sym'] = 'N'         # Change element
at['nzion'] = 5.0       # Set electron count
at['force'] = [0, 0, 0] # Add force
'sym' in at             # Key check
```

### Unit Conversion Constant

```python
from BigDFT.Atoms import AU_to_A   # 0.52917721092 (Bohr to Angstrom)
```

## Creating Fragments

```python
from BigDFT.Fragments import Fragment

# From a list of Atoms
frag = Fragment(atomlist=[at1, at2, at3])

# From an XYZ file
from BigDFT.IO import XYZReader
with XYZReader('molecule.xyz') as reader:
    frag = Fragment(xyzfile=reader)

# From BigDFT posinp dict
frag = Fragment(posinp={
    'units': 'angstroem',
    'positions': [
        {'O': [0.0, 0.0, 0.119]},
        {'H': [0.0, 0.757, -0.476]},
        {'H': [0.0, -0.757, -0.476]},
    ]
})

# From astruct dict (logfile structure)
frag = Fragment(astruct=log.astruct)

# From a System (collapse all fragments into one)
frag = Fragment(system=sys)

# Empty
frag = Fragment()
```

### Fragment as List

```python
len(frag)               # Number of atoms
frag[0]                 # First Atom
frag[-1]                # Last Atom
frag[1:3]               # Slice returns new Fragment
frag.append(atom)       # Add atom
frag.insert(0, atom)    # Insert at position

# Combine fragments
combined = frag1 + frag2       # New Fragment
```

### Fragment Properties

```python
frag.centroid                    # Center of mass [x,y,z] in bohr
frag.get_centroid(units='angstroem', cell=cell)  # With unit/cell options
frag.nel                         # Total valence electrons
frag.q0                          # Total monopole charge (or None)
frag.qcharge()                   # Net charge (float)
frag.center_of_charge()          # Electron-weighted centroid
frag.get_net_force()             # Sum of atomic forces [fx,fy,fz]
frag.ellipsoid()                 # Inertia tensor (3x3)
```

### Fragment Transformations

```python
# Translate (in bohr)
frag.translate([1.0, 0.0, 0.0])

# Rotate about coordinate axes (in-place)
frag.rotate(x=1.57)                        # Radians
frag.rotate(z=90, units='degrees')

# Rotate about arbitrary axis
frag.rotate_on_axis(angle=1.57, axis=[1, 1, 0], centroid=[0, 0, 0])
```

### Fragment Distances

```python
from BigDFT.Fragments import distance, pairwise_distance

d = distance(frag1, frag2)                # Between centroids
d = distance(frag1, frag2, cell=cell)     # With periodic images
d = pairwise_distance(frag1, frag2)       # Nearest atom pair
```

### Fragment Alignment

```python
from BigDFT.Fragments import lineup_fragment, interpolate_fragments

# Align principal axes to coordinate axes, center at origin
aligned = lineup_fragment(frag)

# RMSD between two fragments
rmsd = frag.rmsd(reference_frag)

# Interpolation path (for NEB, etc.)
path = interpolate_fragments(frag_A, frag_B, steps=10)
```

## Creating Systems

```python
from BigDFT.Systems import System

# From fragments
sys = System()
sys['water'] = water_frag
sys['methane'] = methane_frag

# Or in one line
sys = System(water=water_frag, methane=methane_frag)
```

### Creating from Files

```python
from BigDFT.IO import read_pdb, read_xyz, read_mol2

# From PDB
sys = read_pdb('structure.pdb')
sys = read_pdb('structure.pdb', charmm_format=True)

# From XYZ
sys = read_xyz('molecule.xyz')
sys = read_xyz('molecule.xyz', fragmentation='atomic')  # One fragment per atom

# From MOL2
sys = read_mol2('molecule.mol2')
```

### Creating from Logfiles

```python
from BigDFT.Systems import system_from_log

sys = system_from_log(log)                          # Use logfile fragmentation
sys = system_from_log(log, fragmentation='atomic')  # One fragment per atom
sys = system_from_log(log, fragmentation='full')    # All atoms in one fragment
```

### Creating from Dictionaries

```python
from BigDFT.Systems import system_from_dict_positions

posinp = {
    'units': 'angstroem',
    'cell': [10.0, 10.0, 10.0],
    'positions': [
        {'O': [0.0, 0.0, 0.119]},
        {'H': [0.0, 0.757, -0.476]},
        {'H': [0.0, -0.757, -0.476]},
    ]
}

sys = system_from_dict_positions(
    posinp['positions'],
    units=posinp.get('units', 'bohr'),
    cell=posinp.get('cell')
)
```

### Creating from DataFrames

```python
from BigDFT.Systems import system_from_df

sys = system_from_df(dataframe)
```

### Setting the Unit Cell

```python
from BigDFT.UnitCells import UnitCell

# Orthorhombic
sys.cell = UnitCell(cell=[10.0, 10.0, 10.0], units='angstroem')

# Full cell vectors
sys.cell = UnitCell(cell=[[10, 0, 0], [0, 10, 0], [0, 0, 10]], units='bohr')

# Infinite cell (default, free boundary conditions)
sys.cell = UnitCell()
```

## System as Dictionary

```python
len(sys)                        # Number of fragments
sys['water']                    # Get Fragment by name
sys['water'] = new_frag         # Replace fragment
del sys['water']                # Remove fragment
for frag_id in sys:             # Iterate fragment names
for frag_id, frag in sys.items():  # Iterate name-fragment pairs
list(sys.keys())                # All fragment names
list(sys.values())              # All Fragment objects
```

## System Properties

```python
sys.centroid                    # Mean centroid of all fragments
sys.central_fragment            # (name, Fragment) closest to centroid
sys.q0                          # Total monopole (or None)
sys.qcharge                     # Net charge
sys.cell                        # UnitCell object
sys.conmat                      # Connectivity matrix (or None)
```

## Iterating Atoms

```python
# All atoms across all fragments
for atom in sys.get_atoms():
    print(atom.sym, atom.get_position())

# Atoms in a specific order
for atom in sys.get_atoms(order=['frag2', 'frag1']):
    print(atom.sym)

# Get atom types
types = sys.get_types()  # {'C', 'H', 'O', ...}
```

## Nearest Fragment Queries

```python
# Nearest fragment to a target
nearest_id = sys.get_nearest_fragment('target_frag')

# K nearest fragments
neighbors = sys.get_k_nearest_fragments('target_frag', k=5)
# Returns list of (frag_id, distance) tuples

# With distance cutoff
neighbors = sys.get_k_nearest_fragments('target_frag', k=100, cutoff=10.0)
```

## Extracting Data from Logfiles

```python
# Set all available logfile info at once
sys.set_logfile_info(log)

# Or individually
sys.set_atom_forces(log)                        # Forces on atoms
sys.set_atom_multipoles(log, correct_charge=True)  # Charges and multipoles
sys.set_electrons_from_log(log)                 # Electron counts
```

## Output and Serialization

### BigDFT posinp Format

```python
# For input files
posinp = sys.get_posinp(units='angstroem')
# Returns: {'units': 'angstroem', 'positions': [...], 'cell': [...]}

# With custom fragment order
posinp = sys.get_posinp(units='bohr', order=['frag1', 'frag2'])
```

### Write to File

```python
sys.to_file('structure.xyz')    # XYZ format
sys.to_file('structure.pdb')    # PDB format
sys.to_file('structure.yaml')   # YAML format
```

### DataFrame

```python
df = sys.to_dataframe(units='bohr')
# Columns: sym, x_coord, y_coord, z_coord, frag, nel, q0_0, ...

# Cached property
df = sys.df
```

### Serialization

```python
# Flat list of atom dicts with fragment labels
atoms = sys.serialize(units='angstroem')
```

## Fragment Manipulation

### Rename Fragments

```python
# Auto-rename with sequential numbering
sys_renamed = sys.rename_fragments()

# Custom mapping
sys_renamed = sys.rename_fragments({'old_name': 'new_name'})
```

### Merge Fragments

```python
mapping = {
    'protein': ['RES:1', 'RES:2', 'RES:3'],
    'ligand': ['LIG:0'],
}
sys_merged = sys.reform_superunits(mapping)
```

### Extract Subsystem

```python
subsys = sys.subsystem(['frag1', 'frag3'])  # New System with selected fragments
```

### Reorganize by Atom Type

```python
sys_by_type = sys.atomtype_system()  # Fragments grouped by element
```

## Electrostatic Analysis

After setting multipoles from a logfile:

```python
sys.set_atom_multipoles(log)

# Fragment-level dipoles
for frag_id, frag in sys.items():
    d = frag.d0()   # Dipole from atomic charges only
    d = frag.d1()   # Dipole including atomic dipoles
    print(f"{frag_id}: q={frag.qcharge():.3f}, d={d}")

# System-level electrostatic interactions
interactions = sys.electrostatic_interactions
hartree = sys.hartree_interactions
ionic = sys.ionic_interactions

# Distances from a target fragment
distances = sys.distances_from_target('ligand')
```

## Visualization

```python
# 3D interactive display (Jupyter)
sys.display()

# With custom colors
sys.display(colordict={'protein': 'blue', 'ligand': 'red'})

# With field values (color by property)
sys.display(field_vals={'frag1': 0.5, 'frag2': -0.3})

# Quality overview (coordination, bonds, forces)
report = sys.examine()
```

## Connectivity

```python
# Sparse adjacency matrix
adj = sys.adjacency_matrix()  # scipy.sparse.dok_matrix

# Fragment view with bond analysis
fview = sys.fragment_view(purities, bond_orders)
```

## Running Calculations

**Always dry run first** to validate input before running the real calculation:

```python
from BigDFT.Calculators import SystemCalculator
from BigDFT.Inputfiles import Inputfile

# Set up input
inp = Inputfile()
inp.set_xc('PBE')
inp.set_hgrid(0.4)

# Set up positions from system
posinp = sys.get_posinp(units='angstroem')
inp.set_atomic_positions(posinp)

# Dry run: validates input, estimates memory, catches errors fast
calc_dry = SystemCalculator(dry_run=True)
log_dry = calc_dry.run(input=inp, name='calc', run_dir='.')

# Real run (only after dry run succeeds)
calc = SystemCalculator()
log = calc.run(input=inp, name='calc', run_dir='.')

# Get energy and forces
print(log.energy)
print(log.forces)
```

## Common Recipes

### Build a Water Molecule

```python
from BigDFT.Atoms import Atom
from BigDFT.Fragments import Fragment
from BigDFT.Systems import System

water = Fragment(atomlist=[
    Atom({'O': [0.000, 0.000, 0.119], 'units': 'angstroem'}),
    Atom({'H': [0.000, 0.757, -0.476], 'units': 'angstroem'}),
    Atom({'H': [0.000, -0.757, -0.476], 'units': 'angstroem'}),
])

sys = System()
sys['water'] = water
```

### Build a Periodic Crystal

```python
from BigDFT.UnitCells import UnitCell

si = Fragment(atomlist=[
    Atom({'Si': [0.0, 0.0, 0.0], 'units': 'reduced'}),
    Atom({'Si': [0.25, 0.25, 0.25], 'units': 'reduced'}),
])

sys = System()
sys['Si'] = si
sys.cell = UnitCell(cell=[5.431, 5.431, 5.431], units='angstroem')

posinp = sys.get_posinp(units='reduced')
```

### Read PDB and Select Nearby Residues

```python
from BigDFT.IO import read_pdb

sys = read_pdb('protein.pdb')

# Find residues within 5 Angstrom of ligand
from BigDFT.Atoms import AU_to_A
cutoff_bohr = 5.0 / AU_to_A

neighbors = sys.get_k_nearest_fragments('LIG:0', k=100, cutoff=cutoff_bohr)
nearby_ids = [frag_id for frag_id, dist in neighbors]

# Extract subsystem
active_site = sys.subsystem(['LIG:0'] + nearby_ids)
```

### Geometry Optimization Trajectory to XYZ

```python
from BigDFT.Logfiles import Logfile
from BigDFT.Systems import system_from_log

log = Logfile('geopt.yaml')
for i, step in enumerate(log):
    sys = system_from_log(step, fragmentation='full')
    sys.to_file(f'frame_{i:04d}.xyz')
```

### Combine Two Molecules

```python
sys = System()
sys['molecule_A'] = frag_A
sys['molecule_B'] = frag_B

# Translate B away from A
frag_B.translate([10.0, 0.0, 0.0])  # 10 bohr separation
```

### Compute Fragment Charges from Logfile

```python
from BigDFT.Logfiles import Logfile
from BigDFT.Systems import system_from_log

log = Logfile('log-output.yaml')
sys = system_from_log(log)
sys.set_atom_multipoles(log)

for frag_id, frag in sys.items():
    print(f"{frag_id}: charge = {frag.qcharge():.3f} e")
```

## Notes

- Default units are **bohr** throughout PyBigDFT. Use `units='angstroem'` explicitly when needed.
- `AU_to_A = 0.52917721092` converts bohr to angstrom.
- Fragment names in systems from PDB files follow the pattern `RESNAME:RESID` (e.g., `ALA:42`).
- Fragment names from `system_from_log` with `fragmentation='atomic'` follow `ELEMENT:INDEX` (e.g., `C:0`, `O:1`).
- The `get_posinp()` method produces a dict directly usable in `Inputfile.set_atomic_positions()`.
- `System.cell` defaults to an infinite cell (free boundary conditions). Set it explicitly for periodic calculations.
- Atom positions support three unit systems: `'bohr'` (atomic units), `'angstroem'`, and `'reduced'` (fractional, requires cell).
- When a cell is provided to `Atom.get_position()`, minimum image convention is applied automatically.
- The `conmat` (connectivity matrix) on Fragment and System is `None` by default and must be set explicitly or loaded from PDB/MOL2.
