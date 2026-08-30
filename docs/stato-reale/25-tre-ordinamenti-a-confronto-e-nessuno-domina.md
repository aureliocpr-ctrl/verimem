# 25 — Tre ordinamenti a confronto, e nessuno domina

**ws6 · 30/08 ore 18:10** · corpus servibile **12.429**, `mode=ro`, sole SELECT.

Il [documento 19](19-la-cura-del-ranking-peggiora-il-caso-reale.md) ha scartato la cura del ranking
perché **peggiorava i recenti** (14→4). @lead-audit ha chiesto di ridiscuterla con un candidato
migliore — ordinamento ibrido o solo avviso — e di portarla **come proposta con banco**. Eccola.

---

## Prima: l'«ibrido» era già quello scartato

L'ordinamento «per token, poi data a spareggio» **è esattamente quello del documento 19**:
`sorted(righe, key=conteggio, reverse=True)` su una lista già ordinata per data, e **`sorted` in
Python è stabile**. Non è un candidato nuovo — è quello che peggiorava i recenti.

## Il candidato nuovo: pesare i token per rarità (IDF)

`peso(token) = log(1 + N / df(token))` — «tbook» (poche decine di fatti) vale molto più di «senza»
(migliaia). Si ordina per la **somma dei pesi dei token agganciati**.

```
   fascia    usati   per data   per conteggio   per IDF   mai candidato
   recenti      20         11               6         6           8
   medi         20          0               8        10           3
   vecchi       20          0               0         0          18
   ---------------------------------------------------------------
   TOTALE                   11              14        16
```

⇒ **L'IDF è il migliore in totale (16) e batte il conteggio sui medi (10 contro 8).**
🔴 **Ma dimezza i recenti: da 11 a 6.**

## La proposta «indolore» che ho provato, e che cade

Idea: applicare l'IDF **solo al ripiego OR** — dove oggi si ordinano per data anche 2.575 candidati
e l'ordine è arbitrario — lasciando intatto il ramo AND, dove i risultati sono già pertinenti.
**Ipotesi**: i casi in cui la data vince sarebbero quelli agganciati dall'AND.

```
   fascia    ramo    n   per data   per conteggio   per IDF
   recenti   OR     20         11               6         6
   medi      OR     20          0               8        10
   vecchi    AND    15          0               0         0
   vecchi    OR      5          0               0         0
```

**Falsificata:** recenti e medi sono **tutti e venti nel ramo OR**. Non c'è un ramo «sicuro» in cui
confinare il cambio: **il trade-off resta identico.**

---

## 🗳️ La proposta, e la decisione non è tecnica

**Nessuno dei tre ordinamenti domina.** La scelta è fra:

| opzione | recenti | totale | cosa si compra, cosa si paga |
|---|---|---|---|
| **A** — lasciare la data (status quo) | **11** | 11 | non peggiora nulla · i medi restano a 0 |
| **B** — passare all'IDF | 6 | **16** | +5 fatti trovati in totale · **i recenti dimezzati** |

⇒ **È una decisione di prodotto**: privilegiare *il caso che oggi funziona* o *il totale dei fatti
ritrovati*. Il banco dà i numeri; **la preferenza fra i due non la decide il banco.**

### La mia raccomandazione: A, e tenere l'avviso

· il guadagno (**+5 su 60 casi**) **non compensa** il dimezzamento del caso che oggi funziona;
· 🔑 **su tutte e tre le opzioni i vecchi restano a 0**, perché **18 su 20 non sono nemmeno
  candidati**: il difetto è **l'aggancio, non l'ordine**. Nessun ranking li salva, quindi
  **cambiare il ranking non risolve il problema per cui era stato proposto**;
· l'avviso di ripiego (già in `5219443a`) **dice a chi legge che l'ordine non è la rilevanza**, che
  è il valore vero e costa zero regressioni.

## Limiti

· **n=20 per fascia**, 60 casi in tutto: la differenza 11 contro 6 è netta, il +5 in totale meno.
· Le parole del `topic` sono **un proxy** della domanda reale, e probabilmente **ottimista**.
· `df` calcolata con `LIKE '%token%'`: conta anche le occorrenze **dentro** altre parole.
· **L'istante è parte del dato**: 30/08 ore 18:10, corpus servibile 12.429.
