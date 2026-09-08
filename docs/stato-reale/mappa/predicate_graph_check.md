# Mappa di `verimem/predicate_graph_check.py` — 4 righe, 119 righe di codice (lead, 09/09 01:58)

Letto per intero. Prova: pytest del lotto C sul tip `20257636` (`62 passed in 20.70s`, EXIT=0, con `tests/test_predicate_graph_check.py`; lo nomina anche `tests/test_curate_pipeline.py`). Chiamanti letti: `verimem/mcp_server.py:12070` (`hippo_predicate_graph_check`), `verimem/curate_pipeline.py:22,72`. La bozza attribuiva a `_find_cycles.dfs` chiamanti in `skill_lineage_metrics.py`: **falso positivo del nome** (un'altra `dfs`). Arco `a → b` se `post(a) ∩ pre(b) ≠ ∅`. Claim README: nessuna riga.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/predicate_graph_check.py:19` `_build_edges` | adiacenza `id → successori` ordinati; O(S²) su tutte le coppie | `predicate_graph_check` (74) | via il test | - | FUNZIONA COME PROMESSO | pytest 62 passed |
| 2 | `verimem/predicate_graph_check.py:37` `_find_cycles` | cicli per DFS a colori (GRAY/BLACK) più i cappi | `predicate_graph_check` (91) | via il test | - | FUNZIONA COME PROMESSO | pytest 62 passed |
| 3 | `verimem/predicate_graph_check.py:43` `_find_cycles.dfs` | la visita ricorsiva che registra il ciclo quando incontra un nodo GRAY | `_find_cycles` (51, 56) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 62 passed |
| 4 | `verimem/predicate_graph_check.py:66` `predicate_graph_check` | `{has_cycles, cycles (canonicalizzati e deduplicati), n_nodes, n_edges, isolated_skill_ids}`; un cappio da solo non mette la skill «nel grafo» | `verimem/mcp_server.py:12070`, `verimem/curate_pipeline.py:72` | `tests/test_predicate_graph_check.py`, `tests/test_curate_pipeline.py` | - | FUNZIONA COME PROMESSO | pytest 62 passed |

Reperti: (a) `color.get(succ) is GRAY` confronta interi con `is` (righe 46, 50): funziona per 1 e 2 (piccoli interi internati), fragile per convenzione; (b) la DFS è ricorsiva: su una catena lunga più del limite di ricorsione (1000) alza `RecursionError` (letto, non misurato; 325 skill oggi). Nessun P0.
