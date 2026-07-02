"""MCP server for searching the TGCC Irene guide.

Read-only and needs no SSH access. Uses the pre-built packaged index in
irene_mcp/data/docs_index (built from irene_mcp/data/irene_guide.md, an
original orientation guide). Search is BM25
keyword matching by default; if an embedding endpoint is configured and the index
has vectors, semantic search is used instead, with fallback to keyword search.
"""
from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from irene_mcp import config
from irene_mcp.rag.store import DocsIndex
from irene_mcp.serving import serve

mcp = FastMCP("irene-docs")


@lru_cache(maxsize=1)
def _index() -> DocsIndex:
    return DocsIndex(config.DOCS_INDEX_DIR)


def _format(result: dict) -> str:
    return (f"## {result['breadcrumb']}\n"
            f"Source: {result['url']}\n\n"
            f"{result['text']}")


@mcp.tool()
def search_docs(query: str, top_k: int = 4) -> str:
    """Search the TGCC Irene documentation guide.

    Always call this first before answering any question about Irene specifics:
    partitions, Bridge job submission, projects/accounts, storage, login procedure,
    module names, or any machine-specific detail. Do not rely on prior knowledge
    or the orientation facts embedded in skills — those are fallback aids, not
    authoritative. The guide is the source of truth.

    If this tool errors or returns no results, fall back to the inline facts in
    the active skill and note that docs were unavailable.

    When results begin with `[search_method: bm25]`, inform the user that
    keyword search was used because the embedding server could not be reached.
    Results may miss semantically relevant sections that don't share exact
    keywords with the query.

    Args:
        query: Natural-language question or keywords.
        top_k: Number of sections to return.
    """
    results = _index().search(query, top_k=top_k)
    if not results:
        return "No matching documentation sections found."
    sections = "\n\n---\n\n".join(_format(r) for r in results)
    if results[0]["method"] == "bm25":
        return f"[search_method: bm25]\n\n{sections}"
    return sections


@mcp.tool()
def list_doc_sections() -> str:
    """List every section of the Irene guide (table of contents)."""
    lines = [f"- {c['breadcrumb']}  ({c['url']})" for c in _index().chunks]
    return "\n".join(lines)


@mcp.tool()
def read_doc_section(breadcrumb: str) -> str:
    """Read one documentation section in full by its breadcrumb.

    Args:
        breadcrumb: Section path as shown by list_doc_sections or search_docs,
            e.g. 'Welcome > Usage > Submit a batch job'. Partial matches work.
    """
    needle = breadcrumb.lower()
    matches = [c for c in _index().chunks if needle in c["breadcrumb"].lower()]
    if not matches:
        return f"No section matching '{breadcrumb}'. Use list_doc_sections to see all sections."
    return "\n\n---\n\n".join(_format(c) for c in matches)


def main():
    serve(mcp)


if __name__ == "__main__":
    main()
