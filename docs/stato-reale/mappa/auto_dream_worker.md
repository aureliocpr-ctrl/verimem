# verimem/auto_dream_worker.py — mappa

**Owner**: ws4 (ML Ferro) · **509 righe · 11 fra funzioni, metodi e classi**.

Il lavoratore che fa partire il ciclo onirico da solo.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                11 / 11
  con un verdetto                                        8
     «i test che la nominano passano»                    8
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           3
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `auto_dream_worker.py` **nessuna
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

# Mappa di `verimem/auto_dream_worker.py` — 11 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/auto_dream_worker.py:32` `_resolve_engram_dir` | funzione: L'ordine degli alias lo decide `_compat`, non questo modulo. | `verimem/auto_dream_worker.py:473` | `tests/test_l_avviso_diceva_il_contrario_del_codice.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 2 | `verimem/auto_dream_worker.py:47` `_live_dirs_from` | funzione: Build the `live_dirs` dict that `propose_dream_tasks` expects. | `verimem/auto_dream_worker.py:135`; `verimem/auto_dream_worker.py:194` | `tests/test_auto_dream_worker_paths.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 3 | `verimem/auto_dream_worker.py:76` `_prune_old_dreams` | funzione: Retention for Auto-Dream shadow snapshots. | `verimem/auto_dream_worker.py:332`; `verimem/residual_copies.py:58` | `tests/test_auto_dream_retention.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 4 | `verimem/auto_dream_worker.py:110` `_persist_emergence_drafts` | funzione: Cycle 223 — write the current emergence drafts to disk for audit. | `verimem/auto_dream_worker.py:215`; `verimem/auto_dream_worker.py:273` | `tests/test_auto_dream_drafts_persist.py`; `tests/test_auto_dream_stable_partition_envvar.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 5 | `verimem/auto_dream_worker.py:171` `_propose_via_engram` | funzione: Bridge the worker's dream_callable signature to `propose_dream_tasks`. | `verimem/auto_dream_worker.py:123`; `verimem/auto_dream_worker.py:477` | `tests/test_auto_dream_drafts_persist.py`; `tests/test_auto_dream_register.py`; `tests/test_auto_dream_stable_partition_envvar.py` (+2) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 6 | `verimem/auto_dream_worker.py:336` `_maintenance_enabled` | funzione: (nessun docstring) | `verimem/auto_dream_worker.py:358` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_maintenance_enabled\b`, non `_maintenance_enabled(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/auto_dream_worker.py:358`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 7 | `verimem/auto_dream_worker.py:341` `_consolidate_cooldown_s` | funzione: (nessun docstring) | `verimem/auto_dream_worker.py:366` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_consolidate_cooldown_s\b`, non `_consolidate_cooldown_s(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/auto_dream_worker.py:366`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 8 | `verimem/auto_dream_worker.py:348` `run_maintenance` | funzione: WF1 SPINE — the self-maintenance half that was dormant: make the corpus DIGEST, not | `verimem/auto_dream_worker.py:483`; `verimem/webui/engine.html:190` | `tests/test_auto_dream_maintenance.py`; `tests/test_flow_manutenzione_notturna.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 9 | `verimem/auto_dream_worker.py:409` `_quanti` | funzione: Quanti elementi dichiara un esito, qualunque forma abbia. | `verimem/auto_dream_worker.py:450`; `verimem/auto_dream_worker.py:451`; `verimem/auto_dream_worker.py:452` (+5) | `tests/test_as_of_sulle_porte_ordinarie.py`; `tests/test_il_pavimento_vale_anche_per_gli_agenti.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 10 | `verimem/auto_dream_worker.py:425` `_emetti_la_passata` | funzione: La manutenzione automatica dice cosa ha fatto, e cosa e' fallito. | `verimem/auto_dream_worker.py:405` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_emetti_la_passata\b`, non `_emetti_la_passata(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/auto_dream_worker.py:405`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 11 | `verimem/auto_dream_worker.py:470` `main` | funzione: (nessun docstring) | `verimem/_hang_watchdog.py:18`; `verimem/_import_lock.py:7`; `verimem/_singleton_guard.py:34` (+95) | `tests/conftest.py`; `tests/perf/bench.py`; `tests/perf/bench_briefing_v3_robustness.py` (+111) | `README.md:50`; `README.md:66`; `README.md:378` | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
