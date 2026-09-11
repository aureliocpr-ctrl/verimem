# Un motore solo, tanti client leggeri — cosa permette il protocollo, cosa facciamo oggi, cosa costa cambiare

*ws3 Galileo (ricerca), 11/09/2026 ore 19:5x (lette con `date`: `Fri Sep 11 19:49:41 2026`).
Mandato del lead nel post «START 11/09 19:20». **Nessun codice**, e nessuna esecuzione: in
questo turno sono lettore, gli operatori sono Tara e Corrado.*

---

## 1. La domanda, e il numero che la pone

Ieri sera il PC di Aurelio è caduto con un bugcheck mentre il **commit di memoria** era al
**96,7 %**, e nel resoconto di chiusura il lead ha scritto che **22,8 GB stavano in 12 server
MCP**. Tara sta misurando (**T3**, in corso) che cosa pesa dentro un singolo processo
`engram mcp`; il numero che ha portato sul canale è **~2,41 GB di commit per server, identici
da un processo all'altro**.

⚠️ *Quel numero non l'ho misurato io: viene dal canale ed è dichiarato «misura T3 in corso».
Finché T3 non chiude con la sua ripartizione (torch? giudice? embedder?), in questa pagina
vale come **ordine di grandezza**, non come numero da citare fuori.*

La domanda che ne nasce non è «come riduciamo la RAM di un processo», ma:

> **perché i processi sono dodici, e il protocollo ci obbliga davvero ad averne dodici?**

## 2. Cosa dice la specifica MCP — letto, con l'URL

Fonte: <https://modelcontextprotocol.io/specification/2025-06-18/basic/transports>
(versione della specifica **2025-06-18**, letta oggi).

La specifica definisce **due** trasporti standard:

**① stdio.** Testuale:

> «The client **launches the MCP server as a subprocess**.»

Un client, un sottoprocesso. Due client, due sottoprocessi. **La molteplicità dei processi non
è una nostra scelta sbagliata: è la definizione del trasporto che usiamo.** E la specifica lo
raccomanda pure: «Clients **SHOULD** support stdio whenever possible».

**② Streamable HTTP.** Testuale, ed è la riga che risponde alla domanda:

> «In the Streamable HTTP transport, **the server operates as an independent process that can
> handle multiple client connections**.»

Un solo endpoint HTTP (POST e GET sullo stesso path), e le **sessioni** sono parte della
specifica, non un'invenzione nostra:

- il server **PUÒ** assegnare un `Mcp-Session-Id` nell'header della risposta di
  `InitializeResult`; l'id **DEVE** essere globalmente unico e crittograficamente sicuro;
- il client **DEVE** rimandarlo su **ogni** richiesta successiva; un server che lo esige
  **DOVREBBE** rispondere `400` a chi non lo manda;
- il server **PUÒ** terminare una sessione quando vuole: da lì risponde `404`, e il client
  **DEVE** ricominciare con una nuova `InitializeRequest`;
- il client che ha finito **DOVREBBE** mandare `DELETE` con quell'header.

E tre obblighi di sicurezza che, se si apre una porta, diventano nostri:

> «Servers **MUST** validate the `Origin` header… **SHOULD** bind only to localhost
> (127.0.0.1)… **SHOULD** implement proper authentication for all connections.»

**Conclusione di questa sezione, e vale come fatto**: *il protocollo permette già oggi un
motore solo con molti client. Non serve inventare niente: serve cambiare trasporto.*

## 3. Cosa facciamo oggi — letto nel nostro codice

- `verimem/mcp_server.py:68` importa **`from mcp.server.stdio import stdio_server`**, e non
  c'è nessun import di un trasporto HTTP/SSE nel modulo.
- Cercando `streamable_http|sse_server|uvicorn` in tutto il pacchetto, i soli file che
  rispondono sono **`verimem/cli.py`** e **`verimem/gateway.py`** — cioè il **gateway REST**,
  che è un'**altra porta del prodotto**, non un trasporto MCP.
- Cercando una leva (`ENGRAM_MCP_HTTP`, `--http`, `mcp_http`): **nessuna riga**.

⇒ **La porta MCP del prodotto parla solo stdio.** Quindi un processo per client **per
costruzione**, e ogni processo paga per intero il suo modello, il suo giudice e il suo
embedder. Dodici client = dodici motori.

🔎 **E un reperto della classe «il commento manda nel posto sbagliato»**: il commento a
`verimem/mcp_server.py:50` dice che chi vuole i log altrove «ha `ENGRAM_LOG_LEVEL` **e il
transport HTTP**». Chi legge quella riga sulla porta MCP cerca un trasporto HTTP **che su
questa porta non esiste**: il riferimento è al gateway. Una riga da correggere quando si
tocca quel file — **non ora**, non è il mio turno e non è il ticket di nessuno.

## 4. Le tre strade, con il rischio scritto accanto

| | strada | cosa cambia per l'utente | il prezzo, detto prima |
|---|---|---|---|
| **A** | **restare su stdio e dimagrire il processo** (caricare torch/giudice/embedder **solo quando servono**) | niente, se non che la macchina regge | non tocca la **moltiplicazione**: 12 client restano 12 processi. Se il peso vero è il modello, si moltiplica per 12 anche dopo la cura. **È la strada che T63 sta già aprendo** |
| **B** | **un server Streamable HTTP** su `127.0.0.1`, i client si attaccano | un solo motore, un solo modello caricato, una sola coda di scrittura sullo store | **punto unico di guasto** (cade il server, cadono tutti i client) · **coda**: le richieste dei client si serializzano dove prima erano parallele, e il giudice è lento (misurato: 303 s il primo `remember` con fonte) · **un salto in più** (rete locale invece di pipe) · i **tre obblighi di sicurezza** della specifica diventano codice da scrivere e da provare · **chi avvia il server?** un processo che nessun client possiede va gestito (avvio, riavvio, versione) |
| **C** | **ibrido**: stdio per il client, e il lavoro pesante (embedder/giudice) in **un solo servizio** condiviso dietro le quinte | come B sul consumo, senza cambiare come i client si connettono | è ciò che il prodotto **già fa a metà** col `HIPPO_ENCODE_DELEGATE_ONLY` e il daemon dell'embedding — e con quel meccanismo abbiamo già preso **due incidenti in due giorni** (il daemon rinato a 384 mentre lo store scrive a 768; i fatti scritti senza vettore). **La strada non è nuova: è già qui, ed è quella che oggi si rompe in silenzio** |

**Osservazione che vale più delle tre righe sopra**: la strada C esiste già e i suoi difetti
sono i nostri ticket aperti (T60, T-MAP-9, i 14 fatti senza vettore). Prima di aprire la
strada B — che sposta *tutto* nello stesso schema — la domanda onesta è: **perché la
condivisione che abbiamo già non regge?** Se la risposta è «il servizio condiviso non dichiara
la sua versione al client», quel difetto si ripresenta identico, e più grande, su un server
MCP condiviso.

## 5. Quello che NON ho verificato, e come si verifica

Il lead ha chiesto anche come **mem0 / Letta / Zep** servono più agenti e quali **protocolli fra
agenti** esistono e chi li parla. In questo turno **non l'ho letto: NON VERIFICATO.** Non lo
riempio con ciò che «di solito» fanno quei prodotti — sarebbe esattamente la confabulazione
plausibile che il nostro moat deve fermare.

Come si chiude, in ordine di costo:
1. la pagina della documentazione di ciascuno sul **deployment server/self-hosted** e sul
   **multi-tenant** (un URL a testa, letto e citato);
2. se il server è multi-client: **come isola i dati fra agenti** (chiave per agente? un DB per
   agente? un campo?) — è la domanda che decide se il modello è copiabile da noi;
3. i protocolli fra agenti (**A2A** di Google, ACP, e MCP stesso come «porta» non come bus):
   quali **client reali** li parlano oggi — perché un protocollo che nessun client parla è una
   capacità spenta, e su quelle abbiamo già una lezione.

## 6. Cosa serve, prima di decidere

1. **T3 di Tara** con la ripartizione dei ~1,9-2,41 GB: **se il peso è il modello**, la strada A
   da sola non basta e B/C diventano la vera domanda; **se è altro** (import, cache, copie),
   forse la strada A chiude tutto senza un salto architetturale.
2. **Quanti client servono davvero contemporaneamente**: dodici perché servono, o dodici perché
   nessuno li chiude? Non l'ho misurato — è una riga da mettere in coda a un operatore, non un
   numero da indovinare.
3. La **decisione D-1** che ne segue non è mia: io porto il quadro, la sceglie il lead con
   Aurelio.

---

*Fonti citate: la specifica MCP 2025-06-18 (letta oggi, URL sopra) e il codice del nostro
pacchetto alle righe indicate. Tutto ciò che in questa pagina non ha un URL o una riga di
codice accanto è marcato **NON VERIFICATO**.*
