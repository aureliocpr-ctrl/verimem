# Mappa di `verimem/momentum_macro.py` — 3 righe, 109 righe di codice (lead, 09/09 03:12)

Letto per intero. Prova: pytest del lotto F sul tip `20257636` (`105 passed in 31.36s`, EXIT=0, con `tests/test_momentum_macro.py`). Chiamante letto: `verimem/recall_chain.py:13,98` (il campo `momentum` nell'uscita di `hippo_recall_chain`). Lo strato di DECISIONE fra `recall_chain` (probabilità in avanti) e `compose_macro` («un tool che nessuno innesca, perché niente segnala QUANDO una catena ha abbastanza slancio»). La bozza attribuiva a `_empty` un chiamante in `risk_guard.py`: **falso positivo del nome**. Claim README: nessuna riga.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/momentum_macro.py:24` `_collapse` | via i duplicati consecutivi (`A→B→B` è `A→B`) | `momentum_macro_candidate` (76) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 105 passed |
| 2 | `verimem/momentum_macro.py:34` `_empty` | il payload «nessun candidato» a forma fissa | `momentum_macro_candidate` (92) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 105 passed |
| 3 | `verimem/momentum_macro.py:48` `momentum_macro_candidate` | fra i richiami, il migliore con piano in avanti probabile (≥ 0,7) e catena vera (≥ 2 passi distinti); ordinato per probabilità poi punteggio; `macro_path` pronto per `hippo_compose_macro` | `verimem/recall_chain.py:98` | `tests/test_momentum_macro.py` | - | FUNZIONA COME PROMESSO | pytest 105 passed |

Reperti: (a) la raccomandazione è solo un campo nel payload: se poi qualcuno chiama `hippo_compose_macro` non è misurato (il docstring ammette che era «a tool nobody triggers»); (b) `score` assente vale 0,0 (riga 68) mentre `reasoning._appaia` ha scelto `None` per «non misurato»: due convenzioni per lo stesso vuoto. Nessun P0.
