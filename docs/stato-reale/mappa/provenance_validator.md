# verimem/provenance_validator.py — mappa

**Owner**: ws4 (ML Ferro) · **376 righe · 9 fra funzioni, metodi e classi**.

Valida la PROVENIENZA di un fatto: da dove viene e se quel dove regge.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                9 / 9
  con un verdetto                                        6
     «i test che la nominano passano»                    6
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           3
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `provenance_validator.py` **nessuna
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

# Mappa di `verimem/provenance_validator.py` — 9 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/provenance_validator.py:131` `_verify_file_ref` | funzione: Return True iff ``ref`` is ``file:<path>:<lineno>`` AND the path | `verimem/provenance_validator.py:279`; `verimem/provenance_validator.py:316` | `tests/test_content_pin.py`; `tests/test_provenance_absolute_path_traversal.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 2 | `verimem/provenance_validator.py:199` `_verify_commit_ref` | funzione: Return True iff ``ref`` is ``commit <hex6-40>`` AND | `verimem/provenance_validator.py:238`; `verimem/provenance_validator.py:318` | `tests/test_windows_no_console_popup.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 3 | `verimem/provenance_validator.py:235` `_git_sha_exists` | funzione: True iff ``sha`` (bare hex) is a real commit in ``repo_root``. | `verimem/provenance_validator.py:277` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_git_sha_exists\b`, non `_git_sha_exists(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/provenance_validator.py:277`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 4 | `verimem/provenance_validator.py:258` `evidence_ref_exists` | funzione: True iff ``ref`` is an existence-verifiable evidence ref that ACTUALLY | `verimem/provenance_validator.py:295`; `verimem/provenance_validator.py:373` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\bevidence_ref_exists\b`, non `evidence_ref_exists(`, che non vedrebbe i riferimenti passati come callback) → **2 riferimenti**, i primi `verimem/provenance_validator.py:295`; `verimem/provenance_validator.py:373`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 5 | `verimem/provenance_validator.py:285` `any_evidence_ref_exists` | funzione: True iff at least one ref in ``refs`` is existence-verifiable AND exists. | `verimem/anti_confab_gate.py:2118`; `verimem/anti_confab_gate.py:2119`; `verimem/provenance_validator.py:374` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\bany_evidence_ref_exists\b`, non `any_evidence_ref_exists(`, che non vedrebbe i riferimenti passati come callback) → **3 riferimenti**, i primi `verimem/anti_confab_gate.py:2118`; `verimem/anti_confab_gate.py:2119`; `verimem/provenance_validator.py:374`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 6 | `verimem/provenance_validator.py:299` `is_valid_provenance_ref` | funzione: Return True iff ``ref`` matches one of the two verifiable forms | `verimem/provenance_validator.py:80`; `verimem/provenance_validator.py:84`; `verimem/provenance_validator.py:282` (+5) | `tests/test_provenance_commit_ref_format.py`; `tests/test_verified_by_validation.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 7 | `verimem/provenance_validator.py:323` `validate_verified_refs` | funzione: Return True iff ``refs`` is non-empty AND at least one ref passes | `verimem/provenance_validator.py:76`; `verimem/provenance_validator.py:305`; `verimem/provenance_validator.py:370` (+2) | `tests/test_adversarial_guarantees.py`; `tests/test_provenance_commit_ref_format.py`; `tests/test_store_trusted_provenance_spoof.py` (+1) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 8 | `verimem/provenance_validator.py:335` `validate_provisional_refs` | funzione: Return True iff ``refs`` is non-empty AND at least one ref matches | `verimem/provenance_validator.py:78`; `verimem/provenance_validator.py:371`; `verimem/semantic.py:81` (+1) | `tests/test_verified_by_validation.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 9 | `verimem/provenance_validator.py:355` `invalid_provenance_refs` | funzione: Return the subset of ``refs`` that fail | `verimem/provenance_validator.py:83`; `verimem/provenance_validator.py:372` | `tests/test_verified_by_validation.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
