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
| 5 | `set_pinned` (memory.py:1326) | «pin/unpin an episode. Pinned episodes are …» | `mcp_server.py:9050` e `:9062` — esposta dalla porta MCP | — da eseguire | — | **NON MISURATO** | — |
| 6 | `store_batch` (memory.py:818) | «CYCLE #18 — bulk insert con batch embedding.» | `mcp_server.py:9334` · `transcript_ingest.py:124` | — da eseguire | — | **NON MISURATO** | — |

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
