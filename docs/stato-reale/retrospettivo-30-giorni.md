# Il retrospettivo a 30 giorni — cosa dicono i nostri log

**Estratto il 02/09/2026 fra le 00:00 e le 01:00 dallo store di casa, in sola lettura.**
Finestra: 30 giorni. Ogni numero qui sotto è ricavato da una query sul database, non da un
banco costruito. Le celle del registro che li portano sono citate riga per riga.

> **Perché esiste questo documento.** I quattro case-study nascono sparsi su undici celle
> (`W2-368` … `W2-378`), due delle quali **smentiscono** le precedenti. Un lettore esterno
> non le ricompone: qui ci sono i numeri **dopo** le smentite, con detto quali sono caduti.

---

## La riga che riassume tutto

**Tre meccanismi sullo stesso corpus danno tre verdetti diversi.**
Chi dicesse «la memoria funziona» o «la memoria è rotta» sbaglierebbe due volte su tre.

| | meccanismo | verdetto | il numero |
|---|---|---|---|
| **(a)** | presidio in **ingresso** | 🟢 **regge** | 0 claim sostenuti persi su 512 fermati |
| **(b)** | memoria **dopo** la scrittura | 🔴 **erode** | 333 su 395 non corretti ma **sostituiti** |
| **(c)** | **reversibilità** | 🟡 **inerte** | 228 annullabili, **0 annullati** |
| **(d)** | rilevatore di **conflitti** | 🟡 **rumore** | 5 coppie lette su 5, nessuna era un conflitto |

---

## Il protocollo — quattro famiglie, ognuna su DUE campi

La regola del protocollo è una sola: **ogni famiglia si conta sul campo che registra
l'evento E su quello che registra l'AZIONE**, perché *rilevare* e *agire* sono popolazioni
diverse e il prodotto le tiene separate. Chi conta solo la prima misura il rumore.

| famiglia | fonte | evento | azione |
|---|---|---|---|
| errori bloccati | `facts` | `status='quarantined'` | `quarantined_by` (**chi** ha deciso) |
| memoria che degrada | `facts` | `superseded_at` | `superseded_reason` |
| reversibilità | `facts_undo_log` | `created_at` (occasioni) | `undone_at` (usi) |
| contraddizioni | `contradictions` | `detected_at` | `resolved_at` |

**Estrazione, 30 giorni:** 9914 fatti scritti · 911 fermati (9,2%) · 545 sovrascritti ·
6302 contraddizioni rilevate e 414 risolte · **343 occasioni di annullamento e zero usi**.

---

## (a) Il presidio in ingresso regge — e la prova è la popolazione di controllo

| | mediana grounding | sotto 50 | sopra 80 |
|---|---|---|---|
| **fermati** dal moat (512) | **0,5** | — | **0** |
| **ammessi** (8860) | **100,0** | **0** | — |

**Le due popolazioni non si sovrappongono**: nessun ammesso sotto 50, nessun fermato sopra
80. Fra 65 e 100 c'è una fascia vuota e il presidio la usa tutta.

I 21 casi con grounding intermedio erano i candidati a falso positivo. **Ne ho letti quattro
e non lo sono**: sono tutti **frasi con più affermazioni** — *«il file pesa 1657615 byte **ed
è stato caricato** il…»* — dove la fonte ne sostiene una e non l'altra. **Non è il presidio
che sbaglia: è chi scrive che gli chiede di giudicare due cose come una.**

→ `W2-371`. **Limite:** «vero» significa *sostenuto dalla fonte secondo il giudice*, non vero
nel mondo. Se il giudice sbaglia, sbagliano entrambe le popolazioni insieme.

---

## (b) La memoria erode dopo — ed è il case-study che vale

Delle **395** sovrascritture `same-source evolution` (il 72,5% di tutte):

| | |
|---|---|
| numeri **identici** → riformulazione | 20 |
| numeri **diversi** → **dice altro** | **333 (84,3%)** |
| senza numeri, non decidibile così | 42 |

**Cinque lette prima di pubblicare, cinque sostituzioni vere.** La più grave:

```
VECCHIO   «L4.3 segnala 2 scambi su 6»          ← la COPERTURA
NUOVO     «L4.3 produce 0 falsi positivi su 6»  ← la PRECISIONE
```

Due metà della **stessa misura sullo stesso banco**, e la seconda ha cancellato la prima.
**Oggi il registro sa che quel livello non sbaglia e non sa più quanto copre.** Non è un
fatto vecchio superato: **è metà di un A/B distrutta dall'altra metà.**

Il meccanismo ha il nome che il prodotto stampa: `same-source evolution` **presume che la
stessa penna stia correggendo sé stessa**, mentre nell'84,3% dei casi sta scrivendo altro.

→ `W2-369`. **Limite:** criterio sui numeri, i 42 senza numeri restano fuori; 5 casi letti su
333, presi a intervallo fisso e non a caso vero.

---

## (c) La reversibilità è inerte — e una parte del danno è ancora recuperabile

Dei **333** fatti sostituiti:

| | |
|---|---|
| avevano una voce nel registro undo | **228** |
| **annullati** | **0** |
| finestra di annullamento **scaduta** | 26 |
| **recuperabili adesso** | **202 annullabili**, di cui **~178 davvero recuperabili** |

L'ultima riga non è una deduzione: `undo` è stato provato **dalla porta MCP su una copia
consistente dello store**, su un campione di 25 casi reali — **22 riusciti, 3 falliti**, con
`superseded_by` tornato `NULL` su 22. **Il tasso è 88%, non 100%.** La causa dei 3 falliti
non è nota. (`W2-380`)

**La riga «0 usi su 343» non era una curiosità sull'ergonomia: era il conto di un danno che
stava maturando.** Il prodotto sa tornare indietro, l'ha registrato 228 volte per questi
casi, e non gliel'ha chiesto nessuno.

→ `W2-370`. **Non propongo di annullarli**: è una decisione collegiale e tocca lo store di
casa. Il numero è qui.

---

## (d) Il rilevatore di conflitti produce quasi solo rumore

**5956** contraddizioni non risolte nella finestra, di cui **5616 con entrambi i lati ancora
vivi** — quindi non è archeologia: se fossero conflitti veri, sarebbero conflitti attivi.

**Cinque coppie lette dalla più simile in giù. Nessuna si contraddice.** La prima vale per
tutte:

```
A   «...le supersessioni scritte DAL 25 agosto...»
B   «...le supersessioni scritte PRIMA DEL 25 agosto...»      similarity 0,994
```

Due finestre **complementari**, entrambe vere, lette come conflitto perché i testi
differiscono di **una preposizione**. ⇒ **Il rilevatore misura la somiglianza, non
l'incompatibilità**, e su un corpus dove tutti scrivono di commit e percentuali la
somiglianza lessicale è altissima fra fatti che non c'entrano niente.

**Il 414 su 6302 non è pigrizia di chi non risolve: nel 93,4% dei casi non c'era niente da
risolvere.**

### Un criterio che riduce il lavoro del 96,5%

Una contraddizione vera richiede che i due fatti **parlino dello stesso oggetto**. Cercando
gli identificatori condivisi (SHA, nomi di file, sigle di layer):

| | |
|---|---|
| condividono un oggetto → **da guardare** | **195 (3,5%)** |
| nessun oggetto in comune → scartabili | 5421 (96,5%) |

**Verificato su entrambe le popolazioni**, che è ciò che lo rende credibile: fra le scartate,
0 conflitti veri su 5 letti; **fra le promosse, 1 su 3** — e quella vera è:

```
agent_guide.py, stessa riga:  risulta TRUE  ...  risulta FALSE
```

Non prova che i 195 siano tutti veri: **prova che i due gruppi non sono la stessa
popolazione**. Chi vuole ripulire non deve guardare 5616 coppie ma **195**.

→ `W2-372`, `W2-373`.

---

## Due celle di questo retrospettivo sono state smentite, da me

Le lascio scritte perché **il modo in cui sono cadute vale più del numero che portavano.**

**① `W2-374` diceva:** *«i 105 senza traccia annullabile sono tutti anteriori al registro,
buco vero zero»*. La prova era la prima voce **nei dati** (24/08).
**Smentita da `W2-376`:** `git log -S` mostra che il codice ha l'handle dal **04/08 22:49**
(`f288bbe2`, *«ogni ritiro lascia l'handle di undo»*). **Venti giorni di scarto.**
Ricontato: 8 archeologia, **97 buco vero**, 0 dopo il 24/08.

> **Avevo usato il DATO come prova dell'esistenza della FUNZIONALITÀ.**
> E l'errore è esattamente il limite che avevo enunciato tre minuti dopo su un altro caso,
> senza tornare indietro ad applicarlo. ⇒ **Dichiarare un limite non lo chiude, e non
> retroagisce: la cella già pubblicata resta sbagliata finché qualcuno non la rilegge.**

**② La causa dei venti giorni resta APERTA**, e ho escluso quattro spiegazioni **per misura**:

- il codice mancante — **falso**, `f288bbe2` è in `main`
- lo store non allineato — **improbabile**, 634 commit su `main` in quel periodo
- il percorso che non registra — **falso**, 274 `same-source` hanno la voce, `op_type` è
  `supersede` in 343 casi su 343
- un tratto di contenuto — **escluso**: nella finestra le `same-source` **senza** voce sono
  **113** e quelle **con** voce **zero**. Non c'è gruppo di confronto: **è un interruttore
  spento per venti giorni e poi acceso**, non una proprietà dei fatti.

→ `W2-374`, `W2-376`, `W2-377`, `W2-378`.
**Chi riprende non riparta da lì**: va cercato qualcosa **acceso il 24/08 verso le 19:00 che
non è un commit su `main`** — una variabile d'ambiente, una migrazione dello schema, o
l'adozione del codice su questa macchina.

---

## Cosa questo retrospettivo NON dice

- **Lo store è uno solo, il nostro, e ora il limite è MISURATO: solo 127 fatti su 9936
  (1,3%) nominano un dominio esterno — il corpus è al 98,7% auto-referenziale**, e anche
  quei 127 sono casi di banco costruiti da noi, non fatti scritti da chi fa il suo lavoro.
  ⇒ I quattro verdetti valgono per **un agente che documenta sé stesso**, che è il caso
  d'uso dichiarato del prodotto. **Non valgono per un agente che gestisce fatture o
  cartelle cliniche**, e nessuno li citi come se valessero. (`W2-379`)
- **Le contraddizioni totali sono 93868 contro 6302 nella finestra**: il grosso è
  **archeologia**, quindi ogni tasso su quella tabella va dichiarato con la finestra o inganna.
- **Il campione letto è piccolo ovunque**: 5 casi su 333, 4 su 21, 5 su 5616, 3 su 195. Sono
  **indizi con la direzione, non tassi**, e ogni cella lo dichiara.
- **La causa del buco di venti giorni non è nota.** Il documento dice cosa **non** è.
