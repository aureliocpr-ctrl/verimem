# Un motore solo, tanti client leggeri — v2

*Ricerca interna, 12/09/2026. Versione 2: la v1 (11/09) aveva il protocollo e le tre strade;
questa aggiunge un progetto confrontabile **letto nel codice**, i numeri della misura interna, e
in fondo la **bozza della decisione**. Nessun codice di prodotto è stato scritto o eseguito per
questa pagina.*

---

## 1. La domanda

Su una macchina da sviluppo, ogni client che usa la memoria via MCP fa partire **il proprio
processo server**, e ciascuno carica il proprio modello. Con una decina di client aperti la
memoria impegnata dalla somma dei processi diventa il vincolo della macchina — non la CPU, non
il disco: **la memoria impegnata (commit)**.

La domanda non è «come riduciamo un processo», ma: **perché i processi sono tanti, e il
protocollo ci obbliga davvero ad averne tanti?**

## 2. Cosa dice la specifica MCP — letto, con l'URL

Fonte: <https://modelcontextprotocol.io/specification/2025-06-18/basic/transports> (spec
**2025-06-18**, letta l'11/09).

**stdio** — testuale: «The client **launches the MCP server as a subprocess**.» Un client, un
sottoprocesso; N client, N sottoprocessi. E la specifica lo raccomanda: «Clients **SHOULD**
support stdio whenever possible».

**Streamable HTTP** — testuale: «the server operates as an independent process that **can handle
multiple client connections**». Un solo endpoint (POST e GET sullo stesso path). Le **sessioni**
sono nel protocollo: `Mcp-Session-Id` assegnato nell'`InitializeResult`, rimandato dal client su
ogni richiesta, `404` quando il server la chiude (e il client re-inizializza), `DELETE` per
chiuderla dal lato client.

Tre obblighi che diventano nostri se apriamo una porta: validare l'header `Origin` (**MUST**),
legarsi a `127.0.0.1` in locale (**SHOULD**), autenticare (**SHOULD**).

⇒ **Il protocollo permette già oggi un motore solo con molti client.** Non serve inventare
niente: serve cambiare trasporto.

## 3. Cosa facciamo oggi — letto nel nostro codice

- `verimem/mcp_server.py` importa `mcp.server.stdio` e **nient'altro**: nessun trasporto
  HTTP/SSE nel modulo.
- Cercando `streamable_http|sse_server|uvicorn` nel pacchetto rispondono solo `verimem/cli.py` e
  `verimem/gateway.py`, cioè il **gateway REST** — un'altra porta del prodotto, non un trasporto
  MCP.
- Leve per accenderlo (`ENGRAM_MCP_HTTP`, `--http`, `mcp_http`): **nessuna riga**.

⇒ **La porta MCP parla solo stdio**: N client = N motori **per costruzione**, e ogni processo
paga per intero modello, giudice ed embedder.

🔎 *Nota da correggere quando qualcuno tocca quel file*: un commento in cima al server rimanda
chi vuole i log altrove «al transport HTTP» — che su quella porta **non esiste**: il riferimento
è al gateway REST.

## 4. I numeri della misura interna (11/09)

Dal resoconto della piattaforma, **letto sul canale interno, non misurato da chi scrive**:

    daemon di codifica   modello e5-base, dim 768
                         commit proprio 4,86 GB · residente 1,05 GB · store 18.147 fatti
    secondo daemon       modello MiniLM-L12, dim 384 (serve il recall proattivo)
    i due insieme        9,68 GB

Due letture che cambiano la domanda:

**① Il servizio condiviso esiste già, ed è già sdoppiato.** I due daemon *sono* la «strada
ibrida» che questa pagina proponeva come opzione: sono in piedi, e sono **due**, con **due
modelli diversi** — uno allineato allo store, uno no.

**② Il numero che satura non è la RAM: è il commit, e su quel processo vale ~4,6 volte il
residente** (4,86 contro 1,05 GB). È la spiegazione del paradosso osservato: memoria impegnata
quasi all'88-96 % **con diversi GB di RAM apparentemente liberi**. Chi guarda la RAM vede
spazio, chi guarda il commit vede il muro, e a cadere è la macchina.
⚠️ Il rapporto è misurato su **un** processo: che valga anche per i server MCP è un'**ipotesi**,
non un fatto.

📌 **NON VERIFICATO da chi scrive**: la ripartizione per singolo server MCP (quanto è modello,
quanto contesto dell'acceleratore, quanto altro) e i numeri sull'uso della GPU. Sono la misura
che decide fra le alternative del §7, e vanno presi dal loro post con l'output, non di seconda
mano.

## 5. Come fanno gli altri — quattro fonti, con l'URL

**Letta** (<https://docs.letta.com/guides/selfhosting>): un server, **più agenti**, una porta,
stato in PostgreSQL con pgvector. Come isoli i dati **fra** agenti quella pagina non lo dice; e
avvisa che l'immagine Docker «is no longer an actively maintained or supported product surface».

**mem0** (<https://docs.mem0.ai/open-source/overview>): due modalità, che sono le nostre due
strade — **libreria in-process** oppure **server self-hosted**, «A Docker stack with a dashboard,
**per-user API keys**, and a **request audit log**».

**Zep** (<https://help.getzep.com/concepts>): modello **per utente** — «Each user has a user
graph and thread history».

**A2A** (<https://a2a-protocol.org/latest/>): standard aperto donato alla Linux Foundation,
**complementare** a MCP e non alternativo — MCP «standardizes how an agent connects to its
**tools**», A2A serve agli agenti per «**discover each other**, delegate tasks, and share
results». La pagina elenca **sei SDK e nessun client reale** che lo parli: per il nostro problema
(client che condividono un motore) **non c'entra**.

## 6. Il confronto che serviva: un progetto che fa esattamente la scelta opposta

Letto **nel codice**, non nel README (`TencentCloud/TencentDB-Agent-Memory`, ramo `main`, 12/09).

**Il bordo.** `src/gateway/server.ts` espone sette rotte: `GET /health`, `POST /recall`,
`POST /capture`, `POST /search/memories`, `POST /search/conversations`, `POST /session/end`,
`POST /seed`. **La parola `mcp` non compare nel file**: il loro modello è che l'agente punti la
propria *base URL* al proxy. Un'estensione MCP esiste come **issue aperta** (#833), non come
codice.

**L'identità.** Il campo che identifica chi chiama è **`session_key`** (più un `session_id`
opzionale). **Non c'è tenant, non c'è user, non c'è agent id**: l'unità di isolamento è **la
conversazione**.

**L'autenticazione.** `Authorization: Bearer <apiKey>` con confronto a tempo costante. Ma **se la
chiave non è configurata, l'autenticazione è disabilitata** — comportamento legacy dichiarato nel
file. Un servizio condiviso «aperto se non lo configuri» è precisamente ciò che la specifica MCP
chiede di non fare.

**La scrittura.** `/capture` verifica **solo la presenza** dei campi e passa al core;
`handleTurnCommitted` registra **compiti in background** (fire-and-forget) e le memorie derivate
le producono runner a più livelli. **Nel bordo e nel core non risulta un controllo di
verità/qualità/deduplica prima della scrittura**; se esiste sta in un modulo di auto-capture
**non letto: NON VERIFICATO**.

🔑 **La differenza che decide, e non è il trasporto**: loro **scrivono subito e distillano dopo**;
noi **giudichiamo prima e scriviamo dopo**. Se un giorno mettessimo un proxy davanti a più
client, **il giudizio deve restare davanti alla scrittura**: spostarlo in un compito di
background significherebbe comprare la loro architettura e vendere la nostra promessa.

## 7. Bozza della decisione

**La domanda da decidere**: *come serviamo più client senza moltiplicare il motore, senza
spostare il giudizio dalla scrittura, e senza aggiungere un guasto che oggi non esiste?*

| | alternativa | cosa cambia per chi usa il prodotto | rischi, detti prima | quando è la scelta giusta |
|---|---|---|---|---|
| **A** | **Alleggerire il processo**: caricare modello/giudice/embedder solo quando servono; non inizializzare l'acceleratore in un processo che non lo usa | niente di visibile, se non che la macchina regge | non tocca la **moltiplicazione**: N client restano N processi. Se il peso è il modello, si moltiplica lo stesso | se la misura per server dice che il peso **non** è il modello |
| **B** | **Un server condiviso** (Streamable HTTP su `127.0.0.1`, sessioni del protocollo) | un motore solo, un modello caricato, una sola coda verso lo store | **① punto unico di guasto**: cade il server, cadono tutti i client · **② coda**: richieste serializzate dove oggi sono parallele, e il giudizio è lento · **③ un salto in più**: rete locale invece di pipe · **④ le tre garanzie** (`Origin`, bind locale, auth) diventano codice **nostro** da scrivere e provare · **⑤ chi lo avvia, lo riavvia e ne dichiara la versione?** | se il peso è il modello **e** accettiamo di scrivere e presidiare le garanzie |
| **C** | **Ibrido**: i client restano su stdio, il lavoro pesante in un servizio condiviso | come B sul consumo, senza cambiare come i client si connettono | **è ciò che già facciamo, ed è già rotto due volte**: un servizio condiviso rinato con un modello diverso da quello dello store; scritture entrate senza vettore. Il difetto non è il modello: è che **il servizio non dichiara al client la propria versione** | se prima chiudiamo il difetto di dichiarazione — allora C è la strada più corta |

**Le tre condizioni che metterei prima di qualunque «sì»**, in ordine:

1. **La misura per server** (quanto è modello, quanto contesto dell'acceleratore, quanto altro).
   Senza, si sceglie a occhio.
2. **Quanti client servono davvero insieme.** Se i client pesanti sono tre e non dodici, la
   domanda non è «condividere il motore» ma «chi lascia aperti i client».
3. **Il presidio della versione**: qualunque servizio condiviso deve **dichiarare al client**
   modello e dimensione, e il client deve **rifiutare** ciò che non combacia. Vale per la strada
   C che abbiamo già, prima ancora che per la B.

**Quello che questa pagina non decide, e non deve**: quale strada prendere. Porta il quadro, i
numeri con la loro fonte, e i rischi scritti prima — la scelta è di chi guida il prodotto.

---

*Ogni affermazione ha accanto la sua fonte: un URL, una riga di codice, o il marchio **NON
VERIFICATO**.*
