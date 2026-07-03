---
name: remotemanager-dataset-promotion
description: Use when a validated Python function must be transformed into a remote-executable workflow using remotemanager's Dataset API instead of SanzuFunction. Covers Computer validation, Dataset construction, run appending, file staging, Dataset.run/wait/fetch_results, cleanup, and preservation of a JSON-serializable return path for agentic workflows.
---

# Remotemanager Dataset Promotion

Use this skill when the task is to turn an already validated Python function into a remote-executable workflow using `remotemanager.Dataset`.

This skill is specifically for the Dataset API, not `SanzuFunction`.

## MCP vs direct Python use

When using the `remotemanager-MCP` server, the Dataset lifecycle is managed
through MCP tools rather than Python calls:

| Python Dataset API | Equivalent MCP tool |
|--------------------|---------------------|
| `Dataset(...)` | `create_campaign` |
| `ds.append_run(args)` | `append_campaign_run` |
| `ds.run()` | `run_campaign` |
| `ds.wait()` | `wait_campaign` |
| `ds.fetch_results()` | `fetch_campaign_results` |
| `ds.results` / `ds.errors` | `get_campaign_results` |

Use the Python API in this skill when writing code that operates outside the
MCP server boundary, for example standalone scripts, notebooks, or server
extensions.

## Scope

Assume the source function already exists and has already been scientifically validated.

The goal is to build a repeatable Dataset lifecycle:

1. define the function,
2. define and validate the machine connection,
3. construct a `Dataset`,
4. append one or more runs,
5. launch with `run()`,
6. wait for completion,
7. collect outputs with `fetch_results()`,
8. read `results` and `errors`.

## Preconditions

Before using `Dataset`, verify the source function satisfies these constraints:

- The function has explicit keyword arguments.
- The function can run on the remote machine with the available Python environment.
- The return value is JSON-serializable or already converted to Python intrinsic objects.
- Any required input files are known explicitly.

Preferred return types:

- `dict`
- `list`
- `tuple` containing only intrinsic serializable values
- `str`, `int`, `float`, `bool`, `None`

Avoid returning:

- open file handles
- generators
- raw custom objects without explicit serialization
- arrays or classes that are not serialized first

## Step 1: keep the function plain

Do not embed scheduler logic, host selection, or tool protocol logic inside the scientific function.

The scientific helper should remain a plain Python function that can still be tested locally.

## Step 2: define the target machine with `Computer`

When the target is an HPC system or another controlled remote resource, use `Computer` as the Dataset `url`.

The template should define:

- scheduler directives,
- environment setup,
- exposed parameters such as `nodes`, `mpi`, `omp`, and `time`.

Example:

```python
from remotemanager import Computer

machine = Computer(
    template=template,
    host="cluster.example.org",
    submitter="sbatch",
    python="python3",
    shell="bash",
)
machine.nodes = 1
machine.mpi = 4
machine.omp = 8
```

Use a plain `URL(...)` only when no scheduler abstraction is needed.

## Step 3: validate the machine before building a Dataset

Before creating the `Dataset`, validate the remote execution substrate.

The first check should be `machine.test_connection()`.

Pattern:

```python
status = machine.test_connection(verbose=True)
print(status)
```

Use this check to verify:

- the host can be reached,
- credentials are present,
- the remote Python is callable,
- the selected transport is appropriate,
- the job submission path is coherent.

For localhost-only examples, also confirm that the transport choice is intentional. If `rsync` is unavailable, switching to a copy-based transport is acceptable, but do not force that transport for remote hosts.

If `test_connection()` fails, do not proceed to Dataset construction until the failure is understood.

## Step 4: build the Dataset

Construct the Dataset from the function and the validated target machine.

Common arguments:

- `function`: the validated function object
- `url`: a `Computer` or `URL`
- `name`: stable Dataset name
- `skip`: whether an existing dbfile should be reused
- `local_dir`: local staging directory
- `remote_dir`: remote working directory
- `extra_files_send`: files sent with all runs
- `extra_files_recv`: files retrieved from all runs
- `script`, `submitter`, `shell`: execution configuration when needed

Recommended development default:

```python
ds = Dataset(
    function=my_validated_function,
    url=machine,
    name="my_dataset",
    local_dir="temp_dataset_local",
    remote_dir="temp_dataset_remote",
    skip=False,
)
```

Use `skip=False` while developing. Use the default skip behavior only after the workflow is stable and rerun reuse is desired.

## Step 5: append runs explicitly

A Dataset is a container for one or more runs. Each run corresponds to one set of arguments for the function.

Append runs with `append_run()`.

Example:

```python
ds.append_run({"a": 1, "b": 2})
ds.append_run({"a": 5, "b": 7, "mode": "fast"})
```

Important `append_run()` options:

- `args` or direct first dict argument: function arguments
- `name`: explicit runner name
- `extra_files_send`: per-run input files
- `extra_files_recv`: per-run files to collect
- `skip`: skip duplicate runner insertion if possible
- `force`: force insertion
- `lazy`: defer db updates for many appends
- `extra`: inject extra jobscript text for this runner
- `return_runner=True`: return the inserted runner object

If appending many runs, prefer:

```python
with ds.lazy_append() as la:
    for run in runs:
        la.append_run(run)
```

## Step 6: handle external files explicitly

If the function depends on input files, do not pass local absolute paths directly into the remote execution environment.

Instead:

1. stage files through `extra_files_send`,
2. pass only the remote-visible filename or basename into the function.

Pattern:

```python
import os

local_input = "/path/to/input.xyz"
remote_input = os.path.basename(local_input)

ds = Dataset(
    function=my_validated_function,
    url=machine,
    extra_files_send=[local_input],
    skip=False,
)

ds.append_run({"input_file": remote_input})
```

Use `extra_files_recv` when the remote function generates files that must be pulled back after completion.

## Step 7: launch with `run()`

Call `Dataset.run()` after all desired runs are appended.

Example:

```python
ds.run()
```

Important launch options include:

- `force`: rerun even if checks would skip execution
- `dry_run`: generate files and launch command without executing remotely
- `verbose`: local verbosity
- `uuids`: run only selected runners
- `extra`: extra text inserted into runner jobscripts

When moving from machine validation to first remote execution, `dry_run=True` is a good intermediate check.

## Step 8: wait for completion and fetch results

Dataset execution is commonly asynchronous. After `run()`, use `wait()` if the workflow should block until completion.

```python
ds.wait(interval=5, timeout=600)
ds.fetch_results()
print(ds.results)
print(ds.errors)
```

Useful `wait()` options:

- `interval`: polling interval in seconds
- `timeout`: hard timeout in seconds
- `watch=True`: print runner states continuously
- `success_only=True`: wait until all runs succeed
- `only_runner=runner`: wait for a single runner
- `force=True`: raise dataset-level failures more aggressively

## Recommended validation order

Use this sequence when promoting a function:

1. test the function locally,
2. build the `Computer`,
3. call `Computer.test_connection()`,
4. create the `Dataset`,
5. append one minimal run,
6. try `run(dry_run=True)` if appropriate,
7. run the real job,
8. fetch and inspect results.

Do not skip step 3. A broken `Computer` definition makes all later Dataset behavior harder to interpret.
