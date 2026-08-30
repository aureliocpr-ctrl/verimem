# Il prodotto è affidabile su ciò che sa di sé

*ws3 «Galileo», 30/08. Otto promesse **dichiarate** del prodotto, misurate una
per una fra le 12:19 e le 16:00. Le misure sono sparse in sei banchi eseguibili
e sparse **non le legge nessuno** — questo documento le mette in fila e, per
ognuna, dice anche **su quanti casi si applica**.*

---

## La tesi in una riga

**Ciò che il prodotto dichiara di sé regge. Ciò che nessuno ha dichiarato è dove
stanno i buchi.** Per un analista è una distinzione più utile di qualunque
tasso: dice **dove fidarsi** e **dove guardare**.

---

## Le otto promesse

Ogni riga: la promessa **come è scritta nel prodotto**, la misura, il commit.
La colonna che conta di più è l'ultima.

| | promessa (dove è scritta) | misura | esito | **su quanti casi si applica** |
|---|---|---|---|---|
| ① | «SDK processes keep the synchronous one-time load» — `CHANGELOG:635` | 3 processi freschi, fonte che NEGA: **0/6** ammissioni a giudice freddo, controllo 6/6 | 🟢 | ⚠️ **non misurato**: quanti usino SDK contro MCP non è osservabile da qui |
| ② | «first write ~32 s → 0.3 s» — `CHANGELOG:716` | **18–36 s → 0,2–0,3 s**, stesso ordine su altra macchina | 🟢 | **una volta per processo**; quanti processi freschi, non misurato |
| ③ | «it is `grounding_score` that carries it … `status` no» — istruzioni MCP | **3/3**, e **un campo in più**: il layer `L4-skipped` separa «fonte non giudicata» da «nessuna fonte» | 🟢 | si applica **a chi legge i campi** — vedi ⑧ |
| ④ | «a session NOTE skips that screen … **the moat is UNAFFECTED: with a source**» — `agent_guide` | screen saltato **2/2**, moat gira **2/2** | 🟢 | ⚠️ **frequenza alta, rischio misurato NULLO**: `W7-70/71` di *Paragone* ha **letto** 24 casi — **0 self-claim nudi**, 11 resoconti e 13 misure — e il controfattuale dice che **senza l'eccezione la porta ne declasserebbe 21 su 24**. ⇒ *compensazione, non buco* |
| ⑤ | la promessa ③, verificata **sulla porta dove è scritta** | firme **identiche** SDK/MCP: `['0.56/False','null/True','null/False']` | 🟢 | entrambe le porte, regime pulito |
| ⑥ | «only when neither an llm nor the local model is present does the gate fail-open» — `README:64` | **binario, non temporale**: `DELEGATE_ONLY` 0 e 1 → **0/6** a freddo con modello presente | 🟢 | **installazioni senza modello**; non misurabile da qui |
| ⑦ | `doctor` esiste per dire perché manca un punteggio | modello assente → **`status='fail'`**, dice il path, distingue «con fonte → avviso» da «**senza fonte → nessun avviso**» | 🟢 | chi esegue `doctor` |
| ⑧ | la separazione deve sopravvivere alla **lettura** | SDK `recall` → gs 99.56 / `None`; MCP `hippo_facts_search` → espone `grounding_score` **e** `meta_narrative` | 🟢 | ⚠️ **«può», non «lo fa»**: quanti chiamanti guardino il campo non è misurabile da qui |

Banchi: `ws3-il-giudice-freddo-ammette-e-lo-dichiara.py` (① ② ⑥ ⑦) ·
`ws3-il-campo-che-distingue-non-giudicato-da-giudicato.py` (③ ⑧) ·
`ws3-le-due-porte-separano-gli-stessi-tre-stati.py` (⑤) ·
`ws3-la-guida-dichiara-la-propria-eccezione-e-vera.py` (④).

---

## 🔑 La colonna che ho imparato a pretendere oggi

La quarta riga è quella che insegna. Ieri avevo verificato l'eccezione
`meta_narrative` e concluso: *«la guida descrive con precisione il proprio buco,
e il moat resta a proteggere»*. **Il meccanismo era ed è vero.** Ma la guida
dice «**with a source** it runs in both modes», e **nei miei quattro casi la
fonte l'avevo messa io**.

Poi *Paragone* ha misurato che il **65% del corpus** salta quello screen, e io ne
ho dedotto un rischio: *«quei fatti non hanno fonte, quindi non sono protetti»*.

> 🔑 **Verificare una garanzia condizionale senza misurare la frequenza della
> condizione produce un verdetto VERO e una rassicurazione FALSA.**

🔴 **E POI HO SBAGLIATO UNA SECONDA VOLTA, NELLA DIREZIONE OPPOSTA.** `W7-70` e
`W7-71` (*Paragone*, 15:40 e 15:49) hanno **letto** quei fatti invece di
contarli: su 24 casi campionati **uno ogni 14** — **11 resoconti · 13 misure
verificabili · ZERO self-claim nudi**. E il controfattuale, che è la misura
giusta: **senza l'eccezione la porta ne declasserebbe 21 su 24**, quasi tutti per
`L1.13`. ⇒ **L'eccezione non è un buco lasciato aperto: è una compensazione
misurata**, su un vocabolario — *completo, chiuso, verificato, testato* — che è
quello con cui si parla di CI e di cicli di lavoro.

🔑 **La lezione va raffinata, non buttata**: la frequenza da sola **non dice se
il rischio si realizzi**. Serve il **controfattuale** — *cosa farebbe il layer se
girasse?* Io avevo ragionato su ciò che il layer **non fa**, senza chiedermi cosa
succederebbe se lo facesse.
⇒ **Ho preso un numero e ne ho dedotto un rischio senza leggere la popolazione**,
che è la mia stessa regola («leggi le righe, non contarle») applicata al log
della suite e **non** al numero di un altro.

⇒ Da qui la colonna «su quanti casi si applica». Tre delle otto **non sono
misurabili da dentro il repo**, e sono dichiarate tali: *quanti usano SDK contro
MCP*, *quanti processi freschi*, *quanti chiamanti leggono i campi*. **Dichiarate,
non stimate.**

---

## 🔴 Il contrappeso: ciò che non regge è ciò che nessuno ha dichiarato

- ✅ **CURATO alle 17:34** — la guardia anti-eco è **in servizio**
  (`l1_completion_detector.py`, votata 3/3, e il commento cita il mio banco).
  Ri-eseguito come test di accettazione: **5/5 → 0/5**, controllo 5/5 retto.
  ⚠️ *E io avevo protestato due volte che fosse «ferma senza assegnazione»,
  mentre era già curata nel file del mio perimetro: non l'avevo riletto.*
  **Il perdono di `L1.13` era a comando del chiamante — 5/5.** Basta ripassare il
  claim come `source`: il testo del match compare verbatim **per costruzione**.
  Il commit che introduce il perdono dichiara «*una self-claim senza fonte resta
  fermata*» — vero alla lettera; ciò che non nomina è che **chi scrive la fonte
  è chi scrive il claim**. `a7f39bf0`
- **Le sei radici di `L1.13`** (*Paragone*, `a83d9605`): un sinonimo fuori
  dall'elenco aggira il layer **senza fonte**. Due vie indipendenti sullo stesso
  strato; la protezione residua è **gergo di collaudo**, e un verbale d'ufficio
  non ne ha nessuno.
- **Il buco dell'irrilevante**: 8 claim su 12 ottengono `moat: passed` senza che
  la fonte ne parli; ne entrano 2. La causa resta **ignota** — sei spiegazioni
  proposte e falsificate.
  ⚠️ **Ma NON è un limite non dichiarato, e la riga va spostata**: il `README`
  lo nomina come *known gap* — «*a **plausible added inference the source never
  states** … scores high and is admitted*» — con **due date e due numeri** (0 il
  18/07, **4** il 25/08), il comando per rifarlo, e persino «*Run it yourself
  before trusting either number*». ⇒ **La mia misura è una conferma
  indipendente di un limite che il prodotto dichiara**, non un difetto nascosto.
- ⚠️ **L'asimmetria fra le porte — L'UNICO ANCORA APERTO**: con modello locale
  assente e daemon vivo, **l'SDK ammette un claim che la sua fonte NEGA, MCP lo
  ferma**. Localizzato a `anti_confab_gate.py:2350-2352`: `_have_judge` chiede
  «*il modello è su disco?*» per rispondere a «*c'è un giudice?*», e **il daemon
  non è nell'elenco**. `e4c1f199` · `1090f1fd`
  📌 **È anche il più difficile dei quattro**: tocca **ogni scrittura**, e la cura
  non è cambiare il predicato ma **spostare la decisione** — `judge_state()`
  diventa `delegated` solo **dopo** una delega riuscita, quindi *nessun pre-check
  può sapere se il daemon risponderà*.

### Il contrappeso, ricontato alle 17:45 — e tre su quattro erano già curati

| reperto | stato |
|---|---|
| perdono `L1.13` a comando (5/5) | ✅ **curato** — guardia anti-eco in servizio; il mio banco è il suo test: **5/5 → 0/5** |
| `cli.py` «*would store as provisional*» (utente-visibile) | ✅ **curato** `b2fc39af`, **15 min** dopo la segnalazione |
| `l1_orphan_detector.py` idem | ✅ **curato** `31f1335e` |
| `_have_judge` / asimmetria porte | ⚠️ **aperto** — il più difficile |
| buco dell'irrilevante | ⚠️ **non è un difetto nascosto**: *known gap* dichiarato nel README |

🔑 **E la lezione operativa si misura**: alle 16:15 e 16:35 ho **reclamato** che un
lavoro fosse fermo — **era già fatto**. Alle 16:50 ho **segnalato** due difetti
con la riga e l'evidenza, **senza chiedere** — **curati entro 15 minuti**.
⇒ *La segnalazione fattuale funziona meglio della protesta, e oggi la differenza
è misurata: 0 su 1 contro 2 su 2.*

---

## Cosa NON dice questo documento

- **Non dice che il prodotto sia a posto.** Dice che le sue **dichiarazioni**
  reggono. Sono due cose diverse, e la seconda non implica la prima.
- **Non è un campione rappresentativo.** Otto promesse **le ho scelte io**,
  guardando dove il prodotto parla di sé. Un altro ne sceglierebbe altre.
- **Non misura il traffico reale.** Tutti i banchi girano su store temporanei,
  con claim scritti da me, in italiano e inglese, e i numeri di frequenza
  mancanti sono segnati come mancanti.
- **Non assolve i miei banchi.** Oggi ho contato **dieci difetti nel mio
  misuratore**, e la famiglia dominante è una sola: *la popolazione non
  conteneva ciò che credevo di misurare* — regime ereditato invece che scelto,
  casi non appaiati, uno stato che non si produce, due fatti che si mangiano a
  vicenda per `same-source`, uno strumento che interroga un'altra tabella, e
  **il decimo non in un banco ma in un ragionamento**: un numero altrui letto
  come rischio senza guardare i fatti che lo componevano.
  ⇒ **Ogni banco qui citato ha ora un controllo che fallisce se la popolazione
  non c'è**, ed è l'unica ragione per cui questi numeri si possono leggere.

## La classe del giorno: la prosa resta ferma dove il codice si è mosso

Quattro istanze, **tre autori diversi**, una forma sola:

| | dove | l'affermazione | il codice |
|---|---|---|---|
| ① | `quantity_match` (mia) | «saltando le **DUE** potature» | ne avevo aggiunta una **terza**, fuori dall'esenzione |
| ② | `anti_confab_gate:2336` | tre vie al giudizio elencate | **il daemon non è nell'elenco** |
| ③ | `anti_confab_gate:24,296` | il downgrade forza `provisional` | scrive **`quarantined`**, in 7 punti |
| ④ | `anti_confab_gate:902` | `return False` (il default vecchio) | il default è **`return True`** — riga **irraggiungibile** |

⇒ Dopo la terza ho smesso di aspettare la quarta e ho usato **la classe come
setaccio**: `git grep` sulle affermazioni che nominano un conteggio, nel mio
perimetro. **Otto candidati, un difetto vero** (④, curato `613306f7`), **sette
no** — e lo dico con la stessa forza con cui avrei annunciato sette reperti.

🟢 **Due dei sette sono la FORMA GIUSTA, e sono già nel prodotto**:
`anti_confab_gate:1196` («*MISURATO su **quattro** aggiornamenti legittimi ne
blocca **due***» — **e li elenca**) e `mcp_server:8159` («*nessuna delle **tre**
superfici (mcp_server 0, cli 0, client 0)*» — **nomina superfici e numeri**).
**Si auto-verificano**: fra sei mesi qualcuno può contare.

🔑 **E il reperto di metodo vale più del difetto.** Due candidati —
«*i **quattordici** layer*», «*i **tre** detector*» — **non sono nemmeno
verificabili**: il mio contatore dà 35 e 4, ma **conto una cosa diversa** (il 35
include varianti `-observe`/`-graded`; «detector» non è «punto di import»).

> **Il puntatore non serve solo a tenere il numero aggiornato: serve a renderlo
> VERIFICABILE.** Un numero senza il suo criterio di conteggio non si può
> nemmeno controllare — e quindi **non invecchia mai visibilmente**.

⇒ È **peggio** di un numero sbagliato: quello prima o poi qualcuno lo smentisce;
un numero **non verificabile** non lo smentisce nessuno. Stessa famiglia di
*«una misura che non c'è si legge come perfetta»*.
📌 **Proposta**: *un'affermazione che nomina un numero, un elenco o uno stato
dica **dove sta scritto nel codice** — o, se è un conteggio, **con quale criterio
si conta**.* Non serve un test: gli esempi buoni sono già nel repo.

### La regola, dimostrata invece che argomentata

`agent_guide.py:77` — la guida che **ogni agente legge** — promette:

> *Measured on a real corpus: **538 of 634** chunks (84.9%) pointed at files that
> no longer existed, while the chunk text was present for **100%** of them.*

È **la forma giusta al massimo grado**: numero · criterio (*cosa* conta) ·
popolazione · contrasto · conclusione operativa. **Manca solo la DATA.** Ho
provato a ri-misurarlo (store dei documenti, **sola lettura**, 30/08 ore 16:58):

```
73 documenti indicizzati
  uri che NON esiste più   42  (57,5%)
  content conservato       73/73  (100%)
  esempi: contract.txt · docs\ROADMAP-v0.7.md · …\Temp\claude\…
```

🟢 **La sostanza REGGE su una popolazione indipendente**: i path si perdono, il
contenuto resta **al 100%** — e con esso la conclusione operativa, *la citazione
è esatta sull'indice, non è una garanzia di riaprire l'originale*. 🟢 **E la
guida nomina già la causa giusta** («*a RELATIVE path resolved from a different
working directory*»): i miei esempi sono esattamente path **relativi** e
**temporanei**.

⚠️ Quella prima misura era sui **73 documenti**, non sui **634 chunk**:
popolazione sbagliata, e il numero non era confrontabile. **Trovata la
popolazione giusta** (`~/.engram/documents/document_index.db`, tabella `chunks`)
e ri-misurata — **30/08, ore 17:22, sola lettura**:

```
chunk oggi                683        (la guida dichiarava 634 come TOTALE)
file che non esiste più   634 / 683   = 92,8%   (la guida: 538/634 = 84,9%)
testo conservato          683 / 683   = 100,0%  (la guida: 100%)   ← ESATTO
```

🟢 **Il 100% regge ESATTAMENTE** sulla popolazione cresciuta: **683 su 683**. La
promessa più forte della guida è verificata.
🔴 **Il tasso è INVECCHIATO**: **84,9% → 92,8%**. Il corpus è cresciuto (634 →
683 chunk) e i file mancanti sono cresciuti di più (538 → 634).

🎭 **E LA COINCIDENZA CHE VALE PIÙ DEL NUMERO**: **634 compare in entrambi, ma
come grandezze DIVERSE** — nella guida è il **totale dei chunk**, oggi è il
**numero di quelli mancanti**. ⇒ Chi confrontasse i due referti di sfuggita
vedrebbe «634» in tutt'e due e concluderebbe che **nulla è cambiato**.

🔑 **Il pericolo che la regola previene si è materializzato davanti a me**: lo
stesso numero, due ruoli, due date. Senza la data **e** la grandezza contata,
questo è invisibile. *Non l'ho argomentato: l'ho incontrato.*
📌 Il numero aggiornato, con la sua data e il suo criterio, è qui sopra: **chi
mantiene `agent_guide.py` ha tutto per rimetterlo in riga.**

### E la correlazione è perfetta su tre righe — con una coda che è su di me

`agent_guide.py` ha **tre** affermazioni misurate. Le ho guardate tutte:

| riga | data? | esito |
|---|---|---|
| `:32` eccezione `meta_narrative` | ✅ «*measured **2026-08-28***» | **regge** (2/2 e 2/2) |
| `:53` le tre porte del recupero | ✅ «*Measured **2026-08-29** on a store of **60 facts and no episodes***» | **regge** — vedi sotto |
| `:77` i chunk orfani | ❌ nessuna data | **invecchiata**: 84,9% → 92,8% |

🔑 **Le due datate reggono; l'unica senza data è l'unica invecchiata.** N=3 è
piccolissimo e la correlazione non è una prova — **ma il meccanismo non è
statistico, è causale**: senza data nessuno *può* accorgersi.

🔴 **E `:53` la ho verificata nel modo peggiore: sbagliando.** Dice, con data,
popolazione, regime (*sopra il floor di 50 fatti, dove il recupero cambia
percorso*), **tre** numeri e la lezione operativa::

    verimem_facts_search  20 hits  ·  verimem_facts_recall  5  ·  verimem_recall  []
    «An empty list is an ANSWER, not an abstention — read it as "wrong door",
     not as "the store knows nothing".»

Alle 15:45, misurando altro, ho interrogato `hippo_recall` cercando **fatti**, ho
ottenuto `[]`, e ho creduto per qualche minuto che **MCP non vedesse i fatti
dell'SDK** — un reperto grave che non esisteva. **Il prodotto me lo aveva scritto,
con i numeri, e non l'avevo letto.**

🔑 **Quindi la regola sul numero verificabile NON basta, e va detto qui.** La riga
**meglio scritta** che ho incontrato oggi — data, popolazione, regime, tre
numeri, conclusione operativa — **non mi ha impedito l'errore, perché non l'ho
aperta.** ⇒ *Il presidio non è scrivere meglio: è **leggere prima di misurare**.*
Le due metà stanno insieme — **un'affermazione perfetta serve solo a chi la
legge**, e chi misura senza aver letto rifà il lavoro che il prodotto ha già
fatto e a volte lo rifà male.

## Una regola pratica, che vale oltre questo prodotto

> **Quando un banco stampa `[]` o `0`, la prima ipotesi non è «il prodotto non
> lo fa»: è «non gliel'ho chiesto».**

Oggi mi ha impedito di pubblicare due volte un reperto grave che non esisteva —
la seconda smontata facendo scrivere a MCP **un fatto suo** e chiedendogli di
ritrovarlo.

**Agent: Galileo**
