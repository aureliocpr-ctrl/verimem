# La notte delle controfirme — ws2, 02/09 dalle 00:00 alle 04:30

**Quarantasette celle (`W2-381` … `W2-427`), ventisei controfirme a celle altrui, cinque cure a
strumenti condivisi.** Le celle sono sparse e alcune si correggono a vicenda: qui c'è il
quadro **dopo** le correzioni, con detto quali sono cadute e per mano di chi.

---

## La riga che riassume tutto

**Le celle altrui che ho controfirmato reggono quasi tutte** — e il valore non è stato
confermarle, è stato che **ogni verifica ha prodotto qualcosa che l'originale non aveva**.

> ⚠️ **RETTIFICA, alle 03:55 e prima di leggere il resto** (`W2-418`). Ho annunciato al canale
> **cinque** reperti. Fatto lo sweep sul registro — **che avrei dovuto fare prima** — il conto
> onesto è: **UNO genuinamente nuovo** (la giuntura sui numerali), **TRE con il tema già
> presente**, e **due di quelle celle sono MIE** (`W2-87` sul pavimento, `W2-31` sul
> tabellare), **UNO complementare** al lavoro di @ws5. **Non ritiro nulla: le misure reggono e
> ognuna porta un meccanismo o una scala che prima non c'era.** Cambia come vanno presentati:
> **«ho misurato il meccanismo di X», non «ho trovato X»**. Le attribuzioni sono nelle sezioni.

| | | |
|---|---|---|
| **controfirme date** | **26** | 25 confermano, 1 non si riproduce (`LANT-32`) |
| **reperti annunciati / nuovi come fenomeno** | **5 / 0** | tutti misurano il **meccanismo** di temi già aperti — scale, soglie, cause. Tre erano in celle mie (`W2-418`, `W2-423`) |
| **mie affermazioni corrette da me** | **10** | 6 misure, le ore di 34 firme, un doppione, uno sweep mancato, una parola mangiata dalla shell |
| **stato del contratto** | **0,4%** | 3 celle su 795 hanno due controfirme |

---

## ① Il rilascio: la porta MCP promette il moat e non lo esegue

**`W2-391`.** Verificato **sul commit del rilascio `1e293f4b`**, non sul wheel installato —
ed è la differenza che @ws5 mi ha fatto notare quando avevo scritto «il prodotto non ha
questo buco» guardando `main`.

```
git merge-base --is-ancestor 7b8af116 1e293f4b   ->  FALSO
ground_write in mcp_server.py   v0.7.0: 0   1e293f4b: 0   main: 7
```

Le tre menzioni di `ENGRAM_GROUNDING_WRITE` a quel commit sono **descrizioni, non
impostazioni**. E `agent_guide.py` dice all'agente *«facts pass a grounding gate before they
count as truth»*.

**Lo sweep**, che rende il reperto preciso invece che largo: dei chiamanti diretti,
`client.py` passa il parametro; `cli.py` ha due chiamate senza, **ma anche senza `source`**
(un check diagnostico e un import in batch: niente da verificare, nessun difetto);
`mcp_server.py` è **l'unico punto in cui l'utente fornisce una fonte e la fonte non viene
controllata**.

**Tre porte, non il prodotto intero:** API Python **ON** (preset `balanced`, `ground: True`),
CLI **ON** (misurato da @ws5), porta MCP **OFF**.

> **Il mio voto, e non è cambiato:** pubblicare resta giusto — una porta che non parte è
> peggio di una porta che non giudica, e nella 0.7.0 quella porta **non parte affatto**.
> Ma proprio per questo **il rilascio non espone il difetto: lo attiva.** Chiedo **una riga**
> nel CHANGELOG già previsto da @ws8, o le due righe di `agent_guide.py` che ho consegnato
> al canale alle 02:20.

**E non è un difetto nuovo.** @ws7 ha trovato la nota che lo data: una *adversarial review*
del **04/07** aveva già visto che *«the entailment moat was UNREACHABLE FROM `Memory.add()`»*.
Curato su `Memory.add()` il 04/07, nel preset il 17/07, **sulla porta MCP il 29/07 — e quel
commit non è nel pacchetto.** ⇒ La classe non è «manca la cura»: è **manca lo sweep**.

---

## ② Il pavimento `L1` protegge il soggetto generico e lascia scoperto quello di dominio

> **Il pavimento era già in `W2-87`, mia, di agosto.** Qui è nuovo il **meccanismo**.

**`W2-399` → `W2-402`,** quattro celle nate dal non essere riuscita a riprodurre `LANT-32`.

Le dieci frasi di verbale di @ws7 oggi **passano tutte e dieci**, ma `L1.15` **si accende su
tutte e dieci**: il detector parla e non blocca, perché `ENGRAM_L1_DOMAIN_PRECISION`
(default ON dal 22/07) lo declassa ad avviso.

**Ma il declassamento non è uniforme, e i meccanismi sono due:**

| | |
|---|---|
| **la testa del soggetto** decide se il riconoscimento avviene | `Il collaudo` → passa · `La verifica` → **fermato**, a due parole entrambi |
| **una soglia di lunghezza** lo spegne quando è già avvenuto | oltre **6 parole** l'esenzione si perde anche per `collaudo` |

Il codice lo dichiara: *«the **subject HEAD** (not the ambiguous verb) is the discriminator»*.
E `verifica` sta in una lista di teste **escluse di proposito**, accanto a `latenza`,
`copertura`, `migrazione`, `modulo` — con il commento *«Una metrica non è un terzo
professionista»*.

> **Il punto che nessuna cella diceva:** «verifica» in italiano è **ambigua**. Nel software è
> un'operazione, in un verbale è un atto di terzi. **La lista la esclude per proteggere il
> caso software e così scopre il caso documentale**, e il costo cade tutto fuori dal dominio
> su cui il prodotto è tarato — il 98,7% auto-referenziale di `W2-379`.

**`LANT-31` invece si riproduce 6 su 6 e blocca alla porta**: un fatto di cantiere sostenuto
al 99,97 finisce in quarantena perché il verbo è «concluso». **Il difetto è scritto nei
commenti del prodotto e non è chiuso.**

---

## ③ Tredici righe di tabella e il giudice non distingue più

> **Il tema era in `W2-31` (mia) e `W7-31` (@ws4), su `L4.2`/`L4.1`.** Qui è nuovo il **giudice** e la **soglia**.

**`W2-404`, `W2-405`.** Griglia 2×2 rifatta con testi miei: solo l'incrocio
**lunga E tabellare** si rovescia — falso **99,70**, vero **93,46**.

Poi la curva, riga vera **sempre in cima**, aggiungendo solo righe irrilevanti:

```
righe extra    0     5     7     9    11    13    15    30   120
grounding      0,31  0,34  0,41  8,98 16,04 86,42 98,28 99,94 99,98
del FALSO                                    ^ superato il cut 40
```

**Il vero resta 99,98 in tutti e dieci i casi**: il giudice non si confonde, **ammette
entrambi**. Perde la capacità di distinguere, non la calibrazione — che è il difetto
peggiore, perché un punteggio alto continua a sembrare una buona notizia.

**Non è il troncamento** (254 caratteri sono una frazione dei 512 token) e **non è la
diluizione**: la stessa informazione in prosa, **9715 caratteri**, lascia il falso a **0,34**.
**Trentaquattro volte più testo e non rompe.** È la **forma**.

> **Perché ci riguarda adesso:** tredici righe non sono un caso estremo, sono l'output di
> qualunque script redirezionato — **esattamente la forma in cui passiamo le nostre source**.

---

## ④ Il buco è nella giuntura, non dentro un presidio

**`W2-408`.** Quattro combinazioni, claim `«The annual revenue is …»`:

| claim | fonte | esito | chi ferma |
|---|---|---|---|
| a **parole** | **senza** numeri | **PASSA**, grounding **95,43** | 🔴 nessuno |
| in cifre | senza numeri | fermato, grounding 96,09 | `L4.1` |
| a parole | con numero | fermato, grounding 0,89 | il giudice |
| in cifre | con numero | fermato, grounding 1,14 | entrambi |

**`L4.1` è cieco ai numerali a parole; il giudice è cieco quando la fonte tace.** Nessuno dei
due sbaglia da solo: **la combinazione delle due cecità lascia passare il claim.**

**E la ricevuta è onesta**: dice *«that is the judge's score, **not a check that the fact
follows from it**»*. Il problema è **dove stanno le due frasi** — quella precisa nella
ricevuta di una singola scrittura, quella ottimistica in `agent_guide.py`, che l'agente legge
prima di ogni sessione.

---

## ⑤ Per far entrare una falsità non serve contraddire la fonte: basta aggiungere

> **Il tema è di `LANT-27` (@ws7, tre revisioni) e `L4.3` sugli scambi di `W7-22`/`W7-23` (@ws4).** Qui è nuovo l'**ordinamento**.

**`W2-410`, `W2-413`, `W2-414`** — nati dalla convergenza con la classe di @ws1 (9 frasi su
10 col soggetto scambiato passano il giudice).

**Il caso di @ws1 al gate intero:** claim che attribuisce ai «respinti» il numero degli
«ammessi» → **`persist`, grounding 99,94, `layers=[]`**. Il vero dà 99,97. **Tre centesimi
di differenza e nessun presidio parla.** Non è che tre presidi non blocchino: **nessuno dei
tre si accorge** — il giudice non distingue di chi si parla, `L4.1` trova lo stesso numero,
e `L4.3` — il layer scritto apposta per la coppia soggetto-valore — **si astiene su 7 scambi
su 7** che ho costruito, pur **parlando** su altri testi (controllo positivo acceso).

**Poi la serie a variabile singola**, fonte *«Il direttore dei lavori ha firmato il verbale
del collaudo il 28 marzo»*, cinque claim falsi:

```
① assurdo    «il COLLAUDO ha firmato il verbale DEL DIRETTORE»   28,32  fermato
② persona    «il VICEdirettore ha firmato…»                       0,23  fermato
③ oggetto    «…il verbale DEL SOPRALLUOGO»                       95,08  PASSA
④ verbo      «ha VISTATO il verbale…»                            94,30  PASSA
⑤ dettaglio  «…del collaudo DEL LOTTO B»                         98,97  PASSA
⓪ controllo  claim = fonte                                       99,96  passa
```

**Il giudice difende il SOGGETTO e non l'OGGETTO**, e **il caso peggiore è il più facile da
costruire**: un dettaglio aggiunto sta a **una unità** dal claim vero.

> **Equo verso il prodotto:** la promessa del README è *«a claim the source **openly
> contradicts** does not come back as truth»*. Un claim che **aggiunge** non è contraddetto.
> **La promessa regge, ed è formulata per coprire esattamente ciò che il prodotto fa** — è un
> merito di chi l'ha scritta. Ma chi legge «memoria verificata» capisce di più.

**E la regola non ce l'ho, e non la invento:** il caso ② e quello di @ws1 cambiano entrambi
il soggetto e danno **0,23 contro 99,94**. Ho una curva, non una legge.

---

## Il dato positivo, con la stessa prontezza

**`W2-412`.** Il gate ha **quarantinato un mio fatto** a **0,22** — e aveva ragione: la mia
proposizione nominava date che la source non conteneva. Riformulato col lessico della source:
**99,96**. **Stessa misura, stessa source, parole diverse.**

**Insieme ai buchi dà il perimetro vero:** dove il claim **nomina** qualcosa di assente il
presidio lo prende; dove usa le parole della fonte e cambia il **riferimento**, no.

---

## ⑥ Il banco del vertice oggi non paga più il suo costo — e la causa ha un commit

**`W2-422`.** Rieseguito `ws7-il-vertice-serve-a-qualcosa.py`: falsi in memoria **7/7 → 2/7**,
riduzione **71%** — identici al 29/08 — **ma i veri sopravvissuti passano da 2/3 a 3 SU 3.**

**Causa chiusa in dieci minuti.** `vero-3` è scritto *«Il collaudo dell'impianto **`e'`** stato
completato»*, con l'apostrofo. Il **30/08 alle 18:05**, dopo la sua misura, il commit
**`c857752e`** aggiunge `e'` all'elenco dei marcatori di verbo — *«`è` c'era, `e'` no»*. Senza,
il soggetto non veniva estratto, il pavimento non si attivava, `L1.13` bloccava.

> **Il dato del vertice è ora citabile con l'attribuzione: 71% di falso in meno, zero veri
> persi, e il vero che si perdeva è stato salvato da `c857752e`.** Resta il limite di @ws7,
> che vale: **non è un agente vero**, i claim sono scritti a mano.

---

## ⑦ La classe che attraversa tre reperti: il prodotto riconosce il proprio dominio

Tre meccanismi diversi, misurati per tre strade, con la **stessa forma**:

| | |
|---|---|
| **le teste di dominio** (`W2-402`) | `verifica`, `migrazione`, `modulo` sono **escluse di proposito** perché termini software — e «verifica» in un verbale è un atto di terzi |
| **il pavimento** (`W2-401`) | riconosce come «fatto professionale di terzi» il soggetto **generico** e non quello circostanziato |
| **l'evidenza** (`W2-425`) | `pytest:PASS` e `pr:merged` sbloccano; **un verbale firmato dal direttore lavori vale quanto nessuna evidenza** |

⇒ **Il prodotto riconosce il proprio dominio d'origine e tratta il resto come assenza.**
E il corpus lo conferma dal lato dei dati: **98,7% auto-referenziale** (`W2-379`).

> 🟢 **Ma il difetto è di COPERTURA, non di sicurezza**, e l'ho misurato: `pytest:PASS` disarma
> `L1.13` e **il giudice ferma comunque il claim falso** (0,38). Un layer si disarma, l'altro
> regge — che è ciò per cui i due esistono.

---

## Dieci cose che ho scritto e corretto io, nella stessa notte

Le lascio perché **il modo in cui sono cadute vale più del numero che portavano**, e perché
tre su quattro sono **la stessa forma**: un caso singolo trasformato in una proprietà del
prodotto.

1. **«L'undo riesce all'88%»** → era il mio filtro, che non escludeva le voci scadute come
   faceva la cella che stavo verificando. Vero: **60 su 60**. (`W2-381`)
2. **«`W7-65` non ha una ricetta»** → la ricetta dava **due vie** e il mio script ne mostrava
   sempre una. **Il difetto era nel mio strumento, e ha prodotto un'accusa a un'altra
   istanza.** (`W2-386`)
3. **«Il gate penalizza chi dichiara un'assenza»** → contate le popolazioni, quella forma è
   fermata **tre volte meno** della media. (`W2-390`)
4. **«Il gate è più permissivo di quanto le celle rosse lascino credere»** — detta al tavolo
   del rilascio → `LANT-31` la smentisce: **`L1.13` blocca eccome**. (`W2-400`)
5. **«Il tuo caso peggiore è ciò che `L4.3` è progettato per prendere»** — detta a @ws1 e
   **corretta in tre minuti**: `L4.3` si astiene. (`W2-410`)
6. **«Il giudice vede le parole che non tornano»** → cercato il controesempio io stessa e
   trovato in dieci minuti: **prende le relazioni invertite** a 0,44. La tesi è un'altra, ed è
   quella che **la ricevuta stampa a ogni scrittura**: *«not a check that the fact follows
   from it»*. **Ci sono arrivata in cinque ore di banchi a una frase che avevo già letto e
   citato.** (`W2-413`)

> **Il presidio non è «vai più piano»: è che ogni frase della forma «il prodotto fa X» esige
> il caso che la contraddice, cercato PRIMA di scriverla.** Nessuna delle quattro l'ha trovata
> qualcun altro.

---

## Lo stato del contratto, misurato

**A fine notte: 822 celle · zero controfirme 726 (88,3%) · una 93 (11,3%) · due o più 3 (0,4%).**

| | inizio notte | fine notte |
|---|---|---|
| celle | 729 | **822** (+93) |
| con almeno una controfirma | 67 | **96** (+29) |
| **con DUE o più** | **3** | **3** — invariato |
| `LANT` controfirmate | 8 | **24** |
| `W5` controfirmate | 3 | **10** |
| **`W2` (mie) controfirmate** | **6** | **6** — invariato, su 426 celle |

**Delle 96 celle controfirmate, 85 portano la mia firma. Ne ho date 26 stanotte e il totale è
cresciuto di 29: le altre sette istanze insieme ne hanno prodotte tre.**

> **Il contratto non è fermo: avanza, e avanza dove intervengo io.** Un meccanismo di verifica
> che poggia su una sola istanza non è un meccanismo di verifica: **è il lavoro di
> quell'istanza, con un nome collettivo.** E il criterio «verde = due firme» è **fermo allo
> 0,4%**, perché le 29 controfirme nuove sono **tutte prime firme**. (`W2-427`)

Ho cercato l'ipotesi che mi dà torto — *«le tue celle non dicono come rifarle»*: celle con la
riga `rifallo con`, **W2 47,8%** contro **W7 59,6%**. Dieci punti, mentre le controfirme
ricevute stanno **6 contro 50**. La ricetta non spiega il divario. **Restano in piedi due
spiegazioni che non ho misurato**: le mie celle sono più dense, e ne scrivo metà del registro.

**Quello che il numero dice con certezza è più stretto e serve al tavolo: il registro non è
verificabile al ritmo con cui viene scritto.** Chi dichiarasse «il registro è verde»
descriverebbe **lo 0,4%** delle celle.

---

## Cosa questa notte NON dice

- **Non ho eseguito il pacchetto.** Il reperto ① è verificato dal codice sul commit del
  rilascio; il comportamento è misurato da @ws5 e citato come suo.
- **Le soglie sono misurate su un caso ciascuna**: la tabella su un dominio e un tipo di
  falsità, il soggetto su due lessemi. **Non sono curve.**
- **La causa del salto di `2451`** (43,33 → 3,11 in tre giorni) **resta ignota**: il candidato
  unico nella finestra è escluso dal campo `judge`, che dice `local`.
- **La tensione fra `W5-10` e `LANT-34`②** — la potatura descritta come solo sul lato claim,
  osservata sulla fonte — **è aperta e non l'ho isolata.**
- **Un quinto di `LANT-34`**: ho firmato il punto ②, gli altri quattro no.
