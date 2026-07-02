---
name: irene-monitoring-jobs
description: Use when the user asks about status, progress, output, history, queue state, cancellation, or failure analysis for jobs on TGCC Irene.
---

# Monitoring Jobs On Irene

Use `get_job_status` for one job and `get_job_statuses` for several jobs or the
current user's live jobs. The backend reads `ccc_mpp -u $USER` for pending/running
jobs and falls back to `ccc_macct <jobid>` for finished jobs.

For job output, IreneAgent's default scripts write `irene_%I.o` and `irene_%I.e`
in the submission directory unless the JobSpec sets explicit stdout/stderr paths.
Use `fs_tail` or `fs_view` to inspect those files.

Useful live commands through `run_command_on_cluster`:

- `ccc_mpp -u $USER`: compact pending/running job view.
- `ccc_mstat -u`: detailed pending/running job view.
- `ccc_macct <jobid>`: finished-job accounting and step details.
- `ccc_mdel <jobid>`: cancel a job; prefer the `cancel_job` tool.
- `ccc_malter -T <seconds> <jobid>`: reduce a queued/running job time limit; prefer `update_job` with `time_limit`.

Respect TGCC's scheduler-polling guidance: do not repeatedly poll faster than
about one or two aggregate scheduler queries per minute, and do not use `watch`.
