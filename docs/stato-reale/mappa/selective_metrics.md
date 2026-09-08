# `verimem/selective_metrics.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 Marie (QA) · **08/09**.

## Il claim del README

**NESSUNO.**

Cercato nel README con i termini del modulo (`grep -in`) e **nessuna
riga lo copre**. Il claim `README:704` è della famiglia dei detector
L1 e questo file non è uno di quelli: attribuirglielo sarebbe
inventare l'attribuzione — in un documento fatto per collegare i
claim al codice, l'errore peggiore.

⇒ come `ide.py` e `sandbox.py`: **superficie viva fuori dalla
vetrina**. Non è un difetto; è un dato per chi decide che cosa il
prodotto dichiara di essere.

## La copertura di esecuzione

```
perimetro: 51 file di test che nominano i detector L1
copertura: 90.8%
statement non eseguiti: 50, 71, 88, 138
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/selective_metrics.py:40` `_clean` | funzione: (nessun docstring) | `verimem/selective_metrics.py:48`; `verimem/selective_metrics.py:69`; `verimem/selective_metrics.py:86` (+4) | `tests/test_admission_gate_default_on.py`; `tests/test_interactive_judge.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 2 | `verimem/selective_metrics.py:44` `selective_risk_coverage` | funzione: (risk among answered, coverage) at ``threshold`` — strict ``>`` like | `verimem/selective_metrics.py:11`; `verimem/selective_metrics.py:34` | `tests/test_selective_metrics.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/9 statement del corpo scoperti (755 passed, EXIT=0) |
| 3 | `verimem/selective_metrics.py:59` `aurc` | funzione: Area under the risk-coverage curve: rank by confidence (desc), take the | `verimem/selective_metrics.py:13`; `verimem/selective_metrics.py:34`; `verimem/selective_metrics.py:64` (+1) | `tests/test_selective_metrics.py`; `tests/test_stats.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/11 statement del corpo scoperti (755 passed, EXIT=0) |
| 4 | `verimem/selective_metrics.py:82` `e_aurc` | funzione: Excess AURC over the ORACLE ranking (all correct first): 0 = the scores | `verimem/selective_metrics.py:13`; `verimem/selective_metrics.py:34` | `tests/test_selective_metrics.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/6 statement del corpo scoperti (755 passed, EXIT=0) |
| 5 | `verimem/selective_metrics.py:94` `tce_at_lambda` | funzione: Calibration at the DECLARED operating point λ (threshold λ/(1+λ)): | `verimem/selective_metrics.py:17`; `verimem/selective_metrics.py:35` | `tests/test_selective_metrics.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 6 | `verimem/selective_metrics.py:132` `isotonic_fit` | funzione: Pure PAV (pool-adjacent-violators) isotonic regression of correctness on | `verimem/selective_metrics.py:21`; `verimem/selective_metrics.py:34` | `tests/test_selective_metrics.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/17 statement del corpo scoperti (755 passed, EXIT=0) |
| 7 | `verimem/selective_metrics.py:153` `isotonic_fit.predict` | funzione: (nessun docstring) | `verimem/config.py:407`; `verimem/cross_encoder_rerank.py:17`; `verimem/outcome_predict.py:40` (+20) | `tests/conftest.py`; `tests/test_eval_records_read_path_regime.py`; `tests/test_forward_replay.py` (+10) | - | NON MISURATO | - |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

