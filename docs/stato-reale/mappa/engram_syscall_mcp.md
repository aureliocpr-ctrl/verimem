# Mappa di `verimem/engram_syscall_mcp.py` — 8 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/engram_syscall_mcp.py:32` `_have_mcp_sdk` | funzione: (nessun docstring) | `verimem/engram_syscall_mcp.py:207` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/engram_syscall_mcp.py:42` `tool_engram_invoke_recall` | funzione: Typed engram recall via syscall_bridge. | `verimem/engram_syscall_mcp.py:122` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/engram_syscall_mcp.py:56` `tool_engram_invoke_mesh_query` | funzione: Publish a query on the mesh recall channel (vec_bus broadcast). | `verimem/engram_syscall_mcp.py:140` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/engram_syscall_mcp.py:68` `tool_engram_invoke_mesh_fetch` | funzione: Fetch recent mesh messages on a channel. | `verimem/engram_syscall_mcp.py:159` | nessuno | - | NON MISURATO | - |
| 5 | `verimem/engram_syscall_mcp.py:82` `tool_engram_invoke_audit_tail` | funzione: Read last N entries from verimem syscall audit JSONL. | `verimem/engram_syscall_mcp.py:173` | nessuno | - | NON MISURATO | - |
| 6 | `verimem/engram_syscall_mcp.py:88` `tool_engram_dashboard` | funzione: Render engram dashboard widget. | `verimem/engram_syscall_mcp.py:190` | nessuno | - | NON MISURATO | - |
| 7 | `verimem/engram_syscall_mcp.py:195` `get_tool_definitions` | funzione: Return tool defs for any MCP-compatible host to register. | `verimem/engram_syscall_mcp.py:223` | nessuno | - | NON MISURATO | - |
| 8 | `verimem/engram_syscall_mcp.py:203` `main` | funzione: Standalone entry: print tool definitions as JSON (for inspection) | `verimem/_hang_watchdog.py:18`; `verimem/_import_lock.py:7`; `verimem/_singleton_guard.py:34` (+95) | `tests/conftest.py`; `tests/perf/bench.py`; `tests/perf/bench_briefing_v3_robustness.py` (+111) | `README.md:50`; `README.md:66`; `README.md:378` | NON MISURATO | - |
