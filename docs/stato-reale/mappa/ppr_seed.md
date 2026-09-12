# verimem/ppr_seed.py — mappa

**Owner**: ws4 (ML Ferro) · **301 righe · 6 fra funzioni, metodi e classi**.

I semi del Personalized PageRank sul grafo dei fatti.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                6 / 6
  con un verdetto                                        2
     «i test che la nominano passano»                    2
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           4
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `ppr_seed.py` **nessuna
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

# Mappa di `verimem/ppr_seed.py` — 6 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/ppr_seed.py:41` `_token_resolve_enabled` | funzione: In lettura, chi decide se un token e' un'entita' e' lo STORE. | `verimem/ppr_seed.py:180`; `verimem/ppr_seed.py:181` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_token_resolve_enabled\b`, non `_token_resolve_enabled(`, che non vedrebbe i riferimenti passati come callback) → **2 riferimenti**, i primi `verimem/ppr_seed.py:180`; `verimem/ppr_seed.py:181`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 2 | `verimem/ppr_seed.py:82` `_seeds_resolved_from_tokens` | funzione: I token della query che lo STORE riconosce come entita' (max ``budget``), | `verimem/ppr_seed.py:75`; `verimem/ppr_seed.py:182` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_seeds_resolved_from_tokens\b`, non `_seeds_resolved_from_tokens(`, che non vedrebbe i riferimenti passati come callback) → **2 riferimenti**, i primi `verimem/ppr_seed.py:75`; `verimem/ppr_seed.py:182`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 3 | `verimem/ppr_seed.py:124` `_fact_count_of` | funzione: Quanti fatti linka un'entita'. Uno store che non sa rispondere manda il | `verimem/ppr_seed.py:119` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_fact_count_of\b`, non `_fact_count_of(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/ppr_seed.py:119`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 4 | `verimem/ppr_seed.py:137` `_fact_id_of` | funzione: Extract a fact id from a facts_ranked entry, tolerant to its shape | `verimem/ppr_seed.py:145`; `verimem/ppr_seed.py:205` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_fact_id_of\b`, non `_fact_id_of(`, che non vedrebbe i riferimenti passati come callback) → **2 riferimenti**, i primi `verimem/ppr_seed.py:145`; `verimem/ppr_seed.py:205`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 5 | `verimem/ppr_seed.py:149` `ppr_seeded_fact_ids` | funzione: Auto-seed entity-PPR from a free-text ``query`` → ranked fact-id list. | `verimem/ppr_seed.py:300`; `verimem/semantic.py:4953`; `verimem/semantic.py:4954` | `tests/test_fusion_quality_guards.py`; `tests/test_ppr_fusion_budget.py`; `tests/test_ppr_seed.py` (+1) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 6 | `verimem/ppr_seed.py:213` `fuse_dense_and_ppr` | funzione: RRF-fuse a dense ``(Fact, sim)`` hit list with N extra fact-id ranklists | `verimem/ppr_seed.py:250`; `verimem/ppr_seed.py:300`; `verimem/semantic.py:4953` (+1) | `tests/test_fusion_quality_guards.py`; `tests/test_fusion_score_honesty.py`; `tests/test_fusion_score_real_store.py` (+2) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
