# Mappa di `verimem/emerging_skill_register.py` — 4 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/emerging_skill_register.py:47` `_fact_id_for` | funzione: Deterministic content-hash id so repeated registration is idempotent. | `verimem/emerging_skill_register.py:126` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/emerging_skill_register.py:53` `_confidence_from_evidence` | funzione: (nessun docstring) | `verimem/emerging_skill_register.py:146` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/emerging_skill_register.py:60` `_proposition_for` | funzione: (nessun docstring) | `verimem/emerging_skill_register.py:128` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/emerging_skill_register.py:84` `register_emerging_drafts_as_facts` | funzione: Persist each draft as an ``emerging_skill/*`` fact. | `verimem/auto_dream_worker.py:216`; `verimem/auto_dream_worker.py:290`; `verimem/auto_dream_worker.py:306` (+4) | `tests/test_auto_dream_stable_partition_envvar.py`; `tests/test_emerging_register_error_logged.py`; `tests/test_emerging_register_screen.py` (+1) | - | NON MISURATO | - |
