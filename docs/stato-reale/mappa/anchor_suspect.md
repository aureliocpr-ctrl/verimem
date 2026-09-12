# `verimem/anchor_suspect.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

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
copertura: 98.0%
statement non eseguiti: 53
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/anchor_suspect.py:48` `enabled` | funzione: Gate for AUTO-action built on the detector (e.g. auto-quarantine of the | `verimem/anchor_suspect.py:31`; `verimem/ann_index.py:87`; `verimem/ann_index.py:88` (+48) | `tests/security/test_prompt_injection_defense.py`; `tests/test_ann_index.py`; `tests/test_ann_recall_equivalence.py` (+15) | - | **NON MISURATO** | corpo mai eseguito dai 51 file del perimetro |
| 2 | `verimem/anchor_suspect.py:57` `violating_records` | funzione: Record ids whose stored value disagrees with the trusted assertion. | `verimem/anchor_suspect.py:30`; `verimem/anchor_suspect.py:89` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 3 | `verimem/anchor_suspect.py:64` `_classify` | funzione: The shared gate over a support count and its violating ids. | `verimem/anchor_suspect.py:89`; `verimem/anchor_suspect.py:121`; `verimem/ignorance_map.py:212` (+1) | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 4 | `verimem/anchor_suspect.py:81` `detect_suspect_records` | funzione: Bidirectional-trust gate. ``records`` maps record-id -> stored value for one | `verimem/anchor_suspect.py:30` | `tests/test_anchor_suspect.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 5 | `verimem/anchor_suspect.py:94` `precision_recall` | funzione: Real numbers over an injected ground truth (validation aid). | `verimem/anchor_suspect.py:30` | `tests/test_anchor_suspect.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 6 | `verimem/anchor_suspect.py:103` `suspects_for_source` | funzione: Integration over a ``SourceTrustBook``: a trusted source has asserted values | `verimem/anchor_suspect.py:31` | `tests/test_anchor_suspect.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

