---
name: bigdft-dev-liborbs
description: Developer guide for the liborbs library -- orbital manipulation, localization regions, wavelet compression, operator application, and the views abstraction. Use when working on SCF algorithms, Hamiltonian operations, or orbital I/O in BigDFT.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# liborbs Developer Guide

liborbs is BigDFT's library for orbital manipulation. It abstracts the representation of quantum orbitals (wavelet coefficients, real-space mesh, Gaussian projectors) behind a views layer, so SCF algorithm code doesn't need to know the internal representation.

The library handles:
- Localization regions (spatial domains where orbitals live)
- Wavelet compression (sparse storage of coefficients)
- Operator application (kinetic, potential, density)
- Basis conversion (wavelet ↔ mesh ↔ Gaussian)
- MPI distribution and GPU acceleration

Source: `liborbs/src/` (~66 Fortran files, ~43K lines)

## Architecture

```
User code (SCF loop, Davidson, forces)
    │
    ▼
Views layer (wvf_daub_view, wvf_mesh_view)     ← representation-agnostic API
    │
    ├── Operators (kinetic, potential, density)
    ├── Scalar products (wpdot_keys)
    └── I/O (read/write orbitals)
    │
    ▼
Core layer
    ├── locreg_descriptors    ← spatial region definition
    ├── wavefunctions_descriptors  ← compressed storage layout
    ├── convolutions          ← wavelet convolution operators
    ├── workarrays           ← pre-allocated work memory
    └── manager              ← memory/resource management
```

## Key Data Structures

### Localization Region Descriptor

The fundamental data structure. Defines a spatial region where orbitals live, including grid bounds, resolution levels, and boundary conditions.

```fortran
use locregs

type(locreg_descriptors) :: lr

! Key fields:
lr%locregCenter(1:3)    ! Center of region (bohr)
lr%locrad               ! Localization radius (cutoff)
lr%locrad_kernel         ! Density kernel radius
lr%locrad_mult           ! Sparse matrix multiplication radius
lr%Localnorb             ! Number of orbitals in this region

! Grid bounding boxes (lower, upper bounds in each dimension)
lr%nboxc(2,3)            ! Coarse grid box
lr%nboxi(2,3)            ! Interpolating grid box (2x coarse)
lr%nboxf(2,3)            ! Fine grid box

! Derived objects
lr%wfd                   ! Wavefunction compression descriptors
lr%bounds                ! Convolution bounds for kinetic operator
lr%mesh                  ! Cell geometry
lr%mesh_fine             ! Fine grid cell
lr%mesh_coarse           ! Coarse grid cell
lr%bit                   ! Box iterator for mesh traversal
```

There are two main region types in BigDFT:
- **Global region (`glr`)**: Covers the entire simulation domain. Used for cubic scaling.
- **Local regions (`llr`)**: Per-atom regions for linear scaling. Each atom gets its own localization region sized by `rloc`.

### Wavefunction Compression Descriptors

Wavelet coefficients are stored sparsely. Only grid points where the orbital is significant are kept, using a segment-based key system.

```fortran
use compression

type(wavefunctions_descriptors) :: wfd

wfd%nvctr_c      ! Number of coarse grid coefficients (stored)
wfd%nvctr_f      ! Number of fine grid coefficients (stored)
wfd%nseg_c       ! Number of coarse segments
wfd%nseg_f       ! Number of fine segments

! Keys map compressed indices to grid positions
wfd%keyglob(:,:) ! Global key array
wfd%keygloc(:,:) ! Local key array
wfd%keyvloc(:)   ! Local vector keys
wfd%keyvglob(:)  ! Global vector keys
```

The total size of one orbital in compressed form is `nvctr_c + 7*nvctr_f` (1 coarse coefficient + 7 fine wavelet coefficients per fine grid point).

### Wavefunction Manager

Manages memory allocation, work arrays, and GPU context for orbital operations.

```fortran
use liborbs_manager

type(wvf_manager) :: mgr

! Create
mgr = wvf_manager_new(nspinor=1)    ! 1 for collinear, 2 for non-collinear

! Key fields
mgr%nspinor          ! Number of spinor components
mgr%max_daub         ! Max wavelet coefficients across all regions
mgr%max_mesh         ! Max mesh points across all regions

! Work arrays (allocated on demand, cached)
mgr%w_sumrho         ! For density calculation
mgr%w_locham         ! For Hamiltonian application
mgr%w_precond        ! For preconditioning

! Release
call wvf_manager_release(mgr)
```

### Wavefunction Views

Views are the primary abstraction for working with orbitals. They decouple algorithm code from representation details.

```fortran
use liborbs_views

! Wavelet-space view (compressed coefficients)
type(wvf_daub_view) :: dv
dv%lr      ! → locreg_descriptors (region)
dv%manager ! → wvf_manager (resources)
dv%c       ! Memory buffer with wavelet coefficients

! Real-space mesh view (values on grid points)
type(wvf_mesh_view) :: mv
mv%lr      ! → locreg_descriptors (region)
mv%manager ! → wvf_manager (resources)
mv%c       ! Memory buffer with mesh values
```

## Wavefunction Normalization

BigDFT stores wavefunctions in two representations with the same normalization convention:

- **Daubechies wavelet coefficients** (`psi_daub`): `sum(psi_daub²) = 1`
- **ISF mesh values** (`psi_mesh`): `sum(psi_mesh²) = 1`

**Neither is the physical normalization.** The physical wavefunction satisfying `∫|ψ|² dr = 1` is:

```
ψ_physical(r) = psi_mesh(r) / sqrt(volume_element)
```

where `volume_element = hx * hy * hz` (product of ISF grid spacings, typically `(hgrid/2)³`).

This convention means `sum(psi_mesh²) * volume_element ≠ 1` -- it equals `volume_element`. The normalization is baked into the operators so that physical energies come out correctly (see Operator Application below), but you must account for it when forming physical densities for PSolver or when computing quantities manually on the mesh.

## Creating and Using Views

### From Existing Data

```fortran
use liborbs_functions

! Create a wavelet-space view from an existing coefficient array
dv = wvf_view_on_daub(mgr, lr, psi_coeffs)

! Create a mesh view from an existing real-space array
mv = wvf_view_on_mesh(mgr, lr, psi_mesh)

! Release when done
call wvf_view_release(dv)
call wvf_view_release(mv)
```

### Conversion Between Representations

```fortran
! Wavelet → mesh (for applying real-space potential)
mv = wvf_daub_to_mesh(dv)
! or equivalently via the store variant:
mv = wvf_view_to_mesh(dv, store=.true.)  ! store=.true. needed if applying kinetic operator after

! Mesh → wavelet (after applying potential)
dv = wvf_mesh_to_daub(mv)
! or:
dv = wvf_view_to_daub(mv)
```

Mesh data is accessible in `mv%c%mem(:,1)` with shape `(ndim_mesh, nspinor)`.

### Memory Management

Use a fresh `wvf_manager` for each orbital conversion to avoid exhausting the internal buffer pool (the manager has a limited number of memory buffers):

```fortran
do iorb = 1, norb
  mgr = wvf_manager_new(nspinor=1)
  dv = wvf_view_on_daub(mgr, glr, psi(:, iorb))
  mv = wvf_view_to_mesh(dv, store=.true.)
  ! ... use mv ...
  call wvf_deallocate_manager(mgr)
end do
```

## Operator Application

All operators work through the views API.

### Kinetic Energy

The kinetic operator `T = -∇²/2` is applied via wavelet convolution:

```fortran
use liborbs_operators

real(gp) :: ekin

! Apply kinetic operator: mesh_in → daub_out
! Returns kinetic energy contribution via ekin
dv_out = wvf_kinetic_operator(mv_in, ekin=ekin)
```

The kinetic operator takes a mesh view as input and returns wavelet coefficients. The `ekin` output gives the correct physical kinetic energy `⟨ψ|T|ψ⟩`.

**Important: the wavelet kinetic operator includes the identity.** When computing off-diagonal matrix elements via dot products of wavelet coefficients:

```
dot(psi_n_daub, T_psi_m_daub) = T_{nm} + delta_{nm}
```

To extract the kinetic matrix element, subtract the Kronecker delta:

```fortran
T_nm = wpdot_keys(..., psi_n, T_psi_m) - delta_nm
! where delta_nm = 1 if n==m, 0 otherwise
```

This is because BigDFT's wavelet kinetic convolution is `(1 + T)` rather than bare `T`. The diagonal `ekin` output already accounts for this (it subtracts the identity contribution).

### Potential Energy

Apply a local real-space potential `V(r)`:

```fortran
! pot is the potential on the fine grid, in physical units (Hartree)
! Returns potential energy contribution
real(gp) :: epot
dv_out = wvf_potential_operator(mv_in, pot, epot=epot)
```

The potential energy `⟨ψ|V|ψ⟩` is computed internally as:

```
⟨ψ|V|ψ⟩ = sum(V(r) * psi_mesh(r)²)
```

No volume element factor is needed in this formula because of BigDFT's normalization convention (`sum(psi_mesh²) = 1`). The potential `V` is in physical units (Hartree) evaluated at ISF grid points. The `epot` output gives the result directly.

### Combined Hamiltonian

Apply `H = T + V`:

```fortran
! Combined kinetic + potential
dv_hpsi = wvf_hamiltonian(mv_psi, pot, ekin=ekin, epot=epot)
```

### Density Calculation

Compute `ρ(r) = |ψ(r)|²` or accumulate density from multiple orbitals:

```fortran
! Single orbital density
rho = wvf_density(dv)

! Accumulate into existing density array
call wvf_density_accumulate(dv, rho, occupation=occ)
```

### Preconditioning

Apply the preconditioner to orbital gradients (for SCF convergence):

```fortran
dv_precond = wvf_preconditioner(dv_gradient, lr, hpre)
```

## Scalar Products

```fortran
use scalar_product

! Dot product between two wavelet-space orbitals
! Uses compressed key-based multiplication (efficient)
dot = wpdot_keys(nvctr_c, nvctr_f, nseg_c, nseg_f, &
                 keyg1, psi1, keyg2, psi2)
```

For orbitals in the same localization region (same compression), this is a simple dot product. For orbitals in different regions, the key-based product handles the index mapping.

## Multipole-Preserving Quadrature (scfdotf)

The function `scfdotf` from the `multipole_preserving` module computes the 1D overlap between an ISF basis function at grid point `j` and a Gaussian:

```
scfdotf(j, hgrid, pgauss, x0, pow) = ∫ ISF_j(τ) · (τ·h - x0)^pow · exp(-pgauss · (τ·h - x0)²) dτ
```

where:
- `j` is a **0-based** grid index
- `hgrid` is the ISF grid spacing
- `pgauss` is the Gaussian exponent (e.g., `1/(2·sigma²)`)
- `x0` is the center position in physical units
- `pow` is the polynomial power

The result is in **grid units**. To match BigDFT's normalization convention (`sum(c²) = 1`), multiply each 1D overlap by `sqrt(hgrid)`:

```fortran
use multipole_preserving, only: scfdotf

scf_x(j) = scfdotf(j-1, hx, pgauss, x0, 0) * sqrt(hx)
```

For a 3D separable Gaussian, the ISF representation is:

```fortran
proj_isf(ind) = normalization * scf_x(j1) * scf_y(j2) * scf_z(j3)
```

This can be converted to the Daubechies basis via `wvf_view_to_daub` for wavelet-space dot products.

**Note on BigDFT defaults:** BigDFT's default for the local ionic potential is `multipole_preserving: No`, meaning direct evaluation at grid points rather than scfdotf. For nonlocal projectors, BigDFT uses `PROJECTION_1D_SEPARABLE` which projects Gaussians directly to wavelets via tensor products -- a different (more accurate) code path than the scfdotf -> ISF -> Daubechies approach.

## Compression Details

### How Compression Works

BigDFT wavelets use a multiresolution scheme with two levels:
- **Coarse grid**: Scaling function coefficients (smooth part)
- **Fine grid**: Wavelet coefficients (detail/correction part)

Each fine grid point has 7 wavelet coefficients (from the 3D tensor product of 1D wavelets).

Not all grid points are significant -- most of the simulation box is empty (especially for isolated molecules). The compression scheme stores only the non-zero segments:

```
Full grid:  [0 0 0 X X X 0 0 X X 0 0 0 0 X X X X 0 0]
Segments:         [---]     [-]           [------]
Keys:        [(3,5), (8,9), (14,17)]  ← (start, end) of each segment
```

### Compression Strategies

```fortran
! Available strategies (from compression module):
integer, parameter :: STRATEGY_SKIP = 0      ! Skip compressed storage
integer, parameter :: STRATEGY_MASK = 1      ! Bitmask compression
integer, parameter :: STRATEGY_KEYS = 2      ! Key-based (default)
integer, parameter :: STRATEGY_MASK_PACK = 3 ! Packed bitmask
integer, parameter :: STRATEGY_KEYS_PACK = 4 ! Packed keys
```

`KEYS` is the default and most common strategy.

### Creating Compression Descriptors

```fortran
use compression

type(wavefunctions_descriptors) :: wfd

! Initialize from localization region
call wfd_from_locreg(wfd, lr, strategy=STRATEGY_KEYS)

! Query sizes
total_coeffs = wfd%nvctr_c + 7 * wfd%nvctr_f
```

## Localization Region Initialization

### Global Region (Cubic Scaling)

```fortran
use locregs
use initlocregs

type(locreg_descriptors) :: glr

! Initialize from atoms and grid parameters
call init_lr(glr, geocode, hgrids, rxyz, radii, crmult, frmult, ...)
```

Parameters:
- `geocode`: Boundary conditions ('F'=free, 'P'=periodic, 'S'=surface, 'W'=wire)
- `hgrids(3)`: Grid spacing in each direction
- `rxyz(3,nat)`: Atomic positions
- `radii(nat)`: Coarse/fine radii per atom
- `crmult`, `frmult`: Coarse/fine radius multipliers (rmult)

### Local Regions (Linear Scaling)

Each atom gets its own region:

```fortran
type(locreg_descriptors), dimension(nat) :: llr

do iat = 1, nat
  call init_lr(llr(iat), geocode, hgrids, rxyz(:,iat), &
               radii(iat), rloc(iat), ...)
end do
```

The `rloc` parameter from `lin_basis_params` directly controls the size of these local regions.

## Boundary Conditions

liborbs handles all BigDFT boundary conditions:

| Code | Type | Periodicity | Grid treatment |
|------|------|-------------|----------------|
| `'F'` | Free | None | Zero-padded; isolated molecule |
| `'P'` | Periodic | x, y, z | Wrapped; bulk crystal |
| `'S'` | Surface | x, y | Free in z; slab geometry |
| `'W'` | Wire | z | Free in x, y; nanowire |

The boundary condition affects:
- Convolution operators (different algorithms per BC)
- Grid bounding boxes
- MPI communication patterns

## Wavefunction I/O

liborbs provides I/O for reading and writing orbital data (wavelet coefficients) to disk. BigDFT wraps these for its specific file formats.

### Reading Wavefunctions via io_descriptor

The preferred approach for reading BigDFT wavefunction files:

```fortran
use liborbs_io

type(io_descriptor) :: descr
type(locreg_descriptors) :: glr
real(f_double), dimension(:), allocatable :: psi
real(f_double) :: eigenvalue
integer :: norb, ndim_psi
logical :: lstat

! Read metadata and set up global locreg (including compression keys)
descr = io_descriptor_from_file('data/wavefunction.yaml')
call copy_locreg_descriptors(descr%glr, glr)

! Number of orbitals
norb = dict_len(descr%funcs)

! Size of wavelet coefficient array per orbital
ndim_psi = array_dim(glr)  ! = nvctr_c + 7 * nvctr_f

! Allocate and read each orbital
allocate(psi(ndim_psi))
do iorb = 1, norb
  call io_descr_read_phi(descr, psi, eigenvalue, iorb, glr, lstat)
  ! psi now contains Daubechies wavelet coefficients for orbital iorb
end do
```

### Low-Level I/O

For direct file access without the descriptor:

```fortran
use liborbs_io

type(io_descriptor) :: iod

! Open for writing
call io_open(iod, 'wavefunction.bin', 'write')

! Write one orbital's wavelet coefficients
call io_write_orbital(iod, lr, psi_coeffs, iorb)

! Close
call io_close(iod)

! Read back
call io_open(iod, 'wavefunction.bin', 'read')
call io_read_orbital(iod, lr, psi_coeffs, iorb)
call io_close(iod)
```

### BigDFT Wavefunction Files

BigDFT's linear scaling mode writes support functions to `minBasis.*` files in the data directory. These are read back via the `io` module in `bigdft/src/modules/io.f90`:

```fortran
use io

! Write support functions (called at end of LS run)
call writemywaves(iproc, filename, iformat, orbs, glr, psi, ...)

! Read support functions (for restart or post-processing)
call readmywaves_linear_new(iproc, filename, iformat, orbs, glr, psi, ...)
```

Each support function is stored as compressed wavelet coefficients in its localization region. The file also contains:
- Orbital metadata (energies, occupations, spin)
- Grid information (hgrids, localization region parameters)
- Number of basis functions and their assignment to atoms

### Wavefunction YAML Units

The `units` field in `wavefunction.yaml` may be `'angstroem'` even though BigDFT works in bohr internally. Always check and convert atomic positions:

```fortran
if (trim(units_str) == 'angstroem') then
  pos = pos / 0.52917721092_f_double
end if
```

### Cubic vs Linear Wavefunction Files

**Linear scaling** (`minBasis.*`): Each orbital has its own localization region. The file stores per-orbital locreg descriptors and compressed coefficients.

**Cubic scaling** (standard `wavefunction.*`): All orbitals share one global localization region. The file stores the global locreg once, then all orbital coefficients.

Both formats use the same underlying `io_write_orbital` / `io_read_orbital` from liborbs. The difference is in how many localization regions are defined.

### Coefficient Files

In addition to the wavelet-space support functions, BigDFT can write the expansion coefficients (the matrix expressing KS orbitals in terms of support functions):

```
minBasis_coeff.bin  -- nbasis × nbasis × nspin coefficient matrix
```

These are written by `writeLinearCoefficients()` in `io.f90`.

## Work Arrays

Pre-allocated memory for avoiding repeated allocation in iterative algorithms:

```fortran
use liborbs_workarrays

! For density calculation
type(workarr_sumrho) :: w_rho
call allocate_workarr_sumrho(w_rho, lr)
! ... use in density loop ...
call deallocate_workarr_sumrho(w_rho)

! For Hamiltonian application
type(workarr_locham) :: w_ham
call allocate_workarr_locham(w_ham, lr)
! ... use in H|ψ⟩ ...
call deallocate_workarr_locham(w_ham)

! For preconditioning
type(workarr_precond) :: w_pre
call allocate_workarr_precond(w_pre, lr)
! ... use in preconditioner ...
call deallocate_workarr_precond(w_pre)
```

The `wvf_manager` handles this automatically when using the views API. Manual management is only needed when working at the lower level.

## Wavelet Filters

The Daubechies wavelet filters are hardcoded in `filterModule.f90`:

```fortran
use filterModule

! Filter coefficient arrays (length 29 for Daubechies-16):
real(kind=8) :: a(0:ifilter)   ! Scaling function filter
real(kind=8) :: b(0:ifilter)   ! Wavelet filter (derived from a)
real(kind=8) :: c(0:ifilter)   ! Dual scaling function filter
real(kind=8) :: e(0:ifilter)   ! Dual wavelet filter
```

BigDFT uses Daubechies-16 wavelets (order 16, support length 29).

## I/O

### Reading/Writing Orbitals

```fortran
use liborbs_io

type(io_descriptor) :: iod

! Open for writing
call io_open(iod, 'wavefunction.bin', 'write')

! Write orbital data
call io_write_orbital(iod, lr, psi_coeffs, iorb)

! Close
call io_close(iod)

! Read back
call io_open(iod, 'wavefunction.bin', 'read')
call io_read_orbital(iod, lr, psi_coeffs, iorb)
call io_close(iod)
```

Orbital files store compressed wavelet coefficients along with the compression keys, allowing restart from a previous calculation.

## GPU Acceleration

liborbs supports GPU-accelerated convolutions via OpenCL:

```fortran
! GPU context is managed through the wvf_manager
mgr = wvf_manager_new(nspinor=1)
! If compiled with --enable-ocl, GPU operations are used automatically

! For manual control:
mgr%gpu_context   ! OpenCL context handle
mgr%gpu_queue     ! OpenCL command queue handle
```

GPU-accelerated operations:
- Kinetic operator convolutions
- Potential application
- Density accumulation

The GPU kernels are in `convolutions-c/` (C/OpenCL source).

## MPI Distribution

In parallel BigDFT, orbitals are distributed across MPI processes. liborbs handles:

- **Orbital distribution**: Each process owns a subset of orbitals
- **Potential distribution**: Each process owns a spatial slice of the potential
- **Communication**: Reformatting orbitals between distributions

```fortran
use reformatting

! Reformat from one distribution to another
call reformat_wavefunction(psi_in, lr_in, psi_out, lr_out, &
                           comm_pattern)
```

## Confining Potentials

Used in linear scaling to confine support functions:

```fortran
use liborbs_potentials

type(confpot_data) :: cpot

! Initialize confining potential for an atom
call confpot_init(cpot, lr, rxyz_atom, prefactor, power)

! Apply during Hamiltonian
call confpot_apply(cpot, psi_mesh, vpsi_mesh)
```

The `ao_confinement` and `confinement` parameters from `lin_basis_params` control these potentials.

## Key Source Files

| File | Lines | What it contains |
|------|-------|-----------------|
| `locregs.f90` | 3763 | `locreg_descriptors` type and all region operations |
| `compression.f90` | 2185 | Compression scheme, key generation, pack/unpack |
| `convolutions.f90` | 1851 | Wavelet convolution operators for all BCs |
| `locreg_operations.f90` | 1588 | ISF↔wavelet transforms, density in local regions |
| `potential.f90` | 1674 | Real-space potential application |
| `reformatting.f90` | 1703 | MPI reformatting, rototranslations |
| `workarrays.f90` | 1461 | Work array types and allocation |
| `initlocregs.f90` | 1474 | Region initialization from atoms/grid |
| `wavefunction.f90` | 973 | High-level wavefunction operations |
| `views.f90` | ~800 | Views abstraction layer |
| `operators.f90` | ~700 | Operator application through views |
| `manager.f90` | ~500 | Memory manager and caching |
| `scalar_product.f90` | 952 | Dot products with compression keys |
| `bounds.f90` | 1001 | Grid bounds for kinetic convolutions |
| `precond.f90` | 1018 | Preconditioner implementation |
| `filterModule.f90` | 996 | Daubechies wavelet filter coefficients |
| `io.f90` | 1173 | Orbital file I/O |

## Typical Usage in BigDFT

### SCF Loop (Simplified)

```fortran
! In the SCF cycle, for each orbital:

! 1. Create mesh view from wavelet coefficients
mv = wvf_daub_to_mesh(dv_psi)

! 2. Apply Hamiltonian: H|ψ⟩ = T|ψ⟩ + V|ψ⟩
dv_hpsi = wvf_hamiltonian(mv, pot, ekin=ekin, epot=epot)

! 3. Compute residual: |r⟩ = H|ψ⟩ - ε|ψ⟩
! (done at coefficient level)

! 4. Precondition residual
dv_precond = wvf_preconditioner(dv_residual, lr, hpre)

! 5. Update orbital
! psi_new = psi + alpha * precond_residual

! 6. Accumulate density
call wvf_density_accumulate(dv_psi, rho, occupation=occ)
```

### Density Calculation (Full)

```fortran
! Zero density
rho = 0.0_gp

! Loop over orbitals owned by this process
do iorb = 1, norb_local
  ! Get view for this orbital
  dv = wvf_view_on_daub(mgr, glr, psi(:, iorb))

  ! Accumulate |ψ|² with occupation
  call wvf_density_accumulate(dv, rho, occupation=occ(iorb))

  call wvf_view_release(dv)
end do

! MPI reduce density
call fmpi_allreduce(rho, op=FMPI_SUM)
```

## Notes

- liborbs is designed to be representation-agnostic. Always prefer the views API over directly manipulating coefficient arrays.
- The `wvf_manager` handles work array allocation automatically. Only allocate work arrays manually if you need fine-grained control.
- Compression keys are generated once during initialization and reused. They should not be modified during the SCF loop.
- The coarse grid spacing equals `hgrids`, and the fine grid spacing equals `hgrids/2`.
- The number of fine wavelet coefficients per point is 7 (from 2³ - 1 in 3D).
- For linear scaling, each atom's `locreg_descriptors` is sized by `rloc` from `lin_basis_params`.
- GPU operations are transparent through the views API -- the same code runs on CPU or GPU depending on build configuration.
- `geocode` (boundary conditions) must be consistent across all localization regions in a calculation.
