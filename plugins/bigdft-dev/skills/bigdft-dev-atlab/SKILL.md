---
name: bigdft-dev-atlab
description: Developer guide for the ATlab library -- simulation domains, grid cells, box iterators, multipole expansions, spherical harmonics, numerical utilities, and field I/O. Use when working with grid operations, boundary conditions, or domain geometry in BigDFT.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# ATlab Developer Guide

ATlab (Atomic Lab) provides the geometric foundation for BigDFT. It defines simulation domains (unit cells with boundary conditions and metric tensors), real-space grids with efficient iterators, multipole moment representations, spherical harmonics, field I/O, and numerical utilities.

Both BigDFT and liborbs depend on ATlab for all spatial/geometric operations.

Source: `atlab/src/` (~15 Fortran modules)

## Domain (Unit Cell and Boundary Conditions)

The `domain` type defines the simulation box geometry: cell vectors, boundary conditions, and metric tensors for handling non-orthogonal cells.

```fortran
use at_domain

type(domain) :: dom

! Create from parameters
dom = domain_new( &
  units=ATOMIC_UNITS, &            ! or ANGSTROEM_UNITS, NANOMETER_UNITS
  bc=[PERIODIC_BC, PERIODIC_BC, FREE_BC], &  ! per-axis boundary conditions
  acell=[10.0_gp, 10.0_gp, 20.0_gp])        ! cell vector lengths
```

### Boundary Conditions

| Constant | Value | Meaning |
|----------|-------|---------|
| `FREE_BC` | 0 | Open boundary (isolated) |
| `PERIODIC_BC` | 1 | Periodic boundary |

Combined per-axis settings map to BigDFT geocodes:

| bc(1), bc(2), bc(3) | Geocode | System type |
|---------------------|---------|-------------|
| F, F, F | `'F'` | Isolated molecule |
| P, P, P | `'P'` | Bulk crystal |
| P, P, F | `'S'` | Surface slab |
| F, F, P | `'W'` | Wire/nanotube |

```fortran
! Get geocode character
character(len=1) :: gc
gc = domain_geocode(dom)  ! 'F', 'P', 'S', or 'W'

! Check which dimensions are periodic
logical, dimension(3) :: periodic
periodic = bc_periodic_dims(dom%bc)

! Convert from geocode
call change_domain_BC(dom, 'S')  ! Set to surface BC
```

### Non-Orthogonal Cells

For triclinic/monoclinic/hexagonal cells, specify angles or full cell vectors:

```fortran
! From angles (alpha_bc, beta_ac, gamma_ab in radians)
dom = domain_new(units=ATOMIC_UNITS, bc=[PERIODIC_BC, PERIODIC_BC, PERIODIC_BC], &
                 acell=[a, b, c], angles=[alpha, beta, gamma])

! From full cell vectors (columns of abc matrix)
dom = domain_new(units=ATOMIC_UNITS, bc=[PERIODIC_BC, PERIODIC_BC, PERIODIC_BC], &
                 abc=reshape([ax,ay,az, bx,by,bz, cx,cy,cz], [3,3]))
```

### Metric Tensors

Non-orthogonal cells require metric tensors for correct distance/dot product calculations:

```fortran
! Covariant metric (for contravariant vectors)
dom%gd(3,3)     ! g_ij = a_i · a_j
dom%detgd       ! det(g_ij)

! Contravariant metric (for covariant vectors)
dom%gu(3,3)     ! g^ij = (g_ij)^{-1}

! Metric-aware dot product
dp = dotp_gu(dom, v1, v2)    ! v1·v2 using contravariant metric
dp = dotp_gd(dom, v1, v2)    ! v1·v2 using covariant metric

! Metric-aware squared norm
sq = square_gu(dom, v)
sq = square_gd(dom, v)

! Check if cell is orthogonal
if (dom%orthorhombic) then
  ! Can skip metric operations
end if
```

### Distance and Periodicity

```fortran
! Distance between two points (respects BC and minimum image)
d = distance(dom, r1, r2)

! Closest image vector (r2 - r1 folded into cell)
dr = closest_r(dom, r1, r2)

! Project to orthogonal coordinate system
r_ortho = rxyz_ortho(dom, r)

! Fold coordinates into the cell
call domain_fold_into(dom, rxyz)

! Cell volume
vol = domain_volume(dom)
```

### Serialization

```fortran
! Save to dictionary
call domain_merge_to_dict(dict, dom)

! Load from dictionary
call domain_set_from_dict(dict, dom)
```

## Grid Cell and Box Iterator

The `cell` type defines a real-space grid over a domain. The `box_iterator` provides efficient traversal of grid points.

### Cell (Grid Definition)

```fortran
use box

type(cell) :: mesh

! Create grid
mesh = cell_new(dom, ndims=[100, 100, 200], hgrids=[0.4_gp, 0.4_gp, 0.4_gp])

! Key fields
mesh%ndims(3)         ! Grid dimensions [nx, ny, nz]
mesh%hgrids(3)        ! Grid spacing in each direction
mesh%ndim             ! Total points (nx * ny * nz, as integer(f_long))
mesh%volume_element   ! Volume of one grid cell
mesh%dom              ! Associated domain
mesh%habc(3,3)        ! Primitive volume elements in lattice directions
```

### Box Iterator

The iterator traverses grid points efficiently, providing real-space coordinates and indices at each step:

```fortran
type(box_iterator) :: bit

! Iterate over entire grid
bit = box_iter(mesh)
do while (box_next_point(bit))
  ! bit%rxyz(3) = real-space coordinates of current point
  ! bit%i, bit%j, bit%k = grid indices
  ! bit%ind = flattened linear index
  field(bit%ind) = some_function(bit%rxyz)
end do
```

### Sub-Box Iteration

Iterate over a rectangular subset of the grid:

```fortran
! Define subbox bounds [lower, upper] for each axis
integer, dimension(2,3) :: nbox
nbox(:,1) = [10, 50]   ! x range
nbox(:,2) = [10, 50]   ! y range
nbox(:,3) = [20, 80]   ! z range

bit = box_iter(mesh, nbox=nbox)
do while (box_next_point(bit))
  ! Only visits points inside nbox
end do
```

### Cutoff-Based Sub-Box

Get the subbox containing all points within a cutoff radius of a center:

```fortran
! Subbox around a point within cutoff
nbox = box_nbox_from_cutoff(mesh, center_xyz, cutoff_radius)

bit = box_iter(mesh, nbox=nbox, origin=center_xyz)
do while (box_next_point(bit))
  r2 = box_iter_square_gd(bit)  ! Squared distance from origin (metric-aware)
  if (r2 < cutoff_radius**2) then
    ! Point is within sphere
  end if
end do
```

### Parallel Grid Iteration (OpenMP)

```fortran
type(box_iterator) :: bit_local

bit = box_iter(mesh)

!$omp parallel private(bit_local)
call box_iter_split(bit, omp_get_num_threads(), omp_get_thread_num(), bit_local)
do while (box_next_point(bit_local))
  ! Each thread processes its portion
  field(bit_local%ind) = ...
end do
!$omp end parallel
call box_iter_merge(bit)  ! Synchronize results
```

### MPI-Distributed Grid Iteration

```fortran
! i3s = starting z-slab for this process
! n3p = number of z-slabs for this process
bit = box_iter(mesh, i3s=i3s, n3p=n3p)
do while (box_next_point(bit))
  ! Only visits this process's slice
end do
```

### Iterator Utilities

```fortran
! Distance from iterator position to a point
d = box_iter_distance(bit, target_xyz)

! Closest periodic image
dr = box_iter_closest_r(bit, target_xyz)

! Check if current point is inside a subbox
inside = box_iter_inside(bit, nbox)

! Reset iterator to beginning
call box_iter_rewind(bit)
```

## Multipole Moments

Represent charge distributions as multipole expansions (monopole, dipole, quadrupole):

```fortran
use multipoles

! Create individual poles
type(monopole) :: mono
type(dipole) :: di
type(quadrupole) :: quad

mono = pole(charge, sigma)               ! q0, Gaussian width
di = pole(dipole_vector, sigma)           ! q1(-1:1), Gaussian width
quad = pole(quadrupole_tensor, sigma)     ! q2(-2:2), Gaussian width
```

### Multipole Centers

A multipole center is a point source with monopole, dipole, and quadrupole moments:

```fortran
type(multipole_center) :: mc

call multipole_center_set(mc, label='atom1', rxyz=[0,0,0], &
                          mono=mono, di=di, quad=quad)
```

### Evaluating Multipole Fields

```fortran
! Coulomb potential from multipole at a point
V = multipole_at(mc, r_eval)

! Gaussian density representation from multipoles
call multipole_centers_to_gaussian_density(centers, n_centers, mesh, rho)
```

### Serialization

```fortran
! Save/load from dictionary
call multipole_centers_to_dict(dict, centers, n_centers)
call multipole_centers_from_dict(dict, centers, n_centers)
```

## Spherical Harmonics

```fortran
use f_harmonics

! Evaluate solid harmonic Y_lm^n(x, y, z)
val = solid_harmonic(n, l, m, x, y, z)
! n=0: regular solid harmonic (r^l * Y_lm)
! n=1: irregular solid harmonic (Y_lm / r^(l+1))
```

### Field Multipole Extraction

Extract multipole moments from a scalar field on a grid:

```fortran
type(f_multipoles) :: mp

call f_multipoles_create(mp, lmax=2, center=center_xyz)

! Extract moments by iterating over grid
call field_multipoles(bit, field, nfield, mp)

! Get individual moments
q0 = get_monopole(mp)         ! Scalar
q1 = get_dipole(mp)           ! Array(3)
q2 = get_quadrupole(mp)       ! Array(5)
spreads = get_spreads(mp)     ! Array(3) -- second moments

call f_multipoles_release(mp)
```

### From Point Charges

```fortran
call vector_multipoles(mp, nat, rxyz, dom, charges)
```

## Numerical Utilities

```fortran
use numerics

! Physical constants
real(gp), parameter :: Bohr_Ang = 0.52917721092_gp
real(gp), parameter :: Ha_eV = 27.21138505_gp
real(gp), parameter :: Ha_cmm1 = 219474.6313705_gp   ! Hartree to cm^-1
real(gp), parameter :: Radian_Degree = 57.29577951308232_gp

! Safe mathematical functions (no FPE)
y = safe_exp(x)        ! Exponential (clamps extreme values)
y = safe_log(x)        ! Logarithm (handles zero/negative)
y = safe_erf(x)        ! Error function
```

## Analytical Functions

```fortran
use f_functions

type(f_function) :: func

! Create a Gaussian function
func = f_function_new(FUNC_GAUSSIAN, prefactor=1.0_gp, exponent=0.5_gp)

! Evaluate
val = eval(func, x)

! Differentiate
dfunc = diff(func)
dval = eval(dfunc, x)

! 1D grid
type(f_grid_1d) :: grid
grid = f_grid_1d_new(npts=100, start=0.0_gp, spacing=0.1_gp)
```

Available function types: `FUNC_CONSTANT`, `FUNC_GAUSSIAN`, `FUNC_POLYNOMIAL`, `FUNC_COSINE`, `FUNC_EXP_COSINE`, `FUNC_SINE`, `FUNC_ATAN`, `FUNC_ERF`.

## Field I/O

Read and write scalar fields (densities, potentials) on grids:

```fortran
use IObox

type(domain) :: dom
type(cell) :: mesh
real(gp), dimension(:), allocatable :: field

! Read from CUBE file (auto-detects format from extension)
call read_field('density.cube', dom, mesh, field)

! Read only dimensions (no data)
integer, dimension(3) :: ndims
call read_field_dimensions('density.cube', ndims)

! Write to CUBE file
call dump_field('potential.cube', dom, mesh, field, geocode='F')
```

Supported formats:
- `.cube` -- Gaussian CUBE
- `.etsf` -- ETSF-IO (HDF5-based, if compiled with support)
- `.pot` -- Legacy BigDFT potential format

## OpenBabel Integration

Read/write molecular structures in many formats:

```fortran
use at_babel

type(dictionary), pointer :: dict

! Read structure from file (PDB, XYZ, CIF, MOL2, SDF, ...)
call load_dict_from_openbabel(dict, 'molecule.pdb')

! Write structure to file
call dump_dict_with_openbabel(dict, dict_types, 'output.xyz')
```

Requires OpenBabel to be installed and linked at build time.

## Multipole-Preserving Quadrature

Advanced integration scheme that exactly preserves multipole moments when projecting Gaussian functions onto grids:

```fortran
use multipole_preserving

! Initialize for a set of Gaussian widths
call initialize_real_space_conversion(npoints, isf_m, rlocs, nmoms)

! Check if initialized
if (mp_initialized()) then ...

! Get range of interpolating scaling functions
range = mp_range()

! Compute scaling function overlap
overlap = scfdotf(x, h, npoints)

! Cleanup
call finalize_real_space_conversion()
```

This is used internally by BigDFT when projecting pseudopotential projectors and charge densities onto the wavelet grid.

## Key Source Files

| File | Lines | What it contains |
|------|-------|-----------------|
| `domain.f90` | 1391 | `domain` type, metrics, distances, BC handling |
| `box.f90` | 1088 | `cell` type, `box_iterator`, grid traversal |
| `IObox.f90` | 1080 | CUBE/ETSF field I/O |
| `multipole.f90` | 637 | Multipole types and evaluation |
| `harmonics.f90` | ~600 | Spherical harmonics, field moment extraction |
| `mp_quadrature.f90` | 409 | Multipole-preserving quadrature |
| `numerics.f90` | ~300 | Constants and safe math |
| `f_functions.f90` | ~500 | Analytical function types |
| `ISF.f90` | ~400 | Interpolating scaling functions |
| `openbabel_wrapper.f90` | ~200 | OpenBabel interface |

## Common Patterns in BigDFT Code

### Grid Operation with Domain Awareness

```fortran
subroutine compute_on_grid(mesh, pot, rxyz_atom, sigma)
  use box
  use at_domain
  use numerics
  type(cell), intent(in) :: mesh
  real(gp), dimension(:), intent(inout) :: pot
  real(gp), dimension(3), intent(in) :: rxyz_atom
  real(gp), intent(in) :: sigma

  type(box_iterator) :: bit
  real(gp) :: r2, cutoff
  integer, dimension(2,3) :: nbox

  cutoff = 10.0_gp * sigma
  nbox = box_nbox_from_cutoff(mesh, rxyz_atom, cutoff)

  bit = box_iter(mesh, nbox=nbox, origin=rxyz_atom)
  do while (box_next_point(bit))
    r2 = box_iter_square_gd(bit)
    pot(bit%ind) = pot(bit%ind) + safe_exp(-0.5_gp * r2 / sigma**2)
  end do
end subroutine
```

### Domain from Input Dictionary

```fortran
type(domain) :: dom
type(dictionary), pointer :: posinp

call yaml_parse_from_file(posinp, 'input.yaml')
call domain_set_from_dict(posinp // 'posinp', dom)
```

## Grid Coordinate System

### box_iter Coordinates

The `box_iter` iterator uses **mesh-local coordinates** where the first grid point is at `(0, 0, 0)`. Grid point `j` (1-based) has coordinate `(j-1) * hgrid` in each dimension.

BigDFT's global coordinate system is offset from the mesh-local system by the `nboxi` array:

```
rxyz_mesh = rxyz_global - nboxi(1,:) * mesh%hgrids
```

where `nboxi(1,:)` is the lower bound of the ISF grid in global grid units (typically negative for free boundary conditions, e.g., `[-14, -14, -14]`).

**This offset must be applied** when converting atom positions from `wavefunction.yaml` (global coordinates) to mesh-local coordinates for use with `box_iter`. Without this conversion, atom-centered operations (projectors, local potentials) will be placed at the wrong grid location.

```fortran
! Convert atom position from global to mesh-local coordinates
rxyz_local(1) = rxyz_global(1) - nboxi(1,1) * mesh%hgrids(1)
rxyz_local(2) = rxyz_global(2) - nboxi(1,2) * mesh%hgrids(2)
rxyz_local(3) = rxyz_global(3) - nboxi(1,3) * mesh%hgrids(3)

! Now use rxyz_local as the origin for box_iter
bit = box_iter(mesh, nbox=nbox, origin=rxyz_local)
```

The `nboxi` array can be obtained from the `locreg_descriptors` of the global localization region (`glr%nsi` gives the start indices).

## Notes

- ATlab is a dependency of both liborbs and BigDFT. It must be built before either.
- The `domain` type handles all metric complexity. Always use `dotp_gu`/`dotp_gd` and `box_iter_square_gd` instead of manual dot products -- they correctly handle non-orthogonal cells.
- The `box_iterator` automatically handles periodic boundary conditions via minimum image convention.
- `box_nbox_from_cutoff` is essential for performance: iterate only over grid points that could contribute, not the entire grid.
- Grid fields are stored as 1D arrays indexed by `bit%ind`. The iterator handles the 3D→1D mapping.
- The `cell` type includes `volume_element` which is needed for numerical integration: `integral = sum(field * mesh%volume_element)`.
- For orthogonal cells (`dom%orthorhombic = .true.`), metric operations simplify to standard Euclidean operations. The code handles both cases transparently.
- `safe_exp` should always be used instead of `exp` in production code to avoid floating-point exceptions on extreme values.
