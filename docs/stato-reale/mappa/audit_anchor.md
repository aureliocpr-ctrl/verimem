# `verimem/audit_anchor.py`

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
copertura: 86.7%
statement non eseguiti: 97, 174-177, 182-183, 187-188, 200
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/audit_anchor.py:71` `build_payload` | funzione: The signed part of a receipt (everything EXCEPT the signature). Heads are | `verimem/audit_anchor.py:46`; `verimem/audit_anchor.py:52`; `verimem/audit_anchor.py:65` (+4) | `tests/test_tamper_anchor_receipt.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/10 statement del corpo scoperti (755 passed, EXIT=0) |
| 2 | `verimem/audit_anchor.py:107` `sign_anchor` | funzione: Return the full receipt: ``payload`` plus its base64 ed25519 | `verimem/audit_anchor.py:47`; `verimem/cli.py:5814`; `verimem/cli.py:5831` (+2) | `tests/test_tamper_anchor_receipt.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 3 | `verimem/audit_anchor.py:114` `ChainState` | classe: A chain's CURRENT state, as seen at verify time. | `verimem/audit_anchor.py:45`; `verimem/audit_anchor.py:140`; `verimem/cli.py:5769` (+10) | `tests/test_tamper_anchor_receipt.py` | - | NON MISURATO | - |
| 4 | `verimem/audit_anchor.py:130` `AnchorResult` | classe: (nessun docstring) | `verimem/audit_anchor.py:44`; `verimem/audit_anchor.py:140`; `verimem/audit_anchor.py:158` (+4) | nessuno | - | NON MISURATO | - |
| 5 | `verimem/audit_anchor.py:139` `verify_anchor` | funzione: Verify a receipt against the live chains. Checks, in order: | `verimem/audit_anchor.py:48`; `verimem/cli.py:5891`; `verimem/cli.py:5918` (+2) | `tests/test_tamper_anchor_receipt.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 7/38 statement del corpo scoperti (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

