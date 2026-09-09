# mappa — `verimem/document_index.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:26

**587 righe · 17 funzioni · 4 classi.** Contate con `ast`
(`scratchpad/inventario.py`), non con grep. **5 pubbliche, 9 private.**

Metodo e limiti: quelli dichiarati in `semantic.md`. Le quattro trappole già
pagate valgono anche qui — il nome con la parentesi non vede i **callback**;
escludere il file stesso fa sembrare morti gli helper; cercare solo in
`verimem/` e `tests/` dimentica `benchmark/`; il nome nudo dei metodi generici
pesca ogni dizionario.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **5 pubbliche** dell'indice documenti | `tests/test_document_index.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_document_index.py` → `8 passed, 1 warning in 7.x` EXIT=0 |
| le 9 `_private` | via i chiamanti | **NON MISURATE** direttamente | — |

**Zero pubbliche senza test.** ⚠️ 4 classi in questo file: il rapporto
classi/funzioni più alto della mia parte.

## Inventario completo — ogni funzione per nome

**15 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 45 | `_row_get` | priv | A column that may not exist on a row from a pre-migration  | 🔴 **nessuno** |
| 73 | `_termini_di_ricerca` | priv | I termini della query che possono dire qualcosa, minuscoli | 2 — `test_l_anteprima_mostra_la_riga_che_risponde.py` |
| 130 | `_pool_rerank` | priv | Quanti candidati recuperare PRIMA del riordino. | 🔴 **nessuno** |
| 147 | `_rerank_pairs` | priv | I punteggi del cross-encoder, o ``None`` per degradare. | 1 — `test_i_documenti_non_passavano_dal_reranker.py` |
| 156 | `_applica_rerank` | priv | Riordina i chunk col cross-encoder. STADIO IN PIU', MAI UN | 1 — `test_i_documenti_non_passavano_dal_reranker.py` |
| 570 | `_self_check` | priv | Quick manual smoke: python -c "from verimem.document_index | 🔴 **nessuno** |
| 118 | `encode` | **pub** |  | 107 — `conftest.py` |
| 286 | `_connect` | priv |  | 47 — `test_bridge.py` |
| 291 | `_init_db` | priv |  | 🔴 **nessuno** |
| 313 | `index_document` | **pub** | Snapshot + chunk + embed ``content``. Idempotent per conte | 11 — `test_document_index.py` |
| 389 | `index_file` | **pub** | Extract text from a real file (pdf/docx/html/txt) and inde | 9 — `test_document_index_path_guard.py` |
| 402 | `search` | **pub** | Cosine top-k over the LATEST version of every source. | 220 — `test_editfmt_sensitive.py` |
| 548 | `_rerank_attivo` | priv |  | 🔴 **nessuno** |
| 555 | `stats` | **pub** |  | 46 — `e2e_cycle51_54_chain.py` |
| 575 | `encode` | **pub** |  | 107 — `conftest.py` |

## Le classi di questo file — 4 sulla superficie

Il righello del lead conta le **classi** nel denominatore (480 sui miei 21 file
contro i 449 di sole funzioni): una classe e' superficie, e finche' non e'
nominata qui non e' mappata. Per le dataclass la riga porta il **contratto dei
dati** — i campi, che sono cio' che quella classe promette a chi la legge. Il
verdetto e' **preso in prestito** dai blocchi eseguiti piu' sopra: nessuna classe
riceve qui un verde nuovo, e dove nessun test nomina il nome si scrive NON
MISURATA.

| riga | classe | metodi | contratto / cosa promette | test che la nominano | verdetto |
|---|---|---|---|---|---|
| 115 | `_DefaultEmbedder` | 1 | Adapter over the shared ``verimem.embedding.encode`` (model or service | 3 — `test_cli_docs.py` | esercitata dai blocchi eseguiti sopra |
| 218 | `Risultati` | 1 | I risultati di una ricerca, con quanti ne sono stati NASCOSTI. | _generico — cercato qualificato nei blocchi sopra_ | vedi i blocchi eseguiti sopra (nome generico) |
| 265 | `DocumentIndex` | 8 | Chunk-level semantic index with exact provenance over the Documents ti | 18 — `test_document_index_path_guard.py` | esercitata dai blocchi eseguiti sopra |
| 574 | `_E` | 1 | — | _generico — cercato qualificato nei blocchi sopra_ | vedi i blocchi eseguiti sopra (nome generico) |

## I metodi speciali di questo file — 2

In tabella come tutto il resto: il righello legge la seconda colonna, e in prosa
restavano fuori dal conto. **Non sono righe vuote**: i costruttori di questo
prodotto aprono file, eseguono schemi e in tre casi su otto fanno le migrazioni.
Ognuno dice cosa apre e cosa crea, letto dal corpo.

| riga | metodo | classe | cosa apre e cosa crea (letto) | verdetto |
|---|---|---|---|---|
| 253 | `__init__` | `Risultati` | 3 stmt: chiama `super().__init__` (estende una lista) e aggiunge i due contatori che il nome della classe non dice — `illeggibili` e `nascosti` | esercitato da ogni uso di `Risultati` nei blocchi sopra |
| 268 | `__init__` | `DocumentIndex` | 9 stmt: legge `HIPPO_DOCINDEX_DB` dall'ambiente, `mkdir`, `_init_db`. Costruisce due collaboratori: un `DocumentStore` (`self.docs`) e un `_DefaultEmbedder` se non gliene passano uno. Fissa `chunk_size` e `overlap` | esercitato da ogni uso di `DocumentIndex` nei blocchi sopra |

## ⚠️ Questo store NON versiona lo schema

`ensure_schema_version` compare **0 volte** in questo file, contro 3 in
`semantic.py`, 2 in `memory.py`, 3 in `entity_kg.py`; qui la migrazione esiste ma e' **a tentativo** (`ALTER TABLE` in `try/except OperationalError: pass`, righe 293-308). La tabella delle
quattro politiche, con le prove, sta in [`semantic.md`](semantic.md) — sezione
«Quattro politiche di schema in otto store».
