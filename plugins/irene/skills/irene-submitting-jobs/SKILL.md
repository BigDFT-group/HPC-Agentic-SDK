---
name: irene-submitting-jobs
description: Use when the user wants to run, submit, or launch a job on TGCC Irene, including MPI, OpenMP, GPU, container, or interactive workflows.
---

# Submitting Jobs On Irene

Default to a CPU/MPI job on `rome` unless the user clearly needs GPUs or large
single-node memory.

Build JobSpecs around Bridge concepts:

- `attributes.queue_name`: `rome`, `xlarge`, `v100`, `v100l`, `v100l-os`, or `v100xl`.
- `attributes.account`: TGCC project for `-A`; falls back to config.
- `attributes.custom_attributes.filesystems`: optional override for Bridge `-m`.
- `resources.process_count`: total tasks for `-n`.
- `resources.cpu_cores_per_process`: cores per task for `-c`.
- `attributes.duration`: seconds or `HH:MM:SS`; rendered as seconds for `-T`.
- `launcher`: usually `ccc_mprun` for MPI or threaded work. The backend supplies it automatically for multi-task jobs.

Typical MPI JobSpec:

```json
{
  "name": "irene-mpi",
  "executable": "./a.out",
  "launcher": "ccc_mprun",
  "resources": {"process_count": 32},
  "attributes": {"queue_name": "rome", "duration": 1800, "account": "gen12345"}
}
```

Typical hybrid MPI/OpenMP JobSpec:

```json
{
  "name": "irene-hybrid",
  "executable": "./a.out",
  "launcher": "ccc_mprun",
  "environment": {"OMP_NUM_THREADS": "4"},
  "resources": {"process_count": 8, "cpu_cores_per_process": 4},
  "attributes": {"queue_name": "rome", "duration": 1800, "account": "gen12345"}
}
```

For GPU partitions, set `queue_name` to a GPU partition and reserve enough cores
per task. On a 4-GPU node, one GPU normally corresponds to `CpN/GpN` cores per
task; check `ccc_mpinfo` for the current `CpN` and `GpN` values.

For containers, use `container.image` with a pcocc image name. The backend emits
`ccc_mprun -C <image> -- <cmd>`.
