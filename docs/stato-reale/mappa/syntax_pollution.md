# `verimem/syntax_pollution.py`

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
| 1 | `verimem/syntax_pollution.py:46` `PollutionError` | classe: Raised when a proposition fails syntax validation. | `verimem/syntax_pollution.py:23`; `verimem/syntax_pollution.py:124`; `verimem/syntax_pollution.py:131` (+2) | `tests/test_syntax_pollution.py` | - | NON MISURATO | - |
| 2 | `verimem/syntax_pollution.py:103` `detect_xml_markup` | funzione: Return list of marker names found in ``text``. | `verimem/syntax_pollution.py:21`; `verimem/syntax_pollution.py:120`; `verimem/syntax_pollution.py:132` (+2) | `tests/test_syntax_pollution.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 3 | `verimem/syntax_pollution.py:118` `is_polluted` | funzione: True if ``text`` contains any known XML pollution marker. | `verimem/syntax_pollution.py:22`; `verimem/syntax_pollution.py:193` | `tests/test_syntax_pollution.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 4 | `verimem/syntax_pollution.py:123` `validate_proposition` | funzione: Raise ``PollutionError`` if ``text`` is empty or polluted. | `verimem/syntax_pollution.py:23`; `verimem/syntax_pollution.py:194` | `tests/test_syntax_pollution.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 5 | `verimem/syntax_pollution.py:137` `sanitize_proposition` | funzione: Best-effort recovery: strip the envelope-pollution payload. | `verimem/mcp_server.py:7869`; `verimem/mcp_server.py:7870`; `verimem/mcp_server.py:9432` (+4) | `tests/test_syntax_pollution.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 6 | `verimem/syntax_pollution.py:160` `scan_facts` | funzione: Bulk audit. Returns a structured report. | `verimem/mcp_server.py:11868`; `verimem/mcp_server.py:11876`; `verimem/syntax_pollution.py:25` (+1) | `tests/test_syntax_pollution.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

