# Mappa di `verimem/memory_compaction.py` — 3 righe, 89 righe di codice (lead, 09/09 00:50)

Letto per intero. Prove: le stesse due di `oracle.md` (pytest del lotto `61 passed in 82.08s`, EXIT=0, sul tip `20257636`, con `tests/test_memory_compaction.py`; prova alla porta MCP con store isolato: `hippo_find_duplicate_facts` → `quarantenato SERVITO=True · vivo servito=True · 355 char`). Chiamante letto: `verimem/mcp_server.py:10214-10225` (`hippo_find_duplicate_facts`; il nome del tool dice «duplicate facts», il modulo si chiama «compaction»). La bozza indicava anche `curate_pipeline.py:20`: **falso positivo del nome** — quella riga importa `find_duplicates.find_duplicate_skills` (skill, non fatti). Claim README: nessuna riga (615 e 791 usano «duplicated» in altro senso).

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/memory_compaction.py:17` `_tokens` | token `[A-Za-z0-9_-]+` in minuscolo | `find_duplicates` (43, 50) | `tests/test_memory_compaction.py` | - | FUNZIONA COME PROMESSO | pytest 61 passed |
| 2 | `verimem/memory_compaction.py:21` `_jaccard` | Jaccard, 0 se vuoto (copia n. 10 di 18) | `find_duplicates` (51) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 61 passed |
| 3 | `verimem/memory_compaction.py:27` `find_duplicates` | cluster greedy (Jaccard ≥ 0,7 col capofila), riportati se di taglia ≥ 2 con rappresentante, id, `n_dupes` e `max_similarity`; `n_duplicate_pairs` = membri extra | `verimem/mcp_server.py:10215` (`hippo_find_duplicate_facts`) | `tests/test_memory_compaction.py`, `tests/perf/bench.py` | - | FUNZIONA COME PROMESSO (i cluster escono senza lo `status` dei membri, T49) | porta MCP 08/09 22:33 + pytest 61 passed |

Reperti: (a) i token del capofila vengono ricalcolati a ogni confronto (riga 50): O(n·cluster·len), curabile tenendo i token nel cluster; (b) `best_sim` (riga 47) è calcolata e mai usata; (c) doppione di `find_duplicate_facts` con nomi dei tool incrociati (vedi quella mappa).
