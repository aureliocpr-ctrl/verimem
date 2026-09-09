# Mappa di `verimem/parallel_drafter.py` — 2 righe, 89 righe di codice (lead, 09/09 03:54)

Letto per intero. Prova: pytest del lotto G sul tip `20257636` (`117 passed, 1 skipped in 94.44s`, EXIT=0, con `tests/test_parallel_drafter.py`). Chiamanti: **nessuno** (`git grep` su `verimem/ scripts/ benchmark/` → solo il modulo e il test). Ciclo 228 (23/05), ipotesi H8c: `ThreadPoolExecutor` sul drafter delle skill emergenti, con i caveat dichiarati (vince solo per N ≥ 8, sequenziale per N = 1, GIL su Windows). Claim README: nessuna riga.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/parallel_drafter.py:38` `parallel_draft_communities` | le bozze nello STESSO ordine delle comunità; `[]` se vuoto; sequenziale con una sola; pool a 4 | nessuno | `tests/test_parallel_drafter.py` | - | MAI CHIAMATA | pytest 117 passed |
| 2 | `verimem/parallel_drafter.py:71` `parallel_draft_communities._one` | il lavoratore: una bozza o uno stub vuoto se il drafter alza | `parallel_draft_communities` (85) | via il test | - | MAI CHIAMATA (plumbing) | pytest 117 passed |

Reperti: (a) **dodicesimo modulo senza chiamante**: la pipeline delle skill emergenti (`emerging_*`, `skill_drafter`, mappe di ws5/ws1) chiama il drafter sequenziale; il «sub-linear» di H8c non è mai stato acceso nel prodotto; (b) il caveat «only a clear win for N ≥ 8» sta nel docstring e non nel codice: la soglia di fallback è 1, non 8 (letto). Nessun P0.
