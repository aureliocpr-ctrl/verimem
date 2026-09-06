# Verimem — che cos'è, cosa fa davvero, cosa non fa

**8 agosto 2026 · sette istanze, sette fette, ogni riga eseguita e non letta.**
Misurato su `544d27bd`. Le sezioni di dettaglio sono i file numerati qui accanto.

> ⚠️ **NOTA DATATA — 2026-08-26 (ws7). Due cose che chi entra da qui deve sapere.**
>
> **① Il numero qui sotto è invecchiato, e nella direzione che conta.** Questa pagina dice «375 commit indietro»: misurato oggi, `v0.7.0` è **994 commit** dietro `origin/main`. Il pacchetto non si è mosso — `0.7.0` è ancora l'ultima su PyPI — si è mosso `main`. La conclusione del documento **si rafforza**, non cade.
>
> **② Come si validano questi file, perché il modo ovvio sbaglia.** Dal 26/08 il README principale rimanda a questa cartella, quindi qualcuno li ricontrollerà. Il metodo che regge è classificarli per **bersaglio**: chi misura il *pacchetto pubblicato* (fermo) tiene per costruzione; chi misura `main` (mobile) è una **fotografia**, e va letto insieme allo SHA nella sua intestazione — `02m` e `02p` lo dicono già nel nome.
> ⛔⛔ **E APRITE ANCHE I CASI CHE IL RIGHELLO NON HA SEGNALATO.** Un criterio sintattico su una proprietà semantica sbaglia in **entrambe** le direzioni, e il 2026-08-27 le ho viste tutte e due **nello stesso censimento, a un'ora di distanza**: ① *falso positivo* — `l4-1-guarda-in-una-direzione-sola` segnato «numero nel titolo» perché **`L4.1` contiene un 4 e un 1**, che è il nome di un componente (il verdetto era comunque giusto, ma per «due misure»: **numero giusto, ragione sbagliata**, che è il modo in cui un righello rotto ti convince di funzionare); ② *falso negativo* — `04`, `06` e `07` classificati «senza SHA» perché lo dichiarano in un **blocco intestato** (`SHA:` `DATA:` `COMANDI:`) e non fra backtick, quando sono anzi **fra i meglio fatti qui dentro**. 🔑 Il secondo l'ho trovato **solo** andando a leggere i file che il criterio aveva lasciato passare: sui soli segnalati sarebbe rimasto invisibile.
> ⛔ **E non validateli con un controllo di presenza.** Oggi ci sono quasi cascato: `03-cose-spente.md` cita `HIPPO_EXPOSE_TOOLS`, che nel codice **non c'è** — stavo per marcarlo scaduto, e invece l'assenza **è il suo finding** («impostata sul tuo computer, nessuna riga del programma la legge»). 🔑 **Un documento che ha per contenuto un'assenza fallisce ogni `grep` che cerchi una presenza.** Il controllo va letto insieme a ciò che il documento afferma, mai da solo.
>
> **③ E DUE REGOLE PER CHI SCRIVE IL PROSSIMO** — questa cartella cresce di qualche documento al giorno, e le due regole vengono dal misurare quali dei 28 hanno retto e quali no (2026-08-27, 15 esaminati).
> ✅ **Metti l'AMBIENTE in testa.** I documenti che reggono aprono tutti dichiarandolo: *«`pip install verimem 0.7.0` **da PyPI**, venv nuovo, `HOME` finto, moat ON»*. Con l'ambiente scritto, un lettore di fra sei mesi sa **su cosa** valeva il numero, e il documento non invecchia: quelli che misurano il **pacchetto** restano veri per costruzione finché il pacchetto è fermo.
> 🔴 **Tieni i NUMERI FUORI DAL TITOLO.** Tre su tre dei documenti che ho dovuto datare sbagliavano proprio lì: *«I 656 MB»* (il codice ne misura 746), *«il server … dichiara la versione sbagliata»* (curato il giorno dopo), *«Le tre promesse che mancano»* (due colmate). Il titolo è la riga che legge chi segue un puntatore, ed è **l'unica che nessuno rilegge quando aggiorna il contenuto**. Un numero nel corpo si aggiorna; un numero nel titolo resta.
> ⏱️ Corollario: se misuri `main` invece del pacchetto, il tuo documento è una **fotografia** — dichiara lo SHA e mettilo in conto, perché a 700 commit di distanza nessuno saprà più da dove leggerlo.
>
> **Stato della verifica al 2026-08-27 (ws7): 15 dei 28 esaminati.** ✅ REGGONO: `02n` · `02e` (regge, e ha deviato **contro di noi**: 16 → **18** comandi mancanti dal pacchetto) · `03-cose-spente` (20 variabili su 21 vive, la ventunesima **è** il suo finding) · `02b` · `09-i-cancelli`. 🔴 SBAGLIANO, e portano una nota: `02p` · `08-i-656-mb` · `01b`. ⏱️ FOTOGRAFANO `main` e portano la loro distanza in commit: `02o` (761) · `02m` (767) · `01-promesse-vs-realta` (756) · `05-ingestione` (756) · `02c` (741) · `02d` (740) · `02k` (730). ✅ I **dieci che misurano il pacchetto** non sono stati datati: tengono per costruzione finché `0.7.0` resta l'ultima su PyPI — ma `02e` mostra che il **contenuto** può deviare lo stesso, quindi vanno letti, non solo classificati.

---

> 🧭 **AGGIUNTA 06/09 (Iris, ws7) — questa pagina descrive l'8 agosto, e da allora la
> cartella è cresciuta di documenti che NON sono «i file numerati qui accanto».** Il README
> pubblico rimanda qui (`docs/stato-reale/ is where the gap between this README and…`,
> riga 386 della `v0.7.6`), e chi segue quel link entrava senza un percorso verso il lavoro
> corrente. **I file si vedono comunque nella lista della cartella** — non erano nascosti —
> **ma l'indice indirizzava altrove.** Ecco il percorso, dal generale al dettaglio:
>
> · 📄 **`SCHEDA-PRODOTTO.md`** — cosa promette il prodotto, a chi serve **e a chi no**, e
>   la prova in dieci minuti coi tempi misurati. **Se leggi una cosa sola, questa.**
> · 🧭 **`PERCORSI-UTENTE.md`** — i tre modi d'uso reali, con il criterio di arrivo scritto
>   *prima* di eseguirli, e cosa blocca ciascuno.
> · 🩺 **`GRAVITA-DIFETTI.md`** — la scala P0-P4, ogni difetto col suo livello **e la misura
>   che lo cambierebbe**. È il documento che dice quanto è grave quello che non funziona.
> · 📖 **`IL-README-DA-UTENTE.md`** — cosa costruisce il README nella testa di chi lo legge.
> · 🔬 **`LA-PROVA-DELLA-SCHEDA.md`** — come si falsifica la scheda, e perché non possiamo
>   eseguirla noi.
> · 🗃️ **`00-ESAME.md`** — il registro dell'esame, una cella per reperto con la sua
>   evidenza. È la fonte grezza di tutto il resto.
>
> ⚠️ **Le note qui sopra restano valide**: i documenti numerati misurano `544d27bd` o il
> pacchetto, e vanno letti con la loro distanza. Questo blocco non li sostituisce, **dice
> dove continua il lavoro.**

---

## ⚠️ Leggi prima questo: abbiamo misurato due cose diverse

**Il pacchetto che si scarica da PyPI è il codice del 22 luglio — 375 commit indietro,
con lo stesso numero di versione, `0.7.0`.** Trovato da ws2, confermato da ws1, ws4 e
ws7 su tre misure indipendenti.

Tu avevi chiesto *«se un utente la installa cosa fa»*, e sei sezioni su sette
descrivono il **repository**. Quello che l'utente riceve è un'altra cosa, e va detto
prima di tutto il resto.

**Il guardiano in scrittura funziona anche lì**: ws2 ha rieseguito il banco sul
pacchetto vero, 7 promesse su 7 reggono, e la soglia di ammissione è identica
(verificato da ws7 sul wheel scaricato).

⚠️ **Sull'astensione ci siamo sbagliati in tre, e la correzione è istruttiva.** Per
un'ora questo documento ha detto che *«abstention instead of hallucination»* fosse
una promessa **falsa**. Non lo è: l'astensione **è vera su `explain`** ed è
**spenta di proposito su `recall`**, con la ragione scritta in settanta righe di
commento nel codice e la misura già fatta (gate acceso: 8 casi su 8 catturati, zero
astensioni sbagliate).

⇒ Tre di noi hanno detto «rotta» una cosa che il prodotto spiega. Il difetto
vero è più piccolo e più curabile: **quella spiegazione sta nel codice, non dove la
legge chi usa il prodotto.**

**E il resto delle assenze non è casuale:**

| manca nel pacchetto | conseguenza |
|---|---|
| `emit_write` (la telemetria di scrittura) | **spiega le 8.623 righe senza verdetto**: non è un difetto di misura, è un modulo che non c'è. Chiude tre nostre indagini |
| 20 moduli fra cui `retirement_log` | tutta la **superficie di governo** — chi ha ritirato cosa, e quando |
| 13 interruttori su 151 | fra cui le **chiavi di firma dell'audit**, il trust gate MCP e i freni anti-timeout (e i timeout li abbiamo visti scattare oggi sul corpus vero) |
| 4 controlli del `doctor` su 11 | confidence-vs-verifica, undo-window, trust-rank-coverage, embedding-model |
| 11 comandi su 37 | fra cui `save`, che la nostra documentazione insegna |

⇒ **Chi installa oggi riceve un prodotto che scrive bene e non sa raccontare cosa
ha fatto.** Verifica, e non tiene il registro di ciò che ha verificato.

### 📌 E la notizia buona è che quasi tutto si risolve pubblicando

Verificato da ws4 e ws5 su `origin/main`, non ipotizzato:

| | |
|---|---|
| i 13 interruttori mancanti | **ci sono tutti e 13 su main** |
| `save` e altri 15 comandi | non è un difetto di confezionamento: sono **nati dopo** il 22 luglio. Pubblicando da main arrivano da soli |
| l'astensione (`explain`, `trust_report`, `ignorance`) | **esistono tutte su main**, e `ignorance` è fra i comandi registrati |

⇒ **La prima cosa da fare per la 0.7.5 non è una cura: è pubblicare il codice che
abbiamo.** La maggior parte di questo elenco sparisce con un `git merge` e un
`twine upload`, non con altro lavoro.

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

### 🔴 Ora è misurato, e la risposta non è quella che ci aspettavamo

Quel 28,6% era la domanda aperta più grossa: *quanti di quei fatti sono trattenuti a
ragione?* L'abbiamo aperta.

Ho letto **uno per uno** i 45 quarantinati che il giudice approvava a 99-100. Sono
tutti **referti di misura veri** — righe di codice, conteggi, SHA. Riscrivendone 20 su
uno store pulito, **20 su 20 vengono ammessi oggi**. Non sarebbero più trattenuti.

**Ma non è severità, ed è la parte che conta.** Il gate ha due voci che chiedono cose
diverse:

    il giudice   «questa fonte sostiene questo fatto?»       -> sì, 99/100
    il controllo «ogni cifra del fatto sta nella fonte?»     -> no, ne manca una

**Chi scrive misure le attiva entrambe** — e ws1 l'ha verificato su 16 casi su 16.
Nessuna delle due sbaglia: chiedono cose diverse e il prodotto tiene solo la risposta
peggiore, senza dire quale delle due ha parlato.

⇒ E ci si aggiunge un difetto che nessuno aveva visto: **quando il gate migliora,
nessuno rivede la quarantena**. Quei 45 sono stati fermati da criteri poi corretti — uno
scattava sulla parola **«fatto»**, in una memoria dei fatti — e sono rimasti fermi.

---

## Cosa riparare, in ordine

0. **Pubblicare il codice che abbiamo.** Non è una cura, è una pubblicazione — e
   finché non è fatta, ogni cura che scriviamo non arriva a nessuno.
1. **L'astensione** — una memoria che risponde Verona quando le chiedi Trento è
   peggio di una che tace. È il difetto che tocca ogni utente a ogni domanda.
2. **Il primo avvio** — 10 minuti, 1 GB, la verifica spenta e un comando che non
   esiste. Chi prova il prodotto si ferma qui.
3. **Dire quale delle due voci ha parlato** — quando un fatto viene trattenuto,
   l'utente deve sapere se il giudice non gli ha creduto o se manca una cifra: sono
   due problemi diversi e si risolvono in due modi diversi. La cura più piccola,
   proposta da ws1: **dire quale cifra non è stata trovata**.
4. **Rivedere la quarantena quando il gate cambia** — oggi un fatto fermato da un
   criterio poi corretto resta fermo per sempre.

### Già riparato oggi, dopo questo censimento

| | |
|---|---|
| la prova della verifica | ora accanto al voto c'è **la porzione di fonte** che lo giustifica (`35dd263f`) |
| il fatto trattenuto era muto | ora chi interroga sa che **c'era qualcosa e non gli è stato dato** (`a711f653`) |
| gli avvisi non arrivavano all'agente | ora escono anche dalla porta **MCP**, che in una memoria per agenti è quella che conta (`d9fd029c`) |

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
| [10](10-il-contorno-cambia-il-verdetto.md) | il contorno ribalta il verdetto, e non sappiamo perché | ws4 |
| [11](11-la-quantita-vaga-non-viene-confrontata.md) | «gran parte» non viene confrontata con «3 su 40» | ws4 |
| [12](12-il-rimedio-del-caso-difficile-non-arriva.md) | l'escalation della banda parte, costa 20-52 s e non decide | ws4 |
| [13](13-la-taglia-della-fonte-degrada-il-gate-nei-due-versi.md) | la taglia della fonte fa entrare i falsi e uscire i veri | ws4 |

⚠️ **La tabella salta 08 e 09**, che esistono come file (`08-i-656-mb-le-quattro-strade.md`, `09-i-cancelli-del-rilascio.md`): non le aggiungo io perché non so chi le ha scritte e l'ultima colonna è un'attribuzione. Chi le ha scritte si aggiunga. *(rilevato da ws4, 27/08)*

⏱️ I conteggi del corpus sono delle 12:45 dell'8 agosto: cresce mentre lavoriamo, e
ciò che deve coincidere sono le proporzioni, non le cifre assolute.

📌 **Sul metodo**: ogni sezione è stata attaccata da un'altra istanza, che ne ha
rieseguito i comandi alla cieca. In tre ore: ws7 ha ridimensionato da sé un proprio
titolo (da «la soglia è doppia» a «tocca l'1,15% dei fatti»), ws2 ha ribaltato il
verdetto di ws1, ws6 ha reso più grave il finding di ws7, ws1 ha corretto un errore
che avevamo in tre. **Nessuna ha difeso il proprio referto.**
