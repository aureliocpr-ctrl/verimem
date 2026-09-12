# verimem/valore_non_nella_fonte.py — mappa

**Owner**: ws4 (ML Ferro) · **346 righe · 8 fra funzioni, metodi e classi**.

Il controllo DETERMINISTICO claim-fonte che al gate mancava: il valore che il claim afferma e la fonte non contiene. Nasce da una classe misurata — i claim che inventano un DETTAGLIO su un'entita VERA entravano 5 su 5 con g 97,1-99,5, mentre quelli che inventano un'entita erano fermati 0 su 4.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                8 / 8
  con un verdetto                                        0
     «i test che la nominano passano»                    0
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           5
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `valore_non_nella_fonte.py` **nessuna
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

# Mappa di `verimem/valore_non_nella_fonte.py` — 8 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/valore_non_nella_fonte.py:59` `_numeri_come_scritti` | funzione: ``{valore: il numero COM'E' SCRITTO}`` per i numeri del claim. | `verimem/valore_non_nella_fonte.py:303` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_numeri_come_scritti\b`, non `_numeri_come_scritti(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/valore_non_nella_fonte.py:303`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 2 | `verimem/valore_non_nella_fonte.py:86` `ValoreAssente` | classe: Un valore che il claim afferma e la fonte non contiene. | `verimem/valore_non_nella_fonte.py:56`; `verimem/valore_non_nella_fonte.py:112`; `verimem/valore_non_nella_fonte.py:244` (+3) | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\bValoreAssente\b`, non `ValoreAssente(`, che non vedrebbe i riferimenti passati come callback) → **6 riferimenti**, i primi `verimem/valore_non_nella_fonte.py:56`; `verimem/valore_non_nella_fonte.py:112`; `verimem/valore_non_nella_fonte.py:244`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 3 | `verimem/valore_non_nella_fonte.py:115` `ValoreAssente.come_scritto` | funzione: Il numero da mostrare a chi legge: il suo, se ce l'abbiamo. | `verimem/anti_confab_gate.py:2730`; `verimem/anti_confab_gate.py:2743`; `verimem/anti_confab_gate.py:2753` | `tests/test_il_claim_e_la_fonte_leggono_lo_stesso_numero.py`; `tests/test_il_gate_certificava_un_numero_falso_di_mille_volte.py`; `tests/test_lo_span_spende_il_budget.py` (+2) | - | **FUNZIONA COME PROMESSO** | eseguita 08/09 23:10 dentro i casi sopra: restituisce il numero **come il claim lo scrive** (`'40'`, `'1200'`, `'500'`), che è ciò che va mostrato a chi legge la ricevuta invece del float normalizzato |
| 4 | `verimem/valore_non_nella_fonte.py:128` `_tolleranza_dichiarata` | funzione: ±mezza unità dell'ultima cifra che il claim SCRIVE. | `verimem/valore_non_nella_fonte.py:315` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_tolleranza_dichiarata\b`, non `_tolleranza_dichiarata(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/valore_non_nella_fonte.py:315`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 5 | `verimem/valore_non_nella_fonte.py:193` `_dichiara_un_assenza` | funzione: La fonte nega esplicitamente una quantità? | `verimem/valore_non_nella_fonte.py:301` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_dichiara_un_assenza\b`, non `_dichiara_un_assenza(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/valore_non_nella_fonte.py:301`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 6 | `verimem/valore_non_nella_fonte.py:233` `_valori_da_token_che_la_fonte_contiene` | funzione: I valori che il lato claim estrae da token presenti verbatim nella fonte. | `verimem/l1_completion_detector.py:188`; `verimem/valore_non_nella_fonte.py:306` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_valori_da_token_che_la_fonte_contiene\b`, non `_valori_da_token_che_la_fonte_contiene(`, che non vedrebbe i riferimenti passati come callback) → **2 riferimenti**, i primi `verimem/l1_completion_detector.py:188`; `verimem/valore_non_nella_fonte.py:306`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 7 | `verimem/valore_non_nella_fonte.py:244` `valori_non_nella_fonte` | funzione: I valori numerici del claim che nella fonte non compaiono. | `verimem/anti_confab_gate.py:2712`; `verimem/anti_confab_gate.py:2714`; `verimem/valore_non_nella_fonte.py:56` (+2) | `tests/test_grad_3_era_invisibile_e_il_fatto_vero_cadeva.py`; `tests/test_il_claim_e_la_fonte_leggono_lo_stesso_numero.py`; `tests/test_il_gate_certificava_un_numero_falso_di_mille_volte.py` (+10) | - | **FUNZIONA COME PROMESSO** — 5 casi su 5 | eseguita 08/09 23:10 con `env -u`, **sui casi che il docstring stesso nomina** (il modulo nasce da una classe misurata: i claim che inventano un DETTAGLIO su un'entità VERA entravano **5 su 5** con g 97,1-99,5, mentre quelli che inventano un'entità venivano fermati 0 su 4). (1) `"L'ordine 77 conteneva 40 pezzi."` contro una fonte che nomina l'ordine 77 → `['40']`: **trova il dettaglio inventato e NON il numero dell'entità**, che è esattamente la promessa «si confrontano i VALORI, non le coppie (unità, valore)» · (2) `"…vale 1200 euro."` → `['1200']` · (3) claim senza valori nuovi → `[]` · (4) **la tolleranza cura il falso positivo che il docstring racconta**: fonte `durata 443.0485324859619`, claim `443 secondi` → `[]`, ma `500 secondi` → `['500']` — tollera il troncamento senza ammettere ciò che non c'è · (5) senza uno dei due testi → `[]`, «inventarsi un verdetto è esattamente ciò che questo modulo esiste per impedire» · controllo negativo: valore presente nella fonte → `[]` |
| 8 | `verimem/valore_non_nella_fonte.py:323` `assenti_che_la_fonte_scrive_a_parole` | funzione: Quali fra i valori «assenti» la fonte porta scritti a PAROLE. | `verimem/anti_confab_gate.py:2711`; `verimem/anti_confab_gate.py:2727` | `tests/test_un_numero_che_la_fonte_scrive_a_parole.py` | - | **FUNZIONA COME PROMESSO** | eseguita 08/09 23:10: claim `40 pezzi` contro fonte `quaranta pezzi` → l'assente `['40']` viene riconosciuto come scritto a parole. ⚠️ Il docstring dichiara che **serve a DECLASSARE, mai ad ammettere** (il chiamante lo sposta da veto ad avviso e il fatto entra CON l'avviso): questa misura verifica il riconoscimento, **non** che il chiamante lo usi così — quello sta in `anti_confab_gate.py:1897` e non l'ho letto |
