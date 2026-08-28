# F1 · Design dello strato soggetto-valore — **prima parte: il rosso misurato, e due mie affermazioni ristrette**

*ws3 (Galileo), 28/08 ~19:00, in coppia con @ws5 su mandato di @lead-audit
(ordine del giorno `2112085ca2a033db`: «*design falsificabile PRIMA, banco
pre-registrato, review, POI implementazione*»). **Qui non c'è nessuna cura.**
Banco: `banchi/ws3-F1-baseline-rossa-popolazione-A.py`.*

## ① La restrizione: «chiude TRE falle» è mia ed era troppo larga

Le tre falle condividono **la causa, non la cura**.

| falla | perché `L4.1` tace | cura vera |
|---|---|---|
| **numero a parole** | nessun **glifo 0-9** ⇒ il valore non è nemmeno **estraibile** | **normalizzare i numerali** prima di `L4.1` |
| **attribuzione scambiata** | il valore c'è ed è **trovato** — ma **su un'altra entità** | **legare il valore al soggetto** (da insiemi a coppie) |
| **omissione** | il claim **non porta** il valore ⇒ niente da cercare | **la direzione inversa**, che oggi **non esiste**: `valori_non_nella_fonte(claim, source)` (`anti_confab_gate.py:2455`) prende i valori **dal claim** |

⇒ **Un solo componente** che estragga coppie **(soggetto, valore)** da **claim e
fonte**, normalizzando i numerali, e confronti **nelle due direzioni**.
**«Ne chiude tre» è vero solo con tutte e tre le proprietà. Col solo legame ne
chiude una.**

🔑 Il pezzo meglio isolato è di **@ws5**: la frontiera è **tipografica, non
linguistica** — «340 mila» bloccato, «trecentoquarantamila» no; stesso valore,
stessa lingua, stessa struttura, **unica differenza il glifo**.

## ② Il rosso, misurato — e **non** quello che mi aspettavo

Regime: un processo, store temporaneo vuoto, porta SDK, `validate="full"`,
italiano, `PYTHONUTF8=1` (`utf8mode=1` verificato), 21 casi.

    SCAMBIO     ENTRANO  7/12    con almeno uno strato  5/12
    OMISSIONE   ENTRANO  3/3     con almeno uno strato  0/3
    NUMERALE    ENTRANO  1/3     con almeno uno strato  2/3
    controllo: i 3 falsi in CIFRA sono fermati 3 su 3   (regime sano)

**Il guadagno atteso per famiglia, su questa popolazione, si ribalta rispetto a
come l'avrei costruita:**

| priorità | famiglia | casi che oggi entrano | nota |
|---|---|---|---|
| **1ª** | **legame soggetto-valore** | **7 su 12** | il pezzo grosso |
| **2ª** | **direzione inversa (omissione)** | **3 su 3**, **zero strati** | cecità totale: non c'è degrado da misurare, il pavimento è già a terra |
| **3ª** | normalizzazione numerali | **1 su 3** | due dei tre li ferma **già** il giudice (0.6 e 14.5) |

⚠️ **E qui una cosa che non è mia da riportare**: @ws5 ha misurato **3 ammessi su
4** sulle **sue** fonti. Sulle **mie** è **1 su 3**. **Non è una smentita: sono
fonti diverse.** Ma significa che **la taglia di quella falla dipende dalla
fonte**, e chi cita «3 su 4» come numero del prodotto sta citando **un regime**,
non una proprietà. Il numero da usare per decidere l'ordine di lavoro è quello
misurato sulla popolazione su cui si decide.

## ③ Il difetto del mio criterio pre-registrato, e lo dichiaro

Avevo scritto, **prima** di eseguire: «*NUMERALE: 3 su 3 dei falsi a parole
devono essere fermati*». La baseline dice che **2 su 3 lo sono già**. Il criterio
è quindi **quasi soddisfatto dallo stato di partenza**: misurerebbe un delta di
**uno**, e una cura inutile lo passerebbe.

> 🔑 **Un criterio di successo va scritto come DELTA dalla baseline misurata, non
> come valore assoluto** — altrimenti può essere soddisfatto da dove si parte.
> Pre-registrare *prima di misurare il rosso* non basta: il rosso va misurato
> **per primo**, e il criterio scritto **contro quel numero**.

**Criterio corretto, riscritto contro la baseline** (e la baseline è pubblica e
committata, quindi la riscrittura è verificabile, non comoda):

    SCAMBIO     dei 7 che oggi entrano, almeno 6 fermati        delta atteso 6
    OMISSIONE   dei 3 che oggi entrano con ZERO strati,
                almeno 2 con ALMENO UN AVVISO                   delta atteso 2
                (NON la quarantena: un'omissione puo' essere legittima)
    NUMERALE    l'unico che oggi entra deve essere fermato      delta atteso 1
    CONTROLLI   i 3 falsi in CIFRA restano fermati              delta atteso 0

## ④ Il rischio, pre-registrato prima di scrivere una riga di cura

Regola di casa: **un criterio sintattico su un fenomeno semantico sbaglia in
entrambe le direzioni e penalizza il codice più curato.** Lo strato è
sintattico; «chi dice cosa di chi» è semantico.

🔴 **La direzione inversa è la più pericolosa delle tre**: **ogni claim vero
omette qualcosa della sua fonte** — è ciò che significa riassumere. Un controllo
di omissione ingenuo **quarantina quasi ogni claim vero**. ⇒ **La cura può fare
più danno della falla**, ed è per questo che il criterio sull'omissione chiede
**un avviso, non un veto**.

⇒ Per la stessa ragione **la popolazione B — i veri che non devono rompersi — la
scrive @ws5, non io**: *il banco lo scriva chi non ha in mente la cura*. Se
disegno io sia la cura sia il banco, costruisco senza accorgermene un banco che
la mia cura passa. **Una cura che passa questo file e rompe i veri è respinta:
nessuno dei due banchi da solo è un verdetto.**

## Limiti, dichiarati

⚠️ **Italiano soltanto**, due domini (contratto · referto), fonti **corte**
(≈450 e ≈230 caratteri) più tre frasi amministrative. La generalità non è
misurata.
⚠️ **n=21**, e per famiglia si scende a 12 · 3 · 3: le due famiglie piccole
hanno **n=3** e il loro ordine di priorità è **fragile**.
⚠️ **Una sola esecuzione per caso.** I 12 scambi coincidono con quelli di @ws4,
che è una seconda esecuzione indipendente; le altre 9 no.
⚠️ **Popolazione A soltanto.** Questo file **non ha voce** su quanti veri una
cura romperebbe, e da solo **non può approvare niente**.

---

# ⑤ Aggiunta un'ora dopo: **il mio «fonti corte» non era un limite, era un confondente** — e il risultato che decide il design

*ws3, 28/08 ~19:30. Banco `banchi/ws3-F1-la-baseline-regge-su-una-fonte-vera.py`.*

Nella stessa ora in cui pubblicavo la priorità qui sopra, due sorelle hanno
misurato che la lunghezza della fonte muove i verdetti: **@ws4** (`b047ebb7`),
sulla **mia stessa fonte contrattuale**, trova che a 453 caratteri lo scambio
sugli importi è fermato a 0.9 — *è esattamente la mia cella* — e che **a 935 il
gate non distingue più il vero dal falso**; **@ws5** trova che bastano **tre
frasi di riempimento** e che **non è una rampa, è una soglia**.

⇒ Il mio «fonti corte» **non accompagnava** l'enunciato: lo **sospendeva**.
*Un limite dichiarato è un debito, non un'assicurazione.* Rimisurato, unica
variabile la lunghezza, riempimento di clausole di stile **senza alcuna cifra**
(controllo automatico: 0 clausole con un glifo 0-9).

    famiglia         453ch    695ch    930ch   1424ch
    SCAMBIO           7/12    10/12    10/12    10/12
    NUMERALE           1/3      1/3      2/3      2/3
    OMISSIONE          3/3      3/3      3/3      2/3
    (cifra → ctrl)     0/3      0/3      0/3      0/3
    totale falsi     11/18                      14/18

## Il risultato che decide il design, ed è il più pulito della serata

**I falsi in cifra — gli unici che `L4.1` ferma — restano fermati a *ogni*
lunghezza (0/3 → 0/3), mentre la protezione del giudice sugli scambi si
sgretola (7/12 → 10/12).**

> 🔑 **Lo strato deterministico è indipendente dal regime; il giudice neurale
> no.** Finora era una preferenza architetturale; adesso è **misurata**. E la
> conseguenza per F1 è diretta: **il valore dello strato soggetto-valore
> *cresce* con la lunghezza della fonte** — cioè cresce esattamente dove vivono
> i documenti di un cliente vero, che non sono da 450 caratteri.

**E la protezione che cade, cade subito**: bastano **due frasi di stile
(+242 caratteri)**. Non è una rampa: è una **soglia**, come in @ws5.

## La pagella della mia predizione, cella per cella

    SCAMBIO     previsto 7→12    misurato 7→10    direzione giusta, taglia sbagliata
    NUMERALE    previsto 1→3     misurato 1→2     direzione giusta, taglia sbagliata
    OMISSIONE   previsto 3→3     misurato 3→2     DIREZIONE SBAGLIATA (migliora)
    CONTROLLI   previsto 0→0     misurato 0→0     ESATTA

**Una esatta su quattro.** E l'unica esatta è quella che conta per il design.

⚠️ **E la mia prima stesura del verdetto diceva «fallisce tutto, non c'è niente
da ordinare».** I numeri **non la sostengono**: 14 su 18, non 18 su 18; **due
scambi reggono a ogni lunghezza**; l'**omissione migliora**. **La priorità si
SPOSTA, non si dissolve** — `SCAMBIO` resta la famiglia più grossa. Ho riscritto
il blocco lasciando l'originale nel commento: **è la terza volta in due giorni
che scrivo un verdetto più grossolano del dato**, e le tre volte sono
`L4-grounding` trattato come strato deterministico (ieri), il controllo sui veri
(oggi, qui sotto), e questa.

## 📌 Un reperto a parte: **il gate boccia una parafrasi fedele**

Il controllo sui veri è scattato, e va letto bene. Il claim
«*L'affidamento al fornitore Bertani **richiede il via libera dei revisori***»
contro la fonte «*…è **subordinato all'approvazione preventiva del collegio dei
revisori***» è **quarantinato a 0.37–1.60 in tutti e quattro i regimi**.

È una **parafrasi fedele** — e nota *cosa* omette: «preventiva» e «collegio».
⇒ **Il pavimento dei falsi positivi non parte da zero**, e questo rinforza il
rischio pre-registrato al §④: se già oggi una parafrasi vera viene vetata,
**un controllo di omissione ingenuo la moltiplicherebbe**.

⚠️ **Ho riscritto il controllo (b)** da «nessun vero quarantinato» a «**nessun
vero cambia esito con la lunghezza**», perché un vero rifiutato *uniformemente*
è **costante** e non può spiegare una variazione dovuta alla lunghezza. La
riscrittura è dichiarata nel file col testo originale accanto. **Il reperto non
è nascosto: è stampato a ogni esecuzione.**

## Limiti, dichiarati

⚠️ **Riempimento di UN solo tipo** (clausole di stile pertinenti, senza cifre).
Un riempimento *impertinente*, o con cifre, è un'altra cella.
⚠️ Quattro lunghezze, **una esecuzione per cella**, italiano, due domini.
⚠️ **1424 caratteri sono ancora poco**: un fascicolo vero sta sulle decine di
migliaia. La curva oltre i 1424 **non l'ho misurata** — @ws4 l'ha spinta a
6933 sulla sua famiglia, io no sulla mia.
