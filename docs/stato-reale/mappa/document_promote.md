# mappa — `verimem/document_promote.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:37

**258 righe · 2 funzioni · 0 classi** (`ast`). **2 pubbliche, 0 private.**
Metodo e limiti: quelli di `semantic.md`, con le quattro trappole del righello già pagate.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **2 pubbliche** (zero private) | `tests/test_document_promote.py` · `tests/test_la_citazione_mostrata_e_quella_cercabile.py` · `test_il_vanto_entrava_dalla_porta_dei_documenti.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_document_promote.py` → `3 passed, 23 warnings` EXIT=0 · `test_la_citazione_mostrata_e_quella_cercabile.py` → `4 passed, 1 warning in 6.x` EXIT=0 |

**Zero pubbliche senza test**, e **tre** file dedicati per due funzioni: è il
rapporto test/funzione più alto della mia parte. Il nome del terzo
(«il vanto entrava dalla porta dei documenti») dice che qui un difetto c'è già
stato ed è presidiato.

## Inventario completo — ogni funzione per nome

**2 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 34 | `chunk_citation` | **pub** | The exact, checkable citation of a chunk: ``file:<source_i | 1 — `test_la_citazione_mostrata_e_quella_cercabile.py` |
| 39 | `promote_chunk_to_fact` | **pub** | Store ``hit`` (a DocumentIndex search result) as a gated F | 6 — `test_document_promote.py` |
