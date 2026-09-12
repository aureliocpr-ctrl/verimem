# verimem/dream.py — mappa

**Owner**: ws4 (ML Ferro) · **909 righe · 18 fra funzioni, metodi e classi**.

Il consolidamento onirico: proposte di skill generate dal sonno.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                18 / 18
  con un verdetto                                        8
     «i test che la nominano passano»                    8
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           10
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `dream.py` **nessuna
funzione è ancora verificata contro la propria promessa** con casi scelti sul
docstring: le righe con verdetto dicono che il banco è verde, non che la promessa
è mantenuta.

## ⚠️ Le righe NON MISURATO: nessuna è «MAI CHIAMATA»

Ognuna è stata cercata col **NOME NUDO** (`\bnome\b`) e **non** con `nome(`, che
non vedrebbe un riferimento passato come callback — trappola segnalata da @ws6 il
08/09, dopo che stava per proporre la rimozione di codice vivo. **Tutte hanno
riferimenti**: manca la copertura di test, non il chiamante.

⚠️ Quei riferimenti sono **candidati del grep, non letti uno per uno**, e la riga
lo dice. Il grep serve a trovare.


## Nota di metodo (aggiornata alle 20:58)

Le prime due versioni di questo file usavano uno scheletro mio. **Sono state
rigenerate con `scripts/mappa_bozza.py`**, lo strumento comune pubblicato dal
lead alle 20:52: dà più informazione (chiamanti con `file:riga`, test che
nominano il simbolo, righe del README) ed è il formato che
`scripts/mappa_completa.py` sa leggere. Un formato mio avrebbe fatto una
tabella che l'aggregatore non vede.

**Le misure già fatte sono state RIPORTATE, non rifatte**, iniettandole **per
nome** e non per indice: se lo strumento cambia l'ordine delle righe, una
sostituzione per numero metterebbe la prova sulla funzione sbagliata.

⚠️ **I chiamanti in questa tabella vengono da `git grep` e sono CANDIDATI, non
conferme.** Vanno letti uno per uno prima di trasformarli in verdetto: il grep
serve a trovare. E prima di scrivere **MAI CHIAMATA** — che secondo il mandato
porta a proporre una rimozione — va cercato il **nome nudo**, non `nome(`: un
riferimento passato come callback (`head_at=sm.audit_head_at`) non ha parentesi
e non compare. È la trappola che @ws6 ha segnalato alle 20:45 dopo averla quasi
calpestata; su 2.973 funzioni produrrebbe proposte di rimuovere codice vivo.

# Mappa di `verimem/dream.py` — 18 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/dream.py:35` `_backup_sqlite` | funzione: Hot-copia un DB SQLite usando l'API backup (safe con WAL/concurrent reader). | `verimem/dream.py:182`; `verimem/dream.py:185`; `verimem/dream.py:186` (+4) | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_backup_sqlite\b`, non `_backup_sqlite(`, che non vedrebbe i riferimenti passati come callback) → **7 riferimenti**, i primi `verimem/dream.py:182`; `verimem/dream.py:185`; `verimem/dream.py:186`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 2 | `verimem/dream.py:62` `_ignore_sqlite_aux` | funzione: shutil.copytree ignore filter — esclude file SQLite ausiliari. | `verimem/dream.py:84` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_ignore_sqlite_aux\b`, non `_ignore_sqlite_aux(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/dream.py:84`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 3 | `verimem/dream.py:73` `_mirror_dir` | funzione: Copia ricorsiva di una directory (skills/ contiene .md bodies). | `verimem/dream.py:158`; `verimem/dream.py:179`; `verimem/dream.py:180` (+1) | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_mirror_dir\b`, non `_mirror_dir(`, che non vedrebbe i riferimenti passati come callback) → **4 riferimenti**, i primi `verimem/dream.py:158`; `verimem/dream.py:179`; `verimem/dream.py:180`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 4 | `verimem/dream.py:87` `_is_overlap` | funzione: True se `child` è uguale a `parent` o nested dentro `parent`. Resolve simboli. | `verimem/dream.py:110`; `verimem/dream.py:116` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_is_overlap\b`, non `_is_overlap(`, che non vedrebbe i riferimenti passati come callback) → **2 riferimenti**, i primi `verimem/dream.py:110`; `verimem/dream.py:116`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 5 | `verimem/dream.py:100` `_validate_no_overlap` | funzione: Raise ValueError se shadow_root copre alcun live path (parent o uguale). | `verimem/dream.py:170`; `verimem/dream.py:274` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_validate_no_overlap\b`, non `_validate_no_overlap(`, che non vedrebbe i riferimenti passati come callback) → **2 riferimenti**, i primi `verimem/dream.py:170`; `verimem/dream.py:274`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 6 | `verimem/dream.py:123` `create_shadow_engine` | funzione: Crea un SleepEngine puntato a snapshot shadow dei live DB. | `verimem/dream.py:4`; `verimem/dream.py:233`; `verimem/dream.py:781` (+4) | `tests/test_dream_shadow.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 7 | `verimem/dream.py:213` `propose_dream_tasks` | funzione: CYCLE #35 redesign — Hippo Dreams subscription-first. | `verimem/auto_dream_trigger.py:12`; `verimem/auto_dream_worker.py:13`; `verimem/auto_dream_worker.py:19` (+23) | `tests/test_auto_dream_register.py`; `tests/test_auto_dream_stable_partition_envvar.py`; `tests/test_auto_dream_trigger.py` (+9) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 8 | `verimem/dream.py:349` `_validate_skill_json` | funzione: CYCLE #36 — lenient schema validation (decisione di progetto, 2026-05-13). | `verimem/dream.py:472` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_validate_skill_json\b`, non `_validate_skill_json(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/dream.py:472`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 9 | `verimem/dream.py:393` `submit_dream_result` | funzione: CYCLE #36 — Hippo Dreams: persist skill output del LLM sul shadow. | `verimem/dream.py:577`; `verimem/dream.py:903`; `verimem/mcp_server.py:10942` (+1) | `tests/test_dream_adopt.py`; `tests/test_dream_adopt_crashsafe_r3.py`; `tests/test_dream_e2e.py` (+2) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 10 | `verimem/dream.py:515` `_load_artifact` | funzione: Load + validate dream_tasks.json. Helper condiviso da review tools. | `verimem/dream.py:548`; `verimem/dream.py:582`; `verimem/dream.py:622` (+1) | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_load_artifact\b`, non `_load_artifact(`, che non vedrebbe i riferimenti passati come callback) → **4 riferimenti**, i primi `verimem/dream.py:548`; `verimem/dream.py:582`; `verimem/dream.py:622`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 11 | `verimem/dream.py:538` `dream_status` | funzione: CYCLE #37 — Status summary di un dream. | `verimem/dream.py:904`; `verimem/mcp_server.py:10903`; `verimem/mcp_server.py:10912` | `tests/test_dream_e2e.py`; `tests/test_dream_review.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 12 | `verimem/dream.py:573` `dream_list_pending` | funzione: CYCLE #37 — Lista task ancora pending, completa di system_prompt+user_prompt. | `verimem/dream.py:905`; `verimem/mcp_server.py:10902`; `verimem/mcp_server.py:10914` | `tests/test_dream_e2e.py`; `tests/test_dream_review.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 13 | `verimem/dream.py:590` `_skill_signature` | funzione: Dream-mutable fields of a skill, for shadow-vs-live change detection | `verimem/dream.py:669` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_skill_signature\b`, non `_skill_signature(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/dream.py:669`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 14 | `verimem/dream.py:604` `dream_diff` | funzione: CYCLE #37 — Differenze shadow vs live: skill nuove pronte da adottare. | `verimem/dream.py:816`; `verimem/dream.py:817`; `verimem/dream.py:906` (+2) | `tests/test_dream_adopt.py`; `tests/test_dream_diff_changed_skills_audit3.py`; `tests/test_dream_e2e.py` (+1) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 15 | `verimem/dream.py:688` `_backup_live_skills` | funzione: Backup atomico di skills_index.db + dir skills (.md bodies) prima di adopt. | `verimem/dream.py:836` | `tests/test_dream_adopt_crashsafe_r3.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 16 | `verimem/dream.py:714` `_restore_live_skills` | funzione: Restore live skills_index.db + skills dir dal backup. Best-effort. | `verimem/dream.py:874` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_restore_live_skills\b`, non `_restore_live_skills(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/dream.py:874`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 17 | `verimem/dream.py:747` `_write_artifact_durable` | funzione: Write the dream artifact atomically + fsync so an adoption marker | `verimem/dream.py:835`; `verimem/dream.py:878`; `verimem/dream.py:887` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_write_artifact_durable\b`, non `_write_artifact_durable(`, che non vedrebbe i riferimenti passati come callback) → **3 riferimenti**, i primi `verimem/dream.py:835`; `verimem/dream.py:878`; `verimem/dream.py:887`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 18 | `verimem/dream.py:762` `adopt_dream` | funzione: CYCLE #38 — adopt atomico delle new_skills del shadow nel live. | `verimem/dream.py:907`; `verimem/mcp_server.py:10867`; `verimem/mcp_server.py:10881` | `tests/test_dream_adopt.py`; `tests/test_dream_adopt_crashsafe_r3.py`; `tests/test_dream_diff_changed_skills_audit3.py` (+1) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
