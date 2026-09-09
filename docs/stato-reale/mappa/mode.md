# Mappa di `verimem/mode.py` — 3 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/mode.py:28` `engram_mode` | funzione: Return the normalized ENGRAM_MODE ("" if unset). | `verimem/mode.py:50`; `verimem/mode.py:74` | `tests/test_engram_mode.py` | - | NON MISURATO | - |
| 2 | `verimem/mode.py:34` `_setdefault` | funzione: Set ``key=val`` only if it is not already explicitly present + non-empty. | `verimem/mode.py:53`; `verimem/mode.py:61` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/mode.py:43` `apply_engram_mode` | funzione: Project ENGRAM_MODE onto the lower-level env vars (default-set, no clobber). | `verimem/__init__.py:52`; `verimem/_thread_budget.py:31`; `verimem/mode.py:74` | `tests/test_engram_mode.py`; `tests/test_il_tetto_ai_thread_e_applicato.py`; `tests/test_nessun_modulo_nasce_irraggiungibile.py` | - | NON MISURATO | - |
