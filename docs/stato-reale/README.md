# Verimem — che cos'è, cosa fa davvero, cosa non fa

**8 agosto 2026 · sette istanze, sette fette, ogni riga eseguita e non letta.**
Misurato su `544d27bd`. Le sezioni di dettaglio sono i file numerati qui accanto.

---

## La risposta in dieci righe

Verimem è una **memoria che rifiuta di ricordare ciò che non le è stato dimostrato**.
Non è un archivio e non è un motore di ricerca: è un archivio **con un guardiano
all'ingresso**. Quando un agente scrive «ho finito e funziona», verimem lo mette da
parte invece di crederci; quando gli dai un documento e un'affermazione, controlla
che l'affermazione ci sia davvero dentro.

**Funziona.** Il guardiano fa quello che promette, e il caso che lo dimostra è
questo: alla frase «*l'ordine 77 conteneva 40 pezzi*», con i 40 **inventati**, il
giudice semantico dà **95,8 su 100** — perché il senso è coerente col documento — e
il controllo sui numeri la ferma lo stesso. Un prodotto che si fidasse del solo
punteggio te l'avrebbe restituita come verificata.

**Ma appena installato non fa niente di tutto questo**, e nessuno lo dice. E quando
non sa una cosa, quasi sempre risponde lo stesso.

---

## Le nove domande, una per una

### 1. Cosa dovrebbe fare una memoria del genere — e cosa manca

Le promesse scritte sono **25**, fra PyPI, README e il testo che il prodotto invia a
ogni agente che si collega. Misurate: **11 vere, zero false, 1 non misurata**
(§01). Il resto è vero solo in casa nostra (vedi domanda 6).

**Cosa manca del tutto**, rispetto a ciò che un utente si aspetta da una memoria:
**dimenticare** (non c'è un modo dichiarato di far sparire un dato), **il costo**
(nessuna riga dice quanto pesa o quanto ci mette), e **quale porta usare** — ci sono
cinque modi di interrogarla e nessuno spiega quale scegliere.

### 2. Che funzioni abbiamo

Scrittura con guardiano · lettura in cinque modi diversi · ingestione di documenti ·
sostituzione del dato vecchio col nuovo · ricostruzione della storia di un dato ·
quarantena invece della cancellazione. Tutte verificate funzionanti (§01, §05, §07).

### 3. Come ingeriamo i documenti

I cinque formati dichiarati funzionano tutti — txt, md, html, pdf, docx — **e anche
il cinese**. CSV e XLSX falliscono in modo pulito, dicendo il tipo. Un PDF corrotto
non rompe niente. Indicizzare due volte lo stesso file non lo duplica.

🔴 **Ma la citazione non ha la pagina.** L'ancora è un intervallo di *caratteri*
(`prova.pdf:0-203`) e un pezzo di testo può attraversare due pagine: l'informazione
di pagina **è persa in estrazione** e nessun cambio di formattazione la recupera. Chi
si aspetta «pagina 4, riga 12» non lo avrà (§05).

⏱️ 9,4 MB indicizzati in **184 secondi**, senza nessuna barra di avanzamento.

### 4. Come gestiamo la memoria (scrittura)

Tre stadi: un controllo sulle parole che costa zero e ferma gli auto-elogi; il
giudice che confronta col documento e dà un voto da 0 a 100; i controlli sui
dettagli — numeri, negazioni, contraddizioni. Poi il fatto è ammesso o messo in
quarantena (§07).

**Il giudice gira solo se passi una fonte.** Senza, il fatto entra come dichiarazione
non verificata. È una scelta dichiarata, non un guasto — ma non è evidente: il fatto
sembra salvato come tutti gli altri.

### 5. Come gestiamo le informazioni (lettura)

🔴 **Cinque porte per interrogare la memoria, e una sola sa dire «non lo so».**
Su quattro domande la cui risposta non esiste nel corpus, `recall` si astiene **zero
volte su quattro**; `trust_report` quattro su quattro (§04).

E il caso che fa più danno: **chiedi del magazzino di Trento e ti risponde Verona.
Chiedi il lotto C-99 e ti risponde C-12.** La risposta è ben formata, è sbagliata, e
non c'è nessun avviso.

### 6. 🔴 Se un utente la installa, cosa fa

Questa è la domanda a cui nessuno aveva mai risposto. Misurata su una macchina
pulita, ambiente vuoto (§02):

| | |
|---|---|
| `pip install verimem` | **9 minuti 54 secondi**, 70 pacchetti |
| peso su disco | **1,01 GB** (di cui torch 490 MB) |
| primo comando che scrive un fatto | **133 secondi** |

**E la verifica — cioè tutto il prodotto — è SPENTA.** Il giudice sono altri **656
MB** che `pip install` non porta: finché non lanci `verimem warmup`, verimem accetta
tutto senza controllare niente. Il `doctor` lo dice, ma solo se vai a cercarlo.

**Peggio**: la nostra documentazione insegna `verimem save`, che **sul pacchetto
pubblicato non esiste** (PyPI ne ha 26 di comandi, il repo 37). Il primo comando che
un utente copia dalla nostra doc restituisce un errore.

E su uno store con due fatti che non parlano dell'argomento, l'interrogazione
risponde **«TRUSTED»** con provenienza «(none)».

### 7. Che parametri e metriche abbiamo

**173 parametri** e **194 soglie**, di cui 181 fisse nel codice. **69 su 166 non sono
documentati da nessuna parte** (§06).

Il `doctor` dice il vero — tre suoi numeri controllati contro il database coincidono
— ma **non nomina né la soglia di ammissione né una sola variabile impostata**. Chi
installa non ha modo di sapere quali valori sono in vigore.

⚠️ Una scoperta: **importare il pacchetto scrive 13 variabili nell'ambiente**, fra
cui il percorso dello store — che da quel momento è inchiodato.

### 8. Ci sono cose spente?

Sì: **12 misurate spente** su 64 interruttori interrogati, e ce ne sono **151** in
tutto — quindi il censimento copre il 42% (§03).

🔑 E la scoperta che vale più dell'elenco: **«spento» non è una proprietà del
programma, è una proprietà di chi lo lancia.** Lo stesso interruttore è acceso quando
verimem gira dentro Claude e spento quando lo lanci da terminale.

Una manopola (`HIPPO_EXPOSE_TOOLS`) **è impostata sul tuo computer e nessuna riga del
programma la legge**: gira a vuoto.

### 9. Allo stato attuale cosa funziona

**Funziona** il guardiano in scrittura, l'ingestione dei documenti, la sostituzione
del dato vecchio, la storia di un dato, la quarantena.
**Non funziona** l'astensione in lettura (4 porte su 5), la citazione con la pagina,
e il prodotto appena installato.
**Non è misurato**: quanti dei fatti trattenuti siano trattenuti *a ragione*.

---

## I numeri della memoria di casa

    8.999   fatti scritti
    6.425   arrivano davvero all'utente                (71,4%)
    1.828   sostituiti da un aggiornamento
      746   in quarantena: non tornano, e nessuno avvisa
    ─────
    4.279   dei 6.425 serviti NON hanno mai avuto un voto — il 67%

⚠️ **Il 28,6% che non arriva non è di per sé una perdita**: nel banco di prova quattro
ritiri su quattro erano corretti. Ma sul corpus vero **non è misurato**, ed è la
differenza fra «severo» e «mangia i dati».

---

## Le tre cose da riparare, in ordine

1. **L'astensione** — una memoria che risponde Verona quando le chiedi Trento è
   peggio di una che tace. È il difetto che tocca ogni utente a ogni domanda.
2. **Il primo avvio** — 10 minuti, 1 GB, la verifica spenta e un comando che non
   esiste. Chi prova il prodotto si ferma qui.
3. **La prova della verifica** — la fonte viene usata per giudicare e poi buttata:
   resta solo un'impronta. La verifica c'è, il modo di rivederla no.

---

## Le sezioni

| | | autrice |
|---|---|---|
| [01](01-promesse-vs-realta.md) | cosa promette, contro cosa fa | ws1 |
| [02](02-utente-che-installa.md) | l'utente che installa, cronometrato | ws2 |
| [03](03-cose-spente.md) | il censimento delle cose spente | ws4 |
| [04](04-percorso-di-lettura.md) | le cinque porte e l'astensione | ws5 |
| [05](05-ingestione-documenti.md) | i documenti | ws6 |
| [06](06-parametri-metriche-telemetria.md) | parametri, metriche, telemetria | ws7 |
| [07](07-percorso-di-scrittura.md) | il guardiano in scrittura | ws3 |

⏱️ I conteggi del corpus sono delle 12:45 dell'8 agosto: cresce mentre lavoriamo, e
ciò che deve coincidere sono le proporzioni, non le cifre assolute.

📌 **Sul metodo**: ogni sezione è stata attaccata da un'altra istanza, che ne ha
rieseguito i comandi alla cieca. In tre ore: ws7 ha ridimensionato da sé un proprio
titolo (da «la soglia è doppia» a «tocca l'1,15% dei fatti»), ws2 ha ribaltato il
verdetto di ws1, ws6 ha reso più grave il finding di ws7, ws1 ha corretto un errore
che avevamo in tre. **Nessuna ha difeso il proprio referto.**
