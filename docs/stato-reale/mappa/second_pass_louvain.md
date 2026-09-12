# verimem/second_pass_louvain.py — mappa

**Owner**: ws4 (ML Ferro) · **352 righe · 5 fra funzioni, metodi e classi**.

Seconda passata di clustering sulla comunità dei fatti.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                5 / 5
  con un verdetto                                        3
     «i test che la nominano passano»                    3
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           2
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `second_pass_louvain.py` **nessuna
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

# Mappa di `verimem/second_pass_louvain.py` — 5 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/second_pass_louvain.py:35` `_embeddings_for_ids` | funzione: Fetch embeddings as (k, 384) float32 array. Returns ``None`` on | `verimem/second_pass_louvain.py:87`; `verimem/second_pass_louvain.py:120`; `verimem/skill_emergence_detector.py:337` | `tests/test_skill_emergence_dim_r3.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 2 | `verimem/second_pass_louvain.py:75` `_cohesion_for_fact_ids` | funzione: Mean cosine of each row to the centroid for the given fact ids. | `verimem/second_pass_louvain.py:349` | `tests/test_second_pass_louvain.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 3 | `verimem/second_pass_louvain.py:100` `_reweight_subgraph_by_embedding` | funzione: Re-weight subgraph edges by embedding cosine similarity. | `verimem/second_pass_louvain.py:302`; `verimem/skill_emergence_detector.py:214`; `verimem/skill_emergence_detector.py:237` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_reweight_subgraph_by_embedding\b`, non `_reweight_subgraph_by_embedding(`, che non vedrebbe i riferimenti passati come callback) → **3 riferimenti**, i primi `verimem/second_pass_louvain.py:302`; `verimem/skill_emergence_detector.py:214`; `verimem/skill_emergence_detector.py:237`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 4 | `verimem/second_pass_louvain.py:138` `_louvain_on_subgraph` | funzione: Run Louvain on a subgraph. Returns list of communities (node-id | `verimem/second_pass_louvain.py:303`; `verimem/skill_emergence_detector.py:213`; `verimem/skill_emergence_detector.py:238` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_louvain_on_subgraph\b`, non `_louvain_on_subgraph(`, che non vedrebbe i riferimenti passati come callback) → **3 riferimenti**, i primi `verimem/second_pass_louvain.py:303`; `verimem/skill_emergence_detector.py:213`; `verimem/skill_emergence_detector.py:238`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 5 | `verimem/second_pass_louvain.py:165` `second_pass_louvain` | funzione: Run first-pass Louvain, then re-run on the master super-cluster. | `verimem/community_detector.py:89`; `verimem/second_pass_louvain.py:350`; `verimem/skill_emergence_detector.py:167` (+5) | `tests/test_community_causal_edges.py`; `tests/test_second_pass_louvain.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
