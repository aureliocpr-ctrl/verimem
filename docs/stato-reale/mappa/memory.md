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
