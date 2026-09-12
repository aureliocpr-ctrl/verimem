# mappa — `verimem/freshness_check.py`

**owner ws6 Dati** · base `20257636` · 2026-09-09 12:37

**204 righe · 3 funzioni · 0 classi** (`ast`). **1 pubbliche, 2 private.**
Metodo e limiti: quelli di `semantic.md`, con le quattro trappole del righello già pagate.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| l'**unica pubblica** | `tests/test_il_rapporto_di_freschezza_vede_gli_scaduti.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_il_rapporto_di_freschezza_vede_gli_scaduti.py` → `4 passed, 1 warning in 8.x` EXIT=0 |
| le 2 `_private` | via il chiamante | **NON MISURATE** | — |

**Zero pubbliche senza test.**

## Inventario completo — ogni funzione per nome

**3 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 28 | `_cosine` | priv |  | 3 — `test_contradiction_year_range_false_negative.py` |
| 36 | `facts_freshness_check` | **pub** | Cycle #82 (2026-05-16) — surface stale facts and propose | 3 — `test_freshness_check.py` |
| 184 | `_bulk_load_embeddings` | priv | Fetch raw embedding BLOB for a set of fact ids in one SQL  | 🔴 **nessuno** |
