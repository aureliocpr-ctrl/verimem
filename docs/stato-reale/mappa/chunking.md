# Mappa di `verimem/chunking.py` — 3 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/chunking.py:45` `Chunk` | classe: A provenance-anchored slice of a document. | `verimem/chunking.py:8`; `verimem/chunking.py:101`; `verimem/chunking.py:111` (+4) | `tests/test_chunking.py`; `tests/test_document_index_provenance.py` | - | NON MISURATO | - |
| 2 | `verimem/chunking.py:57` `_find_boundary` | funzione: Return ``(offset, is_heading)``: where to end a chunk in ``[start, end)``. | `verimem/chunking.py:128` | `tests/test_la_citazione_esatta_del_vicino.py` | - | NON MISURATO | - |
| 3 | `verimem/chunking.py:96` `chunk_text` | funzione: Split ``text`` into overlapping, boundary-aware, provenance-anchored chunks. | `verimem/chunking.py:156`; `verimem/document_index.py:5`; `verimem/document_index.py:39` (+6) | `tests/test_chunking.py`; `tests/test_document_index.py`; `tests/test_external_f1_quality.py` (+2) | - | NON MISURATO | - |
