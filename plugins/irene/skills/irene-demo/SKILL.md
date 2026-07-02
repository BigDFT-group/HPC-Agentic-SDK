---
name: irene-demo
description: Interactive demo of IreneAgent: facility info, live status, docs search, filesystem access, and a small CPU job on TGCC Irene.
---

# Irene Demo

Start by saying that Irene is TGCC's CPU-first supercomputer and that normal jobs
run on the large `rome` CPU partition through Bridge commands.

Demo sequence:

1. Call `get_facility`; summarize `rome`, `xlarge`, and V100-family partitions.
2. Call `get_resources`; show current partition status from `ccc_mpinfo`.
3. Call `search_docs("How do I submit a CPU MPI job on Irene?")`; mention BM25 if indicated.
4. Call `fs_ls(".")` to verify filesystem access.
5. If the user agrees to consume a tiny allocation, submit a short CPU job:

```json
{
  "name": "irene-demo",
  "executable": "hostname && echo BRIDGE_MSUB_JOBID=$BRIDGE_MSUB_JOBID",
  "resources": {"process_count": 1},
  "attributes": {"duration": 300, "queue_name": "rome"}
}
```

After completion, inspect `irene_<jobid>.o` or the explicit stdout path if one
was set. Finish by pointing users to `/irene-submitting-jobs`,
`/irene-monitoring-jobs`, and `/irene-reference`.
