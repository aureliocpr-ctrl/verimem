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
| 3 | `supersede` (semantic.py:5806) | «Cycle #78 — declare `old_id` superseded by `new_id`.» | `client.py:979` — `_sup_res = self.semantic.supersede(…)` nel ramo same-source evolution; `client.py:3976` nella riconciliazione | `tests/test_entity_supersede_leak.py::test_get_live_only_excludes_superseded` · `tests/test_deep_recall_asof.py` · `tests/test_audit_mutations.py` | riga 179: «`superseded_by` the new (never a silent overwrite — the old row stays for lineage)» · riga 521: «A fact disappears in TWO ways — retired (superseded) or quarantined» | **FUNZIONA COME PROMESSO** sul claim «the old row stays» — ⚠️ ma il presidio più diretto NON passa dalla funzione: vedi la nota sotto la tabella | `pytest -q tests/test_entity_supersede_leak.py` → `4 passed in 7.40s` EXIT=0 · `tests/test_deep_recall_asof.py` → `6 passed in 10.65s` EXIT=0 · `tests/test_audit_mutations.py` → `27 passed in 15.15s` EXIT=0 (tutti 20:35, base 7b9e8ca1) |
| 4 | `recall_hybrid` (semantic.py:5101) | «Hybrid recall: semantic cosine + keyword overlap re-rank.» | — da leggere | — | riga 466 (stessa del §2) | **NON MISURATO** | nessun comando ancora |
| 5 | `supersede_chain` (semantic.py:6146) | «Cycle #81 — declare a multi-hop supersession» | — da leggere | — | riga 179 | **NON MISURATO** | nessun comando ancora |
| 6 | `store_within_budget` (semantic.py:437) | «Persist `fact` via `memory.store` without letting the INTERACTIVE call …» | — da leggere | — | — | **NON MISURATO** | nessun comando ancora |
| 7 | `audit_head_at` (semantic.py:6573) | «Stored head of the `count`-th chained mutation row (1-indexed), or …» | — da leggere | `tests/test_audit_mutations.py` (da confermare leggendo) | riga 179 (lineage) | **NON MISURATO** | nessun comando ancora |

## Contatore

**7 / 155 funzioni aperte · 3 con verdetto sostenuto da un comando eseguito ·
4 dichiarate NON MISURATO.** Le altre 148 sono nell'inventario e non sono
ancora state toccate: non hanno una riga qui perché una riga vuota si legge come
lavoro fatto.

## Il reperto della riga 3, e la sua correzione

**Primo sospetto, e ERA SBAGLIATO**: avevo scritto che il claim README:179
(«never a silent overwrite — the old row stays for lineage») poteva non essere
presidiato, perché il primo test che avevo trovato (`test_audit_mutations`)
prova l'audit della mutazione e non la sopravvivenza della riga. Cercato meglio:
il presidio **c'è**, ed è esplicito —

```python
# tests/test_entity_supersede_leak.py::test_get_live_only_excludes_superseded
assert sm.get("old01") is not None, "plain get must still resolve any id"
assert sm.get("old01", live_only=True) is None, "live_only get must hide a superseded fact"
```
`pytest -q tests/test_entity_supersede_leak.py` → `4 passed in 7.40s` EXIT=0.

**Ma cercandolo ho trovato una cosa più fine, e questa resta.** Quel test
supersede così:

```python
def _supersede(sm, old_id, new_id):
    with sm._connect() as conn:
        conn.execute("UPDATE facts SET superseded_by = ? WHERE id = ?", (new_id, old_id))
```

cioè **in SQL diretto, senza chiamare `semantic.supersede()`**. Presidia
l'invariante dello STORE (una riga marcata resta leggibile), non il
comportamento della FUNZIONE che il README nomina. Se un giorno
`semantic.supersede()` cancellasse la riga invece di marcarla, questo test
resterebbe verde.

⇒ Il claim è coperto **sul dato**, non **sulla funzione**. Non è un difetto e
non apro un ticket: è la distinzione che questa mappa serve a rendere visibile,
e la scrivo qui perché il verdetto «FUNZIONA COME PROMESSO» della riga 3 non
venga letto come «`supersede()` è presidiata».

📌 Metodo, per le prossime 148 righe: il primo test che nomina una funzione non
è necessariamente il test che presidia il suo claim, e un test che presidia il
claim non è necessariamente un test di quella funzione. Vanno guardate e dette
come due cose diverse.
