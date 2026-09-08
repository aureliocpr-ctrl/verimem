# Mappa di `verimem/find_duplicates.py` — 3 righe, 73 righe di codice (lead, 09/09 01:05)

Letto per intero. Prova: pytest del lotto sul tip `20257636` (`51 passed in 17.79s`, EXIT=0, con `tests/test_find_duplicates.py`; lo nominano anche `tests/test_curate_pipeline.py` e `tests/test_find_duplicate_facts.py`). Chiamanti letti: `verimem/mcp_server.py:12029` (`hippo_skills_find_duplicates`, su `a.skills.all()`), `verimem/curate_pipeline.py:20,40` (il passo di dedup della pipeline di cura). È il gemello per le SKILL di `find_duplicate_facts` (il docstring di quello lo dice: «same idea as find_duplicate_skills»). La bozza attribuiva a `_signature` chiamanti in `anomaly_detection.py` e `correction_velocity.py`: **falsi positivi del nome**, sono altre `_signature` locali. Claim README: nessuna riga.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/find_duplicates.py:19` `_signature` | il sacchetto `[a-z0-9]+` di nome + trigger + body + pre + post | `find_duplicate_skills` (55) | `tests/test_find_duplicates.py` | - | FUNZIONA COME PROMESSO | pytest 51 passed |
| 2 | `verimem/find_duplicates.py:28` `_jaccard` | Jaccard con doppia guardia sull'unione vuota (copia n. 9 di 18) | `find_duplicate_skills` (58) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 51 passed |
| 3 | `verimem/find_duplicates.py:35` `find_duplicate_skills` | tutte le coppie a Jaccard ≥ 0,8, ordinate, tetto `top_k`; O(S²) dichiarato «sotto il secondo per S ≤ 1000» | `verimem/mcp_server.py:12029` (`hippo_skills_find_duplicates`), `verimem/curate_pipeline.py:40` | `tests/test_find_duplicates.py`, `tests/test_curate_pipeline.py` | - | FUNZIONA COME PROMESSO | pytest 51 passed |

Reperti: (a) la firma include il `body`: due skill con lo stesso corpo lungo e trigger diversi risultano duplicate (voluto per il dedup, da sapere per chi fonde); (b) il claim «sotto il secondo per S ≤ 1000» non è misurato qui (325 skill nel corpus di casa, 52.650 coppie). Nessun P0.
