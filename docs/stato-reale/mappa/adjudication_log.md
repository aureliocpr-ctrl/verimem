# mappa — `verimem/adjudication_log.py`

**owner ws6 Dati** · base `20257636` · 2026-09-09 12:37

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

## Le classi di questo file — 2 sulla superficie

Il righello del lead conta le **classi** nel denominatore (480 sui miei 21 file
contro i 449 di sole funzioni): una classe e' superficie, e finche' non e'
nominata qui non e' mappata. Per le dataclass la riga porta il **contratto dei
dati** — i campi, che sono cio' che quella classe promette a chi la legge. Il
verdetto e' **preso in prestito** dai blocchi eseguiti piu' sopra: nessuna classe
riceve qui un verde nuovo, e dove nessun test nomina il nome si scrive NON
MISURATA.

| riga | classe | metodi | contratto / cosa promette | test che la nominano | verdetto |
|---|---|---|---|---|---|
| 85 | `AdjudicationRecord` | 0 | **contratto dei dati**: `id`, `ts`, `topic`, `disposition`, `proposition`, `fact_id`, `evidence_class`, `judge` … (13 in tutto) | 1 — `test_adjudication_log.py` | esercitata dai blocchi eseguiti sopra |
| 128 | `AdjudicationLog` | 10 | Isolated per-DB, append-only log of gate verdicts — never touches sema | 4 — `test_adjudication_log.py` | esercitata dai blocchi eseguiti sopra |

## I metodi speciali di questo file — 1

In tabella come tutto il resto: il righello legge la seconda colonna, e in prosa
restavano fuori dal conto. **Non sono righe vuote**: i costruttori di questo
prodotto aprono file, eseguono schemi e in tre casi su otto fanno le migrazioni.
Ognuno dice cosa apre e cosa crea, letto dal corpo.

| riga | metodo | classe | cosa apre e cosa crea (letto) | verdetto |
|---|---|---|---|---|
| 131 | `__init__` | `AdjudicationLog` | 3 stmt: `mkdir` del parent, `_conn()` e una `conn.execute`. **Nessun versionamento** | esercitato da ogni uso di `AdjudicationLog` nei blocchi sopra |

## ⚠️ Questo store NON versiona lo schema

`ensure_schema_version` compare **0 volte** in questo file, contro 3 in
`semantic.py`, 2 in `memory.py`, 3 in `entity_kg.py`; qui la migrazione esiste ed e' **a interrogazione** (`PRAGMA table_info`, righe 141-149). La tabella delle
quattro politiche, con le prove, sta in [`semantic.md`](semantic.md) — sezione
«Quattro politiche di schema in otto store».
