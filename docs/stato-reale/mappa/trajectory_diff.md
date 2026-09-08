# Mappa di `verimem/trajectory_diff.py` — 3 righe, 83 righe di codice (lead, 09/09 03:24)

Letto per intero. Prova: pytest del lotto F sul tip `20257636` (`105 passed in 31.36s`, EXIT=0, con `tests/test_trajectory_diff.py`; lo nomina anche `tests/test_episode_diff.py`). Chiamanti letti: `verimem/causal_extract.py:16,78` (R2.1 consuma la prima divergenza), `verimem/mcp_server.py:9848` (`hippo_trajectory_diff`), `scripts/trajectory_demo.py:24`. Claim README: nessuna riga (grep su «trajector» → nessuna).

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/trajectory_diff.py:14` `_step_signature` | la chiave di confronto: kind, tool, args (repr), contenuto; i timestamp non contano | `trajectory_diff` (42, 43) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 105 passed |
| 2 | `verimem/trajectory_diff.py:24` `trajectory_diff` | dopo `trajectory_normalize`, la prima posizione diversa (o la lunghezza minore se una è prefisso dell'altra), il prefisso comune, i due passi alla divergenza, il riassunto, le lunghezze | `verimem/causal_extract.py:78`, `verimem/mcp_server.py:9848` | `tests/test_trajectory_diff.py`, `tests/test_episode_diff.py` | - | FUNZIONA COME PROMESSO | pytest 105 passed |
| 3 | `verimem/trajectory_diff.py:74` `_summary` | «identical (length N)» o «diverged at step D after P common steps» | `trajectory_diff` (61) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 105 passed |

Reperti: (a) il confronto è posizionale sul `content` esatto: due traiettorie che differiscono per uno spazio nel testo di un pensiero divergono al passo 0 — per il «punto causale» (`causal_extract`) è un limite di metodo non dichiarato; (b) `repr(tool_args)` dipende dall'ordine delle chiavi del dict: argomenti uguali in ordine diverso risultano diversi (letto, non misurato). Nessun P0.
