# Mappa di `verimem/corpus_size.py` — 3 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/corpus_size.py:12` `_safe_size` | funzione: File size or 0 if missing. | `verimem/corpus_size.py:49`; `verimem/corpus_size.py:51`; `verimem/corpus_size.py:53` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/corpus_size.py:22` `_dir_size` | funzione: (total bytes, file count) for a directory's immediate children | `verimem/corpus_size.py:54` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/corpus_size.py:38` `corpus_size_report` | funzione: Return disk usage per memory tier. | `verimem/corpus_size.py:68`; `verimem/curate_pipeline.py:8`; `verimem/curate_pipeline.py:78` (+5) | `tests/test_corpus_size.py`; `tests/test_curate_pipeline.py` | - | NON MISURATO | - |
