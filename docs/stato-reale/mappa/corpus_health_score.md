# Mappa di `verimem/corpus_health_score.py` — 4 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/corpus_health_score.py:14` `_safe_div` | funzione: (nessun docstring) | `verimem/corpus_health_score.py:126`; `verimem/corpus_health_score.py:130`; `verimem/corpus_health_score.py:153` (+1) | nessuno | - | NON MISURATO | - |
| 2 | `verimem/corpus_health_score.py:18` `_count_lineage_connected` | funzione: LEGACY (cycle #29) — count skill in skill_lineage as parent OR child. | nessuno trovato | `tests/test_corpus_health_lineage.py` | - | NON MISURATO | - |
| 3 | `verimem/corpus_health_score.py:44` `_compute_lineage_metrics` | funzione: CYCLE #32 (refined CYCLE #33): ritorna (n_with_alive_parent, n_with_alive_child). | `verimem/corpus_health_score.py:22`; `verimem/corpus_health_score.py:149` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/corpus_health_score.py:89` `compute_health_score` | funzione: Return `{score, components, verdict}` score in [0, 100]. | `verimem/corpus_health_score.py:21`; `verimem/corpus_health_score.py:209`; `verimem/mcp_server.py:10859` (+1) | `tests/test_corpus_health_lineage.py`; `tests/test_corpus_health_score.py`; `tests/test_healthy_dichiara_la_sua_scala.py` | - | NON MISURATO | - |
