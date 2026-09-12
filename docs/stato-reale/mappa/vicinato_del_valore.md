# verimem/vicinato_del_valore.py — mappa

**Owner**: ws4 (ML Ferro) · **320 righe · 6 fra funzioni, metodi e classi**.

Il contesto attorno a un numero: che cosa lo qualifica.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                6 / 6
  con un verdetto                                        4
     «i test che la nominano passano»                    2
     idem, entro un limite DICHIARATO (xfail nei test)   2
  NON MISURATO                                           2
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `vicinato_del_valore.py` **nessuna
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

# Mappa di `verimem/vicinato_del_valore.py` — 6 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/vicinato_del_valore.py:83` `ValoreRiusato` | classe: Un valore che la fonte contiene, ma riferito a un'altra grandezza. | `verimem/vicinato_del_valore.py:77`; `verimem/vicinato_del_valore.py:277`; `verimem/vicinato_del_valore.py:287` (+1) | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\bValoreRiusato\b`, non `ValoreRiusato(`, che non vedrebbe i riferimenti passati come callback) → **4 riferimenti**, i primi `verimem/vicinato_del_valore.py:77`; `verimem/vicinato_del_valore.py:277`; `verimem/vicinato_del_valore.py:287`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 2 | `verimem/vicinato_del_valore.py:97` `_vicinato_grezzo` | funzione: (nessun docstring) | `verimem/vicinato_del_valore.py:144`; `verimem/vicinato_del_valore.py:145`; `verimem/vicinato_del_valore.py:154` (+1) | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_vicinato_grezzo\b`, non `_vicinato_grezzo(`, che non vedrebbe i riferimenti passati come callback) → **4 riferimenti**, i primi `verimem/vicinato_del_valore.py:144`; `verimem/vicinato_del_valore.py:145`; `verimem/vicinato_del_valore.py:154`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 3 | `verimem/vicinato_del_valore.py:101` `_intorno` | funzione: Le parole DI CONTENUTO vicine a ogni occorrenza del numero. | `verimem/vicinato_del_valore.py:298`; `verimem/vicinato_del_valore.py:299` | `tests/test_l42_avvisa_falsamente_sugli_output_di_programma.py` | - | **FUNZIONA COME PROMESSO** *(entro un limite DICHIARATO)* | batch 08/09 21:15, 48 file: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ Fra i test che la nominano ce n'è almeno uno con un **marker `xfail`**, cioè un difetto vivo messo sotto presidio invece che nascosto: `tests/test_l42_avvisa_falsamente_sugli_output_di_programma.py`. **Il verde qui non copre quel caso**, che resta noto e presidiato. Livello: i test che la nominano passano — non «fa ciò che il docstring promette», che va misurato a parte |
| 4 | `verimem/vicinato_del_valore.py:174` `_prefissi` | funzione: Le flessioni non cambiano la grandezza: «exits»/«exit», «strumenti»/«strumento». | `verimem/vicinato_del_valore.py:302`; `verimem/vicinato_del_valore.py:304`; `verimem/vicinato_del_valore.py:309` | `tests/test_la_ricevuta_non_diceva_quale_cifra_mancava.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 5 | `verimem/vicinato_del_valore.py:230` `_da_mostrare` | funzione: Il contesto da mostrare nella ricevuta, col lato DICHIARATO. | `verimem/vicinato_del_valore.py:316`; `verimem/vicinato_del_valore.py:317` | `tests/test_la_ricevuta_di_L42_mostrava_meta_di_cio_che_decideva.py`; `tests/test_la_ricevuta_di_L42_non_mostra_parole_vuote.py`; `tests/test_un_ausiliare_italiano_non_e_una_grandezza.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 6 | `verimem/vicinato_del_valore.py:275` `valori_riusati_da_altro_contesto` | funzione: I valori del claim che la fonte contiene, ma riferiti ad altro. | `verimem/anti_confab_gate.py:2767`; `verimem/anti_confab_gate.py:2769`; `verimem/anti_confab_gate.py:2770` (+1) | `tests/test_il_numero_c_e_ma_parla_d_altro.py`; `tests/test_l42_avvisa_falsamente_sugli_output_di_programma.py`; `tests/test_la_ricevuta_di_L42_mostrava_meta_di_cio_che_decideva.py` (+1) | - | **FUNZIONA COME PROMESSO** *(entro un limite DICHIARATO)* | batch 08/09 21:15, 48 file: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ Fra i test che la nominano ce n'è almeno uno con un **marker `xfail`**, cioè un difetto vivo messo sotto presidio invece che nascosto: `tests/test_l42_avvisa_falsamente_sugli_output_di_programma.py`. **Il verde qui non copre quel caso**, che resta noto e presidiato. Livello: i test che la nominano passano — non «fa ciò che il docstring promette», che va misurato a parte |
