# verimem/atomic_claims.py — mappa

**Owner**: ws4 (ML Ferro) · **284 righe · 13 fra funzioni, metodi e classi**.

La decomposizione di una scrittura in claim ATOMICI, uno per affermazione: il «tempo 1» del design «write = N claim atomici, ognuno giudicato». Pura e deterministica, nessun modello — quindi la promessa si può verificare davvero.

## Stato (2026-09-08, 21:48)

```
  voci elencate con l'AST                                13 / 13
  con un verdetto                                        0
     «i test che la nominano passano»                    0
     idem, entro un limite DICHIARATO (xfail nei test)   0
  NON MISURATO                                           10
     di cui candidati «MAI CHIAMATA» da confermare       0
```

Batch **unico per quattro file** (`dream`, `source_trust`, `auto_dream_worker`,
`anti_confabulation`), 63 file di test in un colpo:
**500 passed, 1 skipped, 2 xfailed, EXIT=0, 262,33 s, zero rossi.**

## ⚠️ I DUE LIVELLI, e cosa NON dice questa tabella

**«I test che la nominano passano» NON è «fa ciò che il docstring promette».**
Ogni riga porta il proprio livello scritto per esteso. Su `atomic_claims.py` **nessuna
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

# Mappa di `verimem/atomic_claims.py` — 13 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/atomic_claims.py:114` `_zone_protette` | funzione: Gli intervalli [inizio, fine) che stanno dentro virgolette. | `verimem/atomic_claims.py:187` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_zone_protette\b`, non `_zone_protette(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/atomic_claims.py:187`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 2 | `verimem/atomic_claims.py:143` `_parola_prima` | funzione: (nessun docstring) | `verimem/atomic_claims.py:153`; `verimem/atomic_claims.py:161` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_parola_prima\b`, non `_parola_prima(`, che non vedrebbe i riferimenti passati come callback) → **2 riferimenti**, i primi `verimem/atomic_claims.py:153`; `verimem/atomic_claims.py:161`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 3 | `verimem/atomic_claims.py:150` `_e_apertura_di_citazione` | funzione: (nessun docstring) | `verimem/atomic_claims.py:137` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_e_apertura_di_citazione\b`, non `_e_apertura_di_citazione(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/atomic_claims.py:137`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 4 | `verimem/atomic_claims.py:158` `_e_chiusura_di_citazione` | funzione: (nessun docstring) | `verimem/atomic_claims.py:130` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_e_chiusura_di_citazione\b`, non `_e_chiusura_di_citazione(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/atomic_claims.py:130`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 5 | `verimem/atomic_claims.py:166` `_dentro` | funzione: (nessun docstring) | `verimem/atomic_claims.py:191` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_dentro\b`, non `_dentro(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/atomic_claims.py:191`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 6 | `verimem/atomic_claims.py:170` `ha_verbo_finito` | funzione: Un pezzo e' un claim solo se ha un verbo finito (lista aperta sopra). | `verimem/atomic_claims.py:57`; `verimem/atomic_claims.py:220`; `verimem/atomic_claims.py:226` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita 08/09 21:59: `'il gate ha ammesso 233 scritture'` → `True` · `'233 scritture'` → `False` · `"e' verificata"` → `True` · `'il gate'` → `False`. ⚠️ È il predicato che decide la decomposizione, e la sua copertura è una **lista chiusa di 1209 verbi**: `ammette`/`serve`/`misura` sì, **`esclude` e `quarantena` no** |
| 7 | `verimem/atomic_claims.py:175` `soggetto_di` | funzione: Il testo del pezzo fino al suo primo verbo finito; '' se non c'e' un verbo | `verimem/atomic_claims.py:57`; `verimem/atomic_claims.py:241` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita 08/09 21:59: `'il gate ha ammesso 233 scritture'` → `'il gate'` · `"la cura e' entrata"` → `'la cura'` · `'233 scritture'` → `''` (nessun verbo finito, come il docstring promette) |
| 8 | `verimem/atomic_claims.py:184` `_spezza` | funzione: Split sulle coordinate, saltando i punti che cadono dentro le virgolette. | `verimem/atomic_claims.py:275` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_spezza\b`, non `_spezza(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/atomic_claims.py:275`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 9 | `verimem/atomic_claims.py:203` `_ausiliare_di` | funzione: L'ultimo ausiliare del pezzo ('' se non c'e'): e' quello che il participio | `verimem/atomic_claims.py:222`; `verimem/atomic_claims.py:223` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_ausiliare_di\b`, non `_ausiliare_di(`, che non vedrebbe i riferimenti passati come callback) → **2 riferimenti**, i primi `verimem/atomic_claims.py:222`; `verimem/atomic_claims.py:223`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 10 | `verimem/atomic_claims.py:210` `_fondi_i_nudi` | funzione: Un pezzo senza verbo finito si fonde col precedente (o col successivo se | `verimem/atomic_claims.py:278` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_fondi_i_nudi\b`, non `_fondi_i_nudi(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/atomic_claims.py:278`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 11 | `verimem/atomic_claims.py:232` `_eredita_il_soggetto` | funzione: Un pezzo che comincia con un verbo finito riceve il soggetto del pezzo | `verimem/atomic_claims.py:282` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_eredita_il_soggetto\b`, non `_eredita_il_soggetto(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/atomic_claims.py:282`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 12 | `verimem/atomic_claims.py:248` `_chiudi` | funzione: (nessun docstring) | `verimem/atomic_claims.py:283` | nessuno | - | **NON MISURATO** | nessun test la nomina. **NON è MAI CHIAMATA**: cercata col NOME NUDO (`\b_chiudi\b`, non `_chiudi(`, che non vedrebbe i riferimenti passati come callback) → **1 riferimenti**, i primi `verimem/atomic_claims.py:283`. ⚠️ Sono **candidati del grep, non letti uno per uno**: manca la copertura di test, e questo lo dice; se il chiamante sia vivo su un percorso esercitato resta da leggere |
| 13 | `verimem/atomic_claims.py:256` `decomponi` | funzione: La scrittura -> i suoi claim atomici, ognuno una frase chiusa. | `verimem/atomic_claims.py:1`; `verimem/atomic_claims.py:57` | `tests/test_decomponi_spezza_in_claim_atomici_senza_perdere_la_coda.py`; `tests/test_nessun_modulo_nasce_irraggiungibile.py`; `tests/test_un_accento_non_decide_se_il_gate_scatta.py` | - | **FUNZIONA COME PROMESSO**, con un limite MISURATO | eseguita 08/09 21:59 con `env -u`, sui casi che il docstring stesso nomina — è pura e deterministica, quindi la promessa si può verificare davvero. **Le tre regole reggono**: (1) soglia 1 parola, «…233 scritture **ed è verificata**» → `['Il gate ha ammesso 233 scritture.', "Il gate e' verificata."]` — la coda c'è, e **il soggetto viene propagato**, che il docstring non prometteva; (2) apostrofo, `e'` e `è` danno lo stesso esito (2 pezzi entrambi); (3) controllo negativo, un testo senza congiunzioni resta **un pezzo solo**. ⚠️ **IL LIMITE, misurato**: « ed » spezza **solo se il secondo pezzo comincia con un verbo che `_VERBI_FINITI` conosce** (1209 elementi). `ed è verificato` → 2 pezzi · `ed ha escluso` → 2 pezzi · **`ed esclude` → 1 pezzo solo**. E fra i mancanti c'è **`quarantena`** (`ha_verbo_finito('quarantena 127 fatti')` → `False`), che è il verbo del nostro dominio. Il docstring dichiara che è una lista; **quanto copra non è misurato da nessuno** |
