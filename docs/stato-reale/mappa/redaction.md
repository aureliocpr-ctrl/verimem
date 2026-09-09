# Mappa di `verimem/redaction.py` — 4 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/redaction.py:19` `_assigned_repl` | funzione: (nessun docstring) | `verimem/redaction.py:86`; `verimem/redaction.py:110` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/redaction.py:24` `_dburl_repl` | funzione: (nessun docstring) | `verimem/redaction.py:60` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/redaction.py:29` `_aws_secret_repl` | funzione: (nessun docstring) | `verimem/redaction.py:65` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/redaction.py:114` `redact_secrets` | funzione: Maschera i segreti in ``text``. Ritorna ``(text_redatto, n_redazioni)``. | `verimem/conversation_ingest.py:317`; `verimem/conversation_ingest.py:381`; `verimem/document_promote.py:53` (+19) | `tests/security/test_redaction_on_write_e2e.py`; `tests/test_redaction.py`; `tests/test_redaction_audit_mod12.py` (+6) | - | NON MISURATO | - |
