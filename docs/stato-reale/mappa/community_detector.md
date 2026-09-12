# verimem/community_detector.py — mappa

**Owner**: ws4 (ML Ferro) · **276 righe · 5 fra funzioni, metodi e classi**.

Louvain sul grafo dei fatti: i sotto-grafi densi («canali»). Difensivo per costruzione — DB mancante, grafo vuoto o errore SQL danno risultato vuoto, mai un'eccezione.

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
Ogni riga porta il proprio livello scritto per esteso. Su `community_detector.py` **nessuna
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

# Mappa di `verimem/community_detector.py` — 5 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/community_detector.py:49` `_sibling_episodes_db` | funzione: Convention: ``~/.engram/semantic/semantic.db`` -> | `verimem/community_detector.py:167`; `verimem/entity_populate.py:39` | `tests/causal_fixture_helper.py`; `tests/test_second_pass_louvain.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **284 passed, 1 skipped, 23 warnings in 239.58s (0:03:59)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 2 | `verimem/community_detector.py:56` `_empty_result` | funzione: (nessun docstring) | `verimem/community_detector.py:230`; `verimem/community_detector.py:235`; `verimem/community_detector.py:238` (+2) | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_empty_result\b`, non `_empty_result(`, che non vedrebbe i riferimenti passati come callback) → **5 riferimenti**, i primi `verimem/community_detector.py:230`; `verimem/community_detector.py:235`; `verimem/community_detector.py:238`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 3 | `verimem/community_detector.py:65` `_load_graph` | funzione: Build an undirected networkx graph from semantic.db. | `verimem/community_detector.py:52`; `verimem/community_detector.py:233`; `verimem/highway_nodes.py:10` (+12) | `tests/test_community_causal_edges.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **284 passed, 1 skipped, 23 warnings in 239.58s (0:03:59)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 4 | `verimem/community_detector.py:156` `_project_causal_edges` | funzione: Read episode->episode causal_edges and project them onto the | `verimem/community_detector.py:150` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_project_causal_edges\b`, non `_project_causal_edges(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/community_detector.py:150`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 5 | `verimem/community_detector.py:198` `detect_communities` | funzione: Detect communities (densely-connected sub-graphs) in the fact graph. | `verimem/community_detector.py:276`; `verimem/dream_community_hook.py:16`; `verimem/dream_community_hook.py:22` (+10) | `tests/test_auto_dream_stable_partition_envvar.py`; `tests/test_community_causal_edges.py`; `tests/test_community_detector.py` (+2) | - | **FUNZIONA COME PROMESSO** — 4 rami su 4 | eseguita 09/09 12:20 sui tre rami difensivi che il docstring dichiara («missing DB / empty graph / SQL error → empty result, **never raises**»): DB inesistente → `n_communities=0, modularity=0.0` · **file che non è un database** (SQL error) → `n_communities=0` · DB sqlite valido ma senza fatti → `n_communities=0`. **Nessuno dei tre solleva.** Più il determinismo che promette il parametro `seed`: due chiamate con `seed=42` danno esito **identico** |
