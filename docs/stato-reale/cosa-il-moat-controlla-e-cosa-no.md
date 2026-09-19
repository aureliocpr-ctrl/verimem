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

---

## ✅ Quello che il moat CONTROLLA, e come si comporta

### ① Le quantità, a parità di unità

    «Il capannone 12 misura 401 metri quadri.»   ->  quarantined, punteggio 5.53
      L4.1 — «il claim afferma un valore che la fonte non contiene: 401 metro»

**Una differenza di un metro quadro viene fermata.** Il controllo si chiama
`L4.1`, e il suo contratto è scritto in `verimem/quantity_match.py`: un conflitto
numerico è *«un valore **diverso** per la **stessa** unità normalizzata»*.

### ② Le affermazioni che la fonte contraddice

Una scrittura fuori tema o che nega la fonte cade allo stesso modo: il moat dà
un punteggio basso e la scrittura resta **fuori dal richiamo di default**.

### ③ La ricevuta dice quale controllo ha girato

Ogni scrittura torna con `layers`, `status` e il punteggio. **Un fatto fermato
dice perché**, e un fatto ammesso dice che è il voto del giudice — non una
verifica che la proposizione segua dalla fonte:

    «the source SCORES as supporting this fact: that is the judge's score,
     not a check that the fact follows from it»

---

## ❌ Quello che il moat NON controlla — con il ticket accanto

### ① Giudizi, valutazioni e previsioni — `T140`

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

### ② Le unità composte — `T105`

    «Il capannone 12 misura 400 metri CUBI.»      ->  admitted, punteggio 96.01

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

### ③ La banda intermedia senza un modello linguistico — `D-0011`

Il giudice locale è un cross-encoder. Nella **banda intermedia** dei punteggi il
verdetto dipende da un secondo giudizio che **richiede un modello linguistico
iniettato**: senza quello, quella banda **non viene giudicata**, e il prodotto
lo dichiara nella ricevuta invece di fingere un verdetto.

⇒ **Chi usa il prodotto senza iniettare un LLM non ha quella difesa.** Non è un
difetto: è una scelta, e sta qui perché l'utente la sappia prima e non dopo.

---

## 🔑 La cosa da ricordare, se si legge una riga sola

Il moat **confronta le quantità e cerca le contraddizioni**: è forte dove c'è un
numero da confrontare o una frase da contraddire. **È debole dove non c'è
nessuna delle due** — un giudizio, una previsione, un'unità che cambia nome.

⇒ Il punteggio accanto a un fatto ammesso **è il voto di un giudice, non una
dimostrazione**. La ricevuta lo dice; questa pagina dice quando quel voto vale
meno.

---

⚠️ **Questa pagina scade.** È misurata su un wheel preciso, e il wheel cambia a
ogni fusione — tre punti del tronco in una mattina hanno dato tre file diversi.
I numeri di `T140` e `T105` sono di oggi e si muoveranno quando le cure entrano.
**Chi la rilegge fra un mese rimisuri prima di fidarsi.**
