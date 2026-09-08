# Mappa di `verimem/trust_calibration.py` — 5 righe, 82 righe di codice (lead, 09/09 01:30)

Letto per intero. Prova: pytest del lotto B sul tip `20257636` (`84 passed, 1 xfailed in 37.23s`, EXIT=0, con `tests/test_trust_calibration_metrics.py`). Chiamanti letti: `verimem/trust_calibration_eval.py:29-31` (il banco di calibrazione), `scripts/bench_trust_calibration.py`, `scripts/bench_trust_scorers_compare.py` (per nome del modulo). La bozza attribuiva a `_check` dieci test e chiamanti in `doctor`: **falsi positivi del nome** (altre `_check`). Metriche pure: Brier, ECE, tabella di affidabilità. Claim README: nessuna riga (grep su «calibrat|brier» → nessuna).

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/trust_calibration.py:20` `_check` | `ValueError` se le due sequenze hanno lunghezza diversa | `brier_score` (29), `reliability_table` (45), `expected_calibration_error` (71) | via `test_trust_calibration_metrics.py` | - | FUNZIONA COME PROMESSO (plumbing) | pytest 84 passed |
| 2 | `verimem/trust_calibration.py:27` `brier_score` | media di `(p − esito)²`; vuoto → 0,0 | `trust_calibration_eval.py:137` | `tests/test_trust_calibration_metrics.py` | - | FUNZIONA COME PROMESSO | pytest 84 passed |
| 3 | `verimem/trust_calibration.py:35` `_bin_index` | il bin di `p` su `n_bins`, con `p=1,0` nell'ultimo | `reliability_table` (50) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 84 passed |
| 4 | `verimem/trust_calibration.py:41` `reliability_table` | per bin: estremi, `n`, media predetta, frazione di positivi | `expected_calibration_error` (76), `trust_calibration_eval.py:142` | `tests/test_trust_calibration_metrics.py` | - | FUNZIONA COME PROMESSO | pytest 84 passed |
| 5 | `verimem/trust_calibration.py:67` `expected_calibration_error` | ECE = Σ (n_bin/N)·\|media − frazione\| | `trust_calibration_eval.py:138` | `tests/test_trust_calibration_metrics.py` | - | FUNZIONA COME PROMESSO | pytest 84 passed |

Reperti: (a) «vuoto → 0,0» per Brier ed ECE è uno zero perfetto senza dati: la stessa forma che `hallucination_rate_at_k` corregge con `degraded=True`; qui il chiamante deve guardare `n` da sé. Nessun P0.
