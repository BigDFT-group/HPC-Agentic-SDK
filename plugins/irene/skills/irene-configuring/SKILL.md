---
name: irene-configuring
description: Use when the user wants to set up, configure, or troubleshoot IreneAgent, including SSH access, default TGCC project/account, filesystem defaults, optional docs embeddings, or ~/.irene/config.json.
---

# Configuring IreneAgent

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

Ask how the user reaches Irene. Prefer an existing SSH alias from `~/.ssh/config`;
otherwise use the TGCC-provided `user@host` destination. If SSH requires a
password, set `ssh.passfile` to the local file containing it, such as
`/tmp/irene`. Access details are in site/project documentation, not in the public
guide.

Ask for the default project ID used with Bridge `-A`. Irene requires a project
for job submission. A JobSpec can still override it per job with
`attributes.account`.

Set `filesystems` to the default Bridge `-m` value. Irene job submissions must
declare filesystems. Use `scratch,work` for ordinary jobs, `scratch,store` for
jobs reading or writing STORE, or `scratch,work,store` when all three are needed.

Validate with:

```bash
uv tool run --quiet --from git+https://github.com/CEA-HPC/Irene-Agent.git@main#subdirectory=server irene-doctor
```

Docs search works offline with BM25. Embeddings are optional and require a custom
site endpoint plus a rebuilt vector index; do not block configuration on them.
