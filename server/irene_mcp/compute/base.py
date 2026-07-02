"""SchedulerBackend ABC and scheduler-neutral script body helpers."""
from __future__ import annotations

import shlex
from abc import ABC, abstractmethod
from datetime import datetime

from ..models import Job, JobSpec


def duration_to_seconds(duration: int | str) -> int:
    """Convert IRI duration to seconds for Bridge #MSUB -T."""
    if isinstance(duration, int):
        return duration
    text = duration.strip()
    days = 0
    if "-" in text:
        day_text, text = text.split("-", 1)
        days = int(day_text)
    parts = [int(p) for p in text.split(":")]
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = 0, parts[0], parts[1]
    else:
        h, m, s = 0, 0, parts[0]
    return days * 86400 + h * 3600 + m * 60 + s


def to_epoch(s: str) -> float | None:
    """Parse a datetime string to epoch seconds when possible."""
    if not s or s in ("Unknown", "N/A", "None", "-"):
        return None
    for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).timestamp()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


def parse_exit_code(s: str) -> int | None:
    """Parse an exit-code field like '0:0' or '0'."""
    try:
        return int(s.split(":")[0])
    except (ValueError, IndexError):
        return None


def render_body(spec: JobSpec, default_launcher: str | None = None) -> str:
    """Render the non-header part of an Irene batch script."""
    lines: list[str] = [""]

    if spec.directory:
        lines.append(f"cd {shlex.quote(spec.directory)}")
    else:
        lines.append("cd ${BRIDGE_MSUB_PWD}")

    for key, value in spec.environment.items():
        lines.append(f"export {key}={shlex.quote(value)}")

    if spec.pre_launch:
        lines.append(spec.pre_launch)

    command = spec.executable
    if spec.arguments:
        command += " " + " ".join(shlex.quote(a) for a in spec.arguments)

    if spec.container:
        c = spec.container
        ctr_args: list[str] = ["ccc_mprun", "-C", shlex.quote(c.image)]
        mounts = []
        for m in c.volume_mounts:
            mount = f"src={m.source},dst={m.target}"
            if m.read_only:
                mount += ",ro"
            mounts.append(mount)
        if mounts:
            ctr_args.append("-E")
            ctr_args.append(shlex.quote("--ctr-mount " + ":".join(mounts)))
        command = " ".join(ctr_args) + " -- " + command
    else:
        launcher = spec.launcher or default_launcher
        if launcher:
            command = launcher + " " + command

    lines.append(command)

    if spec.post_launch:
        lines.append(spec.post_launch)

    lines.append("")
    return "\n".join(lines)


class SchedulerBackend(ABC):
    """Abstract base class for a batch-scheduler backend."""

    name: str

    @abstractmethod
    def render_script(self, spec: JobSpec) -> str:
        """Render *spec* as a scheduler-specific batch script."""

    @abstractmethod
    def submit(self, spec: JobSpec) -> dict:
        """Submit *spec*; return ``{job_id, script_path}``."""

    @abstractmethod
    def get_statuses(self, job_ids: list[str]) -> list[Job]:
        """Return normalized status for each job in *job_ids*."""

    @abstractmethod
    def get_recent_statuses(self, since: str = "unused") -> list[Job]:
        """Return live/recent jobs for the current user."""

    @abstractmethod
    def cancel(self, job_id: str) -> Job | str:
        """Cancel *job_id* and return its resulting state."""
