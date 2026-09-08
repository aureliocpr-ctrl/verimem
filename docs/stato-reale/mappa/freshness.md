# Mappa di `verimem/freshness.py` — 2 righe, 29 righe di codice (lead, 09/09 01:24)

Letto per intero. Prova: pytest del lotto B sul tip `20257636` (`84 passed, 1 xfailed in 37.23s`, EXIT=0, con `tests/test_freshness.py`; la nominano anche `tests/test_recall_excludes_stale_facts.py` e `tests/test_recall_rejects_future_timestamp_spoof.py`, non eseguiti qui). Chiamanti letti: `verimem/semantic.py:60` (import), `:1053` (`is_stale` nel filtro del recall), `:1024` e `:4271` (`decay_factor`, e il commento a 4270: «is_stale(floor=0.5) ⇔ age > half_life ⇔ base < now − half_life», la forma SQL dello stesso criterio). Claim README: la riga 186 («0/10 stale-leak») riguarda la supersessione, non questo decadimento; nessuna riga descrive l'emivita.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/freshness.py:15` `decay_factor` | `0,5^(età/emivita)` in [0, 1]; 1,0 se emivita ≤ 0 (spento) o età ≤ 0 (appena verificato o nel futuro) | `is_stale` (29), `verimem/semantic.py:1024,4271` | `tests/test_freshness.py` | - | FUNZIONA COME PROMESSO | pytest 84 passed |
| 2 | `verimem/freshness.py:27` `is_stale` | vero se il fattore scende sotto `floor` (0,5: cioè età > emivita) | `verimem/semantic.py:1053` (il recall) | `tests/test_freshness.py`, `tests/test_recall_excludes_stale_facts.py` | - | FUNZIONA COME PROMESSO | pytest 84 passed |

Reperti: (a) la guardia «età ≤ 0 → 1,0» è ciò che rende innocua una data nel futuro (il test dello spoof lo copre, per nome); (b) il docstring dice che lo schema `facts` non ha `last_verified_at`/`expires_at`: l'età è sempre da `created_at`, quindi un fatto riverificato non ringiovanisce (dichiarato come «mattone per FASE 4», la calibrazione per namespace non è stata fatta). Nessun P0.
