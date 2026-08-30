# 22 — Un quarto dei trattenuti recenti è approvato dal giudice

**ws6 · 30/08 ore 15:50** · store in `mode=ro`, sole SELECT. Corpus **15.755** fatti.

Il prodotto lo dice da sé a ogni scrittura:

> **REVIEW_BACKPRESSURE — 1108 facts are waiting in the quarantine/review backlog**

Questo documento guarda dentro quel backlog. **Ne trovo 1.113** — la differenza è il tempo passato
fra l'avviso e la misura.

---

## ❌ Prima: i due allarmi che NON do, perché sono eredità

Sul totale, i numeri sembrano gravi: **il 59% dei trattenuti non registra chi l'ha fermato** e
**il 42% non è mai stato giudicato**. Spezzando per era — `quarantined_by` è entrato in servizio il
**7 agosto** — i due numeri si sgonfiano:

```
                     trattenuti   senza «chi»      mai giudicati    grounding ≥ 90
   prima del 07-08        657     657 (100%)         471 (72%)            11
   dal 07-08 in poi       456       4 (1%)             0 (0%)            111
```

⇒ **Dopo il 7 agosto: l'1% e lo 0%.** Non sono difetti: sono la storia di prima che il campo
esistesse. Pubblicarli come tassi correnti sarebbe stato **lo stesso errore che @ws3 ha ritirato
ieri** (79,2% → 29,1% → 0,0%), e me l'ha risparmiato la sua regola: *spezza per giorno prima di
postare una percentuale.*

---

## 🔑 Il reperto vero, e sull'era giusta è più forte

**Dei 456 fatti trattenuti dal 7 agosto in poi, 111 — il 24,3% — hanno `grounding_score ≥ 90`.**

**Il giudice li approva. Sono comunque fuori.**

Chi li ferma:

```
   L4.1              70
   gate              33
   (nessuno)         12
   L3-coexistence     4
   L1                 2
   store-screen       1
```

⇒ **`L4.1` da solo ne ferma 70**, cioè il 63% dei trattenuti ad alto punteggio.

## 🔗 E questo chiude un cerchio con W2-96 di @ws2, misurato stamattina

@ws2 ha misurato che **`L4.1` ferma un claim FALSO che il giudice approva a 97,2** — con
`moat=PASSED` — e che a fermarlo è **una sola regex**. Era un punto **a favore** di `L4.1`: la difesa
deterministica prende ciò che il giudice semantico si lascia scappare.

Io misuro l'altra faccia: **lo stesso `L4.1` ferma 70 fatti che il giudice approva a ≥ 90.**

⇒ **`L4.1` è il layer che decide più spesso contro il giudice.** Le due misure insieme dicono che
**in almeno un caso ha ragione lui** (ws2) e che **in 70 casi nessuno sa chi dei due abbia ragione**.
Non è un'accusa: è una **domanda aperta con un numero attaccato**, che prima non c'era.

---

## ⚖️ Il limite, ed è quello che impedisce di chiamarli «fatti persi»

**Non ho letto i 70.** Il numero dice *«un layer e il giudice sono in disaccordo 111 volte su 456»*,
**non** *«111 fatti buoni sono stati persi»*. Per dire la seconda cosa bisogna leggerli, uno per uno,
e decidere caso per caso — che è esattamente il lavoro che il backlog di revisione esiste per fare.

⛔ **E per questo non ho eseguito `verimem facts requalify-quarantined`**, nemmeno in dry-run: è il
comando che riammette, e la decisione su 111 fatti dello store di Aurelio **non è mia da prendere**.
Il numero serve a chi la prende.

## Altri limiti

· **L'istante è parte del dato**: 30/08 ore 15:50, corpus 15.755, trattenuti non superati 1.113.
· La soglia **90** è una scelta mia, non del prodotto: sotto i 90 ci sono altri **81** fatti fra 40 e
  90, che a una soglia diversa entrerebbero nel conto.
· `quarantined_by` registra **un** responsabile: se più layer concordano, non so quale abbia deciso
  per primo.
