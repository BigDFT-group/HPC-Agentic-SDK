"""Data models mirroring the IRI Facility API schemas for Irene.

Irene is a CPU-first TGCC/CEA supercomputer. The dominant partition is `rome`
with 2,286 AMD Rome CPU nodes. GPU and large-memory partitions are available,
but a normal job is a CPU/MPI job launched through Bridge (`ccc_msub` and
`ccc_mprun`).
"""
from enum import Enum

from pydantic import BaseModel, Field


class JobState(str, Enum):
    """Normalized job states (IRI/PSI-J), mapped from Bridge/Slurm native states."""
    NEW = "new"
    QUEUED = "queued"
    HELD = "held"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    UNKNOWN = "unknown"


_BRIDGE_STATE_MAP = {
    "PEN": JobState.QUEUED,
    "PD": JobState.QUEUED,
    "PENDING": JobState.QUEUED,
    "CF": JobState.QUEUED,
    "CONFIGURING": JobState.QUEUED,
    "RUN": JobState.ACTIVE,
    "R": JobState.ACTIVE,
    "R00": JobState.ACTIVE,
    "R01": JobState.ACTIVE,
    "RUNNING": JobState.ACTIVE,
    "COMP": JobState.ACTIVE,
    "COMPLETING": JobState.ACTIVE,
    "S": JobState.HELD,
    "SUSPENDED": JobState.HELD,
    "COMPLETED": JobState.COMPLETED,
    "CD": JobState.COMPLETED,
    "CANCELLED": JobState.CANCELED,
    "CANCELED": JobState.CANCELED,
    "CA": JobState.CANCELED,
    "FAILED": JobState.FAILED,
    "F": JobState.FAILED,
    "TIMEOUT": JobState.FAILED,
    "TO": JobState.FAILED,
    "OUT_OF_MEMORY": JobState.FAILED,
    "OOM": JobState.FAILED,
    "NODE_FAIL": JobState.FAILED,
}


def map_bridge_state(native: str) -> JobState:
    return _BRIDGE_STATE_MAP.get(native.split()[0].rstrip("+").upper(), JobState.UNKNOWN)


class ResourceSpec(BaseModel):
    """Resources for a job (PSI/J ResourceSpec + Irene extensions).

    Irene Bridge resource requests are CPU/task based: -n is total tasks, -c is
    cores per task, -N optionally constrains node count, and -x requests
    exclusive nodes. GPU allocation on V100-class partitions is controlled by
    choosing a GPU partition and reserving enough cores per task: one GPU is
    allocated for each CpN/GpN cores per task on that partition.
    """
    node_count: int = 1
    process_count: int | None = Field(None, description="Total tasks for Bridge -n")
    processes_per_node: int = Field(1, description="Used to infer total tasks when process_count is absent")
    cpu_cores_per_process: int | None = Field(None, description="Cores per task for Bridge -c; also controls GPU allocation on GPU partitions")
    gpu_cores_per_process: int | None = Field(None, description="PSI/J standard GPU field; Irene maps GPUs through cores per task on GPU partitions")
    gpus: int | None = Field(None, description="Irene extension: requested GPUs per task; converted to cores per task for known GPU partitions")
    exclusive_node_use: bool = Field(False, description="Request exclusive node allocation (-x)")
    memory: int | None = Field(None, description="Advisory only on Irene; Bridge memory is controlled indirectly via cores per task")


class JobAttributes(BaseModel):
    """Scheduler attributes (IRI/PSI-J JobAttributes subset)."""
    duration: int | str = Field(
        7200,
        description="Wall time as integer seconds or HH:MM:SS / D-HH:MM:SS string (Irene default is 7200 seconds)",
    )
    queue_name: str = Field("rome", description="Bridge partition (rome, xlarge, v100, v100l, v100xl, v100l-os)")
    account: str | None = Field(None, description="TGCC project ID for Bridge -A; must be explicit and available to the user")
    reservation_id: str | None = Field(None, description="Reservation name, passed through as a custom scheduler option when supported")
    custom_attributes: dict[str, str] = Field(default_factory=dict, description="Extra Bridge #MSUB options; use key 'm' or 'filesystems' to override -m")


class CompressionType(str, Enum):
    """Compression format for fs_compress / fs_extract (IRI CompressionType)."""
    NONE = "none"
    BZIP2 = "bzip2"
    GZIP = "gzip"
    XZ = "xz"


class VolumeMount(BaseModel):
    """A host path mounted into a container (IRI VolumeMount)."""
    source: str = Field(description="Host path to mount")
    target: str = Field(description="Path inside the container")
    read_only: bool = Field(True, description="Mount as read-only")


class Container(BaseModel):
    """Container specification (IRI Container), executed through pcocc/Bridge.

    `image` is a pcocc image name imported on Irene. In batch jobs the command is
    launched as `ccc_mprun -C <image> -- <cmd>`.
    """
    image: str = Field(description="pcocc image name, e.g. my_pcocc_image")
    volume_mounts: list[VolumeMount] = Field(default_factory=list)


class JobSpec(BaseModel):
    """Job specification (IRI/PSI-J JobSpec subset)."""
    name: str = "irene-job"
    executable: str
    arguments: list[str] = Field(default_factory=list)
    directory: str | None = Field(None, description="Working directory for the job")
    environment: dict[str, str] = Field(default_factory=dict)
    inherit_environment: bool = Field(True, description="Inherit submission environment variables")
    stdin_path: str | None = Field(None, description="Path to use as stdin")
    stdout_path: str | None = None
    stderr_path: str | None = None
    resources: ResourceSpec = Field(default_factory=ResourceSpec)
    attributes: JobAttributes = Field(default_factory=JobAttributes)
    pre_launch: str | None = Field(None, description="Script lines to insert before executable")
    post_launch: str | None = Field(None, description="Script lines to insert after executable")
    launcher: str | None = Field(None, description="Launcher prefix, e.g. 'ccc_mprun' or 'ccc_mprun -E ...'")
    container: Container | None = Field(None, description="Run inside a pcocc container image")


class JobStatus(BaseModel):
    """IRI-compliant job status (state + time + message + exit_code + meta_data)."""
    state: JobState
    time: float | None = Field(None, description="Epoch seconds when known")
    message: str | None = Field(None, description="Human-readable status, queue reason, or accounting summary")
    exit_code: int | None = None
    meta_data: dict | None = Field(None, description="Bridge/Slurm-specific fields")


class Job(BaseModel):
    """IRI Job: identifier + current status + originating spec."""
    id: str
    status: JobStatus | None = None
    job_spec: JobSpec | None = None
