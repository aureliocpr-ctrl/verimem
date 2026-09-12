# `verimem/proof_evidence.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## Il claim del README

**NESSUNO.**

Cercato nel README con i termini del modulo (`grep -in`) e **nessuna
riga lo copre**. Il claim `README:704` è della famiglia dei detector
L1 e questo file non è uno di quelli: attribuirglielo sarebbe
inventare l'attribuzione — in un documento fatto per collegare i
claim al codice, l'errore peggiore.

⇒ come `ide.py` e `sandbox.py`: **superficie viva fuori dalla
vetrina**. Non è un difetto; è un dato per chi decide che cosa il
prodotto dichiara di essere.

## La copertura di esecuzione

```
perimetro: 51 file di test che nominano i detector L1
copertura: 100.0%
statement non eseguiti: —
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/proof_evidence.py:54` `is_machine_checked` | funzione: True when ``verified_by`` cites a process that ran and reported an | `verimem/proof_evidence.py:51`; `verimem/proof_evidence.py:69` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 2 | `verimem/proof_evidence.py:62` `both_machine_checked` | funzione: True when BOTH sides carry machine-checkable evidence. | `verimem/anti_confab_gate.py:510`; `verimem/anti_confab_gate.py:2250`; `verimem/anti_confab_gate.py:2308` (+1) | `tests/test_due_misure_diverse_non_sono_un_aggiornamento.py`; `tests/test_proof_beats_opinion.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.


---

## Il banco nel merito: 18 promesse su 18

Il modulo esprime una regola: **quando entrambe le parti portano una prova
meccanicamente controllabile, l'opinione di un modello non basta a ritirarne
nessuna**. Nasce da un caso vero (dogfooding 2026-07-25): di 9 relazioni fra
successioni intere verificate con un controllo esatto, **7 ritirate a coppie**
perché un cross-encoder legge «stesso soggetto, numeri diversi» come
contraddizione — mentre erano proprietà distinte, entrambe vere e provate.

```
── il controllo positivo, e il negativo che lo rende leggibile ──
OK  'pytest:test_qualcosa_PASS' · 'qa:scenario_uno_PASS' · 'ci:12345:green' → True
OK  'ho controllato io e funziona' · 'doc:manuale#…' · 'conversation:…' · [] · None → False

── L'ALIAS È UNICO ──
OK  su tutti gli 8 input, is_machine_checked == _has_tested_evidence   divergenze=0

── la simmetria ──
OK  due prove → True · una sola da un lato → False (in entrambi i versi)
OK  f(A,B) == f(B,A), anche sui casi asimmetrici

── ciò che il modulo NON fa ──
OK  torna un bool e nient'altro · non muta gli argomenti

18 casi · tutte le promesse reggono                                    EXIT=0
```

📌 **L'equivalenza (divergenze=0) è la promessa che conta**: il docstring dice
«one notion of "proof" for the whole store — **a second copy would drift**, and
this codebase has already paid for that with three divergent copies of its own
rules». È la classe «una copia invece della superficie unica» che questa squadra
ha in memoria, e qui è stata evitata **e** verificata.

## E la regola è applicata — nella forma dichiarata

`anti_confab_gate.py:2308`:

```python
if (_old is not None and both_machine_checked(
        verified_by, getattr(_old, "verified_by", None))):
    continue
```

Con sopra il commento che ne circoscrive lo scopo: «*no status is promoted and
nothing becomes immune — a deterministic clash never reaches this code and still
retires the old value*».

## 🔴 Ma quanto copre? Misurato sullo store vivo: **0,5%**

`anti_confab_gate.py:510-514` dichiara il limite **senza il numero**:

> «quella guardia protegge solo chi porta un `verified_by` deterministico, cioè
> **nessuno di chi scrive dall'SDK**»

Il numero non c'era da nessuna parte. Misurato in sola lettura
(`sqlite3 mode=ro`, nessuna scrittura) su `~/.engram/semantic/semantic.db`:

```
fatti vivi (superseded_by IS NULL)        15679
con un `verified_by` NON VUOTO              588   (3,8%)   ← il controllo
con una PROVA MECCANICA riconosciuta         77   (0,5%)   ← quanto copre la guardia

fra chi HA evidenza, quanta è una prova    13,1%

i prefissi più citati:  fact 3008 · file 416 · bash 393 · git 100 · pytest 96
gli status dei 77 protetti: model_claim 63 · quarantined 13 · verified 1
```

**Il controllo «verified_by non vuoto» è quello che rende leggibile lo 0,5%**:
senza, non si distinguerebbe «pochi portano una prova» da «pochi portano
qualsiasi evidenza». Sono due storie diverse, e qui valgono **entrambe** — solo
il 3,8% cita qualcosa, e di quel poco appena il 13,1% è una prova che una
macchina può ricontrollare. Il riferimento più usato è **`fact:`** (3008): si
cita un altro fatto, non un processo che ha girato.

⚠️ Nota sul numeratore: `pytest` compare 96 volte come **prefisso** ma i fatti
riconosciuti sono 77 — `_has_tested_evidence` vuole la forma intera
(`pytest:<nome>_PASS`), non il solo prefisso. Il 77 è quindi il numero **della
guardia**, non quello di «chi ha nominato pytest».

⇒ **FUNZIONA COME PROMESSO** (18/18) **con copertura misurata dello 0,5%**. Non
è un difetto del modulo: la regola è corretta, applicata e circoscritta come
dichiara. È un dato per chi decide dove mettere il prossimo sforzo — un presidio
giusto che protegge un fatto su duecento.
