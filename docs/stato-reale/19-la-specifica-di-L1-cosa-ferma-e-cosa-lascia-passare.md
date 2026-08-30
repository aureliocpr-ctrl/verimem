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

🤝 **E va RISTRETTA: la lingua conta solo dove decide `L1`.** Un'altra istanza aveva
misurato l'opposto (attestazione nuda: IT ferma 4/4, EN solo 2/4) e le due misure sembravano
contraddirsi. Non lo sono — **le sue frasi italiane usavano parole DENTRO le liste, le mie
quelle FUORI**. Riconciliate, i suoi stessi dati mostrano la cosa che nessuna delle due
diceva da sola:

```
   classe dove decide L1          divario di lingua       (attestazione nuda: 4/4 vs 2/4)
   classe dove decide il GIUDICE  divario ZERO            (negazione: 4/4 e 4/4, L4-grounding)
```

⇒ 📌 **Chi stima il costo di allargare le liste lo pesi SOLO sulle classi `L1`**: dove
decide il giudice, allargarle non serve.

⚠️ **E contare le parole in lista SOVRASTIMA la copertura**: sempre da quei dati, dentro il
perimetro e in inglese `L1` a volte **parla e non ferma** (`L1.20`+`domain-precision` con
grounding 99.9 → `persist`). **Il perimetro non è l'unico problema: c'è anche la soglia.**

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

| | con FONTE **indipendente** | con fonte-**ECO** | senza FONTE |
|---|---|---|---|
| **falso allarme** (ferma un vero) | 🔴 danno reale, moat a 99.3 | — | — |
| **falso permesso** (lascia passare) | 🟢 coperto da `L4-grounding` | 🔴 **la rete APPROVA** | 🔴 **nessuna rete** |

🔴 **La colonna di mezzo è una CORREZIONE al quadro che avevo pubblicato**, e non viene da
una mia misura: viene dal voto sulla guardia anti-eco. Se la «fonte» sono **le parole
dell'agente stesso**, il moat gira, trova il claim davvero contenuto lì dentro, e
**approva** — la difesa forte è accesa e non serve a niente, perché il testo contro cui
misura non è indipendente. Due misure d'altri lo mostrano: **3 su 5 scappano con fonte-eco**,
e il fail-closed anti-auto-sorgente **si aggira per riformulazione 3 volte su 3**.

⇒ **«Il falso permesso ha una rete» vale SOLO se la fonte è indipendente.** Detto senza
quella condizione — come l'avevo scritto io — è **troppo rassicurante**.

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
proprio quello**. Il falso permesso ha una rete **solo con fonte indipendente**; senza
fonte si cura allargando il **vocabolario**, con fonte-eco si cura **all'etichetta della
provenienza**. ⚠️ **Tre leve diverse per tre buchi diversi** — e nessuna delle tre è
«stringere il confronto con la fonte», che è la leva che peggiora i falsi allarmi.

📌 Con la colonna eco, le facce note del buco `L1` sono **quattro** e convergono:
**riformulazione** (`W7-62`) · **eco** (voto anti-eco) · **polisemia** (`W7-61`) ·
**provenienza-etichetta** (ws2). La specifica non le cura: dice **dove sono** e **quale
leva tocca ciascuna**.

**③ Il perimetro è un elenco, e un elenco si allunga — ma NON per primo.** Chiedevo a chi
allarga di misurare entrambe le popolazioni; **l'ho fatto io** (`W7-66`), e il risultato
cambia la raccomandazione. Aggiungendo le sei radici più frequenti di `W7-65`: **6 su 6**
self-claim nudi fermati (guadagno pieno), **3 su 6** fatti veri con fonte fermati
(**rapporto 2 a 1**).

🔑 **Ma i 3 non erano casuali: erano esattamente i 3 in cui claim e fonte hanno flessione
diversa** (`ultimata`/`ultimato`, `evasa`/`evaso`, `espletata`/`espletato`). Allineando
**solo** la flessione, **3 su 3 passano**. ⇒ **Il costo non viene dall'allargamento: viene
dal perdono che confronta stringhe** — conferma indipendente di `W7-61`, e un difetto
strutturale in una lingua flessa che in inglese quasi non si vedrebbe (`shipped` è
`shipped`).

📌 In laboratorio questo dà una **sequenza**: rendere il perdono **morfologico**, poi
allargare l'elenco.

🔄 **Ma sul CORPUS VERO quella sequenza non regge, e l'ho misurato subito dopo** (`W7-67`,
5692 fatti con fonte conservata e giudizio ≥80): il costo è **26 su 5639 — lo 0,46%**, tutto
da **una sola radice** (`esegui`), e i falsi allarmi morfologici sono **0 su 26**. La causa
vera è un'altra: **26 su 26** hanno una fonte che **non contiene affatto** la parola del
claim, e **21 su 26** sono **output grezzo** (`passed`, `EXIT=`, SHA).

🔑 ⇒ **Il perdono testuale è cieco per costruzione proprio nel regime che la disciplina
delle fonti impone**: una fonte che è evidenza grezza sostiene il claim **senza usarne le
parole**, e nessun confronto testuale potrà mai perdonarla. Alla porta quei 26 fermano
**12 su 12** nel campione, con grounding **99,8 / 100,0 / 100,0** — falsi allarmi **certi**,
non potenziali.

📌 **Le due misure insieme**: allargare l'elenco costa poco (0,46%), e **la cura morfologica
che sembrava obbligatoria comprerebbe quasi niente sul traffico**. Il laboratorio e il
corpus danno **lo stesso sintomo con due cause diverse** — chi decide guardi il secondo.

⚠️ E il precedente pesa: quando il 03/08 l'elenco fu allargato alle flessioni, il rischio
fu misurato come **frequenza** (`l1_completion_detector.py:47-49`, *«nessuna forma supera
il 2%»*). **La frequenza non è il costo**: dice quante volte il criterio scatterà, non
quante volte sbaglierà.

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
