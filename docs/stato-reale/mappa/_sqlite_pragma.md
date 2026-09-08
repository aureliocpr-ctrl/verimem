# Mappa di `verimem/_sqlite_pragma.py` — 5 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/_sqlite_pragma.py:25` `synchronous_mode` | funzione: Return the SQLite ``synchronous`` level: 'NORMAL' (default) or 'FULL'. | `verimem/_sqlite_pragma.py:177`; `verimem/entity_kg.py:519`; `verimem/entity_kg.py:520` (+8) | `tests/test_gateway_profile.py`; `tests/test_sqlite_synchronous_knob.py` | - | NON MISURATO | - |
| 2 | `verimem/_sqlite_pragma.py:74` `read_connection` | funzione: A per-thread, reused, READ-ONLY connection. | `verimem/_sqlite_pragma.py:177`; `verimem/entity_kg.py:35`; `verimem/entity_kg.py:622` (+16) | `tests/test_read_connection_is_reused.py` | - | NON MISURATO | - |
| 3 | `verimem/_sqlite_pragma.py:153` `_usable` | funzione: Whether a cached connection still answers. | `verimem/_sqlite_pragma.py:127` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/_sqlite_pragma.py:162` `_drop` | funzione: (nessun docstring) | `verimem/_sqlite_pragma.py:132`; `verimem/_sqlite_pragma.py:149` | nessuno | - | NON MISURATO | - |
| 5 | `verimem/_sqlite_pragma.py:168` `close_read_connections` | funzione: Close this thread's reused readers (tests, shutdown). | `verimem/_sqlite_pragma.py:113`; `verimem/_sqlite_pragma.py:120`; `verimem/_sqlite_pragma.py:177` | `tests/test_read_connection_is_reused.py` | - | NON MISURATO | - |
