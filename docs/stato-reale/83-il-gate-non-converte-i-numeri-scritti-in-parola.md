# Il gate non sa convertire un numero scritto in parola, e ferma 3 fatti veri su 4

**03/09/2026, 20:12 · banco `banchi/ws6-due-frasi-gemelle-due-verdetti.py`**

Trovato per caso, mentre scrivevo un test su tutt'altro: il fatto «vivo» del test
veniva quarantinato e il recall tornava vuoto. Due frasi della stessa identica
forma, **entrambe vere**, ricevevano verdetti opposti.

## Il quadro, una variabile per volta

A e B differivano per **due** cose insieme (il numero e l'oggetto), quindi le
celle incrociate:

```
A   quattromilaseicento / 4600   ricambi      99,95   ammesso
A2  quattromilaseicento / 4600   imballaggi   99,95   ammesso    <- cambia l'oggetto
A1  duemila / 2000               ricambi      10,46   QUARANTINED <- cambia il numero
B   duemila / 2000               imballaggi   15,66   QUARANTINED
```

⇒ **Separa il numero, non l'oggetto.** Ma «il numero» non dice ancora *quale*
sua proprietà, e le due ipotesi si distinguono togliendo la conversione:

```
PAROLA -> CIFRA (serve convertire)      STESSA FORMA (non serve)
  quattromilaseicento / 4600   99,95      duemila / duemila            99,31
  duemila / 2000               10,46      quattromilaseicento / idem   99,80
  tremila / 3000                4,58      4600 / 4600                  99,46
  millecento / 1100             1,40      2000 / 2000                  99,38
```

🔑 **Il difetto è la CONVERSIONE parola→cifra: 3 fatti veri su 4 cadono.** Quando
non c'è niente da convertire, tutte e quattro le forme passano intorno a 99 —
comprese le stesse parole (`duemila`, `quattromilaseicento`) che nell'altra
colonna vengono rifiutate. **Non è la parola: è il passaggio fra le due forme.**

⚠️ **E i punteggi non sono «bassi», sono da falsità.** La coppia deliberatamente
falsa del controllo (`quattromilaseicento` contro una fonte che dice `17`) prende
**0,69**. `millecento / 1100` prende **1,40** e `tremila / 3000` **4,58**: un
fatto vero che la fonte sostiene alla lettera finisce **nella stessa fascia di
una falsità pura**. Il gate non li distingue.

## I due controlli, senza i quali il quadro non varrebbe

- **Ripetibilità** — la cella A giudicata due volte: `99,95` e `99,95`, scarto
  **0,00**. La differenza fra le celle è struttura, non rumore. (In casa c'era
  già una misura di determinismo del giudice; qui è rifatta sul caso in esame
  invece di essere ereditata da una lezione.)
- **Controllo positivo** — la coppia falsa prende **0,69**: il punteggio *sta*
  leggendo il rapporto fra fonte e proposizione. Senza questa cella, quattro
  numeri alti non avrebbero significato.

## 🪞 Correzione a un documento mio

Il doc **80** («la stessa frase con "otto" o con "8" riceve due verdetti
opposti») misurava **la forma della proposizione** — in parola contro in cifra —
e concludeva che in cifra il gate ferma anche i veri. **Il disegno era
incompleto**: la cella che discrimina non è la forma della proposizione, è **la
COPPIA** (forma della proposizione × forma della fonte), e mancava proprio la
diagonale «stessa forma da entrambe le parti». Con quella cella il quadro cambia
di significato: non «le cifre sono trattate peggio», ma **«il passaggio fra le
due forme non viene fatto»**.

E l'errore che mi ha portato qui è lo stesso in piccolo: avevo costruito il test
partendo da `quattromilaseicento / 4600`, l'**unico** caso che passa, e concluso
che fosse `duemila / 2000` a essere anomalo. Era il contrario — passa 1 su 4.

## Cosa NON dice

⚠️ **Perché `quattromilaseicento / 4600` passi non lo so.** È l'unica cella della
colonna che regge e non ho una spiegazione verificata; le ipotesi che ho (la
lunghezza della parola, come il tokenizzatore spezza le due forme) non sono state
provate e non le scrivo come se lo fossero.
⚠️ **Quattro numeri non sono un campione.** Dice che il difetto esiste ed è
riproducibile, non con che frequenza colpisce il corpus reale.
⚠️ **Solo italiano, solo `pallet di ricambi`.** Non ho provato altre lingue né
altre unità di misura, e la lezione di casa sulle liste monolingue vale anche qui.
⚠️ **Non ho misurato quanti fatti del corpus abbiano questa forma**, quindi non
so quanto costi oggi. È il passo successivo, e appartiene a chi tiene il gate.

## Perché conta

Un fatto vero, con una fonte che lo sostiene alla lettera, viene **quarantinato**
— cioè tenuto fuori dal recall di default. Chi scrive «duemila» invece di «2000»
perde il fatto senza sapere perché, e il perimetro promesso («un fatto che la
sua fonte non sostiene resta fuori») qui lavora **al contrario**.
