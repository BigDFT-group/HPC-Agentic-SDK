---
name: irene-configuring
description: Use when the user wants to set up, configure, or troubleshoot the irene plugin, including SSH access, default TGCC project/account, filesystem defaults, optional docs embeddings, or ~/.hpc-agent/irene.json.
---

# Configuring Irene

Settings live in `~/.hpc-agent/irene.json` (the common directory shared by
every hpc-agent-core plugin). Environment variables override the file:
`IRENE_HOST`, `IRENE_ACCOUNT`, `IRENE_FILESYSTEMS`, `IRENE_EMBED_API_KEY`,
and `IRENE_CONFIG`. A legacy `~/.irene/config.json` is still read if it's
the only config present.

Recommended config:

```json
{
  "ssh": {"host": "irene"},
  "computer": {"passfile": "/tmp/irene"},
  "defaults": {"account": "gen12345", "filesystems": "scratch,work"}
}
```

If the user has a config file from before this plugin moved onto
hpc-agent-core: `ssh.passfile` must move to `computer.passfile` (the old
location is no longer read); `account`/`filesystems` still work at their
old top-level location, but `defaults.account`/`defaults.filesystems` is
now preferred.

Plugin installation has two separate phases. Adding the marketplace only fetches
plugin metadata and does not require `uv`. Starting the installed MCP servers
does require `uv`, because the plugin manifest launches `irene-hpc-mcp` and
`irene-docs-mcp` with `uv tool run`.

When troubleshooting installation, first check that the process launching Codex
or Claude Code has `uv` on `PATH`. User installs commonly place it in
`~/.local/bin`; launch the agent from a shell with:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

If the host application cannot inherit that `PATH`, register the MCP servers
manually with the absolute `uv` path, for example `/home/you/.local/bin/uv`.
Keep the repository plugin manifest portable by using `uv` there, not a
machine-specific absolute path.

Ask how the user reaches Irene. Prefer an existing SSH alias from `~/.ssh/config`;
otherwise use the TGCC-provided `user@host` destination. If SSH requires a
password, set `computer.passfile` to the local file containing it, such as
`/tmp/irene`. Access details are in site/project documentation, not in the public
guide. If the agent session is running directly on an Irene front-end node
itself (not a personal laptop), set `"host": "localhost"` instead — no SSH
key or passfile needed at all in that case.

You may store a remembered project ID in `defaults.account`, but job
submission must not use it silently. Every JobSpec must include an
explicit `attributes.account`; if the user has not specified one, call
`get_projects` and ask which available project to charge before
submitting.

Set `defaults.filesystems` to the default Bridge `-m` value. Irene job
submissions must declare filesystems. Use `scratch,work` for ordinary
jobs, `scratch,store` for jobs reading or writing STORE, or
`scratch,work,store` when all three are needed.

Validate with:

```bash
uv tool run --quiet --from git+https://github.com/BigDFT-group/BigDFT-Agents.git@main#subdirectory=server irene-doctor
```

All lines should read `✓` except possibly embedding, which reads `!`
(not `✗`) since no shared embedding endpoint is configured for Irene at
all — that's expected, not a problem. Docs search works offline with BM25
regardless.
