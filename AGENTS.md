# HPC-Agentic-SDK — Agent Instructions

This repository is the public marketplace/distribution layer for HPC agentic
plugins. It currently includes:

- `plugins/irene`: TGCC Irene skills and MCP launch metadata.
- `server/irene_mcp`: Python implementation for the Irene MCP servers.
- `plugins/remotemanager`: marketplace plugin for the external
  `remotemanager-MCP` Python package.

## Design Rules

- Keep marketplace metadata general, portable, and free of user-specific values.
- User-specific information belongs in documented local config URIs, usually
  `~/.config/<plugin-name>/config.yaml`, not in `.mcp.json` or marketplace JSON.
- Each plugin that needs user information must provide a configuring skill that
  names the config URI, checks first-use prerequisites, explains local override
  files, and exposes a validation sequence before real remote work.
- Workflow guidance belongs in plugin `skills/`, not long MCP tool docstrings.
- MCP stdio servers must not print ordinary diagnostics to stdout.
- Do not commit private passfiles, project/account IDs, private install prefixes,
  or user-local runtime paths except as clearly marked examples.

## Marketplace Structure

A plugin directory should normally contain:

```text
plugins/<plugin-name>/.codex-plugin/plugin.json
plugins/<plugin-name>/.claude-plugin/plugin.json
plugins/<plugin-name>/.mcp.json        # only when the plugin starts MCP servers
plugins/<plugin-name>/skills/...       # at least one usage/configuring skill
```

Register plugins in both marketplace manifests:

```text
.agents/plugins/marketplace.json
.claude-plugin/marketplace.json
```

Plugin manifests should include display metadata, repository, keywords, skills,
and `mcpServers` only if `.mcp.json` exists.

## MCP Launcher Pattern

Prefer generic launch metadata such as:

```json
{
  "command": "uv",
  "args": ["tool", "run", "--quiet", "--from", "<package-source>", "<entrypoint>"],
  "env": {}
}
```

If a server needs user paths or credentials, the Python package should resolve
those from its own local config file. If an environment variable is needed, limit
it to selecting the config URI, for example `PLUGIN_CONFIG=/path/to/config.yaml`.

## Updating Existing Plugins

1. Fetch and inspect repository status before editing.
2. Read the plugin manifest, `.mcp.json`, and relevant skills.
3. Keep MCP launch metadata generic. Prefer config files over static env vars.
4. Update plugin-specific skills when behavior or setup changes.
5. Validate JSON manifests and run affected MCP package tests.
6. Commit and push changes, then refresh/reinstall the plugin in the client.

## Adding A New Computer

For a new machine that only needs RemoteManager campaign execution, prefer a
RemoteManager machine configuration rather than a new full MCP server:

```text
~/.config/remotemanager-mcp/machines/<machine>.yaml
~/.config/remotemanager-mcp/user-overrides.local.yaml
```

Create a new facility plugin only when the machine needs custom live status,
filesystem, documentation, or scheduler tools beyond generic RemoteManager
campaign execution.

## Irene Rules

- Irene is CPU-first. Default normal jobs to `rome`.
- Batch scripts use TGCC Bridge `#MSUB` directives and submit with `ccc_msub`.
- Parallel work launches with `ccc_mprun`.
- Job submissions require explicit `-q <partition>`, `-A <project>`, and
  `-m <filesystems>`.
- Before submitting an Irene job, check available projects and ask the user when
  no project was explicitly specified.
- Live status comes from Bridge commands such as `ccc_mpinfo`, `ccc_mpp`,
  `ccc_mstat`, `ccc_macct`, `ccc_mqinfo`, `ccc_compuse`, and `ccc_myproject`.
- Do not encourage frequent scheduler polling; TGCC prohibits `watch` on
  scheduler commands.

## Irene Development

The Irene guide is `server/irene_mcp/data/irene_guide.md`. Rebuild the BM25
index with:

```bash
cd server
python -m irene_mcp.rag.ingest --no-embed
```

Embeddings are optional and not committed by default.

```bash
cd server
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m irene_mcp.doctor
.venv/bin/python tests/smoke.py
```

`tests/smoke.py --job` submits a real job and consumes allocation time.

## Refresh Procedure

After pushing marketplace changes, users may need to refresh/reinstall the
marketplace/plugin and start a new session. MCP tools are loaded at session
startup; updating files in the repository does not add tools to an already
running session.
