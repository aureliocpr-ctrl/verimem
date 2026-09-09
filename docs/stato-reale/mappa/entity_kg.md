# mappa — `verimem/entity_kg.py`

**owner ws6 Aldo** · base `7b9e8ca1` · aperto 2026-09-08 22:22

**1.385 righe · 36 funzioni · 2 classi.** Contate con `ast`. Nella mia lista
ci sono anche i due file vicini, che apro dopo: `entity_extract_lite.py`
(252 righe, 3 funzioni) e `entity_populate.py` (176 righe, 3 funzioni).

## Un dato che vale prima di ogni riga

**23 funzioni pubbliche, e ZERO che nessun test nomina.** È il primo dei tre
file che apro con copertura piena sui nomi: in `semantic.py` ne mancavano 48 su
114 private e una pubblica (`set_derives_from`) era senza test pur essendo in un
claim del CHANGELOG; in `memory.py` una era morta del tutto (`by_task`). Qui no.

Il conto è di `scratchpad/raggruppa.py`, che cerca il nome nudo in `tests/`:
resta il limite già dichiarato — **nominare non è esercitare** — e infatti sotto
il verdetto è sempre «limitato a ciò che quel test asserisce».

## Il claim che questo file serve

`README:554`: «**The graph is alive**: nodes the engine touches fire and new ones
grow in as you work, straight from `/v1/events/flow`. It is an **honest window**,
not the whole store — it shows the most recent entities with the real …»

⚠️ Quel claim è servito dal **gateway** (`/v1/events/flow`), non da questo file.
`entity_kg.py` sta *sotto* la promessa: la mappa lo dice per non far leggere un
verde qui come una verifica della dashboard, che è di un altro owner.

## Le righe, raggruppate per esecuzione

Il verdetto di ogni blocco è **FUNZIONA COME PROMESSO**, limitato
a ciò che quel test asserisce.

**23 pubbliche su 23 coperte, con SEI blocchi eseguiti, tutti verdi.**

| # | blocco | pubbliche nominate | prova |
|---|---|---|---|
| 1 | `test_read_connection_is_reused.py` | 15 | `10 passed in 20.32s` EXIT=0 |
| 2 | `test_anchor_recall.py` | 9 | `8 passed, 1 warning in 10.x` EXIT=0 |
| 3 | `test_entity_kg.py` | 7 | `17 passed, 1 warning in 9.x` EXIT=0 |
| 4 | `test_ppr_fact_ranking.py` | 6 | `8 passed in 9.36s` EXIT=0 |
| 5 | `test_ppr_entity_neighbors.py` | 6 | `11 passed, 1 warning in 10.x` EXIT=0 |
| 6 | `test_entity_traced_paths.py` | 4 | `8 passed in 10.94s` EXIT=0 |

## 🔑 Il debito che avevo dichiarato, e perché non andava stimato

Nel primo giro avevo scritto: «le funzioni si sovrappongono fra i blocchi, il
conteggio deduplicato lo faccio dopo e **non lo stimo qui**». Contato adesso con
`scratchpad/copertura_dedup.py`:

```
SOMMA delle colonne (con i doppioni) : 47
UNIONE, cioè il numero vero          : 23
```

**Sommare le colonne avrebbe dato 47 su 23 pubbliche — il doppio del totale.**
Un numero impossibile, e nessuno se ne sarebbe accorto leggendo la tabella: le
sei righe sono tutte vere, è la somma che non ha senso. `add_edge` e `link_fact`
compaiono in tre blocchi ciascuno.

📌 E il conteggio ha fatto una seconda cosa, più utile del numero: **ha detto
cosa mancava.** Coi primi quattro blocchi l'unione era 21, e le due scoperte
erano `neighbors` e `traced_paths`. Cercate, avevano ciascuna un test dedicato
(`test_ppr_entity_neighbors`, `test_entity_traced_paths`) che nessuno dei quattro
blocchi toccava. Senza il conto deduplicato avrei chiuso il file a 21 su 23
credendolo completo.

## Le `_private`: 12, e sei sono migrazioni registrate

**12 `_private`**: 4 nominate da un test, 8 no. Ma delle 8, **sei sono
migrazioni** (`_migrate_v1_initial` … `_migrate_v6_entity_attrs`) e sono
**registrate in una lista** — `entity_kg.py:487`, `(1, _migrate_v1_initial)` e
seguenti. È la **terza volta** che incontro questa forma: identica in
`semantic.py:2652`, `memory.py:274-279` e qui.

⇒ Non è un buco di copertura: è il modo in cui questo prodotto registra le
migrazioni. La porta è una sola (`ensure_schema_version`) e nessun test nomina i
singoli passi. **Chi mappa gli altri store lo troverà uguale, e può risparmiarsi
il giro che ho fatto tre volte.**

Le due `_private` vere senza test sono helper interni con chiamanti dentro il
file: `_rank_facts` (1141, chiamata a 1286 e 1354) e `_row_to_entity` (1378,
chiamata a 626 e 644). **NON MISURATE** direttamente, esercitate dai loro
chiamanti.

| blocco | `_private` coperte | prova |
|---|---|---|
| `test_entity_kg.py` | `_norm` | `17 passed` EXIT=0 |
| `test_entity_ppr_graph_cache.py` | `_get_graph` | `3 passed in 8.55s` EXIT=0 |
| `test_episode_index_cross_process.py` | `_db_data_version` | `3 passed in 8.21s` EXIT=0 |
| `test_bridge.py` | `_connect` | da eseguire |

## I due file vicini, chiusi

| file | funzioni | pubbliche senza test | prova |
|---|---|---|---|
| `entity_extract_lite.py` (252 righe) | 3 (1 pubblica: `extract_entities_lite`) | **0** | `pytest -q tests/test_aperture_e_lato_solo.py` → `24 passed in 8.29s` EXIT=0 |
| `entity_populate.py` (176 righe) | 3 (3 pubbliche: `entity_kg_path_for`, `populate_entities_for_fact`, +1) | **0** | `pytest -q tests/test_entity_live_latency.py` → `8 passed, 1 warning in 9.2s` EXIT=0 |

⇒ **Il gruppo `entity_*` è chiuso**: 1.813 righe in tre file, 42 funzioni, e
nessuna pubblica senza test. È il gruppo più coperto dei tre aperti finora.
