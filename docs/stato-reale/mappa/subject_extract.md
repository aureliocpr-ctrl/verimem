# verimem/subject_extract.py — mappa

**Owner**: ws4 (ML Ferro) · **340 righe · 6 fra funzioni, metodi e classi**.

Estrae il SOGGETTO di una frase: chi è che fa l'azione.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                6 / 6
  con un verdetto                                        4
     «i test che la nominano passano»                    4
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           2
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `subject_extract.py` **nessuna
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

# Mappa di `verimem/subject_extract.py` — 6 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/subject_extract.py:186` `subject_of` | funzione: Leading noun-phrase subject: tokens before the first finite-verb marker, | `verimem/anti_confab_gate.py:1269`; `verimem/anti_confab_gate.py:1273`; `verimem/anti_confab_gate.py:1279` (+7) | `tests/test_e_apostrofo_e_un_marcatore_di_verbo.py`; `tests/test_il_nome_proprio_conta_come_entita_solo_da_soggetto.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 2 | `verimem/subject_extract.py:207` `subject_head` | funzione: The head noun of the subject NP (rightmost content token). '' if none. | `verimem/subject_extract.py:87`; `verimem/subject_extract.py:94`; `verimem/subject_extract.py:317` | `tests/test_il_soggetto_IT_senza_aprire_le_selfclaim.py`; `tests/test_subject_domain_classify.py`; `tests/test_un_accento_non_decide_se_il_gate_scatta.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 3 | `verimem/subject_extract.py:225` `_subject_tokens` | funzione: Lowercased content tokens of the subject NP (determiners stripped; | `verimem/subject_extract.py:253`; `verimem/subject_extract.py:296`; `verimem/subject_extract.py:337` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_subject_tokens\b`, non `_subject_tokens(`, che non vedrebbe i riferimenti passati come callback) → **3 riferimenti**, i primi `verimem/subject_extract.py:253`; `verimem/subject_extract.py:296`; `verimem/subject_extract.py:337`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 4 | `verimem/subject_extract.py:244` `same_subject` | funzione: True iff the two propositions are ABOUT the same subject — the L3-semantic | nessuno trovato | `tests/test_l3_subject_match.py`; `tests/test_l3_subject_prefilter.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
| 5 | `verimem/subject_extract.py:285` `nli_prefilter_skip` | funzione: True = SAFE to skip the NLI judge for this pair. Converged GLM-5.2 + | `verimem/anti_confab_gate.py:2242`; `verimem/anti_confab_gate.py:2243` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\bnli_prefilter_skip\b`, non `nli_prefilter_skip(`, che non vedrebbe i riferimenti passati come callback) → **2 riferimenti**, i primi `verimem/anti_confab_gate.py:2242`; `verimem/anti_confab_gate.py:2243`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 6 | `verimem/subject_extract.py:306` `is_domain_professional` | funzione: True iff ``text`` reads as a THIRD-PARTY professional/domain fact that the | `verimem/anti_confab_gate.py:198`; `verimem/anti_confab_gate.py:213`; `verimem/anti_confab_gate.py:214` (+2) | `tests/test_e_apostrofo_e_un_marcatore_di_verbo.py`; `tests/test_l1_domain_precision.py`; `tests/test_subject_domain_classify.py` | - | **FUNZIONA COME PROMESSO** *(al livello: i test passano)* | batch 08/09 21:15, 48 file eseguiti in un colpo: **2315 passed, 6 skipped, 43 xfailed, 25 warnings in 1421.89s (0:23:41)**, EXIT=0, zero rossi. ⚠️ **Livello dichiarato**: questo prova che i test che la nominano passano, NON che la funzione faccia ciò che il suo docstring promette — la seconda cosa richiede casi scelti sulla promessa, e per questa riga non l'ho fatta |
