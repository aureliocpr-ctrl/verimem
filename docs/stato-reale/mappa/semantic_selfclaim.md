# verimem/semantic_selfclaim.py — mappa

**Owner**: ws4 (ML Ferro) · **408 righe · 13 fra funzioni, metodi e classi**.

Il rilevatore semantico delle auto-affermazioni: «funziona», «verificato», senza prova.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                13 / 13
  con un verdetto                                        7
     «i test che la nominano passano»                    7
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           5
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `semantic_selfclaim.py` **nessuna
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

# Mappa di `verimem/semantic_selfclaim.py` — 13 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/semantic_selfclaim.py:192` `_looks_negated` | funzione: True when the claim contains a real negation (honest failure report), | `verimem/semantic_selfclaim.py:376` | `tests/test_l120_multilingual_selfclaim.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 2 | `verimem/semantic_selfclaim.py:218` `_looks_reported` | funzione: True when the claim is ATTRIBUTED to someone else (reported speech). | `verimem/anti_confab_gate.py:1417`; `verimem/anti_confab_gate.py:1420`; `verimem/semantic_selfclaim.py:378` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_looks_reported\b`, non `_looks_reported(`, che non vedrebbe i riferimenti passati come callback) → **3 riferimenti**, i primi `verimem/anti_confab_gate.py:1417`; `verimem/anti_confab_gate.py:1420`; `verimem/semantic_selfclaim.py:378`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 3 | `verimem/semantic_selfclaim.py:229` `_is_exemplar_text` | funzione: True se ``t`` è un esemplare HYPE (al netto del prefisso e5). | nessuno trovato | `tests/test_l120_e_un_avviso_non_un_veto.py`; `tests/test_l120_multilingual_selfclaim.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 4 | `verimem/semantic_selfclaim.py:235` `_is_anchor_text` | funzione: True se ``t`` è un'àncora fattuale (al netto del prefisso e5). | nessuno trovato | nessuno | - | MAI CHIAMATA (candidata: nessun chiamante ne' test trovato) | - |
| 5 | `verimem/semantic_selfclaim.py:241` `_active_model` | funzione: (nessun docstring) | `verimem/semantic.py:3567`; `verimem/semantic.py:3573`; `verimem/semantic.py:3606` (+6) | `tests/test_l120_multilingual_selfclaim.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 6 | `verimem/semantic_selfclaim.py:246` `_ColdEncoderDeclined` | classe: Raised by the production default encoder when encoding a proposition would | `verimem/semantic_selfclaim.py:302` | `tests/test_l120_si_disarma_quando_il_daemon_c_e.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 7 | `verimem/semantic_selfclaim.py:252` `_default_encode` | funzione: Production encoder for L1.20 — ``verimem.embedding.encode``, GUARDED so the | `verimem/semantic_selfclaim.py:385` | `tests/test_l120_e_un_avviso_non_un_veto.py`; `tests/test_l120_multilingual_selfclaim.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 8 | `verimem/semantic_selfclaim.py:298` `_default_encode._guarded` | funzione: (nessun docstring) | `verimem/semantic_selfclaim.py:307` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_guarded\b`, non `_guarded(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/semantic_selfclaim.py:307`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 9 | `verimem/semantic_selfclaim.py:310` `_prefixes` | funzione: (query_prefix, passage_prefix) per il modello attivo — replica il | `verimem/semantic_selfclaim.py:344`; `verimem/semantic_selfclaim.py:387` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_prefixes\b`, non `_prefixes(`, che non vedrebbe i riferimenti passati come callback) → **2 riferimenti**, i primi `verimem/semantic_selfclaim.py:344`; `verimem/semantic_selfclaim.py:387`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 10 | `verimem/semantic_selfclaim.py:319` `_thresholds` | funzione: Soglie effettive, o None se il detector deve disarmarsi. | `verimem/semantic_selfclaim.py:380` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_thresholds\b`, non `_thresholds(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/semantic_selfclaim.py:380`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 11 | `verimem/semantic_selfclaim.py:338` `_matrices` | funzione: Esemplari/àncore encodate una volta (lazy, thread-safe). | `verimem/semantic_selfclaim.py:386` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_matrices\b`, non `_matrices(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/semantic_selfclaim.py:386`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 12 | `verimem/semantic_selfclaim.py:353` `_reset_matrices_for_tests` | funzione: (nessun docstring) | nessuno trovato | `tests/test_l120_e_un_avviso_non_un_veto.py`; `tests/test_l120_multilingual_selfclaim.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 13 | `verimem/semantic_selfclaim.py:359` `detect_semantic_selfclaim` | funzione: Dual-check semantico multilingue. Ritorna il warning L1.20 o None. | `verimem/anti_confab_gate.py:1686`; `verimem/anti_confab_gate.py:1687` | `tests/test_l120_multilingual_selfclaim.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
