# Cosa il moat controlla, e cosa no

> **A che serve questa pagina.** Il prodotto promette che un fatto che la fonte
> non sostiene non torni come se fosse vero. È una promessa forte, e come tutte
> le promesse forti ha un **perimetro**. Qui c'è il perimetro, con i numeri e
> con i ticket aperti accanto a ogni buco — perché **un limite che l'utente
> scopre da solo costa più di un limite dichiarato.**

Misurato il 19/09/2026 sul wheel di `main` (`bdf7453b`, versione `0.7.7`), in
venv pulito, con `verimem remember` sulla riga di comando e le stesse scritture
sulla libreria e sulla porta MCP. Fonte unica per tutti i casi:

> ## ⚠️ OGNI NUMERO DI QUESTA PAGINA È DI **UN REGIME**
>
> Misurati **col solo giudice locale cross-encoder, senza modello linguistico
> iniettato**. Con un LLM iniettato la banda intermedia viene giudicata davvero,
> e **lo stesso ingresso può avere esito opposto**. Non è un'ipotesi: un pari ha
> rifatto dalla porta, su `c4bec04c`, il caso delle unità composte —
>
>     questa pagina (CE solo)   400 metri cubi  ->  admitted     96.01   layers=[]
>     con un LLM iniettato      400 metri cubi  ->  quarantined   0.00   ['L4-grounding']
>
> ⇒ **96 punti e l'esito rovesciato, sullo stesso testo e sulla stessa fonte.**
> È `T134`. Quindi: i numeri qui sotto dicono *quanto protegge la configurazione
> di base*, che è quella che un utente ha appena installato — **non il massimo
> che il prodotto sa fare.** Dove il regime cambia la risposta, la riga lo dice
> accanto al numero.


    «Perizia del 2026-09-01: il capannone 12 misura 400 mq.»

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

## ❌ Quello che il moat NON controlla — con il ticket accanto

### ① L'aggiunta non sostenuta — *questa voce non ha un ticket*

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

**Le altre tre voci hanno un ticket, questa no.** Va aperto; il numero lo dà chi
tiene il registro.


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
      ⚠️ col solo cross-encoder. Con un modello linguistico iniettato lo stesso
         claim è quarantined a 0.00 (`L4-grounding`) — `T134`, misura di un pari.

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

    4 verbali VERI su 10 cadono per il verbo
    «sospeso», FALSO e contraddetto dalla fonte, passa a 98.64

⇒ Il presidio guarda **come** è detta la cosa, non **chi** la dice né se la fonte
la sostiene: un verbo «da modello» fa cadere una frase vera, e un verbo innocuo
fa passare una falsa.

⚠️ **Questi due numeri sono del 29/08/2026**, misurati da un pari, e il banco che
li produce è nel repo:
[`banchi/ws5-quale-parola-fa-cadere-un-verbale-vero.py`](banchi/ws5-quale-parola-fa-cadere-un-verbale-vero.py)
(commit `951dc1fa`). **Tre settimane e molte fusioni fa.** La voce sta qui perché
il difetto è strutturale e il banco è eseguibile — ma il numero **va rifatto sul
wheel di oggi** prima di citarlo come corrente, e finché non lo è, porta la sua
data.

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

⇒ Il punteggio accanto a un fatto ammesso **è il voto di un giudice, non una
dimostrazione**. La ricevuta lo dice; questa pagina dice quando quel voto vale
meno.

---

⚠️ **Questa pagina scade.** È misurata su un wheel preciso, e il wheel cambia a
ogni fusione — tre punti del tronco in una mattina hanno dato tre file diversi.
I numeri di `T140` e `T105` sono di oggi e si muoveranno quando le cure entrano.
**Chi la rilegge fra un mese rimisuri prima di fidarsi.**
