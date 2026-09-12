# Inventario delle funzioni — `verimem/cli.py`

> ws7 «Product Owner». Accompagna [CLI-claims.md](CLI-claims.md), che giudica la
> superficie che l'utente tocca (comandi, opzioni, diagnosi). Questo file è
> un **inventario**, non un giudizio: elenca ogni funzione e dice se un test
> la nomina.

⚠️ **Criterio di conteggio, dichiarato**: una riga che combacia con
`^\s*def ` o `^\s*async def `, a qualunque indentazione — le funzioni
annidate ci sono, le lambda no.

⚠️ **La colonna «prova»**: `NON MISURATO oggi (macchina in uso)` — Aurelio,
09/09 12:37, *«sto pure giocando non mi saturate tutto»*. Nessun pytest,
nessuna CLI, nessun modello: questo file è scritto **leggendo**.

⚠️ **La colonna «nei test» è un indizio, non una copertura**: conta le
occorrenze del nome nei file `tests/`. Per un nome raro è informativa; per
uno comune (`main`, `run`, `add`) non discrimina, e lì la riga lo dice
invece di esibire un numero che sembrerebbe una misura.

**130 funzioni.**

| n | funzione | riga | che cos'è | nei test | prova |
|---|---|---|---|---|---|
| 1 | `_radice` | 42 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 2 | `_principale` | 129 | helper privato | **14** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 3 | `flow_tail_cmd` | 161 | comando Typer `tail` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 4 | `lab_live_cmd` | 173 | comando Typer `live` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 5 | `code` | 207 | comando Typer `(dal nome della funzione)` | **221** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 6 | `run` | 225 | comando Typer `(dal nome della funzione)` | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |
| 7 | `_val` | 231 | funzione annidata | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 8 | `status` | 242 | comando Typer `(dal nome della funzione)` | **2136** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 9 | `health` | 342 | comando Typer `(dal nome della funzione)` | **62** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 10 | `backup_all` | 358 | comando Typer `backup-all` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 11 | `_totale_di_default` | 426 | helper privato | **7** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 12 | `_giorni_di_undo` | 452 | helper privato | **6** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 13 | `_quanto_scarica` | 473 | helper privato | **5** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 14 | `warmup` | 486 | comando Typer `(dal nome della funzione)` | **172** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 15 | `tiers` | 673 | comando Typer `help` | **17** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 16 | `doctor` | 716 | comando Typer `(dal nome della funzione)` | **233** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 17 | `airgap` | 741 | comando Typer `(dal nome della funzione)` | **17** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 18 | `index` | 802 | comando Typer `help` | **192** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 19 | `search_docs` | 840 | comando Typer `search-docs` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 20 | `_gateway_data_dir` | 966 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 21 | `gateway_serve` | 972 | comando Typer `serve` | **4** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 22 | `console_cmd` | 1021 | comando Typer `console` | **1** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 23 | `gateway_keys_create` | 1058 | comando Typer `create` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 24 | `gateway_keys_list` | 1081 | comando Typer `list` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 25 | `gateway_backup_cmd` | 1097 | comando Typer `backup` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 26 | `gateway_restore_cmd` | 1117 | comando Typer `restore` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 27 | `gateway_keys_revoke` | 1134 | comando Typer `revoke` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 28 | `_import_llm` | 1146 | helper privato | **1** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 29 | `import_cmd` | 1153 | comando Typer `import` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 30 | `_agente_per_l3` | 1217 | helper privato | **3** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 31 | `_diagnosi_mcp_2x` | 1227 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 32 | `_open_memory` | 1249 | helper privato | **23** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 33 | `_dichiara_store` | 1265 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 34 | `remember_cmd` | 1308 | comando Typer `remember` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 35 | `_avviso_scaduti` | 1422 | helper privato | **1** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 36 | `_avviso_al_passato` | 1455 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 37 | `_avviso_freschezza` | 1483 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 38 | `_avviso_pavimento` | 1520 | helper privato | **6** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 39 | `recall_cmd` | 1574 | comando Typer `recall` | **4** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 40 | `ask_cmd` | 1777 | comando Typer `ask` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 41 | `correct_cmd` | 1874 | comando Typer `correct` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 42 | `ignorance_cmd` | 1962 | comando Typer `ignorance` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 43 | `telemetry_cmd` | 2030 | comando Typer `telemetry` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 44 | `_ledger_window` | 2116 | helper privato | **4** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 45 | `trust_stats_cmd` | 2154 | comando Typer `stats` | **1** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 46 | `_verdetto_del_gate` | 2240 | helper privato | **3** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 47 | `trust` | 2252 | comando Typer `(dal nome della funzione)` | **244** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 48 | `sleep_now` | 2417 | comando Typer `sleep-now` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 49 | `wake` | 2444 | comando Typer `(dal nome della funzione)` | **413** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 50 | `sleep` | 2473 | comando Typer `(dal nome della funzione)` | **261** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 51 | `benchmark` | 2488 | comando Typer `(dal nome della funzione)` | **232** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 52 | `tui` | 2517 | comando Typer `(dal nome della funzione)` | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |
| 53 | `mcp` | 2524 | comando Typer `(dal nome della funzione)` | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |
| 54 | `chat` | 2574 | comando Typer `(dal nome della funzione)` | **71** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 55 | `reset` | 2641 | comando Typer `(dal nome della funzione)` | **45** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 56 | `metrics` | 2652 | comando Typer `(dal nome della funzione)` | **36** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 57 | `dashboard` | 2659 | comando Typer `(dal nome della funzione)` | **133** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 58 | `providers_list` | 2729 | comando Typer `list` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 59 | `providers_scan` | 2755 | comando Typer `scan` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 60 | `providers_models` | 2788 | comando Typer `models` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 61 | `providers_active` | 2810 | comando Typer `active` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 62 | `providers_check` | 2827 | comando Typer `check` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 63 | `skills_list` | 2921 | comando Typer `list` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 64 | `introspect` | 2939 | comando Typer `introspect` | **5** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 65 | `skills_dedup` | 3003 | comando Typer `dedup` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 66 | `skills_show` | 3038 | comando Typer `show` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 67 | `episodes_list` | 3060 | comando Typer `list` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 68 | `episodes_show` | 3075 | comando Typer `show` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 69 | `_progress_printer` | 3092 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 70 | `_print_report` | 3099 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 71 | `_facts_data_dir` | 3127 | helper privato | **6** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 72 | `_facts_sm` | 3151 | helper privato | **10** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 73 | `_fact_id_resolve` | 3183 | helper privato | **1** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 74 | `facts_list` | 3203 | comando Typer `list` | **1** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 75 | `facts_recall` | 3307 | comando Typer `recall` | **5** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 76 | `facts_search` | 3376 | comando Typer `search` | **7** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 77 | `facts_label` | 3433 | comando Typer `label` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 78 | `facts_get` | 3482 | comando Typer `get` | **1** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 79 | `facts_forget` | 3539 | comando Typer `forget` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 80 | `facts_undo` | 3720 | comando Typer `undo` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 81 | `facts_undo_list` | 3779 | comando Typer `undo-list` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 82 | `facts_quarantine_log` | 3807 | comando Typer `quarantine-log` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 83 | `facts_retirement_log` | 3857 | comando Typer `retirement-log` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 84 | `facts_backup` | 3994 | comando Typer `backup` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 85 | `facts_restore` | 4039 | comando Typer `restore` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 86 | `facts_safety` | 4078 | comando Typer `safety` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 87 | `facts_capability` | 4175 | comando Typer `capability` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 88 | `facts_stats` | 4241 | comando Typer `stats` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 89 | `facts_anti_confab_scan` | 4273 | comando Typer `anti-confab-scan` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 90 | `facts_anti_confab_apply` | 4300 | comando Typer `anti-confab-apply` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 91 | `facts_add` | 4367 | comando Typer `add` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 92 | `__init__` | 4558 | funzione annidata | **454** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 93 | `facts_backfill` | 4793 | comando Typer `backfill` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 94 | `facts_archive_narration` | 4817 | comando Typer `archive-narration` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 95 | `facts_cleanup_episode_telemetry` | 4856 | comando Typer `cleanup-episode-telemetry` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 96 | `facts_requalify_quarantined` | 4885 | comando Typer `requalify-quarantined` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 97 | `_consolidate_em` | 4952 | helper privato | **1** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 98 | `consolidate_dry_run` | 4973 | comando Typer `dry-run` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 99 | `consolidate_apply` | 5023 | comando Typer `apply` | **1** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 100 | `consolidate_status` | 5057 | comando Typer `status` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 101 | `_force_utf8_stdio` | 5095 | helper privato | **2** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 102 | `agent_guide_cmd` | 5112 | comando Typer `agent-guide` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 103 | `_continuity_guard` | 5138 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 104 | `_continuity_memory` | 5153 | helper privato | **2** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 105 | `_lineage_exit` | 5165 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 106 | `_moat_cell` | 5171 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 107 | `riga_di_recall` | 5186 | funzione pubblica del modulo | **10** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 108 | `_moat_cella_corta` | 5216 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 109 | `_epoch_di` | 5226 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 110 | `_node_line` | 5252 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 111 | `riga_moat_non_verificato` | 5265 | funzione pubblica del modulo | **9** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 112 | `save_cmd` | 5308 | comando Typer `save` | **5** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 113 | `tip_cmd` | 5492 | comando Typer `tip` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 114 | `recent_cmd` | 5534 | comando Typer `recent` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 115 | `chain_show_cmd` | 5552 | comando Typer `show` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 116 | `chain_orphans_cmd` | 5596 | comando Typer `orphans` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 117 | `chain_relink_cmd` | 5620 | comando Typer `relink` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 118 | `handoff_prepare_cmd` | 5645 | comando Typer `prepare` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 119 | `handoff_show_cmd` | 5676 | comando Typer `show` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 120 | `handoff_log_cmd` | 5694 | comando Typer `log` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 121 | `digest_cmd` | 5711 | comando Typer `digest` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 122 | `_regroup_agent_runtime` | 5754 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 123 | `_audit_adj_log` | 5784 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 124 | `_audit_public_key` | 5792 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 125 | `_audit_episodes_db` | 5800 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 126 | `_audit_episodic_chain_state` | 5820 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 127 | `audit_anchor_cmd` | 5835 | comando Typer `anchor` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 128 | `audit_verify_cmd` | 5894 | comando Typer `verify` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 129 | `_audit_verify_anchor` | 5938 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 130 | `main` | 5982 | funzione pubblica del modulo | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |

**Nomi che non compaiono in nessun file di `tests/`: 79 su 130.**
Non è una misura di copertura — un helper privato può essere esercitato
attraverso il comando che lo chiama senza che il suo nome compaia mai. È
l'indizio più economico disponibile senza eseguire niente.
