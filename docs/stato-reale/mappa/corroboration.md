# `verimem/corroboration.py`

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
copertura: 95.7%
statement non eseguiti: 44
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/corroboration.py:35` `Corroboration` | classe: Two facts in DIFFERENT topics that assert the SAME value for the same | `verimem/corroboration.py:4`; `verimem/corroboration.py:60`; `verimem/corroboration.py:91` (+2) | `tests/test_corroboration.py`; `tests/test_tier2_judge.py` | - | NON MISURATO | - |
| 2 | `verimem/corroboration.py:43` `Corroboration.as_dict` | funzione: (nessun docstring) | `verimem/mcp_server.py:11931`; `verimem/mcp_server.py:11932` | `tests/test_facts_conflict.py`; `tests/test_facts_conflict_lexical.py` | - | NON MISURATO | - |
| 3 | `verimem/corroboration.py:53` `find_corroborations` | funzione: Return fact pairs that independently corroborate the same specific. | `verimem/corroboration.py:129`; `verimem/corroboration.py:135`; `verimem/quantity_match.py:1458` | `tests/test_corroboration.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 4 | `verimem/corroboration.py:120` `corroboration_index` | funzione: Map fact_id → number of DISTINCT other facts that corroborate it. | `verimem/corroboration.py:135`; `verimem/tier2_judge.py:41`; `verimem/tier2_judge.py:232` | `tests/test_corroboration.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

