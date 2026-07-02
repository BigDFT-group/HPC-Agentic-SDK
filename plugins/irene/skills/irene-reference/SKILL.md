---
name: irene-reference
description: Use when answering questions about TGCC Irene specifics: login, projects, partitions, modules, storage, job submission, Bridge commands, GPU allocation, containers, or policies.
---

# Irene Reference

For Irene-specific details, call `search_docs` first. Use live tools when the
answer depends on current state:

- `get_facility` for static machine facts.
- `get_resources` / `get_resource` for current partition information from `ccc_mpinfo`.
- `run_command_on_cluster("ccc_mqinfo")` for current QoS limits.
- `run_command_on_cluster("ccc_compuse")` and `run_command_on_cluster("ccc_myproject")` for project accounting.
- `run_command_on_cluster("module avail <name>")` for current software versions.

Stable facts:

- Irene is CPU-first. Default to `rome` for normal CPU/MPI work.
- `rome`: 2,286 AMD Rome nodes, 128 cores/node, about 228 GiB/node.
- `xlarge`: five large-memory nodes, about 3 TiB/node, one P100 GPU/node.
- `v100`, `v100l`, and `v100xl`: NVIDIA V100 GPU partitions.
- Jobs use Bridge scripts: `#MSUB` directives plus `ccc_msub`.
- Parallel work is launched with `ccc_mprun`.
- `-q <partition>`, `-A <project>`, and `-m <filesystems>` are mandatory for job submission. Always call `get_projects` and ask the user when the project is not explicitly specified.
- Avoid frequent scheduler polling; do not use `watch` on scheduler commands.
