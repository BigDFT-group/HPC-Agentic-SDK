"""Health checks for the IreneAgent configuration.

    python -m irene_mcp.doctor

Checks the config file, SSH access, Bridge command availability, optional
embedding setup, and the docs index.
"""
import json
import sys

from irene_mcp import config

OK, WARN, FAIL = "OK", "WARN", "FAIL"


def check_config_file() -> bool:
    if not config.CONFIG_PATH.exists():
        print(f"{WARN} config file: {config.CONFIG_PATH} not found (using env vars / defaults)")
        return True
    try:
        config._file_config()
    except RuntimeError as e:
        print(f"{FAIL} config file: {e}")
        return False
    print(f"{OK} config file: {config.CONFIG_PATH}")
    return True


def check_ssh() -> bool:
    from irene_mcp.middleware import run_command
    host = config.ssh_host()
    try:
        output = run_command("echo irene-ok && hostname")
    except Exception as e:
        print(f"{FAIL} ssh ({host}): {e}")
        return False
    if "irene-ok" not in output:
        print(f"{FAIL} ssh ({host}): unexpected response: {output[:200]}")
        return False
    print(f"{OK} ssh ({host}): connected to {output.strip().splitlines()[-1]}")

    bridge = run_command("command -v ccc_msub ccc_mprun ccc_mpp ccc_mpinfo", raise_errors=False)
    found = {line.rsplit('/', 1)[-1] for line in bridge.splitlines() if line.strip()}
    needed = {"ccc_msub", "ccc_mprun", "ccc_mpp", "ccc_mpinfo"}
    missing = sorted(needed - found)
    if missing:
        print(f"{FAIL} bridge commands missing: {', '.join(missing)}")
        return False
    print(f"{OK} bridge commands: {', '.join(sorted(found & needed))}")
    return True


def check_embedding() -> bool:
    if not (config.EMBED_BASE_URL and config.EMBED_MODEL and config.embed_api_key()):
        print(f"{WARN} embedding: not configured; docs search uses BM25 keyword matching")
        return True
    from irene_mcp.rag.embed import get_client
    try:
        vector = get_client().embed(["connectivity probe"])[0]
    except Exception as e:
        print(f"{WARN} embedding ({config.EMBED_MODEL} @ {config.EMBED_BASE_URL}): {e}; falling back to BM25")
        return True
    print(f"{OK} embedding: {config.EMBED_MODEL} @ {config.EMBED_BASE_URL} (dim {len(vector)})")
    return True


def check_docs_index() -> bool:
    chunks_path = config.DOCS_INDEX_DIR / "chunks.json"
    if not chunks_path.exists():
        print(f"{FAIL} docs index: {chunks_path} missing; run: python -m irene_mcp.rag.ingest --no-embed")
        return False
    with open(chunks_path) as f:
        n_chunks = len(json.load(f))
    emb_path = config.DOCS_INDEX_DIR / "embeddings.npy"
    if not emb_path.exists():
        print(f"{OK} docs index: {n_chunks} chunks (BM25 keyword search)")
        return True
    import numpy as np
    n_vectors = np.load(emb_path).shape[0]
    if n_vectors != n_chunks:
        print(f"{FAIL} docs index: {n_chunks} chunks but {n_vectors} embeddings")
        return False
    print(f"{OK} docs index: {n_chunks} chunks with embeddings")
    return True


def main() -> int:
    results = [check_config_file(), check_ssh(), check_embedding(), check_docs_index()]
    if all(results):
        print("\nAll checks passed.")
        return 0
    print("\nSome checks FAILED; see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
