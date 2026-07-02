"""Configuration for the Irene MCP servers.

Settings come from, in order of precedence:
  1. Environment variables (IRENE_*)
  2. The user config file ~/.irene/config.json (path override: IRENE_CONFIG)
  3. Defaults

Example config:

    {
      "ssh": {"host": "irene", "passfile": "/tmp/irene"},
      "account": "gen12345",
      "filesystems": "scratch,work",
      "embedding": {"api_key": "..."}
    }

`ssh.host` is an alias from ~/.ssh/config or a plain user@hostname. If Irene
requires password authentication, set `ssh.passfile` to a local file containing
the password; `IRENE_PASSFILE` overrides it. `account` is the default TGCC
project ID charged for jobs that do not set one explicitly. `filesystems` is the
default Bridge -m value; Irene requires job submissions to declare the
filesystems they need.

Documentation search is BM25 keyword search by default. Embedding settings are
optional and only useful after rebuilding a vector index for Irene.
"""
import json
import os
from contextlib import ExitStack
from functools import lru_cache
from importlib import resources
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("IRENE_CONFIG", "~/.irene/config.json")).expanduser()


def _file_config() -> dict:
    """The parsed config file, or {} if absent. Raises on malformed JSON."""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Malformed config file {CONFIG_PATH}: {e}") from e


def ssh_host() -> str:
    """SSH destination for the Irene front-end (alias or user@hostname)."""
    return (os.environ.get("IRENE_HOST")
            or _file_config().get("ssh", {}).get("host")
            or "irene")


def ssh_passfile() -> str | None:
    """Optional remotemanager password file for Irene SSH authentication."""
    return (os.environ.get("IRENE_PASSFILE")
            or _file_config().get("ssh", {}).get("passfile")
            or None)


def default_account() -> str | None:
    """Default TGCC project ID for jobs that do not set one.

    Irene job execution requires -A <project>; this provides a fallback when a
    JobSpec leaves attributes.account unset. Override via IRENE_ACCOUNT.
    """
    return (os.environ.get("IRENE_ACCOUNT")
            or _file_config().get("account")
            or None)


def default_filesystems() -> str:
    """Filesystem list for Bridge -m. Irene requires this on job submissions."""
    return (os.environ.get("IRENE_FILESYSTEMS")
            or _file_config().get("filesystems")
            or "scratch,work")


# --- Optional embedding endpoint -------------------------------------------
# The committed Irene index is keyword-only. These settings are present so a
# site can rebuild a private vector index without changing the docs server.

EMBED_BASE_URL = os.environ.get(
    "IRENE_EMBED_BASE_URL",
    _file_config().get("embedding", {}).get("base_url", ""),
)
EMBED_MODEL = os.environ.get(
    "IRENE_EMBED_MODEL",
    _file_config().get("embedding", {}).get("model", ""),
)


def embed_api_key() -> str:
    """API key for an optional embedding endpoint. Empty string means no auth."""
    file = _file_config().get("embedding", {})
    return os.environ.get("IRENE_EMBED_API_KEY") or file.get("api_key") or ""


# --- Static data ------------------------------------------------------------

_RESOURCE_STACK = ExitStack()


def _bundled_data_dir() -> Path:
    """Filesystem path to package data, including zip-safe extraction fallback."""
    data = resources.files("irene_mcp") / "data"
    return _RESOURCE_STACK.enter_context(resources.as_file(data))


_DATA_DIR = _bundled_data_dir()

DOCS_INDEX_DIR = Path(os.environ.get("IRENE_DOCS_INDEX", _DATA_DIR / "docs_index"))
DOCS_SOURCE = Path(os.environ.get("IRENE_DOCS_SOURCE", _DATA_DIR / "irene_guide.md"))
DOCS_SITE_BASE = "https://www-tgcc.ccc.cea.fr/"


@lru_cache(maxsize=1)
def load_cluster_config() -> dict:
    """Load the static Irene description (partitions, modules, storage)."""
    path = Path(os.environ.get("IRENE_CLUSTER_CONFIG", _DATA_DIR / "irene_config.json"))
    with open(path) as f:
        return json.load(f)
