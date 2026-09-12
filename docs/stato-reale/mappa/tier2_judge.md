# verimem/tier2_judge.py — mappa

**Owner**: ws4 (ML Ferro) · **338 righe · 13 fra funzioni, metodi e classi**.

Il giudice di secondo livello, dopo i layer lessicali.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                13 / 13
  con un verdetto                                        12
     «i test che la nominano passano»                    12
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           1
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `tier2_judge.py` **nessuna
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

# Mappa di `verimem/tier2_judge.py` — 13 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/tier2_judge.py:50` `JudgeAction` | classe: What the Tier-2 judge recommends for an ambiguous claim. | `verimem/tier2_judge.py:63`; `verimem/tier2_judge.py:128`; `verimem/tier2_judge.py:149` (+6) | `tests/test_llm_judge.py`; `tests/test_tier2_judge.py`; `tests/test_triage_corpus.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 2 | `verimem/tier2_judge.py:59` `JudgeVerdict` | classe: A judge's triage opinion. ``confidence`` is the judge's OWN confidence | `verimem/tier2_judge.py:79`; `verimem/tier2_judge.py:87`; `verimem/tier2_judge.py:91` (+9) | `tests/test_tier2_judge.py`; `tests/test_triage_corpus.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 3 | `verimem/tier2_judge.py:69` `Judge` | classe: Pluggable Tier-2 judge. | `verimem/client.py:1923`; `verimem/client.py:2246`; `verimem/client.py:4270` (+10) | `tests/test_abstention_hybrid.py`; `tests/test_all_write_channels_judge_a_source.py`; `tests/test_llm_judge.py` (+3) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 4 | `verimem/tier2_judge.py:77` `Judge.judge` | funzione: (nessun docstring) | `verimem/_telemetry_prefixes.py:70`; `verimem/adjudication_log.py:5`; `verimem/adjudication_log.py:35` (+445) | `tests/_real_model.py`; `tests/conftest.py`; `tests/security/test_no_dangerous_sinks.py` (+97) | `README.md:10`; `README.md:11`; `README.md:14` | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 5 | `verimem/tier2_judge.py:84` `FixedJudge` | classe: Hermetic stub: always returns ``verdict``. For pipeline tests. | `verimem/tier2_judge.py:97`; `verimem/tier2_judge.py:331` | `tests/test_tier2_judge.py`; `tests/test_triage_corpus.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 6 | `verimem/tier2_judge.py:89` `FixedJudge.judge` | funzione: (nessun docstring) | `verimem/_telemetry_prefixes.py:70`; `verimem/adjudication_log.py:5`; `verimem/adjudication_log.py:35` (+445) | `tests/_real_model.py`; `tests/conftest.py`; `tests/security/test_no_dangerous_sinks.py` (+97) | `README.md:10`; `README.md:11`; `README.md:14` | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 7 | `verimem/tier2_judge.py:96` `RecordingJudge` | classe: Like :class:`FixedJudge` but records every call as ``(proposition, | `verimem/tier2_judge.py:332` | `tests/test_tier2_judge.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 8 | `verimem/tier2_judge.py:105` `RecordingJudge.judge` | funzione: (nessun docstring) | `verimem/_telemetry_prefixes.py:70`; `verimem/adjudication_log.py:5`; `verimem/adjudication_log.py:35` (+445) | `tests/_real_model.py`; `tests/conftest.py`; `tests/security/test_no_dangerous_sinks.py` (+97) | `README.md:10`; `README.md:11`; `README.md:14` | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 9 | `verimem/tier2_judge.py:125` `LLMJudge` | classe: Concrete Tier-2 judge backed by an injected LLM (subscription/CLI — no external | `verimem/sleep.py:1122`; `verimem/sleep.py:1123`; `verimem/tier2_judge.py:333` | `tests/test_llm_judge.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 10 | `verimem/tier2_judge.py:135` `LLMJudge.judge` | funzione: (nessun docstring) | `verimem/_telemetry_prefixes.py:70`; `verimem/adjudication_log.py:5`; `verimem/adjudication_log.py:35` (+445) | `tests/_real_model.py`; `tests/conftest.py`; `tests/security/test_no_dangerous_sinks.py` (+97) | `README.md:10`; `README.md:11`; `README.md:14` | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 11 | `verimem/tier2_judge.py:158` `TrustDecision` | classe: Outcome of :func:`assess_claim_trust` for a single fact. | `verimem/tier2_judge.py:189`; `verimem/tier2_judge.py:217`; `verimem/tier2_judge.py:220` (+7) | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\bTrustDecision\b`, non `TrustDecision(`, che non vedrebbe i riferimenti passati come callback) → **10 riferimenti**, i primi `verimem/tier2_judge.py:189`; `verimem/tier2_judge.py:217`; `verimem/tier2_judge.py:220`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 12 | `verimem/tier2_judge.py:179` `assess_claim_trust` | funzione: Decide how much to trust ``fact`` by composing the three layers. | `verimem/semantic.py:5633`; `verimem/tier2_judge.py:15`; `verimem/tier2_judge.py:159` (+3) | `tests/test_tier2_judge.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 13 | `verimem/tier2_judge.py:270` `triage_corpus` | funzione: Consolidation-time Tier-2 triage over the live corpus's ambiguous bucket. | `verimem/sleep.py:1122`; `verimem/sleep.py:1123`; `verimem/tier2_judge.py:336` | `tests/test_triage_corpus.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
