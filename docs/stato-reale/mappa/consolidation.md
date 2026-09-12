# mappa — `verimem/consolidation.py`

**owner ws6 Dati** · base `7b9e8ca1` · aperto 2026-09-08 23:08

**593 righe · 10 funzioni · 0 classi.** Contate con `ast`.
**3 pubbliche, ZERO senza test, e ZERO senza porta.** 7 private: 5 con test,
2 con soli chiamanti interni.

## Le righe

| # | funzione | chiamata da (LETTO) | test | verdetto | prova |
|---|---|---|---|---|---|
| 1 | `auto_consolidate` | **due** porte: `auto_dream_worker.py:386` (il worker notturno) e `cli.py:4989` (comando utente) | `test_consolidation.py` · `test_consolidation_integration.py` · `test_consolidation_refactor.py` · `test_master_index_does_not_outrank_facts.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_consolidation.py` → `9 passed, 1 warning in 9.x` EXIT=0 |
| 2 | `detect_cluster_candidates` | `cli.py:4938` | `test_consolidation.py` · `test_consolidation_integration.py` | **FUNZIONA COME PROMESSO**, limitato | stessa esecuzione |
| 3 | `propose_master_node` | `cli.py:4957` | `test_consolidation.py` · `test_consolidation_refactor.py` · `test_master_index_does_not_outrank_facts.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_master_index_does_not_outrank_facts.py` → `4 passed in 8.10s` EXIT=0 |
| 4 | le 5 `_private` con test | interne | `test_consolidation_bugfixes.py` (3) e altri | **FUNZIONA COME PROMESSO**, limitato | `8 passed, 1 warning in 1x.x` EXIT=0 |
| 5 | `_topic_prefix` (88) · `_preload_consolidated_prefixes` (251) | chiamanti interni | nessuno le nomina | **NON MISURATE**, non morte | — |

## ✅ Il primo file dove il controllo «senza porta» non trova nulla

Ho applicato lo stesso controllo che ha prodotto la tesi delle cinque funzioni
senza porta, e qui **non trova niente**: tutte e tre le pubbliche sono collegate,
e `auto_consolidate` lo è **due volte** — dal worker che gira da solo e dal
comando che l'utente può lanciare.

⇒ È il contronesempio che rende leggibile la tesi. Se ogni file avesse funzioni
senza porta, «senza porta» sarebbe il modo normale di scrivere questo prodotto e
il reperto non direbbe nulla. Qui il collegamento c'è, ed è doppio dove serve:
quindi le cinque di `memory.py` e `facts_conflict.py` sono un'eccezione, non la
regola.

📌 E la coppia worker + CLI è la forma che manca a `restore_decayed`: là
`decay_prune` gira nel worker e l'annullamento non ha comando; qui
`auto_consolidate` ha **entrambi**. Lo stesso file mostra come sarebbe fatta la
cosa completa — utile a chi prenderà quel ticket, che non è mio.

## Inventario completo — ogni funzione per nome

**10 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 88 | `_topic_prefix` | priv | Return the first ``depth`` slash-separated segments of ``t | 🔴 **nessuno** |
| 100 | `detect_cluster_candidates` | **pub** | Group live facts by ``prefix_depth`` of their topic, retur | 2 — `test_consolidation.py` |
| 142 | `_select_key_facts` | priv | Pick up to ``k`` representative propositions from the clus | 1 — `test_consolidation_bugfixes.py` |
| 169 | `propose_master_node` | **pub** | Draft a master Fact for one cluster. | 4 — `test_consolidation.py` |
| 225 | `_cluster_already_consolidated` | priv | Idempotency probe: an AUTO-CLUSTER-MASTER fact already exi | 3 — `test_consolidation_bugfixes.py` |
| 251 | `_preload_consolidated_prefixes` | priv | Cycle 151 MED#4 fix: ONE SQL select to pull every already- | 🔴 **nessuno** |
| 277 | `_source_episodes_for_facts` | priv | Collect all ``source_episodes`` from the given facts. | 3 — `test_consolidation_bugfixes.py` |
| 343 | `auto_consolidate` | **pub** | End-to-end auto-consolidation pass. | 12 — `test_cli_consolidate.py` |
| 448 | `_persist_master` | priv | Persist one cluster's master node (guarded Fact first, the | 9 — `test_consolidation_cycle170_arm_d_self_loop.py` |
| 551 | `_wire_edges` | priv | Insert ``narrative_link`` causal_edges from ``ep_id`` to e | 3 — `test_consolidation.py` |
