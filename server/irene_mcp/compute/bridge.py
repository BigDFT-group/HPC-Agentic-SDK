"""BridgeBackend for the TGCC Irene supercomputer."""
from __future__ import annotations

import re
import shlex
import time

from .. import config
from ..middleware import run_command, write_remote_file
from ..models import Job, JobSpec, JobState, JobStatus, map_bridge_state
from .base import SchedulerBackend, duration_to_seconds, parse_exit_code, render_body, to_epoch

_jobs_dir = ".irene/jobs"
_GPU_CORES_PER_GPU = {
    "v100": 10,
    "v100l": 36,
    "v100l-os": 36,
    "v100xl": 72,
    "xlarge": 112,
}


def _tasks(spec: JobSpec) -> int:
    res = spec.resources
    return res.process_count or max(1, res.node_count * res.processes_per_node)


def _cores_per_task(spec: JobSpec) -> int | None:
    res = spec.resources
    if res.cpu_cores_per_process:
        return res.cpu_cores_per_process
    gpus = res.gpus or res.gpu_cores_per_process
    if gpus:
        return _GPU_CORES_PER_GPU.get(spec.attributes.queue_name.lower(), 1) * gpus
    return None


def _msub_option(key: str, value: str) -> str:
    key = key.lstrip("-")
    return f"#MSUB -{key} {value}" if len(key) == 1 else f"#MSUB --{key} {value}"


def _parse_ccc_msub_job_id(output: str) -> str:
    for line in reversed(output.strip().splitlines()):
        matches = re.findall(r"\b\d{3,}\b", line)
        if matches:
            return matches[-1]
    return ""


def _parse_compuse_projects(output: str) -> list[dict[str, str | None]]:
    projects = []
    seen = set()
    for line in output.splitlines():
        parts = line.split()
        if not parts:
            continue
        token = parts[0]
        if "@" not in token or token.lower().startswith("account"):
            continue
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
    return projects


def _available_projects() -> list[dict[str, str | None]]:
    return _parse_compuse_projects(run_command("ccc_compuse", raise_errors=False))


def _format_projects(projects: list[dict[str, str | None]]) -> str:
    if not projects:
        return "No projects could be parsed from ccc_compuse."
    return ", ".join(
        f"{p['id']}@{p['partition']}" + (f" ({p['status']})" if p.get("status") else "")
        for p in projects
    )


def _validate_account(spec: JobSpec) -> str:
    account = spec.attributes.account
    projects = _available_projects()
    if not account:
        raise ValueError(
            "JobSpec.attributes.account is required on Irene. "
            "Call get_projects first and ask the user which TGCC project to charge. "
            f"Available projects: {_format_projects(projects)}"
        )
    matching = [p for p in projects if p["id"] == account]
    if not matching:
        raise ValueError(
            f"Project '{account}' is not available to the current user according to ccc_compuse. "
            f"Available projects: {_format_projects(projects)}"
        )
    partition = spec.attributes.queue_name
    if not any(p["partition"] == partition for p in matching):
        raise ValueError(
            f"Project '{account}' is not available on partition '{partition}' according to ccc_compuse. "
            f"Available entries for this project: {_format_projects(matching)}"
        )
    return account


def _job_from_mpp_line(line: str) -> Job | None:
    parts = line.split()
    if len(parts) < 8 or not parts[2].isdigit():
        return None
    state = map_bridge_state(parts[6])
    reason = " ".join(parts[12:]) if len(parts) > 12 else None
    return Job(
        id=parts[2],
        status=JobStatus(
            state=state,
            message=reason,
            meta_data={
                "user": parts[0],
                "account": parts[1],
                "ncpus": parts[3],
                "partition": parts[4],
                "native_state": parts[6],
                "time_limit": parts[7] if len(parts) > 7 else None,
                "run_or_start": parts[8] if len(parts) > 8 else None,
                "name": parts[11] if len(parts) > 11 else None,
                "nodes_or_reason": reason,
            },
        ),
    )


def _parse_ccc_mpp(output: str) -> list[Job]:
    jobs: list[Job] = []
    for line in output.splitlines():
        job = _job_from_mpp_line(line)
        if job:
            jobs.append(job)
    return jobs


def _parse_macct(job_id: str, output: str) -> Job:
    fields: dict[str, str] = {}
    for line in output.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()
    native_state = "UNKNOWN"
    exit_code = None
    for line in output.splitlines():
        if " COMPLETED" in line:
            native_state = "COMPLETED"
            exit_code = 0
        elif any(marker in line for marker in (" FAILED", " TIMEOUT", " CANCELLED", " CANCELED")):
            native_state = line.split()[-1]
            exit_code = parse_exit_code(fields.get("exitcode", ""))
    if native_state == "UNKNOWN" and "execution" in fields:
        native_state = fields["execution"]
    return Job(
        id=job_id,
        status=JobStatus(
            state=map_bridge_state(native_state),
            time=to_epoch(fields.get("date", "")),
            exit_code=exit_code,
            message=fields.get("limits"),
            meta_data={"native_state": native_state, "account": fields.get("account"), "name": fields.get("jobname"), "raw": output},
        ),
    )


class BridgeBackend(SchedulerBackend):
    name = "bridge-irene"

    def _header(self, spec: JobSpec) -> list[str]:
        attr = spec.attributes
        res = spec.resources
        account = _validate_account(spec)
        filesystems = (
            attr.custom_attributes.get("filesystems")
            or attr.custom_attributes.get("m")
            or config.default_filesystems()
        )
        lines = [
            "#!/bin/bash",
            f"#MSUB -r {spec.name}",
            f"#MSUB -q {attr.queue_name}",
            f"#MSUB -n {_tasks(spec)}",
            f"#MSUB -T {duration_to_seconds(attr.duration)}",
            f"#MSUB -m {filesystems}",
        ]
        cores = _cores_per_task(spec)
        if cores:
            lines.append(f"#MSUB -c {cores}")
        if res.node_count:
            lines.append(f"#MSUB -N {res.node_count}")
        if res.exclusive_node_use:
            lines.append("#MSUB -x")
        lines.append(f"#MSUB -A {account}")
        if spec.stdout_path:
            lines.append(f"#MSUB -o {spec.stdout_path}")
        else:
            lines.append("#MSUB -o irene_%I.o")
        if spec.stderr_path:
            lines.append(f"#MSUB -e {spec.stderr_path}")
        else:
            lines.append("#MSUB -e irene_%I.e")
        if attr.reservation_id:
            lines.append(f"#MSUB -E --reservation={attr.reservation_id}")
        for key, val in attr.custom_attributes.items():
            if key in {"filesystems", "m"}:
                continue
            lines.append(_msub_option(key, str(val)))
        return lines

    def render_script(self, spec: JobSpec) -> str:
        """Render a JobSpec as an Irene Bridge submission script."""
        default_launcher = "ccc_mprun" if _tasks(spec) > 1 or _cores_per_task(spec) else None
        return "\n".join(self._header(spec)) + render_body(spec, default_launcher=default_launcher)

    def submit(self, spec: JobSpec) -> dict:
        """Write the rendered script on Irene and submit it with ccc_msub."""
        stamp = time.strftime("%Y%m%d-%H%M%S")
        script_path = write_remote_file(
            f"{_jobs_dir}/{spec.name}-{stamp}.sh", self.render_script(spec)
        )
        output = run_command(f"ccc_msub {shlex.quote(script_path)}")
        job_id = _parse_ccc_msub_job_id(output)
        if not job_id:
            raise RuntimeError(f"ccc_msub did not return a job id: {output}")
        return {"job_id": job_id, "script_path": script_path, "submission_output": output.strip()}

    def get_statuses(self, job_ids: list[str]) -> list[Job]:
        """Fetch normalized statuses for one or more jobs."""
        live_jobs = _parse_ccc_mpp(run_command("ccc_mpp -u $USER", raise_errors=False))
        by_id = {j.id: j for j in live_jobs}
        jobs: list[Job] = []
        for job_id in job_ids:
            if job_id in by_id:
                jobs.append(by_id[job_id])
                continue
            output = run_command(f"ccc_macct {shlex.quote(job_id)}", raise_errors=False)
            if output.strip():
                jobs.append(_parse_macct(job_id, output))
        return jobs

    def get_recent_statuses(self, since: str = "unused") -> list[Job]:
        """Return the current user's pending/running jobs from ccc_mpp."""
        return _parse_ccc_mpp(run_command("ccc_mpp -u $USER", raise_errors=False))

    def cancel(self, job_id: str) -> Job | str:
        """Cancel with ccc_mdel, then report the job's state when available."""
        run_command(f"ccc_mdel {shlex.quote(job_id)}")
        jobs = self.get_statuses([job_id])
        return jobs[0] if jobs else f"ccc_mdel sent; job {job_id} not found in ccc_mpp/ccc_macct"
