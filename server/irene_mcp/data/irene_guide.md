# TGCC Irene

An original, plain-language orientation to the TGCC Irene supercomputer, written
for users who drive it through IreneAgent. It records the site-specific facts that
shape job sizing, storage choices, and scheduler interaction. Live values such as
queue occupancy, exact installed versions, and project consumption should be
queried from the machine.

## What Irene Is

Irene is a CPU-first supercomputer at CEA TGCC. Jobs are scheduled by Slurm, but
users normally interact with the scheduler through TGCC Bridge commands such as
`ccc_msub`, `ccc_mprun`, `ccc_mpp`, `ccc_mstat`, `ccc_mdel`, and `ccc_malter`.

The main production partition is `rome`: 2,286 AMD Rome nodes, each with 128 CPU
cores and about 228 GiB of memory. This partition dominates the machine and is
the right default for normal CPU, MPI, and MPI/OpenMP jobs.

Specialized partitions are available:

- `xlarge`: five large-memory Intel Skylake nodes with 112 cores, about 3 TiB of
  RAM, local disks, and one NVIDIA P100 GPU per node.
- `v100`: 32 GPU nodes with 40 CPU cores and four NVIDIA Tesla V100 GPUs per
  node.
- `v100l`: 30 GPU nodes with 36 CPU cores, one V100 GPU, and more memory per
  GPU.
- `v100xl`: two large-memory GPU nodes with 72 CPU cores, one V100 GPU, and
  about 2.9 TiB of RAM.

The practical default is CPU/MPI first. Use GPU partitions only for codes that
actually offload to NVIDIA GPUs, and use `xlarge` when the bottleneck is memory
within one node.

## Connecting And Interactive Use

SSH access details are site- and project-specific; configure an SSH alias such
as `irene` in `~/.ssh/config`, then set IreneAgent's `ssh.host` to that alias.
Login nodes are shared. They are for editing, compiling modest code, staging
files, checking queues, and submitting jobs. Anything heavier than a personal
computer workload belongs in an allocation.

For interactive work, TGCC documents two common Bridge modes:

- `ccc_mprun -K -p <partition> -n <tasks> -T <seconds> -A <project>` creates an
  allocation while keeping you on the login node. Inside that allocation, launch
  steps with `ccc_mprun`.
- `ccc_mprun -s -p <partition> -c <cores> -m <filesystems>` opens a shell on a
  compute node. This is single-node only and useful for compilation,
  post-processing, and short threaded work.

Remote desktop visualization uses `ccc_visu virtual -p <partition>` or
`ccc_visu console -p <partition>`.

## Submitting Jobs

Batch scripts use `#MSUB` directives and are submitted with `ccc_msub <script>`.
The important directives are:

- `#MSUB -r <name>`: job name.
- `#MSUB -q <partition>`: partition. This is mandatory.
- `#MSUB -A <project>`: project/account charged for the job. This is mandatory.
- `#MSUB -m <filesystems>`: filesystems required by the job, such as
  `scratch,work`, `scratch,store`, or `scratch,work,store`. On Irene this is
  mandatory; without it, compute nodes cannot use scratch, work, or store.
- `#MSUB -n <tasks>`: total parallel tasks.
- `#MSUB -c <cores-per-task>`: CPU cores per task. Use this for OpenMP threads,
  memory per task, or GPU allocation on GPU nodes.
- `#MSUB -N <nodes>`: optional node count. Usually Bridge can infer this from
  the task and core request.
- `#MSUB -x`: exclusive node use.
- `#MSUB -T <seconds>`: wall time. The documented default is 7200 seconds, but
  accurate wall time improves backfill scheduling.
- `#MSUB -Q <qos>`: QoS such as `normal`, `test`, or `long`.

Inside the script, run parallel work with `ccc_mprun ./a.out`. The job
submission directory is available as `${BRIDGE_MSUB_PWD}`. Bridge also sets
variables such as `BRIDGE_MSUB_JOBID`, `BRIDGE_MSUB_MAXTIME`,
`BRIDGE_MSUB_NPROC`, `BRIDGE_MSUB_NCORE`, and `BRIDGE_MSUB_REQNAME`.

A typical MPI job looks like:

```bash
#!/bin/bash
#MSUB -r MyJob_Para
#MSUB -n 32
#MSUB -T 1800
#MSUB -o example_%I.o
#MSUB -e example_%I.e
#MSUB -q rome
#MSUB -A <project>
#MSUB -m scratch,work
set -x
cd ${BRIDGE_MSUB_PWD}
ccc_mprun ./a.out
```

A hybrid MPI/OpenMP job asks for tasks with `-n` and cores per task with `-c`,
then sets `OMP_NUM_THREADS` to match `-c`.

## GPU Jobs

GPU jobs run on `v100`, `v100l`, `v100xl`, or another GPU partition exposed by
`ccc_mpinfo`. TGCC's documented model allocates GPUs indirectly from the number
of CPU cores per task. Use `ccc_mpinfo` and the `CpN` and `GpN` columns: one GPU
corresponds to roughly `CpN / GpN` cores per task on that partition.

For example, on a partition with 128 CPU cores and four GPUs per node:

- `-n 1 -c 32` allocates one GPU to the task.
- `-n 1 -c 64` allocates two GPUs to the task.
- `-n 4 -c 32` allocates four GPUs total.

Load `nvhpc` for NVIDIA compilers and GPU libraries. GPU MPI programs are still
launched with `ccc_mprun`. For topology-aware binding, TGCC documents passing
Slurm options through Bridge, for example `#MSUB -E "--gpu-bind=closest"`.

## Monitoring And Accounting

Use `ccc_mpp -u $USER` or `ccc_mstat -u` to see pending and running jobs. The
TGCC manual asks users to keep scheduler polling low: around one or two aggregate
queries per minute, and it explicitly prohibits using `watch` on scheduler or
Bridge commands.

Use `ccc_macct <jobid>` after a job has finished to inspect accounting, memory,
steps, elapsed time, state, and energy information when available. Use
`ccc_mdel <jobid>` to cancel jobs. Use `ccc_malter -T <seconds> <jobid>` to
reduce the time limit of a queued or running job.

Project consumption is checked with `ccc_myproject`; fair-share status by
project and partition is checked with `ccc_compuse`. Projects should consume
awarded hours regularly. Under-consumption can cause awarded hours to be reduced
for some project types; over-consumption lowers priority and may cause jobs to
run only as bonus jobs.

## Storage

Irene exposes several data spaces through environment variables loaded by the
site modules:

- HOME is NFS, backed up, small, and suited to sources and submission scripts.
  The documented quota is 5 GB per user.
- SCRATCH is fast Lustre for temporary computational data and code output. The
  documented default is 100 TB and two million inodes per group. Files not
  accessed for 60 days are purged, and empty directories older than 30 days are
  removed.
- WORK is Lustre for common source code, binaries, and non-purged working data.
  It is not backed up.
- STORE is Lustre plus HSM for large archived files. Prefer large files or packed
  tar archives; use `ccc_hsm`, `ccc_pack`, and `ccc_unpack` for HSM workflows.
- TMP (`CCCTMPDIR` or `CCFRTMP`) is local zram temporary space, purged after each
  job.
- SHM (`CCCSHMDIR`) is tmpfs, about half of RAM, available during `ccc_msub`
  allocations. TGCC strongly recommends it for small temporary files.

Check quotas with `ccc_quota`. Preview scratch purge candidates with
`ccc_will_purge`. Use `lfs setstripe` for files larger than about 10 GB when
parallel I/O benefits from striping.

## Modules, Compilers, And MPI

The `ccc` module defines global site variables and is mandatory. `datadir/own`
and `dfldatadir/own` define data-space variables such as `CCCSCRATCHDIR`,
`CCCWORKDIR`, and `CCCSTOREDIR`. Shared spaces use `datadir/<space>`,
`dfldatadir/<space>`, and `extenv/<space>`.

The default MPI implementation is loaded in the user environment. TGCC documents
Open MPI and Wi4MPI as supervised/recommended MPI paths, while Intel MPI and
other MPI stacks are provided with best-effort support. Compile MPI programs with
`mpicc`, `mpic++`, `mpif77`, or `mpif90`, and launch them with `ccc_mprun`.

Important software modules include `nvhpc`, `mpi/openmpi`, `mpi/intelmpi`,
`mpi/wi4mpi`, `mkl`, `scalapack`, `fftw3/gnu`, `fftw3/mkl`, Python, Julia,
profilers, debuggers, and visualization tools. Query live versions with
`module avail` or `module help <product>` because installed products change over
time.

## Containers

TGCC uses `pcocc` for containers and virtual machines. OCI images can be built
with Docker or Podman on a workstation, copied to Irene, and imported with:

```bash
pcocc-rs image import docker-archive:my_image.tar my_image
```

Run a local container with `pcocc-rs run my_image -- <cmd>`. In batch jobs, run
containers through Bridge:

```bash
ccc_mprun -C my_image -- <cmd>
```

Custom mounts can be passed through Bridge with `-E '--ctr-mount src=<source>,dst=<target>'`.
Cluster data spaces are mounted by default unless pcocc defaults are disabled.

## Staying Current

The TGCC public documentation used for this guide is dated 2026-04-27. Hardware
facts are relatively stable, but partition availability, quotas, modules, QoS
limits, and project accounting are live operational data. Use IreneAgent tools to
query current `ccc_mpinfo`, `ccc_mqinfo`, `ccc_compuse`, `ccc_myproject`, and
`module avail` output when precision matters.
