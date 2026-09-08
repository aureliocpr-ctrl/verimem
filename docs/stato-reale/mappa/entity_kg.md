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

| # | funzioni | chiamata da | test eseguito | verdetto | prova |
|---|---|---|---|---|---|
| 1 | `aliases_of` · `count` · `edges_from` · `entities_for_fact` · `fact_counts` e altre 10 | il percorso di lettura del grafo | `tests/test_read_connection_is_reused.py` — **15** funzioni di questo file, il blocco più denso trovato finora | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_read_connection_is_reused.py` → `10 passed in 20.32s` EXIT=0 |
| 2 | `add_alias` · `aliases_of` · `count` · `facts_for_entity` · `get_by_name` (+2) | il file di test proprio del modulo | `tests/test_entity_kg.py` | **FUNZIONA COME PROMESSO**, limitato | `17 passed, 1 warning in 9.x` EXIT=0 |
| 3 | `add_edge` · `get` · `get_attrs` · `get_by_name` · `link_fact` (+4) | gli àncora del recall | `tests/test_anchor_recall.py` | **FUNZIONA COME PROMESSO**, limitato | `8 passed, 1 warning in 10.x` EXIT=0 |
| 4 | `ppr` · `ppr_weighted` · `session` · `add_edge` · `link_fact` (+1) | il ranking personalizzato | `tests/test_ppr_fact_ranking.py` | **FUNZIONA COME PROMESSO**, limitato | `8 passed in 9.36s` EXIT=0 |

**Copertura di questo giro: 4 esecuzioni, tutte verdi.** Le funzioni toccate si
sovrappongono fra i blocchi (`add_edge` e `link_fact` compaiono in tre) — il
conteggio esatto delle righe distinte lo faccio nel prossimo giro, e **non lo
stimo qui**: un numero non contato in una mappa che serve a contare è il difetto
peggiore che ci si possa mettere, e l'ho già commesso una volta stasera.

## Da fare

- il conto esatto delle pubbliche coperte dai quattro blocchi (deduplicato)
- le `_private` di questo file
- `entity_extract_lite.py` e `entity_populate.py` (6 funzioni in due file)
