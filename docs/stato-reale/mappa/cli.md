# mappa — `verimem/cli.py`

**owner ws6 Aldo** (presa da ws7 Iris, ferma dalle 12:32 — il lead me l'ha
assegnata alle 13:3x) · base `20257636` · aperto 2026-09-09

**5.997 righe · 130 funzioni · 1 classe = 131 definizioni.** Contate con `ast`,
lo stesso righello che ha chiuso i miei 21 file a 480/480.

## ⚠️ Prima di ogni riga: qui il «mai chiamata» e' una trappola, 89 volte

`cli.py` e' **Typer**. Ottantanove definizioni su 131 portano un decoratore
(`@app.command("recall")`, `@facts_app.command("add")`, …) e **non sono chiamate
da nessuna riga di codice**: le chiama il framework al dispatch. Un righello che
cerca `nome(` le dichiarerebbe tutte morte — e' la trappola di `audit_head_at`,
che nei miei 21 file mi aveva prodotto **un** falso morto, moltiplicata per 89.

⇒ Per i comandi il criterio non e' «chi la chiama» ma **«quale test la invoca
come comando»**, e quel righello esiste gia': l'ha scritto ws7 Iris.

## Il righello di ws7, eseguito qui e non rifatto

`docs/stato-reale/banchi/ws7-quali-comandi-della-cli-nessun-test-invoca.py`
raccoglie le liste letterali di argomenti nei test (`invoke(cli.app, ["facts",
"retirement-log"])`) invece di cercare il nome — perche' `serve` compare in 672
file di test come parola inglese. Eseguito sul mio worktree adesso:

```
cli.py:                         5997 righe
comandi dichiarati:             88
invocazioni viste nei test:     4956
controllo positivo (warmup):    visto
comandi che NESSUN test invoca: 22
EXIT=0
```

Stessi numeri della sua mappa (`CLI-claims.md`): **la sua misura si riproduce**.
I 22 comandi e il perche' contino per un utente stanno li', e non li ricopio.

📌 **Due numeri diversi sulla stessa superficie, e servono a due domande.** Il
suo righello dice 22 comandi mai **invocati**; il mio `git grep -lw` sul nome
della funzione dice che 59 funzioni-comando non sono mai **nominate** nei
test. Non sono in contraddizione: un test puo' invocare `["facts", "add"]` senza
scrivere mai `facts_add_cmd`. Il numero che conta per l'utente e' il suo; il mio
serve solo a sapere se esiste anche un test unitario diretto.

## 1. I comandi — 89 definizioni decorate

67 invocati da almeno un test, **22 no**.

| riga | funzione | comando dell'utente | chiamata da | test che lo INVOCA | verdetto | prova |
|---|---|---|---|---|---|---|
| 42 | `_radice` | `verimem @callback` | Typer (`@app.command`) | 🔴 **nessun test lo invoca** | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 161 | `flow_tail_cmd` | `verimem flow tail` | Typer (`@flow_app.command`) | **1** — `test_cli_flow_tail.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 173 | `lab_live_cmd` | `verimem lab live` | Typer (`@lab_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 207 | `code` | `verimem code` | Typer (`@app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 225 | `run` | `verimem run` | Typer (`@app.command`) | **2** — `test_cli.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 242 | `status` | `verimem status` | Typer (`@app.command`) | **11** — `test_cli.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 342 | `health` | `verimem health` | Typer (`@app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 358 | `backup_all` | `verimem backup-all` | Typer (`@app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 486 | `warmup` | `verimem warmup` | Typer (`@app.command`) | **2** — `test_cli_warmup.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 673 | `tiers` | `verimem tiers` | Typer (`@app.command`) | **1** — `test_inventario_dei_tier.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 716 | `doctor` | `verimem doctor` | Typer (`@app.command`) | **1** — `test_gate_model_fetch_and_doctor.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 741 | `airgap` | `verimem airgap` | Typer (`@app.command`) | **1** — `test_cli_airgap.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 802 | `index` | `verimem index` | Typer (`@app.command`) | **2** — `test_cli_docs.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 840 | `search_docs` | `verimem search-docs` | Typer (`@app.command`) | **4** — `test_cli_docs.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 972 | `gateway_serve` | `verimem gateway serve` | Typer (`@gateway_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 1021 | `console_cmd` | `verimem console` | Typer (`@app.command`) | **1** — `test_gateway_tenant_reserved.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 1058 | `gateway_keys_create` | `verimem gateway keys create` | Typer (`@gateway_keys_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 1081 | `gateway_keys_list` | `verimem gateway keys list` | Typer (`@gateway_keys_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 1097 | `gateway_backup_cmd` | `verimem gateway backup` | Typer (`@gateway_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 1117 | `gateway_restore_cmd` | `verimem gateway restore` | Typer (`@gateway_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 1134 | `gateway_keys_revoke` | `verimem gateway keys revoke` | Typer (`@gateway_keys_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 1153 | `import_cmd` | `verimem import` | Typer (`@app.command`) | **1** — `test_cli_import.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 1308 | `remember_cmd` | `verimem remember` | Typer (`@app.command`) | **3** — `test_la_cli_sa_scrivere_una_scadenza.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 1574 | `recall_cmd` | `verimem recall` | Typer (`@app.command`) | **13** — `test_chi_perde_un_fatto_per_eta_lo_sa.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 1777 | `ask_cmd` | `verimem ask` | Typer (`@app.command`) | **6** — `test_ask_taceva_dove_recall_avvisava.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 1874 | `correct_cmd` | `verimem correct` | Typer (`@app.command`) | **3** — `test_correct_dice_quale_ramo_ha_preso.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 1962 | `ignorance_cmd` | `verimem ignorance` | Typer (`@app.command`) | **2** — `test_la_mappa_dell_ignoranza_e_raggiungibile.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2030 | `telemetry_cmd` | `verimem telemetry` | Typer (`@app.command`) | **2** — `test_json_esce_json_anche_quando_non_c_e_niente.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2154 | `trust_stats_cmd` | `verimem stats` | Typer (`@app.command`) | **4** — `test_dashboard_overview.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2252 | `trust` | `verimem trust` | Typer (`@app.command`) | **7** — `test_cli_trust.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2417 | `sleep_now` | `verimem sleep-now` | Typer (`@app.command`) | **1** — `test_cli_agent_namespace.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2444 | `wake` | `verimem wake` | Typer (`@app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 2473 | `sleep` | `verimem sleep` | Typer (`@app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 2488 | `benchmark` | `verimem benchmark` | Typer (`@app.command`) | **1** — `test_read_connection_is_reused.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2517 | `tui` | `verimem tui` | Typer (`@app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 2524 | `mcp` | `verimem mcp` | Typer (`@app.command`) | **4** — `test_cli_agent_namespace.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2574 | `chat` | `verimem chat` | Typer (`@app.command`) | **1** — `test_cli_agent_namespace.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2641 | `reset` | `verimem reset` | Typer (`@app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 2652 | `metrics` | `verimem metrics` | Typer (`@app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 2659 | `dashboard` | `verimem dashboard` | Typer (`@app.command`) | **1** — `test_cli.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2729 | `providers_list` | `verimem providers list` | Typer (`@providers_app.command`) | **1** — `test_cli.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2755 | `providers_scan` | `verimem providers scan` | Typer (`@providers_app.command`) | **1** — `test_cli.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2788 | `providers_models` | `verimem providers models` | Typer (`@providers_app.command`) | **1** — `test_cli.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2810 | `providers_active` | `verimem providers active` | Typer (`@providers_app.command`) | **1** — `test_cli.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2827 | `providers_check` | `verimem providers check` | Typer (`@providers_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 2921 | `skills_list` | `verimem skills list` | Typer (`@skills_app.command`) | **1** — `test_cli.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 2939 | `introspect` | `verimem introspect` | Typer (`@app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 3003 | `skills_dedup` | `verimem skills dedup` | Typer (`@skills_app.command`) | **1** — `test_dedup_skill_e_raggiungibile.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3038 | `skills_show` | `verimem skills show` | Typer (`@skills_app.command`) | **1** — `test_cli.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3060 | `episodes_list` | `verimem episodes list` | Typer (`@episodes_app.command`) | **1** — `test_cli.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3075 | `episodes_show` | `verimem episodes show` | Typer (`@episodes_app.command`) | **1** — `test_cli.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3203 | `facts_list` | `verimem facts list` | Typer (`@facts_app.command`) | **4** — `test_cli_facts.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3307 | `facts_recall` | `verimem facts recall` | Typer (`@facts_app.command`) | **2** — `test_cli_facts.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3376 | `facts_search` | `verimem facts search` | Typer (`@facts_app.command`) | **3** — `test_cli_facts.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3433 | `facts_label` | `verimem facts label` | Typer (`@facts_app.command`) | **1** — `test_le_etichette_epistemiche_sono_collegate.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3482 | `facts_get` | `verimem facts get` | Typer (`@facts_app.command`) | **2** — `test_cli_facts.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3539 | `facts_forget` | `verimem facts forget` | Typer (`@facts_app.command`) | **3** — `test_cli_facts.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3720 | `facts_undo` | `verimem facts undo` | Typer (`@facts_app.command`) | **1** — `test_facts_forget_topic.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3779 | `facts_undo_list` | `verimem facts undo-list` | Typer (`@facts_app.command`) | **1** — `test_facts_forget_topic.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3807 | `facts_quarantine_log` | `verimem facts quarantine-log` | Typer (`@facts_app.command`) | **1** — `test_la_serie_della_quarantena_su_ogni_porta.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3857 | `facts_retirement_log` | `verimem facts retirement-log` | Typer (`@facts_app.command`) | **3** — `test_control_room_porte.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 3994 | `facts_backup` | `verimem facts backup` | Typer (`@facts_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 4039 | `facts_restore` | `verimem facts restore` | Typer (`@facts_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 4078 | `facts_safety` | `verimem facts safety` | Typer (`@facts_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 4175 | `facts_capability` | `verimem facts capability` | Typer (`@facts_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 4241 | `facts_stats` | `verimem facts stats` | Typer (`@facts_app.command`) | **1** — `test_cli_facts.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 4273 | `facts_anti_confab_scan` | `verimem facts anti-confab-scan` | Typer (`@facts_app.command`) | **1** — `test_cli_facts.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 4300 | `facts_anti_confab_apply` | `verimem facts anti-confab-apply` | Typer (`@facts_app.command`) | **1** — `test_cli_facts.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 4367 | `facts_add` | `verimem facts add` | Typer (`@facts_app.command`) | **10** — `test_all_write_channels_judge_a_source.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 4793 | `facts_backfill` | `verimem facts backfill` | Typer (`@facts_app.command`) | **1** — `test_cli_facts_add.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 4817 | `facts_archive_narration` | `verimem facts archive-narration` | Typer (`@facts_app.command`) | 🔴 **nessun test lo invoca** | 🔴 **NON MISURATO** — nessun test invoca il comando | banco ws7: `comandi che NESSUN test invoca: 22`, EXIT=0 |
| 4856 | `facts_cleanup_episode_telemetry` | `verimem facts cleanup-episode-telemetry` | Typer (`@facts_app.command`) | **1** — `test_episode_telemetry_cleanup.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 4885 | `facts_requalify_quarantined` | `verimem facts requalify-quarantined` | Typer (`@facts_app.command`) | **1** — `test_requalify_quarantined.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 4973 | `consolidate_dry_run` | `verimem consolidate dry-run` | Typer (`@consolidate_app.command`) | **1** — `test_cli_consolidate.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5023 | `consolidate_apply` | `verimem consolidate apply` | Typer (`@consolidate_app.command`) | **1** — `test_cli_consolidate.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5057 | `consolidate_status` | `verimem consolidate status` | Typer (`@consolidate_app.command`) | **1** — `test_cli_consolidate.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5112 | `agent_guide_cmd` | `verimem agent-guide` | Typer (`@app.command`) | **1** — `test_agent_guide_single_source.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5308 | `save_cmd` | `verimem save` | Typer (`@app.command`) | **11** — `test_chain_surfaces_show_the_verdict.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5492 | `tip_cmd` | `verimem tip` | Typer (`@app.command`) | **3** — `test_chain_surfaces_show_the_verdict.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5534 | `recent_cmd` | `verimem recent` | Typer (`@app.command`) | **2** — `test_chain_surfaces_show_the_verdict.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5552 | `chain_show_cmd` | `verimem chain show` | Typer (`@chain_app.command`) | **1** — `test_continuity.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5596 | `chain_orphans_cmd` | `verimem chain orphans` | Typer (`@chain_app.command`) | **1** — `test_continuity.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5620 | `chain_relink_cmd` | `verimem chain relink` | Typer (`@chain_app.command`) | **1** — `test_continuity.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5645 | `handoff_prepare_cmd` | `verimem handoff prepare` | Typer (`@handoff_app.command`) | **1** — `test_continuity.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5676 | `handoff_show_cmd` | `verimem handoff show` | Typer (`@handoff_app.command`) | **1** — `test_continuity.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5694 | `handoff_log_cmd` | `verimem handoff log` | Typer (`@handoff_app.command`) | **1** — `test_continuity.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5711 | `digest_cmd` | `verimem digest` | Typer (`@app.command`) | **1** — `test_continuity.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5835 | `audit_anchor_cmd` | `verimem audit anchor` | Typer (`@audit_app.command`) | **1** — `test_tamper_anchor_receipt.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |
| 5894 | `audit_verify_cmd` | `verimem audit verify` | Typer (`@audit_app.command`) | **2** — `test_audit_mutations.py` | **FUNZIONA COME PROMESSO**, limitato a cio' che quel test asserisce | banco ws7 + `tests/test_cli.py` (sotto) |

## 2. Gli helper — 42 definizioni non decorate

Qui il criterio torna quello normale: chi la chiama dentro il file, e chi la
nomina nei test. **1 senza nessun chiamante interno** — l'unico candidato
a MAI CHIAMATA di questo file, verificato sotto.

| riga | funzione | chiamata da | test che la nominano | cosa promette | verdetto |
|---|---|---|---|---|---|
| 129 | `_principale` | 12 righe di questo file (1952, 3630, 3634, 3681…) | 2 — `test_il_nome_dell_attore_arriva_fino_al_campo.py` | Chi la CLI dice di essere quando ritira o cancella un fatto. | **FUNZIONA COME PROMESSO**, limitato |
| 231 | `_val` | 5 righe di questo file (232, 2294, 2318, 4472…) | 🔴 **nessuno** | — | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 426 | `_totale_di_default` | 1 righe di questo file (522…) | 2 — `test_il_readme_e_la_cli_dicono_lo_stesso_peso.py` | Quanto costa `warmup` senza opzioni, sommando cio' che davvero prende. | **FUNZIONA COME PROMESSO**, limitato |
| 452 | `_giorni_di_undo` | 2 righe di questo file (3638, 3692…) | 1 — `test_la_finestra_di_undo_e_una_sola.py` | La finestra di undo, DERIVATA da `UNDO_TTL_SECONDS` invece che scritta. | **FUNZIONA COME PROMESSO**, limitato |
| 473 | `_quanto_scarica` | 3 righe di questo file (431, 515, 555…) | 2 — `test_il_download_annunciato_e_quello_del_modello_in_uso.py` | How much that model costs, or an explicit «never measured». | **FUNZIONA COME PROMESSO**, limitato |
| 966 | `_gateway_data_dir` | 6 righe di questo file (993, 1044, 1070, 1084…) | 🔴 **nessuno** | — | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 1146 | `_import_llm` | 1 righe di questo file (1209…) | 1 — `test_cli_import.py` | LLM for the import ingest — separate factory so tests can stub it. | **FUNZIONA COME PROMESSO**, limitato |
| 1217 | `_agente_per_l3` | 1 righe di questo file (2307…) | 1 — `test_trust_dichiara_cio_che_ha_girato.py` | L'agente che serve a L3 per confrontare col corpus vivo. | **FUNZIONA COME PROMESSO**, limitato |
| 1227 | `_diagnosi_mcp_2x` | 1 righe di questo file (2561…) | 🔴 **nessuno** | La frase del `doctor` sulla rottura di `mcp` 2.x, se e solo se la | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 1249 | `_open_memory` | 7 righe di questo file (656, 1367, 1639, 1801…) | 15 — `test_ask_taceva_dove_recall_avvisava.py` | Factory hook (monkeypatchable in tests): the architecture-A entry — | **FUNZIONA COME PROMESSO**, limitato |
| 1265 | `_dichiara_store` | 2 righe di questo file (1646, 1729…) | 🔴 **nessuno** | Stampa QUALE store ha risposto, e quanti fatti contiene. | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 1422 | `_avviso_scaduti` | 5 righe di questo file (1463, 1732, 1737, 1857…) | 1 — `test_la_porta_non_diceva_che_stava_rispondendo_al_passato.py` | Dice quanti fatti la SCADENZA ha tolto dalla risposta, se ne ha tolti. | **FUNZIONA COME PROMESSO**, limitato |
| 1455 | `_avviso_al_passato` | 2 righe di questo file (1733, 1738…) | 🔴 **nessuno** | Dice che la risposta e' quella di un ALTRO istante, se lo e'. | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 1483 | `_avviso_freschezza` | 2 righe di questo file (1734, 1739…) | 🔴 **nessuno** | Dice quanti fatti l'ETA' tiene fuori dalla vista, se ne tiene. | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 1520 | `_avviso_pavimento` | 3 righe di questo file (1432, 1736, 1863…) | 3 — `test_ask_taceva_dove_recall_avvisava.py` | Dice che il migliore sta sotto il pavimento MISURATO, se ci sta. | **FUNZIONA COME PROMESSO**, limitato |
| 2116 | `_ledger_window` | 1 righe di questo file (2180…) | 1 — `test_lo_stato_non_dice_zero_quando_ha_giudicato_tutto.py` | ``(first_recorded_ts, % of stored facts written since then)``. | **FUNZIONA COME PROMESSO**, limitato |
| 2240 | `_verdetto_del_gate` | 1 righe di questo file (2337…) | 1 — `test_l_anteprima_nomina_lo_status_che_la_scrittura_produce.py` | La riga di esito dell'anteprima, per un'azione del gate. | **FUNZIONA COME PROMESSO**, limitato |
| 3092 | `_progress_printer` | 2 righe di questo file (2468, 2509…) | 🔴 **nessuno** | — | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 3099 | `_print_report` | 2 righe di questo file (2469, 2510…) | 🔴 **nessuno** | — | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 3127 | `_facts_data_dir` | 4 righe di questo file (3173, 4871, 4964, 5811…) | 2 — `test_consolidate_apply_episodes_path_audit3.py` | Resolve the engram data directory honouring env-time overrides. | **FUNZIONA COME PROMESSO**, limitato |
| 3151 | `_facts_sm` | 35 righe di questo file (3230, 3330, 3395, 3487…) | 5 — `test_consolidate_apply_episodes_path_audit3.py` | Build a SemanticMemory pointed at the corpus. | **FUNZIONA COME PROMESSO**, limitato |
| 3183 | `_fact_id_resolve` | 2 righe di questo file (3488, 3646…) | 1 — `test_la_scheda_di_un_fatto_dice_se_e_scaduto.py` | Resolve ``partial`` to a full Fact, accepting id prefix match. | **FUNZIONA COME PROMESSO**, limitato |
| 4557 | `_AgentShim` | 1 righe di questo file (4560…) | 1 — `test_pre_tool_use_hook.py` | — | **FUNZIONA COME PROMESSO**, limitato |
| 4558 | `__init__` | 🔴 **nessuna** | 269 — `seed_data.py` | — | **FUNZIONA COME PROMESSO**, limitato |
| 4952 | `_consolidate_em` | 1 righe di questo file (5040…) | 1 — `test_consolidate_apply_episodes_path_audit3.py` | Build an EpisodicMemory pointed at the env-resolved corpus. | **FUNZIONA COME PROMESSO**, limitato |
| 5095 | `_force_utf8_stdio` | 1 righe di questo file (5986…) | 1 — `test_cli_utf8_stdio.py` | Best-effort UTF-8 stdout/stderr so the CLI's status glyphs (✓ ✗ → ⚠) | **FUNZIONA COME PROMESSO**, limitato |
| 5138 | `_continuity_guard` | 11 righe di questo file (3452, 5343, 5497, 5541…) | 🔴 **nessuno** | Fail-loud in server mode (adversarial glm #6): continuity operates on | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 5153 | `_continuity_memory` | 4 righe di questo file (3461, 3680, 5355, 5665…) | 1 — `test_la_ricevuta_non_dice_entails_quando_boccia.py` | Embedded-store SDK client stamped with the CLI surface principal. | **FUNZIONA COME PROMESSO**, limitato |
| 5165 | `_lineage_exit` | 4 righe di questo file (5363, 5572, 5607, 5639…) | 🔴 **nessuno** | — | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 5171 | `_moat_cell` | 5 righe di questo file (3299, 3369, 3426, 5216…) | 🔴 **nessuno** | Il verdetto del moat in una colonna stretta, senza fingere uno zero. | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 5186 | `riga_di_recall` | 2 righe di questo file (1741, 1870…) | 2 — `test_la_cli_non_diceva_del_record_trattenuto.py` | Una riga di `verimem recall`: il fatto, quanto risponde, se e' verificato. | **FUNZIONA COME PROMESSO**, limitato |
| 5216 | `_moat_cella_corta` | 3 righe di questo file (3299, 3369, 3426…) | 🔴 **nessuno** | Il verdetto in una colonna di tabella. `--` quando non e' stato | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 5226 | `_epoch_di` | 1 righe di questo file (5361…) | 🔴 **nessuno** | «2026-03-15» o un epoch -> secondi. None se non dichiarato. | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 5252 | `_node_line` | 5 righe di questo file (5548, 5587, 5613, 5707…) | 🔴 **nessuno** | One compact line per chain node: id, time, status, moat, topic. | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 5265 | `riga_moat_non_verificato` | 1 righe di questo file (5455…) | 2 — `test_due_righe_della_stessa_ricevuta_si_contraddicevano.py` | Il testo di «not verified», col rimedio GIUSTO per lo stato del giudice. | **FUNZIONA COME PROMESSO**, limitato |
| 5754 | `_regroup_agent_runtime` | 1 righe di questo file (5773…) | 🔴 **nessuno** | — | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 5784 | `_audit_adj_log` | 2 righe di questo file (5869, 5956…) | 🔴 **nessuno** | The adjudications chain that sits next to a semantic.db (sibling | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 5792 | `_audit_public_key` | 1 righe di questo file (5944…) | 🔴 **nessuno** | Resolve the anchor VERIFICATION key from the environment only (never a | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 5800 | `_audit_episodes_db` | 2 righe di questo file (5870, 5966…) | 🔴 **nessuno** | Locate the episodes.db whose mutation chain the anchor should cover. | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 5820 | `_audit_episodic_chain_state` | 1 righe di questo file (5967…) | 🔴 **nessuno** | A ChainState for the episodic mutation chain, or ``None`` when there is | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 5938 | `_audit_verify_anchor` | 1 righe di questo file (5920…) | 🔴 **nessuno** | Verify every covered chain against a signed anchor receipt; exit 1 on | **NON MISURATO** — esercitato dai chiamanti, mai da solo |
| 5982 | `main` | 9 righe di questo file (352, 2258, 2519, 2520…) | 115 — `conftest.py` | Console-script entry (`engram` / `hippo`): force UTF-8 stdio, then run | **FUNZIONA COME PROMESSO**, limitato |

## 3. Zero MAI CHIAMATA — e il candidato che non lo era

Il righello ha segnalato **una** definizione senza nessun chiamante dentro il
file: `__init__` a `cli.py:4558`. Non è codice morto, ed è la quarta trappola
di nuovo in piedi:

| controllo | esito |
|---|---|
| che cos'è | il costruttore di `_AgentShim`, la classe locale definita a 4557 **dentro** una funzione |
| chi la istanzia | `cli.py:4561`, `agent = _AgentShim(sm)`, tre righe sotto |
| nome nudo in tutto il repo | **943 righe** — `__init__` è il nome più generico che esista, e da solo non prova niente |
| il gemello usato | non applicabile: è un costruttore, lo chiama l'istanziazione |

⇒ **Zero MAI CHIAMATA su 131 definizioni.** Non perché il file sia perfetto, ma
perché in un CLI Typer il codice morto non ha la forma «nessuno la chiama»: ha
la forma «nessuno la **invoca**», ed è il numero di ws7 — 22 comandi su 88.

📌 Nei miei 21 file la stessa domanda aveva dato **un** morto vero (`by_task`,
`memory.py:1573`). Qui zero: il perimetro cambia il significato della domanda,
non solo la risposta.

## 4. La classe — `_AgentShim` (4557)

| riga | classe | metodi | contratto | test che la nominano | verdetto |
|---|---|---|---|---|---|
| 4557 | `_AgentShim` | 1 | adattatore locale: espone `.semantic` allo store perché il gate del write path si aspetta un oggetto-agente, non uno store nudo | 🔴 **nessuno nomina il nome** | **NON MISURATA** direttamente — esercitata da ogni `facts add` che passa dal gate |

⚠️ È una classe **dentro una funzione**: nasce e muore in `facts add`. Il
righello del lead la conta come superficie (giustamente: è una definizione), ma
non è raggiungibile da nessuna porta se non quella.

## 5. Che cosa NON dice questa mappa

Tre limiti dichiarati, perché chi legge non li scopra da solo:

1. **«Invocato da un test» non è «coperto».** Il righello di ws7 vede la lista
   di argomenti, non gli assert che seguono. Un comando invocato può avere un
   test che ne verifica solo l'exit code.
2. **Le opzioni non sono qui.** Un comando invocato con `--json` non dice niente
   di `--verbose`. Il gradino delle opzioni è già aperto da ws7 come **T31**
   (`verimem health --tools`), e resta suo.
3. **`tui.py` e `doctor.py` non sono in questo file.** Stanno nella mappa di ws7
   (`CLI-claims.md`, sezioni 5 e 6), insieme al reperto che una delle otto
   azioni della TUI spegne il sandbox con un clic e senza conferma.

## 6. Le esecuzioni — che cosa ho fatto girare davvero

Ogni verdetto verde di questo file poggia su una di queste righe. Nessuna è
citata da un'altra mappa: le ho lanciate qui, oggi, in CI-mode
(`HIPPO_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`).

| # | comando | esito |
|---|---|---|
| 1 | `python docs/stato-reale/banchi/ws7-quali-comandi-della-cli-nessun-test-invoca.py` | `comandi dichiarati: 88` · `invocazioni viste nei test: 4956` · `controllo positivo (warmup): visto` · `comandi che NESSUN test invoca: 22` — EXIT=0 |
| 2 | `pytest -q tests/test_cli.py` | `30 passed, 1 warning in 22.81s` EXIT=0 |
| 3 | `pytest -q tests/test_cli_facts.py` | `15 passed, 1 warning in 14.33s` EXIT=0 |
| 4 | `pytest -q tests/test_cli_consolidate.py tests/test_cli_airgap.py` | `11 passed, 1 warning in 15.61s` EXIT=0 |
| 5 | `python scratchpad/chi_invoca_quale.py` (l'attribuzione, sotto) | `88 / 66 / 22` · `controfirma ws7: solo-mio 0, solo-suo 0` EXIT=0 |

### Come ho ottenuto la colonna «test che lo invoca»

Il banco di ws7 risponde **quanti** comandi non sono invocati, e per farlo tiene
un insieme di tuple senza la provenienza. La colonna che il formato della mappa
chiede — *test che la esercita (file)* — vuole il **chi**. Ho importato il suo
modulo e riusato **le sue regex**, tenendo in più il file da cui viene ogni
invocazione: non è una seconda misura, è la sua con l'attribuzione.

🔑 **E l'ho controfirmata in modo che potesse smentirmi**: l'insieme dei comandi
che il mio passaggio non vede deve coincidere con i 22 che stampa il suo.

```
comandi dichiarati            : 88
comandi con almeno un test    : 66
comandi che NESSUN test invoca: 22
controfirma ws7: solo-mio 0, solo-suo 0
  ✅ stessa lista: l'attribuzione non ha cambiato la misura
```

Se avessi trovato anche un solo comando in più o in meno, il numero non sarebbe
uscito da qui: una controfirma che non può divergere non controfirma niente.

### 🔴 Due volte il mio righello ha sbagliato, e il controllo l'ha detto

Prima di questi numeri ne avevo prodotti due falsi, e li scrivo perché il modo
in cui sono caduti è più utile del risultato:

1. **69 comandi invece di 88.** I 19 comandi dichiarati con `@app.command()`
   **senza nome** (Typer usa il nome della funzione) finivano nel ramo del
   callback globale. Sette dei ventidue orfani di ws7 restavano spaiati — e
   fra loro `health`, `metrics`, `reset`, `tui`, `wake`, che sono cinque delle
   righe più visibili della sua mappa.
2. **23 orfani invece di 22.** Il mio parser raccoglieva la stringa `22`
   dell'intestazione come se fosse un nome di comando, perché filtravo la cifra
   sulla riga **non** strippata.

Entrambi trovati dalla stessa guardia: *ogni orfano di ws7 deve appaiarsi a una
funzione di questo file, altrimenti il numero non si stampa*. È la stessa forma
che a ws7 aveva fatto scendere il suo primo 32 a 22 — e stavolta ha lavorato
contro di me, che è l'unico modo in cui un controllo serve a qualcosa.
