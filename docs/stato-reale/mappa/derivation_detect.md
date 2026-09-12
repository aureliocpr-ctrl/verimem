# `verimem/derivation_detect.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## Il claim del README

> `README:308` — «traced (`derives_from` parents, retractable if a parent falls)»

Letto: il modulo rileva gli archi di derivazione tipizzati che popolano quel `derives_from`. La riga promette il *comportamento* della catena, non il rilevamento: **copertura parziale del claim**.

## La copertura di esecuzione

```
perimetro: 51 file di test che nominano i detector L1
copertura: 95.5%
statement non eseguiti: 48
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/derivation_detect.py:41` `_norm` | funzione: (nessun docstring) | `verimem/derivation_detect.py:62`; `verimem/derivation_detect.py:73`; `verimem/entity_kg.py:307` (+14) | `tests/test_entity_kg.py`; `tests/test_external_f1_msc.py`; `tests/test_openie.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 2 | `verimem/derivation_detect.py:45` `_attr` | funzione: (nessun docstring) | `verimem/anti_confab_gate.py:3339`; `verimem/anti_confab_gate.py:3340`; `verimem/anti_confab_gate.py:3341` (+22) | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita, 1/3 statement del corpo scoperti (755 passed, EXIT=0) |
| 3 | `verimem/derivation_detect.py:51` `detect_derivations` | funzione: Return ids of EXISTING facts the ``source`` cites as parents (high precision). | `verimem/derivation_detect.py:79`; `verimem/mcp_server.py:13532`; `verimem/mcp_server.py:13534` | `tests/test_derivation_detect.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

