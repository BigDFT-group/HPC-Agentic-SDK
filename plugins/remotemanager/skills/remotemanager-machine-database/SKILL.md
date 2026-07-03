---
name: remotemanager-machine-database
description: Use when defining or revising machine YAML files and user_overrides.yaml for remotemanager-MCP, including platform/application structure, override layering, and remotemanager template placeholder syntax.
---

# Remotemanager Machine Database

Use this skill when an agent needs to create or update a machine database entry such as `localhost.yaml` or `irene.yaml`, or when it needs to separate official machine data from user-specific overrides.

## Goal

Produce two coherent inputs for the MCP server:

1. a machine YAML file in the machine database directory
2. an optional override file keyed by host name

The machine YAML should describe reusable machine facts. The override file should carry user-specific or site-specific adjustments.

## What belongs where

Put these in the machine YAML:

- scheduler templates
- platform names and connection mode
- generic shell / submitter / host information
- application names
- generic modules, preamble blocks, and interpreter names
- machine- or application-level runtime roots that are broadly valid for users of that machine

Put these in the override file:

- `passfile`
- user-specific `prefix` or install paths
- project/account names
- transport choice when it is user- or environment-dependent
- platform-specific authentication details

Do not put private user credentials or one-off paths in the machine YAML.

## Machine YAML structure

A machine file has three conceptual parts:

1. top-level template strings (referenced by platform entries)
2. application entries (one per named environment)
3. a `platforms:` mapping (one per execution mode)

The filename stem becomes the `host` argument used with MCP tools:
`irene.yaml` → `host="irene"`, `localhost.yaml` → `host="localhost"`.

Minimal pattern:

```yaml
frontend_template: |
  #!/bin/bash
  #command:optional=False:default=ls#

batch_template: |
  #!/bin/bash
  #mpi:optional=False#
  #omp:default=1#
  #time:optional=False#
  #project:optional=False#
  #command:default=#

intel_oneapi_mpi:
  python_interpreter: python
  modules: python3 cmake inteloneapi mpi/intelmpi mkl
  remote_runtime_root: /scratch/$USER/remotemanager-mcp
  sourcedir: /scratch/$USER/project
  preamble: |
    export PREFIX=/scratch/$USER/binaries/current/suite
    source $PREFIX/bin/bigdftvars.sh

platforms:
  frontend:
    host: irene
    submitter: bash
    shell: bash
    kwargs:
      template: frontend_template
  batch:
    host: irene
    submitter: ccc_msub
    shell: bash
    kwargs:
      template: batch_template
```

## Meaning of the sections

- top-level `*_template` strings are referenced from `platforms.*.kwargs.template`; keys ending in `_template` are excluded from application lookup
- top-level application entries such as `intel_oneapi_mpi` are selected by the MCP `application` argument
- `platforms` entries define how the remote `Computer` is instantiated
- `kwargs` is used to inject referenced top-level objects, especially templates; if a `kwargs` value matches a top-level key, the top-level value is substituted

## Minimal localhost example

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

Use `host="localhost"`, `platform="frontend"`, `application="cpu_compile"` when creating campaigns against this file.

## Override file structure

The override file is keyed by host name. The preferred location is either:

- the path set in `config.yaml` under `overrides:`, or
- `user_overrides.yaml` inside the machine database directory (auto-loaded when `overrides` is unset)

The canonical structure uses explicit `platform:`, `application:`, and `combined:` sections:

```yaml
localhost:
  platform:
    shell: bash

irene:
  platform:
    transport: scp
    passfile: /tmp/irene
  application:
    remote_runtime_root: /scratch/$USER/custom-runtime
  combined:
    project: gen12345
```

Semantics:

- `platform:` is recursively merged into the resolved platform specs
- `application:` is recursively merged into the resolved application specs
- `combined:` is merged into the combined platform+application view used for runtime layout and account selection
- plain scalar keys at the host level (e.g. `project: gen12345`) are treated the same as `combined:` entries
- named platform sections (e.g. `frontend:`) and named application sections (e.g. `cpu_compile:`) are also supported and merged into their respective resolved specs

## Template placeholder syntax

`remotemanager` templates use `#...#` placeholders.

Basic forms:

- `#name#`
- `#name:default=value#`
- `#name:optional=False#`
- `#name:default={expr}#`

Common options:

- `default=...` sets a default value
- `optional=False` makes a value required
- `hidden=True` keeps an internal variable out of the rendered script while still allowing dependent expressions
- `format=...` applies a formatter such as time formatting when supported by the template engine
- `requires=foo` declares dependency on another variable
- `static=True` freezes evaluation against later changes

Dynamic defaults use Python-like expressions in braces:

- `#nodes:default={(mpi*omp)/cores_per_node}#`
- `#jobname:default=RUN_{mpi}_{omp}#`

Escaping matters in defaults containing `:` or `=`. Use backslashes when needed.

## Practical template rules

For MCP campaigns, templates should normally expose:

- `command` for frontend execution templates
- scheduler resources such as `mpi`, `omp`, `time`, `nodes` for batch templates
- scheduler/account fields such as `project`, `queue`, `filesystem` when the machine requires them
- optional environment hooks such as `modules`, `module_preload`, `preamble`

The exposed placeholder names become candidate `append_campaign_run(..., run_options=...)` keys through `dataset.url.args`. Use `describe_campaign_options` after campaign creation to see the exact list.

## Authoring checklist

Before finalizing a machine YAML:

1. ensure each platform points to a real template via `kwargs.template`
2. ensure at least one application entry exists
3. ensure the application provides `python_interpreter` if the remote Python is not implicit
4. keep user-specific values out of the machine YAML when possible
5. verify that required template placeholders correspond to the run options the campaign will need
6. use `describe_computer(host, platform, application)` to inspect the resolved spec and applied overrides
7. use `test_campaign_connection` to validate live connectivity before submitting real jobs

## Validation expectations

A valid machine definition should support these MCP tool calls without error:

- `list_computers` — the host appears in the listing
- `describe_computer(host, platform, application)` — resolves cleanly and shows expected overrides
- `create_campaign(function_name, host, platform, application)` — creates the campaign
- `test_campaign_connection` — succeeds for a live configured campaign
