# Il giudice sbaglia con sicurezza, in entrambi i versi

*ws3 «Galileo», 29/08 sera. Sintesi di sei banchi misurati fra le 19:08 e le
20:34, tutti su store temporaneo con il cross-encoder locale — **nessuna API
esterna**, lo store di Aurelio mai toccato in scrittura.*

Questo documento esiste perché la materia è **da contratto di uscita** e sparsa
in sei banchi **non la legge nessuno**. Ogni numero qui sotto rimanda al commit
che lo ha prodotto; i limiti sono riportati **accanto** ai numeri, non in fondo.

---

## La tesi in una riga

**Il giudice non sbaglia timidamente: sbaglia con sicurezza, in entrambi i
versi. E un errore binario non lascia traccia di incertezza.**

Un falso a 45 chiama una revisione. Un falso a **0,1** dice «è certamente falso»
e chiude la questione. Un vero a **99,0** dice «è certamente vero» e apre la
porta. Il sistema non ha un registro per «non lo so», e questo è il filo che
lega tutto ciò che segue.

---

## ① Due superfici del prodotto promettono cose diverse

`agent_guide.py:40` — ciò che **il server dice agli agenti**:

> *WITH a `source`: the entailment moat, the strong check — the fact is admitted
> **only if the source TEXT actually supports it**.*

Il campo `moat` esposto da MCP, sullo stesso evento:

> *judged 99.9 — the source **SCORES** as supporting this fact: that is the
> judge's score, **NOT a check that the fact follows from it***

**La guida promette un'implicazione. Il campo `moat` avverte che implicazione
non è.** La misura dice quale delle due ha ragione: **la cauta**.

📌 **Proposta, ed è una riga di prosa**: allineare `agent_guide.py:40` alla
cautela che il campo `moat` **già usa** — «*scores as supporting*» invece di
«*actually supports*». *(Non ho toccato il file: è la superficie che il server
mostra agli agenti, e la decisione è di chi la mantiene.)*

---

## ② Quanto è grande il buco — e due numeri che vanno tenuti distinti

Dodici claim **irrilevanti e non contraddittori**, su dodici fonti diverse.
Controllo retto: tre claim veri ammessi 3/3. `706de500`

| | |
|---|---|
| **①** `moat: passed` su un irrilevante | **8 / 12** — misura **la promessa** |
| **②** il claim **entra** davvero | **2 / 12** — misura **ciò che il cliente subisce** |

*senza numeri: passed 5/8 · entrati 2/8 — con numeri: passed 3/4 · entrati 0/4*

🟢 **La seconda metà va detta con la stessa forza**: il gate ferma **6 degli 8**
che il moat lasciava passare, via `L1`, `L4.1` (sui numeri) e `L4-review`. **La
difesa in profondità funziona**: entrano 2 su 12, non 8 su 12.

**Identikit del buco**: *irrilevante* + **senza numeri** + punteggio **sopra
80**. Nessuna parola inventata, nessun numero da controllare, nessuna
contraddizione da rilevare — la fonte semplicemente non ne parla, e il giudice
la trova somigliante. I due entrati: **99,0** e **87,7**.

---

## ③ Non c'è un bordo: c'è un precipizio

Cercavo *quanto* dev'essere lontano un claim perché il punteggio scenda sotto 80
e la banda lo raccolga. Scala di cinque gradini, **tre fonti**. `44dbf0a3`

```
fonte        L1 pert  L2 stesso  L3 sogg+tema  L4 affine  L5 estraneo   bordo
corso           99.4      98.7        95.0         0.2        0.4       L4
fornitore       99.6      89.4        95.4         0.4       33.0       L4
server          99.8      73.2         1.1         0.3        0.3       L2
```

Il bordo cade a gradini **non adiacenti** ⇒ **non è dimensionabile dalla
distanza semantica**. Ma il **salto** sì: **94,8 · 95,0 · 72,1 punti** fra due
gradini consecutivi.

⚠️ **Qui ho dovuto correggere me stesso.** Avevo scritto che `L4-review` «fa il
lavoro» perché aveva raccolto due irrilevanti a 73,7 e 80,0. **Falso**: la banda
raccoglie poco **per costruzione**. Quei due casi erano fortunati. *Avevo
trasformato due celle in un meccanismo.*

---

## ④ E la banda 40-80 non può riempirsi: è il modello, non la taratura

Le misure precedenti erano su casi **discreti** — e un salto fra categorie **non
distingue** «è il modello» da «è la taratura», perché le categorie erano già
discrete. Serviva una serie a supporto **continuo**, che erode il supporto un
pezzetto alla volta. `a21d059c`

```
fonte        G1 esatto G2 riform G3 parzia G4 indebo G5 esteso G6 negato
consegna         100.0      99.9      99.0      99.9      99.8       0.5
biblioteca       100.0      99.6      98.3      97.0      98.7       1.9
impianto         100.0       0.1      96.9      95.9      99.8       1.1

alti (>=80): 14   ·   GRIGI (20-80): 0   ·   bassi (<=20): 4
```

**Zona grigia vuota.** Un cross-encoder addestrato a **decidere** non **gradua**.

⇒ **La banda 40-80** — il ramo che `verimem doctor` descrive come «*escalates to
one llm adjudication or holds the write for review*» — **non può riempirsi**.
Non è un parametro mal tarato: è **una rete tesa dove il pesce non transita
mai**. L'**1,08%** misurato sul corpus reale (`897d0048`) non era un caso: era
la misura di questo.

📌 **Seconda proposta di prosa**: la descrizione della banda in `doctor` promette
un comportamento che **il modello non può produrre**. Se qualcuno la cita come
garanzia, la misura la smentisce.

---

## ⑤ L'altro verso dell'errore

🟢 **Prima la buona notizia**: dieci parafrasi fedeli, dieci meccanismi
linguistici diversi (passiva↔attiva, sinonimi, perifrasi, nominalizzazione,
condensazione…). **Respinte dal giudice: 0 su 10**, tutte fra 96,6 e 100,0.
Controllo 10/10. **Il giudice regge le riformulazioni fedeli.** `062de944`

🔴 **Ma una riga**: «*Di notte il portone è sempre **chiuso***» — parafrasi
fedele di «*non resta mai aperto durante la notte*» — prende **97,6 dal giudice
ed è fermata da `L1.13`**, il *completion claim detector*: **`chiuso` viene letto
come «task chiuso»**, non come «serrato». *(Ho sospettato un artefatto del mio
banco e l'ho escluso con un A/B su store pulito.)*

**`L1` è lessicale e non consulta la fonte.** Qui la fonte diceva esattamente la
stessa cosa e il claim è stato quarantinato lo stesso: **il gate può fermare un
fatto vero e supportato per un'ambiguità di vocabolario**.

⚠️ **1 caso su 10, e «chiuso» è genuinamente ambiguo in italiano.**
Osservazione, **non** difetto proposto. E la classe è già nota agli autori
nell'altra faccia — il commento a `anti_confab_gate.py:1599` racconta che «*nove
detector su dodici leggevano «Il modulo NON funziona in produzione» come la
dichiarazione che funziona*». La negazione è stata curata; l'esenzione
`_is_honest_reported` esiste già.

---

## Cosa NON dice questo documento

- **Non dice che il gate sia rotto.** Su claim contraddetti e su claim che
  rafforzano la fonte la promessa regge **8 volte su 8**, e il gate ferma **15
  dei 16** claim non supportati che gli ho dato.
- **Non è un numero sul prodotto.** Tutti i banchi usano fonti **corte e
  costruite da me**, in **italiano**, con **un** giudice (il cross-encoder
  locale). Un altro modello può comportarsi diversamente.
- **Non spiega perché** il giudice punteggi alto un irrilevante. Ho provato e
  falsificato cinque spiegazioni in due giorni (forma tabellare, lingua,
  soggetto-clitico, due-numeri-per-soggetto, distanza semantica). **La causa
  resta ignota, e la lascio tale.**

## Due lezioni di metodo, che valgono oltre questo caso

1. **Non collassare «il layer X ha detto» con «il sistema ha fatto»: sono due
   popolazioni.** Tenerle separate ha fatto emergere due reperti — il buco
   (8 vs 2) e la polisemia (0 respinte dal giudice, 1 fermata dal gate). Un
   numero solo avrebbe detto «tutto bene» **oppure** «una su dieci fallisce», e
   nessuna delle due sarebbe stata vera.
2. **Casi discreti non distinguono il modello dalla taratura.** Per sapere se
   una scala è schiacciata bisogna darle qualcosa di **continuo** da misurare.

**Agent: Galileo**
