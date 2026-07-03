---
name: remotemanager-configuring
description: Use when setting up or troubleshooting the RemoteManager plugin for first use, especially the user-local ~/.config/remotemanager-mcp/config.yaml, function registry, machine database, overrides, runtime roots, and MCP startup behavior.
---

# Configuring RemoteManager Plugin

## How the plugin works

The marketplace plugin starts `remotemanager-generic-mcp` and does not pass
user-specific environment variables. All user-specific information must live in
a local config file. The default config path is:

```text
~/.config/remotemanager-mcp/config.yaml
```

Set `REMOTEMANAGER_MCP_CONFIG` only when a non-default config file is needed.

## Step-by-step first-use setup

### 1. Create the config directory and machine database directory

```bash
mkdir -p ~/.config/remotemanager-mcp/machines
```

### 2. Create `~/.config/remotemanager-mcp/config.yaml`

```yaml
function_registry: ~/.config/remotemanager-mcp/function-registry.yaml
machine_db: ~/.config/remotemanager-mcp/machines
overrides: ~/.config/remotemanager-mcp/user-overrides.local.yaml
runtime_root: /tmp/remotemanager-mcp-runtime
remote_root: /scratch/$USER/remotemanager-mcp
```

- `function_registry`: YAML file listing callable functions the server exposes.
- `machine_db`: directory containing one YAML file per machine.
- `overrides`: optional per-user overlay applied after the machine database is loaded.
- `runtime_root`: local directory for generated scripts, manifests, and fetched results.
- `remote_root`: default remote working-directory root for non-localhost platforms when no explicit `remote_dir` is given.

### 3. Create the function registry

`~/.config/remotemanager-mcp/function-registry.yaml` must contain a top-level
`functions` mapping. Each entry names the Python module and callable to expose:

```yaml
functions:
  square:
    module: remotemanager_mcp.sample_functions
    function: square
    description: Return the square of a numeric input.
    file_args: []

  cube:
    module: remotemanager_mcp.sample_functions
    function: cube
    description: Return the cube of a numeric input.
    file_args: []
```

The built-in `remotemanager_mcp.sample_functions` module provides `square` and
`cube` for testing. Replace or extend with your own module entries.

`file_args` lists argument names whose values are local file paths that must be
staged to the remote machine before execution.

### 4. Create at least one machine YAML file

The machine database directory must contain one `.yaml` file per host.
A minimal localhost file for testing:

`~/.config/remotemanager-mcp/machines/localhost.yaml`

```yaml
frontend_template: |
  #!/bin/bash

cpu_compile:
  python_interpreter: python3

platforms:
  frontend:
    host: localhost
    submitter: bash
    kwargs:
      template: frontend_template
```

This defines:
- one platform: `frontend` (local bash execution)
- one application: `cpu_compile` (uses system `python3`)

For a remote HPC machine, see the machine-database skill.

### 5. Create the overrides file (optional but recommended for remote machines)

`~/.config/remotemanager-mcp/user-overrides.local.yaml` carries credentials
and per-user settings that should not be committed to shared machine files:

```yaml
localhost:
  platform:
    shell: bash

irene:
  platform:
    transport: scp
    passfile: /tmp/irene
  application:
    remote_runtime_root: /scratch/$USER/remotemanager-mcp
  combined:
    project: gen12345
```

If `overrides` is omitted from `config.yaml`, the server automatically loads
`user_overrides.yaml` from the machine database directory when it exists.

## Verifying the setup

Once the MCP server is active, run these tools in order:

1. `describe_server_config` — reports which config file was loaded, which keys
   are set, and the resolved paths. Use this first when something is not working.
   It does not expose file contents or credentials.

2. `list_functions` — confirms the function registry is readable and shows all
   registered callables. Fails with a targeted error if `function_registry` is
   wrong or missing.

3. `list_computers` — enumerates all hosts in the machine database. Fails with
   a targeted error if `machine_db` is wrong or missing.

4. `describe_computer(host, platform, application)` — resolves one
   host/platform/application combination and shows the resulting `Computer`
   spec including overrides. Run this before creating any campaign.

5. `test_campaign_connection` — validates live connectivity for an already
   created campaign.

## Common error messages and fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Missing remotemanager-MCP config file: ~/.config/remotemanager-mcp/config.yaml` | Config file absent | Create it as shown in step 2 |
| `Function registry not found: ...` | `function_registry` path wrong or file missing | Create the function-registry.yaml (step 3) |
| `Machine database not configured` | `machine_db` not set in config | Add `machine_db:` to config.yaml |
| `Machine database directory not found: ...` | Path in `machine_db` does not exist | Create the directory (step 1) |
| `Machine 'X' was not found in database` | No `X.yaml` in machine_db | Add the machine YAML file |
| `Unknown platform 'X' for machine 'Y'` | Platform name not in `platforms:` block of the YAML | Check spelling or add the platform |
| `Unknown application 'X' for machine 'Y'` | Application entry missing from the machine YAML | Add the application entry |
| `Overrides file not found: ...` | `overrides` path in config.yaml does not exist | Create the file or remove the `overrides:` key |
| `campaign_id required because multiple campaigns exist` | Multiple campaigns registered without a selection | Pass `campaign_id` explicitly or call `select_campaign` |

## Configuration precedence

For each setting, the resolution order is:

1. explicit tool argument (e.g., `database_uri` passed to `list_computers`)
2. legacy environment variable (e.g., `REMOTECOMPUTER_DB`)
3. value from `~/.config/remotemanager-mcp/config.yaml`

Legacy environment variables for reference:

- `REMOTEMANAGER_MCP_FUNCTION_REGISTRY`
- `REMOTECOMPUTER_DB`
- `REMOTEMANAGER_MCP_RUNTIME_ROOT`
- `REMOTEMANAGER_MCP_REMOTE_ROOT`
- `REMOTEMANAGER_MCP_OVERRIDES`

Keep the `.mcp.json` manifest free of user paths. Use the config file instead.

## Scope of the generic plugin

- The plugin can run any function declared in the configured function registry.
- The plugin can target any host/platform/application combination in the configured machine database.
- The marketplace owns skill guidance and stable plugin-launch metadata.
- The `remotemanager-MCP` package evolves independently and can be updated without changing the marketplace entry.

For Irene campaigns, do not rely on implicit project defaults. Check available
projects through the Irene plugin or `ccc_compuse`, then pass the selected
project explicitly in `run_options`.
