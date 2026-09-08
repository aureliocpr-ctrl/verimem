# Mappa di `verimem/failure_diagnosis.py` — 3 righe, 106 righe di codice (lead, 09/09 00:52)

Letto per intero. Prova: pytest del lotto sul tip `20257636` (`61 passed in 82.08s`, EXIT=0, con `tests/test_failure_diagnosis.py`). Chiamante letto: `verimem/mcp_server.py:10178-10200` (`hippo_diagnose_failure`), che passa `a.memory.all(limit=5000)` come episodi passati: lavora sugli EPISODI, non sui fatti, quindi T49 non lo tocca. Claim README: nessuna riga (grep su diagnos → nessuna).

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/failure_diagnosis.py:27` `_tokens` | token > 2 caratteri, senza la lista locale `_STOP` (inglese, più `error/fail/failed/failure` che nel contesto non informano) | `diagnose_failure` (48, 55, 70) | `tests/test_failure_diagnosis.py` | - | FUNZIONA COME PROMESSO | pytest 61 passed |
| 2 | `verimem/failure_diagnosis.py:34` `_jaccard` | Jaccard, 0 se vuoto (copia n. 7 di 18) | `diagnose_failure` (56) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 61 passed |
| 3 | `verimem/failure_diagnosis.py:40` `diagnose_failure` | fra i fallimenti passati con `task_text` a Jaccard ≥ 0,2, i tre token più frequenti del `final_answer` come causa radice; confidenza da numero e concentrazione (≥3 e ≥0,6 → high) | `verimem/mcp_server.py:10194` (`hippo_diagnose_failure`) | `tests/test_failure_diagnosis.py` | - | FUNZIONA COME PROMESSO | pytest 61 passed |

Reperti: (a) la «causa radice» è la parola più frequente nelle risposte finali dei fallimenti simili: un proxy lessicale dichiarato nel docstring («candidate root cause»), non una diagnosi; (b) `_STOP` è un'altra lista monolingue locale (classe ③): un episodio italiano non viene pulito; (c) `top_k` limita solo gli id restituiti, non gli episodi contati. Nessun P0.
