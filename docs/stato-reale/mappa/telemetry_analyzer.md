# verimem/telemetry_analyzer.py — mappa

**Owner**: ws4 (ML Ferro) · **256 righe · 5 fra funzioni, metodi e classi**.

Il registro MCP letto come rapporto per tool: quante chiamate, quanto lente. Puro e tollerante alle righe malformate, per girare anche su un log parzialmente corrotto.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                5 / 5
  con un verdetto                                        2
     «i test che la nominano passano»                    2
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           1
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `telemetry_analyzer.py` **nessuna
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

# Mappa di `verimem/telemetry_analyzer.py` — 5 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/telemetry_analyzer.py:22` `_percentile` | funzione: Linear-interpolation percentile (matches numpy.percentile default). | `verimem/briefing_stats.py:99`; `verimem/briefing_stats.py:100`; `verimem/telemetry_analyzer.py:232` (+3) | `tests/test_eval_retrieval_with_gt.py` | - | **FUNZIONA COME PROMESSO** — verificata contro un RIFERIMENTO ESTERNO | eseguita 09/09 12:18: il docstring promette «matches numpy.percentile», e su `[1,2,3,4,10,100]` i sette percentili **coincidono con `numpy.percentile` a meno di 1e-9**: p0 `1.0000` · p25 `2.2500` · p50 `3.5000` · p75 `8.5000` · p90 `55.0000` · p99 `95.5000` · p100 `100.0000`. **7 su 7.** È il caso migliore che si possa avere: una promessa falsificabile contro qualcosa che non abbiamo scritto noi |
| 2 | `verimem/telemetry_analyzer.py:44` `famiglia_esito` | funzione: L'esito ridotto alla sua famiglia, per poterlo CONTARE. | `verimem/telemetry_analyzer.py:187` | `tests/test_un_esito_e_un_etichetta_non_un_dato.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **284 passed, 1 skipped, 23 warnings in 239.58s (0:03:59)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 3 | `verimem/telemetry_analyzer.py:73` `_pid_di_suite` | funzione: I processi che hanno chiamato la sonda: sono suite, non utenti. | `verimem/telemetry_analyzer.py:174` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_pid_di_suite\b`, non `_pid_di_suite(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/telemetry_analyzer.py:174`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 4 | `verimem/telemetry_analyzer.py:99` `nome_leggibile` | funzione: Il nome come si vede in un rapporto: nessun carattere che sposti il | `verimem/cli.py:2006` | `tests/test_un_nome_non_puo_leggersi_al_contrario.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **284 passed, 1 skipped, 23 warnings in 239.58s (0:03:59)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 5 | `verimem/telemetry_analyzer.py:119` `analyze_audit_log` | funzione: Parse the JSONL audit log and return a per-tool aggregate. | `verimem/cli.py:2005`; `verimem/cli.py:2028` | `tests/test_la_latenza_dichiara_di_chi_e_sopravvissuto.py`; `tests/test_telemetry_analyzer.py`; `tests/test_un_esito_e_un_etichetta_non_un_dato.py` | - | **FUNZIONA COME PROMESSO** | eseguita 09/09 12:18 sul caso che il docstring dichiara — «pure (no side effects) and tolerant of malformed lines (skipped, not raised)»: log con **3 righe valide + 1 malformata + 1 vuota** → `total_calls: 3`, nessuna eccezione, e le latenze per tool calcolate (`a`: count 2, p50 20.0, max 30.0) |
