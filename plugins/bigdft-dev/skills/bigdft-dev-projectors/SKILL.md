---
name: bigdft-dev-projectors
description: Developer guide for Kleinman-Bylander pseudopotential projectors. Covers the HGH/HGH-K projector radial functions, the h_ij coupling matrix, the psppar array layout, normalization, and how to compute nonlocal PSP matrix elements. Use when implementing or debugging nonlocal pseudopotential operations.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Kleinman-Bylander Projector Guide

The nonlocal part of the pseudopotential in BigDFT uses the Kleinman-Bylander (KB) separable form. This skill covers the mathematical structure of the projectors, how they are parameterized in PSP files, and how to compute nonlocal matrix elements `⟨φ_i|V_NL|φ_j⟩`.

## The Separable Form

The nonlocal pseudopotential operator is:

```
V_NL = Σ_a Σ_{l=0}^{l_max} Σ_{m=-l}^{l} Σ_{i,j=1}^{n_proj(l)} |p^a_{lmi}⟩ h^a_{l,ij} ⟨p^a_{lmj}|
```

where:
- `a` runs over atoms
- `l` is the angular momentum channel (s=0, p=1, d=2, f=3)
- `m` is the magnetic quantum number (-l to +l, giving 2l+1 components)
- `i,j` are projector indices within a channel (up to 3 for HGH)
- `p^a_{lmi}(r)` is a projector function centered on atom `a`
- `h^a_{l,ij}` is the coupling matrix (symmetric, from the PSP file)

## Matrix Elements

To compute `⟨φ_n|V_NL|φ_{n'}⟩` between two basis functions:

```
⟨φ_n|V_NL|φ_{n'}⟩ = Σ_a Σ_{l,m} Σ_{i,j} ⟨φ_n|p^a_{lmi}⟩ · h^a_{l,ij} · ⟨p^a_{lmj}|φ_{n'}⟩
```

This factorizes into:
1. Compute all projector overlaps `c_{n,a,l,m,i} = ⟨φ_n|p^a_{lmi}⟩`
2. Contract with the h_ij matrix

In matrix form for a fixed atom `a` and channel `l`:

```
V_NL^{a,l}_{n,n'} = Σ_{m} Σ_{i,j} c_{n,lmi} · h_{l,ij} · c_{n',lmj}
```

Or equivalently: `V_NL^{a,l} = C^{a,l} · (H_l ⊗ I_{2l+1}) · (C^{a,l})^T`

where `C^{a,l}` is the matrix of projector overlaps with shape `(nbasis, n_proj × (2l+1))`.

## Projector Radial Functions

The HGH projectors have the form:

```
p^a_{lmi}(r) = Y_{lm}(r̂) · R_i^l(|r - R_a|)
```

where `Y_{lm}` is a real spherical harmonic and `R_i^l(r)` is a radial function.

### Radial Functions

The radial part for projector index `i` in channel `l` is a Gaussian times a polynomial:

```
R_i^l(r) = N_i^l · r^{l + 2(i-1)} · exp(-r²/(2·r_l²))
```

where:
- `r_l` is the projector radius for channel `l` (from the PSP file: `psppar(l,0)`)
- `N_i^l` is the normalization constant
- The polynomial power `l + 2(i-1)` means:
  - i=1: r^l (lowest order)
  - i=2: r^{l+2}
  - i=3: r^{l+4}

### Explicit Forms by Channel

**s-channel (l=0):**
```
R_1^0(r) = N · exp(-r²/(2·r_0²))
R_2^0(r) = N · r² · exp(-r²/(2·r_0²))
R_3^0(r) = N · r⁴ · exp(-r²/(2·r_0²))
```

**p-channel (l=1):**
```
R_1^1(r) = N · r · exp(-r²/(2·r_1²))
R_2^1(r) = N · r³ · exp(-r²/(2·r_1²))
R_3^1(r) = N · r⁵ · exp(-r²/(2·r_1²))
```

**d-channel (l=2):**
```
R_1^2(r) = N · r² · exp(-r²/(2·r_2²))
R_2^2(r) = N · r⁴ · exp(-r²/(2·r_2²))
R_3^2(r) = N · r⁶ · exp(-r²/(2·r_2²))
```

**f-channel (l=3):**
```
R_1^3(r) = N · r³ · exp(-r²/(2·r_3²))
R_2^3(r) = N · r⁵ · exp(-r²/(2·r_3²))
R_3^3(r) = N · r⁷ · exp(-r²/(2·r_3²))
```

### Normalization Constants

The normalization ensures `∫ |p_{lmi}(r)|² d³r = 1`.

For the Gaussian exponent `α = 1/(2·r_l²)`, and defining `σ = r_l`:

```
N_i^l = √2 · π^{-1/4} · 2^{(l-1)/2 + i - 1} / [σ^{(2(l-1) + 4i - 1)/2} · c_l · √(n_i^l)]
```

where the angular momentum factor `c_l` and polynomial normalization `n_i^l` are:

| l | c_l | n_1^l | n_2^l | n_3^l |
|---|-----|-------|-------|-------|
| 0 | 1 | 1 | 15 | 945 |
| 1 | √3 | 1 | 35 | 10395 |
| 2 | √15 | 1 | 63 | 45045 |
| 3 | √105 | 1 | 99 | 135135 |

The `n_i^l` values follow the pattern of products of consecutive odd numbers. For example:
- n_2^0 = 3·5 = 15
- n_3^0 = 3·5·7·9 = 945
- n_2^1 = 5·7 = 35

## Real Spherical Harmonics

BigDFT uses real spherical harmonics (not complex). For the first few channels:

**l=0 (1 component, m=0):**
```
Y_00 = 1/(2√π)
```

**l=1 (3 components, m=-1,0,1):**
```
Y_{1,-1} = √(3/(4π)) · y/r
Y_{1,0}  = √(3/(4π)) · z/r
Y_{1,1}  = √(3/(4π)) · x/r
```

**l=2 (5 components, m=-2,-1,0,1,2):**
```
Y_{2,-2} = √(15/(16π)) · 2xy/r²
Y_{2,-1} = √(15/(16π)) · 2yz/r²
Y_{2,0}  = √(5/(16π)) · (3z²-r²)/r²
Y_{2,1}  = √(15/(16π)) · 2xz/r²
Y_{2,2}  = √(15/(16π)) · (x²-y²)/r²
```

In practice, when evaluating projectors on a grid, you compute `x = r_x - R_x`, `y = r_y - R_y`, `z = r_z - R_z`, and `r = sqrt(x²+y²+z²)`, then form the product `Y_{lm}(x,y,z) · R_i^l(r)` directly without separating angular and radial parts. The angular dependence is encoded as polynomial factors in x, y, z.

## The psppar Array Layout

PSP parameters are stored in the `psppar` array with indices `psppar(l, k)`:

### Local Potential (l=0 row)

```
psppar(0, 0)  = rloc          ! Local potential Gaussian radius
psppar(0, 1)  = c1            ! Local potential coefficient 1
psppar(0, 2)  = c2            ! Local potential coefficient 2
psppar(0, 3)  = c3            ! Local potential coefficient 3
psppar(0, 4)  = c4            ! Local potential coefficient 4
```

The local potential is:

```
V_loc(r) = -Z_ion/r · erf(r/(√2·rloc)) + exp(-r²/(2·rloc²)) · (c1 + c2·(r/rloc)² + c3·(r/rloc)⁴ + c4·(r/rloc)⁶)
```

### Nonlocal Channels (l=1,2,3,4 rows)

```
psppar(l, 0)  = r_l           ! Projector radius for channel l
psppar(l, 1)  = h_{11}        ! Diagonal coupling
psppar(l, 2)  = h_{12}        ! Off-diagonal coupling (HGH-K: stored directly)
psppar(l, 3)  = h_{13}        ! Off-diagonal coupling
psppar(l, 4)  = h_{22}        ! Diagonal coupling
psppar(l, 5)  = h_{23}        ! Off-diagonal coupling
psppar(l, 6)  = h_{33}        ! Diagonal coupling
```

The h_ij matrix for channel `l` is symmetric and stored as upper triangular:

```
h_l = | h_{11}  h_{12}  h_{13} |     psppar(l, 1)  psppar(l, 2)  psppar(l, 3)
      | h_{12}  h_{22}  h_{23} |  =  psppar(l, 2)  psppar(l, 4)  psppar(l, 5)
      | h_{13}  h_{23}  h_{33} |     psppar(l, 3)  psppar(l, 5)  psppar(l, 6)
```

### Number of Projectors per Channel

Not all channels have 3 projectors. The number `n_proj(l)` is determined by how many h_ij entries are nonzero:
- If only h_{11} ≠ 0: n_proj = 1
- If h_{22} ≠ 0: n_proj ≥ 2
- If h_{33} ≠ 0: n_proj = 3

Most light elements have only 1 projector per channel. Transition metals and heavier elements may have 2-3.

## Reading PSP Files

### HGH-K Text Format

```
Line 1: rloc  nloc  c1  c2  [c3  c4]     # local potential
Line 2: nlterms                            # number of nonlocal channels
# For each channel l = 1..nlterms:
Line:   r_l  nprl  h_11  [h_12  h_13]     # radius, n_proj, first row of h_ij
Line:                h_22  [h_23]          # second row (if nprl >= 2)
Line:                      h_33            # third row (if nprl >= 3)
# For l >= 2, additional k_ij lines follow (spin-orbit, currently skipped)
```

### YAML Format (Database)

```yaml
NonLocal PSP Parameters:
- Channel (l): 0
  Rloc: 0.434
  h_ij terms:
  - 9.020        # h_11
  - 0.555        # h_12
  - 0.0          # h_13
  - -2.419       # h_22
  - 0.0          # h_23
  - 0.0          # h_33
```

The h_ij terms are stored as a flat list in the order: h_11, h_12, h_13, h_22, h_23, h_33.

## Concrete Examples

### Carbon (HGH-K, PBE)

```
rloc = 0.3385, c1 = -8.804, c2 = 1.339
Channel s (l=0): r_0 = 0.3026, h_11 = 9.622, n_proj = 1
Channel p (l=1): r_1 = 0.2915, h_11 = 0.000, n_proj = 1 (effectively no p-projector)
```

Carbon has 4 valence electrons (2s²2p²), 1 s-projector, and a p-projector with zero coupling (h_11=0 for p).

### Carbon (HGH-K + NLCC)

```
rloc = 0.4133, c1 = -5.729, c2 = 0.875
Channel s (l=0): r_0 = 0.4341, n_proj = 2
  h = | 9.020   0.555 |
      | 0.555  -2.419 |
NLCC: rcore = 0.362, core_charge = 20.303
```

This NLCC version has 2 s-projectors with off-diagonal coupling.

### Oxygen (HGH-K + NLCC)

```
rloc = 0.3455, c1 = -11.744, c2 = 1.907
Channel s (l=0): r_0 = 0.3680, n_proj = 2
  h = | 10.859  -0.430 |
      | -0.430  -2.129 |
NLCC: rcore = 0.345, core_charge = 9.021
```

6 valence electrons (2s²2p⁴), 2 s-projectors, no p-projector.

## Computing Projector Overlaps on the Grid

To compute `⟨φ_n|p^a_{lmi}⟩` where `φ_n` is a basis function on the wavelet grid:

### Method 1: Direct Grid Evaluation (Recommended for Standalone Code)

```fortran
! For each atom a, channel l, projector index i, magnetic quantum number m:
!   1. Evaluate p_{lmi}(r) on the grid points where φ_n is nonzero
!   2. Multiply pointwise and sum (numerical integration)

overlap = 0.0_dp
bit = box_iter(mesh, nbox=nbox_phi_n, origin=rxyz_atom)
do while (box_next_point(bit))
  ! Distance from atom center
  dx = bit%rxyz(1) - rxyz_atom(1)
  dy = bit%rxyz(2) - rxyz_atom(2)
  dz = bit%rxyz(3) - rxyz_atom(3)
  r2 = dx*dx + dy*dy + dz*dz
  r = sqrt(r2)

  ! Gaussian radial part
  gauss = exp(-r2 / (2.0_dp * r_l**2))

  ! Radial polynomial: r^{l + 2(i-1)}
  radial = r**(l + 2*(i-1)) * gauss * norm_factor

  ! Real spherical harmonic (angular part)
  ! For l=0: ylm = 1/(2*sqrt(pi))
  ! For l=1, m=0: ylm = sqrt(3/(4*pi)) * dz/r  (etc.)
  ylm = real_spherical_harmonic(l, m, dx, dy, dz, r)

  ! Projector value at this grid point
  proj_val = radial * ylm

  ! Basis function value at this grid point
  phi_val = phi_on_mesh(bit%ind)

  ! Accumulate overlap
  overlap = overlap + phi_val * proj_val * mesh%volume_element
end do
```

### Method 2: Use BigDFT's Projector Machinery

If linking against BigDFT, use the `DFT_PSP_projectors` module which handles projector construction, conversion to wavelets, and scalar product computation internally.

```fortran
use psp_projectors_base
use psp_projectors

! The projector iterator handles all the details:
! - Constructs Gaussian projectors from PSP parameters
! - Converts to wavelet representation (via Gaussian→wavelet projection)
! - Computes scalar products <phi|p> using wavelet keys

call DFT_PSP_projectors_iter_new(psp_it, ...)
call DFT_PSP_projectors_iter_scpr(psp_it, psi_it, ...)
```

## Assembling the V_NL Matrix

```fortran
! Pseudocode for computing V_NL matrix in the support function basis

real(dp), dimension(nbasis, nbasis) :: V_NL
V_NL = 0.0_dp

do iat = 1, nat   ! loop over atoms
  ityp = iatype(iat)

  do l = 0, lmax(ityp)   ! loop over angular momentum channels
    r_l = psppar(l+1, 0, ityp)    ! projector radius (+1 because l=0 is local)
    if (r_l == 0.0_dp) cycle       ! no projector for this channel
    nproj = count_projectors(l, ityp)

    ! Build h_ij matrix for this channel
    call build_hij(l, ityp, psppar, hij)   ! extract from psppar array

    ! Compute projector overlaps with all basis functions
    ! c(n, m, i) = ⟨φ_n | p^{iat}_{l,m,i}⟩
    real(dp), dimension(nbasis, 2*l+1, nproj) :: c
    c = 0.0_dp

    do iproj = 1, nproj
      do m = -l, l
        do n = 1, nbasis
          ! Skip if basis function n doesn't overlap with atom iat's projector
          if (distance(dom, lr(n)%locregCenter, rxyz(:,iat)) > lr(n)%locrad + proj_cutoff) cycle
          c(n, m+l+1, iproj) = compute_projector_overlap(n, iat, l, m, iproj)
        end do
      end do
    end do

    ! Contract: V_NL += Σ_{m,i,j} c(:,m,i) * h_{ij} * c(:,m,j)^T
    do m = 1, 2*l+1
      do iproj = 1, nproj
        do jproj = 1, nproj
          if (hij(iproj, jproj) == 0.0_dp) cycle
          ! Rank-1 update: V_NL += h_{ij} * c(:,m,i) * c(:,m,j)^T
          call dger(nbasis, nbasis, hij(iproj, jproj), &
                    c(:, m, iproj), 1, c(:, m, jproj), 1, V_NL, nbasis)
        end do
      end do
    end do

  end do  ! l
end do  ! iat
```

## Extracting h_ij from psppar

```fortran
subroutine build_hij(l, ityp, psppar, hij)
  integer, intent(in) :: l, ityp
  real(dp), dimension(0:4, 0:6, *), intent(in) :: psppar
  real(dp), dimension(3, 3), intent(out) :: hij
  integer :: lp

  hij = 0.0_dp
  lp = l + 1   ! psppar uses 1-based indexing for nonlocal channels

  hij(1,1) = psppar(lp, 1, ityp)
  hij(1,2) = psppar(lp, 2, ityp)
  hij(1,3) = psppar(lp, 3, ityp)
  hij(2,2) = psppar(lp, 4, ityp)
  hij(2,3) = psppar(lp, 5, ityp)
  hij(3,3) = psppar(lp, 6, ityp)

  ! Symmetric
  hij(2,1) = hij(1,2)
  hij(3,1) = hij(1,3)
  hij(3,2) = hij(2,3)
end subroutine
```

## Projector Cutoff Radius

Projectors are Gaussians, so they decay as `exp(-r²/(2r_l²))`. A practical cutoff is where the projector drops below numerical noise:

```fortran
! Cutoff at 10σ captures essentially all of the Gaussian
proj_cutoff = 10.0_dp * r_l
```

For typical values (r_l = 0.3-0.5 bohr), the cutoff is 3-5 bohr. This means projectors are very localized -- most basis functions won't overlap with any given atom's projectors.

## NLCC (Non-Linear Core Correction)

NLCC adds a frozen core charge density to the total density for XC evaluation. It does NOT affect the nonlocal projectors -- the h_ij matrix and projector functions are the same with or without NLCC. The core charge is a separate Gaussian:

```
ρ_core(r) = q_core / ((2π)^{3/2} · r_core³) · exp(-r²/(2·r_core²))
```

This is relevant for DFT (affects V_XC) but not for the bare HF nonlocal PSP matrix elements.

## Key Source Files

| File | What it contains |
|------|-----------------|
| `pseudopotentials.f90` | PSP data types, psppar parsing, h_ij construction, `apply_hij_coeff` |
| `psp_projectors_base.f90` | `atomic_projectors` and `DFT_PSP_projectors` type definitions |
| `psp_projectors.f90` | Projector construction, scalar product computation, nonlocal application |
| `gaussians.f90` | `gaussian_basis_from_psp` -- converts PSP parameters to Gaussian basis, normalization |

## Notes

- The psppar array uses **1-based indexing** for nonlocal channels: `psppar(1,:)` is the first nonlocal channel (l=0, s-wave), `psppar(2,:)` is l=1 (p-wave), etc. Row 0 is the local potential.
- The h_ij matrix is always symmetric: `h_{ij} = h_{ji}`.
- For HGH-K format, h_ij values are stored directly in the PSP file. For the original HGH format, off-diagonal elements are derived from diagonal elements using specific algebraic relations (see GTH paper, Eq. 9). BigDFT handles both conventions transparently.
- Spin-orbit coupling terms (k_ij) exist in the PSP file for l ≥ 1 but are currently skipped by BigDFT.
- The projector overlap `⟨φ|p⟩` is an inner product over 3D space. On the grid, this is `Σ_r φ(r) · p(r) · dV`. The accuracy depends on grid resolution (`hgrids`).
- Most light elements (H, C, N, O) have at most 1-2 projectors per channel. The V_NL matrix computation is cheap compared to the two-electron integrals.
- When evaluating `Y_{lm} · R_i^l` at r=0, the product is zero for l>0 (because of the r^l factor) and finite for l=0. No special handling needed.
