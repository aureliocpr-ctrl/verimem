# Mappa di `verimem/_singleton_guard.py` — 4 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/_singleton_guard.py:42` `_is_engram_mcp_cmdline` | funzione: True iff ``cmdline`` is an engram/hippo MCP *server* invocation. | `verimem/_singleton_guard.py:59`; `verimem/_singleton_guard.py:88` | `tests/test_singleton_guard.py` | - | NON MISURATO | - |
| 2 | `verimem/_singleton_guard.py:51` `_select_orphan_pids` | funzione: Pure selection: given ``procs`` = iterable of | `verimem/_singleton_guard.py:96` | `tests/test_singleton_guard.py` | - | NON MISURATO | - |
| 3 | `verimem/_singleton_guard.py:66` `_import_psutil` | funzione: Return the psutil module, or None if unavailable (indirection for tests). | `verimem/_singleton_guard.py:78` | `tests/test_singleton_guard.py` | - | NON MISURATO | - |
| 4 | `verimem/_singleton_guard.py:75` `reap_orphan_mcp_servers` | funzione: Terminate orphaned sibling `engram mcp` servers. Returns the reaped pids | `verimem/mcp_server.py:15774`; `verimem/mcp_server.py:15775` | `tests/test_singleton_guard.py` | - | NON MISURATO | - |
