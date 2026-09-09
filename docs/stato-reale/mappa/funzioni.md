# Le funzioni dei sei pacchetti — una riga per funzione

> **ws8 (Corrado), 09/09/2026.** Le trentuno schede di `mappa/` dicono **cosa fa ogni file**
> e **chi lo chiama**; questa tabella scende di un gradino: **una riga per funzione**, con la
> **firma** e la **prima riga del docstring prese dal codice**, non riassunte.
>
> 🔑 **Perché tabellare invece di lasciare la prosa**: una scheda che dice «cosa fa il modulo»
> **non si può contare**. Una riga per funzione sì — e chi legge sa quali funzioni sono state
> guardate e quali no. Dove il docstring manca, la riga lo dichiara invece di inventare una
> descrizione: *«nessun docstring — la riga dice solo firma e file»*.
>
> Generata da `estrai_funzioni.py` con `ast`, non con un `grep`: le funzioni annidate e i
> metodi entrano tutti, e nessuna riga è scritta a mano.

### `verimem/webui/` — 2 funzioni

| n | funzione | file | cosa dichiara di fare |
|---|---|---|---|
| 1 | `asset(name)` | `__init__.py` | Read one packaged asset (cached — the files are immutable at runtime). |
| 2 | `media_type(name)` | `__init__.py` | *(nessun docstring — la riga dice solo firma e file)* |

### `verimem/migrations/` — 4 funzioni

| n | funzione | file | cosa dichiara di fare |
|---|---|---|---|
| 1 | `_read_version(conn, db_id)` | `__init__.py` | Return the current schema version for `db_id` (0 if unknown). |
| 2 | `_write_version(conn, db_id, version)` | `__init__.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 3 | `ensure_schema_version(conn, db_id, target_version, migrations)` | `__init__.py` | Migrate `conn` to `target_version` for the database identified by `db_id`. |
| 4 | `schema_version(conn, db_id)` | `__init__.py` | Public read accessor — does not mutate the DB. |

### `verimem/hooks/` — 12 funzioni

| n | funzione | file | cosa dichiara di fare |
|---|---|---|---|
| 1 | `_bash_extractor(tool_input)` | `pre_tool_use.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 2 | `_edit_extractor(tool_input)` | `pre_tool_use.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 3 | `_write_extractor(tool_input)` | `pre_tool_use.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 4 | `_read_extractor(tool_input)` | `pre_tool_use.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 5 | `_grep_extractor(tool_input)` | `pre_tool_use.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 6 | `_glob_extractor(tool_input)` | `pre_tool_use.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 7 | `extract_step_text(tool_name, tool_input)` | `pre_tool_use.py` | Return the "step text" we will recall facts against. |
| 8 | `_default_agent_factory()` | `pre_tool_use.py` | Best-effort agent loader: opens the local SemanticMemory under |
| 9 | `_safe_untrusted(text, limit)` | `pre_tool_use.py` | Flatten a STORED string for safe display inside the banner. |
| 10 | `_render_banner(tool_name, hits)` | `pre_tool_use.py` | Render the ``<engram-step-recall>`` banner. Same shape style |
| 11 | `run(payload)` | `pre_tool_use.py` | Apply the hook logic to one PreToolUse payload. |
| 12 | `main_stdin_stdout(stdin, stdout)` | `pre_tool_use.py` | CLI entry point. Reads JSON from ``stdin`` (default ``sys.stdin``), |

### `verimem/teams/` — 23 funzioni

| n | funzione | file | cosa dichiara di fare |
|---|---|---|---|
| 1 | `_short_ts(timestamp)` | `bridge.py` | Extract ``HH:MM:SS`` from an ISO8601 timestamp; passthrough else. |
| 2 | `mirror_message(msg)` | `bridge.py` | Mirror one inbox message into verimem THROUGH the moat. |
| 3 | `_msg_color(text)` | `cli.py` | Return the rich color associated with the FIRST protocol tag in |
| 4 | `_now_iso()` | `cli.py` | Return the current UTC time in the same ISO8601 ms format Anthropic uses. |
| 5 | `_inbox_lock(inbox)` | `cli.py` | BOUNDED cross-platform exclusive lock on one inbox file. |
| 6 | `_read_inbox(inbox)` | `cli.py` | Read the inbox JSON array; [] if absent / empty / corrupt. |
| 7 | `_atomic_write_json(path, data)` | `cli.py` | Write ``data`` to ``path`` atomically (unique temp file + os.replace). |
| 8 | `append_to_inbox(team_dir, to, as_, message)` | `cli.py` | Append one message to ``<team_dir>/inboxes/<to>.json`` as an atomic, |
| 9 | `send_cmd(team_dir, to, as_, message)` | `cli.py` | Append one message to the recipient inbox JSON file. |
| 10 | `watch_cmd(team_dir, refresh_sec, max_sec, include_idle, mirror_to_memory, mirror_include_idle)` | `cli.py` | Tail teammates' inboxes. New messages printed one per line. |
| 11 | `charter_cmd()` | `cli.py` | Print the Real-Collaboration Charter (cycle 159). |
| 12 | `collab_test_cmd(team_dir, members, max_min, refresh_sec, report_every_sec, deadlock_after_sec)` | `cli.py` | Cycle 159: empirical-collaboration test. |
| 13 | `__post_init__()` | `harness.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 14 | `poll()` | `harness.py` | Pull new messages and update counters. Returns them for echoing. |
| 15 | `_classify(msg)` | `harness.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 16 | `stalled_members(threshold_sec)` | `harness.py` | Members that haven't emitted a non-idle message in |
| 17 | `converged()` | `harness.py` | Strict-majority voting: ``len(voters) > N/2``. |
| 18 | `is_deadlocked(now)` | `harness.py` | True iff no new message has arrived for ``deadlock_after_sec``. |
| 19 | `report()` | `harness.py` | Compact JSON-friendly snapshot of harness state. |
| 20 | `from_raw(raw)` | `inbox.py` | Build from one raw entry of the inbox JSON array. |
| 21 | `__init__(team_dir)` | `inbox.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 22 | `poll()` | `inbox.py` | Return new messages from every inbox file since the last poll. |
| 23 | `parse_protocol_tags(text)` | `protocol.py` | Extract the cycle-159 control tags from one message. |

### `verimem/swarm/` — 33 funzioni

| n | funzione | file | cosa dichiara di fare |
|---|---|---|---|
| 1 | `_hhmmss(ts)` | `bridge.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 2 | `write_transition_chat_fact(short_id, prev, curr)` | `bridge.py` | Mirror one agent state transition into verimem THROUGH the moat. |
| 3 | `record_completion_episode(short_id)` | `bridge.py` | Create one Episode summarising the agent finish and link it. |
| 4 | `poll_until_done(short_id)` | `bridge.py` | Poll ``read_state`` in a loop until terminal or deadline. |
| 5 | `_load_config(path)` | `cli.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 6 | `run_cmd(config_path, hub_master_ep_id)` | `cli.py` | End-to-end swarm run: spawn N agents, poll until done, report. |
| 7 | `status_cmd(run_id)` | `cli.py` | List background sessions whose display name starts with <run_id>-. |
| 8 | `logs_cmd(short_id)` | `cli.py` | Passthrough to ``claude logs <short_id>`` (terminal dump). |
| 9 | `kill_cmd(run_id, topic)` | `cli.py` | ``claude stop`` every session whose name starts with <run_id>-. |
| 10 | `clean_cmd(run_id, topic)` | `cli.py` | ``claude rm`` every session whose name starts with <run_id>-. |
| 11 | `respawn_cmd(short_id, run_id, topic)` | `cli.py` | ``claude respawn`` one session with audit. |
| 12 | `_hhmmss()` | `lifecycle.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 13 | `_default_jobs_dir()` | `lifecycle.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 14 | `_audit()` | `lifecycle.py` | Record a lifecycle action as a gated chronicle row. |
| 15 | `_run_claude(args)` | `lifecycle.py` | Run a 1-shot claude subcommand. Returns (ok, stdout, stderr). |
| 16 | `stop_session(short_id)` | `lifecycle.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 17 | `respawn_session(short_id)` | `lifecycle.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 18 | `remove_session(short_id)` | `lifecycle.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 19 | `list_swarm_sessions(run_id)` | `lifecycle.py` | Return short_ids of sessions whose state.json ``name`` starts with |
| 20 | `_create_hub_episode(config, mem)` | `orchestrator.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 21 | `_opening_chat_fact(config, memory)` | `orchestrator.py` | Chronicle the run START. Returns the fact id so the closing |
| 22 | `_final_chat_fact(config, report, memory)` | `orchestrator.py` | Chronicle the run FINISHED, chained to the opening chronicle. |
| 23 | `run_swarm(config)` | `orchestrator.py` | Run one swarm end-to-end. Blocks until every agent finishes |
| 24 | `_worker(name, short_id)` | `orchestrator.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 25 | `_topic_shape(v)` | `schemas.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 26 | `_unique_agent_names()` | `schemas.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 27 | `_compose_command(spec)` | `spawn.py` | Build the exact argv to invoke ``claude --bg ...``. |
| 28 | `_compose_env(env_overrides)` | `spawn.py` | Inherit os.environ then force the agent-teams flag on. |
| 29 | `spawn_agent(spec)` | `spawn.py` | Spawn one background agent. Blocks until ``claude --bg`` returns |
| 30 | `_default_jobs_dir()` | `state.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 31 | `find_state_dir(short_id)` | `state.py` | Locate ``<jobs_dir>/<short_id>/`` if it exists. |
| 32 | `read_state(short_id)` | `state.py` | Read + parse the session state. Returns ``None`` if absent. |
| 33 | `from_raw(raw)` | `state.py` | Build from the raw JSON dict, flattening ``output.result`` + |

### `verimem/dashboard_routes/` — 76 funzioni

| n | funzione | file | cosa dichiara di fare |
|---|---|---|---|
| 1 | `register_all(app, templates)` | `__init__.py` | Wire every dashboard sub-module onto the given FastAPI app. |
| 2 | `_kpi(label, value, hint, color)` | `active_memory.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 3 | `register(app, templates)` | `active_memory.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 4 | `active_memory_page()` | `active_memory.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 5 | `active_memory_stats()` | `active_memory.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 6 | `session_token_path()` | `auth.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 7 | `_generate_session_token()` | `auth.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 8 | `get_session_token()` | `auth.py` | Lazily issue and cache the per-process session token. |
| 9 | `reset_session_token()` | `auth.py` | Test helper — clear the cached token so envs can pick up overrides. |
| 10 | `auth_disabled()` | `auth.py` | Cycle #124 (2026-05-17): secure-by-default flip. |
| 11 | `verify_session_token(x_hippo_token)` | `auth.py` | FastAPI dependency: refuse state-changing calls without a valid token. |
| 12 | `bootstrap_token()` | `auth.py` | Force token generation at app startup. Returns the token (never logs it). |
| 13 | `_safe_error(exc, where)` | `chat.py` | FORGIA #189 — sanitize exception messages for HTTP responses. |
| 14 | `register(app, templates)` | `chat.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 15 | `chat_page(request)` | `chat.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 16 | `chat_api(req)` | `chat.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 17 | `plan_api(req)` | `chat.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 18 | `sleep_api()` | `chat.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 19 | `feedback_api(req)` | `chat.py` | Apply user feedback (up/down) on a chat turn to skill fitness. |
| 20 | `register(app, templates)` | `episodes.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 21 | `episodes_page(request)` | `episodes.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 22 | `episode_detail(request, episode_id)` | `episodes.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 23 | `register(app, templates)` | `events.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 24 | `events_page()` | `events.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 25 | `events_recent(limit)` | `events.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 26 | `events_stream(max_seconds)` | `events.py` | Server-Sent Events: pushes new events as they're emitted on the bus. |
| 27 | `listener(evt)` | `events.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 28 | `async gen()` | `events.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 29 | `register(app, templates)` | `health.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 30 | `healthz()` | `health.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 31 | `_build_default_agent()` | `layout.py` | Default factory; isolated for testability. |
| 32 | `get_agent()` | `layout.py` | Return the in-process VerimemAgent singleton. |
| 33 | `reset_agent()` | `layout.py` | Drop the cached singleton (used by tests that monkey-patch _ag). |
| 34 | `page(title, body, full_width)` | `layout.py` | Wrap inner HTML body with the standard <html><head><nav><main> chrome. |
| 35 | `html_escape(s)` | `layout.py` | HTML-escape including quotes (CVE-007 / SEC V7 fix). |
| 36 | `register(app, templates)` | `lineage.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 37 | `lineage_page()` | `lineage.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 38 | `lineage_data()` | `lineage.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 39 | `_safe_list(obj, attr)` | `memory_map.py` | Best-effort: get ``obj.<attr>.all()`` slice; ``[]`` on any failure. |
| 40 | `_direct_load()` | `memory_map.py` | Fallback: instantiate stores directly from CONFIG. |
| 41 | `_build_graph(agent)` | `memory_map.py` | Construct the multi-layer envelope expected by the UI. |
| 42 | `register(app, templates)` | `memory_map.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 43 | `memory_map_page()` | `memory_map.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 44 | `memory_map_graph(limit)` | `memory_map.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 45 | `memory_map_events(request, since, max_seconds)` | `memory_map.py` | SSE feed: BUS in-process + JSONL tail cross-process. |
| 46 | `listener(evt)` | `memory_map.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 47 | `async gen()` | `memory_map.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 48 | `_safe_error(exc, where)` | `settings.py` | FORGIA #189 — sanitize exception messages for HTTP responses. |
| 49 | `_env_for_provider(provider)` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 50 | `_apply_preset_to_settings(cur, preset)` | `settings.py` | Apply a preset (provider+model) to a UserSettings in-place. |
| 51 | `register(app, templates)` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 52 | `settings_page()` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 53 | `settings_active()` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 54 | `settings_providers()` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 55 | `settings_models(provider)` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 56 | `settings_recommended_models(provider)` | `settings.py` | Curated model list from `providers.yaml` — no provider round-trip. |
| 57 | `settings_save(body)` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 58 | `settings_test(body)` | `settings.py` | Apply candidate settings to env temporarily and ping the LLM. |
| 59 | `fallback_get()` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 60 | `fallback_save(body)` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 61 | `permissions_get()` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 62 | `permissions_save(body)` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 63 | `presets_get()` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 64 | `presets_apply(body)` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 65 | `_serialise(spec)` | `settings.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 66 | `register(app, templates)` | `skills.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 67 | `skills_page(request)` | `skills.py` | New design-system skills page (Jinja2 template + dashboard.css). |
| 68 | `skill_detail(skill_id)` | `skills.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 69 | `skill_retire(skill_id)` | `skills.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 70 | `skill_promote(skill_id)` | `skills.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 71 | `_format_event(e)` | `welcome.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 72 | `register(app, templates)` | `welcome.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 73 | `_overview_render(request, templates)` | `welcome.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 74 | `welcome_page(request)` | `welcome.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 75 | `overview(request)` | `welcome.py` | *(nessun docstring — la riga dice solo firma e file)* |
| 76 | `metrics_page(request)` | `welcome.py` | *(nessun docstring — la riga dice solo firma e file)* |

---

## 📏 Il conto, e il reperto che esce dal contarle

```
  funzioni tabellate            150
    con docstring               73
    SENZA docstring             77    (51%)
```

🔑 **Più della metà delle funzioni di questi sei pacchetti non dichiara cosa fa.** Non è un
difetto di stile: il contratto del rilascio chiede *«i documenti interni chiari»*, e per
77 di queste funzioni **l'unica documentazione è il nome**.

⚠️ **E non dico che siano sbagliate**: dico che **non si sa** senza leggerne il corpo. La
riga le elenca lo stesso, con firma e file, perché **una funzione che nessuno ha guardato
e una che nessuno ha documentato non sono la stessa cosa** — e la tabella tiene distinte
le due.

📌 Il conteggio con `grep -cE '^\s*(async )?def '` ne dava **151**; l'`ast` ne trova
**150**. La differenza è **una** riga: il `grep` conta anche un `def` che non è una
definizione (dentro una stringa o un commento). **Ho tenuto il numero dell'`ast`**, che
legge la struttura invece del testo.

---

## 🚨 Le funzioni **mute due volte**: senza docstring E non nominate da nessun test

```
  righe in tabella                                150
  senza docstring                                  76
  non nominate da nessun file di tests/            86
  SENZA DOCSTRING **E** NON NOMINATE DA UN TEST    54
```

⚠️ **«Non nominata da un test» NON vuol dire «non testata».** Una funzione può essere
esercitata **indirettamente**, chiamata da un'altra che il test invoca: il `grep` sui nomi
**trova i candidati e non li conta**. Quello che questa riga dice con certezza è che
**nessun test la nomina**, quindi se cambia comportamento **nessun rosso porta il suo nome**.

🔑 **Sono le funzioni su cui non esiste nessuna dichiarazione**: né il docstring dice cosa
dovrebbero fare, né un test dice cosa non devono smettere di fare. **Cinquantaquattro su
centocinquanta.**

| file | quante | quali |
|---|---|---|
| `settings.py` | **12** | `_env_for_provider`, `_serialise`, `fallback_get`, `fallback_save`, `permissions_get`, `permissions_save`, `presets_get`, `settings_active`, `settings_models`, `settings_page`, `settings_providers`, `settings_save` |
| `pre_tool_use.py` | **6** | `_bash_extractor`, `_edit_extractor`, `_glob_extractor`, `_grep_extractor`, `_read_extractor`, `_write_extractor` |
| `chat.py` | **4** | `chat_api`, `chat_page`, `plan_api`, `sleep_api` |
| `welcome.py` | **4** | `_format_event`, `_overview_render`, `metrics_page`, `welcome_page` |
| `active_memory.py` | **3** | `_kpi`, `active_memory_page`, `active_memory_stats` |
| `skills.py` | **3** | `skill_detail`, `skill_promote`, `skill_retire` |
| `__init__.py` | **2** | `_write_version`, `media_type` |
| `episodes.py` | **2** | `episode_detail`, `episodes_page` |
| `events.py` | **2** | `events_page`, `events_recent` |
| `harness.py` | **2** | `__post_init__`, `_classify` |
| `lifecycle.py` | **2** | `_default_jobs_dir`, `_hhmmss` |
| `lineage.py` | **2** | `lineage_data`, `lineage_page` |
| `memory_map.py` | **2** | `memory_map_graph`, `memory_map_page` |
| `orchestrator.py` | **2** | `_create_hub_episode`, `_worker` |
| `schemas.py` | **2** | `_topic_shape`, `_unique_agent_names` |
| `bridge.py` | **1** | `_hhmmss` |
| `cli.py` | **1** | `_load_config` |
| `health.py` | **1** | `healthz` |
| `state.py` | **1** | `_default_jobs_dir` |

📌 **Da dove partire**, se qualcuno le documenta: `settings.py` ne ha **dodici** — è il file
delle impostazioni, cioè quello dove un comportamento non dichiarato costa di più.

---

## 🧱 E le CLASSI — le diciassette che la tabella delle funzioni non vedeva

Il righello del lead contava **167** definizioni dove io ne dichiaravo **150**. La differenza
sono **17 classi**: `ast.FunctionDef` non le vede, e la mia tabella nemmeno. **Il suo numero
era giusto e il mio incompleto** — non due criteri diversi, un pezzo mancante nel mio.

### Le classi dei sei pacchetti — 17

| n | classe | file | base | metodi | cosa dichiara di essere |
|---|---|---|---|---|---|
| 1 | `_AgentShim` | `hooks/pre_tool_use.py` | — | 0 | *(nessun docstring)* |
| 2 | `CollabHarness` | `teams/harness.py` | — | 7 | Measures collaboration progress on an agent-team's inboxes. |
| 3 | `InboxMessage` | `teams/inbox.py` | — | 1 | One message read out of a teammate inbox file. |
| 4 | `InboxWatcher` | `teams/inbox.py` | — | 2 | Incremental poller over a team's ``inboxes/*.json`` files. |
| 5 | `AgentReport` | `swarm/orchestrator.py` | — | 0 | *(nessun docstring)* |
| 6 | `SwarmReport` | `swarm/orchestrator.py` | — | 0 | *(nessun docstring)* |
| 7 | `AgentSpec` | `swarm/schemas.py` | BaseModel | 0 | One Claude Code background agent inside a swarm run. |
| 8 | `SwarmConfig` | `swarm/schemas.py` | BaseModel | 2 | Top-level swarm run definition. |
| 9 | `SpawnError` | `swarm/spawn.py` | RuntimeError | 0 | Raised when ``claude --bg`` exits non-zero or output is unparseable. |
| 10 | `SpawnResult` | `swarm/spawn.py` | — | 0 | Outcome of a successful spawn. |
| 11 | `SessionState` | `swarm/state.py` | BaseModel | 1 | Subset of fields we read from ``state.json``. |
| 12 | `ChatRequest` | `dashboard_routes/chat.py` | BaseModel | 0 | *(nessun docstring)* |
| 13 | `FeedbackRequest` | `dashboard_routes/chat.py` | BaseModel | 0 | *(nessun docstring)* |
| 14 | `SettingsBody` | `dashboard_routes/settings.py` | BaseModel | 0 | *(nessun docstring)* |
| 15 | `PermissionsBody` | `dashboard_routes/settings.py` | BaseModel | 0 | *(nessun docstring)* |
| 16 | `FallbackChainBody` | `dashboard_routes/settings.py` | BaseModel | 0 | *(nessun docstring)* |
| 17 | `PresetApply` | `dashboard_routes/settings.py` | BaseModel | 0 | *(nessun docstring)* |

```
  funzioni  150
  classi     17
  TOTALE    167   <- il numero del righello del lead
```

