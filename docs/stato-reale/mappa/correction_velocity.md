# Mappa di `verimem/correction_velocity.py` — 4 righe, 138 righe di codice (lead, 09/09 01:54)

Letto per intero. Prova: pytest del lotto C sul tip `20257636` (`62 passed in 20.70s`, EXIT=0, con `tests/test_correction_velocity.py` e `tests/test_correction_semantic_relevance.py`). Chiamante letto: `verimem/briefing.py:299` (dentro `get_briefing`, che riceve `task_text`): vivo nel briefing. La bozza attribuiva a `_ts` chiamanti in `cli.py` e a `_sig_tokens` in `emerging_briefing.py`: **falsi positivi del nome** (altre `_ts`/`_sig_tokens` locali). Riusa `emerging_patterns._signature` (la firma a 4 token dell'idea #1). Claim README: nessuna riga.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/correction_velocity.py:34` `_sig_tokens` | i token della firma a 4 token, come insieme | `detect_correction_pattern` (89, 94) | via i test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 62 passed |
| 2 | `verimem/correction_velocity.py:38` `_outcome` | l'esito in minuscolo, senza spazi | `detect_correction_pattern` (98, 99) | via i test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 62 passed |
| 3 | `verimem/correction_velocity.py:42` `_ts` | `created_at` come float, 0 se assente | `detect_correction_pattern` | via i test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 62 passed |
| 4 | `verimem/correction_velocity.py:46` `detect_correction_pattern` | se la firma del task ha una storia FALLIMENTO→SUCCESSO (episodi scelti dal chiamante via `relevant_ids`, o per sovrapposizione ≥ 3 token), rende il successo correttivo (il PRIMO dopo un fallimento), i fallimenti precedenti (ultimi 3) e la latenza; `partial` non è né l'uno né l'altro | `verimem/briefing.py:299` | `tests/test_correction_velocity.py`, `tests/test_correction_semantic_relevance.py` | - | FUNZIONA COME PROMESSO | pytest 62 passed |

Reperti: (a) la firma a 4 token con soglia 3 esige task quasi identici nel fallback lessicale (dichiarato: la via viva è `relevant_ids` dal recall semantico); (b) `_FAILURE` accetta `error/fail/failed` oltre a `failure`: vocabolario allargato rispetto al `Literal` di `episode.py`, dichiarato. Nessun P0.
