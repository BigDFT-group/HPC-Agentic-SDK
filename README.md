# IreneAgent

Claude Code and Codex plugin for the TGCC **Irene** supercomputer at CEA: submit
and monitor Bridge/Slurm jobs, manage files on the cluster, and search a built-in
Irene guide from the agent.

Irene is CPU-first. The normal target is the `rome` partition: 2,286 AMD Rome
nodes with 128 cores per node. Specialized `xlarge` and V100-family partitions
cover large-memory and GPU workloads.


## Included Plugins

This marketplace currently distributes two user-facing plugins:

- `irene`: live TGCC Irene status, filesystem, job, and documentation tools.
- `remotemanager`: RemoteManager Dataset campaign tools. The Python MCP server
  remains in the external `remotemanager-MCP` repository and is installed at
  launch time with `uv tool run`. User-specific paths are read from
  `~/.config/remotemanager-mcp/config.yaml`, not from marketplace metadata.

Project-wide marketplace maintenance rules live in `AGENTS.md`.

## Configure

Settings live in `~/.irene/config.json`:

```json
{
  "ssh": {"host": "irene", "passfile": "/tmp/irene"},
  "account": "gen12345",
  "filesystems": "scratch,work"
}
```

- `ssh.host` is a `~/.ssh/config` alias or TGCC-provided `user@host`. `IRENE_HOST` overrides it.
- `ssh.passfile` is an optional remotemanager password file, for example `/tmp/irene`. `IRENE_PASSFILE` overrides it.
- `account` is only a remembered project value for configuration workflows. Job submissions must still set `attributes.account` explicitly; the backend validates it against `ccc_compuse`.
- `filesystems` is the default Bridge `-m` value. Irene job submissions must declare filesystems. `IRENE_FILESYSTEMS` overrides it.

Docs search works offline with BM25 over the packaged guide.

## Install

Adding the plugin marketplace only registers the plugin metadata; it does not
start the Irene MCP servers and does not need `uv`.

The installed plugin starts MCP servers with `uv tool run`, so `uv` must be
installed and available on `PATH` before Claude Code or Codex starts the plugin.
If `uv` was installed with `pip install --user` or the official installer, make
sure the agent process inherits `~/.local/bin`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

If the host application is launched from a desktop menu, it may not inherit the
same shell `PATH`. In that case, either start it from a configured shell or use a
manual MCP registration with the absolute path to `uv`.

### Claude Code

```text
/plugin marketplace add BigDFT-group/HPC-Agentic-SDK
/plugin install irene@irene-marketplace
/reload-plugins
```

### Codex

```text
codex plugin marketplace add BigDFT-group/HPC-Agentic-SDK
```

Then open `/plugins`, install `irene`, start a new thread, and run `/irene-demo`.

## Manual MCP Config

Use this form when `uv` is reliably on `PATH` for the process that starts MCP
servers:

```json
{
  "mcpServers": {
    "irene-hpc": {
      "command": "uv",
      "args": ["tool", "run", "--quiet", "--from", "git+https://github.com/BigDFT-group/HPC-Agentic-SDK.git@main#subdirectory=server", "irene-hpc-mcp"],
      "env": {}
    },
    "irene-docs": {
      "command": "uv",
      "args": ["tool", "run", "--quiet", "--from", "git+https://github.com/BigDFT-group/HPC-Agentic-SDK.git@main#subdirectory=server", "irene-docs-mcp"],
      "env": {}
    }
  }
}
```

For local installs where `uv` is not on `PATH`, replace `"command": "uv"` with
the absolute executable path, for example:

```json
{
  "mcpServers": {
    "irene-hpc": {
      "command": "/home/genovese/.local/bin/uv",
      "args": ["tool", "run", "--quiet", "--from", "git+https://github.com/BigDFT-group/HPC-Agentic-SDK.git@main#subdirectory=server", "irene-hpc-mcp"],
      "env": {}
    },
    "irene-docs": {
      "command": "/home/genovese/.local/bin/uv",
      "args": ["tool", "run", "--quiet", "--from", "git+https://github.com/BigDFT-group/HPC-Agentic-SDK.git@main#subdirectory=server", "irene-docs-mcp"],
      "env": {}
    }
  }
}
```

Codex can also register the same servers without editing TOML manually:

```bash
codex mcp add irene-hpc -- /home/genovese/.local/bin/uv tool run --quiet --from git+https://github.com/BigDFT-group/HPC-Agentic-SDK.git@main#subdirectory=server irene-hpc-mcp
codex mcp add irene-docs -- /home/genovese/.local/bin/uv tool run --quiet --from git+https://github.com/BigDFT-group/HPC-Agentic-SDK.git@main#subdirectory=server irene-docs-mcp
```

## Verify

```bash
uv tool run --from git+https://github.com/BigDFT-group/HPC-Agentic-SDK.git@main#subdirectory=server irene-doctor
```
