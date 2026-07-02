"""Live smoke test for Irene MCP servers over stdio.

Usage: python tests/smoke.py [--job]
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_DIR = Path(__file__).resolve().parent.parent
RUN_SH = SERVER_DIR / "run.sh"


async def call(session: ClientSession, tool: str, args: dict | None = None) -> str:
    result = await session.call_tool(tool, args or {})
    text = "\n".join(c.text for c in result.content if c.type == "text")
    status = "ERROR" if result.isError else "ok"
    print(f"--- {tool} [{status}] ---\n{text[:1200]}\n")
    if result.isError:
        raise RuntimeError(f"{tool} failed: {text}")
    return text


async def docs_checks() -> None:
    params = StdioServerParameters(command=str(RUN_SH), args=["irene_mcp.docs_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"irene-docs tools: {[t.name for t in (await session.list_tools()).tools]}\n")
            await call(session, "search_docs", {"query": "submit MPI job Bridge ccc_msub", "top_k": 2})


async def hpc_checks(submit: bool) -> None:
    params = StdioServerParameters(command=str(RUN_SH), args=["irene_mcp.hpc_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"irene-hpc tools: {[t.name for t in (await session.list_tools()).tools]}\n")

            await call(session, "get_facility")
            await call(session, "get_resources")
            await call(session, "get_resource", {"resource_id": "irene"})
            await call(session, "get_projects")
            await call(session, "get_job_statuses", {"job_ids": []})
            await call(session, "fs_ls", {"path": "."})

            if not submit:
                return

            spec = {
                "name": "irene-smoke",
                "executable": "hostname && echo BRIDGE_MSUB_JOBID=$BRIDGE_MSUB_JOBID",
                "attributes": {"duration": 300, "queue_name": "rome"},
                "resources": {"process_count": 1},
            }
            out = await call(session, "submit_job", {"spec": spec})
            job_id = json.loads(out)["job_id"]
            print(f">>> submitted job {job_id}; polling...\n")

            state = "unknown"
            job = None
            for _ in range(20):
                status_text = await call(session, "get_job_status", {"job_id": job_id})
                job = json.loads(status_text)
                state = job["status"]["state"]
                if state in ("completed", "failed", "canceled"):
                    break
                await asyncio.sleep(15)

            assert state == "completed", f"job ended {state}"
            workdir = (job["status"].get("meta_data") or {}).get("workdir", ".")
            await call(session, "fs_tail", {"path": f"{workdir}/irene_{job_id}.o", "lines": 20})


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", action="store_true", help="Submit and verify a tiny real job.")
    args = parser.parse_args()
    await docs_checks()
    await hpc_checks(submit=args.job)
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
