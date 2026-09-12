# T81 — quando il fatto e la fonte non sono nella stessa lingua

*Ticket, 12/09/2026. **Prima la misura, poi la cura**: qui non si propone nessuna cura, si
disegna il banco che dice se il difetto c'è e quanto è grande. Il reperto che l'ha aperto è di
chi tiene i dati; il disegno è di ricerca. **Nessuna esecuzione**: §6.*

---

## 1. Il reperto

Una scrittura con **il fatto in italiano e la fonte in inglese** è stata **quarantinata**, e così
la sua gemella: due scritture su due. Non è un'osservazione sul modello — è una scrittura vera
fatta alla porta.

⚠️ **Ma due casi non sono un tasso**, e un tasso su venti casi di una cella sola sarebbe **un
numero vero e muto**: non distinguerebbe *«la lingua diversa penalizza»* da *«quei venti claim
erano deboli»*.

## 2. Quello che abbiamo già, e che NON è questo

Il prodotto ha già affrontato una questione di lingue, e va citata perché dice dove guardare:

    verimem/semantic_selfclaim.py  —  L1.20, 09/07/2026
    «la famiglia L1 era EN/IT: lo stesso claim gonfiato in otto altre lingue
     passava il gate PULITO — 8 su 10»
    cura: usare l'embedder multilingue COME rilevatore; banco con recall 1.00 in 10 lingue

⇒ Quello riguarda **L1**, il claim **senza** fonte. Qui parliamo del **moat**, il claim **con**
fonte, giudicato per sostegno. **Due strati diversi e due difetti opposti**: là il gate lasciava
passare, qui ferma. Nessun doppione — ma una lezione che vale: *quando da noi qualcosa dipende
dalla lingua, non è mai l'embedder: è il pezzo addestrato in inglese.*

## 3. L'ipotesi, scritta PRIMA della misura perché possa cadere

> **Il giudice del moat è tarato su un insieme in inglese, quindi a pagare non è «l'italiano»:
> è la COPPIA con due lingue diverse.**

    se l'ipotesi regge     IT↔IT e EN↔EN stanno insieme in alto, IT↔EN e EN↔IT stanno sotto
    se e' l'italiano       IT↔IT scende insieme a IT↔EN, e EN↔IT resta in alto
    se e' il claim         tutte e quattro le celle stanno insieme: il difetto non esiste

## 4. Il banco — **quattro celle**, non una

Lo stesso contenuto, scritto quattro volte, **una sola variabile per confronto**:

    claim IT · fonte IT     controllo, stessa lingua
    claim EN · fonte EN     controllo, stessa lingua, l'altra
    claim IT · fonte EN     il caso trovato
    claim EN · fonte IT     il caso SPECULARE — nessuno l'ha ancora guardato

🔑 **La quarta cella è quella che separa le due spiegazioni.** Senza, il numero resta ambiguo.

### I due controlli, obbligatori nello stesso braccio

    POSITIVO   una coppia che il moat DEVE fermare in tutte e quattro le celle
               (il claim afferma un valore che la fonte non contiene)
               se passa -> il banco non sta misurando il gate: si ferma
    NEGATIVO   una coppia sostenuta parola per parola, che DEVE essere ammessa
               se cade -> il gate ferma tutto, e un «100% di quarantena» non
               sarebbe un reperto ma un sintomo del banco

### Due trappole del disegno, dichiarate

1. **I claim non devono somigliare a un'auto-affermazione**: niente «verificato», «funziona»,
   «fatto». Se scatta lo schermo lessicale, misuriamo **un altro strato** e il numero non parla
   del moat.
2. **Ogni numero del claim deve comparire nella fonte.** Un valore che la fonte non contiene fa
   scattare il controllo lessicale dei numeri: è il **controllo positivo**, non un caso ordinario,
   e va tenuto separato.

### Il livello, dichiarato

Si misura **alla porta**: una scrittura vera con la fonte, non una chiamata alla funzione del
gate. *Il livello a cui si misura decide il verdetto*, e su questo ci siamo già bruciati.

### Che cosa deve dire il rapporto — e non è «il tasso»

    per ogni cella:   ammessi / quarantinati          (il conteggio)
                      punteggio MEDIANO e minimo      (quanto lontano dal taglio)
                      chi ha fermato, per nome        (il campo che nomina il layer)

Un tasso senza il punteggio non dice se siamo **a un punto** dalla soglia o **a quaranta**, e la
cura che serve nei due casi è diversa.

## 5. Le venti coppie

*Fatti brevi, sostenuti, senza valori assenti dalla fonte. Ogni riga si scrive in quattro celle.*

    01  IT  La sala macchine ha 64 gigabyte di memoria.
        EN  The machine room has 64 gigabytes of memory.
        FI  Scheda tecnica: sala macchine, memoria 64 GB, due processori.
        FE  Datasheet: machine room, memory 64 GB, two processors.
    02  IT  Il magazzino misura 4200 metri quadri.        EN  The warehouse measures 4200 square metres.
        FI  Planimetria: magazzino, superficie 4200 mq.   FE  Floor plan: warehouse, area 4200 sqm.
    03  IT  Il contratto dura 36 mesi.                    EN  The contract lasts 36 months.
        FI  Clausola 2: durata del contratto 36 mesi.     FE  Clause 2: contract duration 36 months.
    04  IT  La libreria e' alla versione 0.7.7.           EN  The library is at version 0.7.7.
        FI  Registro rilasci: versione corrente 0.7.7.    FE  Release log: current version 0.7.7.
    05  IT  Il timeout e' di 30 secondi.                  EN  The timeout is 30 seconds.
        FI  Configurazione: timeout 30 secondi.           FE  Configuration: timeout 30 seconds.
    06  IT  Il salvataggio parte alle 02:00 ogni giorno.  EN  The backup starts at 02:00 every day.
        FI  Pianificazione: salvataggio giornaliero 02:00. FE  Schedule: daily backup at 02:00.
    07  IT  I centri dati sono due, a Milano e Francoforte. EN  There are two data centres, in Milan and Frankfurt.
        FI  Infrastruttura: due centri dati, Milano e Francoforte. FE  Infrastructure: two data centres, Milan and Frankfurt.
    08  IT  La licenza e' MIT.                            EN  The licence is MIT.
        FI  File di licenza: MIT.                         FE  Licence file: MIT.
    09  IT  La coda contiene 500 elementi.                EN  The queue holds 500 elements.
        FI  Verbale: la coda aveva 500 elementi.          FE  Minutes: the queue held 500 elements.
    10  IT  Il rapporto esce ogni trimestre.              EN  The report is published quarterly.
        FI  Procedura: pubblicazione trimestrale del rapporto. FE  Procedure: quarterly publication of the report.
    11  IT  Il sensore lavora fra -20 e 60 gradi.         EN  The sensor works between -20 and 60 degrees.
        FI  Scheda: intervallo operativo -20 / 60 gradi.  FE  Datasheet: operating range -20 / 60 degrees.
    12  IT  Il pagamento e' a 60 giorni.                  EN  Payment terms are 60 days.
        FI  Condizioni: pagamento a 60 giorni.            FE  Terms: payment at 60 days.
    13  IT  L'archivio contiene 1200 documenti.           EN  The archive contains 1200 documents.
        FI  Inventario: 1200 documenti archiviati.        FE  Inventory: 1200 documents archived.
    14  IT  L'interfaccia risponde in JSON.               EN  The interface answers in JSON.
        FI  Specifica: le risposte sono in JSON.          FE  Specification: responses are in JSON.
    15  IT  L'addestramento e' durato 3 epoche.           EN  Training lasted 3 epochs.
        FI  Registro: addestramento, 3 epoche.            FE  Log: training, 3 epochs.
    16  IT  L'ufficio e' chiuso la domenica.              EN  The office is closed on Sundays.
        FI  Orario: chiuso la domenica.                   FE  Opening hours: closed on Sundays.
    17  IT  Il cavo e' lungo 15 metri.                    EN  The cable is 15 metres long.
        FI  Distinta: cavo, lunghezza 15 metri.           FE  Bill of materials: cable, length 15 metres.
    18  IT  La batteria dura 8 ore.                       EN  The battery lasts 8 hours.
        FI  Prova: autonomia della batteria 8 ore.        FE  Test: battery life 8 hours.
    19  IT  La suite ha 1400 casi.                        EN  The suite has 1400 cases.
        FI  Riepilogo: 1400 casi nella suite.             FE  Summary: 1400 cases in the suite.
    20  IT  L'indice si ricostruisce ogni settimana.      EN  The index is rebuilt weekly.
        FI  Manutenzione: ricostruzione settimanale dell'indice. FE  Maintenance: weekly index rebuild.

    CONTROLLO POSITIVO   claim «La coda contiene 540 elementi.» con la fonte 09 (che dice 500)
                         DEVE essere fermato in tutte e quattro le celle
    CONTROLLO NEGATIVO   claim identico alla fonte 08 («La licenza e' MIT.» / fonte 08)
                         DEVE essere ammesso nelle celle a lingua uguale

## 6. Quello che questo ticket NON fa

- **Non propone una cura.** Se la misura dice che le celle a lingue diverse cadono, la cura è una
  decisione che segue il numero: ritarare, tradurre la fonte prima di giudicare, o dichiarare il
  limite. Sceglierla adesso vorrebbe dire sceglierla senza dati.
- **Non è stato eseguito.** Chi scrive è lettore. Le ottanta scritture vanno fatte **in un solo
  processo** (il giudice si carica una volta: l'ultimo warmup misurato è 54,6 s, poi i giudizi
  sono rapidi) e su uno store temporaneo.
- **Non tocca lo store di lavoro**: il banco scrive su una cartella usa-e-getta.
