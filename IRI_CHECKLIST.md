# IRI Facility API Coverage Checklist

Tracks how far `irene-hpc` covers the IRI Facility API shape. Irene has no REST
facility API; tools execute TGCC Bridge and filesystem commands over SSH.

Legend: implemented, planned, deferred.

## Facility

| IRI endpoint | Tool | Status | Notes |
|---|---|---|---|
| GET /facility | `get_facility` | implemented | Static data from `data/irene_config.json` |

## Status

| IRI endpoint | Tool | Status | Notes |
|---|---|---|---|
| GET /status/resources | `get_resources` | implemented | `ccc_mpinfo` partition summary |
| GET /status/resources/{resource_id} | `get_resource` | implemented | Same, with raw `ccc_mpinfo` included for detail |
| incidents/events | — | deferred | No public incident feed in the packaged docs |

## Account

| IRI endpoint | Tool | Status | Notes |
|---|---|---|---|
| GET /account/projects | `get_projects` | implemented | Parses `ccc_compuse`; falls back to raw `ccc_myproject` |
| GET /account/projects/{id} | `get_project` | implemented | Filters `get_projects` |
| allocations | — | planned | `ccc_myproject` exposes accounting but needs a robust parser |

## Compute

| IRI endpoint | Tool | Status | Notes |
|---|---|---|---|
| POST /compute/job/{resource_id} | `submit_job` | implemented | JobSpec to Bridge `#MSUB` script under `~/.irene/jobs`, submitted by `ccc_msub` |
| PUT /compute/job/{rid}/{job_id} | `update_job` | partial | Time-limit reduction through `ccc_malter -T`; other fields rejected |
| GET /compute/status/{rid}/{job_id} | `get_job_status` | implemented | `ccc_mpp`; finished-job fallback via `ccc_macct` |
| POST /compute/status/{rid} | `get_job_statuses` | implemented | Batch lookup; empty list returns live current-user jobs |
| DELETE /compute/cancel/{rid}/{job_id} | `cancel_job` | implemented | `ccc_mdel` |

## Filesystem

Filesystem tools are implemented using the shared agent pattern and implemented over
shell commands plus remotemanager transfer: `fs_ls`, `fs_stat`, `fs_view`,
`fs_head`, `fs_tail`, `fs_mkdir`, `fs_upload`, `fs_download`, `fs_checksum`,
`fs_cp`, `fs_mv`, `fs_chmod`, `fs_chown`, `fs_symlink`, `fs_compress`, and
`fs_extract`. `rm` is intentionally omitted as a destructive tool.

## Known Deviations

- `submit_job` returns `{job_id, script_path}` directly instead of an async task.
- `fs_upload` and `fs_download` use local file paths and rsync/scp rather than routing file bytes through MCP payloads.
- Irene GPU requests are represented as partition plus cores-per-task because TGCC documents GPU allocation through `CpN/GpN` core reservations.
- `update_job` only supports time-limit reduction, matching `ccc_malter`.
