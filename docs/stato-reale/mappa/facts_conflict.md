# mappa — `verimem/facts_conflict.py`

**owner ws6 Dati** · base `7b9e8ca1` · aperto 2026-09-08 23:01

**563 righe · 11 funzioni · 3 classi.** Contate con `ast`.
**8 pubbliche, ZERO senza test.** 3 private: 1 con test, 2 con soli chiamanti
interni.

⚠️ **Solo 4 file di test nominano questo modulo** — il numero più basso dei sei
file aperti finora. Non è un difetto di per sé (i quattro sono mirati e verdi),
ma è il modulo con la superficie di prova più stretta della mia parte.

## Le righe

| # | funzione | chiamata da | test | verdetto | prova |
|---|---|---|---|---|---|
| 1 | `find_conflicting_pairs` | `mcp_server.py:11906` | `test_facts_conflict.py` · `test_facts_conflict_lexical.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_facts_conflict.py` → `27 passed in 8.54s` EXIT=0 |
| 2 | `find_lexical_conflicts` | `mcp_server.py:11918` | `test_facts_conflict_lexical.py` | **FUNZIONA COME PROMESSO**, limitato | `7 passed in 8.81s` EXIT=0 |
| 3 | **`find_numeric_conflicts`** | 🔴 **nessuno nel prodotto** — vedi sotto | `test_facts_conflict_numeric.py` · `test_quantity_match.py` | **FUNZIONA COME PROMESSO**, ma senza porta | `7 passed in 9.31s` EXIT=0 |
| 4 | `has_negation` · `as_dict` (×3, una per classe) e le altre 3 pubbliche | il rilevamento e la serializzazione | `test_facts_conflict.py` (6 funzioni) | **FUNZIONA COME PROMESSO**, limitato | `27 passed` EXIT=0 |
| 5 | `_content_tokens` (177) · `_overlap_coefficient` (187) | chiamanti **interni**: `_content_tokens` da 257, 367, 378; `_overlap_coefficient` da 278, 417, 532 | nessuno le nomina | **NON MISURATE**, non morte | — |

## `find_numeric_conflicts` — testata, documentata, non collegata

I cinque controlli:

| controllo | esito |
|---|---|
| nome nudo, tutto il repo, ogni tipo di file | `STATE.md:716` + 5 righe in `tests/test_facts_conflict_numeric.py` |
| chiamanti nel prodotto (`verimem/`) | **nessuno** |
| il gemello usato | `find_lexical_conflicts` → `mcp_server.py:11918` ✅ |
| test che la esercitano | 2 file, `7 passed` EXIT=0 |
| documenti che la citano | `STATE.md:716`, insieme a `group_by_topic_family` e `reconcile_new_fact` |

⇒ **Non è MAI CHIAMATA** — un test la esercita davvero — ma **nessuna porta la
raggiunge**. Il gemello lessicale sì. È la stessa forma già trovata quattro
volte, e con questa fa cinque.

## 🔑 La tesi trasversale: cinque funzioni «senza porta» in tre file

Non l'ho cercata: è la quinta volta che la stessa forma esce da file diversi.

| # | funzione | file | ha un test | ha una porta |
|---|---|---|---|---|
| 1 | `restore_decayed` | `memory.py` | sì (`2 passed`) | **no** — 0 in cli/mcp/gateway/client |
| 2 | `is_pinned` | `memory.py` | sì (`4 passed`) | **no** — 0 in `mcp_server.py`, mentre `set_pinned` ne ha 2 |
| 3 | `pinned_episodes` | `memory.py` | sì (`8 passed`) | **no** — 0 in mcp e cli; solo `briefing.py:150` la usa dentro |
| 4 | `salience_of` | `memory.py` | sì (`8 passed`) | **no** — nessun chiamante di prodotto |
| 5 | `find_numeric_conflicts` | `facts_conflict.py` | sì (`7 passed`) | **no** — il gemello lessicale sì |

**Nessuna è rotta e nessuna è morta.** Tutte hanno un test verde, quindi qualcuno
le ha scritte per essere usate e ha verificato che funzionino. Quello che manca è
sempre lo stesso pezzo: **il punto in cui una superficie del prodotto le chiama.**

⇒ Il verdetto per riga resta FUNZIONA COME PROMESSO — sarebbe sbagliato
segnarle rosse, perché fanno ciò che dichiarano. Il reperto è di **struttura**, e
si vede solo mettendo insieme file diversi: è esattamente ciò che una mappa
serve a produrre e che la lettura funzione-per-funzione non può dare.

📌 **Il caso 2 è il più netto**: `set_pinned` è esposta e `is_pinned` no, nello
stesso file, sulla stessa porta. Non è una scelta di disegno che si possa
spiegare con «il decay è manutenzione»: è una coppia scritta insieme di cui è
arrivata solo una metà.

## Inventario completo — ogni funzione per nome

**11 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 99 | `has_negation` | **pub** | True iff `text` contains an ODD number of syntactic negati | 1 — `test_facts_conflict.py` |
| 115 | `strip_negation` | **pub** | Remove every negation marker (both syntactic AND lexical); | 1 — `test_facts_conflict.py` |
| 177 | `_content_tokens` | priv | Lowercased tokens (preserving `#` for identifiers like `F# | 🔴 **nessuno** |
| 187 | `_overlap_coefficient` | priv | Szymkiewicz-Simpson coefficient: |A ∩ B| / min(|A|, |B|). | 🔴 **nessuno** |
| 202 | `find_conflicting_pairs` | **pub** | Return every (positive, negative) fact pair that asserts t | 2 — `test_facts_conflict.py` |
| 326 | `find_numeric_conflicts` | **pub** | Return fact pairs that state a DIFFERENT value for the sam | 2 — `test_facts_conflict_numeric.py` |
| 469 | `find_lexical_conflicts` | **pub** | Retroactive scan for EVERYTHING the expanded lexical write | 1 — `test_facts_conflict_lexical.py` |
| 142 | `as_dict` | **pub** |  | 2 — `test_facts_conflict.py` |
| 304 | `as_dict` | **pub** |  | 2 — `test_facts_conflict.py` |
| 448 | `as_dict` | **pub** |  | 2 — `test_facts_conflict.py` |
| 523 | `_pairs` | priv |  | 1 — `test_rerank_fallback_order_audit3.py` |

## Le classi di questo file — 3 sulla superficie

Il righello del lead conta le **classi** nel denominatore (480 sui miei 21 file
contro i 449 di sole funzioni): una classe e' superficie, e finche' non e'
nominata qui non e' mappata. Per le dataclass la riga porta il **contratto dei
dati** — i campi, che sono cio' che quella classe promette a chi la legge. Il
verdetto e' **preso in prestito** dai blocchi eseguiti piu' sopra: nessuna classe
riceve qui un verde nuovo, e dove nessun test nomina il nome si scrive NON
MISURATA.

| riga | classe | metodi | contratto / cosa promette | test che la nominano | verdetto |
|---|---|---|---|---|---|
| 134 | `ConflictPair` | 1 | **contratto dei dati**: `positive`, `negative`, `semantic_similarity` | 1 — `test_facts_conflict.py` | esercitata dai blocchi eseguiti sopra |
| 291 | `NumericConflictPair` | 1 | **contratto dei dati**: `fact_a`, `fact_b`, `unit`, `value_a`, `value_b` | 1 — `test_facts_conflict_numeric.py` | esercitata dai blocchi eseguiti sopra |
| 437 | `LexicalConflictPair` | 1 | **contratto dei dati**: `fact_a`, `fact_b`, `kind`, `detail` | 1 — `test_facts_conflict_lexical.py` | esercitata dai blocchi eseguiti sopra |
