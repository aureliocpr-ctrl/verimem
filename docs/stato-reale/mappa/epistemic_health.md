# verimem/epistemic_health.py — mappa

**Owner**: ws4 (ML Ferro) · **155 righe · 5 fra funzioni, metodi e classi**.

La salute epistemica del corpus in una manciata di numeri.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                5 / 5
  con un verdetto                                        5
     «i test che la nominano passano»                    5
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           0
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `epistemic_health.py` **nessuna
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

# Mappa di `verimem/epistemic_health.py` — 5 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/epistemic_health.py:29` `FactAudit` | classe: Per-fact epistemic verdict. ``grounded``/``fresh``/``contested`` are None when | `verimem/epistemic_health.py:68`; `verimem/epistemic_health.py:80`; `verimem/epistemic_health.py:84` (+1) | `tests/test_epistemic_health_score.py`; `tests/test_il_voto_non_include_cio_che_non_ha_misurato.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 2 | `verimem/epistemic_health.py:50` `_source_of` | funzione: Provenance text a fact was derived from, if any. Engram facts may carry it as | `verimem/client.py:3528`; `verimem/epistemic_health.py:74` | `tests/test_la_salute_epistemica_e_leggibile.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 3 | `verimem/epistemic_health.py:65` `audit_one` | funzione: Audit a single fact. ``grounder(source, proposition) -> score 0-100``. A fact with | `verimem/client.py:3546`; `verimem/client.py:3563`; `verimem/epistemic_health.py:149` (+1) | `tests/test_epistemic_health_score.py`; `tests/test_il_voto_non_include_cio_che_non_ha_misurato.py`; `tests/test_la_salute_epistemica_e_leggibile.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 4 | `verimem/epistemic_health.py:84` `health_report` | funzione: Aggregate per-fact audits into a corpus health report. Components are each in [0,1]; | `verimem/client.py:3546`; `verimem/client.py:3566`; `verimem/epistemic_health.py:151` (+1) | `tests/test_epistemic_health_score.py`; `tests/test_il_voto_non_include_cio_che_non_ha_misurato.py`; `tests/test_la_salute_epistemica_e_leggibile.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 5 | `verimem/epistemic_health.py:143` `audit_corpus` | funzione: Audit a list of facts and return the health report. The driver; ``facts`` is the | `verimem/admission_gate.py:250`; `verimem/admission_gate.py:334`; `verimem/epistemic_health.py:154` | `tests/test_admission_gate.py`; `tests/test_epistemic_health_score.py`; `tests/test_la_salute_epistemica_e_leggibile.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
