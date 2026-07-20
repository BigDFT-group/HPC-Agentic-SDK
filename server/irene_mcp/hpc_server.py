"""MCP server for TGCC Irene, modeled on the IRI Facility API.

Tool groups mirror the IRI resource groups (facility, status, compute,
filesystem); each operation is executed on the Irene front-end node over SSH
via hpc_agent_core.middleware, since Irene does not expose a REST facility
API itself. Coverage of the full API is tracked in IRI_CHECKLIST.md at the
repo root.
"""
import shlex
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from hpc_agent_core.middleware import download_file, quote_path, run_command, upload_file
from hpc_agent_core.models import CompressionType, Job, JobSpec
from hpc_agent_core.serving import serve
from irene_mcp import compute, config

mcp = FastMCP("irene-hpc")

RESOURCE_ID = "irene"


def _check_resource(resource_id: str) -> None:
    if resource_id != RESOURCE_ID:
        raise ValueError(f"Unknown resource '{resource_id}'; this server manages '{RESOURCE_ID}'")


# === facility ================================================================

@mcp.tool()
def get_facility() -> dict:
    """Describe the Irene facility: subsystems, partitions, modules, storage, conventions.

    Static reference data (no SSH round-trip). Irene is a CPU-first system; the
    Rome partition carries the bulk of the work; xlarge and V100 partitions are specialized. (IRI: GET /facility)
    """
    return config.load_cluster_config()


# === status ==================================================================

@mcp.tool()
def get_resources() -> list[dict]:
    """List compute resources and their live state. (IRI: GET /status/resources)

    Returns the Irene resource with a per-partition node-state summary
    (allocated/idle/other/total) from ccc_mpinfo.
    """
    return [_resource_detail()]


@mcp.tool()
def get_resource(resource_id: str = RESOURCE_ID) -> dict:
    """Get detailed state for a single resource. (IRI: GET /status/resources/{resource_id})

    Includes per-partition node counts and any drained/draining nodes with
    their reasons (from ccc_mpinfo).
    """
    _check_resource(resource_id)
    return _resource_detail(include_drain=True)


def _resource_detail(include_drain: bool = False) -> dict:
    output = run_command("ccc_mpinfo")
    partitions = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 14 or parts[0].lower() in {"partition", "-------------------"}:
            continue
        name = parts[0]
        if name.startswith("-") or not parts[2].isdigit():
            continue
        try:
            partitions.append({
                "partition": name,
                "available": parts[1],
                "cores": {"total": int(parts[2]), "down": int(parts[3]), "used": int(parts[4]), "free": int(parts[5])},
                "nodes": {"total": int(parts[8]), "down": int(parts[9]), "used": int(parts[10]), "free": int(parts[11])},
                "memory_per_core_mb": int(parts[6]),
                "cores_per_node": int(parts[12]),
                "sockets_per_node": int(parts[13]) if len(parts) > 13 and parts[13].isdigit() else None,
                "gpus_per_node": int(parts[16]) if len(parts) > 16 and parts[16].isdigit() else 0,
                "gpu_type": " ".join(parts[17:]) if len(parts) > 17 else None,
            })
        except (ValueError, IndexError):
            continue
    resource: dict = {
        "id": RESOURCE_ID,
        "type": "compute",
        "description": "TGCC Irene (CPU-first AMD Rome system with V100 GPU and xlarge large-memory partitions)",
        "partitions": partitions,
    }
    if include_drain:
        resource["raw_ccc_mpinfo"] = output
    return resource


# === account =================================================================

def _parse_projects(output: str) -> list[dict]:
    projects = []
    seen = set()
    for line in output.splitlines():
        parts = line.split()
        if not parts:
            continue
        token = parts[0]
        if "@" in token and not token.lower().startswith("account"):
            project, partition = token.split("@", 1)
            key = (project, partition)
            if key in seen:
                continue
            seen.add(key)
            projects.append({
                "id": project,
                "partition": partition,
                "account": token,
                "status": " ".join(parts[1:]) if len(parts) > 1 else None,
            })
        elif len(parts) >= 3 and parts[0].lower() == "account" and parts[1].lower() == "status":
            continue
    return projects


@mcp.tool()
def get_projects() -> list[dict]:
    """List projects (Bridge/Slurm accounts) the current user belongs to.
    (IRI: GET /account/projects)

    Each project has an id (account name) used in JobAttributes.account.
    """
    output = compute._run_optional("ccc_compuse")
    projects = _parse_projects(output)
    if projects:
        return projects
    return [{"raw": compute._run_optional("ccc_myproject")}]


@mcp.tool()
def get_project(project_id: str) -> dict:
    """Get details for a single project (Bridge/Slurm account).
    (IRI: GET /account/projects/{id})
    """
    projects = get_projects()
    for p in projects:
        if p.get("id") == project_id:
            return p
    raise ValueError(f"Project '{project_id}' not found for current user")


# === compute =================================================================

@mcp.tool()
def submit_job(spec: JobSpec, resource_id: str = RESOURCE_ID) -> dict:
    """Submit a job described by a JobSpec. (IRI: POST /compute/job/{resource_id})

    The spec is rendered as a Bridge #MSUB script (kept under ~/agent/jobs/ on
    the cluster for auditability) and submitted. Returns the job_id and the
    script path. Irene notes: attributes.queue_name picks the partition
    (rome for CPU work, xlarge for large-memory work, v100/v100l/v100xl for GPU work); attributes.account
    (a TGCC project ID) must be explicitly supplied and is checked against
    get_projects/ccc_compuse before submission; describe CPU work with resources.processes_per_node (MPI ranks)
    and cpu_cores_per_process (threads); executable may be a shell line such as
    'module load mpi/openmpi && ccc_mprun ./a.out'. Show the user the spec (or
    the rendered script) before submitting, unless they asked to just run it.
    """
    _check_resource(resource_id)
    return compute.submit(spec)


@mcp.tool()
def get_job_status(job_id: str, resource_id: str = RESOURCE_ID) -> Job:
    """Get the normalized status of one job. (IRI: GET /compute/status/...)

    state is the normalized IRI state (QUEUED/ACTIVE/COMPLETED/FAILED/
    CANCELED); native_state is Bridge/Slurm's. For queued jobs, reason explains
    the wait. Job stdout defaults to <workdir>/irene_<job_id>.o — read it
    with fs_tail or fs_view.
    """
    _check_resource(resource_id)
    jobs = compute.get_statuses([job_id])
    if not jobs:
        raise ValueError(f"Job {job_id} not found")
    return jobs[0]


@mcp.tool()
def get_job_statuses(job_ids: list[str], resource_id: str = RESOURCE_ID) -> list[Job]:
    """Get statuses for several jobs at once, or recent jobs when job_ids is
    empty. (IRI: POST /compute/status/{resource_id})
    """
    _check_resource(resource_id)
    if job_ids:
        return compute.get_statuses(job_ids)
    # No IDs given: current user's live (queued/running) jobs — Bridge has no
    # date-range accounting query, so this is the live queue, not history.
    return compute.get_recent_statuses()


@mcp.tool()
def update_job(
    job_id: str,
    time_limit: str | None = None,
    name: str | None = None,
    partition: str | None = None,
    account: str | None = None,
    reservation: str | None = None,
    resource_id: str = RESOURCE_ID,
) -> Job:
    """Update a queued or running job. (IRI: PUT /compute/job/{resource_id}/{job_id})

    All fields are optional — only supplied ones are changed.
    time_limit: new wall time as HH:MM:SS or D-HH:MM:SS (works on running jobs too).
    partition, account, reservation: only valid while the job is still queued.
    """
    _check_resource(resource_id)
    unsupported = {"name": name, "partition": partition, "account": account, "reservation": reservation}
    requested = [key for key, value in unsupported.items() if value is not None]
    if requested:
        raise ValueError("Irene Bridge update currently supports time_limit only; unsupported fields: " + ", ".join(requested))
    if not time_limit:
        raise ValueError("No fields to update — supply time_limit")
    run_command(f"ccc_malter -T {compute.duration_to_seconds(time_limit)} {shlex.quote(job_id)}")
    jobs = compute.get_statuses([job_id])
    if not jobs:
        raise ValueError(f"Job {job_id} not found after update")
    return jobs[0]


@mcp.tool()
def cancel_job(job_id: str, resource_id: str = RESOURCE_ID) -> Job | str:
    """Cancel a queued or running job and report its resulting state.
    (IRI: DELETE /compute/cancel/{resource_id}/{job_id})
    """
    _check_resource(resource_id)
    return compute.cancel(job_id)


# === filesystem ==============================================================
# Paths are relative to the home directory unless absolute.

@mcp.tool()
def fs_ls(path: str = ".", show_hidden: bool = False) -> str:
    """List a directory on the cluster. (IRI: GET /filesystem/ls)"""
    flags = "-la" if show_hidden else "-l"
    return run_command(f"ls {flags} {quote_path(path)}")


@mcp.tool()
def fs_stat(path: str) -> str:
    """Stat a file or directory on the cluster. (IRI: GET /filesystem/stat)"""
    return run_command(f"stat {quote_path(path)}")


@mcp.tool()
def fs_view(path: str) -> str:
    """Read a whole text file on the cluster (output capped at 200KB).
    (IRI: GET /filesystem/view) For large files use fs_head/fs_tail.
    """
    return run_command(f"cat {quote_path(path)}")


@mcp.tool()
def fs_head(path: str, lines: int = 50) -> str:
    """Read the first lines of a file on the cluster. (IRI: GET /filesystem/head)"""
    return run_command(f"head -n {int(lines)} {quote_path(path)}")


@mcp.tool()
def fs_tail(path: str, lines: int = 50) -> str:
    """Read the last lines of a file on the cluster — e.g. a job's
    irene_<job_id>.o. (IRI: GET /filesystem/tail)
    """
    return run_command(f"tail -n {int(lines)} {quote_path(path)}")


@mcp.tool()
def fs_mkdir(path: str) -> str:
    """Create a directory (and parents) on the cluster. (IRI: POST /filesystem/mkdir)"""
    quoted = quote_path(path)
    return run_command(f"mkdir -p {quoted} && echo created: $(realpath {quoted})")


@mcp.tool()
def fs_upload(path: str, local_path: str) -> dict:
    """Upload a local file to the cluster. (IRI: POST /filesystem/upload)

    Transfers local_path → path on the cluster via rsync or scp.
    Creates remote parent directories as needed. No size limit.
    Returns {remote_path, bytes, sha256, verified, transport}.
    """
    return upload_file(Path(local_path), path)


@mcp.tool()
def fs_checksum(path: str) -> str:
    """SHA-256 checksum of a file on the cluster. (IRI: GET /filesystem/checksum)"""
    return run_command(f"sha256sum {quote_path(path)}")


@mcp.tool()
def fs_download(path: str, local_path: str | None = None) -> dict:
    """Download a file from the cluster to local disk. (IRI: GET /filesystem/download ⚠ deviation)

    Transfers path → local_path via rsync or scp. No size limit.
    local_path defaults to the filename in the current working directory.
    Returns {local_path, bytes, sha256, verified, transport}.
    Deliberately deviates from the IRI base64 shape — see IRI_CHECKLIST.md.
    """
    dest = Path(local_path) if local_path else Path.cwd() / Path(path).name
    return download_file(path, dest)


@mcp.tool()
def fs_cp(src: str, dst: str) -> str:
    """Copy a file or directory on the cluster. (IRI: POST /filesystem/cp)

    Uses cp -r so it works for both files and directories.
    """
    return run_command(f"cp -r {quote_path(src)} {quote_path(dst)} && echo ok")


@mcp.tool()
def fs_mv(src: str, dst: str) -> str:
    """Move or rename a file or directory on the cluster. (IRI: POST /filesystem/mv)

    Destructive — the source path will no longer exist after this call.
    """
    return run_command(f"mv {quote_path(src)} {quote_path(dst)} && echo ok")


@mcp.tool()
def fs_chmod(path: str, mode: str) -> str:
    """Change file permissions on the cluster. (IRI: PUT /filesystem/chmod)

    mode is an octal string, e.g. '755' or '644'.
    """
    return run_command(f"chmod {shlex.quote(mode)} {quote_path(path)} && echo ok")


@mcp.tool()
def fs_chown(path: str, owner: str = "", group: str = "") -> str:
    """Change file ownership on the cluster. (IRI: PUT /filesystem/chown)

    Supply owner, group, or both. Normal users can only change group to one
    they belong to; changing owner requires root.
    """
    if not owner and not group:
        raise ValueError("Provide at least one of owner or group")
    spec = owner + (":" + group if group else "")
    return run_command(f"chown {shlex.quote(spec)} {quote_path(path)} && echo ok")


@mcp.tool()
def fs_symlink(path: str, link_path: str) -> str:
    """Create a symbolic link on the cluster. (IRI: POST /filesystem/symlink)

    path is the target; link_path is the new symlink to create.
    """
    return run_command(
        f"ln -s {quote_path(path)} {quote_path(link_path)} && echo ok"
    )


_COMPRESSION_FLAGS = {
    CompressionType.NONE: "",
    CompressionType.GZIP: "z",
    CompressionType.BZIP2: "j",
    CompressionType.XZ: "J",
}


@mcp.tool()
def fs_compress(
    target_path: str,
    path: str | None = None,
    match_pattern: str | None = None,
    dereference: bool = False,
    compression: CompressionType = CompressionType.GZIP,
) -> str:
    """Create an archive on the cluster. (IRI: POST /filesystem/compress)

    target_path: path of the archive to create.
    path: source file or directory (defaults to current directory).
    match_pattern: regex passed to find -regex to filter files.
    dereference: follow symlinks (-h).
    compression: gzip (default), bzip2, xz, or none.
    """
    flag = _COMPRESSION_FLAGS[compression]
    deref = "h" if dereference else ""
    tar_flags = f"-{deref}c{flag}f"

    if match_pattern:
        src = quote_path(path or ".")
        pattern = shlex.quote(match_pattern)
        cmd = (
            f"find {src} -regex {pattern} -print0 | "
            f"tar {tar_flags} {quote_path(target_path)} --null -T -"
        )
    else:
        src = quote_path(path or ".")
        cmd = f"tar {tar_flags} {quote_path(target_path)} {src}"

    return run_command(cmd + " && echo ok")


@mcp.tool()
def fs_extract(
    path: str,
    target_path: str,
    compression: CompressionType = CompressionType.GZIP,
) -> str:
    """Extract an archive on the cluster. (IRI: POST /filesystem/extract)

    path: archive file to extract.
    target_path: directory to extract into (created if absent).
    compression: gzip (default), bzip2, xz, or none.
    """
    flag = _COMPRESSION_FLAGS[compression]
    tar_flags = f"-x{flag}f"
    return run_command(
        f"mkdir -p {quote_path(target_path)} && "
        f"tar {tar_flags} {quote_path(path)} -C {quote_path(target_path)} && echo ok"
    )


# === extensions (not part of the IRI API) ====================================

@mcp.tool()
def run_command_on_cluster(command: str) -> str:
    """Run an arbitrary shell command on the Irene front-end node (extension —
    not an IRI endpoint).

    Use only when no dedicated tool fits, e.g. 'module avail' to list software,
    'listcpu -p <project>' to check core-time, or 'lfs quota -p $UID $HOME' for
    disk usage. Runs under a login shell from the home directory; returns
    stdout+stderr. Do not run heavy computation on the front-end — submit a job
    instead. Before calling this, show the user the exact command and a
    one-line explanation of what it does, unless they asked to just run it.
    """
    return run_command(command)


def main():
    serve(mcp)


if __name__ == "__main__":
    main()
