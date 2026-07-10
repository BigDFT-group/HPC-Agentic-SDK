# BigDFT-Agents — Agent Instructions

This repository is the public marketplace/distribution layer for HPC agentic
plugins. It currently includes:

- `plugins/irene`: TGCC Irene skills and MCP launch metadata.
- `server/irene_mcp`: Python implementation for the Irene MCP servers — a
  thin machine-specific skin over
  [`hpc-agent-core`](https://github.com/william-dawson/hpc-agent-core),
  which provides the generic runtime (SSH middleware, PSI/J-style job
  models, health checks, the docs RAG pipeline, MCP serving glue). The
  general porting process this plugin follows is documented once,
  canonically, in
  [hpc-agent-core's `PORTING.md`](https://github.com/william-dawson/hpc-agent-core/blob/main/PORTING.md)
  — no copy or stub of it lives in this repo. Read it before changing how
  `irene_mcp` wires into core.
- `plugins/remotemanager`: marketplace plugin for the external
  `remotemanager-MCP` Python package.
- `plugins/bigdft`: skills-only plugin for using the BigDFT electronic
  structure code as an end user (install, input generation, PyBigDFT
  systems, pseudopotentials, linear scaling, logfile parsing).
- `plugins/bigdft-dev`: skills-only plugin of developer guides for BigDFT's
  Fortran internals (Futile, ATlab, liborbs, PSolver, KB projectors, the
  input-variable pipeline). Kept separate from `plugins/bigdft` so a user
  running calculations doesn't have to install six library-internals
  skills, and a BigDFT source contributor doesn't get input-file skills
  they don't need.

(Note: this repository has been renamed twice — `HPC-Agentic-SDK` →
`IreneAgent` → `BigDFT-Agents`. Some older external references may still
use an earlier name; GitHub redirects both.)

## Design Rules

- **No write access to `hpc-agent-core`.** Every Irene-specific behavior
  (the Bridge scheduler dialect, TGCC project handling, filesystem
  defaults) lives in `server/irene_mcp/`, reached through `configure()`
  arguments or — since Bridge's `#MSUB`/`ccc_*` dialect doesn't fit
  either of core's ready-made backends — a local `BridgeBackend`
  subclassing `hpc_agent_core.compute.base.SchedulerBackend` directly.
  If you think you need to edit the installed `hpc-agent-core` package,
  you've misdiagnosed the problem — reach for local config, a subclass, or
  simply not using a core module instead.
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

Skill directories and their `name:` frontmatter must be prefixed with the
plugin name (`irene-configuring`, `remotemanager-dataset-promotion`,
`bigdft-install`, `bigdft-dev-futile`), even though the skill is invoked as
`/<plugin>:<skill-name>` and the prefix repeats the plugin name. This keeps
skill names unambiguous when multiple plugins are installed together. If a
plugin's skills split into more than one logical group (for example BigDFT's
end-user vs. Fortran-developer skills), prefer a second plugin over deeper
prefixing or subdirectories — skill discovery expects a flat `skills/*/SKILL.md`
layout, and a second plugin lets users install only the group they need.

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
uv run python -m irene_mcp.ingest --no-embed
```

Embeddings are optional and not committed by default — no shared embedding
endpoint is configured for Irene (`docs_cite_url`/`embed_base_url` are
blank; see `server/irene_mcp/config.py`), so search is BM25-only unless a
site configures its own private endpoint.

### Migrating from a pre-hpc-agent-core config file

If you configured this plugin before it moved onto `hpc-agent-core`, two
things changed:

- `ssh.passfile` moved to `computer.passfile` — the old location is no
  longer read (`hpc_agent_core.middleware` only reads the generic
  `"computer"` object). Anyone using password-file SSH auth needs to move
  this one value; everything else in an existing config file keeps working.
- `account`/`filesystems` still work at their old top-level location, but
  the new preferred location is `defaults.account`/`defaults.filesystems`,
  matching the rest of the family.

```bash
cd server
uv run python -m irene_mcp.doctor
uv run python tests/smoke.py
```

`tests/smoke.py --job` submits a real job and consumes allocation time.

**No live Irene SSH access has been available while working on this repo
recently** (see the hpc-agent-core migration notes below) — `doctor`'s SSH
check and `smoke.py`'s HPC checks are expected to fail cleanly until someone
with real access runs them; that failure alone is not a sign anything here
is broken. See "Validation status" below for exactly what was and wasn't
verified.

## hpc-agent-core migration — validation status

`server/irene_mcp` was moved onto `hpc-agent-core` (`middleware`, the
shared PSI/J-style models, the docs RAG pipeline, `doctor`'s checks, and
serving glue now come from the package; only `config.py`, `compute.py`
(the `BridgeBackend` subclass), `hpc_server.py`, and `data/` are
Irene-specific) **without any live TGCC Irene SSH access available** during
the work. That changes what "verified" means here — be precise about it,
don't imply more than was actually checked:

- **Verified**: package installs and imports cleanly; every MCP tool
  registers with zero config present (the "never fail to start"
  invariant); `search_docs`/`list_doc_sections`/`read_doc_section` work
  fully offline (no SSH); `get_facility` (static, no SSH) works.
- **Verified via behavioral-equivalence rendering** (the substitute for
  live testing when no cluster access exists): the pre-migration
  `BridgeBackend.render_script()` and the new one were run side by side,
  with project-listing mocked identically for both, across six
  representative `JobSpec`s (a plain CPU job, a multi-node exclusive MPI
  job, a GPU job on `v100`, a job with a reservation + environment +
  pre/post-launch lines, a pcocc container job, and a job with explicit
  stdout/stderr paths) — **all six rendered byte-identical `#MSUB`
  scripts**. The status/project-parsing functions
  (`_parse_ccc_mpp`, `_parse_macct`, `_parse_compuse_projects`,
  `_parse_ccc_msub_job_id`) were separately checked against synthetic
  sample output from each and also matched exactly. This is strong
  evidence the migration didn't change behavior, but it is **not** the
  same as a real job actually queuing, running, and completing on Irene.
- **Not verified, and should not be assumed working**: an actual
  `ccc_msub` submission, `ccc_mpp`/`ccc_macct` output against this port's
  parsers on real (not synthetic) Bridge output, `ccc_mpinfo` parsing in
  `get_resources`/`get_resource`, and the SSH/passfile connection path
  itself. Run `doctor` and `tests/smoke.py --job` for real, from a machine
  with actual Irene access, before considering this port finished — per
  hpc-agent-core's `PORTING.md` §9, a clean `doctor` and a green
  behavioral-equivalence check are not proof of that on their own.
- Two decisions made under uncertainty, without live access to confirm
  them independently: `docs_cite_url` was left blank rather than kept as
  the old `https://www-tgcc.ccc.cea.fr/` (matching the rest of the family's
  default — set it back if someone confirms that site is stable/reliable
  enough to cite); and the `ssh.passfile` config-schema change (see above)
  hasn't been exercised against a real password-auth Irene login.
- **A real upstream bug was caught and fixed while regenerating the docs
  index (2026-07-10)**: `python -m irene_mcp.ingest` crashed with
  `httpx.UnsupportedProtocol` when `RCCS_EMBED_API_KEY` happened to be set
  in the environment, because `hpc_agent_core.rag.ingest.build_index()`
  only checked `embed_api_key()` before embedding — and that resolves
  truthy from the shared env fallback regardless of whether *this*
  machine has `embed_base_url` configured at all (Irene's is `""` — see
  `config.py`). Fixed upstream in `hpc-agent-core` 0.4.2 (now the pin's
  floor); Irene's docs index stays BM25-only by design either way, but no
  longer crashes getting there.

## BigDFT Rules

- `plugins/bigdft` and `plugins/bigdft-dev` skills follow the authoring
  conventions from the upstream `bigdft-skills` source repo: YAML
  frontmatter, ask the user one question at a time, auto-detect what's
  possible before asking, include code building blocks as fenced
  Python/Fortran, and use `# FILL` comments for values the agent should
  customize.
- Do not add a RemoteManager connection/dataset skill to `plugins/bigdft` or
  `plugins/bigdft-dev`. That responsibility belongs to `plugins/remotemanager`
  (MCP-backed campaign tools). The upstream `bigdft-skills` repo's `remote`
  and `dataset` skills were intentionally dropped when integrating into this
  marketplace because they duplicated raw-Python RemoteManager guidance that
  `plugins/remotemanager` already covers through MCP tools and machine-database
  conventions. BigDFT-specific remote-execution advice (for example,
  validating input locally with `SystemCalculator(dry_run=True)` before
  submitting) lives in `plugins/remotemanager`'s
  `remotemanager-dataset-promotion` skill instead.

## Refresh Procedure

After pushing marketplace changes, users may need to refresh/reinstall the
marketplace/plugin and start a new session. MCP tools are loaded at session
startup; updating files in the repository does not add tools to an already
running session.
