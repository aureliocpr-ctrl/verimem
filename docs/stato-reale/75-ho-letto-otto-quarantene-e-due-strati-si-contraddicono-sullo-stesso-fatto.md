# 75 — Ho letto otto quarantene: il moat approva al 99,98% e un altro strato ferma lo stesso fatto

*ws6/Aldo — 2 settembre 2026, 01:51 (letta). Seguito della misura sulla perdita
del corpus: dei 1324 fatti muti, **879 una fonte ce l'hanno e sono stati
giudicati**. La domanda che restava era se il giudizio fosse giusto.*

## ① Il metodo, e perché è leggere e non contare

**633** quarantinati vivi hanno **sia** un punteggio **sia** uno span di fonte:
sono gli unici su cui si può dire se il verdetto regga, perché si vede **cosa il
gate ha letto**. Ne ho campionati **otto** (seme dichiarato) e li ho **letti**,
claim contro fonte.

⚠️ **Otto non sono un tasso** — è la stessa scelta del [66](66-il-criterio-scartava-proprio-i-casi-piu-comuni.md): su un fenomeno
semantico un percentile non dice niente e quindici coppie di frasi sì.

## ② Il caso che vale il documento: due strati in disaccordo totale

```
id        ab9799f8b2e5      grounding 99.98      quarantined_by  L4.1
CLAIM     «Gli artefatti json citati alle righe 510-514 del README hanno
           ultimo commit fra il 2026-07-05 e il 2026-07-08.»
FONTE     README:510  e2e_crossuser_u2.json  … ultimo commit 2026-07-08
          README:511  qa_gem_k12_u0.json     … ultimo commit 2026-07-06
          README:513  extraction_consolidate… … ultimo commit 2026-07-05
```

Il claim **sintetizza un intervallo** da tre date che la fonte elenca. Il
**moat** — il giudice semantico — dà **99,98 su 100**: per lui la fonte sostiene
il claim. **`L4.1` lo quarantina lo stesso**, perché «fra il 05 e il 08» non
sono valori che compaiono come tali.

> 🔑 **Il fatto è fermato con il punteggio più alto possibile addosso.** Non è
> un giudizio incerto: è un **disaccordo fra strati**, e vince quello
> deterministico contro un'approvazione al 99,98%.

📌 La classe *«`L4.1` quarantina a grounding ~100 se conti tu»* è già in
registro. **Quello che questo caso aggiunge è la forma più netta possibile**: non
«il punteggio si abbassa», ma **il punteggio è pieno e il fatto cade lo stesso**.

## ③ Il secondo: il moat non gradua

```
id        b07292a63513      grounding 0.235      quarantined_by  moat
CLAIM     «Alle 21:47 del 30/08 i run ci completed sono 1167 e i queued sono 895.»
FONTE     «ORA 21:47:09 del 30/08
           coda: completed=1167 · queued=895 · in_progress=13»
```

Ogni elemento del claim è **nella fonte**: l'ora, la data, `completed=1167`,
`queued=895`. L'unica aggiunta è **«run ci»** — la fonte dice «coda», non
specifica che siano run di CI.

✅ **La quarantena è difendibile**: il claim afferma qualcosa che la fonte non
dice. ⚠️ **Ma il punteggio no**: **0,2 su 100** per due parole in più su un claim
altrimenti letterale. ⇒ **Il moat non gradua**: non distingue «quasi tutto
sostenuto, un'aggiunta» da «inventato».

📌 E la conseguenza è pratica: chi legge `grounding_score` per capire *quanto* un
fatto sia fondato riceve un numero che **non è una misura di quanto**, ma quasi
un binario.

## ④ Gli altri sei, in breve

| esito | casi |
|---|---|
| **quarantena giusta** | 1 — claim `40 falsi su 300 / 88 veri su 300` contro una fonte che dice `"falsi_ammessi": 8.0, "veri_persi": 9.5`: **i numeri non corrispondono** |
| **classe nota** («se conti o componi tu, il grounding crolla») | 4 — es. *«quattro file contengono…»* con la fonte che elenca quattro file (`0.3`); *«le tre mutazioni danno EXIT=1 … la suite torna a EXIT=0 con 11 passed»* con la fonte che mostra entrambi gli esiti (`0.3`) |
| **discutibile** | 1 — orari nel claim che la fonte non porta |

## ⑤ Cosa NON prova

⚠️ **Otto casi, scelti con un seme, su 633.** Non do nessun tasso: do due casi
letti e riproducibili per id.
❌ **Non ho ri-eseguito il gate su quei fatti**: leggo il verdetto e lo span
registrati, non rifaccio il giudizio. Il gate di oggi potrebbe decidere
diversamente — la cura dei decimali (`b12e9823`) mostra che cambia.
✅ **Quello che regge**: i due casi di §② e §③ sono **letture dirette** di
`proposition`, `grounding_span`, `grounding_score` e `quarantined_by` sulla
stessa riga. Il disaccordo fra strati del §② **non è un'inferenza**: sono due
campi dello stesso record.
⚠️ **Non dico che `L4.1` vada spento**: il [69](69-la-cura-che-avevo-proposto-costa-sei-ancore-vere-su-diciotto.md) mostra cosa costa stringere un
trigger senza misurare l'altro lato, e qui l'altro lato non l'ho misurato.

---
*Nessun banco: una query in sola lettura e otto casi letti a mano.*
