# IreneAgent

Claude Code and Codex plugin for the TGCC **Irene** supercomputer at CEA: submit
and monitor Bridge/Slurm jobs, manage files on the cluster, and search a built-in
Irene guide from the agent.

Irene is CPU-first. The normal target is the `rome` partition: 2,286 AMD Rome
nodes with 128 cores per node. Specialized `xlarge` and V100-family partitions
cover large-memory and GPU workloads.

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
- `account` is the TGCC project used for Bridge `-A`. `IRENE_ACCOUNT` overrides it.
- `filesystems` is the default Bridge `-m` value. Irene job submissions must declare filesystems. `IRENE_FILESYSTEMS` overrides it.

Docs search works offline with BM25 over the packaged guide.

## Install

The plugin starts MCP servers with `uv tool run`, so `uv` must be installed and
available on PATH before Claude Code or Codex starts the plugin.

### Claude Code

```text
/plugin marketplace add CEA-HPC/Irene-Agent
/plugin install irene@irene-marketplace
/reload-plugins
```

### Codex

```text
codex plugin marketplace add CEA-HPC/Irene-Agent
```

Then open `/plugins`, install `irene`, start a new thread, and run `/irene-demo`.

## Manual MCP Config

```json
{
  "mcpServers": {
    "irene-hpc": {
      "command": "uv",
      "args": ["tool", "run", "--quiet", "--from", "git+https://github.com/CEA-HPC/Irene-Agent.git@main#subdirectory=server", "irene-hpc-mcp"],
      "env": {}
    },
    "irene-docs": {
      "command": "uv",
      "args": ["tool", "run", "--quiet", "--from", "git+https://github.com/CEA-HPC/Irene-Agent.git@main#subdirectory=server", "irene-docs-mcp"],
      "env": {}
    }
  }
}
```

## Verify

```bash
uv tool run --from git+https://github.com/CEA-HPC/Irene-Agent.git@main#subdirectory=server irene-doctor
```
