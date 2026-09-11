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

## 5. Come fanno gli altri — tre pagine lette, con l'URL

*Letto alle 19:55-20:00 dell'11/09. Ogni riga qui sotto ha la sua fonte; dove la pagina non
risponde, sta scritto che non risponde, invece di riempirlo con ciò che «di solito» fanno.*

**Letta** — <https://docs.letta.com/guides/selfhosting>
Server unico che tiene **più agenti**: immagine `letta/letta:latest`, **una porta** (8283) per
la REST API, stato in **PostgreSQL con pgvector**. Come i dati siano isolati **fra** agenti
quella pagina **non lo dice**. E porta un avviso che conta per chi volesse copiarne la forma:
«The Docker image is no longer an actively maintained or supported Letta product surface».

**mem0** — <https://docs.mem0.ai/open-source/overview>
Due modalità, e sono esattamente le nostre due strade: **libreria in-process**
(`pip install mem0ai`) **oppure** un **server self-hosted** — «A Docker stack with a dashboard,
**per-user API keys**, and a **request audit log**». Il ruolo preciso di `user_id`/`agent_id`/
`run_id` nell'isolamento non è in quella pagina.

**Zep** — <https://help.getzep.com/concepts>
Modello **per utente**: «Each user has a user graph and thread history», e il grafo è «A
Context Graph that stores context for **one** application user». Il multi-agente su un solo
servizio quella pagina non lo affronta.

🔑 **Il filo che tengono tutti e tre, ed è la cosa che ci riguarda davvero.** Quando una
memoria smette di essere una libreria dentro il processo del client e diventa **un servizio
condiviso**, compare sempre la stessa domanda nuova: **«di chi è questo dato?»** — chiavi per
utente in mem0, un grafo per utente in Zep, agenti come oggetti di prima classe in Letta.

Da noi quella domanda **oggi non esiste**, e non perché l'abbiamo risolta: perché **ogni
processo è di un client solo**, e l'isolamento ce lo regala il sistema operativo. La strada B
non ci porta solo un endpoint: ci porta **quella domanda**, e con essa autenticazione,
`Origin`, e un registro di chi ha chiesto cosa — le tre cose che la specifica MCP elenca come
**MUST/SHOULD** e che mem0 ha già in vetrina come parte del suo server.

## 5-bis. I protocolli fra agenti — e la domanda che conta più della loro esistenza

**A2A (Agent2Agent)** — <https://a2a-protocol.org/latest/> (letto l'11/09 alle ~19:57).
«An open standard for seamless communication and collaboration between AI agents»,
«originally developed by Google and **donated to the Linux Foundation**», con un comitato in
cui siedono AWS, Cisco, Google, IBM Research, Microsoft, Salesforce, SAP e ServiceNow.

**Non è un concorrente di MCP, e la pagina lo dice da sé**: MCP «standardizes how an agent
connects to its **tools**, APIs, and resources»; A2A serve agli agenti per «**discover each
other**, delegate tasks, and share results». Strumenti contro pari: due assi diversi.

⚠️ **E qui il reperto, che vale per la nostra decisione**: quella pagina elenca **sei SDK**
(Python, JavaScript, Java, C#, Go, Rust), campioni su GitHub e «partner nella comunità» — ma
**non nomina un solo client reale che lo parli in produzione**. Esistono gli SDK; chi li usa
davvero, dalla fonte ufficiale, **non risulta**.

È la nostra classe «**una capacità spenta non emette segnale**» applicata a un protocollo:
adottare A2A perché «è lo standard» significherebbe costruire una porta e poi misurare quanti
ci passano. Prima di aprirla, la domanda da chiudere è **quale client che Aurelio usa
davvero** (Claude Code, l'app, un IDE) parla A2A oggi — e questo **NON l'ho verificato**: la
pagina ufficiale non basta a rispondere, e un elenco di partner non è un elenco di client.

Per il nostro problema di stasera, comunque, **A2A non c'entra**: dodici processi da 2 GB non
sono un problema di *agenti che si parlano*, sono un problema di *client che condividono un
motore* — cioè MCP e il suo trasporto, la sezione 2.

## 5-ter. I numeri di T1/T3 sono arrivati (Tara, 11/09 ~20:04) — e spostano la domanda

Dal resoconto di Tara sul canale, **letto e non misurato da me**:

    pid 24788  intfloat/multilingual-e5-base   dim 768  porta 60479
               commit proprio 4,86 GB · rss 1,05 GB · store 18.147 fatti · differiti 0
    pid  2748  paraphrase-multilingual-MiniLM-L12-v2  dim 384  porta 60548
               (serve il recall proattivo dell'hook)
    insieme    9,68 GB

Tre cose cambiano rispetto a come avevo impostato la pagina due ore fa:

**① Non abbiamo «dodici processi», ne abbiamo dodici più due — e i due sono già la strada C.**
I due daemon di embedding **sono** il servizio condiviso che la strada C propone: esistono, sono
in piedi, e sono **due**, con **due modelli diversi** (768 per lo store, 384 per l'hook). La
condivisione non è un'idea da valutare: è una cosa che facciamo già, e che **già si sdoppia**.

**② Il numero che satura non è la RAM: è il commit, e per questi processi vale ~4,6 volte il
residente** (4,86 GB di commit contro 1,05 di RSS, su quel pid). È la spiegazione del paradosso
di ieri sera — «commit 88,6 % **con 8 GB di RAM libera**»: chi guarda la RAM vede spazio, chi
guarda il commit vede il muro, e a cadere è la macchina. ⚠️ **Il rapporto è misurato su UN
processo**: che valga anche per i server MCP è un'**ipotesi**, non un fatto — si chiude con la
riga di coda della sezione 6.

**③ La ripartizione dei ~1,9-2,41 GB per server MCP non c'è ancora**, e resta la domanda che
decide: se dentro un `engram mcp` il peso è **il modello**, allora togliere il modello dai
dodici (strada C, fatta bene) vale più che condividere il server (strada B); se il peso è
altro, si chiude con la strada A.

🔴 **E un difetto che Tara ha trovato e che riguarda questa pagina**: il docstring del secondo
daemon dichiara «LEGACY MiniLM-L6», mentre lo store è e5-base/768 (T67, suo). Vale come
avvertimento per chiunque progetti il motore unico: **un servizio condiviso che non dichiara
correttamente il proprio modello è peggio di nessun servizio condiviso** — perché i client non
hanno modo di accorgersi del disallineamento. È esattamente il difetto che T-MAP-9 ha già
pagato una volta.

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
