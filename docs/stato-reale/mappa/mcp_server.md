# Mappa di `verimem/mcp_server.py` — ws2 «Porte» (Porte)

**67 righe su 67 elencate · 62 con una prova eseguita.**
Il numero non lo scrivo io: e' l'output di `scripts/mappa_completa.py --owner ws2`,
incollato nel contatore sul canale.

Il denominatore e' **67**, non 66: il righello conta anche le CLASSI, e in
questo file ce n'e' una (`_TokenBucket`). Le mie 66 funzioni + 1 classe = 67,
che e' esattamente il numero che il lead ha annunciato per ws2.

## Due cose sul righello, prima dei numeri

**1. Lanciato come dice l'istruzione, dice che va tutto bene.** L'istruzione
delle 20:48 e' `git show ... > /tmp/mappa_completa.py` e poi lanciarlo. Ma lo
script deriva la radice del repo dalla PROPRIA posizione
(`RADICE = dirname(dirname(abspath(__file__)))`), quindi da fuori il repo
guarda un albero vuoto e stampa:

```
== FUNZIONI E CLASSI: nel codice contro nella mappa ==
  TUTTE  mappate     0 /     0   mancanti     0
```

`mancanti 0`. Poi si schianta su `README.md` — ed e' l'unica ragione per cui
chi lo lancia se ne accorge: se accanto allo script ci fosse un `README.md`
qualsiasi, uscirebbe un rapporto pulito che dice che non manca niente.
Va tenuto **dentro il worktree**, in `scripts/`. Verificato: da `scripts/` dice
`ws2 mappate 0 / 67 mancanti 67`, EXIT=1.

**2. La colonna «chiamata da» viene da `git grep`, e su un nome comune e'
rumore.** `_TokenBucket.__init__` risulta «chiamata da `verimem/_compat.py:27`»:
e' un `__init__` qualsiasi. La docstring del generatore lo dice
(«grep serve a trovare, non a contare») e io ho marcato le righe a rischio
con ⚠️ invece di lasciarle sembrare confermate. Sono 10.

## Su cosa poggia un «FUNZIONA COME PROMESSO» in questa tabella

Su uno di due livelli di evidenza, e la colonna `prova` dice sempre quale:

- **(a) test dedicato**: il file passa (comando ed esito nella riga, EXIT dove
  l'ho catturato) E ho letto che quel test tocca davvero la funzione — non che
  il suo nome compare nel file.
- **(b) coverage**: righe del CORPO eseguite dentro file di test tutti verdi.
  Dice che la funzione e' **esercitata** e non esplode; **non** dice che
  qualcuno abbia asserito il suo contratto. Le righe (b) portano il prefisso
  «coverage su 3 file verdi».

**Nessuno dei due e' una falsificazione: non ho rotto nessuna funzione per
vedere il test diventare rosso.** Quindi il «sensore scollegato» qui e' escluso
dalla lettura e dalla misura, non dal metodo. Lo scrivo perche' con quaranta
righe verdi la differenza fra «provato» e «falsificato» sparisce se non la si
nomina, e chi legge deve poter declassare da solo qualunque riga (b).

**Nota 11 — il punto 2 non e' pignoleria: mi ha gia' corretto due righe.**
La colonna «test che la esercita» viene da `git grep` del nome nei file di
test, e due volte su quattordici il nome c'era ma dentro un **docstring**:
`_pavimento_di` in `test_avviso_mcp_stessa_soglia_dell_sdk.py` (una occorrenza,
riga 7, prosa) e `_apply_tool_namespace` in
`test_le_descrizioni_parlano_lo_stesso_nome_dei_tool.py` (due occorrenze, righe
4 e 82, entrambe prosa). Fermandomi al conteggio avrei scritto due verdi
appoggiati a niente. Il pavimento e' provato da un ALTRO file
(`test_il_pavimento_si_trova_da_ogni_forma_di_agente.py`, che lo chiama cinque
volte compresi i casi negativi `object()` e `None`); il namespace e' provato
dalla PORTA (`asyncio.run(ms.list_tools())` con la variabile accesa), che e'
meglio della funzione privata.

## Le 67 righe

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/mcp_server.py:94` `_ag` | funzione: Process-wide agent, built exactly once, SENZA tenere il lock nel build. | `verimem/dashboard.py:42`; `verimem/dashboard.py:48`; `verimem/dashboard.py:56` (+15) | `tests/conftest.py`; `tests/test_adjudication_receipt.py`; `tests/test_all_write_channels_judge_a_source.py` (+115) | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_il_build_dell_agent_non_tiene_il_lock.py` esito: 4 passed (07/09, fatto `t1b-red-green-del-lock`) |
| 2 | `verimem/mcp_server.py:169` `_remote_cls` | funzione: (nessun docstring) | `verimem/client.py:305`; `verimem/mcp_server.py:190` | `tests/test_mcp_thin.py`; `tests/test_remote_memory.py` | README.md:612 (`hippo_facts_search` e le altre passano dal server condiviso) | FUNZIONA COME PROMESSO | sonda mia dalla PORTA sotto coverage (`server.request_handlers[CallToolRequest]`, store in tempdir, `env -u HIPPO_ENCODE_DELEGATE_ONLY`): `VERIMEM_SERVER_URL=http://127.0.0.1:1` (nessuno ascolta) e poi `hippo_facts_search`: 2 righe del corpo, e la porta ha reso una risposta locale normale invece di piantarsi — il **fail-soft del commento a 7853 e' misurato**, non solo scritto |
| 3 | `verimem/mcp_server.py:174` `_reset_remote_cache` | funzione: (nessun docstring) | nessuno trovato | `tests/test_mcp_thin.py` | README.md:612 (`hippo_facts_search` e le altre passano dal server condiviso) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_mcp_thin.py` esito: 14 passed, EXIT=0 (2 chiamate esplicite) |
| 4 | `verimem/mcp_server.py:181` `_remote` | funzione: (nessun docstring) | `verimem/mcp_server.py:7865`; `verimem/mcp_server.py:7912`; `verimem/mcp_server.py:7939` | `tests/test_mcp_thin.py`; `tests/test_remote_memory.py` | README.md:612 (`hippo_facts_search` e le altre passano dal server condiviso) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_mcp_thin.py` esito: 14 passed, EXIT=0 (il test la chiama 2 volte come `ms._remote(...)`) |
| 5 | `verimem/mcp_server.py:207` `_auth_closed` | funzione: Fail-closed receipt when the configured server rejected our key. | `verimem/mcp_server.py:7867`; `verimem/mcp_server.py:7883`; `verimem/mcp_server.py:7914` (+1) | nessuno | README.md:578 (il server condiviso; il fail-closed e' la sua promessa) | FUNZIONA COME PROMESSO | coverage, secondo run su 11 file verdi (96 passed in 114s, EXIT=0: mcp_thin, remote_memory, mcp_capability_gate, export_import_test_audit, describe_provider_merge, justified_audit_mcp, record_episode_with_facts, fact_forget_scope_r3, un_analogia_che_non_puo_esistere, skills_top_used, security/sandbox_cwd_jail_wiring): 2 righe del corpo |
| 6 | `verimem/mcp_server.py:216` `_remote_row` | funzione: Shape a shared-server search hit like a local recall/search item so a | `verimem/mcp_server.py:7929` | `tests/test_mcp_reads_expose_moat_verdict.py` | README.md:612 (`hippo_facts_search` e le altre passano dal server condiviso) | FUNZIONA COME PROMESSO | coverage, secondo run su 11 file verdi (96 passed in 114s, EXIT=0: mcp_thin, remote_memory, mcp_capability_gate, export_import_test_audit, describe_provider_merge, justified_audit_mcp, record_episode_with_facts, fact_forget_scope_r3, un_analogia_che_non_puo_esistere, skills_top_used, security/sandbox_cwd_jail_wiring): 8 righe del corpo. ⚠️ e' una TRADUZIONE fra la forma del server condiviso e quella locale: il punto dove una porta puo' dire una cosa diversa dall'altra senza che nessuno lo veda |
| 7 | `verimem/mcp_server.py:270` `_ok` | funzione: (nessun docstring) | `verimem/mcp_server.py:7881`; `verimem/mcp_server.py:7928`; `verimem/mcp_server.py:8023` (+294) | `tests/test_mcp_server_security.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 1 riga del corpo (ne ha 2). Nessun test la nomina — 1.663 file esaminati con l'AST — ed e' esercitata da ogni chiamata riuscita: e' il caso che solo coverage vede (nota 14) |
| 8 | `verimem/mcp_server.py:274` `_conta_sostituiti` | funzione: Quanti fatti sono stati RIMPIAZZATI da una scrittura successiva. | `verimem/mcp_server.py:8735`; `verimem/mcp_server.py:8943` | nessuno | README.md:235 (`hippo_facts_recall` dichiara il ranking) | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 4 righe del corpo. Nessun test la nomina |
| 9 | `verimem/mcp_server.py:296` `_pavimento_di` | funzione: Il pavimento calibrato, da QUALUNQUE forma di oggetto la casa passi. | `verimem/mcp_server.py:416` | `tests/test_avviso_mcp_stessa_soglia_dell_sdk.py`; `tests/test_il_pavimento_si_trova_da_ogni_forma_di_agente.py` | README.md:235 (`hippo_facts_recall` dichiara il ranking) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_il_pavimento_si_trova_da_ogni_forma_di_agente.py` esito: 5 passed, EXIT=0 (58,31s). ⚠️ NON il file che la colonna «test» suggeriva per primo: in `test_avviso_mcp_stessa_soglia_dell_sdk.py` il nome compare UNA volta e dentro un docstring (nota 11) |
| 10 | `verimem/mcp_server.py:334` `_avvisi_di_lettura` | funzione: Gli avvisi che CLI e SDK danno gia', portati alla porta dell'AGENTE. | `verimem/mcp_server.py:12895`; `verimem/mcp_server.py:14368` | `tests/test_avviso_mcp_stessa_soglia_dell_sdk.py`; `tests/test_il_pavimento_si_trova_da_ogni_forma_di_agente.py`; `tests/test_l_avviso_non_usciva_dalla_porta_dell_agente.py` (+2) | README.md:235 (`hippo_facts_recall` dichiara il ranking) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_il_pavimento_si_trova_da_ogni_forma_di_agente.py` esito: 5 passed, EXIT=0 (il file la nomina 8 volte) |
| 11 | `verimem/mcp_server.py:532` `_err` | funzione: (nessun docstring) | `verimem/auto_dream_worker.py:464`; `verimem/mcp_server.py:210`; `verimem/mcp_server.py:573` (+151) | `tests/test_il_messaggio_dice_quale_chiave_ha_buttato.py`; `tests/test_mcp_server_security.py`; `tests/test_quando_un_tool_mcp_esplode_dice_QUALE.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_il_messaggio_dice_quale_chiave_ha_buttato.py` esito: 9 passed, EXIT=0 — e il test guida la PORTA (`asyncio.run(m.call_tool(nome, argomenti))`), non la funzione privata |
| 12 | `verimem/mcp_server.py:546` `_err_proposizione_vuota` | funzione: «empty proposition» diceva cosa MANCA, non cosa era stato BUTTATO. | `verimem/mcp_server.py:7873`; `verimem/mcp_server.py:13275` | `tests/test_il_messaggio_dice_quale_chiave_ha_buttato.py` | README.md:353 (`hippo_remember` sulla porta MCP) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_il_messaggio_dice_quale_chiave_ha_buttato.py` esito: 9 passed, EXIT=0. Raggiunta dalla porta con `proposition` vuota (righe 71 e 120); il test presidia anche che nel SORGENTE non restino messaggi cablati (`src.count('_err("empty proposition")')`) |
| 13 | `verimem/mcp_server.py:576` `_iso_day` | funzione: Epoch seconds -> 'YYYY-MM-DD' (UTC) for recall payloads. A readable date lets | `verimem/mcp_server.py:234`; `verimem/mcp_server.py:8270`; `verimem/mcp_server.py:8644` (+2) | `tests/test_mcp_recall_when_date.py` | README.md:235 (`hippo_facts_recall` dichiara il ranking) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_mcp_recall_when_date.py` esito: 4 passed |
| 14 | `verimem/mcp_server.py:593` `_apply_live_filter` | funzione: Drop superseded/orphaned fact_ids from BOTH the legacy ``facts`` union | `verimem/mcp_server.py:13039` | `tests/test_ppr_ranked_live_filter.py` | README.md:235 (`hippo_facts_recall` dichiara il ranking) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_ppr_ranked_live_filter.py` esito: 4 passed |
| 15 | `verimem/mcp_server.py:613` `_drop_none_args` | funzione: Drop keys whose value is ``None`` (audit#2 2026-06-08, A10). | `verimem/mcp_server.py:7841` | `tests/test_mcp_null_arg_coercion.py`; `tests/test_mcp_null_arg_e2e.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_mcp_null_arg_coercion.py` esito: 3 passed (il file la nomina 7 volte) |
| 16 | `verimem/mcp_server.py:630` `_sandbox_replay_audit` | funzione: Task #48 — append one replayable JSONL record for a sandbox_exec | `verimem/mcp_server.py:8017`; `verimem/mcp_server.py:8060` | nessuno | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage, secondo run su 11 file verdi (96 passed in 114s, EXIT=0: mcp_thin, remote_memory, mcp_capability_gate, export_import_test_audit, describe_provider_merge, justified_audit_mcp, record_episode_with_facts, fact_forget_scope_r3, un_analogia_che_non_puo_esistere, skills_top_used, security/sandbox_cwd_jail_wiring): 11 righe del corpo |
| 17 | `verimem/mcp_server.py:678` `_skill_from_dict` | funzione: Reconstruct a Skill from a dict. Lazy import keeps the MCP module | `verimem/mcp_server.py:8989` | `tests/test_mcp_export_import_test_audit.py` | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage, terzo run su 6 file verdi (29 passed in 28s, EXIT=0: episode_batch_screen, mcp_lineage_explain_top, hippo_reason_non_esplode_sulle_skill, skill_import_sanitize_r3, il_doppio_prometteva_piu_del_vero, i_canali_di_scrittura_sono_allineati): 2 righe del corpo, via `tests/test_skill_import_sanitize_r3.py`. ⚠️ `tests/test_mcp_export_import_test_audit.py` — il file che il nome suggeriva — passa (13 ok) senza toccarla (nota 18) |
| 18 | `verimem/mcp_server.py:685` `_forget_cross_scope_denied` | funzione: Audit R3 #2 (multi-tenant security): if the caller supplies a scope | `verimem/mcp_server.py:14763`; `verimem/mcp_server.py:14799`; `verimem/mcp_server.py:14822` | nessuno | README.md:752 (`hippo_forget_scope`, bulk by tenant) | FUNZIONA COME PROMESSO | coverage, secondo run su 11 file verdi (96 passed in 114s, EXIT=0: mcp_thin, remote_memory, mcp_capability_gate, export_import_test_audit, describe_provider_merge, justified_audit_mcp, record_episode_with_facts, fact_forget_scope_r3, un_analogia_che_non_puo_esistere, skills_top_used, security/sandbox_cwd_jail_wiring): 11 righe del corpo (via `tests/test_fact_forget_scope_r3.py`, 4 passed) |
| 19 | `verimem/mcp_server.py:717` `_provider_is_configured` | funzione: Check whether an LLM provider has its credentials available. | `verimem/mcp_server.py:15344` | `tests/test_mcp_describe_provider_merge.py` | README.md:353 (il server non carica il giudice in proprio) | FUNZIONA COME PROMESSO | sonda mia dalla PORTA sotto coverage (`server.request_handlers[CallToolRequest]`, store in tempdir, `env -u HIPPO_ENCODE_DELEGATE_ONLY`): `hippo_provider_switch` con `provider="ollama"` -> `{"error": "provider not configured: ollama (set the appropriate API key env var first)"}`, 3 righe del corpo. ⚠️ al primo tentativo avevo passato `provider="mock"`, che lo schema rifiuta PRIMA del codice: l'errore era mio, non del prodotto (nota 20) |
| 20 | `verimem/mcp_server.py:730` `_content_hash_id` | funzione: Deterministic 12-char hex id derived from (proposition, topic). | `verimem/mcp_server.py:808`; `verimem/mcp_server.py:823`; `verimem/mcp_server.py:9415` (+1) | `tests/test_hippo_remember_idempotent.py` | README.md:353 (`hippo_remember` sulla porta MCP) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_hippo_remember_idempotent.py` esito: 10 passed, EXIT=0 |
| 21 | `verimem/mcp_server.py:779` `_build_fact` | funzione: Build a Fact object with a CONTENT-DERIVED id (cycle #46b + #109). | `verimem/mcp_server.py:9415`; `verimem/mcp_server.py:9522`; `verimem/mcp_server.py:13309` (+3) | `tests/perf/e2e_cycle51_54_chain.py`; `tests/test_hippo_remember_idempotent.py`; `tests/test_mcp_record_episode_with_facts.py` (+5) | README.md:353 (`hippo_remember` sulla porta MCP) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_hippo_remember_idempotent.py` esito: 10 passed, EXIT=0 |
| 22 | `verimem/mcp_server.py:853` `_justified_contradicted_ids` | funzione: Seam for hippo_justified_audit's opt-in contradiction trigger (#4). Reuses the | `verimem/mcp_server.py:9767` | `tests/test_justified_audit_mcp.py` | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | sonda mia dalla PORTA sotto coverage (`server.request_handlers[CallToolRequest]`, store in tempdir, `env -u HIPPO_ENCODE_DELEGATE_ONLY`): due fatti in contraddizione sullo stesso topic e `hippo_justified_audit` con **`detect_contradictions=True`**: 7 righe del corpo. ⚠️ nella sonda precedente avevo scritto `check_contradictions`, che non esiste: il ramo (riga 9765) non partiva e la funzione sembrava morta (nota 20) |
| 23 | `verimem/mcp_server.py:868` `_build_episode` | funzione: Build an Episode object for hosted-mode record. Lazy import + | `verimem/mcp_server.py:9320`; `verimem/mcp_server.py:9386` | `tests/perf/e2e_cycle51_54_chain.py`; `tests/test_mcp_hosted_mode.py`; `tests/test_mcp_record_episode_with_facts.py` | README.md:353 (`hippo_remember` sulla porta MCP) | FUNZIONA COME PROMESSO | sonda mia dalla PORTA sotto coverage (`server.request_handlers[CallToolRequest]`, store in tempdir, `env -u HIPPO_ENCODE_DELEGATE_ONLY`): `hippo_record_episodes_batch` con due episodi -> `{"ok": true, "n_stored": 2, "n_skipped": 0}`, 2 righe del corpo. ⚠️ NON ci arriva `tests/test_mcp_record_episode_with_facts.py`, che pure passa (5 ok) — nota 18 |
| 24 | `verimem/mcp_server.py:892` `_is_hosted` | funzione: True when running embedded inside an LLM host (e.g. Claude Code) | `verimem/airgap.py:15`; `verimem/mcp_server.py:8074`; `verimem/mcp_server.py:8135` | nessuno | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 1 riga del corpo |
| 25 | `verimem/mcp_server.py:904` `_consolidate_light` | funzione: Dedup + promote/retire pass without any LLM call. | `verimem/mcp_server.py:9664`; `verimem/sleep.py:261` | `tests/test_mcp_hosted_mode.py`; `tests/test_sleep_cycle_light.py` | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 6 righe del corpo su 67 di funzione: entra e si ferma presto |
| 26 | `verimem/mcp_server.py:976` `_audit_log_path` | funzione: Append-only audit log. Honour HIPPO_MCP_AUDIT_LOG if set. | `verimem/audit_tail.py:50`; `verimem/mcp_server.py:1227`; `verimem/mcp_server.py:9110` (+2) | `tests/test_audit_summary_integration.py`; `tests/test_l_errore_nomina_il_tool_che_ho_chiamato.py`; `tests/test_mcp_export_import_test_audit.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `ls -la ~/.engram/mcp_audit.log` esito: 2.100.293 byte, scritto l'ultima volta oggi 19:43 → il percorso reso e' quello che il prodotto usa |
| 27 | `verimem/mcp_server.py:1016` `_rotate_audit_if_needed` | funzione: Rinomina path → path.1 quando supera _AUDIT_MAX_BYTES. Best-effort. | `verimem/mcp_server.py:1262` | `tests/test_audit_log_rotation.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_audit_log_rotation.py` esito: 7 passed, EXIT=0. Sulla mia macchina non e' mai scattata davvero (2,1 MB su un tetto di 5 MB, nessun `mcp_audit.log.1`): a farla scattare e' il test |
| 28 | `verimem/mcp_server.py:1055` `_bypass_dal_registro` | funzione: (nessun docstring) | `verimem/mcp_server.py:1061` | nessuno | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 2 righe del corpo. Gira all'import (`GATING_BYPASS_LIST` e' calcolata a livello di modulo) |
| 29 | `verimem/mcp_server.py:1064` `_audit_capability_call` | funzione: Capability-gate-specific audit row. Always emits (mandatory_log). | `verimem/mcp_server.py:1139`; `verimem/mcp_server.py:1171`; `verimem/mcp_server.py:1190` (+2) | `tests/test_lavviso_dice_quali_parametri.py`; `tests/test_mcp_capability_gate.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | coverage, secondo run su 11 file verdi (96 passed in 114s, EXIT=0: mcp_thin, remote_memory, mcp_capability_gate, export_import_test_audit, describe_provider_merge, justified_audit_mcp, record_episode_with_facts, fact_forget_scope_r3, un_analogia_che_non_puo_esistere, skills_top_used, security/sandbox_cwd_jail_wiring): 8 righe del corpo (via `tests/test_mcp_capability_gate.py`, 14 passed) — cioe' il cancello si prova ACCESO, e allora scrive la riga |
| 30 | `verimem/mcp_server.py:1102` `_capability_gate_mode` | funzione: Cycle 2026-05-27 round 15 FIX 6 — dev-friendly toggle. | `verimem/mcp_server.py:1134`; `verimem/mcp_server.py:1148` | nessuno | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `env | grep -i CAPABILITY` esito: nessuna variabile → il modo e' `off`, che e' quello che la docstring dichiara (default dev, 2026-05-27) |
| 31 | `verimem/mcp_server.py:1128` `_capability_gate` | funzione: Cycle 2026-05-27 round 15 P0.5b — runtime gate on tool capabilities. | `verimem/mcp_server.py:7961`; `verimem/mcp_server.py:7970` | `tests/test_lavviso_dice_quali_parametri.py`; `tests/test_mcp_capability_gate.py`; `tests/test_mcp_sandbox_exec.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `grep -c 'cap_allow\|cap_deny\|cap_bypass' ~/.engram/mcp_audit.log` esito: 5 su 15432 righe (0,03%), tutte con `[mode=enforce]`, l'ultima il 2026-07-09; controllo positivo `"outcome":"ok"` → 11604. Fa cio' che la SUA docstring dice; e' il commento a 7959-7969 che descrive il modo acceso come se fosse il normale (nota 9) |
| 32 | `verimem/mcp_server.py:1211` `_audit` | funzione: Append one structured JSONL record. Best-effort — never raises. | `verimem/airgap.py:208`; `verimem/gateway.py:886`; `verimem/gateway.py:888` (+457) | `tests/security/test_pentest_validation.py`; `tests/test_audit_log_rotation.py`; `tests/test_dashboard_bus_coverage.py` (+6) | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: parse JSON di ogni riga di `~/.engram/mcp_audit.log` esito: 15432 leggibili, 0 illeggibili, dal 2026-05-08 01:41 al 2026-09-08 19:43 |
| 33 | `verimem/mcp_server.py:1284` `_TokenBucket` | classe: Simple per-tool token-bucket rate limiter, in-memory. | `verimem/mcp_server.py:1313`; `verimem/mcp_server.py:1318`; `verimem/mcp_server.py:1321` (+1) | `tests/test_mcp_server_security.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_mcp_server_security.py` esito: 13 passed, EXIT=0 (1 chiamata via modulo) |
| 34 | `verimem/mcp_server.py:1291` `_TokenBucket.__init__` | funzione: (nessun docstring) | `verimem/_compat.py:27`; `verimem/client.py:355`; `verimem/document_index.py:255` (+11) ⚠️ nome comune: righe da confermare leggendo | `tests/perf/seed_data.py`; `tests/security/test_pentest_validation.py`; `tests/test_abstention_hybrid.py` (+266) | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 5 righe del corpo |
| 35 | `verimem/mcp_server.py:1298` `_TokenBucket.take` | funzione: (nessun docstring) | `verimem/active_probe.py:149`; `verimem/briefing.py:54`; `verimem/cli.py:2762` (+22) ⚠️ nome comune: righe da confermare leggendo | `tests/test_abstention_is_on_by_default.py`; `tests/test_band_escalation.py`; `tests/test_cli_facts_jsonl_null_confidence.py` (+17) | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 7 righe del corpo su 12: il ramo esaurito potrebbe non essere stato toccato |
| 36 | `verimem/mcp_server.py:1313` `_bucket_for` | funzione: (nessun docstring) | `verimem/mcp_server.py:1329` | nessuno | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 3 righe del corpo |
| 37 | `verimem/mcp_server.py:1325` `_get_bucket` | funzione: (nessun docstring) | `verimem/mcp_server.py:1343` | nessuno | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 6 righe del corpo |
| 38 | `verimem/mcp_server.py:1334` `_rate_limit` | funzione: Return True if call allowed; False if rate-limited. | `verimem/mcp_server.py:7952` | `tests/security/test_pentest_validation.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 2 righe del corpo. ⚠️ la lista dei tool limitati ne contiene DUE (`hippo_run_task`, `hippo_consolidate`, riga 1541): il perimetro e' dichiarato, non e' la porta |
| 39 | `verimem/mcp_server.py:1362` `_looks_shell_like` | funzione: Heuristic regex tripwire — NOT a security boundary. | `verimem/mcp_server.py:8089` | `tests/test_mcp_server_security.py`; `tests/test_nessun_banco_nuovo_ignora_l_esito_del_subprocess.py` | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | comando: `pytest tests/test_mcp_server_security.py` esito: 13 passed, EXIT=0 (6 chiamate). La docstring dichiara che e' un'euristica e NON un confine di sicurezza: il verdetto vale su quella promessa, non su una protezione |
| 40 | `verimem/mcp_server.py:1404` `_doc_path_allowed` | funzione: ``(allowed, reason)`` for indexing ``path`` into the document corpus. | `verimem/mcp_server.py:8586` | `tests/security/test_document_index_path_guard.py` | README.md:274 e 491 (`verimem_document_*`) | FUNZIONA COME PROMESSO | comando: `pytest tests/security/test_document_index_path_guard.py` esito: 12 passed, EXIT=0 (5 chiamate via modulo) |
| 41 | `verimem/mcp_server.py:1448` `_sandbox_policy` | funzione: Build the sandbox policy for the MCP shell surface. | `verimem/mcp_server.py:8036` | `tests/security/test_sandbox_cwd_jail_wiring.py` | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | comando: `pytest tests/security/test_sandbox_cwd_jail_wiring.py` esito: 4 passed, EXIT=0 (2 chiamate via modulo) |
| 42 | `verimem/mcp_server.py:1485` `_shell_perm_enabled` | funzione: True iff `perm_shell` (HIPPO_ENABLE_SHELL) is on. | `verimem/mcp_server.py:7991`; `verimem/mcp_server.py:8089` | `tests/security/test_sandbox_redirect_quoting.py`; `tests/test_sandbox_exec_shell_gate_h2.py` | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | comando: `pytest tests/security/test_sandbox_redirect_quoting.py` esito: 8 passed, EXIT=0 — il test lo IMPORTA da verimem e lo chiama |
| 43 | `verimem/mcp_server.py:1495` `_manual_validate` | funzione: Return error message string on failure, empty string on success. | `verimem/mcp_server.py:1548` | `tests/test_mcp_server.py`; `tests/test_mcp_server_security.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | MAI CHIAMATA | dal PRODOTTO, e ora e' MISURATO, non dedotto: coverage sui tre file che guidano la porta dice `1547 non eseguita` (`except ImportError`) e `1548 non eseguita` (`return _manual_validate(...)`) mentre `1543 ESEGUITA` (`jsonschema.validate(...)`). Le 20 righe del suo corpo che risultano eseguite vengono dalla chiamata DIRETTA di un test. `jsonschema>=4.0.0` e' dipendenza dichiarata (`pyproject.toml:57`), installata 4.26.0. E se girasse sarebbe piu' permissiva del titolare: `isinstance(True,int) -> True` mentre `jsonschema k=True -> RIFIUTATO: True is not of type 'integer'` (nota 10) |
| 44 | `verimem/mcp_server.py:1528` `_validate_input` | funzione: Run jsonschema if available, fall back to manual validator. | `verimem/mcp_server.py:623`; `verimem/mcp_server.py:7847` | `tests/security/test_pentest_validation.py`; `tests/test_mcp_arg_validation_autoderive.py`; `tests/test_mcp_server_security.py` (+1) | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_mcp_arg_validation_autoderive.py` esito: 5 passed, EXIT=0 |
| 45 | `verimem/mcp_server.py:1566` `_derive_lenient_schema` | funzione: Project a tool's inputSchema down to a LENIENT validator. | `verimem/mcp_server.py:1617` | `tests/test_mcp_arg_validation_autoderive.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_mcp_arg_validation_autoderive.py` esito: 5 passed, EXIT=0 |
| 46 | `verimem/mcp_server.py:1602` `_ensure_derived_schemas` | funzione: Populate ``_DERIVED_SCHEMAS`` once from the full tool registry. | `verimem/mcp_server.py:1557`; `verimem/mcp_server.py:7846` | `tests/test_mcp_arg_validation_autoderive.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_mcp_arg_validation_autoderive.py` esito: 5 passed, EXIT=0 |
| 47 | `verimem/mcp_server.py:1636` `_allowed_tool_prefixes` | funzione: Parse ENGRAM_MCP_TOOLS_PREFIX into a set of allowed name prefixes. | `verimem/mcp_server.py:7737` | `tests/test_mcp_tool_filter.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_mcp_tool_filter.py` esito: 16 passed |
| 48 | `verimem/mcp_server.py:1651` `_filter_tools` | funzione: Return only tools whose name starts with one of the given prefixes. | `verimem/mcp_server.py:7735` | `tests/test_mcp_tool_filter.py` | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_mcp_tool_filter.py` esito: 16 passed |
| 49 | `verimem/mcp_server.py:1687` `_list_tools_unfiltered` | funzione: Cycle 176: the full registry, unfiltered. | `verimem/mcp_server.py:1612`; `verimem/mcp_server.py:7732`; `verimem/mcp_server.py:7736` | `tests/test_i_canali_di_scrittura_sono_allineati.py`; `tests/test_l42_avvisa_falsamente_sugli_output_di_programma.py`; `tests/test_la_quarantena_dice_perche.py` (+6) | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | NON MISURATO | ⚠️ coverage dice 0 righe del CORPO eseguite, e si sbaglia: e' provato da due strade indipendenti nello stesso run (nota 16). Non conto un verde su un righello che ho appena visto sbagliare |
| 50 | `verimem/mcp_server.py:7728` `list_tools` | funzione: Public MCP handler: full registry filtered by ENGRAM_MCP_TOOLS_PREFIX. | `verimem/cli.py:2554`; `verimem/doctor.py:91`; `verimem/doctor.py:418` (+6) ⚠️ nome comune: righe da confermare leggendo | `tests/test_anche_il_canale_mcp_cancella_la_catena.py`; `tests/test_anti_confab_gate.py`; `tests/test_anti_confab_gate_mcp_provenance.py` (+24) | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_le_descrizioni_parlano_lo_stesso_nome_dei_tool.py` esito: 4 passed, EXIT=0 — e il test guida `ms.list_tools()` con `VERIMEM_TOOL_NAMESPACE=verimem`, cioe' la PORTA, non la funzione privata |
| 51 | `verimem/mcp_server.py:7741` `_apply_tool_namespace` | funzione: Rename Phase 1 (RENAME-PLAN.md): VERIMEM_TOOL_NAMESPACE=verimem (ENGRAM_TOOL_NAMESPACE alias) exposes the | `verimem/mcp_server.py:7735` | `tests/test_le_descrizioni_parlano_lo_stesso_nome_dei_tool.py`; `tests/test_mcp_tool_namespace_brand.py` | README.md:490 (`verimem_remember`/`verimem_facts_recall`: e' il rename che li espone) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_le_descrizioni_parlano_lo_stesso_nome_dei_tool.py` esito: 4 passed, EXIT=0. ⚠️ il nome compare nel test solo in due docstring: il test la esercita attraverso `list_tools()` (nota 11) |
| 52 | `verimem/mcp_server.py:7759` `_apply_tool_namespace._riferimento` | funzione: (nessun docstring) | `verimem/mcp_server.py:7777`; `verimem/mcp_server.py:7783` | nessuno | README.md:490 (come sopra) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_le_descrizioni_parlano_lo_stesso_nome_dei_tool.py` esito: 4 passed, EXIT=0 — il test verifica proprio i riferimenti dentro le descrizioni, che sono il lavoro di questa funzione |
| 53 | `verimem/mcp_server.py:7797` `call_tool` | funzione: Thin dispatch wrapper: watch the call for hangs (stack-dump on overrun via | `verimem/doctor.py:418`; `verimem/mcp_server.py:987`; `verimem/mcp_server.py:1039` (+5) ⚠️ nome comune: righe da confermare leggendo | `tests/test_adjudication_receipt.py`; `tests/test_anche_il_canale_mcp_cancella_la_catena.py`; `tests/test_audit_silent_failures.py` (+38) | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_il_messaggio_dice_quale_chiave_ha_buttato.py` esito: 9 passed, EXIT=0 — cinque chiamate a `m.call_tool(...)`, cioe' l'handler vero con dentro il guardiano degli hang |
| 54 | `verimem/mcp_server.py:7806` `_call_tool_impl` | funzione: (nessun docstring) | `verimem/mcp_server.py:107`; `verimem/mcp_server.py:997`; `verimem/mcp_server.py:7803` (+1) | `tests/test_il_build_dell_agent_non_tiene_il_lock.py`; `tests/test_il_preload_non_importa_su_un_thread.py`; `tests/test_il_quarto_consumatore_non_conosceva_il_degrado.py` (+9) | README.md:611 (`hippo_remember`/`hippo_facts_recall`, la spina del dispatch) | FUNZIONA COME PROMESSO | comando: `pytest tests/test_il_messaggio_dice_quale_chiave_ha_buttato.py` esito: 9 passed, EXIT=0 — attraversata da ogni `m.call_tool(...)` del test. ⚠️ 9 test toccano una funzione di 7783 righe: e' esercitata, non coperta |
| 55 | `verimem/mcp_server.py:9779` `_call_tool_impl._props` | funzione: (nessun docstring) | `verimem/mcp_server.py:9786`; `verimem/mcp_server.py:9787`; `verimem/mcp_server.py:9788` ⚠️ nome comune: righe da confermare leggendo | `tests/test_include_beliefs.py`; `tests/test_l3_subject_prefilter.py`; `tests/test_recall_cache_cross_conn_staleness.py` (+2) | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 3 righe del corpo |
| 56 | `verimem/mcp_server.py:12402` `_call_tool_impl._cos` | funzione: (nessun docstring) | `verimem/mcp_server.py:12426`; `verimem/memory.py:1987` | `tests/test_un_analogia_che_non_puo_esistere_lo_dice.py` | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | sonda mia dalla PORTA sotto coverage (`server.request_handlers[CallToolRequest]`, store in tempdir, `env -u HIPPO_ENCODE_DELEGATE_ONLY`): due skill importate con `hippo_skill_import` (`{"imported": 2, "errors": []}`) e poi `hippo_reason`: 10 righe del corpo. Nei due run di coverage precedenti risultava spenta perche' senza skill `analogues` e' vuoto e il coseno non viene mai chiamato — non era codice morto, era la sonda che non ci arrivava (nota 20) |
| 57 | `verimem/mcp_server.py:12456` `_call_tool_impl._encode_skill` | funzione: (nessun docstring) | `verimem/mcp_server.py:12464`; `verimem/mcp_server.py:12465` | nessuno | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage, secondo run su 11 file verdi (96 passed in 114s, EXIT=0: mcp_thin, remote_memory, mcp_capability_gate, export_import_test_audit, describe_provider_merge, justified_audit_mcp, record_episode_with_facts, fact_forget_scope_r3, un_analogia_che_non_puo_esistere, skills_top_used, security/sandbox_cwd_jail_wiring): 4 righe del corpo |
| 58 | `verimem/mcp_server.py:12463` `_call_tool_impl._cosine` | funzione: (nessun docstring) | `verimem/coherence_check.py:22`; `verimem/coherence_check.py:42`; `verimem/coherence_check.py:132` (+11) ⚠️ nome comune: righe da confermare leggendo | `tests/test_contradiction_year_range_false_negative.py`; `tests/test_il_vincitore_che_ne_ingoio_dodici.py`; `tests/test_lateral_inhibition.py` | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage, secondo run su 11 file verdi (96 passed in 114s, EXIT=0: mcp_thin, remote_memory, mcp_capability_gate, export_import_test_audit, describe_provider_merge, justified_audit_mcp, record_episode_with_facts, fact_forget_scope_r3, un_analogia_che_non_puo_esistere, skills_top_used, security/sandbox_cwd_jail_wiring): 7 righe del corpo. La gemella `_cos` (12402) resta NON MISURATO: stesso conto, altro ramo (nota 13) |
| 59 | `verimem/mcp_server.py:13597` `_call_tool_impl._default_coherence_hook` | funzione: (nessun docstring) | `verimem/mcp_server.py:13626` | nessuno | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 3 righe del corpo su 18 |
| 60 | `verimem/mcp_server.py:15525` `_call_tool_impl._key_fitness` | funzione: (nessun docstring) | `verimem/mcp_server.py:15535`; `verimem/mcp_server.py:15538` | nessuno | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 1 riga del corpo (ne ha 2). Le gemelle `_key_recency` e `_key_activity` restano NON MISURATO: stesso `def`, ordinamento diverso, e questi test non lo chiedono |
| 61 | `verimem/mcp_server.py:15528` `_call_tool_impl._key_recency` | funzione: (nessun docstring) | `verimem/mcp_server.py:15536` | nessuno | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage, terzo run su 6 file verdi (29 passed in 28s, EXIT=0: episode_batch_screen, mcp_lineage_explain_top, hippo_reason_non_esplode_sulle_skill, skill_import_sanitize_r3, il_doppio_prometteva_piu_del_vero, i_canali_di_scrittura_sono_allineati): 1 riga del corpo. ⚠️ NON dal file che il nome suggeriva: `tests/test_skills_top_used.py` passa (5 ok) senza toccarla (nota 18); ci arriva `tests/test_mcp_lineage_explain_top.py` |
| 62 | `verimem/mcp_server.py:15531` `_call_tool_impl._key_activity` | funzione: (nessun docstring) | `verimem/mcp_server.py:15537` | nessuno | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage, terzo run su 6 file verdi (29 passed in 28s, EXIT=0: episode_batch_screen, mcp_lineage_explain_top, hippo_reason_non_esplode_sulle_skill, skill_import_sanitize_r3, il_doppio_prometteva_piu_del_vero, i_canali_di_scrittura_sono_allineati): 1 riga del corpo, stessa storia di `_key_recency` |
| 63 | `verimem/mcp_server.py:15592` `list_resources` | funzione: (nessun docstring) | `verimem/doctor.py:418`; `verimem/mcp_server.py:15591` ⚠️ nome comune: righe da confermare leggendo | `tests/test_mcp_server.py` | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 5 righe del corpo. Espone due risorse statiche (`hippo://skills/list`, `hippo://episodes/recent`) piu' una per skill promossa, tetto 50. Nessuna per i FATTI (nota 15) |
| 64 | `verimem/mcp_server.py:15619` `_read_resource_body` | funzione: JSON body for a hippo:// resource URI; wrapped by read_resource() into | `verimem/mcp_server.py:15664` | nessuno | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 9 righe del corpo. Quattro forme di URI, tutte skill o episodi (nota 15) |
| 65 | `verimem/mcp_server.py:15659` `read_resource` | funzione: (nessun docstring) | `verimem/doctor.py:419`; `verimem/mcp_server.py:15620`; `verimem/mcp_server.py:15658` ⚠️ nome comune: righe da confermare leggendo | `tests/test_mcp_server.py` | nessuno: il README non promette questa strada | FUNZIONA COME PROMESSO | coverage su 3 file verdi (test_il_messaggio_dice_quale_chiave_ha_buttato, test_mcp_reads_expose_moat_verdict, test_mcp_server — 51 test, EXIT=0): 3 righe del corpo. Rende `ReadResourceContents` invece della stringa nuda, che l'SDK MCP deprecava |
| 66 | `verimem/mcp_server.py:15747` `_serve` | funzione: (nessun docstring) | `verimem/mcp_server.py:15844` ⚠️ nome comune: righe da confermare leggendo | `tests/test_mcp_e2e_smoke.py`; `tests/test_mcp_eager_preload.py`; `tests/test_un_fatto_scaduto_non_viene_servito.py` | nessuno: il README non promette questa strada | NON MISURATO | e non lo sara' da pytest: e' il ciclo `stdio_server()` del processo server. Lo prova un banco end-to-end che avvia il processo, non un test in-process |
| 67 | `verimem/mcp_server.py:15752` `main` | funzione: Entry point for `hippo mcp`. | `verimem/_hang_watchdog.py:18`; `verimem/_import_lock.py:7`; `verimem/_singleton_guard.py:34` (+95) ⚠️ nome comune: righe da confermare leggendo | `tests/conftest.py`; `tests/perf/bench.py`; `tests/perf/bench_briefing_v3_robustness.py` (+112) | README.md:353 (la delega al daemon condiviso «by construction») | NON MISURATO | come `_serve`: e' l'entry point di `hippo mcp`. ⚠️ ed e' il posto dove `os.environ.setdefault("HIPPO_ENCODE_DELEGATE_ONLY", "1")` viene impostata per ogni processo server, e dove sta il commento sulla cecita' del journal (nota 17) |
| 68 | `verimem/mcp_server.py:296` `_fatti_per_il_recupero` | funzione: I fatti che una porta di RECUPERO puo' servire, piu' quanti ne ha tolti. | `verimem/mcp_server.py:10156` (`hippo_prompt_skeleton`); `:10203` (`hippo_chain_facts`); `:10218` (`hippo_oracle_query`); `:10425` (`hippo_cross_agent_consensus`); `:10578` (`hippo_forward_chain`) | `tests/test_nessuna_porta_serve_un_fatto_che_il_moat_ha_fermato.py` | README.md:443 («stored but OUT of default recall — your agent will never repeat it as truth»); mcp_server instructions («kept OUT of default recall») | FUNZIONA COME PROMESSO | comando: `env -u HIPPO_ENCODE_DELEGATE_ONLY python -m pytest -q -p no:randomly tests/test_nessuna_porta_serve_un_fatto_che_il_moat_ha_fermato.py` esito: 9 passed EXIT=0 (10/09, commit `dccfb41e`); falsificato in albero separato contro `20257636`: 9 failed EXIT=1 (rieseguito da @ws1 indipendentemente) |
| 69 | `verimem/mcp_server.py:363` `_status_dei_membri` | funzione: Accanto a ogni `fact_ids` di un payload, lo status di quei fatti. | `verimem/mcp_server.py:10379` (`hippo_find_duplicate_facts`); `:12035` (`hippo_facts_find_duplicates`) | `tests/test_nessuna_porta_serve_un_fatto_che_il_moat_ha_fermato.py` | README.md:443 (la meta' «stored»: chi ripara deve VEDERE il quarantenato, non riceverlo filtrato) | FUNZIONA COME PROMESSO | stesso comando della riga 68: i due casi `..._dice_lo_status_dei_membri` passano. Copre DUE forme di payload — `fact_ids` (memory_compaction) e `fact_a`/`fact_b` (`find_duplicate_facts.py:55`): con una sola, il gemello restava rosso |
| 70 | `verimem/mcp_server.py:426` `_dichiara_nascosti` | funzione: Mette nel payload quanti fatti il filtro di fiducia ha tolto. | `verimem/mcp_server.py:10168`; `:10214`; `:10236`; `:10437`; `:10609` (le cinque porte di recupero) | `tests/test_nessuna_porta_serve_un_fatto_che_il_moat_ha_fermato.py` | nessun claim del README: e' il «non tacere» di R4, non una promessa pubblicata | FUNZIONA COME PROMESSO | il campo `hidden_low_trust` compare nel payload misurato: `{"consensus": [], "n_facts_scanned": 5, "hidden_low_trust": 2}` (10/09, dalla porta) |

---

# Note per riga — il ragionamento, e cosa ho eseguito

Le note sotto sono il lavoro delle 20:00-21:00: la Parte 1 (le dieci dietro un
claim del README) e la Parte 2 (le 24 della spina dorsale di una chiamata).
Restano qui perche' la tabella dice CHE COSA, e queste dicono PERCHE'.

## Nota 12 — tre righe che il conteggio dava per coperte e non lo erano

Dopo la nota 11 ho riapplicato il criterio stretto (il test **importa** il
simbolo, oppure lo chiama come `ms.<nome>(`) a tutte le righe che stavo per
marcare verdi. Tre non l'hanno passato, e restano NON MISURATO:

| simbolo | il file che la colonna «test» suggeriva | chiamate vere |
|---|---|---|
| `_remote_cls` | `tests/test_mcp_thin.py` | 0 |
| `_ok` | `tests/test_mcp_server_security.py` | 0 |
| `_rate_limit` | `tests/security/test_pentest_validation.py` | 0 (il file non lo importa) |

`_ok` e' la funzione che da' forma a **ogni** risposta riuscita del prodotto —
294 chiamanti nel solo `mcp_server.py` — e non ho trovato un test che la
eserciti nominandola. Sara' esercitata di rimbalzo da qualunque test che
chiami un tool riuscito; ma «di rimbalzo» non e' una riga di questa tabella,
e finche' non lo verifico resta NON MISURATO.

Le 13 righe che avevo gia' scritto verdi PRIMA di darmi questo criterio le ho
ricontrollate tutte e 13 con lo stesso metro: passano tutte. Lo dico perche'
un criterio nuovo si prova per primo su cio' che si e' gia' pubblicato.

## Nota 13 — lo stesso coseno scritto due volte, nella stessa funzione

Dentro `_call_tool_impl` vivono `_cos` (riga 12402) e la coppia
`_encode_skill` (12456) + `_cosine` (12463). Sono la stessa cosa:

- stessa stringa da codificare: `f"{s.name}\n{s.trigger}"`;
- stessa formula: `np.dot(va, vb) / (na * nb)`;
- stessa soglia di guardia: `if na < 1e-9 or nb < 1e-9: return 0.0`;
- **due cache diverse**: `_ec` per la prima, `_emb_cache` per la seconda.

61 righe di distanza. Non e' un difetto di comportamento — letti, i due rami
fanno lo stesso conto — ed e' per questo che lo scrivo: e' la **forma** che in
questo stesso file ha gia' prodotto due incidenti pagati, e li documenta il
codice stesso. `_bypass_dal_registro` (1055) esiste perche' la lista dei tool
esentati era scritta a mano in due posti, «28 voci contro 20, cinque in comune,
e due nomi che non corrispondevano a nessun tool». `_pavimento_di` (296) e' la
«terza generazione della stessa cura». Due copie di un coseno oggi sono
identiche; quella che qualcuno correggera' fra sei mesi sara' una sola.
**Nessuna cura: il mandato dice mappa.**

## Nota 14 — tre righelli per la colonna «test», tre numeri diversi

La stessa domanda («questa funzione ha un test?») risponde diverso a seconda
di come la si misura. Tutti e tre i numeri sono sulle stesse 67 righe:

| righello | cosa guarda | quante delle 67 |
|---|---|---|
| `git grep` del nome in `tests/` | qualunque occorrenza, docstring compresi | il piu' alto (e 2 volte su 14 era prosa) |
| AST del file di test | il test **importa** o **chiama** il simbolo | **37** |
| coverage | righe del **corpo** eseguite | **45** |

I 1.663 file di test esaminati per la riga AST; i 45 vengono da **tre soli**
file di test, quindi il numero vero di quel righello e' piu' alto.

**E non e' che uno sia severo e l'altro largo: sbagliano in DIREZIONI
OPPOSTE.** Il grep gonfia (prende il nome dentro un commento). L'AST del test
sgonfia, e proprio dove fa piu' male: fra i suoi «nessun test li nomina» ci
sono `_ok`, `_err` e `_err_proposizione_vuota` — le funzioni che danno forma a
**ogni** risposta e **ogni** errore del prodotto. Nessun test le nomina;
coverage le vede tutte e tre accendersi, perche' ci si arriva **dalla porta**.
Un ruolo che nessun grep e nessun AST del test puo' vedere.

Conseguenza pratica per chi riempie la stessa colonna su un altro file: **il
numero dipende dal righello, non dal codice.** Se ognuno usa il suo, i
contatori non sono confrontabili fra owner.

Dettaglio tecnico che cambia il risultato: coverage segna «esercitata» solo se
una riga del **corpo** e' stata eseguita. La riga del `def` non basta — quella
gira alla definizione del modulo anche se la funzione non e' mai chiamata.
Senza quel controllo il numero mente al rialzo su tutte e 67.

## Nota 15 — la porta delle «resources» non espone i fatti

`mcp_server.py` implementa la superficie MCP `resources`: `list_resources`
(15592), `read_resource` (15659), `_read_resource_body` (15619). Gli URI
esistenti, tutti, presi dal sorgente (14 occorrenze di `hippo://`):

    hippo://skills/list   hippo://skills/{id}
    hippo://episodes/recent   hippo://episodes/{id}

Skill ed episodi. **Nessun URI per i fatti** — l'oggetto che da' il nome al
prodotto. E il README non nomina mai questa superficie:
`grep -c -i resource README.md` -> 1, ed e' «low-resource language» a riga
161; `grep -c 'hippo://' README.md` -> 0. Controllo positivo perche' un grep
vuoto non e' una prova: `grep -c -i memory README.md` -> 42.

Non e' una promessa rotta: e' una superficie che **nessuno rivendica e nessuno
misura**. La segnalo perche' un host MCP mostra le resources all'utente, e
quello che gli mostriamo oggi sono le skill. Nessuna cura: mandato mappa.

## Nota 16 — coverage ha detto 0 su una funzione che ERA girata

`_list_tools_unfiltered` (1687-7724, 6.038 righe) risulta con **una sola**
riga eseguita, la 1687, che e' il `def`: zero righe di corpo. Cioe' «mai
chiamata». Ma nello stesso run, due strade indipendenti dicono il contrario:

1. `_apply_tool_namespace` ha eseguito 19 righe di corpo, e fra quelle c'e' il
   ciclo che rinomina i tool: con una lista vuota quel corpo non gira.
2. `_ensure_derived_schemas` ha eseguito 12 righe, e `_derive_lenient_schema`
   ne ha eseguite 18 — e l'unico modo di arrivarci e' il ciclo su
   `tools = await _list_tools_unfiltered()`.

Quindi la funzione e' girata e ha reso una lista non vuota, e il rapporto la
da' per spenta. **Non so ancora perche'** — l'ipotesi che non ho verificato e'
l'attribuzione delle righe per un corpo fatto di UNA sola espressione lunga
6.000 righe. Quello che so, e che basta per non fidarsi: **un «0 righe
eseguite» di coverage su una funzione enorme non e' prova di codice morto.**
Per questo la sua riga in tabella resta NON MISURATO e non «MAI CHIAMATA»:
non si scrive un verdetto con un righello che si e' appena visto sbagliare.

## Nota 20 — «spenta» tre volte su cinque voleva dire «non ci sono arrivato io»

Per chiudere le ultime righe ho smesso di cercare un test e ho guidato i
**tool** dalla porta, sotto coverage. Tre tentativi, e i primi due hanno
mancato il bersaglio per colpa mia, non del prodotto:

| cosa avevo scritto | cosa succedeva | il nome vero |
|---|---|---|
| `provider="mock"` | lo schema rifiuta prima del codice | l'enum e' anthropic/openai/openrouter/groq/deepseek/ollama/xai |
| `check_contradictions=True` | il ramo a 9765 non partiva, la funzione sembrava morta | **`detect_contradictions`** |
| `hippo_skill_edit` per CREARE una skill | «skill not found»: edit non crea | `hippo_skill_import` con `skills: [{id, …}]` |
| store vuoto | `n_facts: 0`, `analogues: []`: i rami non partono | prima si popola, poi si chiede |

Risultato: `_build_episode`, `_remote_cls`, `_provider_is_configured`,
`_justified_contradicted_ids` e `_cos` erano tutte **vive**, e tutte e cinque
le avevo viste spente. Se mi fossi fermato al primo run avrei scritto cinque
«MAI CHIAMATA» su codice che funziona.

⇒ **La lezione per la mappa, e vale per tutti e otto**: una funzione spenta va
scritta con la CONDIZIONE che la accende, non con l'etichetta «non chiamata».
La condizione e' un fatto sul prodotto («il coseno vive nel ramo delle
analogie, che senza skill non parte»); l'etichetta e' solo il resoconto di un
tentativo mio. E' la nota 18 girata verso di me: la' erano i test a non
arrivarci, qui ero io.

Una cosa buona misurata passando: con `VERIMEM_SERVER_URL` che punta a una
porta dove **non ascolta nessuno**, `hippo_facts_search` ha reso una
risposta locale normale invece di piantarsi. Il «fail-soft» che il commento a
7853 promette e' misurato, non solo scritto.

## Nota 19 — le DUE vie di scrittura che non passano da `Memory.add`

Reperto di @ws3 Ricerca (08/09, post 4c475db1): due vie di scrittura MCP non
passano da `Memory.add`. **La constatazione e' esatta**; l'inferenza che
qualcuno potrebbe trarne — «allora scrivono senza gate» — no. Il gate non sta
dentro `Memory.add`: e' chiamato esplicitamente nel server, su entrambe.

**Via A — `hippo_remember`**

| riga | cosa fa |
|---|---|
| 13313 | `from .anti_confab_gate import run_validation_gate` |
| 13409 | `_ground_write = True` quando c'e' un `source` (l'env puo' solo SPEGNERE) |
| 13421 | `_gate = run_validation_gate(..., source=_source, ground_write=..., claimant=_MCP_PRINCIPAL, documents=LazyDocumentStore())` |
| 13439 | `if _gate.action == "reject"` -> audit `rejected_anti_confab`, ricevuta `ok: false` |
| 13453 | `if _gate.action == "downgrade"` -> `status='quarantined'`, fuori dal recall di default |
| 13539 | `_build_fact(..., confidence_tier=_calcola_tier(_gate...))` |
| 13638 | `a.semantic.store(fact)` |

**Via B — i `key_facts` di `hippo_record_episode`**

| riga | cosa fa |
|---|---|
| 9487 | `_kf_gate = _rvg(..., source=_kf_source, ground_write=True if _kf_source else None, ...)` |
| 9498 | la ricevuta porta il campo `moat`, con «judged N» / «not run — no source» / «could not judge … **this is NOT a pass**» |
| 9511 | `if _kf_gate.action == "reject"` -> il fatto e' **saltato** (`continue`) |
| 9522 | `_build_fact(..., status='quarantined' if downgrade else 'model_claim')` |

Il commento a 9476 racconta l'incidente: **prima** i key_facts scrivevano un
Fact SALTANDO l'anti-confab, entravano a `status='model_claim'`, rank 2,
default-recallable, «scavalcando i detector L1.x». Cioe' il buco esisteva
davvero su questa via, ed e' documentato come chiuso e reso «simmetrico a
hippo_remember».

E la riga 843 di `_build_fact` porta la misura di cosa costa NON passare da
`client.add()`: `confidence_tier` mancava a **145 fatti `mcp:*` su 145**,
mentre 4011 su 4011 `cli:*` ce l'avevano — «restava None PER COSTRUZIONE».
Non un ramo che sbagliava il calcolo: **l'etichetta dipendeva dalla PORTA da
cui il fatto entrava**, non dalla sua qualita'. E' la classe ① (una copia
invece della superficie unica) pagata per intero.

⚠️ **Il codice letto non e' una misura**, e questa nota poggia sulla lettura.
La falsificazione sta in
`tests/test_una_fonte_falsa_dalla_porta_degli_agenti_viene_fermata.py`, che
guida le due vie **dalla porta** con una fonte che parla d'altro e con un
controllo positivo (stessa via, fonte che sostiene, deve ammettere).

## Nota 18 — SEI file di test passano senza toccare la funzione che portano nel nome

Il secondo run di coverage (11 file, 96 passed in 114 s, EXIT=0) e' stato
scelto apposta: dentro c'erano i file che la colonna «test» attribuiva alle
righe ancora scoperte. Sei di quelle righe hanno **zero righe di corpo
eseguite** anche col loro test dentro il run:

| funzione | il file che l'avrebbe coperta | esito del file | righe del corpo eseguite |
|---|---|---|---|
| `_build_episode` | `test_mcp_record_episode_with_facts.py` | 5 passed | **0** |
| `_justified_contradicted_ids` | `test_justified_audit_mcp.py` | 6 passed | **0** |
| `_provider_is_configured` | `test_mcp_describe_provider_merge.py` | 8 passed | **0** |
| `_skill_from_dict` | `test_mcp_export_import_test_audit.py` | 13 passed | **0** |
| `_cos` | `test_un_analogia_che_non_puo_esistere_lo_dice.py` | 5 passed | **0** |
| `_key_recency` / `_key_activity` | `test_skills_top_used.py` | 5 passed | **0** |

Tutti e undici i file sono stati raccolti ed eseguiti — l'ho verificato riga
per riga nell'output di pytest, non dedotto dal totale.

**Non sto dicendo che quei test siano sbagliati.** Un test puo' legittimamente
esercitare un'altra strada: `_build_episode` serve la modalita' ospitata,
`_provider_is_configured` un ramo che quel test non prende. Sto dicendo una
cosa piu' ristretta e misurata: **la colonna «test che la esercita», compilata
col nome, per queste sei righe dice il falso** — e con essa avrei scritto sei
verdi. Sono le righe da guardare per prime se qualcuno cerca dove il presidio
manca davvero: hanno un test che porta il nome giusto, che passa, e che non ci
arriva. E' la forma «una misura che non c'e' si legge come perfetta».

## Nota 17 — `main()` dichiara che il journal non vede le letture MCP,
## e rimisurandolo oggi il buco e' PIU' GRANDE di quello che dichiara

Dentro `main()` (riga ~15790) c'e' un commento datato 2026-08-31 che merita di
stare fuori da un file di 15.848 righe: la variabile `ENGRAM_FLOW_SURFACE=mcp`
marca gli eventi emessi **dal nucleo**, e le LETTURE non ci passano — gli
handler di lettura chiamano `a.semantic` diretto, mentre `flow.recall` lo
emette `Memory.search` in `client.py`. Il commento porta la sua misura: su
4.716 `flow.recall`, `surface=mcp` compare ZERO volte, mentre `mcp` marca
1.373 eventi in totale.

**L'ho rimisurato oggi**, su `events.jsonl` + il ruotato `.1` (26.517 righe, 6
illeggibili, finestra 2026-09-01 20:58 -> 2026-09-08 21:15):

```
payload.surface, TUTTI gli eventi        payload.surface sui soli flow.recall
   unknown      14947                       unknown      2751
   (assente)     8459                       gateway       128
   cli           1706                       cli            16
   mcp            934                       sdk            12
   gateway        275                       mcp              0
```

Il commento regge: **zero letture marcate `mcp`**, e il controllo positivo lo
rende leggibile — `mcp` marca 934 eventi altrove, quindi lo zero e' un'assenza
vera e non un lettore rotto.

⚠️ E il primo tentativo il controllo NON l'aveva passato: cercavo `surface` in
cima al record, e mi usciva «(assente) 26511 su 26517» — cioe' un campo che non
esiste. Il campo vero e' `payload.surface`. Senza il controllo positivo avrei
pubblicato uno zero che non voleva dire niente.

**E il buco e' piu' grande di quello che il commento dichiara.** Delle 2.907
letture, quelle attribuite a una superficie sono 128+16+12 = **156, il 5,4%**:
le altre 2.751 (94,6%) sono `unknown`. Quindi non e' solo che «la porta MCP e'
invisibile»: **chi conta le letture per superficie su questo journal puo'
attribuirne una su venti**, e la fetta MCP di quelle attribuite e' zero.

Il commento dice anche perche' non e' stato curato: aggiungere un `emit` nei
gestori di lettura aggiungerebbe righe a un journal su cui misurano in
parecchi, «so it is a group decision, not a silent fix». Sono d'accordo e non
lo tocco. Lo porto qui perche' un commento a riga 15.790 non e' un canale.

## Il denominatore, e perché me lo sono fatto dare due volte

`66` è il numero del mandato e l'ho verificato prima di usarlo, perché un
contatore con un denominatore sbagliato è peggio di nessun contatore.

- Con `ast.walk` su tutto l'albero: **66**.
- Con un mio visitatore che scendeva solo dentro funzioni e classi: **58**.
  Saltava le funzioni annidate che vivono dentro `if`/`try` di modulo.

I due non concordavano e ho confrontato invece di pubblicare il primo che avevo
in mano — l'errore che ho fatto due volte oggi (un parser che saltava righe in
silenzio; un `iterdir` non ricorsivo che ha dato 3513 KB dove `du` diceva 8,3 GB).

Composizione delle 66, che serve a leggere la mappa:

| dove vivono | quante |
|---|---|
| a livello di modulo | 55 |
| dentro `_call_tool_impl` (l'handler dei tool) | 8 |
| dentro la classe `_TokenBucket` | 2 |
| dentro `_apply_tool_namespace` | 1 |

⚠️ **`grep -c "def "` qui non è il numero**: conterebbe anche i `def` nelle
stringhe e nei commenti, e in questo file ce ne sono. Il mandato dice «niente
grep-conteggi» e questa è la ragione, misurata.

## Come leggere le righe

`promessa` è quello che la funzione dichiara di fare (docstring o nome).
`chiamata da` è chi la usa DAVVERO. `test` è il file che la esercita.
`claim README` dice se sta dietro una promessa pubblica. `verdetto` è mio.
`prova` è il comando che ho eseguito — se manca, la riga dice NON VERIFICATO.

---

## Parte 1 — le funzioni dietro un claim del README

Sono la strada dei tool `hippo_remember` / `hippo_facts_recall` /
`hippo_facts_search` / `hippo_recall_as_of`, cioè ciò che un agente tocca.

### `_ag` — riga 94
- **promessa**: «Process-wide agent, built exactly once, SENZA tenere il lock».
- **chiamata da**: quasi ogni handler di tool (`a = _ag()`).
- **claim README**: sì, indiretto — ogni promessa sui tool passa di qui.
- **verdetto**: ✅ fa quello che dice, ed è la superficie unica dell'agente.
- **prova**: `tests/test_il_build_dell_agent_non_tiene_il_lock.py` — 4 passed
  (misurato il 07/09, fatto `t1b-red-green-del-lock`).

### `_ok` — riga 270
- **promessa**: (nessuna docstring) impacchetta una risposta riuscita.
- **chiamata da**: tutti gli handler, alla fine del ramo felice.
- **claim README**: sì — è la forma di OGNI ricevuta che un agente legge.
- **verdetto**: 🟡 **senza docstring**, ed è la funzione che decide come appare
  ogni risposta del prodotto. Non è un difetto di comportamento: è che il punto
  più letto del file non dice cosa promette.
- **prova**: esercitata da ogni cella MCP; nessun test la nomina direttamente.

### `_conta_sostituiti` — riga 274
- **promessa**: «Quanti fatti sono stati RIMPIAZZATI da una scrittura successiva».
- **chiamata da**: il ramo di lettura, per l'avviso dei ritirati.
- **claim README**: sì — la supersessione è una promessa pubblica.
- **verdetto**: ✅.
- **prova**: `tests/test_ogni_superficie_di_lettura_dichiara_i_sostituiti.py`
  (dentro i 78 passed del 07/09).

### `_pavimento_di` — riga 296
- **promessa**: «Il pavimento calibrato, da QUALUNQUE forma di oggetto la
  lettura abbia reso».
- **chiamata da**: gli avvisi di lettura sulle porte MCP.
- **claim README**: sì — «abstention over hallucination» si regge sul pavimento.
- **verdetto**: ✅, ed è una superficie unica nata da una divergenza fra porte
  (il commento sopra la funzione la chiama «terza generazione della stessa cura»).
- **prova**: `tests/test_avviso_mcp_stessa_soglia_dell_sdk.py`,
  `tests/test_tre_porte_una_risposta_sul_pavimento.py`.

### `_avvisi_di_lettura` — riga 334
- **promessa**: «Gli avvisi che CLI e SDK danno già, portati alla porta [MCP]».
- **chiamata da**: gli handler di lettura.
- **claim README**: sì.
- **verdetto**: ✅ per gli avvisi che copre. ⚠️ **ma è il punto dove un avviso
  nuovo va aggiunto a mano**: è la giuntura che ha prodotto due cure di seguito
  (pavimento, ranking degradato — «⚠️ QUARTA GENERAZIONE DELLA STESSA CURA»).
- **prova**: `tests/test_l_avviso_non_usciva_dalla_porta_dell_agente.py`.

### `_err` — riga 532
- **promessa**: (nessuna docstring) la forma di un errore.
- **chiamata da**: ogni ramo di rifiuto.
- **claim README**: sì — un errore è la risposta che l'agente riceve quando
  qualcosa non va, e il prodotto promette di dire *perché*.
- **verdetto**: 🟡 senza docstring, come `_ok`.
- **prova**: NON VERIFICATO come funzione a sé.

### `_err_proposizione_vuota` — riga 546
- **promessa**: (dal nome) il rifiuto di una scrittura senza testo.
- **chiamata da**: `hippo_remember`.
- **claim README**: sì — è il primo errore che un agente incontra sbagliando.
- **verdetto**: ✅ nome che dice tutto.
- **prova**: NON VERIFICATO.

### `_auth_closed` — riga 207
- **promessa**: «Fail-closed receipt when the configured server rejected [the key]».
- **chiamata da**: il thin client, quando il server condiviso rifiuta la chiave.
- **claim README**: sì — il fail-closed è una promessa esplicita («refusing to
  fall back to a local store»).
- **verdetto**: ✅ e il nome dichiara la direzione del fallimento, che è la cosa
  che conta in un fail-closed.
- **prova**: NON VERIFICATO in questa sessione.

### `_remote_row` — riga 216
- **promessa**: «Shape a shared-server search hit like a local recall/search hit».
- **chiamata da**: il ramo delegato.
- **claim README**: sì — «N sessioni condividono il server» promette che la
  risposta sia la stessa.
- **verdetto**: ⚠️ **è una traduzione fra due forme**, cioè esattamente il punto
  dove una porta può dire una cosa diversa dall'altra senza che nessuno lo veda.
  Merita una cella sua: non l'ho trovata.
- **prova**: NON VERIFICATO.

### `_remote` — riga 181
- **promessa**: (nessuna docstring) il thin client verso il server condiviso.
- **chiamata da**: gli handler quando `VERIMEM_SERVER_URL` è impostata.
- **claim README**: sì.
- **verdetto**: 🟡 senza docstring su una funzione che decide se la lettura
  esce dal processo.
- **prova**: `tests/test_remote_memory.py` la esercita (34 passed il 07/09).

---

## Parte 2 — la spina dorsale: cosa attraversa OGNI chiamata

Le 24 funzioni qui sotto non le ho scelte per nome ma per posizione: sono
quelle che una `tools/call` percorre **prima** di arrivare al pezzo di
`_call_tool_impl` che risponde. Le elenco nell'ordine in cui girano, perché
in un dispatch l'ordine è la cosa che si sbaglia (un cancello dopo una
scorciatoia non è un cancello — `_call_tool_impl:7815` documenta esattamente
questo incidente: «they used to run after `a = _ag()`»).

### L'ordine, letto dal codice (righe 7797-7975)

| # | funzione | riga | cosa fa alla chiamata |
|---|---|---|---|
| 1 | `call_tool` | 7797 | l'unico handler registrato (`@server.call_tool()`); avvolge tutto nel guardiano degli hang |
| 2 | `_call_tool_impl` | 7806 | arma il cronometro, azzera l'alias, riscrive il nome |
| 3 | `_drop_none_args` | 613 | toglie i `null` di primo livello |
| 4 | `_ensure_derived_schemas` | 1602 | costruisce una volta gli schemi indulgenti |
| 5 | `_validate_input` | 1528 | valida (jsonschema, o `_manual_validate` 1495) |
| 6 | *(delega remota)* | 7853 | `_remote`/`_remote_row`/`_auth_closed` — Parte 1 |
| 7 | `_ag` | 7952 | costruisce l'agente locale — Parte 1 |
| 8 | `_rate_limit` | 1334 | solo per 2 tool su ~250 |
| 9 | `_capability_gate` | 1128 | il cancello delle capacità |
| 10 | *(l'handler del tool)* | — | il corpo vero |

`_audit` (1211) non è un passo: è chiamato **da ognuno** di questi passi
quando decide qualcosa, ed è l'unico posto da cui esce una traccia.

### `call_tool` — riga 7797
- **promessa**: «thin dispatch wrapper», guarda la chiamata per gli hang.
- **verdetto**: ✅ ed è deliberatamente **inline**, non su thread — la
  docstring dice perché («that broke stdio»). Budget 30 s, spegnibile con
  `HIPPO_HANG_TRACE_S=0`; è osservabilità, non annulla la chiamata.
- **prova**: `verimem/_hang_watchdog.py` esiste ed è importato lì; NON
  VERIFICATO che il dump atterri (non ho provocato un hang).

### `_call_tool_impl` — riga 7806 · **7784 righe, senza docstring**
- **promessa**: nessuna. È il corpo del prodotto alla porta degli agenti:
  metà del file (7784 righe su 15848) è questa funzione.
- **cosa fa nelle prime 40 righe**: `_REQUEST_START_NS` (da cui nasce
  `latency_ms`), `_REQUEST_TOOL_ALIAS`, e la riscrittura `engram_*` /
  `verimem_*` → `hippo_*`.
- **verdetto**: ⚠️ il commento a 7833 dice la cosa giusta e la dice bene —
  «da qui in poi il nome ricevuto non esiste più in nessuna variabile: si
  conserva ORA, o è perduto». È la funzione più lunga del prodotto e non
  dichiara niente di sé.
- **prova**: `end_lineno - lineno + 1 = 7783`, dallo stesso `ast` del
  denominatore (righe 7806-15588 su un file di 15848).

### `_drop_none_args` — riga 613
- **promessa**: un `null` JSON per un argomento OPZIONALE deve valere «usa il
  default», non schiantare.
- **verdetto**: ✅, e la docstring spiega il perché con il numero (~236 siti
  `int()/float()` che esplodevano). Tiene `0`, `False`, `""`, `[]`: solo
  `None` cade.
- ⚠️ **conseguenza che nessuno ha scritto**: gira PRIMA di `_validate_input`,
  quindi l'allargamento a `"null"` di ogni tipo dentro `_derive_lenient_schema`
  (1590) difende da un valore che, al primo livello, non può più arrivare.
  Non è un difetto — è una cintura sopra le bretelle. **Letto, non eseguito.**

### `_validate_input` (1528) · `_manual_validate` (1495) · `_derive_lenient_schema` (1566) · `_ensure_derived_schemas` (1602)
- **promessa**: ogni tool registrato valida almeno tipo ed enum (prima della
  §305 ne validavano ~15 su ~228).
- **verdetto sul disegno**: ✅ due strati, e la precedenza è dichiarata: lo
  schema scritto a mano vince, quello derivato copre il resto.
- 🔴 **il reperto**: i due validatori dello STESSO input non concordano, e la
  discordanza è invisibile perché il secondo non gira mai.
  - `_manual_validate` esiste solo nel ramo `except ImportError: jsonschema`.
  - `jsonschema>=4.0.0` è **dipendenza dichiarata** (`pyproject.toml:57`) ed è
    installata (4.26.0). Quindi in un'installazione corretta quel ramo è
    irraggiungibile.
  - e se girasse, sarebbe **più permissivo**: usa `isinstance(v, int)`, che in
    Python è vero per un booleano.

    ```
    jsonschema  k=True   -> RIFIUTATO: True is not of type 'integer'
    jsonschema  k=5      -> AMMESSO
    isinstance(True,int) -> True
    ```
  - **verdetto**: 🟡 non è un difetto vivo (il ramo non gira), è **codice di
    riserva che si comporta diversamente dal titolare**. Se un giorno la
    riserva entra in campo, valida meno. Lo scrivo qui perché è il caso che
    un lettore non vede: la funzione c'è, i test la possono chiamare
    direttamente, e il prodotto non la usa mai. **Niente cura: è una mappa.**

### `_rate_limit` (1334) · `_get_bucket` (1325) · `_bucket_for` (1313) · `_TokenBucket.__init__` (1291) · `_TokenBucket.take` (1298)
- **promessa**: «True se la chiamata è permessa, False se limitata».
- **verdetto**: ✅ token bucket in memoria, con lock, 1/min di default e
  override per tool via `HIPPO_MCP_RATELIMIT_<TOOL>_RPM`.
- ⚠️ **perimetro, non difetto**: `_RATE_LIMITED_TOOLS` (1541) contiene **due**
  nomi — `hippo_run_task` e `hippo_consolidate`. Il commento lo dichiara
  («heavy ops only»). Chi legge «rate limiting» in un elenco di funzioni
  crede che copra la porta: copre due tool.
- **prova**: `frozenset({"hippo_run_task", "hippo_consolidate"})`, riga 1541-1543.

### `_capability_gate` (1128) · `_capability_gate_mode` (1102) · `_audit_capability_call` (1064) · `_bypass_dal_registro` (1055)
- **promessa** (commento a 7959-7969, sopra la chiamata): «every call_tool
  invocation runs through `_capability_gate()` which: … **Hard-blocks**
  DESTRUCTIVE / requires_confirm … **Emits an audit row regardless**».
- **verdetto**: 🔴 **la frase è vera e conclude il falso.** Ogni chiamata
  *attraversa* la funzione; ma la prima cosa che la funzione fa è

  ```
  mode = _capability_gate_mode()
  if mode == "off":
      return True, None
  ```

  e `_capability_gate_mode()` rende `"off"` a meno che
  `ENGRAM_CAPABILITY_GATE` non sia impostata. Nel modo di default non blocca
  niente **e non scrive nemmeno la riga di audit** che il commento promette
  «regardless».
- **la misura, con il denominatore e la finestra**:

  ```
  file: C:\Users\<utente>\.engram\mcp_audit.log   (2.100.293 byte, nessun .1: mai ruotato)
  righe leggibili: 15432   finestra: dal 2026-05-08 01:41 al 2026-09-08 19:43
  controllo POSITIVO  '"outcome":"ok"'          -> 11604
  cap_allow|cap_deny|cap_bypass                 ->     5
  ```

  Le cinque, tutte con `[mode=enforce]` nel campo `reason`: una del
  2026-06-03 (`sandbox_exec`), quattro del **2026-07-09** — due `cap_allow` e
  due `cap_deny` (`hippo_fact_forget`, `hippo_forget_scope`). Da allora,
  nessuna. **Il cancello ha deciso 5 volte su 15.432 chiamate registrate in
  quattro mesi (0,03%), l'ultima due mesi fa.**
- **la parte onesta, e conta**: il README **non promette** questo cancello —
  ho cercato `capability|gating|fail-closed` e l'unico esito è la parola
  «Capability» come intestazione di una tabella di confronto (riga 701).
  Quindi **nessuna promessa pubblica è rotta**: il default OFF è una
  decisione dichiarata nella docstring (2026-05-27, «175/215 tool bloccati
  durante sviluppo single-user»). E le due `cap_deny` provano che quando è
  acceso **blocca davvero**. Il reperto non è «è rotto»: è che *il commento
  nel dispatch descrive il modo acceso come se fosse il modo normale*, e
  quello è il testo che un lettore del codice incontra per primo.
- **la decisione, che non è mia**: sta in memoria come preferenza di Aurelio
  («niente default OFF»). La segnalo, non la eseguo — il mandato dice
  niente cure.
- `_bypass_dal_registro` (1055): ✅ **superficie unica nata da una divergenza**
  — prima del 03/09 la lista dei tool esentati era scritta a mano qui e nella
  matrice, «28 voci contro 20, cinque in comune, e due nomi che non
  corrispondevano a nessun tool». Ora deriva da `REGISTRY._caps`.
- `_audit_capability_call` (1064): ✅ e la scelta di registrare **le chiavi
  degli argomenti, mai i valori** è motivata e presidiata da un test
  (`test_i_valori_NON_finiscono_nel_log`).

### `_audit` (1211) · `_audit_log_path` (976) · `_rotate_audit_if_needed` (1016)
- **promessa**: una riga JSONL per chiamata, best-effort, mai solleva.
- **verdetto**: ✅ ed è la funzione con la docstring migliore del file: dice
  che `outcome` è un'**etichetta chiusa** e racconta il difetto che l'ha
  insegnato — conteggi incastrati nel nome, 52 valori distinti di cui 27 con
  cifre dentro, e `hippo_summary_topic` che risultava «100% non-ok» su
  quindici chiamate tutte riuscite (misurato 2026-07-31).
- **è qui che nasce `latency_ms`**: `_REQUEST_START_NS` viene armata in cima a
  `_call_tool_impl` e letta qui. Cioè il numero misura **tutta** la chiamata,
  gate e delega compresi — è il metro con cui è stato visto il primo
  `remember` con fonte a 303 s.
- ⚠️ **scudo PII**: gli argomenti finiscono nel log solo come
  `sha256[:16]`. Deliberato, e non invertibile: da una riga non si sa con
  quale campo il tool sia stato chiamato (è la ragione per cui
  `_audit_capability_call` aggiunge le chiavi a parte).
- `_rotate_audit_if_needed`: ✅ 5 MB, un solo backup `.1`, `os.replace`
  atomico. **Non è mai scattato** su questa macchina: 2,1 MB e nessun `.1`.

### `_iso_day` (576) · `_apply_live_filter` (593)
- `_iso_day`: ✅ epoch → `YYYY-MM-DD`, e la docstring dice a chi serve —
  all'agente che legge, per ragionare sul tempo. `None` su 0 o non numerico.
- `_apply_live_filter`: ✅ ed è **la classe ④ della memoria (il bug è la
  giuntura)** scritta dall'autore stesso: la prima versione filtrava solo
  `facts` e lasciava passare `facts_ranked`, «il segnale di retrieval
  PRIMARIO». Due liste della stessa cosa, una sola filtrata.

### `list_tools` (7728) · `_apply_tool_namespace` (7741) · `_riferimento` (7759)
- **promessa**: il registro completo, filtrato da `ENGRAM_MCP_TOOLS_PREFIX` e
  poi rinominato se `VERIMEM_TOOL_NAMESPACE=verimem`.
- **verdetto**: ✅ e `_apply_tool_namespace` è l'unico punto del file che ha
  già imparato la lezione dello SWEEP: non rinomina solo `name`, riscrive
  anche i **riferimenti dentro le descrizioni** — «misurato 16/08: 50 tool su
  248, 61 riferimenti». Senza, il prodotto rimandava a nomi che non espone.
- `_riferimento` (nested, senza docstring): il commento sopra vale una
  docstring — riscrive **solo** ciò che corrisponde a un tool davvero
  rinominato, perché `hippo_facts_*` è una famiglia e `HIPPO_DISABLED` una
  variabile d'ambiente.
- ⚠️ **asimmetria per disegno**: il filtro dei prefissi agisce sulla
  DISCOVERY; `_call_tool_impl` dispaccia lo stesso qualunque nome registrato
  (commento a 1629). Un tool nascosto resta chiamabile. È dichiarato.

---

## Cosa resta

32 funzioni su 66: le 8 dentro `_call_tool_impl` (`_props`, `_cos`,
`_encode_skill`, `_cosine`, `_default_coherence_hook`, `_key_fitness`,
`_key_recency`, `_key_activity` — nessuna con docstring), e 24 del modulo,
fra cui le superfici di sicurezza (`_looks_shell_like`, `_doc_path_allowed`,
`_sandbox_policy`, `_shell_perm_enabled`, `_forget_cross_scope_denied`), la
costruzione dei fatti (`_build_fact`, `_content_hash_id`, `_build_episode`),
le risorse (`list_resources`, `read_resource`, `_read_resource_body`) e
`main`.

### Il dato sulle docstring — e la correzione al mio stesso numero

Alla Parte 1 avevo scritto «sei funzioni su dieci non hanno docstring». Sulle
**66** il tasso è un altro, e la differenza è tutta nel campione che mi ero
scelto:

```
funzioni totali: 66 | senza docstring: 23 (35%)
```

**Il 35%, non il 60%.** Il mio campione di dieci era la testa del file, dove
stanno gli helper minuti; l'ho pubblicato come «un dato che emerge» e non
reggeva l'allargamento. È la forma che ho già trovato due volte oggi su
misure altrui — un numero letto su una finestra scelta da me — e valeva anche
per me. La riga della Parte 1 resta scritta apposta, con questa accanto.

E la lista intera cambia anche il *senso* del reperto. Le 23 senza docstring,
per lunghezza:

| lunghezza | quante | esempi |
|---|---|---|
| ≤ 12 righe | 20 | `_ok` (2), `_err` (2), `_key_fitness` (2), `_bucket_for` (6) |
| 13-25 righe | 2 | `_default_coherence_hook` (18), `list_resources` (25) |
| **7783 righe** | **1** | **`_call_tool_impl`** |

Una funzione di **due** righe che si chiama `_ok` e impacchetta una risposta
riuscita non ha un problema di documentazione: il nome è la docstring. Alla
Parte 1 le avevo messe sullo stesso piano, ed era sbagliato. Il reperto vero
è **uno solo**, ed è quello che il conteggio percentuale nasconde: metà del
file — 7783 righe su 15848 — è una funzione senza una riga che dica cosa
promette, e ci passa dentro ogni chiamata che un agente fa.

Le tre da guardare dopo, per lunghezza e non per posizione: `list_resources`
(25), `_default_coherence_hook` (18), `_remote` (24, già in Parte 1).
