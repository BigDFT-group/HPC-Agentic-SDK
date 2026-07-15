---
name: bigdft-linear-scaling
description: Configure linear scaling calculations in BigDFT. Covers lin_basis_params (nbasis, rloc, confinement), ig_occupation, and how to add support for new elements. The number of basis functions depends on the pseudopotential electron count. Use when setting up or extending linear scaling calculations.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Linear Scaling Configuration

Linear scaling BigDFT uses localized support functions instead of global wavefunctions. Each atom gets a set of support functions whose number and shape are controlled by `lin_basis_params`, and whose initial occupation is set by `ig_occupation`. These must be consistent with the pseudopotential's valence electron count.

## The Key Relationship

```
Pseudopotential → valence electrons → orbital shells → nbasis + ig_occupation
```

The pseudopotential determines how many valence electrons each element has. Those electrons occupy atomic orbital shells (s, p, d, f), which determines how many support functions (`nbasis`) are needed. The `ig_occupation` tells BigDFT how to distribute electrons across those shells for the initial guess.

### nbasis and Orbital Types

| nbasis | Orbitals | Components | Use for |
|--------|----------|------------|---------|
| 1 | s | 1 | Elements with 1-2 valence e⁻ in s shell (H, Li, Na, K) |
| 4 | s, p | 1+3 | Elements with valence e⁻ in s+p shells (C, N, O, Si, Cl) |
| 9 | s, p, d | 1+3+5 | Transition metals with d electrons (Cu, W) |
| 16 | s, p, d, f | 1+3+5+7 | Lanthanides/actinides with f electrons |

The formula: `nbasis = sum of (2l+1)` for each angular momentum channel l that is occupied.

## Built-In Element Parameters

These elements are defined in the `linear` profile in BigDFT's input variable definitions. They work out of the box.

### Light Elements (s-only, nbasis=1)

| Element | nbasis | rloc | Valence e⁻ | ig_occupation |
|---------|--------|------|-----------|---------------|
| H | 1 | 5.0 | 1 | `1s: 1.0` |
| Li | 1 | 5.5 | 1 | `2s: 1.0` |
| Na | 1 | 7.5 | 1 | `3s: 1.0` |
| K | 1 | 8.0 | 1 | `4s: 1.0` |

### Main Group (s+p, nbasis=4)

| Element | nbasis | rloc | Valence e⁻ | ig_occupation |
|---------|--------|------|-----------|---------------|
| C | 4 | 5.5 | 4 | `2s: 2.0, 2p: 2.0` |
| N | 4 | 5.5 | 5 | `2s: 2.0, 2p: 3.0` |
| O | 4 | 5.5 | 6 | `2s: 2.0, 2p: 4.0` |
| F | 4 | 5.5 | 7 | `2s: 2.0, 2p: 5.0` |
| Si | 4 | 8.0 | 4 | `3s: 2.0, 3p: 2.0` |
| P | 4 | 6.0 | 5 | `3s: 2.0, 3p: 3.0` |
| S | 4 | 6.0 | 6 | `3s: 2.0, 3p: 4.0` |
| Cl | 4 | 6.0 | 7 | `3s: 2.0, 3p: 5.0` |
| Sn | 4 | 6.5 | 4 | `5s: 2.0, 5p: 2.0` |

### Transition Metals

| Element | nbasis | rloc | Valence e⁻ | Notes |
|---------|--------|------|-----------|-------|
| Ca | 5 | 7.5 | 10 | s+p+partial d |
| Zn | 6 | 8.0 | 12 | Filled 3d + 4s |
| Cu | 9 | 7.0 | 11 | 3d¹⁰4s¹ |
| W | 9 | 7.5 | 14 | 5d⁴6s² |
| Ni | 10 | 8.0 | 18 | Large core PSP |
| Fe | 13 | 8.0 | 16 | With 3s3p semicore |

### Common Default Parameters (All Elements)

These apply when not overridden per-element:

```yaml
ao_confinement: -1.0       # Input guess confinement (-1 = automatic)
confinement: [-1.0, 0.0]   # [low_accuracy, high_accuracy] phases
rloc_kernel: 10.0           # Density kernel cutoff radius
rloc_kernel_foe: 12.0       # FOE matrix-vector cutoff radius
```

## Adding a New Element

When your system contains an element not in the built-in list, you need to add three things:

### 1. Determine the PSP and Electron Count

First, decide which pseudopotential to use (see `/bigdft:bigdft-pseudopotentials`). The electron count determines everything else.

```python
# Check the electron count for your PSP
from BigDFT.Inputfiles import Inputfile
inp = Inputfile()
inp.set_psp_nlcc(elements=['Br'])
print(inp['psppar.Br']['No. of Electrons'])  # e.g., 7
```

Or from the `_nzion_default_psp` table in `Atoms.py`:
```
H:1, He:2, Li:1, Be:2, B:3, C:4, N:5, O:6, F:7, Ne:8,
Na:1, Mg:2, Al:3, Si:4, P:5, S:6, Cl:7, Ar:8,
Ca:10, Cu:11, Zn:12, Br:7
```

### 2. Choose nbasis

Based on the valence electron configuration:

| Electron config | nbasis | Example |
|----------------|--------|---------|
| Only s electrons | 1 | H(1), Li(1), Na(1) |
| s + p electrons | 4 | C(4), O(6), Cl(7), Br(7) |
| s + p + d electrons | 9 | Cu(11), Zn(12) with d-shell |
| Semicore s + p + d | 9-13 | Fe(16) with 3s3p semicore |
| s + p + d + f electrons | 16 | Lanthanides |

**Rule:** nbasis must provide enough orbitals to hold all valence electrons. For transition metals with semicore states, you may need more than the minimum.

### 3. Choose rloc (Localization Radius)

Guidelines:

| Element type | Typical rloc | Why |
|-------------|-------------|-----|
| H | 4.0-5.0 | Compact 1s orbital |
| Light main group (C,N,O,F) | 5.0-5.5 | Compact 2p orbitals |
| 3rd row main group (Si,P,S,Cl) | 6.0-8.0 | Larger 3p orbitals |
| Alkali metals (Na,K) | 7.5-8.0 | Diffuse s orbitals |
| Transition metals | 7.0-8.0 | d orbitals need room |

**Rule of thumb:** Start with 6.0 for new elements. Increase if the calculation doesn't converge or support functions are poorly localized. Larger rloc is safer but more expensive.

### 4. Set ig_occupation

The occupation must sum to the number of valence electrons and distribute them across the atomic shells:

```yaml
ig_occupation:
  Br:
    4s: 2.0
    4p: 5.0    # total = 7 = PSP electron count
```

For spin-polarized d-shell elements, you can use fractional occupations or per-component:

```yaml
ig_occupation:
  Fe:
    3s: 2.0
    3p: 6.0
    3d: [1.0, 1.0, 1.0, 1.0, 0.0]   # 4 up, 0 down in 5 d-orbitals
    4s: 2.0
    # total = 2+6+4+2 = 14... but with q16 PSP we have 16 electrons
```

**Important:** The total occupation must equal the number of valence electrons from the PSP. If they don't match, BigDFT will warn.

## YAML Configuration

### Minimal Example (Adding Bromine)

```yaml
dft:
  inputpsiid: linear
  hgrids: 0.4
  disablesym: Yes

lin_basis_params:
  Br:
    nbasis: 4
    ao_confinement: 2.7e-2
    confinement: 2.7e-2
    rloc: 5.5
    rloc_kernel: 8.0
    rloc_kernel_foe: 15.0
  # Include other elements in your system too
  C:
    nbasis: 4
    ao_confinement: 2.7e-2
    confinement: 2.7e-2
    rloc: 5.5
    rloc_kernel: 8.0
    rloc_kernel_foe: 15.0
  H:
    nbasis: 1
    ao_confinement: 4.9e-2
    confinement: 4.9e-2
    rloc: 4.0
    rloc_kernel: 8.0
    rloc_kernel_foe: 15.0

ig_occupation:
  Br:
    4s: 2.0
    4p: 5.0
```

### Full Linear Scaling Setup (From Scratch)

```yaml
dft:
  inputpsiid: linear
  hgrids: 0.4
  rmult: [5.0, 7.0]
  gnrm_cv: 1.e-4
  itermax: 100
  disablesym: Yes

lin_general:
  nit: [2, 3]
  rpnrm_cv: 1.e-6

lin_basis:
  idsx: [5, 0]
  gnrm_cv: [4.e-2, 1.e-2]

lin_kernel:
  linear_method: FOE    # or DIAG, NTPOLY
  rpnrm_cv: 1.e-8

lin_basis_params:
  # One entry per element in your system
  C:
    nbasis: 4
    ao_confinement: 2.7e-2
    confinement: 2.7e-2
    rloc: 5.5
    rloc_kernel: 8.0
    rloc_kernel_foe: 15.0
  H:
    nbasis: 1
    ao_confinement: 4.9e-2
    confinement: 4.9e-2
    rloc: 4.0
    rloc_kernel: 8.0
    rloc_kernel_foe: 15.0
  O:
    nbasis: 4
    ao_confinement: 2.7e-2
    confinement: 2.7e-2
    rloc: 5.5
    rloc_kernel: 8.0
    rloc_kernel_foe: 15.0

ig_occupation:
  C:
    2s: 2.0
    2p: 2.0
  O:
    2s: 2.0
    2p: 4.0
```

### Using the Linear Profile

Instead of specifying everything, you can import the built-in profile and override:

```yaml
import: linear

# Override or add elements
lin_basis_params:
  Br:
    nbasis: 4
    ao_confinement: 2.7e-2
    confinement: 2.7e-2
    rloc: 5.5
    rloc_kernel: 8.0
    rloc_kernel_foe: 15.0

ig_occupation:
  Br:
    4s: 2.0
    4p: 5.0
```

Available profiles: `linear`, `linear_accurate`, `linear_moderate`, `linear_fast`, `linear_purify`.

## Python Configuration

```python
from BigDFT.Inputfiles import Inputfile
from BigDFT import InputActions as A

inp = Inputfile()
inp.set_linear_scaling()

# Or load a profile
inp.load(profile='linear')

# Set NTPoly as the kernel solver
inp.set_ntpoly(thresh_dens=1e-6, conv_dens=1e-4)

# Kernel optimization
inp.optimize_kernel(method='FOE', nit=5, rpnrm=1e-10)

# Support function optimization
inp.optimize_support_functions(nit=1, gnrm=1e-2)

# Coefficient optimization
inp.optimize_coefficients(nit=1, gnrm=1e-5)
```

For `lin_basis_params` and `ig_occupation`, set them directly on the dict:

```python
inp['lin_basis_params'] = {
    'Br': {
        'nbasis': 4,
        'ao_confinement': 2.7e-2,
        'confinement': 2.7e-2,
        'rloc': 5.5,
        'rloc_kernel': 8.0,
        'rloc_kernel_foe': 15.0,
    },
    'C': {
        'nbasis': 4,
        'ao_confinement': 2.7e-2,
        'confinement': 2.7e-2,
        'rloc': 5.5,
        'rloc_kernel': 8.0,
        'rloc_kernel_foe': 15.0,
    },
    'H': {
        'nbasis': 1,
        'ao_confinement': 4.9e-2,
        'confinement': 4.9e-2,
        'rloc': 4.0,
        'rloc_kernel': 8.0,
        'rloc_kernel_foe': 15.0,
    },
}

inp['ig_occupation'] = {
    'Br': {'4s': 2.0, '4p': 5.0},
    'C': {'2s': 2.0, '2p': 2.0},
}
```

## lin_basis_params Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `nbasis` | 4 | Support functions per atom (1, 4, 9, or 16) |
| `ao_confinement` | 8.3e-3 | Input guess confining potential prefactor. Use -1.0 for automatic. |
| `confinement` | [8.3e-3, 0.0] | Confining potential [low_accuracy, high_accuracy]. 0.0 in high accuracy = unconfined. |
| `rloc` | [7.0, 7.0] | Localization radius [low_accuracy, high_accuracy] in bohr |
| `rloc_kernel` | 9.0 | Density kernel cutoff radius (bohr) |
| `rloc_kernel_foe` | 14.0 | FOE matrix-vector multiplication cutoff (bohr). Only matters with `linear_method: FOE`. |

### Parameter Guidelines

- **ao_confinement / confinement:** Controls how tightly support functions are confined. Larger = tighter confinement = faster decay but less accurate. The value 2.7e-2 is a good starting point for main-group elements. Use 4.9e-2 for H.
- **rloc:** Must be large enough that support functions decay to near-zero at the boundary. Too small = artificial confinement artifacts. Too large = expensive. Start with values from similar elements.
- **rloc_kernel:** Controls the sparsity of the density matrix. Larger = more accurate but denser matrices. 8.0-10.0 is typical.
- **rloc_kernel_foe:** Only relevant for FOE method. Must be >= rloc_kernel. 12.0-15.0 is typical.

## Recipes for Common New Elements

### Halogens (F, Cl, Br, I)

All have 7 valence electrons in s+p shells with default PSPs:

```yaml
lin_basis_params:
  Br:
    nbasis: 4
    ao_confinement: 2.7e-2
    confinement: 2.7e-2
    rloc: 5.5
    rloc_kernel: 8.0
    rloc_kernel_foe: 15.0

ig_occupation:
  Br:
    4s: 2.0
    4p: 5.0
```

### Alkaline Earth Metals (Be, Mg, Ca)

2 valence electrons in s shell (default PSP):

```yaml
lin_basis_params:
  Mg:
    nbasis: 1       # Only s-type needed
    ao_confinement: 2.7e-2
    confinement: 2.7e-2
    rloc: 7.0
    rloc_kernel: 10.0
    rloc_kernel_foe: 15.0

ig_occupation:
  Mg:
    3s: 2.0
```

Note: Ca with 10 valence electrons (default PSP includes 3s3p3d) needs nbasis=5 or more.

### Transition Metals (New, Using Small Core PSP)

Example: Adding Mn with q15 (3s²3p⁶3d⁵4s²) Krack PSP:

```yaml
lin_basis_params:
  Mn:
    nbasis: 13        # s+p+d+extra for semicore
    ao_confinement: 2.7e-2
    confinement: 2.7e-2
    rloc: 8.0
    rloc_kernel: 10.0
    rloc_kernel_foe: 15.0

ig_occupation:
  Mn:
    3s: 2.0
    3p: 6.0
    3d: 5.0           # Half-filled d shell
    4s: 2.0
    # total = 15 valence electrons
```

### Transition Metals (Large Core PSP)

Example: Adding Mn with q7 (3d⁵4s²) PSP:

```yaml
lin_basis_params:
  Mn:
    nbasis: 9         # s+p+d sufficient (no semicore)
    ao_confinement: 2.7e-2
    confinement: 2.7e-2
    rloc: 7.0
    rloc_kernel: 10.0
    rloc_kernel_foe: 15.0

ig_occupation:
  Mn:
    3d: 5.0
    4s: 2.0
    # total = 7 valence electrons
```

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| "electrons != occupation" warning | ig_occupation sum doesn't match PSP | Adjust ig_occupation to sum to PSP electron count |
| Support functions not converging | rloc too small, confinement too tight | Increase rloc, decrease ao_confinement |
| Very slow calculation | rloc or rloc_kernel too large | Reduce to smallest stable values |
| Linear scaling gives wrong energy | nbasis too small for element | Increase nbasis to next tier (1→4, 4→9, 9→16) |
| Missing element error | No lin_basis_params for element | Add entry for every element in system |
| FOE not converging | rloc_kernel_foe too small | Increase rloc_kernel_foe |

## Notes

- Every element in the system must have a `lin_basis_params` entry for linear scaling to work.
- The `ig_occupation` is optional for elements in `_ig_default_occupations` (H, He, Li, Be, B, C, N, O, F, Ne, P, S) but required for all others.
- The `import: linear` profile provides parameters for: H, Li, C, N, O, F, Si, P, S, Cl, Na, K, Sn, Ca, Zn, Ni, Cu, Fe, W.
- For elements not in any profile, you must provide `lin_basis_params` and `ig_occupation` explicitly.
- The confinement `[-1.0, 0.0]` means: automatic in low-accuracy phase, unconfined in high-accuracy phase. This is the recommended default.
- `nbasis` must be 1, 4, 9, or 16 -- corresponding to complete angular momentum shells. Intermediate values (like 5 for Ca) are possible but represent partial shells.
