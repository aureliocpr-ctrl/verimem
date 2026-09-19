# Cosa il moat controlla, e cosa no

> **A che serve questa pagina.** Il prodotto promette che un fatto che la fonte
> non sostiene non torni come se fosse vero. È una promessa forte, e come tutte
> le promesse forti ha un **perimetro**. Qui c'è il perimetro, con i numeri e
> con i ticket aperti accanto a ogni buco — perché **un limite che l'utente
> scopre da solo costa più di un limite dichiarato.**

Misurato il 19/09/2026 sul wheel di `main` (`bdf7453b`, versione `0.7.7`), in
venv pulito, con `verimem remember` sulla riga di comando e le stesse scritture
sulla libreria e sulla porta MCP. Fonte unica per tutti i casi:

    «Perizia del 2026-09-01: il capannone 12 misura 400 mq.»

🔤 *In questa pagina scriviamo **ammesso** dove la ricevuta scrive
`status='model_claim'`: è più chiaro per chi legge, ma sono **due nomi per lo
stesso esito** — se un giorno il vocabolario si unifica, questa pagina è uno dei
posti da aggiornare.*

⚠️ *Questa citazione è stata cancellata per un'ora da una riscrittura del
riquadro qui sotto, che ha sostituito un blocco per posizione e si è portata via
quello che stava in mezzo: la pagina annunciava «fonte unica per tutti i casi» e
poi non la mostrava.*

> ## 🔴 UN'ABBREVIAZIONE NELLA FONTE DISARMA IL CONTROLLO SULLE UNITÀ
>
> **È il fatto più importante di questa pagina, e non è un numero: è il modo in cui
> i documenti veri sono scritti.** Lo stesso claim falso — *«400 metri cubi»*
> contro una fonte che dice 400 metri quadri — passa o viene trattenuto **a
> seconda di come la fonte scrive l'unità**:
>
>     fonte PER ESTESO   «…misura 400 metri quadri.»  ->  quarantined  75.81  ['L4-review']
>     fonte ABBREVIATA   «…misura 400 mq.»            ->  admitted     96.01  []
>
>     controllo, stesso giro, claim VERO «400 metri quadri»:
>     contro la fonte per esteso  98.97      contro la fonte abbreviata  98.55
>
> ⇒ **`mq`, `mc`, `kg`, `km²` sono esattamente come scrivono perizie, verbali e
> fatture.** Il giudice valuta la **coppia**: «400 metri cubi» contro «400 mq» non
> è lo stesso ingresso di «400 metri cubi» contro «400 metri quadri», e nel primo
> caso la contraddizione di unità non viene vista.
>
> 🗓️ ⚠️ **Tutti i numeri di questa pagina sono presi con la fonte ABBREVIATA**
> — cioè **sul ramo in cui il moat protegge di meno**. Chi li rifà con una fonte
> per esteso otterrà numeri diversi, e migliori.
>
> 🔬 **Rimisurato da chi scrive questa pagina, cambiando UNA SOLA COSA.** La
> prima misura — di un pari — cambiava **due** cose fra le due fonti: l'unità *e
> la data*. Qui cambia solo l'unità, stessa data, stesso processo, stessa
> macchina:
>
>     fonte «Perizia del 2026-09-01: … 400 mq.»           + «400 metri cubi»
>                                          ->  model_claim   96.00531768798828  []
>     fonte «Perizia del 2026-09-01: … 400 metri quadri.»  + «400 metri cubi»
>                                          ->  quarantined   74.09764862060547  []
>     controllo, claim VERO «400 metri quadri»:  98.548 (abbreviata)  ·  98.897 (esteso)
>
> ⇒ **L'effetto resta con una variabile sola: non era la data, è l'unità.** E la
> data *sposta il punteggio* senza cambiare il verdetto (74.10 qui, 75.81 nella
> misura del pari, che aveva anche un'altra data) — una ragione in più per
> cambiare **una cosa per volta**.
>
> 🌡️ **IL REGIME DI TUTTI QUESTI NUMERI: banda SPENTA** (`ENGRAM_BAND_LLM=0`),
> cioè senza la scalata a un modello linguistico. La pagina lo diceva solo più
> in basso, e questo riquadro è quello che si legge per primo — rilievo di un
> pari, ed è la stessa classe che questa pagina esiste per chiudere.
>
> ⚠️ **E c'è UNA MISURA CHE MANCA, dichiarata qui invece che scoperta dopo:**
> nessuno ha ancora provato *«fonte abbreviata + 400 metri cubi»* **con la banda
> ATTIVA**. Se anche con la banda il claim falso passa, il difetto è **del
> prodotto** e questo riquadro è giusto com'è; se con la banda viene trattenuto,
> il difetto è **di un regime** e il riquadro lo sta dicendo più largo di quello
> che è. **È due celle e un minuto**, e non è stata fatta perché richiede un
> secondo modello acceso insieme al giudice.
>
> 🔮 **E per un'ora questo riquadro ha detto un'altra cosa**: che lo stesso
> ingresso desse esiti diversi **su macchine diverse**. Era falso, e l'errore
> stava **nel banco, non nel prodotto** — due persone confrontavano due fonti
> diverse credendo di confrontare la stessa. Prima di accorgercene avevamo
> confrontato gli sha256 dei modelli, le versioni di torch, trenta variabili
> d'ambiente e lo stato del giudice: **le due stringhe, che costavano due
> secondi, per ultime.**

---

## ✅ Quello che il moat CONTROLLA, e come si comporta

### ① Le quantità, a parità di unità

    «Il capannone 12 misura 401 metri quadri.»   ->  quarantined, punteggio 5.53
      L4.1 — «il claim afferma un valore che la fonte non contiene: 401 metro»

**Una differenza di un metro quadro viene fermata.** Il controllo si chiama
`L4.1`, e il suo contratto è scritto in `verimem/quantity_match.py`: un conflitto
numerico è *«un valore **diverso** per la **stessa** unità normalizzata»*.

### ② Le affermazioni che la fonte contraddice, e quelle fuori tema

    «Il capannone 12 misura 900 metri quadri.»    ->  quarantined, punteggio 0.81
    «La torre Eiffel è alta 330 metri.»           ->  quarantined, punteggio 0.24

**Negare la fonte e parlare d'altro cadono tutti e due, e cadono in basso**: la
scrittura resta **fuori dal richiamo di default**. Sono i due presidi più forti
di questa pagina, e vanno detti con i loro numeri esattamente come si dicono i
buchi.

### ③ La ricevuta dice quale controllo ha girato

Ogni scrittura torna con `layers`, `status` e il punteggio. **Un fatto fermato
dice perché**, e un fatto ammesso dice che è il voto del giudice — non una
verifica che la proposizione segua dalla fonte:

    «the source SCORES as supporting this fact: that is the judge's score,
     not a check that the fact follows from it»

⚠️ **Dice quale CONTROLLO ha girato, non quale GIUDICE ha deciso.** I due non
sono la stessa cosa, e il secondo oggi manca: è `T134`, alla voce ④ qui sotto.

---

### ④ Quando **non può** giudicare trattiene — e con la fonte per esteso **lo ferma**

È la parte della promessa che nessuno scrive, e va detta qui perché è quella
che decide cosa succede il giorno in cui qualcosa non funziona:

    senza il giudice di banda   400 metri cubi -> quarantined  75.81  ['L4-review']

`L4-review` vuol dire **tenuto per revisione**. Il modulo lo dichiara come
comportamento a prova di guasto — *«no CLI, a CLI error, a timeout … keep
today's held-for-review behavior»* — e il giudice di banda è **un pezzo di
prodotto**, non un accessorio: `band_escalation.py` scala prima a un modello
locale e poi alla CLI come ripiego, e `ENGRAM_BAND_LLM=0` serve a uscirne.

⚠️ **Questa riga ha avuto una diagnosi sbagliata per un'ora**: diceva che
`L4-review` scatta su *«una macchina su tre»*. Non era la macchina — era la
**fonte**. Con la fonte per esteso lo stesso claim falso viene **trattenuto** a
75.81; con la fonte abbreviata esce **ammesso** a 96, senza strati.

⇒ Quindi il comportamento a prova di guasto **c'è**, e questa è la lode: quando
il giudizio non è pieno il prodotto **tiene per revisione invece di ammettere**.
Ma lo fa **sull'ingresso che riesce a leggere**, e un'abbreviazione nella fonte
gli toglie il caso di mano prima che arrivi fin lì.

⚠️ **E il nome dello strato regge su una misura sola.** Rifacendo con la fonte
per esteso — una variabile sola — il claim falso è **trattenuto lo stesso**
(`quarantined`, 74.10) **ma `layers` è vuoto**: nessuno strato lo dichiara, lo
ferma il punteggio sotto soglia. Quindi il fatto che il prodotto trattenga è
**confermato due volte**; che sia `L4-review` a farlo è visto **una volta sola**,
ed è la parte da rimisurare prima di scriverla come meccanismo.

## ❌ Quello che il moat NON controlla — con il ticket accanto

### ① L'aggiunta non sostenuta — `T146`

    fonte  «Perizia del 2026-09-01: il capannone 12 misura 400 mq.»
    claim  «Il capannone 12 ha tre piani interrati e un eliporto.»
                                    ->  admitted, punteggio 89.98, layers=[]

La fonte non li nomina, e il claim li aggiunge. **Non contraddice** — non c'è un
valore da smentire — e **non è fuori tema**: parla dello stesso capannone. Sta
nel mezzo fra i due casi che il moat ferma, e lì non ha niente da confrontare:
**`layers=[]` dice che nessun controllo gira.**

⚠️ È la forma che un lettore chiamerebbe *confabulazione* per prima — un
dettaglio inventato di sana pianta — ed è la ragione per cui sta in cima e non
in fondo.

🛡️ **Va letta con la difesa che il prodotto dichiara**, perché non è un
difetto nascosto: la ricevuta **non promette l'implicazione**, dichiara un voto.

    grounded 89.9 — scored as supported by the source
                    (the judge's score, not a check that it follows)

⇒ Chi legge quella riga sa già di non avere una dimostrazione. **Chi non la
legge — o chi usa una porta che quella riga non ce l'ha — no.**

Misurato da chi scrive questa pagina: sei casi, una fonte, wheel `0.7.6`, e le
tre porte danno lo stesso punteggio a tutte le cifre. Il banco completo sta in
[`percorsi/05-numeri-con-unita.md`](percorsi/05-numeri-con-unita.md).

**Questa voce è nata senza ticket** — la pagina lo dichiarava — e il numero
è arrivato dopo: `T146`.


### ② Giudizi, valutazioni e previsioni — `T140`

Se la fonte dà **dati** e il claim dà una **qualifica**, il claim passa.

    fonte  «Il server ha 32 GB di memoria e otto core.»
    claim  «Il server è sovradimensionato per il carico attuale.»

⇒ La fonte non lo dice, e un lettore onesto direbbe «questo la fonte non lo
dice» — ma nessun numero è in conflitto, quindi `L4.1` non ha nulla da
confrontare. Stessa cosa per le valutazioni («è migliorato») e le previsioni
(«basterà fino a fine mese»).

**Misurato su un campione minuscolo: n=3, punteggi 97-99.** ⚠️ Tre casi non sono
una misura: è un segnale. **Il numero definitivo di questa riga arriva con
`T140`** — un banco di quaranta casi, metà scritti da chi non misura, in corso.

### ③ Le unità composte — `T105`

    «Il capannone 12 misura 400 metri CUBI.»      ->  admitted, punteggio 96.01
      ⚠️ questo numero vale con la fonte **abbreviata** («400 mq»). Con la
         fonte per esteso lo stesso claim è **trattenuto** a 75.81 (`L4-review`):
         il riquadro in cima.

Stessa cifra, **unità diversa**: passa. Non è una svista del controllo — è il
suo perimetro: `L4.1` confronta il valore *a parità di unità*, e due unità
diverse non sono un conflitto per definizione.

**Misurato: 12 unità composte su 16 vengono troncate**, e il difetto ha due
facce — in italiano si perde l'aggettivo («metri **cubi**» → «metro»), in
inglese il sostantivo («cubic **meters**» → «cubic»), così che `cubic meters` e
`cubic inches` diventano confrontabili.

⚠️ **E c'è una conseguenza che vale più del caso singolo.** Il modulo tiene
identiche **di proposito** due vie — il controllo in scrittura e lo scanner che
ripassa il corpus — perché *«una confabulazione che il gate segnalerebbe deve
essere ritrovabile retroattivamente nel corpus, e viceversa»*. Quel «viceversa»
significa che **ciò che non viene fermato alla scrittura non viene trovato
neanche dopo**: non è «passa e poi lo troviamo».

### ④ La banda intermedia: senza un LLM non è che manchi un giudizio — cambia la SOGLIA — `D-0011`, `T139`, `T134`

Il giudice locale è un cross-encoder, e nella **banda intermedia** dei punteggi
il prodotto prevede un secondo giudizio che **richiede un modello linguistico
iniettato**.

🔴 **Questa pagina scriveva che senza quel modello la banda «non viene
giudicata». È FALSO, ed è stato corretto prima della pubblicazione** — una
proprietà del prodotto dedotta invece che misurata. Quello che succede è
diverso:

    senza LLM iniettato   la banda la giudica il CROSS-ENCODER DA SOLO,
                          con la soglia del backend dichiarato: 70 invece di 40
    conseguenza misurata  97 fatti dello store finiscono in banda,
                          e sono TUTTI quarantinati        (`T139`, misura di oggi)

⇒ **Non è un buco nella difesa: è una difesa più severa** di quella che il
lettore si aspetta, e che trattiene 97 fatti. Chi non inietta un LLM non perde
una difesa: ne prende una che taglia più in alto e non gliel'ha detto nessuno.

🔴 **E la seconda frase che questa pagina scriveva era falsa allo stesso
modo**: «il prodotto lo dichiara nella ricevuta invece di fingere un verdetto».
Oggi **la ricevuta non dice quale giudice ha deciso** (`T134`, in cura). Quindi
chi legge un verdetto **non sa con quale soglia è stato dato**, ed è esattamente
la differenza fra i due regimi dichiarati in cima a questa pagina.

### ⑤ Il presidio anti-autocertificazione legge il VERBO, non chi parla — `T144`

Cambiando **una sola parola** in una frase vera e sostenuta dalla stessa fonte il
claim cade; e un claim **falso**, che la fonte contraddice, passa:

    5 verbali VERI su 10 cadono per il verbo        (erano 4 il 29/08)
    «sospeso», FALSO e contraddetto dalla fonte, passa a 98.64

⇒ Il presidio guarda **come** è detta la cosa, non **chi** la dice né se la fonte
la sostiene: un verbo «da modello» fa cadere una frase vera, e un verbo innocuo
fa passare una falsa.

🗓️ **Rimisurati sul tronco di oggi**, con lo stesso banco del 29/08 mai
toccato da allora — [`banchi/ws5-quale-parola-fa-cadere-un-verbale-vero.py`](banchi/ws5-quale-parola-fa-cadere-un-verbale-vero.py),
commit `951dc1fa` — così che **l'unica cosa cambiata è il tronco**. Store
temporaneo, tre giri con gli stessi numeri al centesimo:

| | 29/08 | oggi | |
|---|---|---|---|
| veri caduti per il verbo | 4 su 10 | **5 su 10** | è **peggiorato** |
| «sospeso» (falso) | 98.64 | **98.64** | identico al centesimo |

Il quinto caduto è **`concluso`**, declassato da `L1.13` con **grounding 99.90**.

🔎 **E si sa perché**, isolato con un bisect a una variabile:

    e1f5e041 (parent)   concluso  persist    99.90   —        -> 4 caduti
    1a4b8635            concluso  downgrade  99.90   L1.13    -> 5 caduti
    (tronco di oggi)    concluso  downgrade  99.90   L1.13    -> 5 caduti

`1a4b8635` è *«la guardia anti-eco: il perdono di `L1.13` non si compra passando
il claim come fonte»*, del **30/08 — il giorno dopo il banco**.

⇒ **Una cura giusta ha aggiunto un falso negativo.** Ha chiuso una scappatoia
vera, e nel farlo ha tolto il perdono anche a un verbale di terzi **che la fonte
sostiene**. Il grounding resta `99.90`: **non è il giudice che ha cambiato idea,
è il lessico.** È la cosa da ricordare di questa voce, più dei due numeri.

⚠️ Misura di un pari, non di chi scrive questa pagina.

---

## 🔑 La cosa da ricordare, se si legge una riga sola

Il moat **confronta le quantità e cerca le contraddizioni**: è forte dove c'è un
numero da confrontare o una frase da contraddire. **È debole dove non c'è
nessuna delle due** — un dettaglio aggiunto, un giudizio, una previsione,
un'unità che cambia nome. E **sbaglia in tutte e due le direzioni** quando a
cambiare è il verbo: lascia passare un falso e trattiene un vero.

⚠️ **Il primo della lista è il più comune.** Aggiungere alla fonte qualcosa che
la fonte non dice non fa scattare niente, perché non c'è niente da confrontare:
`layers=[]`.

🔴 **E prima ancora: è debole quando non riconosce quello che la fonte dice.**
Un'unità **abbreviata** — `mq`, `mc`, `kg` — gli toglie di mano la contraddizione
prima di arrivare al confronto. Il documento vero è quasi sempre scritto così.

⇒ Il punteggio accanto a un fatto ammesso **è il voto di un giudice, non una
dimostrazione**. La ricevuta lo dice; questa pagina dice quando quel voto vale
meno.

---

⚠️ **Questa pagina scade.** È misurata su un wheel preciso, e il wheel cambia a
ogni fusione — tre punti del tronco in una mattina hanno dato tre file diversi.
I numeri di `T140` e `T105` sono di oggi e si muoveranno quando le cure entrano.
**Chi la rilegge fra un mese rimisuri prima di fidarsi.**
