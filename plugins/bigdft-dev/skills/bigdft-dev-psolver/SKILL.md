---
name: bigdft-dev-psolver
description: Developer guide for the Poisson Solver library -- solving for the Hartree potential from a charge density. Covers kernel creation, solver invocation, boundary conditions, implicit solvation, GPU acceleration, and the FFT-based algorithm. Use when working with electrostatics, Hartree potential, or implicit solvent in BigDFT.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# PSolver Developer Guide

PSolver solves the Poisson equation (or its generalized form with a dielectric medium) to compute the Hartree potential from a charge density:

```
Vacuum:     ∇²V(r) = -4πρ(r)
Dielectric: ∇·[ε(r)∇V(r)] = -4πρ(r)
```

It uses FFT-based convolution with Interpolating Scaling Functions (ISF) to handle multiple boundary conditions. It also provides implicit solvation (PCM-like) with cavity construction and non-electrostatic energy terms.

Source: `psolver/src/` (~20 Fortran files)

## Quick Start: Solving the Poisson Equation

The minimal workflow is: create kernel → set kernel → solve → read results.

```fortran
use Poisson_Solver

type(coulomb_operator) :: kernel
type(dictionary), pointer :: dict
real(dp), dimension(:,:,:), allocatable :: rhopot
real(dp) :: ehartree

! 1. Initialize kernel from input dictionary and domain
kernel = pkernel_init(iproc, nproc, dict, dom, ndims, hgrids)

! 2. Build the FFT kernel for the boundary conditions
call pkernel_set(kernel)

! 3. Solve: density in → potential out (overwrites rhopot!)
call H_potential('G', kernel, rhopot, pot_ion, ehartree, offset, sumpion)

! 4. Clean up
call pkernel_free(kernel)
```

**Critical:** `rhopot` is **overwritten in place**. It contains density on input and potential on output.

## Kernel Creation

### From a Dictionary (Standard)

```fortran
type(coulomb_operator) :: kernel
type(dictionary), pointer :: dict

! dict contains psolver input parameters (from PS_input_variables_definition.yaml)
! dom is an at_domain domain type
! ndims(3) = grid dimensions
! hgrids(3) = grid spacing

kernel = pkernel_init(iproc, nproc, dict, dom, ndims, hgrids)
```

`pkernel_init` reads the dictionary, fills defaults from the YAML schema, and sets up the `coulomb_operator` structure. It does **not** build the FFT kernel yet.

### From Explicit Parameters

```fortran
kernel = pkernel_init(iproc, nproc, dict, dom, ndims, hgrids, &
                      mpi_env=mpi_env, &    ! MPI communicator
                      alpha_bc=alpha, &      ! Cell angle α (non-orthogonal)
                      beta_ac=beta, &        ! Cell angle β
                      gamma_ab=gamma)        ! Cell angle γ
```

### Building the FFT Kernel

After `pkernel_init`, call `pkernel_set` to compute the actual Fourier-space kernel:

```fortran
! Vacuum solver (default)
call pkernel_set(kernel, verbose=.true.)

! With dielectric (for generalized Poisson)
call pkernel_set(kernel, eps=eps_array, dlogeps=dlogeps_array, &
                 oneoeps=oneoeps_array, oneosqrteps=oneosqrteps_array, &
                 corr=correction_array)
```

### Null Kernel

```fortran
kernel = pkernel_null()   ! All fields nullified
```

### Free Kernel

```fortran
call pkernel_free(kernel)   ! Deallocate everything
```

## Solving

### H_potential (Compatibility Wrapper)

The traditional BigDFT interface:

```fortran
call H_potential(datacode, kernel, rhopot, pot_ion, eh, offset, sumpion, &
                 quiet, rho_ion, stress_tensor)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `datacode` | `character(1)` | `'G'` = global (full array on each process), `'D'` = distributed (z-slabs across processes) |
| `kernel` | `coulomb_operator` | The kernel (may be modified for SCCS) |
| `rhopot` | `real(dp), dimension(*)` | **In:** density, **Out:** potential (overwritten!) |
| `pot_ion` | `real(dp), dimension(*)` | Ionic potential (added to output if `sumpion=.true.`) |
| `eh` | `real(dp)` | **Out:** Hartree energy (+ cavitation + eVextra) |
| `offset` | `real(dp)` | **Out:** Potential integral (for periodic BC normalization) |
| `sumpion` | `logical` | Add `pot_ion` to output potential? |
| `quiet` | `character(3)`, optional | `'yes'` to suppress output |
| `rho_ion` | `real(dp), dimension(*)`, optional | Ionic charge density (for generalized Poisson) |
| `stress_tensor` | `real(dp), dimension(6)`, optional | **Out:** Stress tensor [xx,yy,zz,yz,xz,xy] |

### Electrostatic_Solver (Modern Interface)

```fortran
type(PSolver_energies) :: energies

call Electrostatic_Solver(kernel, rhopot, energies, pot_ion, rho_ion, ehartree)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `kernel` | `coulomb_operator` | The kernel |
| `rhopot` | `real(dp), dimension(*)` | Density in → potential out |
| `energies` | `PSolver_energies`, optional | All energy components |
| `pot_ion` | `real(dp), dimension(*)`, optional | Ionic potential |
| `rho_ion` | `real(dp), dimension(*)`, optional | Ionic density |
| `ehartree` | `real(dp)`, optional | Hartree energy only |

### Setting Options Before Solving

```fortran
call PS_set_options(kernel, &
                    global_data=.true., &       ! 'G' mode
                    verbose=.true., &
                    calculate_strten=.true., &  ! Compute stress tensor
                    update_cavity=.false., &    ! Don't rebuild SCCS cavity
                    final_call=.true.)          ! Prepare force-related data
```

## Boundary Conditions

The kernel handles four boundary condition types, determined by the `domain` geocode:

| Geocode | Type | Periodicity | Algorithm |
|---------|------|-------------|-----------|
| `'F'` | Free | None | ISF Green's function convolution |
| `'P'` | Periodic | x, y, z | Reciprocal space: `4π/|k|²` |
| `'S'` | Surface | x, z | Mixed: periodic in-plane, ISF out-of-plane |
| `'W'` | Wire | z | Mixed: periodic along wire, ISF transverse |

The boundary condition is set via the `domain` passed to `pkernel_init`. PSolver automatically selects the correct kernel construction and FFT algorithm.

### Screening (Helmholtz/Yukawa)

For screened Coulomb interactions `(∇² - μ²)V = -4πρ`:

```yaml
psolver:
  kernel:
    screening: 0.1    # μ screening parameter (default: 0 = standard Poisson)
```

Or in Fortran:

```fortran
kernel%mu = 0.1_gp   ! Before pkernel_set
```

## Implicit Solvation

PSolver implements continuum solvation models where the solute is in a molecular cavity surrounded by a dielectric medium.

### Configuration (YAML)

```yaml
psolver:
  environment:
    cavity: soft-sphere       # or 'sccs' or 'none'
    epsilon: 78.36            # Dielectric constant (water)
    fact_rigid: 1.12          # Cavity scaling factor
    delta: 0.5                # Transition smoothness (bohr)
    cavitation: Yes           # Include non-electrostatic terms
    gammaS: 72.0              # Surface tension (dyn/cm)
    alphaS: -22.0             # Repulsion free energy (dyn/cm)
    betaV: -0.35              # Dispersion free energy (GPa)
    gps_algorithm: PCG        # or 'SC' for self-consistent iteration
    itermax: 200              # Max GPe iterations
    minres: 1.e-8             # GPe convergence threshold
```

### Cavity Types

**Rigid / Soft-Sphere:**
Fixed cavity constructed from atomic van der Waals radii. The dielectric function transitions smoothly from 1 (inside) to ε₀ (outside) over a width controlled by `delta`. The cavity shape doesn't change during the SCF.

**SCCS (Self-Consistent Continuum Solvation):**
Cavity determined self-consistently from the electron density. The dielectric function depends on ρ(r), so the cavity updates each SCF step. Set `update_cavity=.true.` in options.

### Solver Algorithms for Dielectric

**PCG (Preconditioned Conjugate Gradient):**
Default for generalized Poisson. Solves ∇·[ε∇φ] = -4πρ iteratively using vacuum Poisson as preconditioner. Requires: `oneosqrteps`, `corr` arrays.

**SC/PI (Self-Consistent / Polarization Iteration):**
Simpler but slower convergence. Iterates: solve vacuum Poisson → update polarization → repeat. Requires: `oneoeps` array.

### Energy Components

After solving with implicit solvent:

```fortran
type(PSolver_energies) :: energies

call Electrostatic_Solver(kernel, rhopot, energies)

energies%hartree      ! Electrostatic energy: ½∫ρV
energies%elec         ! Electronic electrostatic contribution
energies%eVextra      ! Extra potential from SCCS
energies%cavitation   ! Non-electrostatic: γS·A + αS·A + βV·V
energies%strten(6)    ! Stress tensor components
```

### Poisson-Boltzmann Extension

For electrolyte solutions, PSolver solves the coupled generalized Poisson + Poisson-Boltzmann equations:

```yaml
psolver:
  environment:
    cavity: soft-sphere
    epsilon: 78.36
    pb_method: standard       # 'linear', 'standard' (Gouy-Chapman), 'modified' (Bikermann)
    pb_itermax: 50
    pb_minres: 1.e-10
    pb_eta: 1.0               # Mixing parameter
```

## Data Layout and MPI Distribution

### Global Mode (`datacode='G'`)

Every MPI process holds the full density/potential array:

```fortran
real(dp), dimension(md1, md3, md2) :: rhopot
! md1, md2, md3 = grid dimensions (may differ slightly from ndims due to padding)
```

### Distributed Mode (`datacode='D'`)

Each process holds a slab of z-planes:

```fortran
real(dp), dimension(md1, md3, md2_local) :: rhopot
! md2_local = kernel%grid%n3p (number of z-planes for this process)
! Starting z-plane = kernel%grid%istart
```

### FFT Grid Dimensions

The FFT may use slightly different dimensions than the input grid (zero-padding):

```fortran
kernel%grid%m1, m2, m3     ! Original grid dimensions
kernel%grid%n1, n2, n3     ! FFT dimensions (zero-padded)
kernel%grid%md1, md2, md3  ! Working dimensions
kernel%grid%nd1, nd2, nd3  ! Fourier-space dimensions (1/8 for symmetry)
kernel%grid%n3p            ! This process's z-plane count
kernel%grid%istart         ! This process's starting z-plane
```

## The FFT Algorithm

PSolver's core algorithm (in `PSolver_Core.f90`, routine `G_PoissonSolver`):

1. **Pack density** into zero-padded work array `zf`
2. **1D FFT** along z-direction (parallel, each process does its z-planes)
3. **MPI_ALLTOALL** transpose: redistribute from z-slabs to x-slabs
4. **2D FFT** along x and y (local per process)
5. **Kernel multiplication** in Fourier space: `V(k) = K(k) · ρ(k)`
6. **Inverse 2D FFT**
7. **MPI_ALLTOALL** transpose back
8. **Inverse 1D FFT**
9. **Unpack potential** from `zf` back to output array
10. **Compute energy**: `E_H = ½ ∫ ρ(r) V(r) dr` (done during unpack)

The kernel `K(k)` depends on boundary conditions:
- Periodic: `4π/|k|²`
- Free: ISF-discretized Green's function
- Mixed: combination per direction

## GPU Acceleration

PSolver supports GPU-accelerated FFTs:

```yaml
psolver:
  setup:
    accel: CUDA           # or DBFFT (MKL-SYCL), ONEMATH (oneMATH-SYCL), none
    keep_gpu_memory: Yes  # Reuse GPU buffers across calls
    use_gpu_direct: Yes   # GPU-direct MPI communication
```

The GPU path replaces CPU FFTs with cuFFT (CUDA) or oneMKL FFTs (SYCL). The kernel multiplication and packing/unpacking also run on GPU when available.

## Key Types Reference

### coulomb_operator

The central object. Contains everything needed to solve:

```fortran
type(coulomb_operator) :: kernel

kernel%mesh          ! cell (grid geometry)
kernel%grid          ! FFT_metadata (dimensions, MPI distribution)
kernel%opt           ! PSolver_options (runtime flags)
kernel%kernel(:)     ! Fourier-space kernel array
kernel%mu            ! Screening parameter
kernel%cavity        ! cavity_data (dielectric parameters)
kernel%method        ! Solver method (VAC, PI, PCG, PB variants)
kernel%mpi_env       ! MPI environment
kernel%w             ! Work arrays (zf = FFT workspace)
kernel%diel          ! Dielectric function arrays
kernel%GPU           ! GPU memory handles
```

### PSolver_energies

```fortran
type(PSolver_energies) :: e

e%hartree      ! ½∫ρV
e%elec         ! Electrostatic from total charge
e%eVextra      ! SCCS correction potential energy
e%cavitation   ! γS·A + αS·A + βV·V
e%strten(6)    ! Stress tensor [xx,yy,zz,yz,xz,xy]
```

### PSolver_options

```fortran
type(PSolver_options) :: opt

opt%datacode           ! 'G' or 'D'
opt%verbosity_level    ! 0 or 1
opt%keepGPUmemory      ! Reuse GPU allocations
opt%calculate_strten   ! Compute stress tensor
opt%update_cavity      ! Rebuild SCCS cavity
opt%use_input_guess    ! Warm-start iterative solver
opt%only_electrostatic ! Skip cavitation terms
opt%final_call         ! Prepare force data
opt%potential_integral ! Offset for periodic BC
```

## Input Variable Sections

### kernel

| Variable | Default | Description |
|----------|---------|-------------|
| `screening` | 0.0 | Helmholtz screening μ (0 = standard Poisson) |
| `isf_order` | 16 | ISF interpolation order (higher = more accurate) |
| `stress_tensor` | Yes | Compute stress tensor |

### environment

| Variable | Default | Description |
|----------|---------|-------------|
| `cavity` | none | Cavity type: none, soft-sphere, sccs |
| `epsilon` | 78.36 | Dielectric constant |
| `fact_rigid` | 1.12 | Rigid cavity radius scaling |
| `delta` | 0.5 | Transition smoothness (bohr) |
| `cavitation` | Yes | Include non-electrostatic terms |
| `gammaS` | 72.0 | Surface tension (dyn/cm) |
| `alphaS` | -22.0 | Repulsion coefficient (dyn/cm) |
| `betaV` | -0.35 | Dispersion coefficient (GPa) |
| `gps_algorithm` | PCG | Generalized Poisson solver: PCG or SC |
| `itermax` | 200 | Max GPe iterations |
| `minres` | 1e-8 | GPe convergence |
| `pi_eta` | 0.6 | SC mixing parameter |
| `input_guess` | Yes | Use initial guess for GPe |
| `fd_order` | 16 | Finite difference order for ∇ε |
| `pb_method` | none | PB: none, linear, standard, modified |
| `pb_itermax` | 50 | PB max iterations |
| `pb_minres` | 1e-10 | PB convergence |

### setup

| Variable | Default | Description |
|----------|---------|-------------|
| `accel` | none | GPU: none, CUDA, DBFFT, ONEMATH |
| `keep_gpu_memory` | Yes | Persist GPU buffers |
| `use_gpu_direct` | Yes | GPU-direct MPI |
| `taskgroup_size` | 0 | MPI task grouping (0 = auto) |
| `global_data` | No | Use global arrays |
| `verbose` | Yes | Print solver info |

## Key Source Files

| File | What it contains |
|------|-----------------|
| `Poisson_Solver.f90` | Public module definition, `coulomb_operator` type |
| `PSolver_Main.f90` | `Electrostatic_Solver`, `H_potential`, input fill routines |
| `createKernel.f90` | `pkernel_init`, `pkernel_set`, `pkernel_free` |
| `PSolver_Core.f90` | `G_PoissonSolver` -- the FFT convolution engine |
| `Build_Kernel.f90` | Kernel construction for each BC type |
| `PStypes.f90` | `FFT_metadata`, `PSolver_options`, `PSolver_energies` |
| `PSbase.f90` | Precision definitions, timing categories |
| `environment.f90` | Cavity construction, dielectric functions, SCCS |
| `psolver_workarrays.f90` | Work array types and allocation |
| `FDder.f90` | Finite difference derivatives for ∇ε |
| `scaling_function.f90` | ISF basis for free BC kernel |
| `gpu_fft_interfaces.f90` | GPU FFT dispatch (CUDA, SYCL) |

## Density Normalization Convention

PSolver expects **physical density** (charge per volume). BigDFT's wavefunction mesh values use a grid normalization where `sum(psi_mesh²) = 1` (see liborbs skill). To form the physical density for PSolver from mesh wavefunctions:

```fortran
rho_physical(r) = psi_mesh(r)² / volume_element
```

where `volume_element = hx * hy * hz` (product of ISF grid spacings, typically `(hgrid/2)³`). This ensures `sum(rho_physical) * volume_element = total_charge`.

PSolver returns the electrostatic potential in physical units (Hartree) and `ehartree = ½ ∫ ρ V dr`.

## Two-Electron Integrals via PSolver

PSolver can be used to compute two-electron repulsion integrals `(ij|kl)` in the Mulliken notation:

```
(ij|kl) = ∫∫ φ_i(r₁)φ_j(r₁) · 1/|r₁-r₂| · φ_k(r₂)φ_l(r₂) dr₁ dr₂
```

### Algorithm

For a given pair (i,j):

1. **Form the pair density** (physical units):
```fortran
rho_ij(r) = phi_i_mesh(r) * phi_j_mesh(r) / volume_element
```

2. **Solve Poisson** -- the density array is overwritten with the potential:
```fortran
call H_potential('G', kernel, rho_ij, pot_dummy, eh_ij, offset, .false., quiet='yes')
! rho_ij now contains V_ij (the Coulomb potential of ρ_ij)
```

3. **Integrate against pair (k,l)** -- no additional volume element factor:
```fortran
eri_ijkl = sum(V_ij(r) * phi_k_mesh(r) * phi_l_mesh(r))
```

The volume element factors cancel between steps 1 and 3 due to BigDFT's normalization convention.

### Optimization

The Poisson solve (expensive) is done once per (i,j) pair. The integration against all (k,l) pairs is cheap (just grid sums). Combined with Cauchy-Schwarz screening, the cost scales as O(N²_significant) Poisson solves rather than O(N⁴).

## Notes

- The density array is **overwritten** by the potential. If you need the density afterward, copy it before calling the solver.
- For periodic systems, the potential has an arbitrary constant offset. The `offset` output from `H_potential` gives the average potential, which BigDFT uses for alignment.
- `pkernel_set` is expensive (builds the FFT kernel). Call it once and reuse the kernel across SCF iterations. Only rebuild if the grid or boundary conditions change.
- For implicit solvent with SCCS, call `pkernel_set` with dielectric arrays, and set `update_cavity=.true.` so the cavity updates each SCF step.
- The ISF order (`isf_order`) controls the accuracy of the free-BC kernel. Higher values give better accuracy at marginal cost. 16 is the default and sufficient for most calculations.
- PSolver can be used standalone (without BigDFT) for any Poisson equation problem. Just link against `libPSolver-1` and `futile`.
- Stress tensor computation adds overhead. Only enable with `calculate_strten=.true.` when needed.
