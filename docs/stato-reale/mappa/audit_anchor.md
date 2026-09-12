# `verimem/audit_anchor.py`

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
copertura: 86.7%
statement non eseguiti: 97, 174-177, 182-183, 187-188, 200
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/audit_anchor.py:71` `build_payload` | funzione: The signed part of a receipt (everything EXCEPT the signature). Heads are | `verimem/audit_anchor.py:46`; `verimem/audit_anchor.py:52`; `verimem/audit_anchor.py:65` (+4) | `tests/test_tamper_anchor_receipt.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/10 statement del corpo scoperti (755 passed, EXIT=0) |
| 2 | `verimem/audit_anchor.py:107` `sign_anchor` | funzione: Return the full receipt: ``payload`` plus its base64 ed25519 | `verimem/audit_anchor.py:47`; `verimem/cli.py:5814`; `verimem/cli.py:5831` (+2) | `tests/test_tamper_anchor_receipt.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 3 | `verimem/audit_anchor.py:114` `ChainState` | classe: A chain's CURRENT state, as seen at verify time. | `verimem/audit_anchor.py:45`; `verimem/audit_anchor.py:140`; `verimem/cli.py:5769` (+10) | `tests/test_tamper_anchor_receipt.py` | - | NON MISURATO | - |
| 4 | `verimem/audit_anchor.py:130` `AnchorResult` | classe: (nessun docstring) | `verimem/audit_anchor.py:44`; `verimem/audit_anchor.py:140`; `verimem/audit_anchor.py:158` (+4) | nessuno | - | NON MISURATO | - |
| 5 | `verimem/audit_anchor.py:139` `verify_anchor` | funzione: Verify a receipt against the live chains. Checks, in order: | `verimem/audit_anchor.py:48`; `verimem/cli.py:5891`; `verimem/cli.py:5918` (+2) | `tests/test_tamper_anchor_receipt.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 7/38 statement del corpo scoperti (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.


---

## Il banco nel merito: **i rami di fallimento, che nessun test percorre**

Le righe non eseguite dai test del perimetro — **97, 174, 182, 187, 200** — sono,
senza eccezioni, i punti in cui il modulo deve **dichiarare un fallimento**
(`failures.append` / `raise`).

Per un modulo di tamper-evidence è il caso peggiore possibile: se `verify_anchor`
non fallisse quando deve, direbbe **«catena intatta» su una catena manomessa**, e
la suite resterebbe verde. **Un presidio che non è mai stato visto scattare non è
un presidio.**

Le predizioni vengono dal contratto del docstring `:22-29` («*counts may only
grow, and the anchored head must still sit at its anchored position*»):

```
OK  A  catena estesa (14 righe, head al posto) → passa                    ok=True
OK  B  TRUNCATE (7 < 10 righe ancorate) → fallisce
          "mutations: tail truncated — current 7 chained rows < anchored 10"
OK  C  REWRITE (stesso conteggio, head cambiata) → fallisce
          "mutations: head at anchored row 10 does not match the receipt…"
OK  D  catena non intatta (verify interno rosso) → fallisce
OK  E  stato di una catena NON fornito → fallisce                        [riga 182]
OK  F  payload alterato dopo la firma → fallisce sulla FIRMA
OK  G  ricevuta vecchia su stato rollbackato a quel punto → passa (dichiarato)

8 casi · tutti i rami di fallimento scattano                              EXIT=0
```

**A e G sono le due colonne che rendono leggibile il resto.** Senza A («fallisce
sempre» sarebbe indistinguibile da «funziona») e senza G — il caso del
**contratto onesto**, in cui una ricevuta vecchia verifica contro uno stato
rollbackato esattamente a ciò che firmava, e il docstring **lo dichiara come
limite operativo, non lo nasconde**.

### La riga 187, che il primo banco NON aveva raggiunto

Il caso «ricevuta senza `mutations_rows`» falliva sulla **firma**, non sul campo:
togliere un campo *dopo* la firma la invalida, e il verdetto si ferma prima. La
riga 187 si raggiunge solo con una ricevuta **firmata così** — malformata ma
autentica, il caso di un produttore vecchio o difettoso:

```
ok=False
· mutations: receipt is missing mutations_rows          ← riga 187, raggiunta
```

📌 Lo scrivo perché è la parte che si sarebbe persa: **il primo banco dava «8 su
8» e una riga restava comunque non percorsa.** Un banco che passa non prova di
aver toccato ciò che voleva toccare — bisogna guardare *quale* messaggio esce,
non solo che il verdetto sia rosso.

⇒ **verdetto: FUNZIONA COME PROMESSO**, con la prova. E il buco non è nel
codice: è che **nessun test della suite lo esercita**, quindi la protezione
contro truncate e rewrite oggi non è custodita da niente. Banco pronto in
`<scratchpad>/banco_audit_anchor.py` (8 casi) e `riga187.py`. **Non li promuovo
io** (regola 2).
