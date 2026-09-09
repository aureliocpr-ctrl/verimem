# mappa — `verimem/adjudication_log.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:37

**311 righe · 13 funzioni · 2 classi** (`ast`). **7 pubbliche, 5 private.**
Metodo e limiti: quelli di `semantic.md`, con le quattro trappole del righello già pagate.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **7 pubbliche** del registro delle aggiudicazioni | `tests/test_L41_non_tocca_i_riformulati.py` e altri | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_L41_non_tocca_i_riformulati.py` → `9 passed, 23 warnings` EXIT=0 |
| le 5 `_private` | via i chiamanti | **NON MISURATE** direttamente | — |

**Zero pubbliche senza test.**

## Inventario completo — ogni funzione per nome

**12 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 34 | `_chain_payload` | priv | The EXACT field set hashed into the tamper-evidence chain. | 1 — `test_adjudication_pins.py` |
| 57 | `_pins_column` | priv | The stored ``pins`` text VERBATIM — what verify() must re- | 🔴 **nessuno** |
| 67 | `_loads_pins` | priv | Pins off a row, tolerant of a pre-migration row and of jun | 🔴 **nessuno** |
| 151 | `_conn` | priv |  | 3 — `test_dg_backfill_batched.py` |
| 156 | `record` | **pub** | Append one adjudication; return its id. Never updates an e | 94 — `bench_briefing_proactive_v2.py` |
| 204 | `_row` | priv |  | 6 — `test_continuity.py` |
| 213 | `get` | **pub** |  | _generico — cercato qualificato nei blocchi sopra_ |
| 219 | `list` | **pub** | Adjudications newest-first, optionally filtered by disposi | 581 — `causal_fixture_helper.py` |
| 241 | `verify` | **pub** | Recompute the hash-chain over the audit rows in append (ro | 57 — `conftest.py` |
| 279 | `head` | **pub** | The current chain head — the ``entry_hash`` of the most-re | 47 — `test_adjudication_log_chain.py` |
| 290 | `count` | **pub** | Number of chained rows (``entry_hash`` present — pre-chain | _generico — cercato qualificato nei blocchi sopra_ |
| 300 | `head_at` | **pub** | Stored ``entry_hash`` of the ``count``-th chained row (1-i | 1 — `test_tamper_anchor_receipt.py` |

### I dunder di questo file

L'inventario sopra esclude i metodi speciali, e qui sono nominati per chiudere il
conteggio: **`__init__`**. Sono costruttori e accessori di protocollo — non hanno
un claim del README, non hanno un test proprio, e sono esercitati da **ogni** uso
della loro classe: il verdetto è quello dei blocchi qui sopra, non una riga a sé.
