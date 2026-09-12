# `verimem/wake.py` — 1.725 righe, 58 funzioni

**L'esecutore.** *«Wake cycle — the executor.»* Il file più grande dopo il gate, e l'unico
della mia superficie che **si apre con la sicurezza invece che col mestiere**. Mappato su
`7b9e8ca1`.

---

## 1. Le prime OTTO funzioni del file sono difese contro la prompt injection

Prima di qualunque cosa riguardi l'esecuzione, righe 83-249, sotto un'intestazione esplicita
`--- Prompt-injection defense (CVE-008) ---`:

| funzione | cosa impedisce |
|---|---|
| `_wrap_untrusted` (105) | l'osservazione esterna entra **marcata** `untrusted_content` |
| `_is_external_source_in_recent_traces` (124) | sapere se le ultime tracce hanno toccato l'esterno |
| `_episode_is_contaminated` (145) | *«True iff any past trace fetched external content»* |
| `_injection_review_blocks_call` (162) | **rifiutare** la chiamata che sta per partire |
| `_macro_blocked_by_injection_guard` (174) | la **scorciatoia** — vedi §2 |
| `_extract_source_arg` (216) | da dove viene il testo di una tool call |
| `_submit_cutoff_index` (232) | dopo quale indice non si può più «consegnare» |

🔑 **Il contenuto esterno è marcato, non filtrato**: il prodotto non prova a ripulire un
testo ostile, lo **circonda** e poi decide se una chiamata può partire. È la stessa scelta di
`_hang_watchdog` (rendere visibile invece che prevenire), applicata alla sicurezza.

---

## 2. 🔴 CVE-008 — la difesa aveva una scorciatoia intorno

> riga 175: *«CVE-008 (rescan2 2026-06-02): **the procedural macro fast-path bypassed** [la
> guardia]»*
> riga 1142: *«…the LLM loop gates dangerous tools»*

⇒ La guardia c'era **sul percorso lento** (il loop dell'LLM) e **non su quello veloce** (il
macro compilato, `_try_compiled_macro` a 1103). Una difesa presente e aggirabile **per
costruzione**, trovata in un rescan.

📌 È la forma che sui nostri appunti si chiama *«il bug è la GIUNTURA»*: nessuno dei due
percorsi era sbagliato, mancava il controllo **dove si incontravano**. Vale la pena cercarla
altrove: **ogni fast-path è un candidato**.

✅ **E oggi è CHIUSA** — la guardia del macro è chiamata a `1146`, quella del loop a `1444`,
e il fast-path deterministico è **uno solo**: la verifica sta nel §7. Questo paragrafo
racconta il difetto **storico**, non uno aperto.

---

## 3. Il file ha UNA superficie sola per tutto — e il mio sospetto contrario era sbagliato

    _run_with_strategy (1387)   «The unified wake loop — SINGLE SOURCE OF TRUTH»
    _run_loop_tools    (1504)   «thin facade over _run_with_strategy»   NESSUNO LA NOMINA
    _run_loop_react    (1630)   «thin facade over _run_with_strategy»   NESSUNO LA NOMINA
    _call_tool         (1590)   «Single source of truth for BOTH»

🔴 **CORREZIONE DEL 09/09, e riguarda come ho scritto questa riga ieri.** Avevo
riportato «thin facade» dal loro docstring **senza cercarne i chiamanti**. Cercati
oggi, non ce ne sono:

    def _run_loop        wake.py:1353   <- l'ingresso VERO, chiamato a 1296 e 1313
    def _run_loop_tools  wake.py:1504   zero riferimenti, nel prodotto e nei test
    def _run_loop_react  wake.py:1630   zero riferimenti, nel prodotto e nei test

⇒ Non sono facciate: sono le **porte di prima**, rimpiazzate da `_run_loop` e mai
tolte. E il loro docstring non dice «facciata» e basta, dice **«entry»** — cioè
promette di essere il punto d'ingresso di una modalità. ⇒ verdetto
**NON COME PROMESSO**, non «codice morto»: la differenza è che un lettore che
cerca da dove parte la modalità tool-use finisce qui, e qui non parte niente.

📌 Stessa forma a `_system_prompt` (1263): esiste, ma il prompt di sistema lo
costruisce `strategy.system_prompt`, usata a 1411 e definita in
`wake_strategy.py:109, 183, 352`. La versione di `WakeAgent` non è nominata da
nessuno.

🔑 **La lezione è su di me**: «un docstring dice cosa credeva l'autore» è una
regola che avevo già scritto, e ieri l'ho applicata al codice altrui e non alla
mia mappa. Riportare una promessa non è verificarla — e una mappa che ricopia i
docstring propaga le promesse invece di misurarle.

⚠️ **Qui avevo scritto che il pruning invece era duplicato**, perché `ast` conta 22 e 21
righe per `_prune_working_memory` e `_prune_working_memory_react`, e il secondo docstring
dice *«same algorithm, different encoding»*. **Ho eseguito il confronto invece di
pubblicare il sospetto, e il sospetto è caduto:**

    istruzioni (senza docstring):  3  contro  3
    l'algoritmo vero:              working_memory.prune_messages (riga 59)
    le due strategie:              react_obs_is_candidate · react_obs_replace

⇒ **Non sono due implementazioni: sono due adattatori da tre istruzioni** su un algoritmo
unico, che vive in un altro modulo. Le 21 righe di differenza erano **quasi tutte
docstring**. Il pattern è quello giusto — strategy — e il file lo applica anche al pruning,
non solo al loop.

📌 **La lezione è sul metodo, non sul codice**: contare le righe di due funzioni **non**
dice se una logica è duplicata. `_dispatch_native` (5 righe) e `_dispatch` (18) sono
asimmetrici per la stessa ragione — uno riceve argomenti già strutturati, l'altro deve
parsare `ActionInput` — e **non li ho verificati allo stesso modo**, quindi su quelli non
affermo niente.

---

## 4. Cosa fa davvero l'esecutore: memoria che entra nel prompt

Metà delle 58 funzioni serve a **costruire il contesto da episodi passati**:

- `_retrieve_skills` (614) — *«Bayesian-weighted retrieval: cosine-pool then Thompson…»*, con
  `_retrieve_skills_legacy` (681) accanto: *«il percorso pre-bayesiano, ignora la fitness»*
- `_forward_replay_block` (829) — un **«predicted path»** deterministico dalla memoria
- `_avoid_path_block` (969) — il prefisso di azioni degli episodi **falliti** simili
- `_divergence_block` (1034) + `_historical_divergence_counts` (916) — dove questa
  esecuzione si discosta da un «gemello riuscito»
- `_build_episode_context` (762) — la deriva TCM del contesto
- `_apply_lateral_inhibition` (415) — filtro greedy sui link antagonisti

🔑 **Il prodotto non ricorda per rispondere: ricorda per DECIDERE il prossimo passo.** Queste
sei funzioni sono la differenza fra una memoria e un esecutore che impara.

---

## 5. La riga che ho curato oggi

`wake.py:301` — `np.random.default_rng()`. Era **dentro** `with lock_import()` insieme
all'assegnazione (lavoro sotto il lock, violazione della regola di `_import_lock` scritta da
me il 06/09); ora l'import è esplicito dentro il blocco e la costruzione fuori (`cd644eff`).
Ed è il punto in cui la richiesta si fermava nel dump di T1b.

---

## 6. Le 58 funzioni

**8 top-level** (7 private di difesa + `trivial_validator` pubblica) · **3 classi**
(`WakeConfig`, `WakeResult`, `WakeAgent`) · **50 metodi** di `WakeAgent`, di cui **20
pubblici** (le statistiche `FORGIA`: istogrammi, breakdown, co-occorrenze, finestre
temporali, `predict_next_skill`, i tre di contesto `reset`/`checkpoint`/`restore`) e **30
privati** (recupero, costruzione del prompt, i due loop, i due pruner, i due dispatch).

---

## 7. Quello che questa mappa NON dice — dichiarato

- ~~Non ho misurato se i due pruner divergano~~ → **MISURATO, e ha smentito me** (§3):
  tre istruzioni ciascuno, algoritmo unico in `working_memory.prune_messages`. *Il limite era
  scritto e l'ho chiuso con un comando — se non l'avessi fatto, avrei pubblicato un ticket
  che non esiste.*
- **`_dispatch_native` (5 righe) contro `_dispatch` (18)**: NON verificati allo stesso modo.
  L'asimmetria ha una spiegazione plausibile nei docstring (uno riceve argomenti già
  strutturati, l'altro parsa `ActionInput`), ma **plausibile non è misurato** e su questo
  non affermo niente.
- ~~Non ho verificato che la guardia di CVE-008 copra OGNI fast-path~~ → **VERIFICATO, e
  chiude in positivo.** La domanda era *«quanti percorsi saltano il loop dell'LLM?»*:

      _macro_blocked_by_injection_guard   definita 174   CHIAMATA a 1146  (dentro _try_compiled_macro)
      _injection_review_blocks_call       definita 162   CHIAMATA a 1444  (dentro il loop LLM)
      riga 1101   «--- Procedural compilation fast-path ---»   ← l'unico
      riga  846   «informational, not a deterministic fast-path» ← dichiara di NON esserlo

  ⇒ **C'è UN solo fast-path deterministico, e ha la sua guardia**, con lo stesso criterio
  del percorso lento (il docstring a 181: *«hatch as `_injection_review_blocks_call`»*). La
  cura di CVE-008 non ha lasciato scorciatoie aperte, e un secondo punto che poteva
  sembrarne una **dichiara di non esserlo**.
- **Le funzioni `FORGIA` sono lette solo di nome**: sono venti superfici pubbliche di
  statistica, e non so quante siano usate da un chiamante vero.
- `_critique`, `_tool_catalog`, `_system_prompt`, `_estimate_messages_size`: solo nomi.

---

*Mappato da ws5 (Piattaforma) su `7b9e8ca1`. Le misure di riga del §3 sono mie, con `ast`.*

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


### `verimem/wake.py` — 61 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/wake.py:79` `trivial_validator` | funzione | **nessuno** | `tests/test_compilation.py` | NON MISURATO |
| 2 | `verimem/wake.py:105` `_wrap_untrusted` | funzione: Wrap observation in untrusted_content markers when source is external. | `verimem/wake.py` | `tests/security/test_pentest_validation.py`; `tests/security/test_prompt_injection_defense.py` (+1) | NON MISURATO |
| 3 | `verimem/wake.py:124` `_is_external_source_in_recent_traces` | funzione: True if any of the last `lookback` traces was an external-source tool. | **nessuno** | `tests/security/test_prompt_injection_defense.py`; `tests/test_wake_extra.py` | NON MISURATO |
| 4 | `verimem/wake.py:145` `_episode_is_contaminated` | funzione: True iff any past trace fetched external content. | `verimem/wake.py` | `tests/security/test_pentest_validation.py`; `tests/test_wake_extra.py` | NON MISURATO |
| 5 | `verimem/wake.py:162` `_injection_review_blocks_call` | funzione: Return True if the impending tool call should be refused. | `verimem/wake.py` | `tests/security/test_pentest_validation.py`; `tests/security/test_prompt_injection_defense.py` (+1) | NON MISURATO |
| 6 | `verimem/wake.py:174` `_macro_blocked_by_injection_guard` | funzione: CVE-008 (rescan2 2026-06-02): the procedural macro fast-path bypassed | `verimem/wake.py` | `tests/test_wake_macro_injection_guard_scan68.py` | NON MISURATO |
| 7 | `verimem/wake.py:188` `_macro_blocked_by_injection_guard._tool_of` | funzione | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 8 | `verimem/wake.py:216` `_extract_source_arg` | funzione: Pick the first 'sourcey' field from a tool call's input. | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 9 | `verimem/wake.py:232` `_submit_cutoff_index` | funzione: rescan2 2026-06-02 (wake.py:1391-1428): index AFTER which parallel tool | `verimem/wake.py` | `tests/test_wake_post_submit_sideeffect_scan68.py` | NON MISURATO |
| 10 | `verimem/wake.py:250` `WakeConfig` | classe | `verimem/agent.py`; `verimem/cli.py` (+1) | `tests/test_active_memory_integration.py`; `tests/test_bayesian_gates.py` (+11) | NON MISURATO |
| 11 | `verimem/wake.py:266` `WakeResult` | classe | `verimem/agent.py`; `verimem/wake.py` | `tests/test_engram_code.py`; `tests/test_wake_used_macro.py` | NON MISURATO |
| 12 | `verimem/wake.py:277` `WakeAgent` | classe | `verimem/agent.py` | `tests/test_active_memory_integration.py`; `tests/test_agent_smoke.py` (+28) | NON MISURATO |
| 13 | `verimem/wake.py:278` `WakeAgent.__init__` | funzione | `verimem/client.py`; `verimem/document_index.py` (+2) | `tests/test_i_default_che_il_readme_dichiara.py`; `tests/test_windows_no_console_popup.py` | NON MISURATO |
| 14 | `verimem/wake.py:322` `WakeAgent.skill_usage_histogram` | funzione: FORGIA pezzo #142: skill_id → number of episodes that used it. | `verimem/wake.py` | `tests/test_memory_skill_histogram.py`; `tests/test_scaling_perf_regression.py` (+2) | NON MISURATO |
| 15 | `verimem/wake.py:330` `WakeAgent.outcome_breakdown` | funzione: FORGIA pezzo #146: outcome → episode count. | `verimem/wake.py` | `tests/test_memory_outcome_breakdown.py`; `tests/test_wake_admin_aliases.py` | NON MISURATO |
| 16 | `verimem/wake.py:337` `WakeAgent.skill_co_occurrence` | funzione: FORGIA pezzo #159: which skills appear together with `skill_id`. | `verimem/mcp_server.py`; `verimem/wake.py` | `tests/test_memory_skill_cooccurrence.py`; `tests/test_skill_co_occurrence.py` (+1) | NON MISURATO |
| 17 | `verimem/wake.py:347` `WakeAgent.skill_bundle_candidates` | funzione: FORGIA pezzo #161: surface skill_bundle_candidates on the agent. | `verimem/mcp_server.py`; `verimem/sleep.py` (+1) | `tests/test_memory_skill_bundles.py`; `tests/test_wake_skill_bundles.py` | NON MISURATO |
| 18 | `verimem/wake.py:363` `WakeAgent.compound_skills` | funzione: FORGIA pezzo #167: skills synthesized from a bundle of 2+ parents. | `verimem/mcp_server.py` | `tests/test_wake_compound_skills.py` | NON MISURATO |
| 19 | `verimem/wake.py:371` `WakeAgent.prime_skills_via_topics` | funzione: FORGIA pezzo #181: schema-driven skill priming. | **nessuno** | `tests/test_wake_schema_priming.py` | NON MISURATO |
| 20 | `verimem/wake.py:415` `WakeAgent._apply_lateral_inhibition` | funzione: FORGIA pezzo #171: greedy filter on antagonist links. | `verimem/wake.py` | `tests/test_wake_lateral_inhibition.py` | NON MISURATO |
| 21 | `verimem/wake.py:448` `WakeAgent.steps_summary` | funzione: FORGIA pezzo #147: trace-step distribution stats. | `verimem/wake.py` | `tests/test_memory_steps_summary.py`; `tests/test_wake_admin_aliases.py` | NON MISURATO |
| 22 | `verimem/wake.py:455` `WakeAgent.token_usage_summary` | funzione: FORGIA pezzo #148: aggregate token usage across all episodes. | `verimem/memory.py`; `verimem/wake.py` | `tests/test_memory_method_aliases.py`; `tests/test_memory_token_usage.py` (+1) | NON MISURATO |
| 23 | `verimem/wake.py:462` `WakeAgent.find_by_task` | funzione: FORGIA pezzo #150: find every episode for a given task_text. | **nessuno** | **nessuno** | MAI CHIAMATA |
| 24 | `verimem/wake.py:470` `WakeAgent.episodes_in_window` | funzione: FORGIA pezzo #150: episodes in [start_ts, end_ts). | `verimem/memory.py`; `verimem/wake.py` | `tests/test_memory_window.py` | NON MISURATO |
| 25 | `verimem/wake.py:478` `WakeAgent.recent_episodes` | funzione: FORGIA pezzo #132: return the K most recent episodes. | `verimem/briefing.py`; `verimem/mcp_server.py` | `tests/test_memory_delete.py` | NON MISURATO |
| 26 | `verimem/wake.py:487` `WakeAgent.delete_episode` | funzione: Delete one episode by id. Thin delegate to memory.delete(). | **nessuno** | `tests/test_memory_delete.py` | NON MISURATO |
| 27 | `verimem/wake.py:498` `WakeAgent.metrics` | funzione: Snapshot of WakeAgent-level stats. | **nessuno** | `tests/test_agent_smoke.py`; `tests/test_wake_metrics.py` | NON MISURATO |
| 28 | `verimem/wake.py:534` `WakeAgent.predict_next_skill` | funzione: Predict the most likely next skill given a usage history. | **nessuno** | `tests/test_e2e_memory_integration.py`; `tests/test_wake_predict_next_skill.py` | NON MISURATO |
| 29 | `verimem/wake.py:566` `WakeAgent.reset_context` | funzione: Snap the cross-session ContextEngine state back to zero. | **nessuno** | `tests/test_e2e_memory_integration.py`; `tests/test_wake_context_lifecycle.py` | NON MISURATO |
| 30 | `verimem/wake.py:577` `WakeAgent.checkpoint_context` | funzione: Return a defensive COPY of the current context engine state. | **nessuno** | `tests/test_e2e_memory_integration.py`; `tests/test_wake_context_lifecycle.py` | NON MISURATO |
| 31 | `verimem/wake.py:590` `WakeAgent.restore_context` | funzione: Load a previously-saved context state into the engine. | **nessuno** | `tests/test_e2e_memory_integration.py`; `tests/test_wake_context_lifecycle.py` | NON MISURATO |
| 32 | `verimem/wake.py:614` `WakeAgent._retrieve_skills` | funzione: Bayesian-weighted retrieval: cosine-pool then Thompson re-rank. | `verimem/wake.py` | `tests/test_wake_extra.py`; `tests/test_wake_inhibition_e2e.py` | NON MISURATO |
| 33 | `verimem/wake.py:681` `WakeAgent._retrieve_skills_legacy` | funzione: The pre-Bayesian path: top-k cosine, ignores fitness. | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 34 | `verimem/wake.py:695` `WakeAgent._retrieve_episodes` | funzione | `verimem/wake.py` | `tests/test_wake_cross_session_context.py`; `tests/test_wake_dg_retrieval.py` (+2) | NON MISURATO |
| 35 | `verimem/wake.py:762` `WakeAgent._build_episode_context` | funzione: Run the TCM context drift over the episode's task + observations. | `verimem/wake.py` | `tests/test_wake_tcm_integration.py` | NON MISURATO |
| 36 | `verimem/wake.py:798` `WakeAgent._build_user_prompt` | funzione | `verimem/wake.py` | `tests/test_forward_replay.py`; `tests/test_wake_extra.py` | NON MISURATO |
| 37 | `verimem/wake.py:829` `WakeAgent._forward_replay_block` | funzione: Build a deterministic 'predicted path' block from past memory. | `verimem/wake.py` | `tests/test_active_memory_integration.py`; `tests/test_bayesian_gates.py` (+4) | NON MISURATO |
| 38 | `verimem/wake.py:916` `WakeAgent._historical_divergence_counts` | funzione: For each step of the success reference, count how many past | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 39 | `verimem/wake.py:969` `WakeAgent._avoid_path_block` | funzione: Surface the action prefix of recent FAILED similar episodes. | `verimem/wake.py` | `tests/test_wake_extra.py` | NON MISURATO |
| 40 | `verimem/wake.py:1034` `WakeAgent._divergence_block` | funzione: Run trace alignment between `failure` and a success-twin. | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 41 | `verimem/wake.py:1103` `WakeAgent._try_compiled_macro` | funzione: Run the top skill's compiled macro if applicable. | `verimem/wake.py` | `tests/test_bayesian_gates.py`; `tests/test_macro_abort_salvage.py` (+1) | NON MISURATO |
| 42 | `verimem/wake.py:1197` `WakeAgent._adaptive_macro_threshold` | funzione: Lower the similarity threshold when the compiled macro is high-confidence. | `verimem/wake.py` | `tests/test_rnd_active_memory.py`; `tests/test_wake_extra.py` | NON MISURATO |
| 43 | `verimem/wake.py:1211` `WakeAgent._prioritise_episodes` | funzione: Rank a set of candidate episodes by composite priority. | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 44 | `verimem/wake.py:1239` `WakeAgent._skill_similarity` | funzione: Cosine similarity between task and the skill's effective trigger embedding. | `verimem/wake.py` | `tests/test_wake_extra.py` | NON MISURATO |
| 45 | `verimem/wake.py:1257` `WakeAgent._tool_catalog` | funzione | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 46 | `verimem/wake.py:1263` `WakeAgent._system_prompt` | funzione — **soppiantata da `strategy.system_prompt`, usata a wake.py:1411 e definita in wake_strategy.py:109, 183, 352; questa non e' nominata** | **nessuno** | **nessuno** | MAI CHIAMATA |
| 47 | `verimem/wake.py:1268` `WakeAgent.run` | funzione | `verimem/agent.py`; `verimem/band_escalation.py` (+16) | `tests/perf/bench_briefing_proactive.py`; `tests/perf/bench_briefing_proactive_v2.py` (+117) | NON MISURATO |
| 48 | `verimem/wake.py:1353` `WakeAgent._run_loop` | funzione: Pick an encoding strategy and run the unified wake loop. | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 49 | `verimem/wake.py:1387` `WakeAgent._run_with_strategy` | funzione: The unified wake loop — single source of truth. | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 50 | `verimem/wake.py:1504` `WakeAgent._run_loop_tools` | funzione: Native tool-use entry — thin facade over `_run_with_strategy`. — **il docstring la dichiara «Native tool-use ENTRY», ma l'ingresso vero e' `_run_loop` (def 1353, chiamata a 1296 e 1313) e nessuno la nomina** | **nessuno** | **nessuno** | NON COME PROMESSO |
| 51 | `verimem/wake.py:1524` `WakeAgent._estimate_messages_size` | funzione: Thin wrapper — kept on the class for backward compat with tests | **nessuno** | `tests/test_wake_extra.py` | NON MISURATO |
| 52 | `verimem/wake.py:1529` `WakeAgent._prune_working_memory` | funzione: Trim mid-trajectory tool observations once the running message | **nessuno** | `tests/test_rnd_active_memory.py`; `tests/test_wake_extra.py` | NON MISURATO |
| 53 | `verimem/wake.py:1553` `WakeAgent._format_tool_results` | funzione: Format tool results — backward-compat shim around | **nessuno** | `tests/test_wake_extra.py` | NON MISURATO |
| 54 | `verimem/wake.py:1583` `WakeAgent._dispatch_native` | funzione: Native tool-use dispatch — args come in already structured. | **nessuno** | `tests/test_wake_extra.py` | NON MISURATO |
| 55 | `verimem/wake.py:1590` `WakeAgent._call_tool` | funzione: Execute one tool by name. Single source of truth for both | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 56 | `verimem/wake.py:1617` `WakeAgent._tool_schemas` | funzione: Build the tools payload for native tool-use APIs. | `verimem/wake.py`; `verimem/wake_strategy.py` | **nessuno** | NON MISURATO |
| 57 | `verimem/wake.py:1630` `WakeAgent._run_loop_react` | funzione: ReAct text-mode entry — thin facade over `_run_with_strategy`. — **il docstring la dichiara «ReAct text-mode ENTRY»; stessa prova di `_run_loop_tools`: nessun riferimento nel prodotto ne' nei test** | **nessuno** | **nessuno** | NON COME PROMESSO |
| 58 | `verimem/wake.py:1650` `WakeAgent._prune_working_memory_react` | funzione: ReAct text-mode pruner — same algorithm, different encoding. | **nessuno** | `tests/test_wake_extra.py` | NON MISURATO |
| 59 | `verimem/wake.py:1673` `WakeAgent._dispatch` | funzione: ReAct text-mode dispatch — parses ActionInput as JSON first. | **nessuno** | `tests/test_wake_extra.py` | NON MISURATO |
| 60 | `verimem/wake.py:1695` `WakeAgent._critique` | funzione | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 61 | `verimem/wake.py:1716` `_extract_answer` | funzione: Best-effort extraction of the answer from submit_solution payload. | **nessuno** | **nessuno** | MAI CHIAMATA |

<!-- /TABELLA-FUNZIONI ws5 -->





