# Le definizioni residue di ws7 e ws8 — 9 righe (lead, 09/09 14:20)

Le cinque classi di `tui.py` e le quattro definizioni annidate che gli inventari di Iris (ws7) e Corrado (ws8) non contengono, scritte dal lead per lettura (nessuna esecuzione: sono widget Textual, generatori SSE e shim). I chiamanti sono nel file stesso.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/tui.py:44` `ChatPane` | il pannello chat: log scorrevole, riga di stato («Ctrl+Enter to send · /sleep to consolidate»), `TextArea` in basso | `HippoTUI` (378 e seguenti) | nessuno (Iris: otto azioni della TUI mai eseguite dai test) | - | NON MISURATO (letto) | letto |
| 2 | `verimem/tui.py:119` `SkillsPane` | tabella delle skill (id, name, stage, status, trials, fitness) | `HippoTUI` | nessuno | - | NON MISURATO (letto) | letto |
| 3 | `verimem/tui.py:139` `EpisodesPane` | tabella degli episodi (id, task, outcome, steps, tokens, skills) | `HippoTUI` | nessuno | - | NON MISURATO (letto) | letto |
| 4 | `verimem/tui.py:161` `SettingsPane` | il pannello delle impostazioni (Input/Select per sezione) | `HippoTUI` | nessuno | - | NON MISURATO (letto) | letto |
| 5 | `verimem/tui.py:378` `HippoTUI` | l'app Textual: `VerimemAgent.build()` nel costruttore, quattro pannelli, i binding Ctrl+Enter/R/S/Q (Ctrl+S = ciclo di sonno) | `verimem/cli.py` (comando della TUI, mappa di Iris) | nessuno | - | NON MISURATO (letto; Iris: «una spegne il sandbox a un clic») | letto |
| 6 | `verimem/cli.py:4557` `facts_add._AgentShim` | lo shim con il solo attributo `semantic` che il gate vuole, costruito dentro `facts add` | `facts_add` (4560) | via i test di `facts add` (mappa di Iris) | - | FUNZIONA COME PROMESSO (plumbing; copia n. 2 dello shim, vedi riga 9) | letto |
| 7 | `verimem/dashboard_routes/events.py:94` `register.events_stream.gen` | il generatore SSE: drain non bloccante della coda (2048), cap `max_seconds`, `try/finally` che disiscrive SEMPRE il listener wildcard (audit#3-r3 R0: prima ogni connessione lasciava una closure in `BUS._wildcards`: latenza e RAM crescevano a ogni refresh, DoS lento non autenticato) | `events_stream` (54) | test SSE della console (mappa di Corrado) | - | NON MISURATO qui (letto) | letto |
| 8 | `verimem/dashboard_routes/memory_map.py:413` `register.memory_map_events.gen` | il gemello per la mappa della memoria: BUS in-process + coda JSONL cross-process, `?since=` per i duplicati al reconnect, stesso `try/finally` | `memory_map_events` (387) | test SSE della console (mappa di Corrado) | - | NON MISURATO qui (letto) | letto |
| 9 | `verimem/hooks/pre_tool_use.py:175` `_default_agent_factory._AgentShim` | lo shim con `semantic` per lo `StepInjector` del hook; la data dir dagli alias (`_compat`, prima ENGRAM_DATA_DIR per prima: l'opposto della regola) | `_default_agent_factory` (177) | `tests/test_pre_tool_use_hook.py` (per nome del modulo) | - | FUNZIONA COME PROMESSO (plumbing; copia n. 1 dello shim) | letto |

Reperti: (a) due `_AgentShim` locali (cli.py e hooks) con lo stesso scopo: classe ①; (b) i due generatori SSE sono la stessa forma scritta due volte, con la stessa lezione (il listener wildcard che perdeva): la seconda copia è nata per correggere la prima invece di unificarla.
