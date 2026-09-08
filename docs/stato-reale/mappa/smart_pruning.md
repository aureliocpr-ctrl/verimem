# Mappa di `verimem/smart_pruning.py` — 3 righe, 87 righe di codice (lead, 09/09 03:20)

Letto per intero. Prova: pytest del lotto F sul tip `20257636` (`105 passed in 31.36s`, EXIT=0, con `tests/test_smart_pruning.py`). Chiamante letto: `verimem/mcp_server.py:10288-10290` (`hippo_smart_prune`). La bozza attribuiva a `_safe_fitness` un chiamante in `skill_roi.py` e a `_freshness` uno in `fact_priority.py`: **falsi positivi del nome** (altre funzioni omonime: `fact_priority._freshness` ha emivita 180 g, questa 90 g). Claim README: nessuna riga (grep su «prun» → nessuna).

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/smart_pruning.py:24` `_safe_fitness` | `successi/prove`, 0 senza prove | `smart_prune` (60) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 105 passed |
| 2 | `verimem/smart_pruning.py:32` `_freshness` | decadimento a emivita 90 g su `last_used_at`; mai usata → 0,5 | `smart_prune` (65) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 105 passed |
| 3 | `verimem/smart_pruning.py:40` `smart_prune` | `score = ROI · peso_status · freschezza` con `ROI = fitness · avg_tokens · log(1+prove)` (0,01 senza prove); `retired` escluse; top `budget` in `keep`, il resto in `prune` | `verimem/mcp_server.py:10290` (`hippo_smart_prune`) | `tests/test_smart_pruning.py` | - | FUNZIONA COME PROMESSO | pytest 105 passed |

Reperti: (a) la ROI moltiplica per `avg_tokens`: una skill che consuma PIÙ token vale di più nel punteggio (dichiarato nel docstring come «ROI»): con lo stesso fitness, la più cara si tiene e la più economica si pota — se è l'intenzione, va detto nella descrizione del tool; (b) tre emivite diverse per tre «freshness» (`freshness.py` parametrica, `fact_priority` 180 g, qui 90 g): classe ①. Nessun P0.
