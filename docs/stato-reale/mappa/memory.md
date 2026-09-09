# mappa — `verimem/memory.py`

**owner ws6 Aldo** · base `7b9e8ca1` · aperto 2026-09-08 21:50

**2.718 righe · 83 funzioni · 1 classe (`EpisodicMemory`).** Contate con `ast`
(`scratchpad/inventario.py`), non con grep.

Metodo e limiti: gli stessi dichiarati in `semantic.md`. In più, da lì porto
quattro trappole già pagate: il nome cercato con la parentesi non vede i
**callback**; escludere il file stesso fa sembrare morti gli helper interni;
cercare solo in `verimem/` e `tests/` dimentica `benchmark/`; e il nome nudo dei
metodi generici pesca ogni dizionario.

## Le righe

| # | funzione (file:riga) | cosa promette | chiamata da (LETTO) | test | claim | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `decay_prune` (memory.py:1363) | «Delete episodes whose retention < threshold. Returns the set …» | **`sleep.py:1104`** — e **nessuna porta**: 0 occorrenze in `cli.py`, `mcp_server.py`, `gateway.py` | `tests/test_audit_mutations_episodic.py` · `tests/test_causal_edge_gc.py` | riga 708: «True forget (GDPR): deleted data cannot resurface» | **FUNZIONA COME PROMESSO**, limitato a ciò che il test asserisce | `pytest -q tests/test_audit_mutations_episodic.py` → `15 passed, 1 warning in 10.x` EXIT=0 |
| 2 | `restore_decayed` (memory.py:1455) | «Reverse a decay prune (A-7). Re-inserts archived episodes + traces» | 🔴 **nessuno**: 0 occorrenze in `cli.py`, `mcp_server.py`, `gateway.py`, `client.py` e in tutto `verimem/`. L'unico uso è `tests/test_decay_prune_undo.py:30` | `tests/test_decay_prune_undo.py` | riga 708 — è la garanzia che la rende vera | **FUNZIONA COME PROMESSO** — ma vedi il reperto sotto | `pytest -q tests/test_decay_prune_undo.py` → `2 passed, 1 warning in 9.8s` EXIT=0 |
| 3 | `store` (memory.py:552) | «Insert or replace an episode. Backwards-compatible default returns None.» | `store_within_budget` (semantic.py:437) per gli episodi; `mcp_server.py:9402` | `tests/test_deferred_write_durability.py` | — | **FUNZIONA COME PROMESSO**, limitato | `3 passed in 9.32s` EXIT=0 |
| 4 | `audit_head_at` (memory.py:2645) | «The episodic chain head AS OF the `count`-th chained row» | — da leggere; ⚠️ **omonima** di quella in `semantic.py:6573`: due catene, non un duplicato | `tests/test_audit_mutations_episodic.py` | riga 244 («audit every revision») | **FUNZIONA COME PROMESSO**, limitato | `15 passed` EXIT=0 |
| 5 | `set_pinned` (memory.py:1326) | «pin/unpin an episode. Pinned episodes are …» | `mcp_server.py:9050` e `:9062` — esposta dalla porta MCP | `tests/test_episode_decay.py` | — | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_episode_decay.py` → `10 passed, 1 warning in 9.x` EXIT=0 |
| 6 | `store_batch` (memory.py:818) | «CYCLE #18 — bulk insert con batch embedding.» | `mcp_server.py:9334` · `transcript_ingest.py:124` | `tests/test_memory.py` | — | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_memory.py` → `5 passed, 1 warning in 9.7s` EXIT=0 |
| 7 | `by_outcome` (memory.py:1565) | gli episodi con un dato esito | usata dai test e dalla porta di ricerca | `tests/test_memory.py` · `tests/test_mcp_search_and_list.py` | — | **FUNZIONA COME PROMESSO**, limitato | `5 passed` EXIT=0 · `13 passed, 1 warning in 9.x` EXIT=0 |
| 8 | **`by_task`** (memory.py:1573) | gli episodi di un dato task | 🔴 **NESSUNO** | 🔴 **nessuno** | — | 🔴 **MAI CHIAMATA** — vedi sotto | `grep -rnw by_task .` (tutto il repo, ogni tipo di file) → **1 riga: la definizione** |
| 9 | `decay_pruning_candidates` (memory.py:1292) | «Episodes whose Ebbinghaus retention falls below the threshold.» | il ciclo di sonno, con `decay_prune` | `tests/test_episode_decay.py` | riga 708 | **FUNZIONA COME PROMESSO**, limitato | `10 passed` EXIT=0 |
| 10 | `add_causal_edge` · `causal_graph` (1530, 1539) | il grafo causale fra episodi | — da leggere | `tests/test_memory.py` · `e2e_cycle51_54_chain.py` | — | **FUNZIONA COME PROMESSO**, limitato | `5 passed` EXIT=0 |
| 11 | `delete` · `delete_by_task_text` · `count` · `all` · `get` | la famiglia di lettura/cancellazione degli episodi | 4 file di test le coprono insieme | `tests/test_memory_delete.py` · `tests/test_audit_mutations_episodic.py` | riga 289 («True forget») | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_memory_delete.py` → `6 passed, 1 warning in 10.x` EXIT=0 |
| 12 | `is_pinned` (memory.py:1336) | «check whether an episode is currently pinned» | 🔴 nessun chiamante di prodotto: `mcp_server.py` **0** occorrenze | `tests/test_memory_pin.py` | — | **FUNZIONA COME PROMESSO** — ma senza porta, vedi sotto | `pytest -q tests/test_memory_pin.py` → `4 passed, 1 warning in 7.7s` EXIT=0 |
| 13 | `pinned_episodes` (memory.py:1345) | «list every pinned episode, newest-first» | `briefing.py:150` — uso **interno**; `mcp_server.py` **0**, `cli.py` **0** | `tests/test_briefing.py` | — | **FUNZIONA COME PROMESSO** — ma senza porta | `pytest -q tests/test_briefing.py` → `8 passed in 7.60s` EXIT=0 |
| 14 | `salience_of` (memory.py:1258) | «Read the cached salience score for an episode.» | nessun chiamante di prodotto: solo `tests/test_salience_recall.py` | `tests/test_salience_recall.py` | — | **FUNZIONA COME PROMESSO**, limitato | `8 passed, 1 warning in 9.3s` EXIT=0 |
| 15 | `compute_salience` (memory.py:1080) | «Prediction-error surprise of `episode` vs the centroid…» | nessun chiamante di prodotto; citata in `docs/archive/2026-05-13_FORGIA.md:616` | `tests/test_episode_save_encode_circuit_breaker.py` | — | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_episode_save_encode_circuit_breaker.py` → `5 passed, 1 warning in 8.4s` EXIT=0 |
| 16 | `backfill_pending_embeddings` (memory.py:755) | «Embed episodes persisted with the DEFER sentinel» | `cli.py:4755` — esposta dalla CLI | `tests/test_backfill_heals_model_mismatch.py` | — | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_backfill_heals_model_mismatch.py` → `5 passed in 7.66s` EXIT=0 |
| 17 | `recall_explain` (memory.py) | il perché di un richiamo | `mcp_server.py:9178` — esposta da MCP | `tests/test_mcp_lineage_explain_top.py` | — | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_mcp_lineage_explain_top.py` → `13 passed, 1 warning in 7.x` EXIT=0 |
| 18 | `cluster_similar` (memory.py) | raggruppa episodi simili | `dream.py:293` — il consolidamento | `benchmark/bench.py` | — | **FUNZIONA COME PROMESSO**, limitato — ⚠️ e il suo test non è solo `benchmark/bench.py`: `tests/test_memory.py` e `tests/perf/test_perf.py` la nominano | `pytest -q tests/test_memory.py` → `5 passed, 1 warning in 9.7s` EXIT=0 |

## 🔴 Il reperto: si pota da soli, si ripristina solo scrivendo codice

```
decay_prune       cli 0 · mcp 0 · gateway 0 · sleep.py 2   ← gira DA SE'
restore_decayed   cli 0 · mcp 0 · gateway 0 · client 0     ← NESSUNA PORTA
```

`memory.py:1393` dichiara la garanzia — «so a mis-fired decay is reversible via
`restore_decayed()`» — e `memory.py:332` la ripete sullo schema delle tracce. La
funzione esiste, è corretta e ha un test verde. **Ma non è raggiungibile da
nessuna superficie del prodotto**: la potatura parte da sola nel ciclo di sonno,
l'annullamento richiede di aprire un interprete Python e chiamare un metodo.

⇒ Non è un difetto della funzione: il verdetto della riga 2 resta FUNZIONA COME
PROMESSO. È un'**asimmetria fra le due direzioni** — automatica la perdita,
manuale il recupero. Il README riga 708 vende «True forget (GDPR): deleted data
cannot resurface»: il verso della cancellazione è presidiato, quello del
ripristino non ha porta.

📌 **Non l'ho scoperto da zero, e lo dico**: `docs/stato-reale/00-ESAME.md:1636`
(cella W2-119, ws2) analizza già `decay_prune` in profondità — i tre presidi nel
codice, `episodes_undo_log` a 0 righe, `action='decay'` a 0 in tutti i database,
e la chiusura in positivo (i 28 episodi non erano di casa, stavano in store
temporanei). Quella cella chiede se i presidi sono **verificabili**; questa riga
chiede se sono **raggiungibili**. Sono due domande diverse sulla stessa funzione,
e la seconda non era stata fatta.


## 🔴 `by_task` (1573) — il primo MAI CHIAMATA della mappa, e regge alla verifica

Il mandato dice che questo verdetto porta a **proporre la rimozione**, quindi
prima ho applicato la regola che avevo scritto io dopo i tre falsi morti di
`semantic.py`:

| controllo | esito |
|---|---|
| nome **nudo** in tutto il repo, **ogni tipo di file** (non solo `.py`/`.md`) | **1 riga: la definizione stessa** |
| chiamanti **dentro** il file | nessuno |
| richiami **dinamici** (`getattr`, dispatch, la stringa `"by_task"`) | nessuno |
| test che la nominano | nessuno |
| documenti che la citano | nessuno |

E il **controllo che la rende leggibile**: il suo gemello di due righe sopra,
`by_outcome` (1565), stessa firma e stessa forma, **è usato** — compare in
`tests/test_memory.py` e `tests/test_mcp_search_and_list.py`, entrambi verdi.
Quindi non è la famiglia a essere morta: è questa funzione, scritta per
simmetria con l'altra e mai chiamata da nessuno.

⇒ **PROPOSTA: rimozione.** Non la eseguo — durante la mappa non si cura — e la
consegno con il comando che la sostiene. Chi la prende verifichi che non sia
parte di un'API pubblica documentata altrove che non ho cercato (l'ho cercata in
`README`, `CHANGELOG` e `docs/`: zero).

📌 Vale la pena dire **quanto è costato arrivare a un morto vero**: in
`semantic.py` tre righelli diversi mi avevano dato 1, 91 e 2 falsi morti, tutti
smentiti. Qui il metodo corretto dà **1 su 88 funzioni pubbliche fra i due file**
(41 in `semantic.py`, 47 in `memory.py`, contate con `ast`). Un tasso del genere è la ragione per cui il verdetto MAI CHIAMATA va
speso solo dopo tutti e cinque i controlli della tabella qui sopra.


## 🔴 Il filo che lega i tre reperti: `memory.py` espone le AZIONI, non le LETTURE

Tre righe diverse, tre volte la stessa forma. Non l'avevo cercata: è emersa
mappando.

```
① restore_decayed   si POTA da soli (sleep.py:1104) · si RIPRISTINA solo da Python
② is_pinned         si PINNA da MCP (4 occorrenze) · non si CHIEDE (0 · 0)
   pinned_episodes  usata da briefing.py:150 · non si ELENCA (mcp 0, cli 0)
③ salience_of       calcolata e messa in cache · nessuna porta la legge
```

Misurato, un comando per riga:

| domanda | comando | esito |
|---|---|---|
| si può pinnare da MCP? | `grep -c "episode_pin\|episode_unpin" verimem/mcp_server.py` | **4** |
| si può chiedere se è pinnato? | `grep -c is_pinned verimem/mcp_server.py` | **0** |
| si può elencare i pinnati? | `grep -c pinned_episodes verimem/mcp_server.py` · `cli.py` | **0** · **0** |
| si può annullare una potatura? | `grep -c restore_decayed` su cli/mcp/gateway/client | **0** ovunque |

⇒ Un agente che usa la porta MCP **può cambiare lo stato di un episodio e non
può interrogarlo**. Vede l'effetto — gli episodi pinnati compaiono nel briefing,
perché `briefing.py:150` chiama `pinned_episodes` internamente — ma non può
chiedere *quali* siano, né verificare che il proprio `pin` abbia avuto effetto.

**Nessuna delle funzioni è rotta**: tutte hanno il verdetto FUNZIONA COME
PROMESSO con la loro prova. Il reperto è **dove finiscono**: la scrittura arriva
alla porta, la lettura dello stato che quella scrittura ha cambiato no.

📌 Non apro ticket e non curo. Lo consegno come **tesi della mappa su questo
file**, perché una singola riga non l'avrebbe mostrata: serviva vederne tre.


## Le `_private` di `memory.py`: 35, a blocchi

**35 `_private`** (contate con `ast`): **16** nominate da almeno un test, **19**
da nessuno. Stessa forma di `semantic.md`: il blocco è l'unità, il verdetto vale
per il blocco, e il limite è dichiarato.

| blocco (test) | `_private` coperte | prova |
|---|---|---|
| `test_dg_cabling.py` | 2 — `_dg_projection`, `_global_dg_projection` | `6 passed, 1 warning in 9.4s` EXIT=0 |
| `test_context_engine.py` | 1 — `_normalize` | `7 passed in 7.53s` EXIT=0 |
| `test_episode_batch_screen.py` | 1 — `_screen_episode_inplace` | `5 passed, 1 warning in 8.1s` EXIT=0 |
| `test_episode_embedding_model_isolation.py` | 1 — `_migration_v6_embedding_model` | `8 passed, 1 warning in 9.6s` EXIT=0 |
| `test_due_processi_non_rieseguono_la_migrazione.py` | 1 — `_migration_v2_salience_columns` | `5 passed in 9.72s` EXIT=0 |
| `test_slow_txn_telemetry.py` · `test_entity_live_latency.py` · `test_bridge.py` · `test_episode_telemetry_cleanup.py` | 4 — `_slow_txn_warn_s`, `_work`, `_connect`, e il cleanup | da eseguire |

### Le 19 senza test: due meritavano di essere aperte, e nessuna è morta

**① Le migrazioni.** Quattro delle sei (`_migration_v1_initial_schema`,
`v3_dg_embedding`, `v4_context_embedding`, `v5_pinned`) non sono nominate da
nessun test; **v2 e v6 sì**. Ma tutte e sei sono **registrate insieme** in una
lista:

```
memory.py:274-279
    (1, _migration_v1_initial_schema),
    (2, _migration_v2_salience_columns),
    …
    (6, _migration_v6_embedding_model),
```

⇒ La porta è una sola e la esercita chi apre uno store: `test_dg_cabling.py`
manipola `_schema_version` degli episodi e passa (`6 passed` EXIT=0). Il fatto
che due su sei siano nominate e quattro no **non è una differenza di copertura**:
è una differenza di quali migrazioni hanno avuto un difetto proprio da
presidiare. Verdetto: **FUNZIONA COME PROMESSO** per il gruppo.

**② `_archive_episodes_for_undo` (1413)** — e questa vale più delle altre
diciotto. È **il primo dei tre presidi del decay** citati nella cella W2-119 di
ws2: *«`_archive_episodes_for_undo()` **prima** del delete»*, cioè ciò che rende
possibile `restore_decayed`. Nessun test la nomina, ma è chiamata a
`memory.py:1394`, **dentro `decay_prune`**, quindi la esercita
`tests/test_decay_prune_undo.py` (`2 passed` EXIT=0) — che è precisamente il test
che verifica che l'annullamento funzioni.

⇒ **FUNZIONA COME PROMESSO**, per via indiretta. E il legame si chiude: la
garanzia della riga 2 (`restore_decayed`) poggia su questa funzione, e il test
che prova l'una prova anche l'altra. Il reperto della riga 2 resta quello che
era — **manca la porta, non il presidio.**

## Inventario completo — ogni funzione per nome

**82 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 55 | `_slow_txn_warn_s` | priv | Twin of semantic._slow_txn_warn_s (kept local: no cross-im | 1 — `test_slow_txn_telemetry.py` |
| 83 | `_encode_episode_within_budget` | priv | Encode an episode summary for a store, returning None if i | 🔴 **nessuno** |
| 149 | `_dg_serialize` | priv | Pack a k-sparse `d_expand` float32 vector to the on-disk f | 🔴 **nessuno** |
| 168 | `_dg_deserialize` | priv | Reconstruct the dense `d_expand` float32 vector from the | 🔴 **nessuno** |
| 180 | `_global_dg_projection` | priv | Cached W_dg matrix shared by every `EpisodicMemory` instan | 1 — `test_dg_cabling.py` |
| 194 | `_migration_v2_salience_columns` | priv | v1 → v2: add the columns required by salience-weighted rec | 1 — `test_due_processi_non_rieseguono_la_migrazione.py` |
| 212 | `_migration_v1_initial_schema` | priv | v0 → v1: stamp the original schema (already applied via | 🔴 **nessuno** |
| 221 | `_migration_v3_dg_embedding` | priv | v2 → v3: add a `dg_embedding` BLOB column for FORGIA pezzo | 🔴 **nessuno** |
| 231 | `_migration_v4_context_embedding` | priv | v3 → v4: add a `context_embedding` BLOB column for FORGIA  | 🔴 **nessuno** |
| 241 | `_migration_v5_pinned` | priv | v4 → v5: add `pinned INTEGER NOT NULL DEFAULT 0` for FORGI | 🔴 **nessuno** |
| 253 | `_migration_v6_embedding_model` | priv | v5 → v6 (2026-06-03): add `embedding_model TEXT` per-riga  | 1 — `test_episode_embedding_model_isolation.py` |
| 283 | `_normalize` | priv | Unit-norm a vector. Pure-numpy, no sklearn dep. Matches th | 5 — `test_context_engine.py` |
| 98 | `_work` | priv |  | 1 — `test_entity_live_latency.py` |
| 427 | `_connect` | priv |  | 47 — `test_bridge.py` |
| 455 | `_screen_episode_inplace` | priv | Defang injection + redact secrets in an episode's free-tex | 2 — `test_episode_batch_screen.py` |
| 516 | `_store_episode_telemetry` | priv | Route a cross-LLM call-telemetry episode to a SEPARATE | 1 — `test_episode_telemetry_cleanup.py` |
| 552 | `store` | **pub** | Insert or replace an episode. Backwards-compatible default | _generico — cercato qualificato nei blocchi sopra_ |
| 755 | `backfill_pending_embeddings` | **pub** | Embed episodes persisted with the DEFER sentinel (empty | 7 — `test_backfill_heals_model_mismatch.py` |
| 818 | `store_batch` | **pub** | CYCLE #18 — bulk insert con batch embedding. | 6 — `test_episode_batch_screen.py` |
| 976 | `_dg_projection` | priv | Return the deterministic W_dg projection (cached process-w | 1 — `test_dg_cabling.py` |
| 984 | `_backfill_dg_embeddings` | priv | Compute and persist `dg_embedding` for any episode that | 2 — `test_dg_backfill_batched.py` |
| 1038 | `_ensure_dg_index` | priv | Build (or reuse) an in-memory matrix of DG-encoded vectors | 3 — `test_e2e_memory_integration.py` |
| 1080 | `compute_salience` | **pub** | Prediction-error surprise of `episode` vs the centroid of  | 4 — `test_episode_save_encode_circuit_breaker.py` |
| 1148 | `_compute_novelty` | priv | Novelty axis ∈ [0,1]: 1 - max(cosine to k nearest neighbou | 🔴 **nessuno** |
| 1165 | `_compute_valence` | priv | Valence axis ∈ [0,1]: absolute affective load — fraction o | 🔴 **nessuno** |
| 1185 | `_compute_task` | priv | Task axis ∈ [0,1]: cosine(episode, current_goal_focus). | 🔴 **nessuno** |
| 1200 | `_compute_repetition` | priv | Repetition axis ∈ [0,1]: log(1+count_same_task_id) / | 🔴 **nessuno** |
| 1225 | `compute_salience_4d` | **pub** | 4D importance composite (SCM cycle 141). | 1 — `test_salience_4d.py` |
| 1258 | `salience_of` | **pub** | Read the cached salience score for an episode. | 1 — `test_salience_recall.py` |
| 1267 | `_raw_cosine_recall` | priv | Internal cosine top-k WITHOUT side effects. | 1 — `test_episode_save_encode_circuit_breaker.py` |
| 1292 | `decay_pruning_candidates` | **pub** | Episodes whose Ebbinghaus retention falls below the thresh | 4 — `test_curate_pipeline.py` |
| 1326 | `set_pinned` | **pub** | FORGIA #197: pin/unpin an episode. Pinned episodes are | 2 — `test_mcp_pin_metrics.py` |
| 1336 | `is_pinned` | **pub** | FORGIA #197: check whether an episode is currently pinned. | 2 — `test_mcp_pin_metrics.py` |
| 1345 | `pinned_episodes` | **pub** | FORGIA #197: list every pinned episode, newest-first. | 3 — `test_briefing.py` |
| 1363 | `decay_prune` | **pub** | Delete episodes whose retention < threshold. Returns the s | 5 — `test_audit_mutations_episodic.py` |
| 1413 | `_archive_episodes_for_undo` | priv | Snapshot ``ids`` (full episode rows + their traces) into | 🔴 **nessuno** |
| 1455 | `restore_decayed` | **pub** | Reverse a decay prune (A-7). Re-inserts archived episodes  | 1 — `test_decay_prune_undo.py` |
| 1508 | `_bump_access_tracking` | priv | Atomic update of `last_accessed_at` and `access_count` for | 🔴 **nessuno** |
| 1530 | `add_causal_edge` | **pub** |  | 5 — `e2e_cycle51_54_chain.py` |
| 1539 | `causal_graph` | **pub** |  | 2 — `test_mcp_lineage_trace.py` |
| 1549 | `get` | **pub** |  | _generico — cercato qualificato nei blocchi sopra_ |
| 1557 | `all` | **pub** |  | _generico — cercato qualificato nei blocchi sopra_ |
| 1565 | `by_outcome` | **pub** |  | 4 — `test_audit_summary.py` |
| 1573 | `by_task` | **pub** |  | 🔴 **nessuno** |
| 1581 | `_db_data_version` | priv | Cross-process cache-coherence probe — mirror of SemanticMe | 3 — `test_episode_index_cross_process.py` |
| 1608 | `_ensure_recall_index` | priv | Lazily build / rebuild the in-memory recall index. | 5 — `bench.py` |
| 1667 | `_batch_get_episodes` | priv | Fetch many episodes (with traces) in two queries instead o | 🔴 **nessuno** |
| 1692 | `recall` | **pub** | Top-k episodes ranked by `cosine + α × salience + β × rece | _generico — cercato qualificato nei blocchi sopra_ |
| 1931 | `_rerank_and_finalise` | priv | Compose `cosine + α·salience + β·recency + γ·context_cos` | 1 — `test_episode_recall_nonfinite.py` |
| 1989 | `recall_by_context` | **pub** | Top-k episodes ranked by cosine on `context_embedding` onl | 5 — `test_e2e_memory_integration.py` |
| 2052 | `cluster_similar` | **pub** | Greedy clustering: episodes with cos-sim ≥ threshold to a  | 3 — `bench.py` |
| 2089 | `count` | **pub** | Total episode count, optionally filtered by outcome. | _generico — cercato qualificato nei blocchi sopra_ |
| 2106 | `clear` | **pub** | Wipe every episode/trace/edge. ``principal`` is MANDATORY  | _generico — cercato qualificato nei blocchi sopra_ |
| 2127 | `skill_outcome_breakdown` | **pub** | FORGIA pezzo #157: outcome → count for episodes that used  | 1 — `test_memory_skill_outcome.py` |
| 2141 | `skill_co_occurrence` | **pub** | FORGIA pezzo #158: count which other skills appear with `s | 3 — `test_memory_skill_cooccurrence.py` |
| 2168 | `skill_bundle_candidates` | **pub** | FORGIA pezzo #160: skill-pair bundle candidates. | 4 — `test_mcp_compound_skills.py` |
| 2207 | `update_salience` | **pub** | FORGIA pezzo #175: in-place salience update bypassing comp | 2 — `test_sleep_synaptic_tagging.py` |
| 2224 | `synaptic_tag_candidates` | **pub** | FORGIA pezzo #174: synaptic tagging (Frey & Morris 1997). | 2 — `test_memory_synaptic_tag.py` |
| 2276 | `negative_bundle_candidates` | **pub** | FORGIA pezzo #169: lateral inhibition — pair → failure det | 2 — `test_memory_negative_bundles.py` |
| 2317 | `average_episode_age_s` | **pub** | FORGIA pezzo #153: mean age in seconds across all episodes | 1 — `test_memory_avg_age.py` |
| 2333 | `steps_summary` | **pub** | FORGIA pezzo #144: aggregate stats on number of steps per  | 2 — `test_memory_steps_summary.py` |
| 2355 | `outcome_breakdown` | **pub** | FORGIA pezzo #143: dict outcome → count for every distinct | 3 — `test_corpus_diff.py` |
| 2368 | `skill_usage_histogram` | **pub** | FORGIA pezzo #139: dict skill_id → number of episodes that | 4 — `test_memory_skill_histogram.py` |
| 2403 | `token_usage_summary` | **pub** | FORGIA pezzo #137: aggregate token usage stats across all  | 3 — `test_memory_method_aliases.py` |
| 2431 | `token_usage_stats` | **pub** | Alias di `token_usage_summary` per backward-compat col MCP | 4 — `test_audit_summary_integration.py` |
| 2435 | `recall_explain` | **pub** | CYCLE #11 — versione strutturata di `recall` con breakdown | 3 — `test_mcp_lineage_explain_top.py` |
| 2469 | `episodes_last_n_minutes` | **pub** | FORGIA pezzo #135: episodi degli ultimi N minuti. | 1 — `test_memory_window.py` |
| 2483 | `episodes_in_window` | **pub** | FORGIA pezzo #134: episodi creati in [start_ts, end_ts). | 1 — `test_memory_window.py` |
| 2503 | `find_by_task_text` | **pub** | FORGIA pezzo #110: exact-match query on task_text. | 1 — `test_memory_find_by_task_text.py` |
| 2523 | `search_episodes` | **pub** | FORGIA pezzo #195: substring/keyword search over `task_tex | 3 — `test_mcp_search_and_list.py` |
| 2563 | `delete_by_task_text` | **pub** | FORGIA pezzo #111: cancella tutti gli episodi con questo t | 2 — `test_audit_mutations_episodic.py` |
| 2579 | `delete` | **pub** | FORGIA pezzo #109: delete one episode + its traces + edges | _generico — cercato qualificato nei blocchi sopra_ |
| 2623 | `audit_verify` | **pub** | First tampered ``audit_mutations`` row id in episodes.db,  | 5 — `test_adjudication_log_chain.py` |
| 2631 | `audit_head` | **pub** | Current episodic mutation-chain head (archive off-box). | 4 — `test_adjudication_log_chain.py` |
| 2637 | `audit_count` | **pub** | Number of chained rows in the episodic mutation chain — th | 1 — `test_tamper_anchor_receipt.py` |
| 2645 | `audit_head_at` | **pub** | The episodic chain head AS OF the ``count``-th chained row | 1 — `test_tamper_anchor_receipt.py` |
| 2653 | `gc_orphan_causal_edges` | **pub** | Delete causal_edges whose src OR dst episode no longer exi | 2 — `test_audit_mutations_episodic.py` |
| 2680 | `_load_traces` | priv |  | 🔴 **nessuno** |
| 2689 | `_row_to_episode` | priv |  | 🔴 **nessuno** |
| 1016 | `_flush` | priv |  | 🔴 **nessuno** |
| 1765 | `_keyword_fallback` | priv |  | 🔴 **nessuno** |
| 2694 | `_col` | priv |  | 🔴 **nessuno** |

## Le classi di questo file — 1 sulla superficie

Il righello del lead conta le **classi** nel denominatore (480 sui miei 21 file
contro i 449 di sole funzioni): una classe e' superficie, e finche' non e'
nominata qui non e' mappata. Per le dataclass la riga porta il **contratto dei
dati** — i campi, che sono cio' che quella classe promette a chi la legge. Il
verdetto e' **preso in prestito** dai blocchi eseguiti piu' sopra: nessuna classe
riceve qui un verde nuovo, e dove nessun test nomina il nome si scrive NON
MISURATA.

| riga | classe | metodi | contratto / cosa promette | test che la nominano | verdetto |
|---|---|---|---|---|---|
| 364 | `EpisodicMemory` | 67 | — | 147 — `conftest.py` | esercitata dai blocchi eseguiti sopra |

## I metodi speciali di questo file — 1

In tabella come tutto il resto: il righello legge la seconda colonna, e in prosa
restavano fuori dal conto. **Non sono righe vuote**: i costruttori di questo
prodotto aprono file, eseguono schemi e in tre casi su otto fanno le migrazioni.
Ognuno dice cosa apre e cosa crea, letto dal corpo.

| riga | metodo | classe | cosa apre e cosa crea (letto) | verdetto |
|---|---|---|---|---|
| 370 | `__init__` | `EpisodicMemory` | 12 stmt: `mkdir`, `_connect`, `executescript`, **`ensure_schema_version`**, **`_replay_pending_facts`**. Crea gli indici in memoria (`_faiss_index`, `_recall_index`, `_dg_index`) con le rispettive `data_version` e il flag `_index_dirty`: stessa forma di `SemanticMemory`, migrazioni comprese | esercitato da ogni uso di `EpisodicMemory` nei blocchi sopra |
