# La gravità dei difetti — la scala e i casi noti

**Iris · Product Owner · 2026-09-04 20:30.** Serve a `ws2`/`ws5`/`ws1` per il
pezzo 2 del disegno esploso (i tre percorsi d'uso, entro il 05/09 18:00): loro
eseguono e cronometrano, **la gravità la do io**.

---

## ⬛ STATO AL 05/09 21:15 — la tabella sola, quella che vale

*Il resto del documento è la cronaca di come ci siamo arrivati, con gli
argomenti e i ritiri. **Se leggi una riga sola, leggi questa tabella.** È in
cima per la stessa ragione per cui esiste la scheda prodotto: ieri due difetti
da utente erano già scritti nel README, alla riga 397 di 812.*

| # | difetto | livello | rompe | stato |
|---|---|---|---|---|
| **T1** | **la porta MCP dà la stessa spiegazione della CLI — 903 s dopo, quando chi aspettava se n'è già andato** | **P0** | U-A, U-C | **cura APPROVATA nel merito** (Tara: scaldare le librerie del giudice all'avvio, **17,3 s** contro «non torna») — 🔁 **06/09 10:30: le tre cure SONO in main** (`31d4d57f` il tokenizzatore fuori dal lock, `2e13a5b5` il preload scalda le librerie, `0363a813` l'avvio dichiara costo e leva — verificati con `merge-base --is-ancestor`; la riga «non ancora in main» era **obsoleta**). ⚠️ **Il livello NON cambia lo stesso, e per una ragione diversa**: nessuno ha **rimisurato dal lato utente** quanto aspetta oggi la prima scrittura con fonte sulla porta MCP. Cura in main ≠ difetto chiuso. **La misura che lo chiude**: un primo `remember --source` da MCP su installazione fresca, cronometrato |
| **D-1** | una self-claim **preceduta da una frase vera** passa il cancello | **P0** | la promessa centrale | aperto |
| **D-6** | **entrambe** le porte MCP accettano `as_of` e lo ignorano senza dirlo | **P0** | U-A, U-B | **cura IN MAIN** (`db7dfd11` + presidio `79625479`) — **da riverificare, non da riscrivere** |
| **T10** | la promozione documento→fatto non ascoltava il gate come il gate | **P0 sul codice, ma il ticket ha un problema PRIMA del merito** | U-B | vedi sotto |
| **T14** | il gate **decide** che i due fatti coesistono (`L3-coexistence`: scambia il **valore che cambia** per un soggetto diverso) — su **MCP il verdetto non arriva affatto**, e **in lettura il terzo riceve 2 fornitori diversi per lo stesso servizio** (*la porta è corretta: senza la relazione quelli sono due fatti distinti*) | **P0 su MCP · P1 su SDK** | U-B, U-A | causa trovata da Aldo; due difetti in fila · 🔁 **06/09 09:05: la cura ESISTE e NON è in main** — ramo di @ws6 Aldo `6bd8c6ae` (`_entita_diverse` + `subject_of`, `canonical_source_of` nell'ordine penna→firma→`"user"`), **riletta dal lead**: regge, con **una riga da restringere** (`due_fonti_dichiarate_e_diverse` oggi lascia passare il caso «uno anonimo, l'altro con penna dichiarata»; per la 0.7.7 la coesistenza vale **solo fra due anonimi**, il caso misto va a `xfail` strict per la 0.7.8). **Il livello NON cambia finché non entra**: una cura su un ramo non toglie nulla a chi installa · ✅🔴 **13:30 — È ENTRATA, e cura la PRIMA metà soltanto** (`b979bc4c`, `9827aed4`, `d7cd08c4`, `6bd8c6ae` verificati con `merge-base` su `0939b5b0`): il **criterio** non scambia più il valore che cambia per un soggetto diverso. ⚠️ **Ma il P0 era la SECONDA metà** — *«su MCP il verdetto non arriva affatto»* — che è il **pezzo 3c del muro 1, REVERTATO stamattina** insieme a 3a. ⇒ **P1 sull'SDK: curato. P0 su MCP: aperto.** *Stessa struttura di T16, e stessa disciplina: non si declassa perché «la cura è entrata», si guarda **quale metà** cura* |
| **T16** | il **percorso esplicito lo riceve solo l'SDK** — la CLI non ha `--db` su nessun comando che legge — e risponde `no facts found` **con `exit 0`**: è la riga che il nostro Quickstart insegna | ✅ **CURATO, ENTRAMBE LE METÀ** *(tre riscritture in tre ore: «curato» alle 10:10 era **troppo generoso**, «a metà» alle 13:05 era **giusto per venti minuti**, e alle 13:15 la seconda metà è entrata davvero)* | U-C, U-A | effetto misurato da me il 06/09 · causa corretta da Aldo · 🟢 **06/09 10:10, letto su `1f2eb47f`**: `--db` è ora su **`remember`, `recall`, `search`, `get`, `list`** (`cli.py` righe 1311, 1561, 3143, 3247, 3312, 3407), non più solo su `console` e `stats`. **Ho riscritto la mia riga del README**, che diceva il contrario ed era pubblicata da un'ora. ⚠️ **Verificato leggendo, non eseguendo**: la prova dal lato utente (due cartelle, scrivo con l'SDK e rileggo dalla CLI) resta da fare, e finché non la faccio scrivo «curato» e non «chiuso». 📌 *Stavo per aggiungere in vetrina che «la risposta nomina lo store aperto», preso dal messaggio di commit: **non è vero per `recall`** — quel `store:` lo stampa il comando `console` (`cli.py:1048`), e nessun test di @ws2 lo asserisce. Tolto.* · 🔴 **13:05, la CI conferma e il livello NON scende**: il run `34021131704` su `d14f0ece` è **FAILURE su tre piattaforme** con `test_la_porta_dice_quale_store_ha_aperto` → *«la risposta non dice quale store ha aperto: chi ha sbagliato cartella non ha modo di accorgersene, ed è esattamente il P0»*. ⇒ **la metà entrata cura chi SA di avere due store; il P0 era l'altra metà** — chi ha seguito il Quickstart e non sa di averne due continua a leggere `no facts found` con `exit 0`. **T16 non si chiude.** *(La mia riga delle 10:10 diceva «curato»: era troppo generosa, e me ne accorgo solo perché il test di @ws2 asserisce la promessa che io avevo tolto dal README.)* · ✅ **13:15 — LA SECONDA METÀ È ENTRATA** (main `ab2f45c5`): `_dichiara_store()` in `cli.py:1265`, chiamata **due volte dentro `recall`** (righe 1618 e 1679, la seconda con `motivo="cercato in:"` quando non trova nulla). ⇒ **chi non sa di avere due store adesso legge il percorso**, e il `no facts found` con `exit 0` smette di essere un mistero. **Ho rimesso nel README la promessa che avevo tolto** — questa volta **verificata leggendo i chiamanti**, non presa da un messaggio di commit, e ristretta a ciò che il codice fa davvero: **`recall`**, non tutte le porte. ⏳ **Resta la prova da utente** (due cartelle: scrivo con l'SDK, rileggo dalla CLI): finché non la faccio, «curato», non «chiuso» · 📖 **Letto il testo che l'utente vedrà** (`cli.py:1288-1304`): `cercato in: C:\…\semantic.db — 0 fatti`, con **una sola etichetta** (`motivo` sostituisce `store:`, non lo precede) e **`soft_wrap=True`** perché il percorso non vada a capo dentro il nome del file — *«un percorso spezzato a metà non si copia e non si incolla»*, e il difetto era uscito in CI mentre l'utente col terminale stretto lo pagava in silenzio. **È scritto bene, e il conteggio dei fatti è la parte che chiude il ragionamento.** 📌 **L'unica cosa che manca, e la lascio come osservazione non come ticket**: la riga dice **dove** ha cercato, non **cosa fare** — chi non conosce `--db` capisce di guardare nel posto sbagliato ma non che può indicarne un altro. È il terzo passo classico (*il prodotto dice il problema, non la via d'uscita*), e vale meno delle due metà appena entrate |
| **T6** | le chiamate rifiutate per validazione **non entrano** in `mcp_audit.log` — 3 chiamate, 2 righe, e il campo `error` resta `""` | **P1** | U-B | **verificato da me il 06/09** |
| **T19** | 🔴 **quando l'encode non è disponibile il fatto entra SENZA embedding, la ricevuta dice `admitted` (grounding 99,97), e poi la ricerca risponde «probabilmente la risposta NON è in memoria» — su un fatto CHE C'È**: un'assenza fabbricata, esattamente la risposta che questo prodotto esiste per rendere affidabile | **P0** | U-A, U-B, U-C | picco **26 fatti** in 35 minuti, di cinque di noi (@ws5 Tara) · ✅ **danno CHIUSO alle 04:59: zero muti, tutti RIPARATI** — ma **nessun presidio del prodotto lo aveva segnalato** |
| **T18** | **il ramo `as_of` SOSTITUISCE i filtri invece di comporli**: `include_superseded` ingoiato (Giano) e **scaduti esclusi senza avviso** (Aldo) sono **due sintomi di una radice sola** — chi chiede il passato riceve **meno** di quello che ha chiesto e non lo sa | **P1** | U-A, U-B | radice unificata dal lead · livello mio · owner Giano+Aldo · **la classe è delimitata**: `min_relevance` e `k` passano (misurato), a cadere sono **i filtri di stato del fatto** |
| **T23** | **il prodotto calcola le date in DUE FUSI**: `temporal_context` (il motore di `as_of`), `semantic_conflict` e un punto della porta MCP in **UTC**; otto punti rivolti all'utente (CLI, riepiloghi, export) in **fuso locale**. ⇒ a cavallo della mezzanotte **la data su cui il filtro ha deciso e la data che l'utente legge possono essere due giorni diversi**, e le date che legge sono coerenti fra loro: non ha modo di accorgersene | **P1** | U-A, U-B | reperto di @ws1 Marie, **analisi statica, zero processi** · livello mio · ⬆️ **sale a P0 se** si misura che morde sul default di `as_of` (l'unico presidio si chiama già `test_la_data_dichiarata_slittava_di_un_giorno`) · ⬇️ **è zero** per chi gira in UTC |
| **T20** | **l'avviso della porta MCP su `asserted_at` è più largo del vero**: dichiara *«THIS PORT DOES NOT SET THE EVENT TIME … accepted without error and ignored, measured 2026-08-31»*, ma il **ramo remoto** di `hippo_remember` lo passa (`mcp_server.py:7807`). Un limite dichiarato che spegne una capacità viva è peggio di un limite taciuto: chi legge **rinuncia** | **P2** `[VETRINA]` | U-B | reperto mio, **corretto da me**: la mia riga di ieri («da MCP non si può scrivere il passato») era un'assenza dedotta da **uno** strumento · owner Giano · ⬆️ **sale a P1 se** il ramo locale la perde davvero — allora il difetto è l'**asimmetria fra i due rami**, non l'avviso. **Non l'ho verificato**: il gestore locale cade in un dispatcher che non ho letto |
| **T26** *(numero mio, se è già preso ditemelo)* | 🔴🔴 **sul candidato di release `5e61d333`, alla porta MCP e in configurazione DI DEFAULT, il moat NON gira**: il modello del giudice non si importa sul thread di sfondo (`cannot import name 'AutoModelForSequenceClassification'`) e la scrittura con fonte entra **`judged=False`, `layers=['L4-skipped']`**. Con `HIPPO_PRELOAD_BACKGROUND=0` lo stesso fatto, stessa fonte, esce **`judged=True`, `grounding 98,37`** | 🔴 **P0 · BLOCCA IL TAG** | **la promessa del punto 1**, sulla porta principale | **A/B a una variabile di @ws1 Marie** (14:30), RAM letta 4,05/4,04 GB, un processo per volta, chiusi · ⚠️ **lo stesso import da solo nello stesso venv RIESCE**: non è una dipendenza rotta, è un import **concorrente** — stessa famiglia di T1b · 🔑 **perché P0 e non P1**: la frase con cui ci presentiamo è *«ogni scrittura passa un cancello»*, e **sulla porta che un agente usa, in default, non lo passa**. Il prodotto lo **dichiara** (`L4-skipped` è nella ricevuta) ma chi legge `admitted` non guarda `layers`: è la forma di **T19**, applicata alla promessa centrale. ⇒ **il livello dice che questo non si tagga**: non perché il difetto sia nuovo, ma perché **rilasciare così pubblica una promessa che il default non mantiene** · 📊 **QUANTO PESA, misurato da @ws6 Aldo sul corpus vero**: `13/275` fatti nelle **ultime 24 h** sono entrati così — **4,7%**, contro `66/8833` nello storico (**0,7%**): **sette volte tanto**. ⇒ *non è un caso di laboratorio: è quasi una scrittura su venti, adesso.* · ✅ **14:38 — IL TAG SI È FERMATO**: decisione del lead, che cita il livello come mio e la misura come di @ws1; @ws5 ha confermato la causa **ritirando la propria spiegazione delle 13:08**; T26 entra nel CHANGELOG in *«Not solved yet»* con la frase *«this release is not tagged until the fix is in and measured on the MCP port»*. 🔑 **La regola che ha deciso è di Aurelio**: *«ci apriamo al mondo solo quando tutto funziona davvero»* |
| **T22** | il costo in memoria di **una sessione** del server MCP (il lead lo registra come **1,15 GB di commit**, @ws5) | ⛔ **LIVELLO NON DATO** | U-B | ⚠️ **Non lo do perché non ho la misura, e scrivo dove ho guardato invece di richiederla una terza volta.** La **fonte esiste**: `docs/stato-reale/banchi/ws5-chi-importa-torch-nel-client.py`, che misura **chi** importa `torch` e **a quale passo**, con la predizione depositata *prima* di eseguire (`import verimem` → no torch; `import verimem.mcp_server` → sì). **L'esito non risulta né sul canale né nel repo.** 🔑 **Perché mi interessa da PO**: se `mcp_server` tira dentro `torch`, il «client leggero» non esiste e **il costo si moltiplica per il numero di agenti** — cioè colpisce **U-B, «un team su uno store»**, che è un nostro percorso dichiarato. ⇒ **appena c'è l'esito do il livello**; il numero `1,15 GB` **non l'ho verificato io** |
| **T15** | l'audit dice **cosa** ma non **chi**: c'è `caller_pid`, non un'identità | **P1** | U-B | misurato dalla porta MCP |
| **T9** | **gli scaduti muti**: `facts_recall` e `ask` non dichiarano ciò che la scadenza ha tolto, mentre SDK e CLI sì | **P1** | U-A, U-B | cura in disegno (Aldo+Giano, finestra ③) |
| **T13** | il **SIGSEGV** di `test_hang_watchdog`: 3 run su 10, e `exit 139` non compare nell'API | **P1** `[PROVA]` | nessun percorso — **la prova che diamo** | owner Corrado (CI) |
| **T2a** | 248 strumenti su 249 si chiamano `hippo_`, `serverInfo` dice `verimem` | **P2** `[VETRINA]` | U-C, U-A | aperto |
| **T2b** | 249 strumenti = **38.675 token** per sessione, e **102 non sono mai stati chiamati**: 37 coprono il 90% degli usi | **P2** `[VETRINA]` | U-A | design dei profili pronto (Nadia); cura facile |
| **T4** | le chiavi dell'output sono in italiano | **P2** · debito che cresce | U-A | aperto |
| **D-7** | la CLI non stampa gli id dei fatti | **P2** | U-A | aperto |
| **T11** | la distinzione «verificato / mai verificato» sopravvive nel record in **due campi nulli** — 1.743 fatti su 11.719 | **P2** `[VETRINA]` | U-B | misurato oggi, dichiarato nelle istruzioni MCP |
| **T12** | le porte gemelle divergono su **tre livelli**: il massimo (50/100), il **nome del parametro** (`k`/`limit`) e il **nome del campo** (`text`/`proposition`) | **P3** | U-A | famiglia di T4 e D-7 |
| **T17** | 🔑 **`L4.2` cerca l'unità SOLO A DESTRA del numero, in ENTRAMBI i testi** — e sbaglia ogni volta che sta a sinistra in uno dei due: `EXIT=2`, `STRUMENTI…: 249`, `03:27` (l'unità è la posizione), *«…quello con i dati 28/100»*. ⇒ ~~avvisa falsamente su **quasi ogni output di programma**~~ 🔁 **CLASSE RISTRETTA dallo stesso @ws2 alle 09:50, venti minuti dopo il reperto**: due suoi fatti con **esattamente** quella forma (`PRIMA_SCRITTURA_CON_FONTE_S=20.6`, `grounding_score=99.68628692626953`) sono **passati** ⇒ **non è «ogni etichetta-valore», e quale sia la classe vera NON è ancora noto** — il livello regge sull'A/B, l'ampiezza no | ⬆️ **P1** *(era `P2 [PROVA]`, **falsificato** il 06/09 09:40)* | U-A, U-B | 5 prove mie + 3 di @ws4 Nadia · 🔴 **@ws2 Giano ha misurato che BLOCCA**, con un A/B a **una variabile sola** (stessa source, cambia solo la forma del numero): «le righe risultano **1**» → `grounding 98.9472`, `layers ['L4.1','L4.2']`, **QUARANTINED**; «le righe risultano **una**» → `grounding 96.9620`, `layers []`, **ammesso**. ⇒ **il fatto trattenuto è sostenuto PIÙ di quello ammesso**, e la mia riga «non blocca un percorso, degrada il presidio» era **sbagliata**. ⚠️ **Aggravante**: la nostra `O3` impone di passare come source l'**output grezzo**, cioè proprio la forma `etichetta valore` su cui il layer inciampa — il difetto colpisce il modo d'uso che prescriviamo. ⬆️ **sale a P0 se** si misura che un fatto trattenuto così fa rispondere alla ricerca un'assenza **senza dichiarare la quarantena** (allora è T19); **resta P1** finché la ricevuta porta `quarantined_by`, che @ws2 legge a ogni salvataggio — **ma è una pratica sua, non un presidio del prodotto** |
| **T3** | note interne nelle descrizioni (202 strumenti su 249) | **P3** `[VETRINA]` | nessuno | si cura con T2b |
| **T5** | l'errore non dice cosa **accetta** | **P3** | U-A | aperto |
| **T8-bis** | 🔑 **l'avviso di `doctor` sulla copertura del giudice non si spegne MAI**: la condizione è `giudicati/totali < 0.5` (`doctor.py:724`) su una grandezza **cumulativa**, e i fatti scritti prima che il giudice fosse pronto restano non giudicati **per sempre**. Chi installa e fa le prime prove si porta dietro un `!` permanente su un comando che il README prescrive **due volte** — e impara a ignorarlo | **P1** | U-C, U-A | ⚠️ **NON curato** (`doctor.py` **invariato** fra `v0.7.6` e main) · 🔁 **formulazione RIFATTA il 06/09 su lettura del codice di @ws8 Corrado**: la mia diceva *«l'exit code non discrimina»* ed **era falsa** — `cli.py:721` dichiara `0/1/2` ed è un contratto pubblico. Avevo letto la causa dal **testo** dell'avviso (*warming*) invece che dalla **condizione**: stessa forma di T17 |
| **T7** | 1160 MB di venv | **P4 · DICHIARATO** | nessuno | numero da rinfrescare |
| ~~T8~~ | ~~`doctor` esce 1 su un'installazione che funziona~~ | **RITIRATO** | — | **non è un difetto** |

**SEI P0, e non è inflazione: sono tutti la stessa forma.** *Il prodotto
serve come vero — o tace — qualcosa che chi legge non ha modo di controllare.*
🔴 **E il sesto, T19, è il più puro: non tace, AFFERMA** — dice «probabilmente la
risposta non è in memoria» su un fatto che c'è.
D-1 ammette una self-claim; D-6 dà il presente a chi chiede il passato; T14
decide che due fatti in conflitto coesistono e su MCP non lo dice; T16 risponde
`no facts found` con `exit 0` da uno store che non è quello in cui abbiamo
scritto; T1 fa aspettare quindici minuti e può finire `judged=False`. *(T10 resta
fuori dal conteggio: sospeso, e per una ragione che precede il merito.)*
**Se un giorno questi cinque sono chiusi, il prodotto mantiene la frase con cui
si presenta. Finché sono aperti, no.**

---

## T1 — il titolo, alla terza riscrittura

> **«La porta MCP dà la stessa spiegazione della CLI — 903 secondi dopo, quando
> chi aspettava se n'è già andato.»**

> 🔁 **CORREZIONE 21:25, e la correzione è più istruttiva del titolo.** Alle
> 21:08 avevo scritto *«la porta MCP TACE dove la CLI parla»*. **Falso**, e
> l'ha misurato Tara **su main e sulla 0.7.6 di PyPI**, con il giudice messo
> nella condizione vera del campo (`judge_state() == "warming"`): la risposta
> MCP contiene **la stessa identica frase della CLI, parola per parola**, più un
> campo `moat` che la dice in breve e `"confidence_tier": "unverified"`.
> ⇒ **La porta MCP non tace: arriva tardi.** E la differenza non è di sfumatura,
> cambia la cura — Tara ha giustamente rifiutato di implementare «una ricevuta
> immediata», che avrebbe aggiunto **un secondo canale per un testo che il primo
> consegna già**.
>
> ⚠️ **E l'errore è mio, non di chi me l'ha passato.** Il CTO mi ha chiesto di
> riscrivere T1 «come lo dice Corrado», e l'ho fatto: ma quella di Corrado era
> **un'osservazione**, non una misura in condizione controllata. **Ho promosso
> l'osservazione di uno a titolo ufficiale senza aspettare il controllo
> dell'altro** — e il controllo è arrivato diciassette minuti dopo. La regola che
> mi ero data ieri («ogni livello porta il **regime** di chi ha misurato») vale
> anche per i **titoli**, non solo per i livelli.

Il vecchio titolo («la prima scrittura con fonte via MCP ci mette 313 s») era
**sbagliato in tre modi**, e i tre me li hanno corretti gli altri:

1. **Non è 313 s.** Sono **fino a 903** (Corrado, due giri). Il 313 era la mia
   prima lettura, e prima ancora c'era un 303: **erano finestre di chi guardava,
   non durate del fenomeno.** Nadia ha aggiunto il pezzo che chiude la questione:
   *«il 300 nel nostro codice non c'è»* — 58 occorrenze su 391 file, **nessuna è
   un'attesa**. Il numero veniva dal client, non dal prodotto.
2. **Non è «ci mette tanto» in astratto: è che la spiegazione arriva DOPO che
   chi doveva leggerla ha smesso di aspettare.** La CLI, davanti alla stessa
   identica situazione, risponde in **1,2 s** con la spiegazione; la porta MCP
   dà **la stessa frase**, ma dopo 313-903 s — e il client di Corrado aveva
   smesso di ascoltare a **300**. ⇒ Il prodotto **produce** l'onestà che
   promette e **non riesce a consegnarla**.
   *(Qui avevo scritto «una porta tace»: falso, vedi la correzione sopra.)*
3. **La causa non è quella che avevo scritto io.** Avevo lasciato aperte due
   letture (la cura non ha protetto / è il download). **Erano tutte e due
   sbagliate**: è l'import di `scipy`/`torch` eseguito nel thread della
   richiesta, e il braccio A' di Tara — lo stesso import fatto nel **main**
   all'avvio del server — torna in **28-33 s**.

🔑 **La lezione di prodotto, che tengo per la scheda**: il numero che avevo in
mano («313 s») descriveva **il mio strumento di misura**, non il prodotto. Tre
persone hanno dovuto correggermi perché io avevo un numero e loro avevano il
fenomeno. **Un numero senza la finestra in cui è stato preso non è una misura**
— ed è la stessa regola che il CTO ha messo fra quelle di oggi.

**Perché resta P0** anche adesso che ha una causa e una cura: non per l'attesa,
ma perché **al fondo dell'attesa il fatto può entrare `judged=False`**. La
lentezza è il sintomo, il giudizio saltato è il danno.

E la misura di Tara lo rende **più** netto, non meno. Il prodotto scrive
`"confidence_tier": "unverified"`, dichiara `L4-skipped`, spiega che il giudice
sta caricando e che *«this is NOT a pass»*: **è tutto quello che gli chiediamo di
fare.** Poi lo consegna a un destinatario che se n'è andato 600 secondi prima, e
il fatto resta scritto. ⇒ **Un prodotto onesto che non riesce a farsi sentire
produce lo stesso esito di uno che tace** — e per l'utente i due casi sono
indistinguibili. È questo che tiene T1 a P0.

## T9 · **P1** — gli scaduti muti

`facts_recall` e `ask` **non dichiarano i fatti che la scadenza ha tolto**;
`SDK` e `CLI` lo fanno (è entrato su main ieri, `bb93d120`). Aldo ha la causa,
ed è **la stessa giuntura di D-6**: le porte MCP chiamano `a.semantic`
direttamente e **scavalcano `Memory.search`**, dove il prodotto costruisce i
`Risultati`. Tre misure indipendenti concordano, e il codice stesso dichiara di
essere **alla quarta generazione della stessa cura**.

**P1 e non P0, e l'argomento è preciso**: qui il prodotto **non serve un falso**
— tace un contesto. Un agente riceve meno risultati e non sa perché.
**Cosa lo alza a P0**: se qualcuno misura che l'assenza silenziosa porta un
agente a **scrivere una conclusione sbagliata** — cioè a trattare «non lo so
più» come «non è mai stato vero» — allora il prodotto sta producendo un errore,
non nascondendo un contesto, e sale. *La misura è a portata: due domande allo
stesso store, una prima e una dopo la scadenza.*

⚠️ **E una nota che vale più del livello**: T9 e D-6 **non sono due difetti,
sono due sintomi di una giuntura**. La cura che li chiude entrambi vale il doppio
di due cure separate — e Aldo lo ha già detto meglio di me: *«il presidio che
impedisce al prossimo campo di uscire da una porta sola vale più della mia
cura»*.

## T10 · promozione documento→fatto (`a499afc8`) — **il livello viene dopo**

Il commit fa sì che la promozione **ascolti `L4.1` come il gate**, non conti gli
avvisi `*-observe` e scriva `quarantined_by`. I numeri che porta con sé:
`25/40 → 12/40`, `12/40 → 5/40`, `8/40 → 5/40`, `56/56 → 0/72` su
`quarantined_by`.

**Il difetto che cura sarebbe P0**: un documento indicizzato poteva diventare un
fatto servito **senza il criterio che vale per le scritture dirette** — cioè una
seconda porta d'ingresso che non passa dal cancello. È la forma di D-1 spostata
di un piano.

🔴 **Ma questo ticket ha un problema prima del merito, e da Product Owner lo
dico chiaro: il codice non ha un autore.** Lo START lo attribuiva a Nadia; lei
ha guardato e ha risposto con l'output — firma `Claude Fable 5.1`, tocca
`document_promote.py`, mentre il suo ramo di ieri conteneva solo `docs/`. E lo
**stesso SHA è stato attribuito due volte, a due lavori diversi**, e nessuno dei
due è quello che il commit contiene.

**La mia posizione**: *un ticket il cui codice non ha un autore identificato non
entra in main perché i numeri sono buoni.* Non perché il codice sia sospetto —
i numeri li ho letti e sono forti — ma perché **su una cura del cancello il
razionale delle scelte È il contenuto**: quali avvisi si ascoltano e quali no è
una decisione di prodotto, e deve poterla difendere qualcuno. Nadia ha detto la
cosa giusta: *«porto la falsificazione, ma non sono l'autrice; il razionale non
ce l'ho»*.
⇒ **Serve che qualcuno la firmi**: chi l'ha scritta la rivendica e risponde, **o**
chi la porta avanti la **riadotta esplicitamente** dichiarando di aver rifatto le
scelte per conto proprio. Fino ad allora il livello resta **sospeso**, e non è
una formalità: è l'unico caso in cui un ticket non ha un numero perché non ha
una persona. *La decisione è del CTO; questa è la posizione di prodotto.*

---

## Perché la scala non parla di codice

Un difetto non è grave perché è profondo: è grave **per quello che impedisce a
qualcuno di fare**. Le stesse due righe di codice sono un dettaglio in un
percorso e un muro in un altro. Quindi ogni voce qui sotto porta **il percorso
che rompe**, e se non rompe nessun percorso lo dice.

| livello | significato operativo | cosa comporta |
|---|---|---|
| **P0 · ROMPE LA PROMESSA** | il prodotto fa la cosa che dice di impedire | non si pubblica, non si consiglia, si dice nel README finché non è curato |
| **P1 · BLOCCA UN PERCORSO** | un caso d'uso dichiarato non arriva in fondo | va curato prima di chiamare quel percorso «supportato» |
| **P2 · RALLENTA** | il percorso arriva in fondo ma a un costo che l'utente non si aspettava | va **dichiarato** subito e curato quando si può |
| **P3 · FASTIDIO** | l'utente inciampa, capisce, prosegue | ticket, nessuna urgenza |
| **P4 · DICHIARATO** | è una trappola, ma il prodotto la scrive | non è un difetto: è debito di documentazione se la scritta è nel posto sbagliato |

⚠️ **Un livello non si alza per far notare una cosa.** Se tutto è P0, la scala
non serve più a decidere — e questo progetto ha già pagato una volta il prezzo
di un numero che voleva dire troppe cose.

---

## I tre percorsi (nomi di lead-audit, 04/09)

- **U-A · un agente che lavora** — scrive fatti su di sé e sul lavoro fatto, e
  poi li rilegge. È il caso per cui il prodotto esiste.
- **U-B · un team su uno store** — più scrittori, uno store condiviso, letture
  che devono restare fedeli.
- **U-C · da zero in dieci minuti** — installo, provo, capisco se fa per me.

---

## I difetti noti, con la gravità

### D-1 · **P0** — la self-claim passa se preceduta da una frase vera
`LANT-175` · trovato da utente sul pacchetto pubblicato `0.7.6`

«La funzionalità è verificata.» **da sola è fermata**; la stessa frase
**preceduta da un fatto vero passa**. Misurato su **sette forme** (una frase,
due, una subordinata, un soggetto non umano, tre parole, e le stesse due in
**inglese**) e su **tutte e tre le porte** (CLI, API, MCP).

**Perché P0 e non P1**: la promessa scritta nel `--help` del prodotto è
*«abstention instead of hallucination»*, e il caso che passa è **esattamente**
la confabulazione che il gate esiste per fermare — un agente che scrive «ho
fatto X, e il collaudo è a posto». Non rompe un percorso: **rompe la frase con
cui il prodotto si presenta.**

**Rompe**: U-A in pieno, U-B (il fatto entra nello store di tutti).
**Non rompe**: U-C — chi prova dieci minuti non se ne accorge, ed è la parte
che preoccupa di più.

⚠️ **Il rilevatore funziona**: `L1.15` si accende **anche nei casi che passano**.
Cede l'escalation, per una decisione presa sul **soggetto** invece che
sull'**affermazione**. La carve-out che la causa è nata per una ragione buona e
misurata (i fatti di terzi veri: sei su sette fermati il 28/08): **il difetto
non è che esista, è che si applichi a tutta la frase invece che alla
proposizione che l'ha meritata.**

### D-2 · **P1 su U-C, P2 su U-A** — la scrittura rallenta dentro la sessione
`LANT-175` · misurato da utente, store vuoto

Otto `remember` di fila: **3 · 4 · 4 · 23 · 28 · 32 · 38 · 40 secondi**.
L'ottava costa **più di dieci volte** la prima, con otto fatti in tutto.

**Perché P1 su U-C**: «da zero in dieci minuti» con 40 s a scrittura significa
**una quindicina di fatti**, e l'utente passa il tempo ad aspettare invece che a
capire. Il percorso non arriva dove promette.
**Perché solo P2 su U-A**: un agente che scrive in background tollera 40 s.

⚠️ **Causa non stabilita, e non la invento.** Un dato che non so spiegare: una
scrittura in **0,1 s** in mezzo a vicine da 25 s.

### D-3 · **P3** — `doctor` e `warmup` danno due cifre per lo stesso download
`LANT-175` · `doctor.py` righe 777 e 785 dicono `~656 MB`, `warmup --help`
**eseguito** stampa `~746 MB`

**Perché P3 e non P2**: l'utente scarica comunque la cosa giusta; il numero
sbagliato lo confonde e basta. **Ma è nel comando che si esegue per capire cosa
manca**, quindi non è indifferente.

🔑 **La cura c'è già a metà**: `cli.py:413` porta il commento *«L'help dichiarava
"~656 MB" cablato nel testo: 90 MB in meno del vero»*. Curato lì, **non**
propagato a `doctor.py`.
⚠️ **Livello: il testo è nel pacchetto (letto sul file installato), ma non l'ho
fatto emettere** — due tentativi per accendere quel ramo sono falliti.

### D-4 · **P4 · dichiarato** — la ricevuta MCP dice `"ok": true` su un fatto quarantinato
Le istruzioni del server MCP dicono, a lettere chiare: *«do not read `ok` as
"the fact was accepted"»*. ⇒ **Non è un difetto nascosto: è una trappola
scritta.** Resta la domanda di prodotto — *un campo che chiede di non essere
letto per quello che sembra è il campo giusto?* — ma è materia di design, non un
ticket.

### D-5 · **da misurare** — la porta MCP espone **249 strumenti**
Osservato, non giudicato: non so quanto costi a un client caricarli tutti né se
qualcuno li filtri. **Non gli do una gravità finché non c'è la misura** — la
matrice dei permessi è di `ws4`, e la misura del costo è di chi tiene le porte.

---

## Cosa chiedo a chi esegue i tre percorsi (ws2, ws5, ws1)

1. **Portate il difetto, non la diagnosi.** Scrivete cosa avete provato a fare e
   dove vi siete fermati. La causa la cerca chi tiene quel pezzo.
2. **Cronometrate.** Un percorso «funziona» in dieci minuti o in due ore sono due
   prodotti diversi.
3. **Segnate anche ciò che ha funzionato.** Un elenco di soli difetti non dice se
   il prodotto è usabile: dice solo dov'è rotto.
4. **Non alzate la gravità per farvi notare.** Portatemi il fatto; il livello lo
   metto io e lo difendo.

---

# I ticket dell'agenzia T1-T8 — la gravità

**Iris · 2026-09-04 21:0x.** Assegnati su mandato del CTO (`7d9270c86ab16b56`),
sui sette reperti da utente di Corrado più il `doctor` di Tara. Owner delle cure
e revisori sono già assegnati: qui c'è **solo il livello e cosa lo cambierebbe**.

## Due regole nuove, dichiarate prima dei livelli

**① `[VETRINA]` — una dimensione, non un livello.** Tre di questi difetti non
bloccano niente e sono lo stesso importanti: sono ciò che l'utente **legge** su
di noi. La tentazione era aggiungere un livello «P2,5 · fa brutta figura»; non
l'ho fatto, perché una scala che cresce ogni volta che serve enfasi smette di
ordinare. La gravità dice **cosa blocca**; il marcatore `[VETRINA]` dice **cosa
comunica**. Sono ortogonali: un difetto può essere P3 e `[VETRINA]`, e in quel
caso si cura presto benché sia P3, perché costa poco e si vede molto.

**② Ogni livello porta LA MISURA CHE LO CAMBIEREBBE.** Un livello senza questo è
un'opinione che nessuno può falsificare. Dove la misura non c'è ancora, il campo
dice quale sarebbe — così chi la fa sa che il livello si muove.

## I livelli — ⚠️ **TABELLA STORICA DEL 04/09, NON LO STATO**

> 🔴 **Questa tabella è la fotografia del 04/09 e contiene livelli SUPERATI**:
> qui T1 è ancora P1 (oggi è **P0**) e T8 è ancora un difetto (oggi è
> **RITIRATO**). Serve a leggere *come* ci siamo arrivati, insieme agli
> argomenti e ai ritiri che la seguono. **Lo stato di adesso è la tabella in
> cima al documento, e solo quella.**
>
> *Non l'ho cancellata perché la cronaca degli errori vale quanto i livelli;
> l'ho marcata perché due tabelle senza un'etichetta sono la classe ① —
> una copia invece della superficie unica — dentro il mio stesso documento.
> Me ne sono accorta il 05/09 perché uno script si è rifiutato di scrivere
> trovandone due dove ne aspettava una.*

| # | difetto | livello | percorso che rompe | chi l'ha misurato |
|---|---|---|---|---|
| **T1** | la prima scrittura **con fonte** via MCP: cinque minuti di silenzio | **P1** · primo in coda | U-C, U-A | Corrado (audit del server) |
| **T2a** | 248 strumenti su 249 si chiamano `hippo_`, `serverInfo` dice `verimem` | **P2** `[VETRINA]` | U-C, U-A | Corrado |
| **T2b** | 249 strumenti = **38.675 token** di contesto per sessione | **P2** `[VETRINA]` | U-A | **Iris, misurato stasera** |
| **T3** | note interne nelle descrizioni («FORGIA #318 — Round 35», «Cycle #137») | **P3** `[VETRINA]` · **non gratis** | nessuno | Corrado; **contate da Iris** |
| **T4** | chiavi dell'output in italiano (`"ricerca"`, `"ramo"`, `"ordinati_per"`) | **P2** · debito che cresce | U-A | Corrado — e **ricevuto da me** stasera |
| **T5** | l'errore di validazione dice cosa manca, non cosa accetta | **P3** | U-A | Corrado |
| **T6** | le chiamate rifiutate per validazione **non entrano** in `mcp_audit.log` | **P1** | U-B | Corrado (non verificato da me) |
| **T7** | 1160 MB di venv (torch 539) in 4m47s | **P4 · DICHIARATO** | nessuno | Corrado |
| **T8** | `verimem doctor` esce 1 su un'installazione che funziona | **P2** | U-C | Tara, e fatto `d598fbae5396` |

---

## T1 — perché P1 e non «MASSIMA», e perché è lo stesso il primo

Il CTO ha proposto la gravità massima. **Secondo la mia scala è P1**, e la
differenza non è un dettaglio di etichetta.

P0 è riservato a «il prodotto fa la cosa che dice di impedire»: oggi ce l'ha un
difetto solo, la self-claim che passa se preceduta da una frase vera (**D-1**).
T1 non fa entrare nessuna confabulazione — anzi, il fatto arriva **giudicato**
(`grounding_score=99.92`). Blocca un percorso, e lo blocca del tutto: è P1.

**Se alzo T1 a P0, D-1 e T1 diventano indistinguibili, e sono due cose molto
diverse**: uno si cura per non mentire, l'altro per non far aspettare. La scala
serve a questo o non serve a niente.

**E resta il primo della coda**, come il CTO ha già deciso — per una ragione che
la gravità non misura: **sta sulla prima scrittura che chiunque fa**. Gravità =
quanto è grave. Ordine = quanto è vicino alla porta d'ingresso. Sono due assi, e
T1 è il caso in cui il secondo comanda.

### Il dato che porto io, e che sposta la diagnosi

Il tag `v0.7.6` contiene già, in `verimem/local_grounding.py:743-751`, questo:

> *«The moat CE cold-load (~30s measured 2026-07-18: import + model build under
> the judge lock) **blocked the FIRST gated write of every fresh server** — same
> class as the 2026-06-05 embedding hang, new site. In delegate-only mode the
> load runs on a background thread instead; **until warm, `try_local_score`
> returns None and the caller degrades honestly** (injected llm, or the
> L4-skipped advisory admit).»*

⇒ **Il prodotto dichiara nel codice di aver curato esattamente la forma del
ticket 1**, con lo stesso nome («the FIRST gated write of every fresh server») e
con un comportamento promesso preciso: *non aspettare — degradare e tornare*.

La ricevuta di Corrado dice che non è andata così: `latency_ms=303072`,
`outcome=ok_new`, e **`judged=True grounding_score=99.92`**. Un `grounding_score`
pieno significa che la scrittura **ha atteso il giudice** invece di degradare con
l'avviso `L4-skipped`. Qualunque sia la causa dell'attesa, **il comportamento
osservato è l'opposto di quello dichiarato**, e questo è vero indipendentemente
dalla diagnosi.

⚠️ **E qui mi fermo, perché la diagnosi non è mia e ci sono due letture che i
dati che ho non separano** — dirne una sola sarebbe la forma che ho già pagato
oggi (una parola in comune non è lo stesso guasto):
- **(a)** la cura non ha protetto (p.es. `HIPPO_ENCODE_DELEGATE_ONLY` non era `1`
  in quel processo);
- **(b)** la cura ha protetto ciò che copre — il **cold-load**, ~30 s — e i 303 s
  sono il **download** dei 711 MB, che è un'altra cosa e che quel ramo non tocca.
  I due ordini di grandezza (30 s contro 303 s) rendono (b) almeno plausibile
  quanto (a).

**La misura che le separa costa una riga**, ed è per Tara e Corrado: nel processo
MCP dell'esercizio, `HIPPO_ENCODE_DELEGATE_ONLY` valeva `1`? E la cartella del
modello era vuota prima della chiamata? Con quelle due risposte il ticket ha una
causa invece di due ipotesi.

### Cosa cambia il livello

- Rifatto **senza daemon condiviso** e torna sotto i 30 s → **P2**.
- Il client va in **timeout prima** che torni (Claude Code chiude la chiamata) e
  il fatto **viene scritto lo stesso** → resta P1 ma peggiora di specie: da
  «lento» a **«esito ignoto su una scrittura andata a buon fine»**, che è la
  condizione peggiore per una memoria. *Non l'ho verificato: è la prima cosa che
  chiederei a chi rifà l'esercizio.*

---

## T2b e T3 — la misura che mancava, fatta stasera

Il 04/09 avevo lasciato i 249 strumenti **senza gravità** («D-5: osservato, non
giudicato — non gli do un livello finché non c'è la misura»). La misura ora c'è,
e la grandezza giusta non è il numero di strumenti: è **il payload che un client
MCP mette nel prompt a ogni sessione**, che l'utente lo usi o no.

```
  strumenti                      : 249
  col prefisso hippo_            : 248
  col prefisso verimem_          : 0
  PAYLOAD INTERO di tools/list   : 154,703 byte  ~38,675 token
  di cui descrizioni             : 71,219 byte
  di cui schemi di ingresso      : 66,161 byte
```

**38.675 token è il prezzo fisso di avere verimem collegato** — circa **il 19%
di una finestra da 200k**, ~155 token per strumento, prima che l'utente scriva
una riga. **P2**: il percorso arriva in fondo, a un costo che nessuno si aspetta
e che nessuno gli ha detto.

E dentro quel testo ci sono le note interne di T3, **contate e non stimate**:

```
    FORGIA       158 strumenti   es. hippo_skill_antagonists
    Round N       53 strumenti   es. hippo_fact_forget_with_undo
    Cycle N       50 strumenti   es. hippo_remember
    ⇒ strumenti con ALMENO una nota interna: 202 su 249
```

**202 su 249 = 81%**, e fra loro c'è **`hippo_remember`**, cioè lo strumento
principale del prodotto. T3 resta P3 perché non blocca nessuno, ma smette di
essere solo una brutta figura: quelle note **si pagano in token a ogni
sessione**, sono nella stessa superficie di T2b e **si curano insieme**.

⚠️ **REGIME, e va citato con il numero**: misurato sull'**albero di lavoro
locale** con `miniconda3\python.exe`, **non** sul wheel 0.7.6 di PyPI — il venv
dell'esercizio di Corrado non esiste più sul disco. Controllo di allineamento a
favore: il conteggio degli strumenti (**249**, di cui 248 `hippo_`) coincide con
quello che Corrado ha letto sulla 0.7.6. Chi cita i 38.675 token lo rifaccia sul
wheel pubblicato. Banco: `scratchpad/costo_di_contesto_dei_249.py`, da
versionare in `docs/stato-reale/banchi/`.

---

## T6 — perché un P1 su un difetto che non si vede

Un log che **omette i rifiuti** non ha un buco: ha un silenzio. Chi lo legge
conclude che è andato tutto bene, e non ha modo di accorgersi del contrario. È
la forma che abbiamo già pagato («un'assenza di misura si legge come perfetta»),
e stavolta è sul percorso U-B, dove l'audit **è** il deliverable: un team mette
verimem su uno store condiviso proprio per sapere cosa ha fatto l'agente.

⚠️ **Non verificato da me**: è il reperto di Corrado. Se qualcuno lo falsifica,
il livello cade con lui.

---

## T7 — il difetto è dove sta la scritta, non che manchi

**Il README dichiara già i costi su disco**, alla riga 397 di 812:

| step | on disk |
|---|---|
| `pip install verimem` — 74 packages, `torch` is more than half of it | **~1.0 GB** |
| first `verimem warmup` | **~2.3 GB** |
| **total, first run on a clean machine** | **~3.3 GB** |

Corrado ha misurato 1160 MB contro «~1.0 GB»: **il 16% in più**, con il regime
dichiarato (Windows, py3.13) uguale al suo. Quindi T7 è **P4 · DICHIARATO** —
non un difetto, un numero da rinfrescare.

🔑 **E questo è il reperto di prodotto della serata, più dei singoli ticket**:
**due dei sette «difetti da utente» erano già scritti nel README**, alla riga
giusta per chi lo legge tutto. Nessuno lo legge tutto. Il difetto non è che la
verità manchi: è che **stia alla riga 397 su 812**.

Questo decide che cos'è la scheda prodotto di domani. Non è un riassunto del
README: è **la risposta a "cosa deve stare nella prima schermata"** — e la prova
che serve è che un utente arrivi in fondo ai dieci minuti senza aprire le altre
780 righe.

---

## T8 — il guardiano che dice «no» quando è «sì»

Il README **prescrive** il comando: *«`verimem doctor` verifies the install»*
(righe 113 e 432). L'utente lo esegue e riceve `exit=1`; il passo successivo del
Quickstart, con il suo assert, esce `0` (fatto `d598fbae5396`, grounding 99,98):

```
  3 · verimem doctor                             8.2s  exit=1
  4 · il Quickstart del README, con il suo assert 30.5s exit=0   OK
```

**P2 e non P3** perché non è un comando qualsiasi: è quello che esiste per dire
se fidarsi. Un diagnostico che dà falsi allarmi si smette di leggere — e allora
non protegge più quando il problema è vero. **P2 e non P1** perché il percorso
arriva in fondo lo stesso: chi tira dritto ce la fa.

**Cosa lo cambia**: se dentro quell'`exit=1` c'è anche una condizione che
*davvero* rompe l'uso (non solo `not offline-pinned`), sale a P1 — perché allora
il rumore sta nascondendo un allarme vero. Owner Tara, e vale la pena guardarci.

---

# D-6 e D-7 — i due difetti del percorso ① (Giano, 04/09 21:11)

**Iris · 21:25.** Giano ha eseguito il percorso «un agente che lavora» dal
pacchetto di PyPI: giro intero **40 s**, **sette cose funzionano, tre no**.
Porta il fatto, il livello lo metto io.

## D-6 · **P0** — la porta MCP accetta `as_of` e lo ignora senza dirlo

```
CONTROLLO POSITIVO — MCP senza as_of:  1 risultato     ← acceso
SDK con as_of=ieri:                    0 risultati     ← filtra
MCP con as_of=ieri:                    1 risultato     ← NON filtra
la risposta MCP dichiara il filtro?    False           ← e non lo dice
```

**È il secondo P0, e non l'ho alzato per farlo notare: è la stessa specie del
primo.** `D-1` è «una self-claim non sostenuta entra come vera»; D-6 è «un fatto
superato torna come corrente». In entrambi **il prodotto serve come vero
qualcosa che non lo è, e chi legge non ha modo di accorgersene.** Quella è la
definizione di P0 che ho scritto ieri, prima di conoscere questo difetto.

**Perché non P1**, che sarebbe stato comodo: P1 è «il percorso non arriva in
fondo». Qui il percorso arriva in fondo — **dà una risposta**. Il guaio è che la
risposta è sbagliata e **indistinguibile da una giusta**: la stessa domanda,
stesso store, stesso istante, due esiti a seconda della porta, e il campo che
dovrebbe dichiarare il filtro dice `False` senza che nessuno lo legga.
**Non arrivare in fondo è meno grave che arrivarci con la risposta sbagliata.**

**E c'è un'aggravante di vetrina che il livello da solo non dice**: `as_of` è
una delle righe con cui ci **distinguiamo** nella tabella dei concorrenti del
README — *«Bi-temporal history & time travel (`as_of`) | shipped, tested»*
contro *«latest-value only (mem0 2.0.4)»*. Su una delle tre porte quella riga,
oggi, non è vera. **Rivendicare una capacità che una porta non ha è peggio che
non averla**: è la sola riga che un prodotto di verificabilità non si può
permettere.

🟢 **Circostanza che conta**: la cura **esiste già** — è il pezzo 3 di Giano
(`364b34fb`), fermo sul ramo in attesa della falsificazione di Marie e della
finestra del CTO. Quindi è **P0 con la cura in coda**, non un P0 aperto. Il
livello resta P0 finché la cura non è **nel pacchetto pubblicato**, perché la
gravità si misura su ciò che l'utente ha in mano, non su ciò che abbiamo sul
ramo.

**Cosa lo cambia**: la cura entra e viene pubblicata → il ticket si chiude. Se
invece si scoprisse che `as_of` sulla porta MCP **non è mai stato dichiarato**
(non compare nello schema dello strumento), scenderebbe a P1: sarebbe una
funzione mancante invece di una risposta falsa. *Non l'ho verificato — è la
prima cosa da guardare, e la guarda chi tiene le porte.*

## D-7 · **P2** — la CLI non stampa gli id dei fatti

`verimem recall` restituisce 250 caratteri e **nessun id**, mentre SDK e MCP lo
restituiscono. Trovato da Giano ieri, ricomparso oggi nel percorso.

**P2 e non P3**: non è un fastidio estetico, è **una capacità che una porta su
tre non ha** — e la nostra promessa dichiarata è «una capacità, tre porte,
stessa risposta». Chi lavora da riga di comando non può riferirsi a un fatto per
id.

**Cosa lo alza a P1** — e la misura è a portata di chiunque abbia dieci minuti:
**dalla CLI esiste un altro modo di correggere o ritirare un fatto specifico**
(per topic, per testo esatto, per posizione)? Se sì, resta P2: la strada è
scomoda ma c'è. **Se non ne esiste nessuno, un percorso dichiarato non arriva in
fondo e diventa P1.** Non l'ho verificato, e non do il livello peggiore a una
cosa che non ho guardato.

## Una nota di metodo, che vale più dei due livelli

Giano ha portato **sette cose che funzionano** insieme alle tre che non
funzionano. È la regola 3 di quelle che ho chiesto a chi esegue i percorsi
(«segnate anche ciò che ha funzionato»), ed è la ragione per cui la scheda
prodotto ha potuto scrivere una promessa invece di una lista di scuse: **un
elenco di soli difetti non dice se il prodotto è usabile, dice solo dov'è
rotto.** Le due righe migliori della scheda — la contraddizione risolta dal
prodotto e la transizione raccontata — vengono da quel suo elenco di verdi.

---

# Aggiornamento 21:45 — un ticket ritirato, un P0 nuovo, e T1 che cambia di livello

**Iris.** Tre cose sono arrivate in dieci minuti e due cambiano quello che avevo
scritto. Le registro qui con la stessa energia con cui avevo dato i livelli.

## T8 — **RITIRATO**, e non da me: da chi l'aveva aperto

Tara ha rifatto la misura con un A/B a una variabile sola:

```
stessa 0.7.6, stesso venv, stesso comando:
HIPPO_DATA_DIR=<store nuovo>   verimem doctor   →   EXIT=0     (nessun warning)
senza HIPPO_DATA_DIR           verimem doctor   →   EXIT=1
```

Nella prova C1 `ENGRAM_DATA_DIR` era **ereditata dall'ambiente** e puntava allo
store di produzione: `doctor` non stava diagnosticando l'installazione nuova,
diagnosticava uno store da 15.294 fatti, **i tre warning erano veri**, e
`exit 1` su warning è documentato (`0` ok, `1` warning, `2` errore).

**Il ticket 8 non è un difetto, ed è il contrario: il prodotto qui si comporta
bene.** Nomina lo store che sta guardando invece di nasconderlo.

⚠️ **E la parte che riguarda me.** Avevo dato **P2** a T8 argomentando che «il
README manda l'utente a un comando che dice *no* quando la risposta è *sì*».
Quell'argomento era buono e la premessa era falsa: **non ho verificato la misura
che stavo classificando**, l'ho presa dal fatto in memoria `d598fbae5396` — che
resta vero come misura (`doctor` 8,2 s `exit=1`, Quickstart 30,5 s `exit=0`) ma
**descriveva un ambiente sporco**. La lezione non è «Tara ha sbagliato»: è che
**una gravità data su una misura che non ho letto nel suo regime è una gravità
che non ho controllato.** D'ora in poi, per ogni livello, il campo «misurato da»
porta anche **il regime** — non solo il nome.

## Il P0 nuovo — **su una macchina nuova il fatto con fonte entra NON giudicato**

Corrado, stesso pacchetto, unica variabile il daemon:

```
CON il daemon di casa acceso
  flow.write  grounding_score=99.92135620117188  judged=True   layers=[]      latency_ms=303072
SENZA daemon — un utente che installa oggi
  flow.warmup what=moat-judge phase=start
  flow.write  grounding_score=None  judged=False  layers=['L4-skipped']
              status=model_claim  stored=True                                latency_ms=313110
```

**313 secondi di attesa per NON avere il giudizio, e il fatto è `stored=True`.**

**P0**, e la ragione è la definizione, non l'enfasi: la promessa scritta in cima
al prodotto è che una scrittura con la sua fonte viene **verificata prima di
essere ammessa**. Per un utente nuovo, oggi, quella promessa **non si realizza**
— e non c'è un errore: c'è una scrittura riuscita.

**Perché non è il caso già dichiarato nel README.** Il README dice: senza
giudice installato le scritture sono ammesse **con un avviso esplicito**
`L4-skipped`, mai in silenzio — ed è vero e onesto. Ma **qui il giudice è
installato** (712 MB sul disco, misurato da Tara) e il write **prova a
scaldarlo** (`flow.warmup phase=start`): non è «non l'hai scaricato», è «ce
l'hai e non è servito a niente». **La scritta copre un caso diverso da quello
che capita.**

## T1 — **da P1 a P0**, e non perché ho cambiato scala

Avevo dato **P1** a T1 argomentando: «non fa entrare nessuna confabulazione — il
fatto arriva **giudicato**, `grounding 99,92`». Quel `99,92` **veniva dalla
misura col daemon acceso**. Senza daemon lo stesso identico giro dà
`judged=False`.

⇒ **T1 e il P0 qui sopra sono lo stesso difetto visto da due lati**: l'attesa
era il sintomo, **il giudizio saltato è il danno**. Il mio P1 stava classificando
la lentezza; la conseguenza vera è che la promessa non si realizza.

**Alzo T1 a P0** e dichiaro il motivo per cui questo non viola la regola che ho
scritto io («un livello non si alza per far notare una cosa»): **non è cambiato
il livello, è cambiato il difetto.** Un'ora fa nessuno sapeva che finiva
`judged=False`. Se qualcuno mostra che il caso senza daemon non è quello di un
utente reale, torna P1 — e la misura che lo deciderebbe è già chiesta da Corrado:
**cosa legge l'utente nella risposta MCP?** Se la risposta dice a chiare lettere
«non giudicato», il difetto è grave ma onesto; **se non lo dice, è saltato E
silenzioso**, ed è il peggiore dei due mondi.

## D-6 — resta P0, e si allarga

Giano ha colmato quello che aveva dichiarato mancante: non una porta MCP, **due
su due** (`hippo_facts_search` e `hippo_facts_recall`), entrambe accettano
`as_of` e lo ignorano, nessuna delle due lo dichiara, l'SDK filtra. Il livello
non cambia: **cambia quante volte lo stesso P0 morde.**

---

## La domanda di prodotto che Corrado ha girato a me, e la mia risposta

> *«Quando il giudice non è disponibile, il fatto con fonte deve entrare NON
> giudicato (com'è ora), o non deve entrare?»*

**Non è una domanda a due risposte, ed è per questo che è rimasta aperta.**

**① Deve entrare** — un prodotto che rifiuta di scrivere quando un componente
non è pronto perde dati che l'utente ha già prodotto, e li perde nel momento
peggiore: il primo minuto. `L4-skipped` è la scelta giusta.

**② Ma non deve entrare COSÌ.** Oggi finisce `status=model_claim`, che è
**esattamente lo stato di un fatto giudicato e ammesso**. Lo stato non
distingue «giudicato e passato» da «mai giudicato»: la distinzione sta solo in
`grounding_score=None`, un campo che si legge se lo si sa. Per un prodotto che
vende verificabilità, **la differenza fra "verificato" e "non verificato" non
può stare in un campo nullo**: deve stare nello stato, e deve tornare al primo
richiamo.

**③ E la vera risposta è che la domanda arriva troppo tardi.** Il difetto non è
cosa fare *quando* il giudice non c'è: è che **il prodotto abbia aspettato 313
secondi per scoprirlo**. Chi aspetta cinque minuti ha diritto al giudizio, non a
un avviso. Le due cure stanno in ordine:
1. **non far aspettare per niente** — se il giudice non è pronto, dillo
   *subito*: una scrittura che torna in 2 secondi dicendo «non giudicato, il
   giudice si sta scaldando, richiama fra un minuto» è un prodotto onesto;
   una che torna in 313 secondi dicendo la stessa cosa è un prodotto rotto;
2. **rendere lo stato leggibile senza sapere dove guardare** — e qui la
   domanda per chi tiene il gate è se `model_claim` debba coprire due
   condizioni così diverse.
3. Un interruttore `strict` (rifiuta se non posso giudicare) è la terza,
   **e viene per ultima**: è la risposta comoda, quella che sposta la scelta
   sull'utente prima di aver sistemato ciò che dipende da noi.

*Owner della cura: non io — Tara per il warmup, il gate per lo stato. Questa è
la posizione di prodotto, e la difendo; la decisione tecnica è del CTO.*
---

## T11 · **P2** `[VETRINA]` — la distinzione fra «verificato» e «mai verificato» sopravvive alla scrittura in **due campi nulli**

**Misurato da Iris, 05/09 21:36**, sullo store di Aurelio **in sola lettura**
(`mode=ro`), nato da una domanda che avevo posto sul canale e che invece di
aspettare ho verificato.

**La domanda era**: quando la spiegazione del giudice-in-caricamento (`L4-skipped`,
*«this is NOT a pass»*) arriva nella risposta della chiamata — come Tara ha
misurato — **sopravvive nel fatto**? Chi lo rilegge dopo, o un collega che
ispeziona lo store, la trova?

**Risposta: no.** La tabella `facts` ha **32 colonne** e nessuna è dedicata ai
warning del gate. La stringa `L4-skipped` compare solo in `proposition`, `topic`
e `grounding_span` — cioè **dentro il testo dei nostri stessi fatti**, che di
`L4-skipped` parlano, non come campo di stato.

```
status=model_claim                    : 11.719
  di cui giudicati (score NOT NULL)   :  9.976
  di cui MAI GIUDICATI (score NULL)   :  1.743      ← 14,9%

un MAI GIUDICATO : status='model_claim'  tier=None    quarantined_by=None
                   epistemic=None        grounding_span=None
un GIUDICATO     : status='model_claim'  tier='high'  score=99.97
```

⇒ **Un fatto mai giudicato e uno giudicato al 99,97 hanno lo STESSO `status`.**
Ciò che li separa, nel record, è che due campi sono **vuoti**: `grounding_score`
e `confidence_tier`. Non c'è un'etichetta, non c'è il testo, non resta traccia
del fatto che una fonte fosse stata data e il giudice non ci fosse.

**Perché P2 e non P0**, benché tocchi la promessa centrale: **è dichiarato**, e
lo è nel posto giusto — le istruzioni del server MCP dicono testualmente che
`status` resta `model_claim` in entrambi i casi e che *«it is `grounding_score`
that carries it — a number means a source was judged, `null` means never
judged»*. Il prodotto non nasconde niente: **lo scrive**. E la distinzione
**arriva davvero** nel payload di lettura, dove `grounding_score: null` è
presente e visibile.

**Perché allora un livello, e non «non è un difetto»**: perché **la distinzione
che questo prodotto vende è affidata all'assenza di un valore.** Chi legge una
lista di fatti la coglie solo se sa che quel campo esiste e che il suo essere
nullo significa qualcosa. È la differenza fra dire una cosa e **farla vedere**,
ed è esattamente quello che avevo risposto a Corrado ieri sera — *«per un
prodotto che vende verificabilità la differenza fra verificato e non verificato
non può stare in un campo nullo»* — solo che allora era un'opinione e adesso è
una misura.

⚠️ **E la parte che NON so, che è la più interessante**: dei 1.743 mai giudicati,
**quanti avevano una fonte?** Un fatto scritto senza `source` non è giudicato
**per progetto** — è corretto così. Un fatto scritto **con** una fonte e non
giudicato perché il giudice era freddo è tutt'altra cosa: è T1 che lascia il suo
segno. **Il record non distingue i due casi**, quindi il numero non si può
spezzare — e questa impossibilità *è* il difetto, non un limite della mia misura.

⚠️ **Regime**: store di Aurelio (17.680 fatti), letto in sola lettura, corpus
storico che contiene anche fatti scritti prima del gate (i `legacy_unverified`
sono contati a parte e non entrano negli 11.719). Chi cita il 14,9% lo rifaccia
su uno store nuovo prima di metterlo in una pagina pubblica.

🔑 **La cura che proporrei, e non è mia da scrivere**: uno stato che dica la
condizione invece di lasciarla dedurre — `unjudged` accanto a `model_claim`, o
un `confidence_tier` che valga `unverified` invece di restare `None`, che è
peraltro **il valore che la risposta della chiamata già usa** (`"confidence_tier":
"unverified"`, misurato da Tara). ⇒ **Il prodotto ha già la parola giusta: la
dice nella risposta e non la scrive nel record.** Quella asimmetria è il ticket.

---

## T12 · **P3** — le due porte gemelle hanno **limiti massimi diversi nello schema**

**Reperto di Giano (ws2), 05/09 22:58**, trovato cercando altro:

```
  ⚠️ hippo_facts_recall NON ha risposto JSON:
     'Input validation error: 100 is greater than the maximum of 50'
  hippo_facts_recall   k=100      -1        ← RIFIUTATO dallo schema
  hippo_facts_search   limit=100  100       ← accettato, e rende 100
```

Stessa capacità, due porte, **due contratti pubblici diversi**. Non è un limite
interno: è lo **schema** che un agente legge per sapere cosa può chiedere.

**P3, e l'argomento è che l'errore parla.** Chi legge lo schema di `facts_recall`
vede `maximum: 50` e non sbaglia; chi sbaglia è chi **assume** che due porte
gemelle abbiano lo stesso contratto — e quando sbaglia riceve un messaggio
esplicito che dice il numero e il limite. **L'utente inciampa, capisce,
prosegue**: è la definizione di P3.

**Perché non P4 (dichiarato)**: P4 è per una trappola che il prodotto *sceglie*
e *scrive*. Qui non c'è una scelta documentata da nessuna parte — è una
divergenza che nessuno ha voluto. Uno schema è dichiarato *per costruzione*, ma
la divergenza fra due schemi non lo è.

⚠️ **Cosa lo alzerebbe, e nessuno l'ha ancora guardato**: Giano dichiara di
**non** aver cercato il tetto vero di `facts_search` (ha provato 100, non ha
trovato il massimo) né se la CLI abbia un **terzo** limite. Se da qualche parte
un limite **tronca in silenzio** invece di rifiutare, quello non è P3: è la
forma «serve meno di quanto hai chiesto e non lo dice», ed è **P0** — la stessa
specie di D-6 e T9. **La misura è una riga per porta**: chiedi oltre il massimo e
guarda se ti rifiuta o se ti risponde con meno.

🔑 **E T12 non va letto da solo.** Con **T4** (le chiavi dell'output in italiano)
e **D-7** (la CLI non stampa gli id) forma **una famiglia sola**: *una capacità,
tre porte, contratti diversi*. Presi uno per uno sono tre P2/P3 che nessuno
cura mai; presi insieme sono **il difetto che il ruolo delle porte esiste per
chiudere**, e il presidio che li impedirebbe tutti e tre vale più delle tre cure
separate. Giano l'ha detto meglio: *«non l'avevo mai misurata sui limiti, solo
sui campi»*.

## T13 · **P1** `[PROVA]` — il SIGSEGV di `test_hang_watchdog`, owner Corrado

3 SIGSEGV su 10 run falliti (due versioni di Python, tre commit, uno dei quali
conteneva **solo un documento**), il crash arriva **dopo 3939 test passati**, e
`exit 139` **non compare da nessuna parte nell'API**: si legge solo scaricando
il log del job.

> 🔁 **Alle 23:00 avevo scritto che a questo difetto la mia scala NON si applica**
> — «P0-P4 misurano cosa impedisce a un utente di fare, e questo tocca noi».
> **Il CTO mi ha dato P1 e ho cercato l'argomento invece di eseguire o rifiutare.
> L'argomento c'è, e non era quello che cercavo io.**
>
> La mia scala misura i **percorsi d'uso**. Ma un prodotto non consegna solo
> percorsi: consegna anche **le prove di quei percorsi** — «CI verde su 9 job» è
> nella vetrina, ed è ciò su cui un utente decide di fidarsi prima di installare.
> **Se un terzo dei nostri rossi è rumore, quella prova non regge**: non sappiamo
> se i 3939 verdi sarebbero rimasti verdi, perché il processo si è portato via
> anche quelli.
> ⇒ **P1 su una dimensione che la scala non aveva**: non blocca un percorso
> d'uso, blocca **la prova che diamo di quel percorso**. Marcatore **`[PROVA]`**,
> accanto a `[VETRINA]` — e come `[VETRINA]` **è una dimensione, non un livello
> nuovo**: dice *cosa rende inaffidabile*, non *cosa impedisce*.

**Perché P1 e non P0 su quella dimensione**: la prova è compromessa, non
**falsa**. Un run che muore non dichiara verde ciò che è rosso — dichiara
*fallito* ciò che forse era verde. **Sbaglia nella direzione prudente**, e questo
lo tiene sotto il livello massimo. Se un giorno un segfault producesse un
`success`, sarebbe P0 immediato.

**Owner Corrado** (Release/CI), come deciso dal CTO. E il pezzo che manca è già
scritto: **la condizione E** — la suite intera con `test_hang_watchdog` **in
fondo** invece che al suo posto. *Se il crash segue la posizione e non il file,
la causa è lo stato accumulato e non il watchdog.*

⚠️ **E resta separato il difetto di prodotto, che nessuno ha misurato**:
`_hang_watchdog.py` è **codice che gli utenti eseguono**. Se sotto carico
prolungato può portarsi via il processo, un utente subirebbe lo stesso crash —
e allora sarebbe **P0 su U-A**, perché un processo che muore si porta via anche
ciò che aveva già fatto. **Non misurato, quindi senza livello.** Sono due
ticket, non uno: T13 è ciò che sappiamo, l'altro è ciò che temiamo.

---

## T14 · **P1** — dopo una correzione con fonte, il fatto vecchio **non viene superato affatto**

**Misurato da Iris su `origin/main` (`95e886bb`), worktree pulito, con fonte e giudice
acceso**, 06/09 00:00. Banco: `ws7-il-percorso-di-un-team-su-uno-store.py`.

Anna scrive *«il fornitore di pagamenti del checkout è Stripe»* con il suo verbale; Bruno
corregge — *«è Adyen»* — con la comunicazione al team che lo sostiene. La correzione è
**giudicata e ammessa**: `cross_encoder`, score 99,45, tier `high`. Poi, nello store:

```
vecchio (anna)  status='model_claim'  superseded_by=None  superseded_at=None
nuovo   (bruno) status='model_claim'  superseded_by=None  superseded_at=None
```

🔑 **Il titolo che avevamo dato al difetto era sbagliato, e il dato lo corregge.** Non è
«il recall serve ancora il fatto superato»: **il fatto vecchio non è superato**.
`superseded_by` è nullo su entrambi. I due fatti coesistono nella top-k perché il prodotto
**li tratta come due fatti indipendenti**, non come una revisione. ⇒ È un difetto della
**relazione fra le scritture**, non della lettura — e questo sposta l'owner: tocca lo store
e la politica di supersessione **prima** delle porte.

### E il pezzo che vale più del difetto: il prodotto se n'era accorto

La ricevuta della correzione porta questo, verbatim:

```
advice = "il giudice non trova sostegno per questo claim nel fatto in memoria, che parla
          dello STESSO SOGGETTO (fact 677c78a3a2e1) — controlla prima di affermare."
```

**Il prodotto ha trovato il fatto correlato, ha riconosciuto che parla dello stesso
soggetto, ne ha citato l'id esatto — e poi ha ammesso il nuovo senza collegarli.**
⇒ Il difetto non è «non se ne accorge»: è **«se ne accorge, lo dice, e non agisce di
conseguenza»**. Il rilevamento c'è già; quello che manca è il collegamento fra quel ramo e
la supersessione.
⇒ **La cura ha già il suo controllo positivo**: quell'`advice` deve diventare **o una
supersessione o un conflitto dichiarato**, mai un'ammissione muta.

### Perché P1 e non P0

**La mia riga per il P0 è**: *il prodotto serve come vero — o tace — qualcosa che chi legge
non ha modo di controllare.* **Qui non tace**: avverte chi scrive, al momento della
scrittura, nominando il fatto in conflitto. Non è una confabulazione ammessa in silenzio.

**È P1** perché un percorso dichiarato — la revisione dentro un team, il passo 3 di U-B —
**non arriva in fondo**: chi legge dopo trova due fatti contraddittori entrambi serviti, e
l'avviso è arrivato a **chi ha scritto**, non a **chi legge**.

⚠️ **Cosa lo alzerebbe a P0, e la misura è piccola**: se quell'`advice` **non compare su una
delle tre porte**. L'ho visto **dall'SDK**; se su MCP manca, il caso rientra in «tace» e
diventa P0. *Non l'ho verificato.*

### La divergenza con Giano, ridotta a una domanda sola

Giano, su U-A, vede **solo il corrente**. Io, qui, vedo i due fatti coesistere. Con
`superseded_by` in mano la domanda non è più «perché divergiamo» ma:
**nel suo giro, il fatto vecchio aveva `superseded_by` valorizzato?** Se sì, la differenza
fra noi è **come si scrive la correzione** — e allora prima ancora di una cura serve **una
riga di documentazione**, perché oggi il modo giusto non è scritto da nessuna parte.

---

## T12 si allarga per la terza volta: **anche il nome del campo nella risposta**

Il ticket era nato sul **valore massimo** (`facts_recall` 50, `facts_search` 100, reperto di
Giano). Poi ho trovato, sbattendoci contro, che differisce anche il **nome del parametro**
(SDK e `facts_recall` usano `k`, `facts_search` usa `limit`). Stanotte, misurando T14, il
terzo:

```
SDK  search() -> elementi con chiave 'text'
MCP  hippo_facts_search -> items con chiave 'proposition'
```

⇒ **Stessa capacità, tre differenze di contratto su tre livelli diversi**: quanto puoi
chiedere, come si chiama quello che chiedi, come si chiama quello che ricevi. **Il livello
resta P3** — ogni singola differenza si scopre con un errore che parla — **ma la famiglia
non è più un dettaglio**: T12 + T4 (chiavi in italiano) + D-7 (id mancanti dalla CLI) sono
**quattro** divergenze di contratto fra porte che dichiariamo gemelle.
🔑 **E l'ho scoperta perché il mio banco leggeva `proposition` e trovava `None`**: il
fallback su `str(r)` faceva funzionare il conteggio per caso. **Un difetto di contratto che
si nasconde dietro un fallback è peggio di uno che rompe**: rompendo, si vede.

---

## T14 sale: **P0 sulla porta MCP**, P1 sull'SDK — misurato, non dedotto

**Iris, 06/09 00:13**, worktree su `origin/main`, store temporaneo, daemon acceso,
**finestra dichiarata 600 s** (atteso ~60 s). Banco:
`docs/stato-reale/banchi/ws7-t14-l-avviso-del-conflitto-sulla-porta-mcp.py`.

Avevo scritto che T14 è **P1 e non P0** *«perché il prodotto non tace: avverte chi scrive,
nominando il fatto in conflitto»*, e avevo dichiarato la misura che l'avrebbe alzato:
**quell'avviso compare anche sulla porta MCP?**

**Non compare.** Stessa correzione, stessa fonte, stesso store, porta MCP:

```
chiavi della ricevuta MCP: adjudication · anti_confab_warnings · confidence · deferred
    gate_knobs_denied · grounding_score · id · moat · ok · proposition · replaced
    source_signature · status · topic · verified_by

  'advice' fra le chiavi?          NO
  'stesso soggetto' nel corpo?     NO
  anti_confab_warnings             []          <- vuoto
  moat   "judged 99.8 — the source SCORES as supporting this fact"
  status "model_claim"   ok true   replaced false
```

⇒ **Per l'utente MCP il prodotto TACE**, e la mia riga per il P0 è precisamente *«serve
come vero — o TACE — qualcosa che chi legge non ha modo di controllare»*.

### Cosa vede davvero un utente MCP che scrive una correzione

`ok: true` · `status: model_claim` · `replaced: false` · `moat: judged 99.8` ⇒ **tutto
verde**. Ha appena inserito nello store un fatto che contraddice uno esistente, il prodotto
**se n'era accorto** (l'SDK lo dimostra: cita l'id del fatto in conflitto), e **sulla sua
porta non gliel'ha detto**. Il `99.8` che legge non parla del conflitto: parla solo del
fatto che la **sua** fonte sostiene la **sua** frase.

🔑 **E il campo che renderebbe tutto ovvio esiste già su quella porta**: `replaced` dice
`false`. Dice il *cosa* e non il *perché*: non «non ho rimpiazzato nulla **benché ci fosse
un candidato**». **La porta ha il posto dove metterlo e non ce lo mette.**

> 🔁🔴 **CORREZIONE del 06/09 09:30 — ed è peggio di così (`T24`, reperto di @ws6 Aldo,
> `git grep` su tutto il pacchetto).** `replaced` **è sempre `False` PER COSTRUZIONE**:
> non è un campo generico che dice il *cosa* e non il *perché* — **è un campo che non
> misura mai niente**, nemmeno quando una supersessione avviene davvero. Un campo
> pubblico il cui nome promette ciò che il valore non porta.
> ⚠️ **E questo invalida una MIA prova, non il ticket.** Nei tre bracci che ho misurato
> alle 06:01 avevo scritto *«`replaced=False` in tutti e tre»* e l'avevo letto come un
> **verdetto del prodotto**: era **un criterio spento per costruzione, non un risultato
> falsificato**. T14 regge — lo reggono le sei guardie escluse e il ramo del rango — ma
> **quella riga non lo provava**.
> ✅ **Criterio nuovo, dal lead**: la supersessione si legge **dallo STORE**
> (`superseded_by` sul fatto vecchio), **mai** da `replaced`.
> 🪞 *Terza volta oggi che leggo il NOME o il TESTO invece della CONDIZIONE (T17, T8-bis,
> questa). La forma è sempre la stessa: un campo o un messaggio si legge per come è
> ALIMENTATO, non per come si chiama.*

### Il livello, e perché sono due

**P0 su MCP · P1 sull'SDK.** Non è un'incoerenza: **la gravità si misura su ciò che
l'utente ha in mano**, e l'utente MCP ha in mano meno. Sull'SDK l'avviso arriva a chi
scrive — resta un percorso che non arriva in fondo (P1); su MCP non arriva a nessuno, e il
prodotto fa esattamente la cosa che dice di impedire (P0).
⇒ **La porta MCP è quella che gli agenti usano.** È la porta del caso d'uso per cui il
prodotto esiste.

⚠️ **Quinta divergenza di contratto della famiglia T12**, e la più costosa: le due ricevute
divergono su **quattordici campi** — dieci esistono solo su MCP (`anti_confab_warnings`,
`confidence`, `deferred`, `gate_knobs_denied`, `ok`, `proposition`, `replaced`,
`source_signature`, `topic`, `verified_by`) e quattro solo sull'SDK (`advice`, `stored`,
`quarantined_by`, `warnings`). **Fra i quattro che mancano su MCP c'è proprio quello che
qui decide un livello.** T12 resta P3 come classe, ma questa istanza specifica **non è un
inciampo**: è il canale per cui un difetto diventa invisibile.

---

## Il passo 5 di U-B, misurato sulla porta giusta — **T6 confermato** e **T15 nuovo**

**Iris, 06/09 00:37**, worktree su `origin/main`, store temporaneo, daemon acceso,
**finestra dichiarata 600 s** (atteso ~90 s). Banco:
`docs/stato-reale/banchi/ws7-u-b-passo-5-l-audit-dalla-porta-mcp.py`.

Tre chiamate dalla porta MCP — due valide e **una volutamente invalida**
(`hippo_facts_recall` con `k=100`, che lo schema rifiuta a 50). Il registro:

```
righe nel registro: 2          (per TRE chiamate)
campi: args_hash · caller_pid · error · latency_ms · outcome · tool · ts

{"ts":…, "tool":"hippo_remember",      "caller_pid":29928, "outcome":"ok_new", "error":"", "latency_ms":20522.0}
{"ts":…, "tool":"hippo_facts_search",  "caller_pid":29928, "outcome":"ok",     "error":"", "latency_ms":8.19}

la chiamata rifiutata: "Input validation error: 100 is greater than the maximum of 50"
righe che nominano 'recall': 0
```

### T6 · **P1 CONFERMATO**, e ora l'ho verificato io

Il 04/09 avevo dato P1 a T6 (*«le chiamate rifiutate per validazione non entrano in
`mcp_audit.log`»*) **su un reperto di Corrado, senza rieseguirlo**, e l'avevo scritto nel
documento. **Adesso è misurato: tre chiamate, due righe, la rifiutata manca.** Il livello
regge e la ragione è la stessa: un registro che omette i rifiuti **afferma per omissione**
che è andato tutto bene.
🔑 **E c'è un dettaglio che lo rende più netto: il campo `error` ESISTE ed è `""` in
entrambe le righe.** Il posto per dirlo c'è — come `replaced` in T14 — **e resta vuoto
perché la riga che dovrebbe riempirlo non viene mai scritta.**

### T15 · **P1** — l'audit dice **cosa**, non **chi**

`dice COSA: ['tool']` ✅ · **`dice CHI: NESSUN CAMPO`** 🔴

C'è `caller_pid: 29928`. **Un numero di processo non è un'identità**: non dice quale
agente, quale persona, quale `principal`. Due agenti diversi sulla stessa macchina, nello
stesso processo, sono indistinguibili — ed è precisamente il caso di U-B.

⚠️ **Ma il livello va argomentato contro me stessa**, perché la provenienza **c'è
altrove**: ogni fatto porta `writer_principal` (misurato al passo 2: `anna`/`bruno`). Un
team può ricostruire **chi ha scritto quale fatto** leggendo i fatti. ⇒ Quello che manca
nell'audit è **chi ha fatto le AZIONI** — chi ha letto, chi ha tentato, chi si è visto
rifiutare una chiamata. **P1 e non P2** perché in uno store condiviso *chi ha guardato
cosa* è metà del motivo per cui esiste un registro; **non P0** perché il prodotto non
afferma il falso: dice meno.

### 🪞 E una correzione al MIO criterio di arrivo, che era mal scritto

Avevo scritto che U-B arriva in fondo se passano **2 + 4 + 5**. **Il 5 non serve alla
frase che avevo scritto io**: *«un quarto ricostruisce dallo store chi ha scritto cosa,
quando, e perché il valore corrente è quello»*. «Chi / cosa / quando» si ricostruisce **dai
fatti** (passo 2, verde); «perché il corrente è quello» dipende dal **passo 4** (T14, rosso).
⇒ **Il criterio non è raggiunto per colpa del passo 4, non del 5.** Il mio elenco operativo
non corrispondeva alla mia stessa frase — e l'ho scoperto solo eseguendo il passo che
credevo decisivo. **Un criterio scritto prima non è automaticamente un criterio giusto: va
riletto contro la frase che dice di misurare.**

### ⇒ U-B: il criterio è ora **DECIDIBILE, e NON è raggiunto**

    1 due scrittori ✅ · 2 provenienza ✅ · 3 correzione giudicata ✅ · 6 scadenza ✅
    4 solo il corrente 🔴 T14   ·   5 audit 🔴 T6 + T15
    ⇒ NON ARRIVA IN FONDO, e il responsabile è il passo 4.

⚠️ **Settima volta della stessa forma, colta subito.** Il mio banco stampava *«il registro
nomina un rifiuto/errore? True»* — **falso positivo**: la parola `error` c'era come **nome
di campo**, non come contenuto. L'ho vista solo perché ho stampato **le righe intere**
invece di fidarmi del conteggio. **Il criterio guardava di nuovo una rappresentazione.**

---

## T14, la causa — e la mia formulazione era imprecisa

**Trovata da Aldo (ws6) il 06/09 00:49**, quattro bracci a una variabile per volta, slot
preso e rilasciato. **La risposta è la terza, e non era nessuna delle due che avevo
formulato io.**

Avevo scritto: *«il prodotto se ne accorge, lo dice, e non agisce di conseguenza»*.
**Falso nella seconda metà: il prodotto AGISCE.** Il gate emette un verdetto esplicito —
`L3-coexistence` in **4 bracci su 4** — e lo motiva con parole sue:

```
"L3-coexistence": {
  "reason": "a contradiction was found but both facts are kept",
  "advice": "the clashing facts were judged to be about DIFFERENT ENTITIES — a distinct
             code, date, numbered record, attribute or proper name — so neither is an
             update of the other: both stay servable…"
}
```

⇒ **Non è un'omissione: è una decisione, presa su un criterio identificabile.** E il
criterio è `_entita_diverse`, che Aldo ha misurato come funzione pura:
`Stripe` contro `Adyen` → **entità diverse**. **Il criterio guarda i nomi propri ovunque
siano, e quando il nome proprio è il VALORE CHE CAMBIA lo scambia per un soggetto
diverso.** «Il fornitore del checkout è Stripe» → «…è Adyen» è l'aggiornamento **dello
stesso attributo dello stesso soggetto**; il gate ci legge due record distinti.

🔑 **Questo migliora il ticket, non lo indebolisce**: un difetto con un criterio nominato e
una funzione pura che lo isola è **curabile**; «non collega la correzione» non lo era.
Il merito è di Aldo, e il metodo pure — quattro bracci, una variabile per volta, e **cinque
sue ipotesi cadute** per arrivarci.

### Ma il P0 su MCP resta, e ora è più netto

Il verdetto `L3-coexistence`, con la sua `reason` e il suo `advice`, **è quello che l'utente
avrebbe bisogno di leggere**. Sulla porta MCP, nella stessa condizione:

```
anti_confab_warnings = []      adjudication.reason = ""
la stringa 'L3-coexistence' compare nella ricevuta MCP?   False
la stringa 'coexist' in qualunque forma?                  False
```

⇒ **Non manca «un avviso»: manca IL VERDETTO.** Il prodotto ha preso una decisione
motivata sui due fatti e **su quella porta non la consegna**. Chi corregge un fatto da MCP
riceve `ok:true`, `replaced:false`, `moat: judged 99.8` — e la decisione che lo riguarda
resta dentro.

⇒ **Sono due difetti in fila, e vanno curati in ordine inverso a come li abbiamo trovati:**
1. **il criterio sbaglia** (`_entita_diverse` sul valore che cambia) — owner lo store, cura
   di Aldo, ed è il difetto di merito;
2. **il verdetto non arriva su MCP** — ed è **indipendente dal primo**: *anche quando il
   gate deciderà giusto, se il verdetto non arriva sulla porta degli agenti l'utente non
   saprà comunque cosa è successo al suo fatto.* Curare solo il ① lascia in piedi il ②.

---

## T8-bis · **P1** — due avvisi di `doctor` non si spengono mai, e uno dei due sembra transitorio

> 🔁 **TITOLO RIFATTO il 06/09 08:40.** Diceva *«l'exit code di `doctor` non
> discrimina»*: **falso**, e l'ha mostrato @ws8 Corrado leggendo il codice —
> `cli.py:721` dichiara `0 all-ok · 1 warnings · 2 failures`, un contratto pubblico
> che **discrimina in tre livelli**. Il mio errore: avevo letto la causa dal **testo**
> dell'avviso (la parola *warming*) invece che dalla **condizione** che lo accende
> (`_judged / _n < 0.5`, `doctor.py:724`). ⚠️ **È la seconda volta che sbaglio così
> sullo stesso tipo di oggetto**: su **T17** avevo letto la regola dal testo
> dell'avviso e @ws4 Nadia trovò nel codice il verso opposto.
> ⬆️ **E il difetto ne esce PEGGIORE**, non migliore: `_judged / _n` è **cumulativo**,
> quindi i fatti scritti prima che il giudice fosse pronto restano non giudicati per
> sempre e **quell'avviso non si spegne da solo**. La cronaca qui sotto conserva il
> percorso, inclusa la formulazione ritirata.

### 🔁🔴 06/09 07:30 — **la riga «già curato su main» era MIA ed era FALSA**, e il difetto è un altro

**Nato dalla domanda di @ws8 Corrado**, che non trovava il commit da mettere nel CHANGELOG
della 0.7.7 e **si è rifiutato di inventarlo**. Aveva ragione:

```
git diff v0.7.6..origin/main -- verimem/doctor.py     ->  INVARIATO
commit fra v0.7.6 e main che nominano doctor/relevance/floor  ->  nessuno
```

⇒ **Non c'è nessuna cura in arrivo.** La mia riga prometteva un rilascio che avrebbe
sistemato una cosa che nessuno aveva toccato.

#### Perché mi ero sbagliata: **due esiti, stessa versione, e ho incolpato la versione**

La mia misura di stanotte diceva *«su main esce 0, sul pacchetto esce 1»*. Rifatta oggi,
la variabile è un'altra:

```
① store nuovo, directory vuota      doctor EXIT=0   «nessuno store da esaminare»
② store creato ma senza recall      doctor EXIT=0   «not computed yet»
③ store vuoto DOPO un recall        doctor EXIT=1   «floor 0.0000 computed on 0 facts»
```

⇒ **Non «main o pacchetto»: SE il floor è già stato calcolato**, e si calcola **al primo
recall**. Su main non l'avevo ancora fatto; sul pacchetto sì.
🔑 *Quando due esiti hanno la stessa versione, la variabile è un'altra — e attribuirla alla
versione è un errore che si pubblica.*

#### 🔴 E il difetto vero, che vale più della riga sbagliata

Nel braccio **sano** — floor `0.8554` su 3 fatti, tutti gli altri check verdi — **`doctor`
esce `1` lo stesso**:

```
✓ version · ✓ mcp · ✓ data-dir · ✓ daemon · ✓ embedding-model · ✓ undo-window · ✓ topic-crowding
! moat-judge   local CE gate model installed (state here: warming), but only …
EXIT=1
```

⇒ **L'exit code di `doctor` non distingue «installazione rotta» da «installazione appena
fatta».** È la stessa forma di **T17** — *un verdetto che si accende quasi sempre smette di
essere letto* — **applicata al comando che il README prescrive DUE VOLTE** (righe 113 e
432) come verifica dell'installazione.

🪞 **E la prova che funziona così siamo noi**: nella scheda avevo scritto all'utente *«se al
passo 3 vedi rosso, tira dritto»*. **Avevamo già imparato a ignorarlo — e dentro quelle
righe ce n'era una che segnala una capacità spenta.**

#### Perché **P1** e non P3, e cosa lo porterebbe a P0

**P1**: il pavimento a `0.0000` **spegne l'astensione per rilevanza** e **non si ricalcola**
quando arrivano i fatti — il prodotto lo dichiara da sé (*«reads no longer recompute it:
that cost 24s inside a query»*). Una capacità della prima schermata — *«or with an honest
«I don't know»»* — resta spenta finché nessuno esegue `warmup`, e **l'unico segnale è
dentro un comando il cui verdetto abbiamo imparato tutti a scavalcare**.

📏 **La misura per il P0 l'ho FATTA e NON l'ha dimostrato**, quindi resta P1:

```
ORDINE-A (fatti prima)    floor 0.8554 · domanda estranea -> 3 serviti
ORDINE-B (recall prima)   floor 0.0000 · domanda estranea -> 3 serviti
```
⇒ **La differenza nel pavimento è reale e riprodotta**, ma **nemmeno il braccio sano tace**
sulla domanda estranea da `verimem recall`: il pavimento non morde su quella porta, e il
confronto non prova il danno. **Il banco esce `NON MISURATO`, non «uguale».**
*(Prossimo passo, quando la RAM lo permette: la stessa prova dalla porta MCP, dove la
risposta porta `sotto_il_pavimento`.)*


**Chiuso da Iris il 06/09 01:35**, rieseguendo U-C col banco corretto (il primo troncava
l'uscita). Pacchetto **0.7.6 da PyPI**, venv vergine, ambiente ripulito, **dopo un `warmup`
riuscito**. Totale del giro: 337,7 s.

```
✓ daemon        shared encode daemon warm on :60784
✓ moat-judge    local CE gate model installed — the grounding moat is ON
✓ llm           no llm provider — the moat and recall do not need one
✓ confidence-vs-verifica   0 fatti giudicati dal moat: troppo pochi per…
! relevance-floor   floor 0.0000 computed on 0 facts, now 0 — a floor of 0.0 (…«no floor»)
      fix: verimem warmup
⇒ exit = 1
```

**Il difetto in una riga**: su un'installazione nuova lo store è **vuoto per definizione**,
il pavimento di rilevanza si calcola **su 0 fatti**, il check diventa `WARN` e `doctor`
esce **1** — **suggerendo `verimem warmup`, che è il comando appena eseguito e che non
c'entra**: il warmup scarica il modello, non crea fatti. **Tutti gli altri check sono
verdi.**

### Perché **P3**, e non ciò che il ticket 8 diceva all'inizio

Il ticket 8 era nato come *«`doctor` esce 1 su un'installazione che funziona»*, ed è stato
**ritirato giustamente** da Tara: quell'`exit 1` veniva da una variabile d'ambiente
ereditata. **Questo è un altro difetto, molto più piccolo e molto più preciso**, e riguarda
**tutti** i nuovi utenti perché la condizione — *store vuoto* — è inevitabile.

**P3**: l'utente inciampa (un rosso al terzo comando del Quickstart), **capisce** (gli altri
check sono verdi e il testo dice cosa manca), **prosegue** (il Quickstart passa). Non blocca
il percorso — U-C arriva in fondo in 5,6 minuti.
⚠️ **Con un'aggravante che non alza il livello ma va scritta**: **il `fix` è sbagliato.**
Mandare l'utente a rifare il comando che ha appena fatto è peggio che non suggerire niente,
perché lo fa dubitare di ciò che ha fatto bene.

### 🔴 ~~E la parte migliore: è già curato su `main`~~ — **RITIRATA il 06/09: era falsa**

*Questa sezione diceva che su `main` `doctor` esce `0` e che bastava aspettare il prossimo
rilascio. **Non è così**, e la quarta copia della stessa frase l'ho trovata applicando la
regola che mi ero data: **quando un'affermazione di stato cade, si cerca la FRASE, non il
documento**.*

```
git diff v0.7.6..origin/main -- verimem/doctor.py   ->   INVARIATO
```

⇒ **Non c'è nessuna cura da far entrare.** L'`exit 0` che avevo osservato veniva da un
**altro stato dello store** (il floor non ancora calcolato), non da un'altra versione — e
appena il floor si calcola su zero fatti, **anche `main` esce `1`**.
📌 **Resta valido il suggerimento di smoke**, ma con il criterio giusto: non *«doctor non
deve vedere rosso»* — bensì **«leggi QUALI righe hanno `!`»**, perché **due** non si
spengono aspettando: `relevance-floor 0.0000` (astensione spenta) e `moat-judge`
(copertura cumulativa sotto la metà).
> 🔁 **Corretto il 06/09 08:40**: questa riga diceva *«quella SOLA segnala una capacità
> spenta»* e dava `moat-judge` per transitoria. Sono **due**. E la mia parentesi
> «uscirà `1` anche a installazione sana» presupponeva la formulazione ritirata sopra:
> @ws8 ha letto che con `_n == 0` la condizione è falsa e **su store vuoto `doctor`
> esce `0`**. ⚠️ **Questo non torna con la mia misura di stanotte**, dove uno store
> vuoto dopo un recall dava `EXIT=1` con `floor 0.0000 computed on 0 facts`: il mio `1`
> può essere venuto dal **pavimento** e non dalla copertura. **Non lo risolvo leggendo**
> — il controllo che decide è eseguire `doctor` su uno store vuoto e guardare **quale
> riga** porta il `!`. In attesa di RAM.

🪞 **E la lezione sul mio banco**: la prima esecuzione **troncava l'uscita a due righe** e
lasciava solo `fix: verimem warmup` — abbastanza per accorgersi che qualcosa non andava,
**non abbastanza per sapere cosa**. Ho dovuto rieseguire (5,6 minuti) per una riga che il
primo giro aveva già prodotto e buttato via. **Un banco che tronca l'uscita fa pagare due
volte la stessa misura.**

---

## T2b — il numero che mancava, e la cura proposta (Nadia, 06/09 01:38)

Avevo dato a T2b un costo (**38.675 token per sessione**) e nessuna misura di **quanto di
quel costo serva**. Nadia l'ha portata, dai **15.099 usi veri** del nostro traffico:

```
11 strumenti = 50% degli usi · 28 = 80% · 37 = 90%
102 strumenti MAI CHIAMATI in 119,8 giorni
```

⇒ **Il ticket cambia di natura: non è «sono tanti», è «paghiamo per una coda che non
serve».** 37 strumenti coprono il 90% e ne esponiamo 249; **102 non li ha chiamati mai
nessuno.** ⚠️ **Perimetro dichiarato da lei e che tengo**: è **il nostro** traffico, non
quello di un utente — la curva potrebbe essere diversa per chi usa il prodotto in un altro
modo, e questo va detto se il numero finisce in una pagina pubblica.

### E la diagnosi è la nostra classe ①, in una forma nuova

· **La manopola che esiste** — `ENGRAM_MCP_TOOLS_PREFIX` (`mcp_server.py:1533/1543/1550/7598`)
  — lavora **per prefisso**, e i venti più usati **non condividono un prefisso**: sono
  `hippo_` come gli altri 228. Con `hippo_` passano tutti, con qualunque altro se ne perde
  la maggior parte. **Non può esprimere un profilo.**
· **La manopola che servirebbe** — `HIPPO_EXPOSE_TOOLS`, una **lista di nomi** — è
  **impostata con 10 nomi sulla macchina di Aurelio** e ha **zero righe nel sorgente**
  (verificato da me, poi da Marie: *«è inerte, il server ne espone 249 in entrambi i
  bracci»*).

🔑 **Nadia lo dice meglio di come lo direi io**: *«le due metà della soluzione esistono in
due posti diversi: quella implementata non serve, quella che servirebbe non è implementata.
Non manca un'idea: manca una giuntura.»*

### Cosa cambia nel livello: **niente, e lo dico**

**T2b resta P2.** La curva rende il difetto più *nitido* e la cura più *facile*, ma non
cambia **cosa impedisce a un utente di fare**: paga un costo di contesto che non si aspetta
e arriva in fondo lo stesso. **Un ticket meglio compreso non è un ticket più grave** — e la
tentazione di alzarlo perché adesso «si vede meglio» è la stessa che ho rifiutato per T1 il
04/09.

⇒ **Quello che cambia è la PRIORITÀ, non la gravità**: una cura con tre livelli già
dimensionati sulla curva (`minimo` 11 · `base` 28 · `pieno` 37) e un innesto su codice che
**già filtra** è un P2 che costa poco — e i P2 che costano poco si fanno prima dei P2 che
costano molto. *La decisione è del CTO; l'implementazione è della porta (@ws2), non mia.*

---

## T16 · **P0** — l'SDK scrive in un posto, la CLI ne guarda un altro, e la CLI dice «no facts found» con `exit 0`

**Misurato da Iris, 06/09 02:00**, ambiente ripulito, `HIPPO_DATA_DIR` impostato, **la
riga che il nostro Quickstart insegna**: `Memory("memoria.db")`.

```
SDK scritto:  798a2d0d0baf
SDK rilegge:  ['Il fornitore di pagamenti del checkout e Stripe.']     ✅

la CLI, dalla STESSA cartella, stesso ambiente:
  verimem recall "fornitore di pagamenti"
  exit = 0
  no facts found                                                        🔴

dove sono finiti i file:
  nella CWD  →  memoria.db 98.304 byte · memoria.db-shm · memoria.db-wal
  nello STORE (`HIPPO_DATA_DIR`) →  events.jsonl 613 byte
```

### 🔁 La causa che avevo scritto era sbagliata — la corregge @ws6 Aldo, e la misura è sua

**Avevo scritto**: *«il prodotto ha due modi di dire dove sta la memoria e i due non si
parlano: l'SDK usa il percorso, la CLI usa il data dir»*. **Falso nella causa**, e Aldo
l'ha misurato in tre ambienti prima di scrivere (`364d88c7ed0c33a1`):

```
SENZA variabili
  Memory()            ->  C:\Users\aurel\.engram\semantic\semantic.db
  open_memory()       ->  C:\Users\aurel\.engram\semantic\semantic.db   ← quello della CLI
  CONFIG.semantic_db  ->  C:\Users\aurel\.engram\semantic\semantic.db
con HIPPO_DATA_DIR    ->  tutte e tre nel tempdir indicato
con ENGRAM_DATA_DIR   ->  tutte e tre nel tempdir indicato
```

⇒ **Il default è già una superficie unica: le tre porte NON divergono.** Quello che avevo
osservato — i fatti in una cartella, gli eventi nell'altra — era **vero nell'effetto e
sbagliato nel meccanismo**: avevo dedotto «due risoluzioni che non si parlano» da un
comportamento, **senza misurare la risoluzione**. ⚠️ È la **decima** occorrenza della
forma che mi porto dietro da due giorni — *ho guardato una rappresentazione della cosa
invece della cosa* — e stavolta l'ha intercettata un pari, non io.

### La causa vera: **un'asimmetria di interfaccia**, non di risoluzione

```
Memory("memoria.db")   ->  db_path = 'memoria.db'          RELATIVO alla CWD
la CLI ha --db ?           recall: 0 · remember: 0 · facts: 0     occorrenze
```

⇒ **Il percorso esplicito è una cosa che solo l'SDK può ricevere.** La CLI non «legge il
data dir invece del percorso»: **non ha modo di sapere che un percorso esiste**. E ne
segue un secondo effetto che nessuno aveva nominato: **`Memory("memoria.db")` resta
relativo alla CWD** — lo stesso identico codice, lanciato da due cartelle diverse, apre
**due store diversi**, e ognuno risponde «non lo so» sull'altro. *(Il RED su questo lo
scrive Aldo: è il suo pezzo, non lo rifaccio.)*

📌 **Il livello resta P0, e il perché non dipendeva dalla causa**: l'effetto misurato —
la CLI dice `no facts found` con `exit 0` sulla riga che insegniamo — è quello che
decide la gravità. **Ma una causa sbagliata nel documento è peggio di nessuna causa**:
chi legge dimensiona la cura su di essa, ed è esattamente quello che era successo (vedi
la correzione al piano, sotto).

### Perché **P0**

La mia riga per il P0 è: *il prodotto serve come vero — o **tace** — qualcosa che chi legge
non ha modo di controllare.* Qui **la CLI tace**: dice `no facts found` **con `exit 0`**,
e — come ha scritto @ws6 Aldo per i file alla radice — **non esiste modo, dalla risposta,
di distinguere «non ho quel fatto» da «sto guardando il posto sbagliato»**. È la stessa
risposta che il prodotto dà quando davvero non sa, ed è la risposta che questo prodotto
esiste per rendere affidabile.

⚠️ **E non è un uso sbagliato: è la riga che insegniamo noi.** `Memory("memoria.db")` sta
nel Quickstart del README e nella scheda prodotto. Chi segue le nostre istruzioni finisce
esattamente qui.

### Il legame con gli altri due reperti di stanotte

· **@ws6 ALDO, i nove file alla radice**: il suo è il lato *store* dello stesso problema —
  file che sembrano la memoria e non lo sono, e **il peggiore ha lo schema giusto con zero
  fatti**. Il mio è il lato *utente*: **è il nostro Quickstart a crearne uno**.
· **@ws5 TARA** l'aveva **sfiorato** il 05/09 ritirando il ticket 8: *«il Quickstart del
  README scrive in un posto e la CLI ne guarda un altro quando le variabili d'ambiente
  sono in disaccordo… lo verifico prima di aprire qualsiasi cosa»*. **Aveva ragione, e
  adesso c'è la misura** — e le variabili non erano nemmeno in disaccordo: erano coerenti,
  ed è il **percorso relativo** a scavalcarle.

### Cosa lo abbasserebbe

Se `Memory("memoria.db")` **con `HIPPO_DATA_DIR` impostato** fosse documentato come «due
store distinti, di proposito», sarebbe **P4 · dichiarato**. *Non l'ho trovato scritto da
nessuna parte* — né nel Quickstart, né nella scheda, né nelle istruzioni MCP — ma **non ho
letto le 812 righe del README**, e chi le conosce può smentirmi in un `grep`.

### 🔑 E la cura più piccola non è tecnica

Prima ancora di far parlare i due percorsi, **la CLI non deve dire `no facts found` senza
dire DOVE ha guardato.** Una riga — *«nessun fatto in `<path>`»* — trasforma un silenzio
indistinguibile in un messaggio che si corregge da solo, e **`doctor` lo fa già**: nomina
lo store che sta esaminando, ed è precisamente per questo che Tara ha potuto ritirare il
ticket 8 in dieci minuti.

---

## T16 — la riga che funziona su entrambe le porte, misurata (e una correzione alla cura proposta)

**Il CTO mi ha assegnato il pezzo 3**: *«la riga insegnata funziona su ENTRAMBE le porte
nella stessa cartella: o `Memory()` col default condiviso, o `Memory("memoria.db")` + il
comando CLI con `--db memoria.db»`*. **Misurate tutte e due, più quella di oggi**, ambiente
ripulito, `HIPPO_DATA_DIR` impostato, 06/09 02:07:

```
A  Memory("memoria.db")  +  verimem recall …            SDK OK · CLI NON TROVA   exit 0
B  Memory("memoria.db")  +  verimem recall … --db …     SDK OK · CLI NON TROVA   exit 2
     → Usage: recall [OPTIONS] QUERY        ⇒ `recall` NON ACCETTA `--db`
C  Memory()  senza argomento  +  verimem recall …       SDK OK · CLI TROVA ✅     exit 0
```

⇒ **La riga da insegnare oggi è `Memory()` senza argomento**: SDK e CLI vedono lo stesso
store, e la coppia scrivi-rileggi funziona **senza cure e senza aggiramenti**.

🔴 **E una correzione alla cura proposta**: il piano dice *«`--db PATH` esiste su
`recall`/`remember`/`facts` **se non c'è già**»*. **Non c'è su nessuno dei tre**, e adesso
è misurato due volte in modo indipendente: io dal comportamento — `verimem recall … --db`
esce **2** con l'usage — e **Aldo contando le occorrenze**: `recall: 0 · remember: 0 ·
facts: 0`. ⇒ **Il pezzo (2) della cura non è un ritocco: è tutto da scrivere**, su tre
comandi invece che su zero, e chi lo prende deve saperlo prima di dimensionarlo.
L'opzione `--db` compare altrove in `cli.py` (righe 1023, 1860, 5440,
5499) ma **non su `recall`**, che è il comando del Quickstart. ⇒ **Il pezzo (2) della cura
è più grande di come è stato dimensionato**, e chi lo prende deve saperlo prima.

## E l'osservazione di Giano, che alza il ticket invece di ridurlo

Giano ha **vissuto lo stesso difetto il 04/09** e l'ha attribuito a sé. Il suo appunto di
quella sera, verbatim:

> *«ho scritto via `Memory("<dir>/u.db")` ma riletto da CLI e MCP che aprono
> `HIPPO_DATA_DIR/semantic/semantic.db` — **due store**, e un rosso falso pronto da
> consegnare»*

⇒ **Ha aggiustato il proprio banco ed è andato avanti.** È una conferma indipendente a 48
ore di distanza, e porta con sé l'argomento che rende questo P0 più grave degli altri:

🔑 **Un difetto che l'utente scambia per un proprio errore non viene mai segnalato.**
Giano conosce il prodotto, aveva passato la serata dentro quel codice, e ha comunque
concluso «ho sbagliato io a costruire il banco». **Chi installa da PyPI non ha nemmeno gli
strumenti per formulare il dubbio**: vede `no facts found`, `exit 0`, e conclude che la
memoria non ha salvato — o che il prodotto non funziona.
⇒ **Il tasso di segnalazione atteso di T16 è circa zero.** Non lo troveremo mai nei report
degli utenti: si trova solo misurandolo, e infatti l'abbiamo trovato due volte da soli,
**la prima delle quali l'abbiamo archiviata come colpa nostra.**

---

## T17 · **P2** — `L4.2` avvisa falsamente su **ogni codice di uscita**, e l'avviso dice di correggere sotto un verdetto che accetta

**Trovato da Iris usando il prodotto, non leggendolo**, salvando i fatti di T16 —
06/09 02:26-02:29, `verimem save` da `C:/Users/aurel/Code/HippoAgent`, **codice di main
`ca28d8cf`** (il campo `build=` della ricevuta), non il pacchetto pubblicato.

### Cosa si vede

Ogni salvataggio con una source che contiene un codice di uscita riceve, **sotto un
`admitted` con `grounded` sopra 99**, questo:

```
admitted id=d6730be7fbab topic='verimem/t16-cli-senza-db' narrative
  L4.2 — il claim riusa un numero della fonte riferendolo a un'altra grandezza:
2 qui e' «stampando», nella fonte «prima del numero: exit»
     la cifra compare nella fonte ma parla d'altro: correggi la grandezza,
     oppure passa la fonte che sostiene questo valore
  grounded 100.0 — scored as supported by the source
```

⇒ **Il 2 del claim è lo stesso 2 della fonte, e la grandezza è la stessa** (il codice di
uscita). L'avviso è falso.

### La misura: **5 prove, e due mie ipotesi falsificate per strada**

| # | claim | fonte | `L4.2` |
|---|---|---|---|
| 1 | «…esce 0, mentre… esce 0» | `exit 0` | 🔴 avvisa — «(nessuna parola accanto)» |
| 2 | «esce 2 **stampando** Usage…» | `EXIT=2` | 🔴 avvisa — «2 qui è *stampando*» |
| 3 | «esce 2**.**» | `EXIT=2` | 🔴 avvisa — «(nessuna parola accanto)» |
| 4 | «**exits** 2.» — **in inglese** | `EXIT=2` | 🔴 avvisa — identico |
| 5 | «ha richiesto **2 s**» | `elapsed **2 s**` | ✅ **TACE** |

**Le due ipotesi che ho falsificato prima di arrivare alla causa:**
· *«è il gerundio dopo il numero»* → **no**: la prova 3, col numero a fine frase, avvisa
  uguale;
· *«è la lingua — `esce` contro `exit`»* → **no**: la prova 4, in inglese, avvisa
  **identica**, e continua a dire «(nessuna parola accanto)» mentre la parola accanto è
  `exits`.

### La causa: **due convenzioni ai due lati della stessa giuntura**

Il messaggio la dichiara da solo, e nessuno l'aveva letta fino in fondo:

```
2 qui e' «(nessuna parola accanto)»,  nella fonte «PRIMA DEL NUMERO: exit»
        ↑ nel claim cerca DOPO                    ↑ nella fonte cerca PRIMA
```

⇒ **Nel claim l'unità viene cercata dopo il numero; nella fonte, prima.** Quando l'unità
sta prima del numero — `EXIT=2`, `exit 0`, `status 1`, cioè **la forma di ogni codice di
uscita** — i due lati non possono combaciare, mai. La prova 5 lo spegne: metti l'unità
**dopo** da entrambe le parti (`2 s` contro `elapsed 2 s`) e **l'avviso sparisce**.

🔑 **Classe ④ — il bug è la giuntura**: nessuno dei due lati è sbagliato da solo.

### Perché **P2** e non meno

Il verdetto è **corretto** — il fatto entra, `grounded` alto, niente viene servito come
vero senza esserlo: **non è un P0**. Ma:

· ⚠️ **l'avviso chiede un'azione** — *«correggi la grandezza, oppure passa la fonte che
  sostiene questo valore»* — **sotto un verdetto che accetta**. Chi legge non sa se ha
  sbagliato: e se «corregge», riscrive un fatto giusto o ne salva un duplicato.
· 🎯 **E colpisce esattamente la forma di evidenza che noi raccomandiamo**: la nostra
  regola dice che la source dev'essere l'**output grezzo** — l'`EXIT=`, lo SHA, il numero
  di test passati. **Il prodotto avvisa falsamente proprio sulla forma di prova che chiede.**

### Il danno vero, che non è il singolo avviso

**Un avviso che si accende sempre smette di essere letto.** Se ogni fatto con un codice di
uscita porta un `L4.2` falso, chi scrive impara in tre giorni a scorrere oltre — e il
giorno in cui `L4.2` ha ragione, **quel giorno l'avviso non lo vede nessuno**. È la forma
speculare di *«un marcatore che non marca»*: **un marcatore che marca sempre non
distingue più niente.**

### Cosa lo abbasserebbe, e cosa lo alzerebbe

· ⬇️ **P3** se la finestra di ricerca dell'unità fosse **simmetrica per progetto** e
  documentata come «l'unità va scritta dopo il numero»: sarebbe un vincolo dichiarato, non
  un avviso falso. *Non l'ho trovato scritto da nessuna parte.*
· ⬆️ **P1** se qualcuno mostra che l'avviso **cambia anche una decisione**, non solo la
  lettura — per esempio se in una porta o in un profilo `L4.2` non è solo informativo ma
  concorre a trattenere il fatto. **Io ho visto solo `admitted`: 5 su 5.**

### Il limite di questa misura, dichiarato

**Cinque prove, tutte mie, un ambiente solo, tutte da CLI sul codice di main `ca28d8cf`.**
Non ho provato le altre due porte, e non ho letto il codice di `L4.2`: **la causa qui
sopra è dedotta dal comportamento e dal testo dell'avviso stesso**, che è precisamente il
tipo di deduzione che stanotte mi ha già ingannata una volta (la causa di T16). ⇒ **Chi
prende il ticket legga il codice prima di credere alla mia spiegazione**; il fatto
misurato — 4 avvisi falsi su 4 e un controllo che li spegne — regge comunque.

### 🔁 Il perimetro si allarga — **e la seconda forma non è un caso della prima**

**@ws4 Nadia**, 06/09 03:51 (`03e4753b74ad65aa`), **trovato usando il prodotto**: `L4.2`
avvisa falsamente **anche sugli orari**.

```
FATTO:  «Il commit ebc2bf74 ... risulta delle 03:27 del 2026-09-06.»
SOURCE: ebc2bf74 2026-09-06 03:27 test della promozione: ...

L4.2 — 27 qui e' «(solo parole grammaticali accanto)», nella fonte «test»
```

Il `27` è **dentro `03:27`**, e la fonte porta **lo stesso identico orario**. Il layer ha
spezzato l'ora, ha preso il `27` da solo, e nella fonte ha pescato `test` — la prima parola
del messaggio di commit.

#### La causa unificata, e sono **due** meccanismi diversi

| forma | cosa succede | esempio |
|---|---|---|
| ① l'unità sta **prima** del numero | il claim la cerca **dopo**, la fonte **prima**: non combaciano mai | `EXIT=2` · `exit 0` · `status 1` |
| ② **il numero è composto** | 🔑 **non esiste nessuna unità da cercare, né prima né dopo: l'unità è la POSIZIONE** | `03:27` · `2026-09-06` · `2.14.0` · `3/40` |

⇒ **La ② non è un caso particolare della ①.** Nella prima il layer guarda dalla parte
sbagliata; **nella seconda cerca una cosa che per quella forma di numero non può esistere.**
Una cura che sistema solo la finestra di ricerca **lascia in piedi tutti gli orari e tutte
le date.**

#### Perché il livello **non** sale, e cosa lo alzerebbe davvero

Il perimetro si allarga di molto — **quasi ogni fatto che salviamo porta un orario, una
data o uno SHA** — ma l'argomento del livello non cambia: **il fatto passa**, il verdetto è
corretto, nessun falso viene servito come vero. **Resta P2.**

⚠️ **E resisto alla tentazione di alzarlo perché la popolazione è più grande**: la misura
che avevo dichiarato per il P1 è un'altra — *«l'avviso cambia anche una decisione, non solo
la lettura»* — e **nessuno l'ha mostrata**. Una popolazione più grande rende l'argomento
«diventa rumore di fondo» **più solido**, non il difetto più grave.

📏 **La misura che manca, e la nomino perché non ce l'ho**: **su cento fatti realmente
salvati, quanti ricevono un `L4.2` falso?** Se è il 5% è un fastidio; se è il 60% **il
canale di avviso è morto** e allora sì che il livello cambia — non per la gravità del
singolo avviso, ma perché **un presidio che nessuno legge più non è un presidio**. ⛔ **Non
la stimo**: si conta sulle ricevute vere, non su un banco che scriverei io.

### 🔁 La classe giusta non è «orari»: è **`ETICHETTA: valore`**, e non è mia

**@ws4 Nadia, 06/09 04:06** (`915e57208f6045f4`), seconda istanza in venti minuti — e
stavolta si vede **la regola**:

```
FATTO:  «La funzione _list_tools_unfiltered ... restituisce 249 strumenti.»
SOURCE:  STRUMENTI ESPOSTI A RUNTIME: 249
         primi 3: ['sandbox_exec', 'hippo_run_task', 'hippo_consolidate']

L4.2 — 249 qui e' «strumenti», nella fonte «primi»
```

Nel **claim** l'unità sta **dopo** (*«249 strumenti»*) e il layer la trova. Nella **fonte**
l'etichetta sta **prima** (`STRUMENTI…: 249`) e dopo il numero c'è la riga successiva: il
layer piglia **`primi`** e lo confronta con `strumenti`.

⇒ **L'output di un programma ha quasi sempre la forma `ETICHETTA: valore`**, con l'unità
**prima** del numero:

```
EXIT=0    ·  PUSH_EXIT=0  ·  STRUMENTI ESPOSTI A RUNTIME: 249  ·  grounding_score=99.98
16 passed ·  1 failed, 12670 passed  ·  03:27  ·  2026-09-06  ·  torch 2.13.0+cpu
```

🔑 **Non è il caso raro: è il caso normale della nostra source**, perché la regola che ci
diamo chiede di passare **l'output grezzo**. ⇒ **Chi segue la regola riceve un avviso falso
quasi ogni volta.**

#### Cosa cambia nel livello: **resta P2, ma prende `[PROVA]`**

⚠️ **Non lo alzo a P1**, e la ragione è quella che avevo dichiarato: il P1 richiede che
*l'avviso cambi una decisione*, e **nessuno l'ha mostrato**. I fatti passano — `admitted`,
grounding 99,9 e 100.

✅ **Ma prende il marcatore `[PROVA]`**, che è la casella giusta: *ciò che rende
inaffidabile la prova che diamo*. **Un avviso che scatta quasi sempre smette di essere
letto**, e il giorno che `L4.2` ne emette uno **vero** — un numero davvero riferito a
un'altra grandezza — **non lo guarderà nessuno**. Il difetto non danneggia i dati: **consuma
l'attenzione che serve altrove**, e l'attenzione è il presidio.

#### 📏 Il tasso: quello che ho, e quello che manca

**Casi reali osservati stanotte: 7 · avvisano: 6** *(5 miei, di cui 4 avvisano — il quinto
aveva l'unità dopo il numero da entrambi i lati — più i 2 di Nadia, entrambi avvisano)*.

⚠️ **E dichiaro il bias, perché il numero da solo ingannerebbe**: i due casi di Nadia sono
arrivati **proprio perché avvisavano**; nessuno riporta un salvataggio che è andato liscio.
⇒ **`6/7` è un limite superiore su un campione auto-selezionato, non un tasso.**

📌 **La misura pulita, che nessuno ha fatto**: contare, **sulle ricevute vere di tutte e
otto**, su cento fatti salvati quanti ricevono un `L4.2` falso. **Non la stimo**: la
plausibilità è alta *(la forma `ETICHETTA: valore` è la norma negli output)*, ma una ragione
teorica per cui un tasso dovrebbe essere alto **non è un tasso**.

### 🔁🔴 La regola vera è di @ws4 Nadia, e la mia era un caso particolare — **letto dal testo dell'avviso invece che dal comportamento**

**Terza istanza, 06/09 05:36** (`ff9399aef7459d90`), trovata da lei salvando l'ultimo fatto
della notte:

```
CLAIM:  «…il braccio a etichette casuali segna 30/100 astensioni mai viste
         sbagliate e quello con i dati 28/100.»
FONTE:  «① scorciatoia: 28/100 astensioni mai viste sbagliate ⛔ HA IMPARATO LA FORMA»

L4.2 — 28 qui e' «prima del numero: dati», nella fonte «astensioni»
```

🔑 **Qui l'unità sta DOPO nella fonte e PRIMA nel claim — l'esatto contrario dei miei
casi — e l'avviso scatta lo stesso.**

⇒ **La regola non è** *«nel claim cerca dopo, nella fonte prima»*, come avevo scritto:
**`L4.2` cerca l'unità SOLO A DESTRA del numero, in ENTRAMBI i testi**, e sbaglia ogni
volta che l'unità sta a sinistra **in uno qualsiasi dei due**.

```
EXIT=2                              l'etichetta e' a sinistra   (output)
STRUMENTI ESPOSTI A RUNTIME: 249    l'etichetta e' a sinistra   (output)
03:27                               l'unita' e' la POSIZIONE    (orario)
«…e quello con i dati 28/100.»      l'unita' e' a sinistra      (claim)   <- il verso opposto
```

#### 🪞 Come ci sono arrivata sbagliando, ed è la forma della notte

**Ho preso il testo dell'avviso per la logica del layer.** Il messaggio dice *«nella fonte:
prima del numero: exit»* — ma quello è **ciò che l'avviso RIPORTA di aver trovato**, non
**dove ha cercato**. Nel ticket avevo persino dichiarato *«la causa è dedotta dal
comportamento e dal testo dell'avviso stesso»*: **la dichiarazione c'era, il caso che la
falsificava no.** Non ho cercato il verso opposto; l'ha trovato lei **usando il prodotto**.

⇒ È la dodicesima occorrenza di *una rappresentazione della cosa invece della cosa*, e
stavolta la rappresentazione era **il messaggio d'errore del prodotto che sto misurando**.

#### 📌 Perché questa correzione serve a chi scrive la cura

**Una cura che guardasse solo a sinistra nella FONTE passerebbe i primi due casi e
fallirebbe il terzo.** I casi riproducibili sono **tre**, e il terzo copre il verso
opposto: **vanno tutti e tre nel RED.** Tutti `admitted` (grounding 99,9 · 100 · 99,7) —
**resta rumore, non un blocco**, e il livello resta `P2 [PROVA]`.

---

## T18 · **P1** — `include_superseded` è ingoiato in silenzio quando si combina con `as_of`

**Trovato da @ws2 Giano** (`9413be3cd9a45507`), misurato da lui sul codice; **il livello è
mio**, e per darlo ho dovuto misurare una cosa che ridimensiona **un numero mio**.

### Il difetto

```
SENZA as_of, include_superseded=False : ['nuovo']
SENZA as_of, include_superseded=True  : ['nuovo', 'vecchio']    ← funziona
CON   as_of, include_superseded=False : ['nuovo']
CON   as_of, include_superseded=True  : ['nuovo']               ← 🔴 IGNORATO
```

**Causa**, `verimem/client.py`: il ramo `as_of` chiama `recall_as_of(...)`, che
`include_superseded` **non lo accetta nemmeno**. ⚠️ La **CLI eredita** (`verimem recall`
passa da `m.search`), *non verificato ma atteso — lo dichiara Giano stesso*.

### Perché **P1** e non P0

La riga del P0 è *«il prodotto serve come vero — o **tace** — qualcosa che chi legge non ha
modo di controllare»*. Qui chi chiede il passato **coi superati** riceve il passato
**senza**: **quello che riceve è vero, gliene manca un pezzo.** È un'omissione, non un
falso servito come vero — ed è la differenza con **D-6**, dove chi chiede il passato riceve
**il presente**, cioè un dato sbagliato.

📏 **La misura che lo alza a P0**: un caso in cui l'assenza del superato fa **concludere il
falso** — *«non è mai esistito un altro fornitore»*, *«questo valore non è mai cambiato»*.
Se qualcuno lo mostra, sale.

### 🪞 La misura che decideva il livello, e il numero mio che ha ribaltato

Se il ramo `as_of` ingoiasse **più** parametri, non sarebbe un difetto ma **una superficie
rotta**, e il livello cambierebbe. Da `inspect` — esecuzione, non lettura:

```
Memory.search()  accetta 8 parametri oltre a query
recall_as_of()   ne accetta 2 (piu' query/when/sm)
⇒ CINQUE non hanno dove andare: deep · history_hops · include_superseded ·
                                min_relevance · with_history
```

🔴 **Quel `5` è vero in ogni cifra e completamente fuorviante**: un parametro può essere
applicato **dopo** il ramo e funzionare lo stesso. Misurato col comportamento, e col
controllo positivo obbligatorio (*il parametro morde da solo?*):

|  | senza `as_of` | con `as_of` | |
|---|---|---|---|
| `min_relevance` | 3 → 0, morde | 3 → 0, morde | ✅ **passa** |
| `k` | 3 → 1, morde | 3 → 1, morde | ✅ **passa** |
| `include_superseded` | 3 → 3, **non morde da solo** | — | ⚠️ **NON MISURATO** |

⇒ **Zero ingoiati fra quelli che ho saputo far mordere.**
🔑 **Se avessi pubblicato il `5` come conteggio di difetti avrei gonfiato di cinque volte un
difetto singolo** — con un numero vero. *Un numero letto da una firma non è una misura del
comportamento.*

### 🔁 E venti minuti dopo la radice si è allargata — ma la mia misura la DELIMITA

Il lead ha unificato due reperti (`1398019dc90ff377`): `include_superseded` ingoiato
(**Giano**) e **scaduti esclusi senza avviso** (**Aldo**) hanno **la stessa radice** — *il
ramo `as_of` **sostituisce** i filtri invece di **comporli***. Due sintomi, una cura sola,
owner Giano+Aldo.

⇒ **Avevo scritto «è un caso, non una classe»: era prematuro.** È **una classe**, e la mia
misura serve a dire **quanto è larga**: non tutti i parametri cadono — `min_relevance` e `k`
**passano**, misurati — **cadono i filtri sullo STATO del fatto** (superato, scaduto), che
sono esattamente quelli che `as_of` dovrebbe **comporre** con la sua condizione temporale
invece di scavalcare.

📌 **Il livello resta P1 per entrambi i sintomi**, e per la stessa ragione: chi chiede
riceve **meno**, non il falso. **La misura che li alza a P0 è la stessa**: un caso in cui
l'assenza non dichiarata fa **concludere il falso**.

### 🔗 Il terzo sintomo, ed è di specie diversa: **la stessa grandezza con due definizioni**

**@ws6 Aldo, 06/09 03:49** — *lo stesso fatto, nello stesso istante*: `recall` **lo toglie
perché SCADUTO**, e `hippo_assess_fact_freshness` **risponde `fresh`**, perché lì
«expired» significa un'altra cosa. Il lead lo mette dentro T18 e la nota è mia.

⇒ **Non è lo stesso meccanismo degli altri due.** I primi due sono un filtro **perso**;
questo è **una parola che vuole dire due cose in due punti del prodotto**. È la **classe ①**
— *una copia invece della superficie unica* — applicata a una **definizione** invece che a
del codice.

🔑 **E per l'utente è peggio del filtro perso**, perché la contraddizione è **visibile e
non spiegata**: chiede se un fatto è fresco, gli si dice **sì**; chiede quel fatto e non
gli arriva **perché è scaduto**. Nel caso dei filtri riceve meno senza saperlo; qui
**riceve due risposte che non possono essere entrambe vere**, e nessuna delle due è
sbagliata dal punto di vista di chi l'ha scritta.

📌 **Cosa deve produrre la cura, oltre al codice**: **una definizione sola di «scaduto»,
scritta**, e le due porte che la usano. ⚠️ Se invece si decide che sono davvero due
grandezze diverse — la validità del fatto e la freschezza del suo contenuto — allora
**devono avere due NOMI diversi**, perché oggi l'utente non ha modo di sapere che
`expired` non è `expired`.

### ⚠️ E il terzo rosso non valido della notte, nello stesso banco

Al primo giro ho passato un `datetime` a `as_of`. **Vuole epoch seconds, e la docstring lo
dice** (`as_of (epoch seconds)`): `TypeError`, il banco ha contato `-1` e **ha stampato
«INGOIATO» su un errore mio**. Non un difetto del prodotto — **il mio uso sbagliato di un
parametro documentato**.

🔑 **E la parte che conta**: **dieci minuti prima avevo aggiunto esattamente questo presidio
a un altro banco** — *«se il presupposto del verdetto non si è verificato, esci NON
MISURATO»* — **e non l'ho messo in questo.** Ho curato l'istanza invece della classe, che è
la classe ① che segnalo nei documenti degli altri. Adesso il presidio è di classe:
**qualsiasi eccezione dentro la misura fa uscire `NON MISURATO`**, perché un'eccezione mia
non è un risultato del prodotto e **contarla come zero fabbrica un rosso**.

*(banco: `banchi/ws7-quanti-parametri-ingoia-as-of.py`)*

---

## T19 · **P0** — il fatto entra cieco, la ricevuta dice `admitted`, e la ricerca **fabbrica un'assenza**

**Misurato da @ws5 Tara**, 06/09 04:45 (`96b6e644be48533b`), in sola lettura sullo store.
**Il livello è mio, e questo è il P0 più puro della notte.**

### Cosa succede

```
criterio: VUOTO = embedding IS NULL OR LENGTH(embedding)=0
ULTIME 3h:      VUOTI=13   PIENI=53    (19,7%)
CORPUS INTERO:  VUOTI=13   PIENI=17834 ( 0,1%)
```

**Tutti e tredici i fatti ciechi dell'intero corpus sono stati scritti stanotte, in
trentadue minuti, da cinque persone diverse.** Un fatto sano pesa 3072 byte; questi pesano
**0**, con `embedding_model` vuoto.

Il `save` **riesce**: `admitted`, grounding **99,97**. E poi:

```
sotto_il_pavimento: score_migliore 0.0
«nessun risultato supera la soglia di rilevanza calibrata su questo corpus:
 probabilmente la risposta NON e' in memoria»          ← su un fatto CHE C'E'
```

### Perché **P0**, e perché è più puro degli altri quattro

La riga del P0 è: *il prodotto serve come vero — o **tace** — qualcosa che chi legge non ha
modo di controllare.* 🔑 **Qui non tace: AFFERMA.** Dice *«probabilmente la risposta non è
in memoria»* su un fatto che è in memoria. **Un'assenza fabbricata** — ed è **esattamente la
risposta che questo prodotto esiste per rendere affidabile**.

⚠️ **E la distinzione che decide il ticket, perché la causa può essere ambientale**: che il
daemon di encode non risponda **può** essere un problema locale. **Ma due comportamenti sono
del prodotto, in qualunque ambiente:**
1. **la ricevuta dichiara `admitted` senza un campo che dica «senza embedding»**. Il
   prodotto *lo dice* — `store: encode delegate unavailable` — ma in **una riga di log che
   scorre via**, non in un campo della ricevuta: chi automatizza la scrittura non lo vede
   mai, e **la ricevuta è il contratto**;
2. **la ricerca dichiara un'assenza** invece di dire *«ho fatti che non posso confrontare»*.

⇒ **Il ticket non è «il daemon cade»: è che il prodotto dica di sì a una scrittura mutilata
e poi neghi ciò che contiene.**

### La seconda faccia: **`health` dice `ok` mentre il 100% delle scritture è cieco**

```
status ok · episodes_db ok · skills_store ok · semantic_db ok · disabled_flag false
```

**Non ha un campo per il daemon di encode.** ⇒ Il comando che l'utente usa **proprio per
sapere se sta bene** dice che sta bene. È la forma *«una capacità spenta non emette
segnale»*, applicata al misuratore di salute.

### 🪞 E una cosa che riguarda me, e non è un aneddoto

**Alle 04:39 stavo per salvare due fatti** (T17 e il reperto sul README). **Non l'ho fatto
solo perché gli slot del giudice erano occupati** e ho deciso di non interferire con una
misura sul percorso critico. ⇒ **Sarebbero entrati ciechi**, e me ne sarei accorta domani
cercandoli.

🔑 **Non è stato un presidio: è stata una coincidenza.** Fra le 04:04 e le 04:36 **non
esisteva niente che fermasse una scrittura cieca** — non la ricevuta, non `doctor`, non
`health`. Cinque di noi ci sono cascate. **La misura di quanto è grave un difetto è anche
questa: chi lo ha evitato, lo ha evitato per caso?**

### ⏱️ Otto minuti dopo: **23, non 13** — e il righello ovvio dice ancora zero

**Ricontato da me alle 04:53**, in sola lettura (`mode=ro`) sullo store, dopo che @ws6 Aldo
aveva **ritirato** l'allerta scrivendo *«sul corpus 0 fatti muti su 17855»*:

```
TOTALE                                17857
criterio di Aldo  (embedding IS NULL)      0     <- vero, e CIECO
criterio di Tara  (IS NULL OR LENGTH=0)   23
  di cui NON nulli ma di lunghezza 0      23
```

⇒ **Il ritiro era sbagliato, e il numero sta CRESCENDO**: 13 alle 04:45, **23 alle 04:53**
— **+10 in otto minuti.** Non è un incidente chiuso.

🔑 **E la parte che vale oltre il ticket**: la trappola di `IS NULL` **era già scritta nel
messaggio di Tara delle 04:45**, come prima delle sue due avvertenze. **Otto minuti dopo lo
stesso righello ha prodotto lo stesso zero, e stavolta è diventato un ritiro pubblico** —
con la riga *«se avete cambiato qualcosa per colpa del mio messaggio, rimettetelo com'era»*,
che avrebbe rimesso cinque persone a scrivere fatti ciechi.
⇒ **Una trappola documentata non protegge chi non ha letto il documento**, e fra otto
istanze che lavorano in parallelo il tempo fra «documentato» e «letto» è dove succedono le
cose. 📌 *E vale anche per me: due misure che si contraddicono sullo stesso oggetto non si
mediano — si rifanno con entrambi i criteri, che è come ho tenuto in piedi questo P0 invece
di ritirarlo.*

✅ **Cosa NON cade del ritiro di Aldo, e va tenuto**: il suo A/B *«con e senza
`HIPPO_ENCODE_DELEGATE_ONLY`, embedding 1/1 in entrambi»* **resta vero**. ⇒ **Il difetto non
è sistematico su ogni scrittura**, dipende dallo stato del daemon — ed è precisamente perché
i muti sono 23 e non tutti.

### ✅ 04:59 — **DANNO CHIUSO: zero muti, e i fatti sono stati RIPARATI, non cancellati**

Rimisurato da me (`mode=ro`) appena @ws5 Tara ha annunciato il daemon giusto:

```
ORA 04:59:51 · TOTALE 17867 · MUTI (IS NULL OR LENGTH=0): 0

e82ba2ca5ddd: len=3072  model='intfloat/multilingual-e5-base'
d3908717349c: len=3072  model='intfloat/multilingual-e5-base'
10148b5566db: len=3072  model='intfloat/multilingual-e5-base'      <- gli stessi id
2e9b3f6a211e: len=3072  model='intfloat/multilingual-e5-base'         che alle 04:53
37f689d519c1: len=3072  model='intfloat/multilingual-e5-base'         erano a 0 byte
```

**La curva intera**: `13` (04:45) → `23` (04:53) → `26` (picco, @ws4) → **`0`** (04:59).
⇒ **Nessun fatto è andato perso**, e chi legge questo ticket domani deve saperlo subito.

🔴 **Ma il ticket NON cade, e il livello resta P0.** La riparazione ha tolto **il danno**,
non **il difetto**: per trentacinque minuti il prodotto ha detto `admitted` a fatti che non
sarebbero mai tornati, e poi ha risposto *«probabilmente la risposta non è in memoria»* su
fatti che aveva.

🔑 **E il dato che vale più di tutti, da Product Owner**: l'incidente si è chiuso in
quindici minuti **perché una di noi ha guardato il database**. **Nessun presidio del
prodotto lo ha segnalato** — non la ricevuta (`admitted`, grounding 99,97), non `doctor`,
non `health` (`status ok`). ⇒ **Un utente solo, senza otto persone che si parlano, non
avrebbe avuto nessuno che glielo diceva.** È questo che tiene il livello a P0, non il
numero dei fatti.

### Le due trappole del righello, che valgono da sole

· **`embedding IS NULL` NON li trova**: il campo non è nullo, è **vuoto**. Il primo
  conteggio di Tara stampava `SENZA-EMBEDDING=0` **con il controllo positivo acceso** — era
  a un passo dal pubblicare «nessun problema». Il criterio giusto è
  `IS NULL OR LENGTH(embedding)=0`.
· **`hippo_health` dice `ok`** (sopra). *E conta `facts: 15487` mentre la tabella ne ha
  `17847`: due denominatori diversi, non indagato.*

### Cosa lo abbasserebbe

⬇️ **P1** se la ricevuta portasse un campo esplicito — `embedding: none`, o uno `status`
diverso — **e** la ricerca dicesse *«N fatti non confrontabili»* invece di negare. Allora
sarebbe lento e imperfetto, ma **onesto**, e chi automatizza potrebbe controllarlo.
📌 **Il backfill esiste** (`hippo_backfill_embeddings`) e i tredici id sono nel messaggio di
Tara: **non è una perdita definitiva** — ma nessuno lo saprebbe senza questa misura.