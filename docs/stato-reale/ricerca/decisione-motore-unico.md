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

🔎 **Un indizio a favore di A, e il motivo per cui NON basta**: nella misura la scheda risulta
**allocata al 90 % con lo 0 % di utilizzo**. Tiene separate due cose che è facile confondere —
**il contesto è riservato** (e occupa) e **il calcolo avviene** (e usa). Lo zero dice che in
*quell'istante* nessuno calcolava; **non** dice che il giudizio non usi la scheda quando gira.
⇒ La misura giusta non è un'istantanea a riposo: è l'utilizzo **durante** un giudizio. Se anche
lì è vicino a zero, allora quei contesti sono puro peso e A è gratis davvero; se sale, A ha un
prezzo e va ristretta come sopra.
⚠️ Questa è la falsificazione che più facilmente passa inosservata, perché A *sembra* una pulizia
e invece è una scelta di prestazioni.

**Aggiornamento del 12/09 — A è più larga di come la raccomandazione la descrive.** La prima cura
era stata cercata con il nome dell'acceleratore e aveva trovato **due** punti. Ma un modello
costruito **senza dire su quale dispositivo** prende la scheda da sé, e quel nome **nel nostro
codice non compare**: la ricerca giusta non era la parola, era **«chi costruisce un modello»** —
e i punti sono **cinque**, due dei quali già a posto, con il caricatore dell'embedder fra quelli
che mancavano. ⇒ **A non è «una riga»**: è una leva esterna **più** uno sweep sui costruttori,
tenuto da un presidio che cammina il pacchetto. Non la sposta dal primo posto; **le toglie
l'aria di cosa gratuita**, e chi la vende come tale sta descrivendo la versione da due righe che
copriva metà del problema.

### F3 — «il presidio della versione non copre i modi in cui quel servizio si rompe davvero»

**L'affermazione sotto accusa**: che «dichiara e rifiuta» basti a irrobustire C. Il presidio
ferma **un** modo di guasto (modello diverso da quello dello store). Non ferma: il servizio che
**muore** e lascia i client a scrivere senza; la **coda** che si allunga; due client che scrivono
**insieme**; il servizio che risponde con **latenza** invece che con errore.

**Misura che decide — e si può fare oggi, leggendo**: prendere i **due incidenti già
documentati**, elencare i modi di guasto osservati, e contare **quanti sarebbero stati fermati
dal presidio della versione**.

### F3 — FATTA, leggendo il postmortem. E l'esito rovescia il punto 2 della raccomandazione

*Letto il postmortem dell'incidente delle quattordici scritture senza vettore. La catena ha
**sette anelli**; accanto a ciascuno, se il «presidio della versione» lo avrebbe fermato.*

| # | anello, come sta nel postmortem | il presidio lo ferma? |
|---|---|---|
| 1 | discovery e lock del servizio stanno **nella home dell'utente, mai nella cartella dei dati**: un banco che isola la cartella **non isola il servizio** | **no** — è un problema di *dove* si cercano, non di *quale versione* |
| 2 | un processo isolato trova la discovery globale, **avvia un servizio col proprio modello e lo registra per tutti** | **no** — e anzi: il servizio trovato **«non dichiara il suo modello»** |
| 3 | il client **rifiuta** il modello che non combacia | **SÌ — e c'era già** |
| 4 | in modalità «solo delega» **non esiste ripiego locale**, quindi il rifiuto diventa un'eccezione | no |
| 5 | l'eccezione viene catturata e la riga **viene scritta senza vettore**, con un solo avviso nel log | no |
| 6 | la **ricevuta dice `stored=True judged=True`** e non dice che il vettore manca: nove scritture di fila passano per riuscite | **no — ed è l'anello che fa il danno** |
| 7 | il servizio resta **giù per ore** e nessuno se ne accorge | no |

🔴 **Esito: 1 anello su 7, e quell'uno era già presente.** Il postmortem lo dice testualmente —
*«il client lo rifiuta, ed è giusto»*. **Il presidio della versione non è la cura di questo
incidente: è la parte che ha funzionato.** Il danno è arrivato **a valle** del rifiuto, perché il
rifiuto si è trasformato in una scrittura muta con una ricevuta che diceva di sì.

⇒ **«C irrobustita» va riscritta**, e in ordine di efficacia diventa: ① la **ricevuta non mente**
(chi scrive deve sapere che il vettore manca) · ② il servizio **dichiara** il proprio modello
(metà del presidio che davvero manca) · ③ discovery e lock **dove stanno i dati**, non nella home
· ④ il rifiuto del client, **che c'è già**.

*Nota su cosa questa lettura non prova*: è **un** incidente su due. L'altro (il servizio rinato
con un modello diverso) ha la stessa radice, ma non l'ho scomposto anello per anello: **NON
VERIFICATO** che la proporzione sia la stessa.

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

**Conto fatto sui numeri che già abbiamo — è una STIMA, non una misura, e le assunzioni sono
dichiarate.** Due tempi documentati nelle cronache interne dei giorni scorsi (regimi diversi,
non misurati oggi): **~303 s** il primo salvataggio con fonte dal pacchetto sotto la porta
MCP (caso **freddo**, comprende il caricamento del giudice) e **~22 s** un giudizio **a
regime** su CPU.

Assunzioni: il giudizio è **seriale** (un client alla volta) e ogni scrittura con fonte ne paga
uno intero. Allora la capacità della coda condivisa è

    60 s / 22 s  ≈  2,7 scritture con fonte al minuto, in tutto e per tutti i client

⇒ **Con tre client che salvano insieme, il terzo aspetta oltre un minuto**; con dieci, l'ultimo
aspetta quasi quattro minuti — e la coda cresce senza limite appena il carico supera quella
soglia. Oggi quel costo non si vede perché **ogni client ha il suo giudice** e i giudizi vanno
in parallelo: **è esattamente la cosa che B toglie**.

⚠️ **Che cosa questa stima NON dice**: non dice quante scritture con fonte al minuto facciamo
davvero nel momento di punta — **non è misurato**, ed è il numero che trasforma la stima in
verdetto. Non dice nulla su un giudice che sappia lavorare in parallelo: se ne esistesse uno, la
soglia si sposta e F6 cade.

⇒ **Conseguenza per la raccomandazione**: B non va descritta come «la terza strada,
se serve». Va descritta come **«la strada che richiede prima di rendere il giudizio parallelo o
molto più veloce»** — altrimenti scambiamo un vincolo di memoria con un vincolo di attesa, e il
secondo lo paga l'utente a ogni salvataggio.

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
