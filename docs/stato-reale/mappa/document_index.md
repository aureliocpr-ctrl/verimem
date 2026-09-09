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

### I dunder di questo file

L'inventario sopra esclude i metodi speciali, e qui sono nominati per chiudere il
conteggio: **`__init__`**. Sono costruttori e accessori di protocollo — non hanno
un claim del README, non hanno un test proprio, e sono esercitati da **ogni** uso
della loro classe: il verdetto è quello dei blocchi qui sopra, non una riga a sé.
