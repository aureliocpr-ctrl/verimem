# `verimem/evidence_requirement.py`

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
copertura: 100.0%
statement non eseguiti: —
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/evidence_requirement.py:34` `is_specific_claim` | funzione: True iff the text asserts a checkable specific — a quantity | `verimem/evidence_requirement.py:92`; `verimem/evidence_requirement.py:102`; `verimem/evidence_requirement.py:110` (+3) | `tests/test_evidence_requirement.py`; `tests/test_un_numero_non_misurabile_resta_una_affermazione_specifica.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 2 | `verimem/evidence_requirement.py:67` `evidence_requirement_enabled` | funzione: Opt-in via ``ENGRAM_EVIDENCE_REQUIREMENT`` (default OFF). | `verimem/evidence_requirement.py:98`; `verimem/evidence_requirement.py:111`; `verimem/sleep.py:391` (+3) | `tests/test_evidence_requirement.py`; `tests/test_sleep_tier2_triage.py`; `tests/test_un_numero_non_misurabile_resta_una_affermazione_specifica.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 3 | `verimem/evidence_requirement.py:74` `resolve_write_confidence` | funzione: Cap confidence for a SPECIFIC, UNSOURCED claim. | `verimem/evidence_requirement.py:112`; `verimem/mcp_server.py:13474`; `verimem/mcp_server.py:13475` | `tests/test_evidence_requirement.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

