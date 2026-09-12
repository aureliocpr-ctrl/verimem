# `verimem/evidence_hint.py`

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
| 1 | `verimem/evidence_hint.py:38` `evidence_in_text` | funzione: ``[(kind, cited_value)]`` for every evidence reference named in the prose. | `verimem/evidence_hint.py:24`; `verimem/evidence_hint.py:62` | `tests/test_verimem_evidence_hint.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 2 | `verimem/evidence_hint.py:49` `hint_for` | funzione: A sentence naming what the writer already cited, or None when the prose | `verimem/anti_confab_gate.py:65`; `verimem/anti_confab_gate.py:3101`; `verimem/evidence_hint.py:24` | `tests/test_verimem_evidence_hint.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.


---

## Il banco: 12 promesse su 12

```
── le quattro forme riconosciute ──
OK  (commit) «…last commit ff2aaa3e»            → 'ff2aaa3e'
OK  (file)   «…in verimem/semantic.py:1573»     → 'verimem/semantic.py:1573'
OK  (test)   «girato pytest e EXIT=0…»          → 'pytest'
OK  (pr)     «chiuso con la PR #412»            → 'PR #412'

── il controllo negativo, che rende leggibile il resto ──
OK  prosa senza riferimenti → []  ·  hint_for → None (non inventa un suggerimento)
OK  testo vuoto → []  ·  None → []

── ciò che il modulo NON fa ──
OK  `hint_for` torna una STRINGA, non un verdetto
OK  la frase CITA il riferimento e dice che nella proposizione è un'ASSERZIONE
OK  NON propone una forma specifica  ← la lezione del docstring: suggerire
    `commit:` sbloccherebbe 6 casi su 60, mentre `pytest:<t>_PASS` ne sblocca 40

12 casi · tutte le promesse reggono                                    EXIT=0
```

## 🔴 Ma il numero che il docstring pubblica **non regge più**: 34,2% → 13,3%

Il docstring dichiara una misura del **2026-07-28**:

> «of **509 quarantined facts, 174 (34.2%)** name a commit SHA, a file:line, a
> pytest/EXIT result or a PR in their own text — 95 commits, 69 test results,
> 30 file:line, 18 PRs»

**Predizione depositata prima di eseguire**: i valori assoluti saranno più alti
(il corpus cresce), la percentuale resterà nello stesso ordine (30-40%).
**Smentita.** Rimisurata oggi, 42 giorni dopo, con la funzione stessa del modulo
(`evidence_in_text`) su `~/.engram/semantic/semantic.db` in sola lettura:

```
                                         28/07        08/09 (vivi)   08/09 (tutti)
quarantenati                              509            1404           2820
ne nominano una nella PROSA               174             187            395
                                        34,2%           13,3%          14,0%

per tipo   commit                          95             113            225
           test                            69              61            166
           file:line                       30              30             32
           PR                              18              14             16
```

**Il denominatore è cresciuto 2,8× (o 5,5×), il numeratore 1,1× (o 2,3×).**

⚠️ E qui c'è il difetto della misura originale, che è anche il motivo per cui non
posso dire *perché*: **il docstring non dichiara quale denominatore usava**. «509
quarantined facts» sono i vivi o tutti? Se erano i vivi, il confronto è
1404/509; se erano tutti, 2820/509. Ho misurato **entrambi** invece di sceglierne
uno e far finta che fosse l'unico — ed entrambi danno una quota **meno della
metà** di quella pubblicata.

### Perché conta, e che cosa NON dice

Il modulo **non è rotto**: 12 promesse su 12. È il **numero che lo giustifica**
ad essere invecchiato — e quel numero è la motivazione scritta della sua
esistenza («spesso il writer HA l'evidenza e l'ha messa nella frase»). Oggi
«spesso» vale **un quarantenato su sette**, non uno su tre.

**Non so quale delle due cause sia**, e lo scrivo invece di sceglierne una:
(a) il corpus è cresciuto in una direzione che cita meno; (b) la misura di allora
usava un perimetro diverso da entrambi i miei. ⇒ **NON MISURATO** su quale.

🔑 **Un numero in un docstring è una promessa come le altre: si riverifica, non
si cita.** E un numero senza denominatore dichiarato non è riverificabile
davvero — si può solo rimisurare in tutti i modi plausibili e riportarli tutti,
che è ciò che ho fatto.

📌 Un dato curioso da lasciare a chi indagherà: **`file:line` è fermo a 30 sui
vivi**, identico al 28/07, mentre commit e test sono cresciuti. Se qualcuno cerca
la causa, quella colonna è il punto da cui partire.
