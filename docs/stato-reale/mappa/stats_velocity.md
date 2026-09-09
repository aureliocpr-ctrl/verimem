# Mappa di `verimem/stats_velocity.py` — 2 righe, 38 righe di codice (lead, 09/09 03:56)

Letto per intero. Prova: pytest del lotto G sul tip `20257636` (`117 passed, 1 skipped in 94.44s`, EXIT=0, con `tests/test_stats_velocity.py`). Chiamante letto: `verimem/mcp_server.py:9994-10001` (`hippo_stats_velocity`, nome dall'elenco dei tool). Claim README: nessuna riga (grep su «velocity» → nessuna).

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/stats_velocity.py:8` `_items_in_window` | quanti elementi hanno `created_at` ≥ ora − finestra | `compute_velocity` (26, 27) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 117 passed |
| 2 | `verimem/stats_velocity.py:16` `compute_velocity` | episodi e fatti al giorno nella finestra (7 g), con i conteggi | `verimem/mcp_server.py:10001` | `tests/test_stats_velocity.py` | - | FUNZIONA COME PROMESSO | pytest 117 passed |

Reperti: (a) il chiamante passa i fatti da `list_facts(limit=10000)` (mappa `oracle.md`): su un corpus dove i 10.000 più recenti coprono meno di 7 giorni la velocità è sottostimata senza avviso — sul corpus di casa non è il caso (15.675 vivi in mesi), ma il tetto è silenzioso; (b) i quarantenati contano come «fatti scritti» (T49 nella forma «conteggio»): può essere l'intenzione (velocità di scrittura), va detto nella descrizione del tool. Nessun P0.
