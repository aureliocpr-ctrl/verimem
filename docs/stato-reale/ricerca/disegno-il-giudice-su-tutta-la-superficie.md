# Il giudice su tutta la superficie — disegno del banco

*Ricerca interna, 12/09/2026 sera. Questo è il **disegno**, non il banco: dice quali superfici
si misurano, che cosa ci si aspetta da ciascuna, e che cosa significa «provato dal pacchetto».
Nessun codice eseguito per scriverlo.*

---

## 1. La domanda, e perché non è «il giudice funziona»

Su una porta sola, misurando, si è scoperto che il moat **non veniva chiamato affatto**: il
parametro non era passato e il valore predefinito era «non chiedere». Il difetto non era nel
giudice: era **nel fatto che nessuno lo interrogava**, e nessuna misura del giudice lo avrebbe
mai visto.

⇒ La domanda di questo banco non è quanto sia bravo il giudice. È:

> **quante superfici scrivono o rispondono senza passare dal giudice, quali di quelle una
> persona usa davvero, e che cosa dice la ricevuta quando il giudizio non c'è.**

## 2. Le superfici, e l'atteso per ciascuna

Tre famiglie, e per ognuna vanno contate **tutte** le porte, non quella comoda.

| famiglia | che cosa fa | atteso |
|---|---|---|
| **scrittura diretta** | un fatto con una fonte entra nello store | il giudizio avviene **prima** della scrittura; la ricevuta dice **chi** ha giudicato e con quale esito |
| **scrittura da conversazione** | un dialogo diventa fatti | ogni fatto estratto passa dallo stesso giudizio della scrittura diretta; i fatti che il dialogo non dice sono **trattenuti** e **contati** nella ricevuta |
| **lettura e risposta** | ciò che esce quando qualcuno chiede | un fatto trattenuto **non** compare come vero; se un motivo per cui non compare esiste, chi legge deve poterlo sapere |

Per ciascuna: **la porta della riga d'arrivo non è la funzione**, è il punto che una persona
tocca davvero — riga di comando, strumento esposto all'agente, metodo pubblico della libreria.
Lo stesso difetto può essere presente su una e assente sull'altra: è già successo.

## 3. Le quattro domande che il banco deve saper distinguere

Per ogni superficie, il verdetto deve cadere in una di queste quattro caselle — **e la
differenza fra la seconda e la terza è dove finora abbiamo sbagliato**:

1. **giudicato e ammesso** — il giudice ha risposto, il fatto entra;
2. **giudicato e trattenuto** — il giudice ha risposto no, il fatto entra segnato e fuori dal
   richiamo ordinario;
3. **non giudicato, e la ricevuta lo dice** — nessun giudice disponibile: accettabile **se e
   solo se** chi scrive lo legge nella risposta;
4. **non giudicato, e la ricevuta non lo dice** — è il difetto: chi scrive crede di avere una
   garanzia che non ha.

Il banco non misura «quanti fatti sono buoni». Misura **in quale casella cade ogni superficie**,
e fallisce sulla quarta.

## 4. Che cosa vuol dire «provato dal pacchetto» — e perché cambia l'esito

Non dal repository: **dal pacchetto installato**, come lo riceve chi ci usa. La differenza non è
formale:

- nel repository esistono cartelle e file che **il pacchetto non contiene**, e un banco che li
  importa prova qualcosa che l'utente non ha;
- le variabili d'ambiente della macchina di sviluppo **non ci sono** altrove: una configurazione
  che qui è attiva per abitudine, da un'altra parte è assente;
- il servizio ausiliario che qui gira **da un'altra parte non è avviato** — ed è il caso ③ del
  paragrafo precedente, oggi **il più frequente fuori di qui**.

⇒ Regola del banco: installare, poi **provare da una cartella che non è quella del codice**, con
l'ambiente ripulito dalle variabili che qui diamo per scontate. Se un esito cambia fra repo e
pacchetto, **vale quello del pacchetto**.

## 5. Il caso che va misurato per primo, non per ultimo

**Il servizio del giudice non c'è.** Qui è l'eccezione, fuori è la regola: chi installa non ha
un daemon avviato. Le domande, in ordine:

1. la scrittura **avviene lo stesso**? (probabile, ed è una scelta difendibile)
2. la ricevuta **dice** che non è stata giudicata, con parole che chi legge capisce?
3. quel fatto resta **segnato** perché un giudizio successivo possa arrivare?
4. **esiste un modo di sapere quanti fatti aspettano ancora un verdetto**, senza leggere i log?

La quarta è quella che l'incidente del vettore mancante ha già fatto pagare: il differimento era
progettato e documentato, e il danno l'ha fatto **il non saperlo**.

## 6. Quello che questo disegno non decide

- **Non decide la cura**: se una superficie cade nella quarta casella, la cura la sceglie chi
  possiede quella porta.
- **Non misura la qualità del giudizio** (quanto è bravo): quella è un'altra domanda, con altri
  dati, e confonderle è il modo più rapido per rispondere a nessuna delle due.
- **Non conta i fatti dello store di nessuno**: il banco lavora su dati propri, creati e
  distrutti nel suo perimetro.
