# `verimem/observability.py` — 310 righe, 22 funzioni

*«Observability: structured logging, event bus, metrics registry.»* Tre meccanismi in un
file. Mappato su `7b9e8ca1`.

---

## 1. Tre meccanismi, e ciascuno ha il suo pezzo

| meccanismo | funzioni |
|---|---|
| **logging strutturato** | `_resolve_log_level` (43) · `route_logs_to_stderr` (66) · `get_log` (265) |
| **event bus** | `subscribe` (117) · `unsubscribe` (124) · `emit` (146) · `history` (165) · i cinque `_on_*` (233-254) |
| **metrics registry** | `inc` (188) · `observe` (192) · `gauge` (196) · `snapshot` (200) · `reset` (221) |

📌 `route_logs_to_stderr` (66): *«Re-route every structlog line to **stderr** (colors off)»* —
è la funzione che rende usabile un server MCP, dove **stdout è il protocollo**: una riga di
log su stdout romperebbe la comunicazione. Un dettaglio che vale un incidente.

📌 `unsubscribe` (124): *«No-op if absent»* — togliersi da un bus a cui non si è iscritti
non è un errore. Piccola cortesia che evita try/except ai chiamanti.

---

## 2. `_estratto` (275) — il campo tagliato senza mutilare ciò che porta

> *«Taglia un campo dichiarato ESTRATTO senza mutilare il graf[ema]…»*

⇒ Un troncamento **consapevole della codifica**: tagliare a byte in mezzo a un carattere
multi-byte produce un mojibake, e in un log italiano (o in un fatto con accenti) succede
subito. Il nome del campo dice **che è un estratto**, quindi chi legge non crede di avere
il testo intero.

🔑 È la stessa disciplina della mappa: **un valore parziale deve dichiarare di esserlo.**

---

## 3. Quello che questa mappa NON dice — dichiarato

- **`history` (165)**: c'è uno storico degli eventi in memoria. **Non so quanto è grande né
  se abbia un limite** — un bus con storico illimitato in un processo lungo è una perdita
  lenta, e questa è una domanda da porre, non un'accusa.
- **I cinque `_on_*`** (`_on_any_event`, `_on_episode_completed`, `_on_skill_synthesized`,
  `_on_skill_promoted`, `_on_skill_retired`) sono letti **solo di nome**: non so cosa fanno
  né chi li registra.
- **Non ho verificato** che `route_logs_to_stderr` sia chiamata da tutte le porte che ne
  hanno bisogno: sarebbe un grep, e il fatto che una sola porta se ne dimentichi
  romperebbe *quella* porta in modo difficile da diagnosticare.

---

*Mappato da ws5 (Tara) su `7b9e8ca1`.*

---

<!-- TABELLA-FUNZIONI ws5 -->

## Dove sta ogni funzione, e con che verdetto

*Rubrica generata dall'AST. Cosa e' misurato e cosa no, per colonna:*

- **dove e chi** — `file:riga` dall'AST: misurato.
- **cos'e'** — tipo e prima riga del docstring: e' cio' che la funzione
  PROMETTE, non cio' che fa.
- **nominata da** — file che NOMINANO il nome corto: chiamate, ma anche
  riferimenti nudi, property e annotazioni. Gli alias di import sono
  risolti (senza, `emit_write` risultava a zero). Contando solo le
  chiamate, 17 funzioni su 27 risultavano morte e non lo erano: Protocol,
  property e callback non passano da una `ast.Call`. Include il file
  stesso. ⚠️ Un nome che vive in piu' classi (`call`, `to_dict`) somma
  usi non suoi: e' un TETTO, non una misura.
- **test** — file sotto `tests/` che lo nominano: dice che e' TOCCATA,
  non che sia coperta.
- **verdetto** — `MAI CHIAMATA` = zero riferimenti nel prodotto E zero nei
  test (i dunder esclusi: li chiama il linguaggio). `NON MISURATO` =
  tutto il resto, ed e' lo stato onesto: sapere chi la nomina non e'
  sapere che funziona.


### `verimem/observability.py` — 25 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/observability.py:43` `_resolve_log_level` | funzione | `verimem/observability.py` | **nessuno** | NON MISURATO |
| 2 | `verimem/observability.py:66` `route_logs_to_stderr` | funzione: Re-route every structlog line to stderr (colors off), for entry points — **il nome e le righe 22-25 promettono stderr perche' «its protocol owns stdout»; ma `PrintLoggerFactory(file=sys.stderr)` legge sys.stderr alla CHIAMATA, e con `sys.stderr is None` (pythonw, servizio senza console) `file=None` significa stdout: **86 byte misurati il 09/09**. Era la causa del rosso intermittente di test_ws5_il_download (T41). Il verdetto vale su questo commit: la cura e' sul ramo `tara/t41-logger-tace` (`be118f90`), non ancora su main** | `verimem/cli.py` | **nessuno** | NON COME PROMESSO |
| 3 | `verimem/observability.py:96` `Event` | classe | `verimem/_hang_watchdog.py`; `verimem/encode_service.py` (+3) | `tests/test_bump_on_recall_nonblocking.py`; `tests/test_daemon_health_probe.py` (+12) | NON MISURATO |
| 4 | `verimem/observability.py:101` `Event.to_json` | funzione | **nessuno** | **nessuno** | MAI CHIAMATA |
| 5 | `verimem/observability.py:108` `EventBus` | classe: Synchronous pub/sub. Thread-safe. Keeps a ring buffer of recent events. | `verimem/observability.py` | **nessuno** | NON MISURATO |
| 6 | `verimem/observability.py:111` `EventBus.__init__` | funzione | `verimem/client.py`; `verimem/document_index.py` (+2) | `tests/test_i_default_che_il_readme_dichiara.py`; `tests/test_windows_no_console_popup.py` | NON MISURATO |
| 7 | `verimem/observability.py:117` `EventBus.subscribe` | funzione | `verimem/dashboard_routes/events.py`; `verimem/dashboard_routes/memory_map.py` (+1) | `tests/test_dashboard_bus_coverage.py`; `tests/test_eventbus_unsubscribe_leak.py` (+2) | NON MISURATO |
| 8 | `verimem/observability.py:124` `EventBus.unsubscribe` | funzione: Remove a previously-registered subscriber. No-op if absent. | `verimem/dashboard_routes/events.py`; `verimem/dashboard_routes/memory_map.py` | `tests/test_eventbus_unsubscribe_leak.py`; `tests/test_l_estratto_dell_evento_non_mutila.py` (+1) | NON MISURATO |
| 9 | `verimem/observability.py:146` `EventBus.emit` | funzione | `verimem/agent.py`; `verimem/bench_harness.py` (+17) | `tests/test_l_estratto_dell_evento_non_mutila.py`; `tests/test_memory_map_routes.py` (+1) | NON MISURATO |
| 10 | `verimem/observability.py:165` `EventBus.history` | funzione | `verimem/code.py`; `verimem/dashboard_routes/events.py` (+2) | `tests/test_client_sdk.py`; `tests/test_dashboard_bus_coverage.py` (+5) | NON MISURATO |
| 11 | `verimem/observability.py:179` `MetricsRegistry` | classe: Lightweight in-memory metrics: counters + histograms. | `verimem/observability.py` | **nessuno** | NON MISURATO |
| 12 | `verimem/observability.py:182` `MetricsRegistry.__init__` | funzione | `verimem/client.py`; `verimem/document_index.py` (+2) | `tests/test_i_default_che_il_readme_dichiara.py`; `tests/test_windows_no_console_popup.py` | NON MISURATO |
| 13 | `verimem/observability.py:188` `MetricsRegistry.inc` | funzione | `verimem/observability.py` | `tests/test_la_gamba_windows_non_ha_il_tempo_di_dare_il_verdetto.py` | NON MISURATO |
| 14 | `verimem/observability.py:192` `MetricsRegistry.observe` | funzione | `verimem/observability.py`; `verimem/wake.py` | `tests/test_auto_memory.py`; `tests/test_context_engine.py` (+4) | NON MISURATO |
| 15 | `verimem/observability.py:196` `MetricsRegistry.gauge` | funzione | **nessuno** | **nessuno** | MAI CHIAMATA |
| 16 | `verimem/observability.py:200` `MetricsRegistry.snapshot` | funzione | `verimem/ann_cache.py`; `verimem/cli.py` (+5) | `tests/test_corpus_health_snapshot.py`; `tests/test_flow_entity_events.py` (+1) | NON MISURATO |
| 17 | `verimem/observability.py:221` `MetricsRegistry.reset` | funzione | `verimem/cli.py`; `verimem/code.py` (+2) | `tests/test_context_engine.py`; `tests/test_dashboard_bus_coverage.py` (+2) | NON MISURATO |
| 18 | `verimem/observability.py:233` `_on_any_event` | funzione | `verimem/observability.py` | **nessuno** | NON MISURATO |
| 19 | `verimem/observability.py:237` `_on_episode_completed` | funzione | `verimem/observability.py` | **nessuno** | NON MISURATO |
| 20 | `verimem/observability.py:246` `_on_skill_synthesized` | funzione | `verimem/observability.py` | **nessuno** | NON MISURATO |
| 21 | `verimem/observability.py:250` `_on_skill_promoted` | funzione | `verimem/observability.py` | **nessuno** | NON MISURATO |
| 22 | `verimem/observability.py:254` `_on_skill_retired` | funzione | `verimem/observability.py` | **nessuno** | NON MISURATO |
| 23 | `verimem/observability.py:265` `get_log` | funzione | `verimem/bench_harness.py`; `verimem/cli.py` (+14) | **nessuno** | NON MISURATO |
| 24 | `verimem/observability.py:275` `_estratto` | funzione: Taglia un campo dichiarato ESTRATTO senza mutilare il grafema. | `verimem/observability.py` | **nessuno** | NON MISURATO |
| 25 | `verimem/observability.py:297` `emit` | funzione | `verimem/agent.py`; `verimem/bench_harness.py` (+17) | `tests/test_l_estratto_dell_evento_non_mutila.py`; `tests/test_memory_map_routes.py` (+1) | NON MISURATO |

<!-- /TABELLA-FUNZIONI ws5 -->






