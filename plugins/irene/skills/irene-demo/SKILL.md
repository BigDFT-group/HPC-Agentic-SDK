---
name: irene-demo
description: Interactive demo of the irene plugin — walks through facility info, live cluster status, docs search, filesystem access, and job submission on TGCC Irene. User-invocable with /irene-demo.
user-invocable: true
---

# Irene Demo

Run each step in order — actually call the tools, don't just describe the
plan. Present results as a readable narrative, not raw JSON dumps. Pause
after each step and show the output before moving on.

---

## Step 1 — Facility overview

Call `get_facility`. Present the key facts as a short table: `rome`/`rome-long`
(CPU, the default), `xlarge` (large-memory), and the V100-family GPU
partitions. Lead with one sentence: **"Irene at TGCC (CEA) is a CPU-first
supercomputer — normal jobs run on the `rome` partition through Bridge
commands, not raw Slurm."**

---

## Step 2 — Live cluster status

Call `get_resources`. Show current partition status from `ccc_mpinfo` as a
short table or utilization bar per partition. Point out which partitions have
idle capacity right now.

---

## Step 3 — Documentation search

Call `search_docs` with *"How do I submit a CPU MPI job on Irene?"*. Show the
top result's breadcrumb and a short excerpt, and note whether it came from
vector search or BM25 keyword fallback.

---

## Step 4 — Filesystem

Call `fs_ls(".")` to verify filesystem access and show the listing cleanly.
Highlight anything interesting, e.g. job scripts under `agent/jobs/`.

---

## Step 5 — Recent jobs

Call `get_job_statuses([])` (empty list = the current user's recent jobs, via
`ccc_mpp`/`ccc_macct`). If there are jobs, show them as a table: job ID | name
| state | partition | elapsed. If there are none, say so and move on.

---

## Step 6 — Test job

If the user agrees to consume a tiny allocation: call `get_projects` and ask
which project to charge if they haven't already specified one — never guess
or invent a project name. Tell the user you'll submit a quick test job, then
call `submit_job`:

```json
{
  "name": "irene-demo",
  "executable": "hostname && echo BRIDGE_MSUB_JOBID=$BRIDGE_MSUB_JOBID",
  "resources": {"process_count": 1},
  "attributes": {"duration": 300, "queue_name": "rome", "account": "<selected-project>"}
}
```

Show the returned job ID and script path. Then call `get_job_status(<job_id>)`
immediately and report the initial state.

If the user doesn't want to consume an allocation, skip this step and say so.

---

## Step 7 — Monitor and read output

Poll `get_job_status` every ~15 seconds (use `run_command_on_cluster("sleep
15")` as the wait). Stop when the state is `completed` or `failed` (or after
~5 polls — tell the user to check back themselves if it's still queued).

Once completed, inspect `irene_<jobid>.o` (or the explicit stdout path if one
was set) with `fs_tail` or `fs_view` and show the output.

---

## Closing

Summarize what just happened in bullet points: facility and live status
checked, docs searched, filesystem verified, recent jobs checked, a CPU job
submitted and its output retrieved (if run).

Then say: *"From here you can submit real workloads with
/irene-submitting-jobs, monitor them with /irene-monitoring-jobs, or ask
anything about the cluster via /irene-reference."*
