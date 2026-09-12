# mappa — `verimem/contradiction.py`

**owner ws6 Dati** · base `7b9e8ca1` · aperto 2026-09-08 22:53

**705 righe · 21 funzioni · 2 classi.** Contate con `ast`.
**11 pubbliche, ZERO senza test.** 8 private: 6 con test, 2 con soli chiamanti
interni (`_group_by_topic` 243, `_row_to_contradiction` 484 — **NON MISURATE**,
non morte).

## Le righe

| # | funzione | chiamata da | test | verdetto | prova |
|---|---|---|---|---|---|
| 1 | `heal_contradictions` | **`auto_dream_worker.py:392`** — gira nel worker notturno, in automatico | **6** file la nominano: `test_heal_contradictions_scan68`, `test_flow_scansione_conflitti`, `test_flow_manutenzione_notturna`, `test_il_ripristino_lascia_il_record_coerente`, `test_il_vincitore_che_ne_ingoio_dodici`, `test_la_catena_del_ritiro_finisce_da_qualche_parte` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_heal_contradictions_scan68.py` → `3 passed, 1 warning in 10.x` EXIT=0 · `test_flow_scansione_conflitti.py` → `4 passed` EXIT=0 |
| 2 | `scan_corpus` | `auto_dream_worker.py:390` | `test_heal_contradictions_scan68` · `test_flow_scansione_conflitti` | **FUNZIONA COME PROMESSO**, limitato | stesse esecuzioni |
| 3 | `detect_numeric_clashes` · `detect_boolean_clashes` · `add` · `count_unresolved` · `list_unresolved` · `list_all` · `resolve` · `list_unresolved_for_fact` (+2) | il rilevamento e lo store dei conflitti | `test_contradiction.py` (7 funzioni) · `test_self_curation.py` · `test_fact_delete_cascade_r3.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_contradiction.py` → `17 passed, 1 warning in 10.x` EXIT=0 |
| 4 | le 6 `_private` con test | interne | `test_contradiction_typed_numbers.py` (3) e altri | **FUNZIONA COME PROMESSO**, limitato | `5 passed in 7.80s` EXIT=0 |

## 🔑 La cura del rango HA attraversato il confine — in due file su tre

Alle 20:36 avevo consegnato un reperto (msg `f1ab66149e3e2bb5`) dicendo che la
lezione di `_rango_di_fiducia` «non ha attraversato il confine del file».
**Non era esatto, e lo correggo qui.** `heal_contradictions` la importa e la usa:

```python
# contradiction.py:537
from .semantic import _rango_di_fiducia
```

e il suo docstring porta gli stessi numeri del docstring di `semantic.py:599`:

> «`skipped_unknown_trust` — coppie in cui almeno un lato ha uno stato che
> `_STATUS_RANK` non conosce. **Prima finivano nel confronto come rango 0 e il
> lato ignoto veniva RITIRATO: sullo store vero erano 257 coppie, 227 con un
> `model_claim` che ritirava un `user_manual`.** Vedi `semantic._rango_di_fiducia`.»

### Il quadro corretto

| file | politica sullo stato ignoto | usa `_rango_di_fiducia` |
|---|---|---|
| `semantic.py` | `None` = **non decido** | sì (6064, 6080) |
| `contradiction.py` | salta la coppia, `skipped_unknown_trust` | **sì** (537) |
| `anti_confab_gate.py` | `.get(…, 2)` = **model_claim** in 4 punti | **no**, 0 volte |

⇒ Non sono «due politiche in due file»: la cura è arrivata in **due file su
tre**, e manca nell'ultimo. Questo **rafforza** il reperto invece di
indebolirlo — dimostra che la cura è **portabile**, perché è già stata portata
una volta, e che quello che resta è finire il giro.

📌 E c'è un dato che pesa: `heal_contradictions` gira **da sola** nel worker
notturno (`auto_dream_worker.py:392`, `principal="system:heal"`). Nella mia
misura del 07/09 era responsabile di **130 ritiri su 292**. Le decisioni di
questa funzione non passano da nessuna mano umana, e il criterio con cui decide
è quello che le tre righe della tabella qui sopra descrivono.

## Inventario completo — ogni funzione per nome

**19 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 122 | `_extract_numbers` | priv |  | 1 — `test_contradiction_typed_numbers.py` |
| 126 | `_classify_numbers` | priv | Cycle #123: classify extracted numbers by semantic type. | 2 — `test_contradiction_typed_numbers.py` |
| 153 | `_values_clash` | priv | Detect a meaningful numeric clash between two propositions | 2 — `test_contradiction_typed_numbers.py` |
| 209 | `_cosine` | priv | Compute cosine on freshly-encoded propositions. | 3 — `test_contradiction_year_range_false_negative.py` |
| 226 | `_has_negation` | priv | Negation check — DELEGA alla superficie unica in ``quantit | 2 — `test_due_opposti_non_possono_vivere_insieme.py` |
| 243 | `_group_by_topic` | priv |  | 🔴 **nessuno** |
| 250 | `detect_numeric_clashes` | **pub** | See module docstring. Returns one Contradiction per offend | 3 — `test_contradiction.py` |
| 299 | `detect_boolean_clashes` | **pub** | Find same-topic pairs where ONE side has a negation marker | 3 — `test_contradiction.py` |
| 504 | `heal_contradictions` | **pub** | Self-healing pass over ALREADY-detected contradictions. | 11 — `test_flow_manutenzione_notturna.py` |
| 616 | `scan_corpus` | **pub** | Run all detectors over the corpus and persist new contradi | 5 — `test_contradiction.py` |
| 381 | `_connect` | priv |  | 47 — `test_bridge.py` |
| 395 | `add` | **pub** | Insert a contradiction. Returns True if a new row was crea | _generico — cercato qualificato nei blocchi sopra_ |
| 417 | `list_unresolved` | **pub** |  | 2 — `test_contradiction.py` |
| 427 | `list_all` | **pub** |  | 3 — `test_ask_ha_un_contratto_solo.py` |
| 436 | `resolve` | **pub** |  | _generico — cercato qualificato nei blocchi sopra_ |
| 446 | `list_unresolved_for_fact` | **pub** | Cycle #117: return unresolved contradictions that involve | 3 — `test_fact_delete_cascade_r3.py` |
| 462 | `resolve_all_for_fact` | **pub** | Cycle #117: mark every unresolved contradiction involving | 1 — `test_trust_signal.py` |
| 475 | `count_unresolved` | **pub** |  | 3 — `test_contradiction.py` |
| 484 | `_row_to_contradiction` | priv |  | 🔴 **nessuno** |

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
| 84 | `Contradiction` | 1 | **contratto dei dati**: `fact_a_id`, `fact_b_id`, `kind`, `similarity`, `detected_at`, `id`, `resolved_at`, `resolution_note` | 10 — `test_contradiction.py` | esercitata dai blocchi eseguiti sopra |
| 366 | `ContradictionStore` | 10 | SQLite-backed store for detected contradictions. | 18 — `test_contradiction.py` | esercitata dai blocchi eseguiti sopra |

## I metodi speciali di questo file — 2

In tabella come tutto il resto: il righello legge la seconda colonna, e in prosa
restavano fuori dal conto. **Non sono righe vuote**: i costruttori di questo
prodotto aprono file, eseguono schemi e in tre casi su otto fanno le migrazioni.
Ognuno dice cosa apre e cosa crea, letto dal corpo.

| riga | metodo | classe | cosa apre e cosa crea (letto) | verdetto |
|---|---|---|---|---|
| 94 | `__post_init__` | `Contradiction` | 1 stmt con logica vera: l'`id` e' lo **sha256 di `sorted(a,b) + kind`**, quindi la stessa coppia in ordine inverso produce lo STESSO id — la deduplicazione delle contraddizioni sta qui, non nel database | esercitato da ogni uso di `Contradiction` nei blocchi sopra |
| 374 | `__init__` | `ContradictionStore` | 3 stmt: `mkdir`, `_connect`, `executescript`. **Nessun `ensure_schema_version`** — `grep -c` in questo file: 0. Lo schema e' statico | esercitato da ogni uso di `ContradictionStore` nei blocchi sopra |

## ⚠️ Questo store NON versiona lo schema

`ensure_schema_version` compare **0 volte** in questo file, contro 3 in
`semantic.py`, 2 in `memory.py`, 3 in `entity_kg.py`; e **zero** `ALTER TABLE`: lo schema e' statico. La tabella delle
quattro politiche, con le prove, sta in [`semantic.md`](semantic.md) — sezione
«Quattro politiche di schema in otto store».
