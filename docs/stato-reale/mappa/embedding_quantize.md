# Mappa di `verimem/embedding_quantize.py` — 3 righe, 92 righe di codice (lead, 09/09 02:44)

Letto per intero. Prova: pytest del lotto E sul tip `20257636` (`233 passed in 145.12s`, EXIT=0, con `tests/test_embedding_quantize.py`). Chiamanti: **nessuno in `verimem/`**; solo `scripts/bench_f16_quantize.py:48`. Il docstring (ciclo 207, 23/05) promette compressione 2× degli embedding (1536 → 768 byte per 384 dimensioni) con perdita di recall «sub-1% (community wisdom)»: la conversione esiste, **lo store non la usa** (nessun import nel prodotto). Claim README: nessuna riga (grep su «quantiz|float16» → nessuna).

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/embedding_quantize.py:27` `quantize_float16` | blob f32 di 1536 byte → f16 di 768; taglia sbagliata → invariato | il banco `scripts/bench_f16_quantize.py` | `tests/test_embedding_quantize.py` | - | MAI CHIAMATA dal prodotto | pytest 233 passed |
| 2 | `verimem/embedding_quantize.py:47` `dequantize_float16` | l'inverso; taglia sbagliata → invariato | il banco | `tests/test_embedding_quantize.py` | - | MAI CHIAMATA dal prodotto | pytest 233 passed |
| 3 | `verimem/embedding_quantize.py:67` `max_relative_error` | errore relativo massimo dopo il giro; `inf` su taglia sbagliata (dichiarato «helper for tests») | i test | `tests/test_embedding_quantize.py` | - | MAI CHIAMATA dal prodotto (helper di test nel pacchetto) | pytest 233 passed |

Reperti: (a) **modulo intero senza chiamante nel prodotto** (lista: resource_monitor, hot_reload, sos_compensator, recall_usage, codebase_ingest, coding_reflection, betweenness_cache, embedding_quantize); (b) «taglia sbagliata → invariato» significa che un blob a 768 dimensioni (un altro modello) passa senza errore né avviso: se un giorno viene cablato, il silenzio va tolto; (c) `_EXPECTED_DIM = 384` è una costante locale, non `CONFIG`: quinta copia della dimensione dell'embedder (letto: il numero è già in `embedding.py`, mappa di ws5). Nessun P0.
