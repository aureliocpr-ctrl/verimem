# verimem/ann_cache.py — mappa

**Owner**: ws4 (ML Ferro) · **112 righe · 5 fra funzioni, metodi e classi**.

ANNCache tiene vivo UN indice HNSW fra le chiamate di recall: costruirlo costa ~52 s a 100k, quindi si costruisce una volta e si riusa. Sotto la soglia (100.000, in ann_gate.py) il recall resta la forza bruta esatta.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                5 / 5
  con un verdetto                                        4
     «i test che la nominano passano»                    4
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           1
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `ann_cache.py` **nessuna
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

# Mappa di `verimem/ann_cache.py` — 5 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/ann_cache.py:34` `ANNCache` | classe: (nessun docstring) | `verimem/ann_cache.py:1`; `verimem/ann_gate.py:38`; `verimem/semantic.py:2764` (+4) | `tests/test_ann_background_build.py`; `tests/test_ann_cache.py`; `tests/test_uno_store_piccolo_non_carica_faiss.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **284 passed, 1 skipped, 23 warnings in 239.58s (0:03:59)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 2 | `verimem/ann_cache.py:35` `ANNCache.__init__` | funzione: (nessun docstring) | `verimem/_compat.py:27`; `verimem/client.py:355`; `verimem/document_index.py:255` (+11) | `tests/perf/seed_data.py`; `tests/security/test_pentest_validation.py`; `tests/test_abstention_hybrid.py` (+265) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **284 passed, 1 skipped, 23 warnings in 239.58s (0:03:59)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 3 | `verimem/ann_cache.py:48` `ANNCache._spawn_build` | funzione: Start at most ONE background builder for (matrix snapshot, version), | `verimem/ann_cache.py:97` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_spawn_build\b`, non `_spawn_build(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/ann_cache.py:97`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 4 | `verimem/ann_cache.py:61` `ANNCache._spawn_build._run` | funzione: (nessun docstring) | `verimem/ann_cache.py:74`; `verimem/flow_events.py:311`; `verimem/preload.py:354` (+2) | `tests/test_airgap_live_probe.py`; `tests/test_bench_compare.py`; `tests/test_doctor_reports_moat_coverage.py` (+11) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **284 passed, 1 skipped, 23 warnings in 239.58s (0:03:59)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 5 | `verimem/ann_cache.py:77` `ANNCache.query_pool` | funzione: Return top-(k*oversample) candidate indices via the cached ANN, or | `verimem/ann_cache.py:12`; `verimem/ann_cache.py:17`; `verimem/semantic.py:4204` (+2) | `tests/test_ann_background_build.py`; `tests/test_ann_cache.py`; `tests/test_corpus_cache_cross_process_generation.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **284 passed, 1 skipped, 23 warnings in 239.58s (0:03:59)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
