# Mappa di `verimem/betweenness_cache.py` — 4 righe, 162 righe di codice (lead, 09/09 02:24)

Letto per intero. Prova: pytest del lotto D sul tip `20257636` (`73 passed, 6 xfailed in 72.21s`, EXIT=0, con `tests/test_betweenness_cache.py`). Chiamanti: **nessuno** (`git grep ensure_highway_cache` su `verimem/ scripts/ benchmark/` → solo il modulo e il test). Il docstring promette: «The MCP / Auto-Dream worker calls `ensure_highway_cache` once per firing; recall hot-paths read from the file directly» — **nessuno dei due lo fa**: né il worker né il recall nominano il modulo. Claim README: nessuna riga (grep su «betweenness|highway» → nessuna).

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/betweenness_cache.py:47` `_graph_signature` | `nodi.archi.max_created_at` sui fatti vivi (+ `causal_edges` se la tabella c'è); errore SQL → `""` | `ensure_highway_cache` (130, 151) | via il test | - | MAI CHIAMATA (plumbing di una funzione senza chiamante) | pytest 73 passed |
| 2 | `verimem/betweenness_cache.py:76` `_read_cache` | il JSON della cache o `None` | `ensure_highway_cache` (127) | via il test | - | MAI CHIAMATA (plumbing) | pytest 73 passed |
| 3 | `verimem/betweenness_cache.py:85` `_write_cache` | scrive il JSON creando la cartella | `ensure_highway_cache` (155) | via il test | - | MAI CHIAMATA (plumbing) | pytest 73 passed |
| 4 | `verimem/betweenness_cache.py:93` `ensure_highway_cache` | i top-K nodi «autostrada» da cache se fresca (< 30 min) e con firma del grafo invariata, altrimenti ricalcolo con `get_highway_nodes` e riscrittura (errore di scrittura ignorato) | nessuno | `tests/test_betweenness_cache.py` | - | MAI CHIAMATA (il docstring dice che il worker la chiama a ogni giro: falso) | pytest 73 passed |

Reperti: (a) **modulo intero senza chiamante** e con un docstring che descrive un'integrazione mai fatta (ciclo 198, 23/05): si aggiunge alla lista (resource_monitor, hot_reload, sos_compensator, recall_usage, codebase_ingest, coding_reflection); il recall paga la betweenness campionata (~150 ms su 1,7k, docstring) ogni volta, se la usa — da verificare nella mappa di `highway_nodes` (ws5); (b) la firma del grafo non vede le modifiche in loco dei fatti vecchi, dichiarato. Nessun P0.
