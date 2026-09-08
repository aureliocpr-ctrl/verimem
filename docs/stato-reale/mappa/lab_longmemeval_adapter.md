# Mappa di `verimem/lab_longmemeval_adapter.py` — 3 righe, 127 righe di codice (lead, 09/09 03:28)

Letto per intero. Prova: pytest del lotto F sul tip `20257636` (`105 passed in 31.36s`, EXIT=0, con `tests/test_lab_longmemeval_adapter.py`). Chiamanti: **nessuno in `verimem/`, `scripts/`, `benchmark/`**. Il docstring lo dichiara SKELETON (ciclo 178, 22/05): «real dataset fetch + LLM-judge harness deferred to cycle 178.1»; il match è una sottostringa senza LLM. Claim README: la riga 62 nomina `LongMemEval_s` fra i dataset del comparativo (C10): **quei numeri non passano da questo adattatore** (nessun import in `benchmark/`); da collegare alla mappa del banco comparativo (ws8/ws4).

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/lab_longmemeval_adapter.py:49` `LongMemEvalAdapter` | l'adattatore scheletro (sessione → episodio, round → turno, fact → fatto) | nessuno | `tests/test_lab_longmemeval_adapter.py` | README:62 (i numeri NON vengono da qui) | MAI CHIAMATA dal prodotto (scheletro dichiarato) | pytest 105 passed |
| 2 | `verimem/lab_longmemeval_adapter.py:55` `LongMemEvalAdapter.adapt_sessions` | dispaccia ogni sessione a un `ingester` iniettato; non-dict → skipped, eccezione → errors, il giro continua | nessuno | `tests/test_lab_longmemeval_adapter.py` | - | MAI CHIAMATA dal prodotto | pytest 105 passed |
| 3 | `verimem/lab_longmemeval_adapter.py:86` `LongMemEvalAdapter.evaluate_query` | una query al `recall_callable` iniettato e un match per sottostringa (case-insensitive) con `expected_answer`; eccezione → `match=False` | nessuno | `tests/test_lab_longmemeval_adapter.py` | - | MAI CHIAMATA dal prodotto | pytest 105 passed |

Reperti: (a) undicesimo modulo senza chiamante, e con «lab_» nel nome nel pacchetto pubblicato: da spostare sotto `benchmark/` o togliere (ws8); (b) il nome «LongMemEval» dentro il pacchetto accanto a un README che cita LongMemEval_s fa credere che il comparativo passi da qui: non è così. Nessun P0.
