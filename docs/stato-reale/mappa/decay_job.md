# verimem/decay_job.py — mappa

**Owner**: ws4 (ML Ferro) · **276 righe · 5 fra funzioni, metodi e classi**.

Il decadimento della confidenza con l'eta': new = max(floor, original * exp(-age / tau)), tau 30 giorni, mezza vita ~21. Nasce da un audit: «i fatti stagionati non perdono peso, sistema inerte».

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                5 / 5
  con un verdetto                                        2
     «i test che la nominano passano»                    2
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           2
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `decay_job.py` **nessuna
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

# Mappa di `verimem/decay_job.py` — 5 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/decay_job.py:56` `compute_decayed_confidence` | funzione: Return ``max(floor, original * exp(-age / tau))``. | `verimem/decay_job.py:197`; `verimem/decay_job.py:274` | `tests/test_decay_job.py` | - | **FUNZIONA COME PROMESSO** | eseguita 09/09 12:18 sulla formula che il docstring scrive, `new = max(floor, original * exp(-age / tau))`, `tau` 30 giorni, `floor` 0.05: 0 giorni → `1.000000` · **21 giorni → `0.496585`, cioè esattamente `exp(-21/30)`: la «mezza vita ~21» del docstring è verificata** · 30 giorni → `0.367879` · **3650 giorni → `0.050000`, dove `exp` puro darebbe `0.000000`: il `floor` morde** · età negativa → `1.0`, «clamped at zero» come dichiarato |
| 2 | `verimem/decay_job.py:89` `_connect` | funzione: (nessun docstring) | `verimem/_sqlite_pragma.py:47`; `verimem/cli.py:3140`; `verimem/cli.py:3189` (+185) | `tests/swarm/test_bridge.py`; `tests/swarm/test_integration_haiku.py`; `tests/swarm/test_lifecycle.py` (+44) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **284 passed, 1 skipped, 23 warnings in 239.58s (0:03:59)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 3 | `verimem/decay_job.py:104` `_changed` | funzione: Whether the decay produced a meaningful confidence delta. | `verimem/decay_job.py:203` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_changed\b`, non `_changed(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/decay_job.py:203`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 4 | `verimem/decay_job.py:109` `_ensure_last_decay_column` | funzione: Additive, idempotent migration: ``facts.last_decay_at`` (REAL, nullable). | `verimem/decay_job.py:168` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_ensure_last_decay_column\b`, non `_ensure_last_decay_column(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/decay_job.py:168`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 5 | `verimem/decay_job.py:124` `run_decay_pass` | funzione: Walk every fact, apply the decay formula, persist updates. | `verimem/decay_job.py:275`; `verimem/mcp_server.py:15102`; `verimem/mcp_server.py:15109` (+1) | `tests/test_decay_idempotent_r3.py`; `tests/test_decay_job.py`; `tests/test_flow_decay_dichiarato.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **284 passed, 1 skipped, 23 warnings in 239.58s (0:03:59)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
