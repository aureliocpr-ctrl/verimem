# G2 — install-from-scratch transcript (2026-07-04)

Machine: Windows 11, Python 3.13 (venv from miniconda base). Evidence for
RELEASE_GATE G2. Every step below was executed live; outputs are verbatim
(trimmed to the relevant lines).

## Steps

1. **Build wheel** from the repo (packaging itself under test):
   `python -m build --wheel` → `Successfully built hippoagent-0.3.0-py3-none-any.whl`
2. **Virgin venv**: `python -m venv fresh_venv` → pip 26.1.2.
3. **Install the wheel** (downloads all deps: torch CPU, sentence-transformers,
   fastapi, mcp, …): exit 0, no resolver conflicts.
4. **Import + SDK smoke** (temp DB):
   - `import engram` → OK, `__version__ 0.3.0`
   - `Memory(path=tmp).add("The team's favorite benchmark is HaluMem.")`
     → `{'stored': True, 'status': 'model_claim'}`
   - `add("Everything works perfectly and is fully verified.")`
     → `{'stored': True, 'status': 'quarantined'}` — **the anti-confab gate
     fires in a fresh install with zero configuration** (unsupported
     "it works/verified" claim downgraded).
   - `search("favorite benchmark")` → 1 hit, carries
     `grounding_score / id / score / status / text / topic` (provenance on
     reads, as documented).
5. **CLI entrypoints**: `engram.exe --help` and `hippo.exe` both installed and run.
6. **MCP stdio server**: `engram mcp` + JSON-RPC `initialize` handshake.
   - **BUG FOUND (first wheel)**: structlog lines interleaved on stdout with
     JSON-RPC frames (`mcp_preload_using_shared_daemon`, …). Root cause:
     `cli.py` imports observability at module top → stdout logger configured
     before `mcp_server`'s `HIPPO_LOG_STDERR` default could apply on the
     `engram mcp` path (the documented one). Direct
     `python -m engram.mcp_server` was unaffected.
   - **Fix**: `observability.route_logs_to_stderr()` called by the `mcp` CLI
     command before the server import. TDD:
     `tests/test_mcp_stdout_purity_g2.py` (red on the old path, green after).
   - **Re-verified on the rebuilt wheel**: initialize response with
     stdout protocol-pure → `MCP initialize OK (stdout puro): engram 1.28.1`.

## Declared limits / follow-ups
- The venv shared the machine's HF model cache: model download UX on a truly
  empty machine is **G8**, not covered here.
- Cosmetic: MCP `serverInfo.version` reports the server's own versioning
  (1.28.1) while the package is 0.3.0 — harmonize at the G7 rename.
- First wheel took the full dependency download (torch CPU ~stack); document
  expected install size in the public README (G6).

**Verdict: G2 PASS** (install → SDK with gate live → CLI → MCP protocol-pure),
with one real bug found and fixed by the gate itself.
