# mappa — `verimem/documents.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:37

**332 righe · 13 funzioni · 2 classi** (`ast`). **8 pubbliche, 4 private.**
Metodo e limiti: quelli di `semantic.md`, con le quattro trappole del righello già pagate.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **8 pubbliche** | `tests/test_documents_tier.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_documents_tier.py` → `24 passed in 8.07s` EXIT=0 |
| le 4 `_private` | via i chiamanti | **NON MISURATE** direttamente | — |

**Zero pubbliche senza test.** `test_documents_tier.py` con 24 celle è il test
più denso incontrato su un file di questa dimensione.

## Inventario completo — ogni funzione per nome

**12 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 38 | `_content_hash` | priv | sha256 esadecimale del contenuto (chiave di versione). | 🔴 **nessuno** |
| 57 | `default_db_path` | **pub** | Path di default del tier documents — DB dedicato, SEPARATO | 2 — `test_documents_tier.py` |
| 92 | `_connect` | priv |  | 47 — `test_bridge.py` |
| 97 | `_init_db` | priv |  | 🔴 **nessuno** |
| 106 | `ingest` | **pub** | Persisti uno snapshot. IDEMPOTENTE su ``(source_id, conten | 43 — `test_saas_atomic.py` |
| 172 | `ingest_file` | **pub** | Snapshot di un file (caso d'uso continuità-MD: linka un MD | 3 — `test_documents_tier.py` |
| 187 | `_row_to_doc` | priv |  | 🔴 **nessuno** |
| 194 | `get` | **pub** |  | _generico — cercato qualificato nei blocchi sopra_ |
| 202 | `get_latest` | **pub** |  | 4 — `test_documents_tier.py` |
| 213 | `list_versions` | **pub** |  | 6 — `test_documents_tier.py` |
| 231 | `list_sources` | **pub** | Elenca le fonti — SOLO la versione piu' alta di ogni ``sou | 2 — `test_documents_tier.py` |
| 258 | `search` | **pub** | Ricerca LESSICALE (non semantica) sul contenuto della vers | 220 — `test_editfmt_sensitive.py` |

### I dunder di questo file

L'inventario sopra esclude i metodi speciali, e qui sono nominati per chiudere il
conteggio: **`__init__`**. Sono costruttori e accessori di protocollo — non hanno
un claim del README, non hanno un test proprio, e sono esercitati da **ogni** uso
della loro classe: il verdetto è quello dei blocchi qui sopra, non una riga a sé.
