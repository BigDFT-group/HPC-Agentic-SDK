# IreneAgent — Agent Instructions

IreneAgent provides two MCP servers: `irene-hpc` for live cluster interaction and
`irene-docs` for the built-in Irene guide. The server package is under
`server/irene_mcp`; plugin payload is under `plugins/irene`.

## Design Rules

- Keep the IRI-shaped tool surface in `hpc_server.py` unless the checklist is updated.
- All cluster I/O goes through `middleware.run_command` or `write_remote_file`.
- Runtime data must be packaged under `server/irene_mcp/data`.
- Workflow guidance belongs in `plugins/irene/skills`, not long tool docstrings.
- Do not print to stdout from server code; MCP stdio uses stdout.

## Irene Facts

- Irene is CPU-first. Default normal jobs to `rome`.
- Batch scripts use TGCC Bridge `#MSUB` directives and submit with `ccc_msub`.
- Parallel work launches with `ccc_mprun`.
- Job submissions require `-q <partition>`, `-A <project>`, and `-m <filesystems>`.
- Live status comes from Bridge commands such as `ccc_mpinfo`, `ccc_mpp`, `ccc_mstat`, `ccc_macct`, `ccc_mqinfo`, `ccc_compuse`, and `ccc_myproject`.
- Do not encourage frequent scheduler polling; TGCC prohibits `watch` on scheduler commands.

## Docs Index

The guide is `server/irene_mcp/data/irene_guide.md`. Rebuild the BM25 index with:

```bash
cd server
python -m irene_mcp.rag.ingest --no-embed
```

Embeddings are optional and not committed by default for this port.

## Development

```bash
cd server
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m irene_mcp.doctor
.venv/bin/python tests/smoke.py
```

`tests/smoke.py --job` submits a real job and consumes allocation time.
