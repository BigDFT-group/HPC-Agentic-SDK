---
name: bigdft-dev-variables
description: Add or modify input variables in BigDFT, CheSS, or PSolver. Covers the full pipeline from YAML definition through code generation, Fortran parsing, and accessing values in code. Use when adding new input parameters or modifying existing ones.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Adding and Modifying Input Variables

This skill covers the complete pipeline for input variables in BigDFT, CheSS, and PSolver. A variable flows through these stages:

```
YAML definition → C string (build time) → Fortran dictionary (runtime) → derived type field → use in code
```

When the user wants to add or modify an input variable, walk through each stage. **Ask which module (bigdft, chess, or psolver) the variable belongs to** before starting, then follow the appropriate file paths.

## File Map

| Stage | BigDFT | CheSS | PSolver |
|-------|--------|-------|---------|
| YAML definition | `bigdft/src/input_variables_definition.yaml` | `chess/src/chess_input_variables_definition.yaml` | `psolver/src/PS_input_variables_definition.yaml` |
| Build rule | `bigdft/src/import_database.mk` | `chess/src/import_database.mk` | `psolver/src/Makefile.am` |
| Key constants | `bigdft/src/helpers/public_keys.f90` | `chess/src/chess_base.f90` | `psolver/src/PStypes.f90` |
| Derived type | `bigdft/src/modules/input_keys.f90` (`input_variables`) | `chess/src/chess_base.f90` (`chess_params`, `foe_params`) | `psolver/src/PStypes.f90` (`PSolver_options`) |
| Dict → type mapping | `bigdft/src/modules/input_keys.f90` (`input_set_dict`) | `chess/src/chess_base.f90` (`chess_input_fill`) | `psolver/src/PSolver_Main.f90` (`PS_input_fill`) |
| Default initialization | `bigdft/src/modules/input_keys.f90` (`default_input_variables`) | `chess/src/chess_base.f90` (`chess_init`) | `psolver/src/PStypes.f90` |
| Dict initialization | `bigdft/src/modules/input_dicts.f90` | `chess/src/chess_base.f90` (`chess_input_dict`) | `psolver/src/PStypes.f90` (`PS_input_dict`) |

## Step 1: YAML Definition

Add the variable to the appropriate YAML file. The schema uses these reserved keywords:

```yaml
section_name:
  variable_name:
    COMMENT: Short description (shown in logfile output)
    DESCRIPTION: |
      Extended multi-line description for documentation.
      Explain what the variable controls and when to change it.
    default: 1.0e-4
    RANGE: [0.0, 1.0]          # numeric bounds (optional)
    EXCLUSIVE:                  # allowed discrete values (optional)
      1: Description of option 1
      2: Description of option 2
    CONDITION:                  # only valid when another var has certain values (optional)
      MASTER_KEY: other_variable
      WHEN: [value1, value2]   # valid when master equals these
      # or: WHEN_NOT: [value3] # valid when master does NOT equal these
    PROFILE_FROM: other_variable  # inherit profile from another var (optional)
    fast: 1.0e-3               # named profile value (optional)
    accurate: 1.0e-6           # another named profile (optional)
```

### Required Fields
- `COMMENT` -- always include, it appears in logfile output
- `default` -- always include, it's the value used when user doesn't specify

### Optional Fields
- `DESCRIPTION` -- for documentation; multi-line with `|`
- `RANGE` -- `[min, max]` for numeric validation; use `.inf` for unbounded
- `EXCLUSIVE` -- mapping of allowed values with descriptions, OR a list of allowed values
- `CONDITION` -- makes variable only meaningful when a master variable has certain values
- `PROFILE_FROM` -- links this variable's profile to another's (when master switches profile, this one follows)
- Named profiles (e.g., `fast:`, `accurate:`) -- alternative values selectable by name

### BigDFT Example

Adding a new variable `my_threshold` to the `dft` section:

```yaml
dft:
  # ... existing variables ...
  my_threshold:
    COMMENT: Convergence threshold for my new feature
    DESCRIPTION: |
      Controls the convergence criterion for the new algorithm.
      Smaller values give tighter convergence but cost more iterations.
    RANGE: [1.0e-12, 1.0]
    default: 1.0e-4
    accurate: 1.0e-6
    fast: 1.0e-3
```

### CheSS Example

Adding a variable to the `foe` section:

```yaml
foe:
  my_foe_param:
    COMMENT: Description of FOE parameter
    RANGE: [0.0, 1.0]
    default: 0.5
```

### PSolver Example

Adding a variable to the `environment` section with a condition:

```yaml
environment:
  my_solvent_param:
    COMMENT: Custom solvent parameter
    RANGE: [0.0, 100.0]
    default: 1.0
    CONDITION:
      MASTER_KEY: cavity
      WHEN_NOT: [none]
    PROFILE_FROM: cavity
    soft-sphere: 1.5
    sccs: 2.0
```

## Step 2: Key Constant (BigDFT Only)

For BigDFT variables, add a string constant to `bigdft/src/helpers/public_keys.f90`:

```fortran
character(len = *), parameter :: MY_THRESHOLD = "my_threshold"
```

The string value **must exactly match** the YAML key name.

Key constants are organized by section. Find the right group:

```fortran
! DFT section keys
character(len = *), parameter :: HGRIDS = "hgrids"
character(len = *), parameter :: IXC = "ixc"
character(len = *), parameter :: NCHARGE = "qcharge"
! ... add yours in the appropriate group ...
```

For CheSS and PSolver, key constants are defined locally in their respective source files (`chess_base.f90`, `PStypes.f90` or `PSolver_Main.f90`).

## Step 3: Derived Type Field

Add a field to the Fortran derived type that will hold the parsed value.

### BigDFT

In `bigdft/src/modules/input_keys.f90`, find the `input_variables` type (around line 165) and add:

```fortran
type :: input_variables
   ! ... existing fields ...

   !> Convergence threshold for my new feature
   real(gp) :: my_threshold

   ! ... more fields ...
end type input_variables
```

Use the appropriate Fortran type:
- `integer` for integers and enumerator indices
- `real(gp)` for floating point (`gp` is the global precision kind)
- `logical` for booleans (YAML Yes/No)
- `character(len=N)` for strings
- `real(gp), dimension(N)` for fixed-size arrays
- `type(f_enumerator)` for enumerated values with string labels

### CheSS

In `chess/src/chess_base.f90`, add to the appropriate params type:

```fortran
type :: foe_params
   ! ... existing fields ...
   real(kind=8) :: my_foe_param
end type foe_params
```

### PSolver

In `psolver/src/PStypes.f90`, add to `PSolver_options` or the relevant type:

```fortran
type :: PSolver_options
   ! ... existing fields ...
   real(dp) :: my_solvent_param
end type PSolver_options
```

## Step 4: Default Value

### BigDFT

In `input_keys.f90`, find the `default_input_variables` subroutine (or the section-specific default routine like `dft_input_variables_default`) and add:

```fortran
subroutine dft_input_variables_default(in)
  type(input_variables), intent(inout) :: in
  ! ... existing defaults ...
  in%my_threshold = 1.0e-4_gp   ! must match YAML default
end subroutine
```

### CheSS

In `chess_base.f90`, in the initialization code inside `chess_init` or equivalent:

```fortran
cp%foe%my_foe_param = 0.5d0
```

### PSolver

In `PStypes.f90` or the initialization routine:

```fortran
opt%my_solvent_param = 1.0d0
```

## Step 5: Dictionary → Type Mapping

This is where the parsed YAML dictionary value gets transferred into the Fortran struct field.

### BigDFT

In `input_keys.f90`, find the `input_set_dict` subroutine (around line 1641). It has a nested `select case` structure organized by section, then by key:

```fortran
subroutine input_set_dict(in, level, val)
  type(input_variables), intent(inout) :: in
  character(len=*), intent(in) :: level
  type(dictionary), pointer :: val

  select case(trim(level))

  case(DFT_VARIABLES)
    select case(trim(dict_key(val)))

    case(HGRIDS)
      dummy_gp(1:3) = val
      in%hx = dummy_gp(1)
      in%hy = dummy_gp(2)
      in%hz = dummy_gp(3)

    case(IXC)
      in%ixc = val

    ! ADD YOUR VARIABLE HERE:
    case(MY_THRESHOLD)
      in%my_threshold = val

    end select

  case("geopt")
    ! ... geopt variables ...

  end select
end subroutine
```

**Type conversion patterns** found in the existing code:

```fortran
! Simple scalar assignment (auto-converts from dict value)
in%itermax = val                ! integer
in%my_threshold = val           ! real
in%disablesym = val             ! logical (YAML Yes/No → .true./.false.)

! Array unpacking
dummy_gp(1:3) = val             ! extract array from dict
in%hx = dummy_gp(1)            ! assign individual elements

! String with integer fallback
str = val
if (is_atoi(str)) then
  ipos = val
  in%qcharge = real(ipos, gp)
else
  in%qcharge = val
end if

! String to enumerator
str = val
select case(trim(str))
case('gaussian')
  in%projection = PROJECTION_1D_SEPARABLE
case('radial')
  in%projection = PROJECTION_RS
end select

! Enumerator type
in%geopt_approach = val         ! f_enumerator assignment from string
```

### CheSS

In `chess_base.f90`, find `chess_input_fill`:

```fortran
subroutine chess_input_fill(val, level, cp)
  type(chess_params), intent(inout) :: cp
  character(len=*), intent(in) :: level
  type(dictionary), pointer :: val

  select case(trim(level))
  case(FOE_PARAMETERS)
    select case(trim(dict_key(val)))

    case(EF_INTERPOL_DET)
      cp%foe%ef_interpol_det = val

    ! ADD HERE:
    case(MY_FOE_PARAM)
      cp%foe%my_foe_param = val

    end select
  end select
end subroutine
```

### PSolver

In `psolver/src/PSolver_Main.f90`, find `PS_input_fill`:

```fortran
subroutine PS_input_fill(k, opt, level, val)
  ! ...
  select case(trim(level))
  case(ENVIRONMENT_VARIABLES)
    select case(trim(dict_key(val)))

    ! ADD HERE:
    case('my_solvent_param')
      opt%my_solvent_param = val

    end select
  end select
end subroutine
```

## Step 6: Access in Code

Once the variable is in the derived type, access it wherever the type is available.

### BigDFT

The `input_variables` type is typically passed as `in` or accessible through run objects:

```fortran
subroutine my_new_feature(in, atoms, ...)
  use module_input_keys, only: input_variables
  type(input_variables), intent(in) :: in

  ! Use the variable
  if (my_residual > in%my_threshold) then
    ! not converged yet
  end if
end subroutine
```

In practice, `input_variables` is often accessed through:
- Direct argument passing: `subroutine foo(in, ...)` where `in` is `type(input_variables)`
- Through run objects: `runObj%inputs%my_threshold`
- Through the input dictionary directly (before parsing into struct): `val = dict // 'dft' // 'my_threshold'`

### CheSS

```fortran
subroutine my_chess_routine(cp, ...)
  use chess_base, only: chess_params
  type(chess_params), intent(in) :: cp

  threshold = cp%foe%my_foe_param
end subroutine
```

### PSolver

```fortran
subroutine my_ps_routine(kernel, ...)
  use PStypes, only: coulomb_operator
  type(coulomb_operator), intent(in) :: kernel

  param = kernel%opt%my_solvent_param
end subroutine
```

### Accessing from the Dictionary Directly

Sometimes you need the value before the struct is populated, or in code that only has the dictionary:

```fortran
! BigDFT
if ('my_threshold' .in. (dict // 'dft')) then
  threshold = dict // 'dft' // 'my_threshold'
end if

! CheSS
if ('my_foe_param' .in. (dict // 'foe')) then
  param = dict // 'foe' // 'my_foe_param'
end if

! PSolver
if ('my_solvent_param' .in. (dict // 'environment')) then
  param = dict // 'environment' // 'my_solvent_param'
end if
```

## How It Works Under the Hood

### Build Time: YAML → C

The `import_database.mk` makefile rule converts the YAML file into a C source file containing the entire YAML as a static string:

```makefile
.yaml.c:
	sed -e "s/^/\"/;s/$$/\\\n\"/" $< > $@
	# Wraps in a C function callable from Fortran
```

This generates a function like `get_input_variables_definition()` (BigDFT), `get_chess_input_variables_definition()` (CheSS), or `get_ps_inputvars()` (PSolver).

### Runtime: C → Dictionary

At initialization, the Fortran code calls the C function to get the YAML string, then parses it:

```fortran
! BigDFT (input_keys.f90, input_keys_init)
external :: get_input_variables_definition
call yaml_parse_database(parsed_parameters, get_input_variables_definition)
parameters => parsed_parameters // 0   ! variable definitions
profiles  => parsed_parameters // 1    ! named profiles
```

### Runtime: Validation and Completion

The futile library's `input_file_complete` validates user input against the schema:

```fortran
call input_file_complete(parameters, dict, imports=profiles)
```

This:
- Fills missing values with defaults from the YAML definition
- Validates numeric values against RANGE
- Checks discrete values against EXCLUSIVE
- Evaluates CONDITION rules
- Resolves profile names (e.g., user writes `accurate`, gets the corresponding value)
- Stores metadata (which values were user-provided vs defaults)

### Runtime: Dictionary → Struct

Finally, the populated dictionary is iterated and each key-value pair is assigned to the appropriate struct field via the `select case` dispatch.

## Section Names

### BigDFT Sections

| YAML Section | Fortran Constant | Description |
|-------------|-----------------|-------------|
| `dft` | `DFT_VARIABLES` | Core DFT parameters |
| `kpt` | `KPT_VARIABLES` | K-point sampling |
| `geopt` | `"geopt"` | Geometry optimization |
| `md` | `MD_VARIABLES` | Molecular dynamics |
| `mix` | `MIX_VARIABLES` | SCF mixing |
| `sic` | `SIC_VARIABLES` | Self-interaction correction |
| `tddft` | `TDDFT_VARIABLES` | Linear-response TDDFT |
| `output` | `OUTPUT_VARIABLES` | Output control |
| `perf` | `PERF_VARIABLES` | Performance and linear scaling |
| `mode` | `MODE_VARIABLES` | Calculator backend |
| `lin_general` | `LIN_GENERAL` | Linear scaling general |
| `lin_basis` | `LIN_BASIS` | Linear scaling basis |
| `lin_kernel` | `LIN_KERNEL` | Linear scaling kernel |
| `lin_basis_params` | `LIN_BASIS_PARAMS` | Per-element basis params |

### CheSS Sections

| YAML Section | Fortran Constant | Description |
|-------------|-----------------|-------------|
| `foe` | `FOE_PARAMETERS` | Fermi Operator Expansion |
| `lapack` | `LAPACK_PARAMETERS` | ScaLAPACK settings |
| `ntpoly` | `NTPOLY_PARAMETERS` | NTPoly solver |

### PSolver Sections

| YAML Section | Fortran Constant | Description |
|-------------|-----------------|-------------|
| `kernel` | `KERNEL_VARIABLES` | Coulomb kernel |
| `environment` | `ENVIRONMENT_VARIABLES` | Cavity and solvation |
| `setup` | `SETUP_VARIABLES` | Computational setup |

## Checklist

When adding a new variable, verify all of these:

- [ ] YAML definition with COMMENT and default (and RANGE/EXCLUSIVE if applicable)
- [ ] Key constant in public_keys.f90 (BigDFT) or local module (CheSS/PSolver)
- [ ] Field in the derived type with a doc comment
- [ ] Default value set in the initialization routine (matching YAML default)
- [ ] `select case` entry in the dict→type mapping routine
- [ ] The YAML key name, the Fortran string constant, and the dictionary access all use the **exact same string**
- [ ] If adding to BigDFT: also update PyBigDFT's `InputActions.py` if the variable should have a Python convenience function

## Notes

- The YAML key name is **case-sensitive** and must match exactly between the YAML file, the Fortran string constant, and any Python references.
- Values in the YAML file can use strings like `accurate` or `fast` as profile names. The validation system resolves these to actual values.
- After modifying the YAML file, you must rebuild (the C file is regenerated from YAML at build time).
- The `input_file_complete` function from futile handles all validation -- you don't need to write validation code in the `select case` mapping.
- For CONDITION dependencies: the master variable must be defined *before* the dependent variable in the YAML file.
- For CheSS and PSolver variables accessed from BigDFT: the chess/psolver dictionaries are stored as `in%chess_dict` and `in%PS_dict` in the `input_variables` type, and initialized lazily when those modules are first called.
