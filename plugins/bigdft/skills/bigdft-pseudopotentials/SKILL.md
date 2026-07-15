---
name: bigdft-pseudopotentials
description: Set up pseudopotentials for BigDFT calculations. Covers the Python API (set_psp_nlcc, set_psp_krack, set_psp_file), command-line file copying, PSP formats, and the relationship between PSP choice and electron count. Use when configuring pseudopotentials or troubleshooting electron count issues.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# BigDFT Pseudopotentials

BigDFT uses norm-conserving pseudopotentials in the Goedecker-Teter-Hutter (GTH) family. The choice of pseudopotential determines how many valence electrons each atom has, which in turn affects the calculation cost, accuracy, and the linear scaling basis configuration.

## Available PSP Types

| Type | Description | Python API | Location |
|------|-------------|-----------|----------|
| **HGH** | Original Hartwigsen-Goedecker-Hutter | (hardcoded default) | `bigdft/utils/PSPfiles/HGH/` |
| **HGH-K** | HGH with Kleynman-Bylander separable form | `set_psp_file` | `bigdft/utils/PSPfiles/HGH-K/` |
| **HGH-K + NLCC** | HGH-K with Non-Linear Core Correction | `set_psp_nlcc` | `PyBigDFT/BigDFT/Database/psppar/SS/` |
| **Krack (PBE)** | Goedecker-Krack, PBE functional | `set_psp_krack('PBE')` | `PyBigDFT/BigDFT/Database/psppar/Krack/PBE/` |
| **Krack (LDA)** | Goedecker-Krack, LDA functional | `set_psp_krack('LDA')` | `PyBigDFT/BigDFT/Database/psppar/Krack/LDA/` |
| **All-Electron** | No pseudopotential (full nuclear potential) | `set_psp_AE` | (generated) |

**Default behavior:** If no PSP is specified, BigDFT uses hardcoded HGH parameters for common elements. For anything beyond the basics, explicitly set pseudopotentials.

## Python API (Recommended)

### NLCC Pseudopotentials (Recommended for Most Calculations)

```python
from BigDFT.Inputfiles import Inputfile

inp = Inputfile()

# Use NLCC for all elements in the system
inp.set_psp_nlcc()

# Use NLCC for specific elements only
inp.set_psp_nlcc(elements=['C', 'H', 'O', 'N'])
```

NLCC (Non-Linear Core Correction) pseudopotentials are HGH-K format with a core charge correction that improves accuracy, especially for properties sensitive to the core-valence interaction. Available for 31 elements.

### Krack Pseudopotentials

```python
# PBE functional (72 elements available)
inp.set_psp_krack('PBE')
inp.set_psp_krack('PBE', elements=['Fe', 'O'])

# LDA functional
inp.set_psp_krack('LDA')
inp.set_psp_krack('LDA', elements=['Si', 'O'])
```

**Important:** For some elements, multiple Krack PSPs exist with different valence electron counts (e.g., Fe-q8 and Fe-q16, Ag-q11 and Ag-q19). The Python API selects the smallest electron count by default. To use a different one, use `set_psp_file` with the specific file.

### Single PSP File

```python
# From a file path
inp.set_psp_file(filename='psppar.Fe')

# Auto-detects element from filename
# psppar.Fe → element 'Fe'

# Explicit element
inp.set_psp_file(filename='/path/to/custom_psp', element='Fe')
```

### Directory of PSP Files

```python
# Load all psppar.* files from a directory
inp.set_psp_directory(directory='/path/to/my_psps/')

# Filter to specific elements
inp.set_psp_directory(directory='/path/to/my_psps/', elements=['C', 'O', 'H'])
```

### All-Electron (No Pseudopotential)

```python
# Specify inverse scale per element
inp.set_psp_AE(scales={'H': 0.6, 'O': 0.4})
```

This creates a minimal PSP entry with all electrons as valence (Z_ion = Z_atomic).

## Command-Line Method (Copying PSP Files)

For the Fortran executable, BigDFT looks for files named `psppar.{Element}` in the run directory.

### File Naming Convention

The file **must** be named `psppar.{Element}` where `{Element}` is the atomic symbol with correct capitalization:

```
psppar.H     # Hydrogen
psppar.C     # Carbon
psppar.Fe    # Iron (capital F, lowercase e)
psppar.Si    # Silicon
```

### Copying from the Source Tree

```bash
# Source locations
PSPDIR=$BIGDFT_ROOT/bigdft/utils/PSPfiles

# HGH format (basic)
cp $PSPDIR/HGH/psppar.C .
cp $PSPDIR/HGH/psppar.H .

# HGH-K format (separable)
cp $PSPDIR/HGH-K/psppar.C .
cp $PSPDIR/HGH-K/psppar.Si .

# Krack format (rename required -- Krack files use Element-qN naming)
cp $PSPDIR/Krach-PBE/Fe-q16 psppar.Fe
cp $PSPDIR/Krach-PBE/Ag-q11 psppar.Ag

# LDA variants from root
cp $PSPDIR/psppar.C_lda psppar.C
```

### Krack File Naming

Krack PSPs in the source tree use a different naming convention:

```
Element-qN    (e.g., Fe-q8, Fe-q16, Ag-q11, Ag-q19)
```

Where `N` is the number of valence electrons. You must rename to `psppar.{Element}` when copying:

```bash
cp Krach-PBE/Fe-q16 psppar.Fe
```

### Specifying in YAML Input

You can also embed PSP data directly in `input.yaml`:

```yaml
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

## PSP and Electron Count

The pseudopotential determines how many electrons are treated as valence. This number is critical because it affects:

1. **Calculation cost** -- more valence electrons = more expensive
2. **Linear scaling `nbasis`** -- must accommodate all valence orbital types
3. **Input guess occupations** (`ig_occupation`) -- must sum to the valence electron count
4. **System charge** -- `qcharge` is relative to the PSP electron count

### Default Valence Electron Counts

These are the defaults used when no explicit PSP is set (from hardcoded HGH data):

| Element | Valence e⁻ | Shells | Element | Valence e⁻ | Shells |
|---------|-----------|--------|---------|-----------|--------|
| H | 1 | 1s | Na | 1 | 3s |
| He | 2 | 1s | Mg | 2 | 3s |
| Li | 1 | 2s | Al | 3 | 3s3p |
| Be | 2 | 2s | Si | 4 | 3s3p |
| B | 3 | 2s2p | P | 5 | 3s3p |
| C | 4 | 2s2p | S | 6 | 3s3p |
| N | 5 | 2s2p | Cl | 7 | 3s3p |
| O | 6 | 2s2p | Ar | 8 | 3s3p |
| F | 7 | 2s2p | Ca | 10 | 3s3p3d |
| Ne | 8 | 2s2p | Cu | 11 | 3d4s |
| | | | Zn | 12 | 3d4s |

### Transition Metal Considerations

Transition metals often have multiple PSP options with different core/valence partitions:

| Element | Small core | Large core | Notes |
|---------|-----------|-----------|-------|
| Fe | q16 (3s3p3d4s) | q8 (3d4s) | q16 needed for accurate magnetism |
| Ag | q19 (4s4p4d5s) | q11 (4d5s) | q11 sufficient for most uses |
| Cu | q19 (3s3p3d4s) | q11 (3d4s) | q11 is the default |
| Ni | q18 (3s3p3d4s) | q10 (3d4s) | q18 for bulk properties |

**Rule of thumb:** Use the small-core (more electrons) PSP when:
- Studying magnetic properties
- Core-valence overlap matters (high pressure, small bond lengths)
- High accuracy is needed for energy differences

Use the large-core (fewer electrons) PSP when:
- Cost matters more than accuracy
- Qualitative results are sufficient

### Reading the Electron Count from a PSP

In the PSP file or YAML, look for the `No. of Electrons` or `zion` field:

```yaml
# YAML format
No. of Electrons: 6    # ← this is the valence electron count

# Text format (second number on first data line)
8   6   960508         # zatom=8 (oxygen), zion=6 (valence electrons)
```

In Python:

```python
from BigDFT.Logfiles import Logfile
log = Logfile('log-output.yaml')
# The logfile reports the PSP that was used and its electron count
```

## Checking Which PSP Was Used

After a calculation, the logfile reports the PSP for each element:

```yaml
psppar.O:
  Pseudopotential type: HGH-K + NLCC
  No. of Electrons: 6
  ...
```

You can also check via:

```python
from BigDFT.Inputfiles import Inputfile

inp = Inputfile()
inp.set_psp_nlcc(elements=['O'])
print(inp['psppar.O'])  # Shows the full PSP dict
print(inp['psppar.O']['No. of Electrons'])  # 6
```

## Notes

- BigDFT's PSP lookup order: inline YAML input → `psppar.{Element}` file in run directory → hardcoded defaults.
- The `Pseudopotential XC` field in the PSP should match your calculation's XC functional. Mismatches produce a warning but the code will still run.
- NLCC PSPs (`set_psp_nlcc`) use `Pseudopotential XC: -101130` which corresponds to PBE.
- Krack PSPs are available for 72 elements (PBE) and more (LDA).
- The NLCC database has 31 elements. For elements not covered, fall back to Krack or HGH.
- When using `set_psp_krack`, the PSP with the **smallest** electron count is selected by default. For transition metals, you may want the larger core explicitly.
- The `psppar.{Element}_lda` naming in the root PSPfiles directory indicates LDA-specific variants.
