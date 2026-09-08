# Mappa di `verimem/failure_clusters.py` — 3 righe, 79 righe di codice (lead, 09/09 02:54)

Letto per intero. Prova: pytest del lotto E sul tip `20257636` (`233 passed in 145.12s`, EXIT=0, con `tests/test_failure_clusters.py`). Chiamante letto: `verimem/mcp_server.py:10063-10069` (`hippo_failure_clusters`). La bozza attribuiva a `_signature` chiamanti in `anomaly_detection.py` e `correction_velocity.py`: **falsi positivi del nome**: questa `_signature` (5 token più frequenti) è una COPIA di `anomaly_detection._signature`, riga per riga. Claim README: nessuna riga.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/failure_clusters.py:22` `_signature` | i 5 token più frequenti del `task_text`, ordinati | `cluster_failures` (50) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 233 passed |
| 2 | `verimem/failure_clusters.py:28` `_informative_tokens` | token > 2 caratteri fuori da `_STOP` (inglese + `error/fail/failed/failure`) | `cluster_failures` (60) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 233 passed |
| 3 | `verimem/failure_clusters.py:35` `cluster_failures` | i soli episodi `failure` raggruppati per firma (≥ 2), con i 5 token più comuni delle risposte finali come «probabile pattern d'errore», ordinati per taglia, tetto `top_k`, al più 10 id per cluster | `verimem/mcp_server.py:10069` (`hippo_failure_clusters`) | `tests/test_failure_clusters.py` | - | FUNZIONA COME PROMESSO | pytest 233 passed |

Reperti: (a) due copie: `_signature` identica a `anomaly_detection._signature`, `_STOP` identica a `failure_diagnosis._STOP` — classe «una copia invece della superficie unica», e tutte e tre le firme di episodio (`anomaly_detection`, `failure_clusters`, `emerging_patterns`) si chiamano `_signature` con tre definizioni; (b) la firma senza stopword: «the, to, a, of, in» dominano i 5 token più frequenti di qualsiasi task inglese, quindi task diversi si raggruppano insieme (stesso reperto di `anomaly_detection`; letto, non misurato). Nessun P0.
