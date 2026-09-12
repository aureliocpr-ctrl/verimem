# verimem/symbolic_inference.py — mappa

**Owner**: ws4 (ML Ferro) · **137 righe · 5 fra funzioni, metodi e classi**.

Il ponte simbolico-neurale: deduzioni a costo zero su fatti a forma di regola, in avanti e senza chiamare un LLM. Deliberatamente semplice — non un interprete Prolog.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                5 / 5
  con un verdetto                                        1
     «i test che la nominano passano»                    1
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           2
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `symbolic_inference.py` **nessuna
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

# Mappa di `verimem/symbolic_inference.py` — 5 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/symbolic_inference.py:35` `parse_rule` | funzione: Return {antecedent, consequent} if proposition is a rule. | `verimem/mcp_server.py:10496`; `verimem/mcp_server.py:10507`; `verimem/symbolic_inference.py:85` (+1) | `tests/test_symbolic_inference.py` | - | **FUNZIONA COME PROMESSO** — 6 pattern su 6 | eseguita 09/09 12:14 con `env -u`, sui **sei pattern che il docstring elenca**: `A -> B` · `A => B` · `If A then B` · `A implies B` · `When A, B` · `A → B` (freccia unicode) → tutti danno `{'antecedent': 'A', 'consequent': 'B'}`. Controllo negativo, 3 su 3: `'Il gate ha ammesso 233 scritture.'`, `'A e B'` e la stringa vuota → `None` |
| 2 | `verimem/symbolic_inference.py:52` `_antecedent_in_facts` | funzione: Return the fact whose proposition contains the antecedent as a whole-word, | `verimem/symbolic_inference.py:102` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_antecedent_in_facts\b`, non `_antecedent_in_facts(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/symbolic_inference.py:102`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 3 | `verimem/symbolic_inference.py:74` `forward_chain` | funzione: Forward-chain rules against state facts up to max_depth layers. | `verimem/fact_chain.py:7`; `verimem/mcp_server.py:10495`; `verimem/mcp_server.py:10517` (+1) | `tests/test_fact_chain.py`; `tests/test_il_vincitore_che_ne_ingoio_dodici.py`; `tests/test_symbolic_inference.py` (+1) | - | 🔴 **NON COME PROMESSO** *(il caso base regge, il limite no)* | eseguita 09/09 12:17. **Caso base OK**: regola `If il varco e' aperto then il varco e' insicuro` + stato `il varco e' aperto` → `il varco e' insicuro`, `evidence_id: s1`; senza lo stato, nessuna deduzione. **MA il `max_depth` non limita la lunghezza della catena**, e l'esito dipende dall'ORDINE delle regole — predizione scritta prima ed eseguita:<br>`ORDINE  (r1,r2) max_depth=1 → ['B','C']  max_depth_reached=1`<br>`INVERSO (r2,r1) max_depth=1 → ['B']       max_depth_reached=1`<br>`INVERSO (r2,r1) max_depth=5 → ['B','C']   max_depth_reached=2`<br>**Causa letta**: il ciclo esterno conta i layer, ma quello interno scorre tutte le regole e le deduzioni entrano in `known_pool` **dentro lo stesso giro**, quindi `r2` vede subito ciò che ha dedotto `r1`. Il commento dell'autore dice «Add as known for **next-layer** chaining»: si aspettava il layer successivo. Anche il campo `depth` lo riflette — `C` esce con `depth: 1` pur venendo da `inferred_r1`. ⚠️ **Precisazione onesta**: il docstring dice solo «depth limit (default 5)» e non definisce cosa sia un *depth*; il codice fa una cosa difendibile (fixpoint parziale per giro). Il difetto è che **il parametro non fa ciò che il suo nome e il commento suggeriscono, e l'esito dipende da un dato che il chiamante spesso non controlla**. Numero T e owner: chiesti al lead, non aperti da me |
| 4 | `verimem/symbolic_inference.py:116` `forward_chain._Inferred` | classe: (nessun docstring) | `verimem/symbolic_inference.py:123` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_Inferred\b`, non `_Inferred(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/symbolic_inference.py:123`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 5 | `verimem/symbolic_inference.py:117` `forward_chain._Inferred.__init__` | funzione: (nessun docstring) | `verimem/_compat.py:27`; `verimem/client.py:355`; `verimem/document_index.py:255` (+11) | `tests/perf/seed_data.py`; `tests/security/test_pentest_validation.py`; `tests/test_abstention_hybrid.py` (+265) | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **284 passed, 1 skipped, 23 warnings in 239.58s (0:03:59)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
