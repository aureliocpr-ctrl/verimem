# verimem/anti_confabulation.py — mappa

**Owner**: ws4 (ML Ferro) · **500 righe · 14 fra funzioni, metodi e classi**.

Lo strato anti-confabulazione: uno dei posti dove vive «stops what the source does not support».

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                14 / 14
  con un verdetto                                        6
     «i test che la nominano passano»                    5
     idem, entro un limite DICHIARATO (xfail nei test)   1
  NON MISURATO                                           8
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `anti_confabulation.py` **nessuna
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

# Mappa di `verimem/anti_confabulation.py` — 14 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/anti_confabulation.py:94` `_find_shipped_keyword` | funzione: Return the first SHIPPED-like keyword found, else ``None``. | `verimem/anti_confabulation.py:211` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_find_shipped_keyword\b`, non `_find_shipped_keyword(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/anti_confabulation.py:211`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 2 | `verimem/anti_confabulation.py:103` `_parla_di_software` | funzione: Il claim riguarda un artefatto software, o solo una parola omonima? | `verimem/anti_confabulation.py:194`; `verimem/anti_confabulation.py:214` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_parla_di_software\b`, non `_parla_di_software(`, che non vedrebbe i riferimenti passati come callback) → **2 riferimenti**, i primi `verimem/anti_confabulation.py:194`; `verimem/anti_confabulation.py:214`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 3 | `verimem/anti_confabulation.py:153` `_is_pr_id_token` | funzione: A pr id-ish token to ignore when checking qualifiers: pure digits, or a | `verimem/anti_confabulation.py:170` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_is_pr_id_token\b`, non `_is_pr_id_token(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/anti_confabulation.py:170`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 4 | `verimem/anti_confabulation.py:161` `_is_landed_pr_ref` | funzione: True only for a pr: ref provably merged: a 'merged' token is present AND | `verimem/anti_confabulation.py:179` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_is_landed_pr_ref\b`, non `_is_landed_pr_ref(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/anti_confabulation.py:179`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 5 | `verimem/anti_confabulation.py:174` `_has_commit_ref` | funzione: True if any ref is a LANDED anchor for a shipped-like claim: commit:/ | `verimem/anti_confabulation.py:216`; `verimem/l1_orphan_detector.py:100`; `verimem/l1_orphan_detector.py:127` | `tests/test_anti_confab_pr_merged_r3.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 6 | `verimem/anti_confabulation.py:184` `detect_unsupported_shipped_claim` | funzione: L1 anti-confabulation warning detector. | `verimem/anti_confab_gate.py:57`; `verimem/anti_confab_gate.py:1464`; `verimem/anti_confabulation.py:289` (+6) | `tests/test_anti_confab_pr_merged_r3.py`; `tests/test_anti_confabulation_shipped_warning.py`; `tests/test_una_parola_non_e_un_claim.py` | - | **FUNZIONA COME PROMESSO** *(entro un limite DICHIARATO)* | batch 08/09 21:15, 48 file: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ Fra i test che la nominano ce n'è almeno uno con un **marker `xfail`**, cioè un difetto vivo messo sotto presidio invece che nascosto: `tests/test_una_parola_non_e_un_claim.py`. **Il verde qui non copre quel caso**, che resta noto e presidiato. Livello: i test che la nominano passano — non «fa ciò che il docstring promette», che va misurato a parte |
| 7 | `verimem/anti_confabulation.py:259` `_find_diagnosis_keyword` | funzione: Return the first diagnosis-like keyword found, else ``None``. | `verimem/anti_confabulation.py:291` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_find_diagnosis_keyword\b`, non `_find_diagnosis_keyword(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/anti_confabulation.py:291`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 8 | `verimem/anti_confabulation.py:268` `_has_test_ref` | funzione: True if any ref in ``verified_by`` matches test/pytest/bash. | `verimem/anti_confabulation.py:294` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_has_test_ref\b`, non `_has_test_ref(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/anti_confabulation.py:294`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 9 | `verimem/anti_confabulation.py:276` `detect_unsupported_diagnosis_claim` | funzione: L1.5 anti-confabulation warning for diagnosis-driven claims. | `verimem/anti_confab_gate.py:56`; `verimem/anti_confab_gate.py:1465`; `verimem/anti_confabulation.py:465` (+5) | `tests/test_anti_confabulation_diagnosis.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 10 | `verimem/anti_confabulation.py:354` `_find_task_state_phrase` | funzione: Return the first task-state phrase found (word-bounded), else ``None``. | `verimem/anti_confabulation.py:381` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_find_task_state_phrase\b`, non `_find_task_state_phrase(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/anti_confabulation.py:381`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 11 | `verimem/anti_confabulation.py:360` `_has_tracker_ref` | funzione: True if any ref in ``verified_by`` matches pr/issue/task/git. | `verimem/anti_confabulation.py:384` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_has_tracker_ref\b`, non `_has_tracker_ref(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/anti_confabulation.py:384`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 12 | `verimem/anti_confabulation.py:368` `detect_unsupported_task_state_claim` | funzione: L1.7 anti-confabulation warning for task-state claims. | `verimem/anti_confab_gate.py:58`; `verimem/anti_confab_gate.py:1466`; `verimem/anti_confabulation.py:471` (+5) | `tests/test_anti_confabulation_task_state.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 13 | `verimem/anti_confabulation.py:420` `scan_orphaned_facts` | funzione: Scan a corpus of facts and return ones that would trigger an | `verimem/anti_confabulation.py:408`; `verimem/anti_confabulation.py:480`; `verimem/anti_confabulation.py:497` (+9) | `tests/test_anti_confabulation_reconciler.py`; `tests/test_cli_facts.py`; `tests/test_mcp_anti_confab_scan.py` (+2) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 14 | `verimem/anti_confabulation.py:479` `summarize_scan` | funzione: Render a one-line summary of a ``scan_orphaned_facts`` report. | `verimem/anti_confabulation.py:498`; `verimem/cli.py:4229`; `verimem/cli.py:4235` (+2) | `tests/test_anti_confabulation_reconciler.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
