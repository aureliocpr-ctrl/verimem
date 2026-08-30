# 27 — La porta ignora il campo che dice di cosa parla un fatto

**ws6 · 30/08 ore 18:55** · corpus servibile **12.438**, `mode=ro`, sole SELECT.

Il [documento 25](25-tre-ordinamenti-a-confronto-e-nessuno-domina.md) si chiude così: *«se volete
recuperare l'archivio vecchio, la leva non è il ranking: è far entrare quei fatti fra i candidati.
Quello non l'ho misurato»*. **Ora è misurato.**

---

## Il candidato ovvio, e perché nessuno l'aveva guardato

`search_facts` fa `LIKE` **solo su `proposition`**. Ma il campo che lega un fatto al suo argomento è
**`topic`**: cercando `omnex project`, il fatto ha `topic = project/omnex/...` e una `proposition`
che **non contiene nessuna delle due parole**.

⇒ **La porta ignora l'unico campo che dice di cosa parla un fatto.**

## La misura

```
   fascia     n  |  top5 P   mai P   cand. P  |  top5 P+T   mai P+T   cand. P+T
   recenti   20  |      12       7      1259  |       20         0           1
   medi      20  |       0       4      2411  |       20         0           1
   vecchi    20  |       0      18         5  |        2         0          20
```

`P` = `LIKE` su `proposition` (oggi) · `P+T` = `LIKE` su `proposition` **oppure** `topic`.

## ⚠️ La circolarità, dichiarata prima dei risultati

**La query è fatta con le parole del `topic`**, quindi cercare nel topic trova **per costruzione**.
Le colonne `top5 P+T` e `mai P+T` sono **circolari e non provano nulla da sole**.

🔑 **Il numero che NON è circolare è quello dei CANDIDATI**: **da 1.259 e 2.411 a 1**. Quella
riduzione non dipende da come ho costruito la query — dipende dal fatto che **il topic è
selettivo e la proposition no**. Ed è ciò che conta, perché **con un solo candidato l'ordinamento
smette di decidere qualsiasi cosa**.

E la circolarità stessa è il punto: **il topic *è* l'argomento**. Se una domanda per argomento non
aggancia, non è perché la domanda è mal posta — è perché la porta guarda nel posto sbagliato.

---

## 🔴 Questo mi obbliga a rivedere la motivazione del mio voto sul ranking

Nel doc 25 ho votato **A** (lasciare l'ordinamento per data) con questa ragione: *«su tutte e tre le
opzioni i vecchi restano a 0, quindi cambiare il ranking non risolve il problema per cui era stato
proposto»*.

**Quella ragione era vera solo finché l'aggancio restava rotto.** Con `P+T`:

· sui **recenti** e sui **medi** i candidati diventano **1** ⇒ **l'ordinamento è irrilevante**,
  qualunque esso sia;
· sui **vecchi** i «mai candidati» vanno **da 18 a 0** — entrano — **ma il top5 resta 2 su 20**,
  perché con venti candidati **l'ordine per data li mette in fondo**.

⇒ **Le due cure non sono alternative: sono complementari, e in quest'ordine.**
**Prima si aggancia** (il topic), **poi l'ordinamento torna a contare — ma solo per i vecchi**, che
è esattamente la fascia per cui era stato proposto.

⚖️ **Il mio voto resta A** — non si cambia il ranking adesso — **ma la motivazione cambia**: non
«il ranking non serve», bensì **«il ranking non serve PRIMA dell'aggancio, e andrà rivisto DOPO»**.
Chi vota tenga presente che sono due decisioni in sequenza, non una.

## Limiti

· **La colonna `P+T` è circolare** per costruzione (vedi sopra): l'unico numero che porto come
  risultato è **la riduzione dei candidati**.
· **n=20 per fascia**, 60 casi.
· **Non ho misurato il costo**: `LIKE` su due colonne raddoppia i parametri e può cambiare i tempi.
  **Non lo propongo come cura finché non è cronometrato.**
· **Non ho misurato il rumore**: cercare nel topic potrebbe far entrare fatti irrilevanti che oggi
  restano fuori. Con i candidati a 1 sembra improbabile, **ma «sembra» non è una misura**.
· **L'istante è parte del dato**: 30/08 ore 18:55, corpus servibile 12.438.
