"""TGCC Irene settings, registered with hpc-agent-core.

This module calls `hpc_agent_core.config.configure(...)` once, at import
time, before any other hpc_agent_core module touches config. Every other
module in this package (`compute`, `hpc_server`, `docs_server`, `doctor`)
imports this module first so the registration has already happened.

Settings resolve in order: environment variable > the user's config file >
the default registered here. The user config file lives at the common
`~/.hpc-agent/irene.json` (see hpc_agent_core.config for the exact
resolution, including the legacy `~/.irene/config.json` fallback).

Irene requires password-based SSH auth for some users (a `passfile`). This
is a per-user value, so it goes through hpc_agent_core's generic
`"computer"` config-file object, not through configure()'s machine-level
computer_defaults:

    {
      "ssh": {"host": "irene"},
      "computer": {"passfile": "/tmp/irene"},
      "defaults": {"account": "gen12345", "filesystems": "scratch,work"},
      "embedding": {"api_key": "..."}
    }

Note for anyone who configured this plugin before this migration: the old
schema nested passfile under `ssh.passfile` — that location is no longer
read (hpc_agent_core.middleware.get_frontend() only reads the `"computer"`
object), so move it to `computer.passfile` in your config file. `account`
and `filesystems` still work at the old top-level location too (see
default_account/default_filesystems below), so those don't need to move.
"""
import json
import os
from functools import lru_cache

from hpc_agent_core import config as _core

_core.configure(
    env_prefix="IRENE",                  # -> IRENE_HOST, IRENE_CONFIG, IRENE_EMBED_API_KEY
    default_host="irene",                 # ssh.host fallback: an alias in ~/.ssh/config, or user@hostname
    package="irene_mcp",                  # matches this package's actual name
    embed_base_url="",                    # no shared embedding endpoint for this site; BM25 only until one is configured
    embed_model="",
    docs_cite_url="",                     # blank: TGCC's site stability is unconfirmed — see AGENTS.md
    config_dir_name=".irene",             # legacy path ~/.irene/config.json, kept working for existing users
    # No computer_defaults: passfile (if needed) is per-user, so it belongs
    # in the end user's own config file under "computer", not here.
)

# Re-export the registered values/functions the rest of the package imports
# from here (kept for readability at call sites):
ssh_host = _core.ssh_host
embed_api_key = _core.embed_api_key
CONFIG_PATH = _core.config_path()
DATA_DIR = _core.data_dir()


@lru_cache(maxsize=1)
def load_cluster_config() -> dict:
    """Irene's static facts (partitions, subsystems, storage, modules) —
    bundled package data, not the user's config file."""
    with open(DATA_DIR / "irene_config.json") as f:
        return json.load(f)


def _user_config() -> dict:
    """The user's config file parsed, or {} if absent/malformed. Read at
    call time (never at import) so a missing config never blocks startup."""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def default_account() -> str | None:
    """The TGCC project to charge when a job doesn't name one.

    Irene requires -A <project> on every job submission. Resolves
    IRENE_ACCOUNT, then the config file's defaults.account, then the
    pre-migration top-level `account` key (so existing configs keep
    working), then None (submit_job then errors with a clear message
    rather than submitting an unbillable job).
    """
    user_config = _user_config()
    return (os.environ.get("IRENE_ACCOUNT")
            or (user_config.get("defaults") or {}).get("account")
            or user_config.get("account"))


def default_filesystems() -> str:
    """The filesystem list for Bridge's #MSUB -m, when a job doesn't set
    attributes.custom_attributes['filesystems']. Irene requires this on
    every job submission."""
    user_config = _user_config()
    return (os.environ.get("IRENE_FILESYSTEMS")
            or (user_config.get("defaults") or {}).get("filesystems")
            or user_config.get("filesystems")
            or "scratch,work")
