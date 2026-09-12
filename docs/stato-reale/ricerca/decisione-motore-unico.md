# Decisione: come servire più client senza moltiplicare il motore

*Ricerca interna, 12/09/2026. Questa pagina **non** argomenta a favore della raccomandazione: la
scrive per intero e poi cerca di **abbatterla**. Per ogni pezzo c'è l'osservazione che lo
smentirebbe e la misura che la produce. I fatti su cui poggia stanno nella pagina «un motore
solo, tanti client leggeri», ciascuno con la sua fonte.*

---

## 1. La raccomandazione, come è stata formulata

1. **Prima A** — il server per sessione **non inizializza l'acceleratore**, e i carichi pesanti
   si fanno **pigri** (si caricano quando servono, non all'avvio).
2. **Poi C irrobustita** — il servizio condiviso che **già abbiamo**, più il **presidio della
   versione**: il servizio **dichiara** modello e dimensione, il client **rifiuta** ciò che non
   combacia.
3. **B solo dopo** — un server condiviso al posto di un processo per client, **se e solo se**,
   fatte A e C, i client pesanti restano oltre quello che la macchina regge.
4. **In ogni strada, il giudizio resta davanti alla scrittura.**

## 2. Perché regge (i fatti che la sostengono, non le opinioni)

- **A ha un bersaglio misurato**: otto processi tengono un contesto sull'acceleratore, la scheda
  è al **90 %** con **0 %** di utilizzo, e la causa sono **due righe** che scelgono
  l'acceleratore appena è disponibile. Nessuna di quelle otto occupazioni sta servendo un
  calcolo.
- **A non pregiudica nulla**: è una leva di configurazione, reversibile, e lascia aperte C e B.
- **C esiste già**: il servizio condiviso non è un'idea, è in piedi. E i suoi due guasti noti
  hanno **la stessa radice**: il servizio non dichiara al client con quale modello sta lavorando.
- **B è la più costosa e la meno reversibile**: introduce un punto unico di guasto, una coda dove
  oggi c'è parallelismo, un salto in più, e tre garanzie di sicurezza da scrivere. Metterla per
  ultima è coerente col fatto che nessuna misura, oggi, dice che serva.

## 3. Quello che la smentirebbe — sei falsificazioni, ognuna con la sua misura

### F1 — «A non tocca il vincolo che ci ha fatto cadere»

**L'affermazione sotto accusa**: che togliere l'acceleratore ai server riduca la **memoria
impegnata**. È il punto più debole di tutta la raccomandazione, e lo dice la misura stessa:
**quanta parte dei 2,29 GB di commit in più venga dal contesto dell'acceleratore NON è
misurata**; le librerie mappate sono *file-backed* e pesano sul working set, **non** direttamente
sul commit.

**Misura che decide**: il **commit** di un processo server appena avviato, **con** e **senza**
l'acceleratore visibile, sulla stessa macchina e nello stesso momento (A/B in una sola
esecuzione). Se la differenza è **≈ 0**, A libera la scheda ma **non** la memoria impegnata, e la
ragione che la mette al primo posto cade: resta buona per la VRAM, non per il commit.
*Costo noto: un processo nuovo costa ~2,59 GB, quindi va fatta quando il tetto lo consente.*

### F2 — «A cura la macchina e rompe ciò che l'utente paga»

**L'affermazione sotto accusa**: che il calcolo sull'acceleratore non serva. Le due righe
incriminate stanno nel **giudice** — cioè nel percorso che l'utente aspetta quando scrive con una
fonte, e che in passato è arrivato a **centinaia di secondi** al primo uso.

**Misura che decide**: il tempo di **un giudizio** sulla stessa frase, con e senza acceleratore.
Se sulla CPU costa sensibilmente di più, A **non è gratis**: scambia memoria della scheda con
latenza dell'utente, e va allora ristretta ai processi che **non** giudicano (i client che solo
leggono), lasciando l'acceleratore a **uno** che giudica.
⚠️ Questa è la falsificazione che più facilmente passa inosservata, perché A *sembra* una pulizia
e invece è una scelta di prestazioni.

### F3 — «il presidio della versione non copre i modi in cui quel servizio si rompe davvero»

**L'affermazione sotto accusa**: che «dichiara e rifiuta» basti a irrobustire C. Il presidio
ferma **un** modo di guasto (modello diverso da quello dello store). Non ferma: il servizio che
**muore** e lascia i client a scrivere senza; la **coda** che si allunga; due client che scrivono
**insieme**; il servizio che risponde con **latenza** invece che con errore.

**Misura che decide — e si può fare oggi, leggendo**: prendere i **due incidenti già
documentati**, elencare i modi di guasto osservati, e contare **quanti sarebbero stati fermati
dal presidio della versione**. Se sono **meno della metà**, il presidio è necessario ma non
sufficiente, e «C irrobustita» va riscritta con l'elenco completo (dichiarazione + battito +
rifiuto esplicito quando il servizio non c'è).

### F4 — «C non riduce il consumo, perché il peso non sta dove lo spostiamo»

**L'affermazione sotto accusa**: che spostare il lavoro pesante in un servizio condiviso tolga
peso ai client. Vale **solo** se il client, dopo, non carica più la libreria pesante. Se il
client continua a importarla per altri motivi (un percorso di lettura, un import all'avvio, una
dipendenza indiretta), il consumo resta.

**Misura che decide**: le **mappe** di un client che usa il servizio condiviso — la libreria
pesante c'è ancora, sì o no? È la stessa lettura già fatta per confrontare processo pesante e
leggero, quindi **a costo zero e senza avviare niente**.

### F5 — «l'ordine è sbagliato: la prima non è A, è il presidio»

**L'affermazione sotto accusa**: l'ordine, non le strade. **A protegge la macchina; il presidio
di C protegge i dati.** Finché il presidio non c'è, il servizio condiviso può continuare a far
entrare scritture con il modello sbagliato — ed è già successo. Una macchina che va in
sofferenza si riavvia; **una memoria che si riempie di righe scritte male non si riavvia**.

**Misura che decide**: quante scritture sono passate per il servizio condiviso **da quando il
difetto esiste**, e quante di quelle sono **recuperabili**. Se il numero è diverso da zero e
cresce ogni giorno, **il presidio va prima di A**, e A resta comunque la cura più economica —
solo, seconda.

### F6 — «il vincolo del giudizio davanti alla scrittura rende B impossibile, non ultima»

**L'affermazione sotto accusa**: che B sia «l'ultima strada». Se il giudizio resta davanti alla
scrittura (e deve restare: è la promessa del prodotto), allora in B **tutte le scritture di tutti
i client passano da una coda sola davanti a un giudizio lento**. Non è un costo in più: potrebbe
essere **il motivo per cui B non si fa affatto**.

**Misura che decide**: il tempo di un giudizio × il numero di scritture al minuto nel momento di
punta. Se il prodotto è già oggi vicino al limite con **un** client, B non è «l'ultima strada»:
è **una strada chiusa**, e la vera alternativa diventa «meno client pesanti», non «un motore
solo».

## 4. La misura che deciderebbe l'intera raccomandazione

Se se ne potesse fare **una sola**, è quella di **F1**: **il commit di un server appena avviato,
con e senza acceleratore, nella stessa esecuzione.**

- Se la differenza è **grande** → A è la prima cosa da fare, per la ragione giusta, e la
  raccomandazione regge così com'è.
- Se la differenza è **piccola o nulla** → A resta (per la scheda), ma **non** è la cura del
  vincolo che ci ha fatto cadere: il primo posto passa a **F5** (il presidio, che protegge i
  dati) e la domanda sul commit torna aperta, con la risposta da cercare in F4.

**Le due letture che si possono fare subito, senza avviare niente e senza toccare il tetto**: F3
(contare i modi di guasto dei due incidenti contro ciò che il presidio ferma) e F4 (le mappe di
un client che usa il servizio condiviso).

## 5. Cosa questa pagina non dice

- **Non dice quale strada prendere**: dice a quali condizioni la raccomandazione è giusta e a
  quali è sbagliata.
- **Non contesta il vincolo** del giudizio davanti alla scrittura — lo tratta come dato, perché è
  la promessa del prodotto; F6 misura quanto costa, non se vada tolto.
- **Non contiene misure nuove fatte da chi scrive**: chi scrive è in sola lettura. Ogni numero
  citato viene dalle misure interne già pubblicate, e quello che manca è marcato come mancante.

---

*Ogni affermazione ha accanto la sua fonte, oppure è marcata come non misurata.*
