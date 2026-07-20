"""TGCC Irene documentation-search MCP server — thin wrapper over hpc_agent_core.

Read-only, needs no SSH access. All the actual logic lives in
hpc_agent_core.docs_server.build(); this module just registers Irene's
settings (importing irene_mcp.config for its side effect) and serves.
"""
from mcp.server.fastmcp import FastMCP

from hpc_agent_core.docs_server import build
from hpc_agent_core.serving import serve
from irene_mcp import config  # noqa: F401 -- registers via configure()

mcp = FastMCP("irene-docs")
build(mcp)


def main():
    serve(mcp)


if __name__ == "__main__":
    main()
