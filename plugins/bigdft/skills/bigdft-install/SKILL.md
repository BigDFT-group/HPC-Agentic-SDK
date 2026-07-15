---
name: bigdft-install
description: Guide installation of BigDFT from source. Determines the user's platform, compilers, and libraries, then generates an rcfile and walks through the build. Use when the user wants to compile or install BigDFT.
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# BigDFT Installation

Help the user build BigDFT from source using the `Installer.py` wrapper around jhbuild. **Ask each question one at a time.** Auto-detect what you can by running shell commands before asking the user.

## Pre-flight: Gather System Information

Before asking any questions, silently run these commands and record the results:

```bash
ls ./Installer.py ../Installer.py ../bigdft-suite/Installer.py ./bigdft-suite/Installer.py ~/bigdft-suite/Installer.py 2>/dev/null  # find source
pwd                  # current directory
uname -s -m          # OS and architecture
hostname             # for matching existing rcfiles
which mpifort mpif90 mpicc gfortran gcc ifort ifx icx 2>/dev/null
mpifort --version 2>/dev/null || mpif90 --version 2>/dev/null
gfortran --version 2>/dev/null
gcc --version 2>/dev/null
ifort --version 2>/dev/null || ifx --version 2>/dev/null
python3 --version 2>/dev/null
pkg-config --libs lapack blas 2>/dev/null
echo $MKLROOT
ls /opt/homebrew/opt/openblas 2>/dev/null   # macOS Homebrew
ls /usr/lib/x86_64-linux-gnu/liblapack* 2>/dev/null  # Debian/Ubuntu
```

Fill in this checklist (do not show it to the user):

```
Platform:        ___  (linux-x86_64 / linux-aarch64 / darwin-arm64 / darwin-x86_64)
Hostname:        ___
Fortran MPI:     ___  (mpifort / mpif90 / mpiifort / ftn / none)
Fortran serial:  ___  (gfortran / ifort / ifx / frt / none)
C compiler:      ___  (gcc / icc / icx / clang / fcc / none)
C++ compiler:    ___  (g++ / icpc / icpx / clang++ / FCC / none)
GCC version:     ___  (needed to decide -fallow-argument-mismatch)
BLAS/LAPACK:     ___  (mkl / openblas / accelerate / system / none)
MKLROOT:         ___  (path or empty)
Python 3:        ___  (version or none)
CUDA available:  ___  (yes / no; check nvcc or nvidia-smi)
OpenCL avail:    ___  (yes / no)
```

## Questions

### 1 -- Source location

Before asking, check whether the current working directory (or a nearby directory) already contains `Installer.py`. Also check common locations like `../bigdft-suite`, `./bigdft-suite`, and `$HOME/bigdft-suite`. If you find it, confirm with the user rather than asking from scratch:

```
I see bigdft-suite at <path>. Is that the one you want to build?
```

Only if nothing is found, ask:

```
Where is the bigdft-suite source directory?
(e.g. ~/bigdft-suite or /opt/bigdft-suite)
```

Verify the path exists and contains `Installer.py`.

### 2 -- Build directory

```
Where should I create the build directory?
Default: a "build" directory next to the source.
```

The build directory **must** be separate from the source. Create it if it doesn't exist.

### 3 -- Compilers and MPI

If auto-detection found compilers, confirm with the user:

```
I detected:
  Fortran MPI compiler: <detected>
  C compiler: <detected>
  C++ compiler: <detected>

Are these correct, or would you like to use different compilers?
```

If nothing was detected, ask explicitly:

```
Which compilers should I use?
  - Fortran MPI compiler (e.g. mpifort, mpiifort, ftn)
  - C compiler (e.g. gcc, icc, icx, clang)
  - C++ compiler (e.g. g++, icpc, icpx, clang++)
```

### 4 -- BLAS/LAPACK

If auto-detection found a library, confirm. Otherwise ask:

```
Which BLAS/LAPACK implementation should I link against?
  1. Intel MKL (set MKLROOT if not already)
  2. OpenBLAS (-lopenblas)
  3. Apple Accelerate (-framework Accelerate)  [macOS only]
  4. System LAPACK (-llapack -lblas)
  5. Custom (provide linker flags)
```

### 5 -- Anything beyond the default?

By default, build `bigdft` with standard optimization (`-O2`). Do **not** ask about modules, optimization flags, or optional features unless the user brings them up. Instead, ask a single open-ended question:

```
I'll build bigdft with -O2 optimization. Any custom requirements?
(e.g. also build spred, enable GPU support, debug flags, etc.)
```

If they say no, proceed with defaults. If they mention specifics, handle accordingly:

- **Modules**: default is `['bigdft']`. Other options: `['spred']` (full suite), `['chess']` (CheSS only), or any subset of: futile, atlab, chess, liborbs, psolver, bigdft, spred, PyBigDFT, bigdft-client.
- **GPU**: add CUDA (`--enable-cuda-gpu`) and/or OpenCL (`--enable-opencl`) flags. Only mention if hardware was detected in pre-flight.
- **Optimization**: `-O2` is default. `-O3` for aggressive, `-O0 -g -fbounds-check -fbacktrace` for debug.
- **Optional features**: Python bindings (`conditions.add("python")`), testing (`conditions.add("testing")`), dynamic libraries (`--enable-dynamic-libraries`).

For GCC >= 10, always add `-fallow-argument-mismatch` to FCFLAGS regardless of what the user asks for.

## rcfile Generation

After collecting answers, generate a configuration file. Write it to `<build-dir>/custom.rc`.

### rcfile Template

```python
# BigDFT configuration file
# Generated for: FILL (hostname / platform)
# Date: FILL

import os

# Modules to build
modules = FILL  # e.g. ['bigdft'] or ['spred']
moduleset = 'suite'

# Skip system-provided packages
skip = FILL  # e.g. ["PyYAML", "libyaml"]

# Conditions -- leave ALL commented out unless the user explicitly requests them
# conditions.add("testing")     # only if user wants to run tests
# conditions.add("python")      # only if user explicitly asks for Python/PyGObject bindings
# conditions.add("no_upstream") # only if user wants to skip upstream dependencies

def env_configuration():
    '''Configure compilers and flags for autotools packages.'''
    conf = {}
    conf["FC"] = "FILL"        # e.g. "mpifort"
    conf["CC"] = "FILL"        # e.g. "gcc"
    conf["CXX"] = "FILL"       # e.g. "g++"
    conf["FCFLAGS"] = "FILL"   # e.g. "-O2 -fopenmp"
    conf["CFLAGS"] = "FILL"    # e.g. "-O2"
    conf["CXXFLAGS"] = "FILL"  # e.g. "-O2 -std=c++11"
    # FILL: BLAS/LAPACK linking
    conf["--with-ext-linalg"] = "FILL"
    return " ".join(['"' + k + '=' + v + '"' for k, v in conf.items()])

autogenargs = env_configuration()

# Module-specific overrides
module_autogenargs = {}
module_cmakeargs = {}
module_makeargs = {}

# FILL: Add module-specific settings if needed
# Example: module_autogenargs['bigdft'] = env_configuration() + ' --with-gobject=yes'
# Example: module_cmakeargs['ntpoly'] = '-DCMAKE_Fortran_COMPILER=FILL ...'
```

### BLAS/LAPACK Reference Configurations

Use the appropriate linking line based on the user's choice:

**Intel MKL (GNU compilers):**
```python
mkl = os.environ["MKLROOT"] + "/lib/intel64"
conf["FCFLAGS"] = "-I" + os.environ["MKLROOT"] + "/include -O2 -fopenmp"
conf["--with-ext-linalg"] = (
    "-L" + mkl + " -Wl,--start-group "
    "-lmkl_gf_lp64 -lmkl_gnu_thread -lmkl_core "
    "-Wl,--end-group -lgomp -lpthread -lm -ldl"
)
```

**Intel MKL (Intel compilers):**
```python
mkl = os.environ["MKLROOT"] + "/lib/intel64"
conf["FCFLAGS"] = "-I" + os.environ["MKLROOT"] + "/include -O2 -qopenmp"
conf["--with-ext-linalg"] = (
    "-L" + mkl + " "
    "-lmkl_intel_lp64 -lmkl_intel_thread -lmkl_core "
    "-liomp5 -lpthread -lm -ldl"
)
```

**Intel MKL with ScaLAPACK (Intel compilers + Intel MPI):**
```python
mkl = os.environ["MKLROOT"] + "/lib/intel64"
conf["--with-ext-linalg"] = (
    "-L" + mkl + " "
    "-lmkl_scalapack_lp64 -lmkl_intel_lp64 -lmkl_intel_thread -lmkl_core "
    "-lmkl_blacs_intelmpi_lp64 -liomp5 -lpthread -lm -ldl"
)
```

**OpenBLAS:**
```python
conf["--with-ext-linalg"] = "-lopenblas"
# or with explicit path:
conf["--with-ext-linalg"] = "-L/path/to/openblas/lib -lopenblas"
```

**Apple Accelerate (macOS):**
```python
conf["--with-ext-linalg"] = "-framework Accelerate"
```

**System LAPACK/BLAS:**
```python
conf["--with-ext-linalg"] = "-llapack -lblas"
```

### Compiler Flag Reference

**GCC (gfortran):**
```
FCFLAGS: -O2 -fopenmp -fPIC
         -fallow-argument-mismatch  (GCC >= 10, required)
CFLAGS:  -O2 -fPIC
LIBS:    -lstdc++  (sometimes needed)
```

**Intel classic (ifort/icc):**
```
FCFLAGS: -O2 -qopenmp -fPIC
CFLAGS:  -O2 -fPIC
```

**Intel oneAPI (ifx/icx):**
```
FCFLAGS: -O2 -qopenmp -fPIC
CFLAGS:  -O2 -fPIC
CXXFLAGS: -O2 -std=c++11
```

**Cray wrappers (ftn/cc):**
```
FC=ftn  (no explicit MPI flags needed)
BLAS/LAPACK: --with-blas=no --with-lapack=no  (Cray libsci is automatic)
```

**Fujitsu (frt/fcc on Fugaku):**
```
FC=mpifrt or mpifrtpx (cross-compile)
FCFLAGS: -SSL2BLAMP -Kfast,openmp,noautoobjstack
LIBS: -SSL2BLAMP -Kfast,openmp -Nlibomp --linkstl=libfjc++
--with-ext-linalg: -fjlapackex
```

**macOS with Clang + gfortran:**
```
FC=mpifort  CC=clang  CXX=clang++
FCFLAGS: -O2 -fopenmp -mtune=native
CFLAGS: -O2 -std=c99 -Wno-error=implicit-function-declaration
LIBS: -lc++
```

### GPU Configuration

**CUDA:**
```python
# Add to autogenargs:
conf["--enable-cuda-gpu"] = ""
conf["--with-cuda-path"] = "/usr/local/cuda"  # or $CUDA_HOME
conf["NVCC_FLAGS"] = "--compiler-options -fPIC"
# For specific architecture:
conf["NVCC_FLAGS"] = "-arch sm_80 -O3 --compiler-options -fPIC"
```

**OpenCL:**
```python
conf["--enable-opencl"] = ""
conf["--with-ocl-path"] = "/usr/local/cuda"  # NVIDIA OpenCL
# or for Intel:
conf["--with-ocl-path"] = "/opt/intel/oneapi/..."
```

**SYCL (Intel oneAPI):**
```python
conf["FCFLAGS"] += " -fsycl -fsycl-device-code-split=per_kernel"
conf["CXXFLAGS"] = "-O2 -fsycl -fsycl-device-code-split=per_kernel -fPIC"
# Add to linalg: -lmkl_sycl
```

### NTPoly Configuration

NTPoly uses CMake and often needs special handling:

```python
module_cmakeargs['ntpoly'] = (
    "-DCMAKE_Fortran_COMPILER=FILL "      # e.g. mpifort
    "-DCMAKE_C_COMPILER=FILL "            # e.g. gcc
    "-DCMAKE_CXX_COMPILER=FILL "          # e.g. g++
    "-DCMAKE_Fortran_FLAGS_RELEASE='-O2 -fopenmp -fPIC' "
    "-DBUILD_SHARED_LIBS=ON "
    "-DFORTRAN_ONLY=NO"
)
```

For Fujitsu compilers, add: `-DCMAKE_Fortran_MODDIR_FLAG=-M`

### Packages to Skip

Common packages to skip when already system-installed:

```python
# Conda environment
skip = ["spglib", "PyYAML", "libyaml", "ntpoly", "libxc"]

# HPC with module system (common)
skip = ["PyYAML", "libyaml"]

# Minimal build
skip = ["ntpoly"]
```

## Build Execution

After writing the rcfile, determine whether the source is a git checkout or a tarball. If the source directory contains a `.git` directory (or the individual packages like `futile/`, `bigdft/` contain `autogen.sh` but no `configure`), it is a developer build from git and needs autogen first.

**For git checkouts (developer builds):**
```bash
cd FILL  # build directory
FILL/Installer.py autogen -y
FILL/Installer.py build -f FILL/custom.rc -y
```

**For tarballs:**
```bash
cd FILL  # build directory
FILL/Installer.py build -f FILL/custom.rc -y
```

The `-y` flag auto-answers yes to prompts.

Tell the user:
- The build log is in `<build-dir>/_jhbuild/logs/` if something fails
- Build parallelism is auto-detected (CPU count + 1)
- After a successful build, source the environment: `source <build-dir>/install/bin/bigdftvars.sh`

## Troubleshooting

If the build fails, check the error and suggest fixes:

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `Type mismatch` in Fortran | GCC >= 10 strictness | Add `-fallow-argument-mismatch` to FCFLAGS |
| `cannot find -llapack` | Missing LAPACK | Install or fix `--with-ext-linalg` path |
| `No rule to make target` | Stale build | Run `Installer.py clean` then rebuild |
| `libyaml.so not found` at runtime | Missing LD_LIBRARY_PATH | `export LD_LIBRARY_PATH=<build>/install/lib:$LD_LIBRARY_PATH` |
| `MPI_Init` errors | Wrong compiler wrapper | Ensure FC is an MPI wrapper (mpifort, not gfortran) |
| `configure: error: cannot run test program` | Cross-compilation mismatch | Add `--build=` and `--host=` flags |
| Build in source dir error | Must use separate build dir | Create and cd to a separate build directory |
| `autogen.sh: not found` | Developer build needs autogen | Run `Installer.py autogen` first |

## Installer.py Action Reference

After the initial build, the user may need these:

| Command | Purpose |
|---------|---------|
| `Installer.py build -f custom.rc` | Full build with dependencies |
| `Installer.py make` | Recompile without reconfigure (fast) |
| `Installer.py clean` | Clean all build artifacts |
| `Installer.py buildone <module>` | Build a single module |
| `Installer.py cleanone <module>` | Clean a single module |
| `Installer.py check` | Run test suite |
| `Installer.py autogen` | Regenerate configure scripts (developers) |
| `Installer.py dry_run` | Show build order (generates buildprocedure.png) |
| `Installer.py link` | Show linker flags for external codes |

Available modules: `futile`, `atlab`, `chess`, `liborbs`, `psolver`, `bigdft`, `PyBigDFT`, `spred`, `bigdft-client`.

## Existing rcfile Reference

If the user is on a known HPC system, suggest using an existing rcfile from the source tree instead of generating one. Known systems:

| System | rcfile | Compilers | Notes |
|--------|--------|-----------|-------|
| **macOS (Clang)** | `rcfiles/macos_clang.rc` | clang + gfortran | Accelerate framework |
| **macOS (GCC/Homebrew)** | `rcfiles/macos_gcc.rc` | Homebrew gcc + gfortran | Auto-detects GCC version |
| **Ubuntu/Debian** | `rcfiles/ubuntu_MPI.rc` | gcc + mpifort | OpenBLAS, debug flags |
| **Ubuntu OpenCL** | `rcfiles/ubuntu_OCL.rc` | gcc + mpif90 | OpenCL + OpenMP |
| **Ubuntu OpenMP only** | `rcfiles/ubuntu_OMP.rc` | gfortran (no MPI) | Minimal, serial+OpenMP |
| **Conda** | `rcfiles/conda.rc` | conda compilers | Skips conda packages |
| **Container** | `rcfiles/container.rc` | gcc + mpif90 | CUDA + OpenCL |
| **Container + MKL** | `rcfiles/container_mkl.rc` | gcc + mpif90 | MKL + CUDA |
| **ARCHER2** | `rcfiles/archer2.rc` | Cray ftn (GNU) | MKL, Cray wrappers |
| **Fugaku (native)** | `rcfiles/fugaku_node.rc` | Fujitsu frt | ARM A64FX |
| **Fugaku (cross)** | `rcfiles/fugaku_cross.rc` | Fujitsu frtpx | Cross-compile for A64FX |
| **IRENE (GNU)** | `rcfiles/irene-gnu.rc` | gcc + mpif90 | CEA, MKL |
| **IRENE (Intel)** | `rcfiles/irene.rc` | Intel + mpif90 | CEA, MKL + ScaLAPACK |
| **Leonardo** | `rcfiles/leonardo.rc` | gcc + mpif90 | A100 GPUs, CUDA + OpenCL |
| **Hokusai** | `rcfiles/hokusai.rc` | Intel + mpiifort | RIKEN, MKL |
| **Topaze** | `rcfiles/topaze.rc` | Intel + mpif90 | CUDA + OpenCL, bio support |
| **Vega (FOSS)** | `rcfiles/vega-foss-cuda.rc` | gcc + mpif90 | MKL + CUDA |
| **Vega (Intel)** | `rcfiles/vega-intel.rc` | Intel + mpif90 | MKL |
| **Adastra** | `rcfiles/adastra.rc` | Intel oneAPI (ifx) | AMD GPU, SYCL |
| **Manneback** | `rcfiles/mann_gnu.rc` | gcc (EasyBuild) | UCLouvain, MKL |

If a match is found, suggest:
```bash
cd <build-dir>
<src-dir>/Installer.py build -f <src-dir>/rcfiles/<match>.rc
```

## Notes

- Never build inside the source directory. Always create a separate build directory.
- The `buildrc` file is auto-generated in the build directory after the first build and can be reused for subsequent builds.
- After a successful build, a `Makefile` is generated in the build directory with convenience targets (`make build`, `make clean`, `make check`).
- For developer builds (from git, not tarball), run `Installer.py autogen` before the first build.
- `source install/bin/bigdftvars.sh` sets up PATH, LD_LIBRARY_PATH, PYTHONPATH, and PKG_CONFIG_PATH.
- The build system auto-detects CPU count and uses `jobs = cpu_count + 1` for parallel make.
- Conditions control optional features: `testing`, `python`, `no_upstream`, `bio`, `ase`, `vdw`, `sirius`, `sycl`, `dill`, `boost`, `spg`, `amber`, `devdoc`, `simulation`.
