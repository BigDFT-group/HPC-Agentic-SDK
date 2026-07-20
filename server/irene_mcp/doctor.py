"""Health checks for the IreneAgent configuration.

    python -m irene_mcp.doctor

Reuses hpc_agent_core.doctor's config/guide/index/embedding checks, but
defines its own SSH+scheduler check rather than calling
hpc_agent_core.doctor.main() directly: that helper's check_ssh() expects a
single scheduler_probe command whose output *starts with* the scheduler's
name (e.g. "slurm 24.05.8"), which fits Slurm/Grid Engine but not Bridge —
there's no one Bridge command shaped like that, just several (ccc_msub,
ccc_mprun, ccc_mpp, ccc_mpinfo) that need to simply exist. Per
hpc_agent_core.doctor's own docstring, this is the expected way to diverge:
reuse the independently-callable check_* functions that fit, write a local
replacement for the one that doesn't.
"""
import sys

from hpc_agent_core.doctor import (
    OK,
    FAIL,
    check_config_file,
    check_docs_guide_bundled,
    check_docs_index,
    check_embedding,
)
from hpc_agent_core.middleware import run_command
from irene_mcp import config  # noqa: F401 -- registers via configure()

_BRIDGE_COMMANDS = {"ccc_msub", "ccc_mprun", "ccc_mpp", "ccc_mpinfo"}


def check_ssh_and_bridge() -> bool:
    host = config.ssh_host()
    try:
        output = run_command("echo irene-doctor-ok && hostname")
    except Exception as e:
        print(f"{FAIL} ssh ({host}): {e}")
        return False
    if "irene-doctor-ok" not in output:
        print(f"{FAIL} ssh ({host}): unexpected response: {output[:200]}")
        return False
    print(f"{OK} ssh ({host}): connected to {output.strip().splitlines()[-1]}")

    # Checked one at a time: `command -v` exits non-zero for a single missing
    # command, and hpc_agent_core.middleware.run_command always raises on
    # non-zero exit — a single combined "command -v a b c" would raise (and
    # lose which ones were actually found) the moment any one is missing.
    missing = []
    for cmd in sorted(_BRIDGE_COMMANDS):
        try:
            run_command(f"command -v {cmd}")
        except RuntimeError:
            missing.append(cmd)
    if missing:
        print(f"{FAIL} bridge commands missing: {', '.join(missing)}")
        return False
    print(f"{OK} bridge commands: {', '.join(sorted(_BRIDGE_COMMANDS))}")
    return True


def main() -> int:
    results = [
        check_config_file(),
        check_ssh_and_bridge(),
        check_docs_guide_bundled(),
        check_docs_index(),
        check_embedding(),
    ]
    if all(results):
        print("\nAll checks passed.")
        return 0
    print("\nSome checks FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
