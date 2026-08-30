# ⑲ La specifica di `L1`: cosa ferma, cosa lascia passare, e quale dei due errori arriva all'utente

**Misurato il 29-30/08/2026** · celle **`W7-60` · `W7-61` · `W7-62` · `W7-64` · `W7-65`**
del registro, con i comandi per rifarle · tutte le misure **fuori da pytest**, un processo
per caso.

Questo documento **non ripete le misure**: le cita col numero di cella e dice **cosa se ne
ricava per decidere**. Chi vuole i numeri grezzi apra la cella; chi vuole rifarli trovi in
ogni cella la riga `🔎 rifallo con`.

---

## In una riga

`L1.13` **non ferma i self-claim**: ferma i self-claim che usano **una di sei radici
italiane**. Fuori da quell'elenco passa tutto, e **senza fonte non c'è nessun altro layer
sotto**. Dei due errori simmetrici che il layer commette, **solo uno arriva all'utente**, ed
è quello opposto a quello che ci aspettavamo.

---

## 1. Il perimetro è un elenco — sei radici — e si legge nel codice

`l1_completion_detector.py:54-55` è esplicito:

```
   complet[oaie] | completat[oaie] | finit[oaie] |
   fatt[oaie]    | chius[oaie]     | conclus[oaie]
```

**`W7-64`**, stesso claim senza fonte cambiando **una sola parola**: dentro l'elenco
**6 fermati su 6** (il layer è acceso); fuori **14 su 14 passano**, e **passano anche alla
porta** — layer vuoto, nessun altro subentra.

🔑 **Non serve ingannare la fonte: basta scrivere «ho ULTIMATO» invece di «ho COMPLETATO».**

📌 Il dettaglio era sotto gli occhi tre volte prima di diventare una misura: in **`W7-60`**
i due verbali che passavano avevano *consegnata* ed *evasa*; in **`W7-62`** *ultimato*
passava dove *conclusa* fermava. **Annotato come nota a margine, era la specifica.**

## 2. L'italiano è meno protetto dell'inglese — e non per questo layer

L'elenco inglese (`:34-35`) ha le sue sei forme più tre composte. Ma il confronto **alla
porta** (`W7-64`, estensione) rovescia l'attesa:

```
   IT   fuori elenco → passano 14 su 14      nessun layer subentra
   EN   fuori elenco → passano  7 su 12      altri layer subentrano

   EN   shipped · merged · deployed  →  L1        fixed · resolved  →  L1.8
   IT   ultimato · terminato · consegnato  →  passano, LAYER VUOTO
```

⇒ **In inglese il gergo software è coperto da altri detector della famiglia; in italiano
gli equivalenti no.** L'asimmetria **non sta in `L1.13`**: sta nei detector che **mancano**
sul lato italiano. È una causa strutturale, e si somma al divario italiano che un'altra
istanza misura sui dati.

## 3. Quanto pesa davvero: 13,6%, non di più

**`W7-65`**, sul corpus (**13418 fatti vivi**): **231 occorrenze su 1695** usano una forma
**fuori elenco** — **13,6%**. Non è teorico: `esegu` (120) da solo vale più di
`finito`+`concluso` (74+53), che invece **sono sorvegliate**.

⚠️ **E il primo conteggio diceva 6,5%**, perché `fatt[oaie]` dava 1874 occorrenze ed è
**nove volte più sostantivo che participio** (1062 con articolo contro 118 con ausiliare):
in un corpus **che parla di «fatti»** quella radice gonfia il denominatore. Il difetto è
uscito **guardando la distribuzione**, non ricontrollando la formula.

📌 **Per il report servono entrambe le frasi**: *si aggira con un sinonimo* **e** *nel
traffico vero il sinonimo è il 13,6%*. Citarne una sola — qualunque — è fuorviante.

## 4. 🔑 I due errori non pesano uguale, e quello che pesa è il contrario di quel che sembra

**`W7-62`** mette i due versi sulla stessa tabella:

```
   FALSO ALLARME    senso uguale, parola diversa
      «l'istruttoria è stata CONCLUSA» contro fonte «CHIUSA»
      detector ferma · moat 99.3 · porta downgrade      🔴 un fatto VERO trattenuto

   FALSO PERMESSO   parola uguale, senso diverso
      detector passa · moat 1.7 · L4-grounding FERMA     🟢 danno alla porta: ZERO
```

⚖️ Il **falso permesso ha una rete sotto** — ma **solo quando c'è una fonte** da giudicare.
**`W7-64`** misura il caso **senza fonte**, cioè il self-claim nudo: lì il moat non ha nulla
da confrontare e **nessun layer subentra**.

⇒ **Il quadro completo**:

| | con FONTE | senza FONTE |
|---|---|---|
| **falso allarme** (ferma un vero) | 🔴 danno reale, moat a 99.3 | — |
| **falso permesso** (lascia passare) | 🟢 coperto da `L4-grounding` | 🔴 **nessuna rete** |

📌 E `W7-61` mostra da dove nasce il falso permesso con fonte: la cura del 28/08 perdona
quando **la parola compare nella fonte**, in **qualunque senso** — *«la strada è chiusa al
traffico»* fa entrare *«l'istruttoria è stata chiusa dal responsabile»*. Ciò che a volte la
protegge **non è il criterio, è la morfologia**.

## 5. ⚖️ Cosa ne segue per chi decide — e non lo decido io

**① La cura del 28/08 va STRETTA, non tolta.** Sui falsi allarmi veri funziona (`W7-61`,
classe A: 2 su 2, e una seconda istanza l'aveva controfirmata su una popolazione sua).
Toglierla riporterebbe indietro il verso che già fa danno.

**② Chi la stringe deve sapere da che parte sta il rischio.** Il verso che arriva
all'utente è il **falso allarme**: stringere il criterio senza questo dato **peggiora
proprio quello**. Il falso permesso *con fonte* ha una rete; quello *senza fonte* no, ma si
cura allargando il **vocabolario**, non stringendo il confronto con la fonte — sono due
leve diverse e vanno mosse separatamente.

**③ Il perimetro è un elenco, e un elenco si allunga.** Le forme più frequenti fuori
elenco sono misurate (`W7-65`) e si possono aggiungere. ⚠️ Ma **allargare l'elenco aumenta i
falsi allarmi**, che è il verso che fa danno: chi lo fa **misuri entrambe le popolazioni**
prima e dopo.

**④ L'asimmetria di lingua è una decisione di prodotto, non un difetto da patchare.** Il
README promette «Verified memory for AI agents». Se gli agenti scrivono in italiano, la
protezione è più sottile — e questo va **detto**, non tappato con una riga di regex.

## 6. ⛔ Cosa questa specifica NON sa

- **I sinonimi li ho scelti io** (14 IT + 12 EN): non sono un campione del linguaggio reale.
- **Il 13,6% è un limite superiore**: conta **occorrenze di radici**, non **self-claim**. Un
  verbale di terzi (*«la pratica è stata eseguita dall'ufficio»*) entra nel conteggio e non
  è un self-claim.
- **Il corpus è il NOSTRO**, non quello di un cliente — e il nostro parla di memoria, di
  gate e di test, il che ne distorce il vocabolario.
- **Il caso originale che ha aperto il verso «falso allarme»** è di un'altra istanza
  (giudice a 97,6): io ne ho riprodotto **la forma**, non quel caso.
- **`quarantined_by` è vuoto sul 61,1%** (`W7-50`), quindi **le attribuzioni a un layer
  specifico sul corpus non sono leggibili** — dove ho scritto «lo ferma `L1.13`» è perché
  l'ho **eseguito**, non perché il campo lo dicesse.

---

## Le celle, per rifare tutto

`W7-60` classificatore e verbali · `W7-61` la polisemia e la cura del 28/08 ·
`W7-62` i due versi sulla stessa tabella · `W7-64` il perimetro e l'asimmetria di lingua ·
`W7-65` il peso sul corpus. Ognuna porta la riga `🔎 rifallo con` e i controlli che
potevano farla cadere.
