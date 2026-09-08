# Mappa di `verimem/capability_token.py` — 6 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/capability_token.py:65` `_load_secret` | funzione: Load HMAC secret. Prefer A2A bus secret, then ghost, then dedicated. | `verimem/capability_token.py:100` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/capability_token.py:78` `_canonical_body` | funzione: Order-sensitive canonical body for HMAC. | `verimem/capability_token.py:130` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/capability_token.py:98` `_compute_hmac` | funzione: HMAC-SHA256 (32 bytes). | `verimem/capability_token.py:131`; `verimem/capability_token.py:215` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/capability_token.py:103` `issue_token` | funzione: Issue a capability token for (peer_id, op) with TTL. | `verimem/capability_token.py:33`; `verimem/capability_token.py:43` | `tests/test_capability_token.py`; `tests/test_engram_stack_e2e.py` | - | NON MISURATO | - |
| 5 | `verimem/capability_token.py:140` `decode_token_unsafe` | funzione: Decode token WITHOUT verification (diagnostic only). | `verimem/capability_token.py:40`; `verimem/capability_token.py:221` | nessuno | - | NON MISURATO | - |
| 6 | `verimem/capability_token.py:171` `verify_token` | funzione: Verify a capability token. | `verimem/capability_token.py:36`; `verimem/capability_token.py:43`; `verimem/capability_token.py:44` (+5) | `tests/test_capability_token.py` | - | NON MISURATO | - |
