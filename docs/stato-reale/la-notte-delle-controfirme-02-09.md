# La notte delle controfirme — ws2, 02/09 dalle 00:00 alle 03:30

**Ventotto celle (`W2-381` … `W2-408`), sedici controfirme a celle altrui, cinque cure a
strumenti condivisi.** Le celle sono sparse e alcune si correggono a vicenda: qui c'è il
quadro **dopo** le correzioni, con detto quali sono cadute e per mano di chi.

---

## La riga che riassume tutto

**Le sedici celle altrui che ho controfirmato reggono quasi tutte** — e il valore non è
stato confermarle, è stato che **ogni verifica ha prodotto un reperto che l'originale non
aveva**. Tre buchi del prodotto sono venuti fuori così, non cercandoli.

| | | |
|---|---|---|
| **controfirme date** | **16** | 15 confermano, 1 non si riproduce (`LANT-32`) |
| **reperti nuovi nati da una controfirma** | **3** | il pavimento `L1`, la soglia tabellare, la giuntura sui numerali |
| **mie affermazioni ritirate da me** | **4** | tutte con la misura che le smentiva, tutte entro un'ora |
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

## Quattro cose che ho scritto e ritirato io, nella stessa notte

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

> **Il presidio non è «vai più piano»: è che ogni frase della forma «il prodotto fa X» esige
> il caso che la contraddice, cercato PRIMA di scriverla.** Nessuna delle quattro l'ha trovata
> qualcun altro.

---

## Lo stato del contratto, misurato

**795 celle · zero controfirme 711 (89,4%) · una 81 (10,2%) · due o più 3 (0,4%).**
**Delle 81 celle controfirmate, 73 portano la mia firma**: senza, il registro ne avrebbe 8.

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
