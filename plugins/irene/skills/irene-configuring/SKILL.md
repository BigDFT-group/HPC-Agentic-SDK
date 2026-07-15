---
name: irene-configuring
description: Use when the user wants to set up, configure, or troubleshoot the irene plugin, including SSH access, default TGCC project/account, filesystem defaults, optional docs embeddings, or ~/.irene/config.json.
---

# Configuring Irene

Settings live in `~/.irene/config.json`. Environment variables override the file:
`IRENE_HOST`, `IRENE_PASSFILE`, `IRENE_ACCOUNT`, `IRENE_FILESYSTEMS`,
`IRENE_EMBED_API_KEY`, and `IRENE_CONFIG`.

Recommended config:

```json
{
  "ssh": {"host": "irene", "passfile": "/tmp/irene"},
  "account": "gen12345",
  "filesystems": "scratch,work"
}
```

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
manually with the absolute `uv` path, for example `/home/genovese/.local/bin/uv`.
Keep the repository plugin manifest portable by using `uv` there, not a
machine-specific absolute path.

Ask how the user reaches Irene. Prefer an existing SSH alias from `~/.ssh/config`;
otherwise use the TGCC-provided `user@host` destination. If SSH requires a
password, set `ssh.passfile` to the local file containing it, such as
`/tmp/irene`. Access details are in site/project documentation, not in the public
guide.

You may store a remembered project ID in `account`, but job submission must not
use it silently. Every JobSpec must include an explicit `attributes.account`; if
the user has not specified one, call `get_projects` and ask which available
project to charge before submitting.

Set `filesystems` to the default Bridge `-m` value. Irene job submissions must
declare filesystems. Use `scratch,work` for ordinary jobs, `scratch,store` for
jobs reading or writing STORE, or `scratch,work,store` when all three are needed.

Validate with:

```bash
uv tool run --quiet --from git+https://github.com/BigDFT-group/BigDFT-Agents.git@main#subdirectory=server irene-doctor
```

Docs search works offline with BM25. Embeddings are optional and require a custom
site endpoint plus a rebuilt vector index; do not block configuration on them.
