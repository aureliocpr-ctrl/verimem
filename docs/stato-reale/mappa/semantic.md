# mappa — `verimem/semantic.py`

**owner ws6 Aldo** · base `7b9e8ca1` · aperto 2026-09-08 20:43

**6.690 righe · 155 funzioni · 4 classi.** Misurato con `ast`, non con grep:
`scratchpad/inventario.py verimem/semantic.py` — l'albero sintattico conta le
definizioni, `grep "def "` conterebbe anche le stringhe e i commenti.

## Metodo, e i suoi limiti dichiarati

- «chiamata da» è **letta**, non grepata: il grep trova il punto, poi si apre il
  file a quella riga e si guarda che sia una chiamata vera.
- «prova» è un comando **eseguito** con il suo esito. Dove non l'ho eseguito il
  verdetto è **NON MISURATO** e la casella dice cosa mancherebbe per misurarlo.
- Un test che passa prova **ciò che quel test asserisce**, non tutto il claim:
  dove il test copre una parte del claim, il verdetto lo dice.

## Le righe

| # | funzione (file:riga) | cosa promette | chiamata da (LETTO) | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `store` (semantic.py:2843) | «Insert or replace a fact. Backwards-compatible default returns None.» | `client.py:873` — `self.semantic.store(fact, embed="sync", purpose=purpose, …)`, unica via di scrittura dell'SDK | `tests/test_client_sdk.py` | riga 179: «the old row stays for lineage» (parziale: qui solo l'inserimento) | **FUNZIONA COME PROMESSO** (limitato a: la scrittura entra e la ricevuta torna) | `pytest -q tests/test_client_sdk.py` → `23 passed, 23 warnings in 94.91s` EXIT=0 (20:17, base 7b9e8ca1) |
| 2 | `recall` (semantic.py:4008) | «Semantic recall over facts (cosine on embeddings).» | `client.py:1343` — `hits = self.semantic.recall(query, k=k, deep=deep, …)`; `client.py:2891-2892` per il confronto normali/profondi | `tests/test_i_due_rami_di_search_portano_le_stesse_cose.py` | riga 466: «Search — optionally with history context or as of a past moment» | **FUNZIONA COME PROMESSO** (limitato a: i due rami tornano le stesse cose) | `pytest -q tests/…due_rami…py` → `4 passed, 1 warning in 12.38s` EXIT=0 (20:20, base 7b9e8ca1) |
| 3 | `supersede` (semantic.py:5806) | «Cycle #78 — declare `old_id` superseded by `new_id`.» | `client.py:979` — `_sup_res = self.semantic.supersede(…)` nel ramo same-source evolution; `client.py:3976` nella riconciliazione | `tests/test_audit_mutations.py` | riga 179: «`superseded_by` the new (never a silent overwrite — the old row stays for lineage)» · riga 521: «A fact disappears in TWO ways — retired (superseded) or quarantined» | **NON MISURATO** sul claim «the old row stays»: il test che ho eseguito prova che la mutazione è registrata nell'audit, non che la riga vecchia sopravviva. Serve una cella che legga la riga vecchia dopo il supersede. | `pytest -q tests/test_audit_mutations.py` → `27 passed, 1 warning in 15.15s` EXIT=0 (20:42, base 7b9e8ca1) |
| 4 | `recall_hybrid` (semantic.py:5101) | «Hybrid recall: semantic cosine + keyword overlap re-rank.» | — da leggere | — | riga 466 (stessa del §2) | **NON MISURATO** | nessun comando ancora |
| 5 | `supersede_chain` (semantic.py:6146) | «Cycle #81 — declare a multi-hop supersession» | — da leggere | — | riga 179 | **NON MISURATO** | nessun comando ancora |
| 6 | `store_within_budget` (semantic.py:437) | «Persist `fact` via `memory.store` without letting the INTERACTIVE call …» | — da leggere | — | — | **NON MISURATO** | nessun comando ancora |
| 7 | `audit_head_at` (semantic.py:6573) | «Stored head of the `count`-th chained mutation row (1-indexed), or …» | — da leggere | `tests/test_audit_mutations.py` (da confermare leggendo) | riga 179 (lineage) | **NON MISURATO** | nessun comando ancora |

## Contatore

**7 / 155 funzioni aperte · 3 con verdetto sostenuto da un comando eseguito ·
4 dichiarate NON MISURATO.** Le altre 148 sono nell'inventario e non sono
ancora state toccate: non hanno una riga qui perché una riga vuota si legge come
lavoro fatto.

## Da riportare al lead (non è una cura, è un reperto della mappa)

`supersede` è la funzione dietro il claim più forte del README sulla memoria —
«never a silent overwrite» — e il primo test che ho trovato a esercitarla prova
l'audit, non la sopravvivenza della riga. Se nessun test copre «the old row
stays», quel claim è appoggiato su una promessa non presidiata. Lo verifico
nella prossima finestra e, se è così, è un ticket.
