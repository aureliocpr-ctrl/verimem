# Mappa di `verimem/gateway_audit.py` — 11 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/gateway_audit.py:33` `audit_enabled` | funzione: ``ENGRAM_GATEWAY_AUDIT_LOG`` overrides the ``create_app`` default. A memory | `verimem/gateway.py:883`; `verimem/gateway.py:886`; `verimem/gateway_audit.py:30` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/gateway_audit.py:42` `_utc_day` | funzione: (nessun docstring) | `verimem/gateway_audit.py:60` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/gateway_audit.py:46` `_iso_now` | funzione: (nessun docstring) | `verimem/gateway_audit.py:95` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/gateway_audit.py:50` `JsonlAuditSink` | classe: Thread-safe, append-only JSONL writer with per-UTC-day rotation. One line | `verimem/gateway.py:883`; `verimem/gateway.py:890`; `verimem/gateway_audit.py:30` | nessuno | - | NON MISURATO | - |
| 5 | `verimem/gateway_audit.py:54` `JsonlAuditSink.__init__` | funzione: (nessun docstring) | `verimem/_compat.py:27`; `verimem/client.py:355`; `verimem/document_index.py:255` (+11) | `tests/perf/seed_data.py`; `tests/security/test_pentest_validation.py`; `tests/test_abstention_hybrid.py` (+265) | - | NON MISURATO | - |
| 6 | `verimem/gateway_audit.py:59` `JsonlAuditSink.path_for_today` | funzione: (nessun docstring) | `verimem/gateway_audit.py:65` | nessuno | - | NON MISURATO | - |
| 7 | `verimem/gateway_audit.py:62` `JsonlAuditSink.__call__` | funzione: (nessun docstring) | nessuno trovato | `tests/test_claude_cli_model_arg.py`; `tests/test_daemon_runner.py`; `tests/test_il_quarto_canale_di_scrittura.py` (+3) | - | NON MISURATO | - |
| 8 | `verimem/gateway_audit.py:69` `AccessAuditMiddleware` | classe: ASGI middleware: emit one access record per HTTP request via ``sink``. | `verimem/gateway.py:883`; `verimem/gateway.py:889`; `verimem/gateway_audit.py:30` | nessuno | - | NON MISURATO | - |
| 9 | `verimem/gateway_audit.py:73` `AccessAuditMiddleware.__init__` | funzione: (nessun docstring) | `verimem/_compat.py:27`; `verimem/client.py:355`; `verimem/document_index.py:255` (+11) | `tests/perf/seed_data.py`; `tests/security/test_pentest_validation.py`; `tests/test_abstention_hybrid.py` (+265) | - | NON MISURATO | - |
| 10 | `verimem/gateway_audit.py:77` `AccessAuditMiddleware.__call__` | funzione: (nessun docstring) | nessuno trovato | `tests/test_claude_cli_model_arg.py`; `tests/test_daemon_runner.py`; `tests/test_il_quarto_canale_di_scrittura.py` (+3) | - | NON MISURATO | - |
| 11 | `verimem/gateway_audit.py:86` `AccessAuditMiddleware.__call__.send_wrapper` | funzione: (nessun docstring) | `verimem/gateway.py:789`; `verimem/gateway_audit.py:92` | nessuno | - | NON MISURATO | - |
