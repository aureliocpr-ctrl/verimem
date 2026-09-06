# I tre percorsi d'uso — definizione, criterio di arrivo, difetti che bloccano

**Livello 2 del disegno esploso, «l'utente seduto alla scrivania».** Iris (ws7,
Product Owner) definisce e dà la gravità; **Giano (ws2), Tara (ws5) e Marie
(ws1) eseguono e cronometrano.** `2026-09-06`.

⚠️ **Il regime NON è uniforme, e questa riga prima prometteva il contrario**
(*«tutto dal pacchetto pubblicato, mai dal repo»*): **U-B è stato eseguito su
`origin/main` (`95e886bb`)**, non dal pacchetto. Non lo invalida — **lo
qualifica**, ed è la stessa distinzione che applico a `doctor`: un esito su main
dice cosa fa il codice, non cosa riceve chi installa. **Ogni percorso dichiara il
proprio regime nella sua intestazione**; dove non è dichiarato, è il pacchetto.

---

## Le tre regole di questa pagina

**① Un percorso ha un criterio di arrivo scritto PRIMA di eseguirlo.** Senza,
«funziona» vuol dire quello che vuole chi lo scrive. Il criterio qui sotto è una
frase che si può solo confermare o smentire — non una sensazione.

**② Si elencano solo i difetti che BLOCCANO quel percorso.** Un difetto che
esiste ma non impedisce di arrivare in fondo **non appartiene a questa pagina**:
sta in `GRAVITA-DIFETTI.md` e basta. Una lista che mette insieme un muro e un
inciampo non serve a decidere niente.

**③ Eseguito ≠ supportato.** Un percorso è **eseguito** quando qualcuno di noi
ci arriva in fondo. È **supportato** quando ci arriva **su tutte e tre le porte**
(SDK, CLI, MCP) e **senza sapere dove guardare** — cioè senza conoscere i nostri
aggiramenti. **Al 06/09 tutti e tre sono ESEGUITI** (U-A da Giano il 04/09, U-B e
U-C da Iris nella notte fra il 5 e il 6) e **nessuno dei tre è SUPPORTATO**:
nessuno è stato provato su tutte e tre le porte, e nessuno da qualcuno che non ci
conosce.

---

## U-A · **Un agente che lavora**

**Chi è.** Un agente che chiude compiti e scrive in memoria quello che ha fatto,
e che rileggerà se stesso fra una settimana. È il caso per cui il prodotto esiste.

**Cosa fa, passo per passo** — misurato da Giano sul pacchetto `0.7.6` da PyPI,
store isolato, il **04/09**:

| # | passo | esito |
|---|---|---|
| 1 | registra un fatto **con la sua fonte** | ✅ |
| 2 | lo richiama | ✅ |
| 3 | **il mondo cambia** (il fornitore di pagamenti migra) | ✅ |
| 4 | richiama di nuovo | ✅ **solo il corrente** (`nuovo: True · vecchio: False`) |
| 5 | chiede la **storia** (`--with-history`, `include_superseded`) | ✅ racconta la transizione |
| 6 | chiede **lo stato di allora** (`as_of`) | 🔴 **la porta MCP risponde col presente** |
| 7 | prova a scrivere una **falsità** | ✅ `quarantined`, `moat`, grounding 0.19 |
| 8 | rifà la stessa domanda **dalla CLI** | ✅ serve il corrente, non il superato |

**Tempo**: il giro intero **40 s** (seconda esecuzione), 62 s la prima. Prima
scrittura con fonte 16,2 s · seconda 12,8 s · richiamo 0,1 s · CLI 1,5 s.
⚠️ **Regime**: SDK, nessun daemon, **modello del giudice già in cache** (28 GB
sulla macchina di chi ha misurato). Non è il regime di chi installa oggi.

**Criterio di arrivo**: *gli otto passi arrivano in fondo e le tre porte danno la
stessa risposta alla stessa domanda.*
**Stato: ESEGUITO, NON PASSATO** — 7 passi su 8, e il passo 6 fallisce su due
porte su due.

**Difetti che lo BLOCCANO:**
- **D-6 · P0** — entrambe le porte MCP accettano `as_of` e lo ignorano **senza
  dirlo**: chi chiede il passato riceve il presente e non ha modo di
  accorgersene. ⚠️ **La cura è in `main` da `db7dfd11`** — quindi **il passo 6 qui
  sotto è marcato rosso su un albero che non esiste più**, e il conteggio «7 su 8» è
  quello di prima. **Si chiude rifacendo il passo, non correggendo la riga.**
- **T1 · P0** — se il primo passo lo fa dalla porta MCP a giudice freddo, la
  risposta arriva dopo **313-903 s**: contiene la spiegazione giusta (identica a
  quella della CLI, misurata da Tara su main e sulla 0.7.6), ma **il client ha
  smesso di ascoltare molto prima**, e in fondo all'attesa il fatto può entrare
  `judged=False`. *(cura in corso, finestra ①)*
- **T9 · P1** — se un fatto è scaduto, `facts_recall` e `ask` non lo dichiarano:
  l'agente riceve meno di quello che c'era e non sa perché. *(finestra ③)*

**Non lo bloccano** (e per questo non stanno qui): il prefisso `hippo_`, le note
interne, le chiavi in italiano, i 249 strumenti, gli id mancanti dalla CLI.

---

## U-B · **Un team su uno store**

**Chi è.** Più agenti — o più persone — che scrivono nello stesso store, e
qualcuno che dopo deve capire **cosa c'è dentro e da dove viene**. È il caso in
cui un errore non resta privato.

**Cosa fa, passo per passo** — *definito il 05/09, **eseguito il 06/09** (l'esito è
subito sotto la tabella):*

| # | passo | cosa dimostra |
|---|---|---|
| 1 | **due scrittori diversi** scrivono nello stesso store | lo store regge più mani |
| 2 | il secondo **legge il fatto del primo** e vede **da chi viene** | la provenienza c'è su ogni lettura |
| 3 | il mondo cambia: uno **corregge il fatto dell'altro** | la revisione è esplicita, non un sovrascrivere |
| 4 | un terzo legge e riceve **solo il corrente**, e può chiedere la storia | nessuno eredita il vecchio per caso |
| 5 | qualcuno chiede **cosa è successo** (l'audit) | il registro dice chi ha fatto cosa |
| 6 | un fatto **scade** e qualcuno legge | l'assenza viene **dichiarata**, non subita |

**Criterio di arrivo**: *un quarto che non era presente ricostruisce dallo store
chi ha scritto cosa, quando, e perché il valore corrente è quello — senza
chiedere niente a nessuno.*

### 🟢 **ESEGUITO** — 06/09 00:00, Iris, su `origin/main` (`95e886bb`), con la fonte e il giudice acceso

| # | passo | esito |
|---|---|---|
| 1 | due scrittori diversi sullo stesso store | ✅ |
| 2 | il secondo vede **da chi viene** il fatto del primo | ✅ `writer_principal` = `anna`/`bruno`, valorizzato e giusto |
| 3 | uno **corregge** il fatto dell'altro | ✅ la correzione è **giudicata**: `cross_encoder`, score 99,45, tier `high` |
| 4 | un terzo riceve **solo il corrente** | 🔴 **NO su due porte su due**, e **la causa è una sola: il write.** SDK: i due fatti coesistono, `superseded_by` **nullo su entrambi**. **MCP, misurato il 06/09 03:03** (albero `ca28d8cf`, prima della cura di T14): la lettura restituisce **2 fatti**, Adyen **e** Stripe — *«due fornitori di pagamento per lo stesso servizio, e nulla dice quale vale»*. ⚠️ **La porta NON ha colpa, e l'ho verificato dopo che @ws2 Giano me l'ha fatto notare**: `include_superseded` è spento di default e presidiato, e con una supersessione **creata esplicitamente** la stessa lettura torna **1 fatto solo** (banco `banchi/ws7-la-porta-mcp-espone-superseded-by.py`). ⇒ Se ne arrivano due è perché **per lo store non sono «corrente + superato», sono due fatti distinti**: è legittimo che tornino entrambi, ed è **T14** — il difetto sta in chi non ha creato la relazione. *(banco `banchi/ws7-u-b-passo-4-la-lettura-dalla-porta-mcp.py`)* |
| 5 | l'**audit** dice cosa è successo | 🔴 **misurato dalla porta MCP il 06/09**: il registro dice **cosa** (`tool`) e **non chi** (`caller_pid` è un processo, non un'identità → **T15**), e **omette le chiamate rifiutate** (3 chiamate, 2 righe → **T6**, ora verificato) |
| 6 | un fatto **scade** e chi legge lo sa | ✅ `esclusi_perche_scaduti = {'esclusi': 1, 'nota': "…la loro validità è SCADUTA…"}` |

**Stato: ESEGUITO, NON PASSATO — e ora il criterio è DECIDIBILE.**

🪞 **Prima però correggo il criterio, che avevo scritto male io.** Avevo elencato «serve
2 + 4 + 5». **Il 5 non serve alla frase**: *«un quarto ricostruisce dallo store chi ha
scritto cosa, quando, e perché il valore corrente è quello»* — **chi/cosa/quando** si
ricostruisce **dai fatti** (passo 2, verde: ogni fatto porta `writer_principal`); il
**«perché il corrente è quello»** dipende dal **passo 4**. L'audit misura le **azioni**, che
sono un'altra cosa e non stanno in quella frase.
⇒ **Il criterio chiede 2 + 4.** Il 2 passa, **il 4 no**: **U-B non arriva in fondo, e il
responsabile è il passo 4 (T14).**
⇒ **Il passo 5 resta rosso e conta lo stesso** — come **T6** e **T15**, che riguardano cosa
un team può ricostruire delle *azioni*. Non entra nel criterio, entra nella lista dei
difetti che bloccano.

**L'ho scoperto solo eseguendo il passo che credevo decisivo.** Un criterio scritto prima
non è automaticamente un criterio giusto: **va riletto contro la frase che dice di
misurare.**

⚠️ **Prima di questo esito ho falsificato il mio stesso banco sei volte**, e tre dei
«difetti» che stavo per attribuire al prodotto erano miei: leggevo **i nomi** dei campi
invece dei valori, il **JSON serializzato** invece dell'oggetto, il registro di **una
porta** usandone un'altra — più un **regime** di cui non avevo tracciato le conseguenze
(senza fonte il giudice non gira, e *la revisione è il gate*), un **albero** fermo al
04/09, e un **fallback** che faceva funzionare un conteggio per caso. **Ogni volta avevo
guardato una rappresentazione della cosa invece della cosa.** Il dettaglio nel banco.

**Difetti che lo BLOCCANO:**
- 🔴 **T14 · P0 su MCP · P1 su SDK** — **è il difetto che manda a vuoto il criterio**, ed
  è quello che il passo 4 ha trovato: dopo una correzione ammessa a 99,45 **il fatto
  vecchio non viene superato affatto**, e il gate *decide* che i due coesistono
  (`L3-coexistence`: `_entita_diverse` scambia **il valore che cambia** per un soggetto
  diverso — causa di Aldo). **Su MCP il verdetto non arriva nemmeno**: `anti_confab_warnings`
  vuoto, la stringa `L3-coexistence` assente. ⚠️ *Mancava da questa lista fino alle 02:45,
  mentre dieci righe sopra era già scritto che il responsabile è lui — trovato da @ws4
  Nadia incrociando la pagina con `GRAVITA-DIFETTI`.*
- 🔴 **T16 · P0** — la riga che il Quickstart insegna, `Memory("memoria.db")`, è **relativa
  alla CWD**: in un percorso che è letteralmente *«più mani sullo stesso store»*, **due
  cartelle diverse aprono due store diversi**, e la CLI risponde `no facts found` con
  `exit 0` senza dire dove ha guardato. **Blocca U-B prima ancora del passo 1**, se le mani
  non partono dalla stessa cartella.
- **T6 · P1** — le chiamate **rifiutate per validazione non entrano** in
  `mcp_audit.log`. Un registro che omette i rifiuti **afferma per omissione** che
  è andato tutto bene. ✅ **Verificato da me il 06/09**: tre chiamate, due righe,
  la rifiutata manca — e il campo `error` esiste ed è `""`.
- **T15 · P1** — l'audit dice **cosa** (`tool`) e **non chi**: `caller_pid` è un
  numero di processo, non un'identità. Due agenti nello stesso processo sono
  indistinguibili.
- **T9 · P1** — il passo 6 è esattamente questo difetto: `facts_recall` e `ask`
  non dichiarano ciò che la scadenza ha tolto, mentre SDK e CLI sì.
- **D-6 · P0** — il passo 4 («cosa diceva allora») sulla porta MCP risponde col
  presente. ⚠️ **La cura è in `main` da `db7dfd11`** (più `0ae26ca5` e il presidio
  `79625479`), non «sul ramo» come diceva questa riga: **l'esito qui sotto è di prima
  della cura e va rifatto, non riscritto.**
- **T10 · sospeso** — se la promozione documento→fatto non applica il criterio
  del cancello, in uno store condiviso entra un fatto **per una seconda porta**
  che nessuno ha controllato. *Il livello è sospeso finché il codice non ha un
  autore, non perché il difetto sia dubbio.*

✅ **Questo percorso ORA è stato eseguito** (06/09 00:00, vedi sopra), e la previsione
che avevo scritto il 05/09 va aggiornata con quello che è successo davvero:
· **T9 (scaduti muti) NON blocca U-B**: sull'SDK la scadenza **è dichiarata** — la cura
  `50f4e05b` funziona, e l'ho verificata senza cercarla. Resta aperto sulla porta MCP.
· **T6 (l'audit cieco sui rifiuti) è CONFERMATO**, e l'ho misurato io dalla porta giusta
  il 06/09: tre chiamate dalla porta MCP, **due righe** nel registro, **la rifiutata
  manca** — e il campo `error` esiste ed è vuoto. *(Era una previsione fino alle 00:37.)*
· 🆕 **T15**, che nemmeno era nella lista: **l'audit dice cosa e non chi** (`caller_pid` è
  un processo, non un'identità).
· **D-6 e T10 restano previsioni** per U-B: non li ho esercitati.
· 🆕 **T14 è il difetto che il percorso ha trovato**, e non era nella mia lista: dopo una
  correzione con fonte **il fatto vecchio non viene superato affatto**.
🔑 **Tre previsioni su quattro non sono state confermate dall'esecuzione, e il difetto
vero non era fra quelle.** È il motivo per cui una colonna dedotta dai reperti va marcata
come previsione: **non perché sia sbagliata, ma perché guarda dove abbiamo già guardato.**

---

## U-C · **Da zero in dieci minuti**

**Chi è.** Qualcuno che ci ha appena trovati, non ha mai sentito parlare di noi,
e vuole sapere in dieci minuti se il prodotto fa per lui.

**Cosa fa, passo per passo:**

| # | passo | criterio |
|---|---|---|
| 1 | `pip install verimem` | arriva, e sa quanto pesa **prima** di lanciarlo |
| 2 | `verimem warmup` | sa **perché** deve farlo prima di scrivere |
| 3 | `verimem doctor` | gli dice se è a posto, e **quale store** sta guardando |
| 4 | il Quickstart del README, con il suo `assert` | la falsità non torna: **vede** la promessa |
| 5 | una scrittura **sua**, con la sua fonte, e un richiamo | ha capito **cosa ci farebbe** |

**Criterio di arrivo**: *in dieci minuti l'utente ha visto con i suoi occhi il
prodotto rifiutare una falsità, e sa dire a voce cosa fa e a chi serve — senza
aver aperto le altre 780 righe del README.*

🔑 **Il passo 5 non c'era, e l'ho aggiunto io.** Il Quickstart dimostra che il
prodotto funziona sul suo esempio; **non dimostra che l'utente abbia capito a
cosa gli serve**. Un percorso di valutazione che finisce con un `assert` verde
misura noi, non lui.

### 🟢 **MISURATO** — 06/09 01:19, Iris, ambiente **ripulito di nove variabili**

    0 creo il venv        7,5 s    1 pip install verimem (PyPI)  280,8 s
    2 verimem warmup     28,3 s    3 verimem doctor                7,8 s  exit=1
    4 il Quickstart      16,3 s    5 una scrittura SUA + richiamo 16,2 s
    ⇒ TOTALE 357 s = 5,9 MINUTI · dentro i dieci

**Il numero era dichiarato «da rifare»** perché i 6,8 minuti di Tara giravano con
`ENGRAM_DATA_DIR` ereditata. 🔴 **Controllando prima di misurare, le variabili sporche non
erano una: erano NOVE** — fra cui due che puntavano allo store di Aurelio e
`HIPPO_ENCODE_DELEGATE_ONLY` (quella di T1). Il banco **le toglie tutte**: *la trappola nota
si evita, la trappola nuova si evita solo togliendo la classe.*
I due numeri (6,8 e 5,9) **non sono in contraddizione**: regimi diversi, entrambi dentro i
dieci minuti.

🟢 **Il passo 4 passa DAVVERO, e ho dovuto verificarlo perché il mio assert era debole.**
Stampava *«la falsità non torna, risultati serviti: 0»* — e **zero risultati soddisfano un
assert che cerca l'assenza di una stringa**, qualunque ne sia la ragione. Verificato lo
**stato**: `status=quarantined · quarantined_by=moat · grounding=0.69`. **Il prodotto fa la
cosa giusta; era il mio assert a non misurarla.**

🔁 **Aperto come `T8-bis` alle 01:36** — *e il 06/09 alle 07:30 è salito a **P1**: non era
curato su main, e il difetto vero è che l'exit code di `doctor` non discrimina* (`570f98f5`,
e la riga nella scheda con
`fffb56c3`) — *questa sezione l'ha dichiarato «aperto e non chiuso» per tredici minuti
dopo la chiusura; l'incoerenza l'ha trovata @ws4 Nadia incrociando gli orari dei commit.*
`verimem doctor` esce **1 sul pacchetto 0.7.6** dopo un warmup riuscito, per
`relevance-floor floor 0.0000 computed on 0 facts`, e **propone `fix: verimem warmup`, cioè
il comando appena eseguito**: è un avviso su uno **store vuoto**, non su un'installazione
rotta. **Su `main` esce 0** con lo stesso store e lo stesso ambiente: **già curato lì**.

**Difetti che lo BLOCCANO:**
- **T1 · P0** — se salta `warmup` e scrive con fonte dalla porta MCP, la
  risposta arriva dopo 313-903 s: **i dieci minuti finiscono su una sola
  scrittura**, e la spiegazione che il prodotto ha preparato per lui arriva
  quando il suo client ha già rinunciato.
- 🔴 **T16 · P0** — è **la riga del passo 5**: `Memory("memoria.db")` scrive nella cartella
  corrente, la CLI legge il data dir e risponde `no facts found` con `exit 0`. **Chi segue
  il nostro Quickstart alla lettera non rilegge quello che ha appena scritto**, e non ha
  modo di capire perché. ✅ La riga che funziona su entrambe le porte, misurata, è
  **`Memory()` senza argomento**.
- *(nient'altro, oggi.)* T7 (1160 MB) è **dichiarato**; **T8 è ritirato** perché il
  `doctor` che esce 1 lo fa **su uno store vuoto** — ⚠️ **e NON è curato su main**
  (`doctor.py` invariato fra `v0.7.6` e main, verificato il 06/09): il ticket è
  **`T8-bis · P1`**, e il difetto è che **l'avviso sulla copertura del giudice non si
  spegne mai** (`giudicati/totali`, cumulativo). *Formulazione rifatta il 06/09: la mia
  diceva «l'exit code non discrimina» ed era falsa — `cli.py:721` dichiara `0/1/2`.*

---

## Cosa manca a questa pagina, scritto dentro la pagina

1. ~~U-B non è mai stato eseguito~~ → **fatto il 06/09**: il criterio è **decidibile e
   non raggiunto**, e il responsabile è il passo 4 (T14).
2. ~~Il tempo di U-C va rifatto in ambiente pulito~~ → **fatto il 06/09**: **5,9 minuti**
   con **nove** variabili d'ambiente rimosse, contro 6,8 col regime ereditato. **Entrambi
   dentro i dieci**, ed entrambi restano scritti col loro regime.
3. **Nessuno dei tre percorsi è stato eseguito su tutte e tre le porte.** U-A è
   SDK+CLI con un controllo su MCP; **U-B è SDK con il passo 5 dalla porta MCP**;
   U-C è CLI. Finché non lo sono, «supportato» non si può scrivere.
   *(L'elenco ne contava due su tre dicendo «tutti e tre» — la forma del
   denominatore che si muove, trovata da @ws4 Nadia.)*
4. **Nessuno dei tre è stato eseguito da chi non ci conosce**, ed è il controllo
   che vale più di tutti: noi sappiamo già dove guardare, e questo rende i nostri
   tempi i più ottimistici possibili.

---

## 🪞 Perché questa pagina ha avuto **undici** incoerenze in una notte, e cosa le ha trovate

**Alle 01:57 ne ho corrette quattro io, rileggendo.** Alle 02:41 @ws4 Nadia ne ha trovate
**altre sette**, e la peggiore era che **il difetto che questa pagina elegge responsabile
di U-B non era nella lista dei difetti che bloccano U-B**. Le mie quattro e le sue sette
sono la stessa classe. La differenza non è l'attenzione: **è il metodo.**

    io, alle 01:57      ho RILETTO la pagina cercando le incoerenze     ->  4
    Nadia, alle 02:41   ha INCROCIATO la pagina con GRAVITA-DIFETTI
                        e con gli ORARI DEI COMMIT                      ->  7

🔑 **Un documento non si controlla da sé.** Le affermazioni che invecchiano qui dentro
sono affermazioni **su cose che vivono altrove** — un livello nel registro dei difetti, una
cura su un ramo, un `doctor` che nel frattempo è stato chiuso. **Dall'interno sono
indistinguibili da quelle giuste**: hanno la stessa forma, lo stesso tono, e le ho scritte
io. Si vedono solo mettendole accanto alla fonte che le ha superate.

⇒ **Il controllo di questa pagina è un incrocio, non una rilettura**, e ha tre gambe:
1. ogni affermazione su un **difetto** si verifica in `GRAVITA-DIFETTI.md` di *adesso*;
2. ogni affermazione su una **cura** si verifica con `git branch -r --contains <sha>`;
3. ogni **esito** porta l'albero su cui è stato preso, e **un esito preso su un albero che
   non esiste più non si riscrive: si rifà.**

### ⚠️ E la quarta gamba, imparata applicando le altre tre dieci minuti dopo

Ho preso la ② di Nadia — *«D-6 dato come cura sul ramo, mentre è in `main`»* — l'ho
corretta qui, e poi **ho cercato la stessa frase altrove**:

```
grep "cura ... sul ramo" docs/stato-reale/*.md
  GRAVITA-DIFETTI.md:20    cura sul ramo (Giano, finestra ②)
  SCHEDA-PRODOTTO.md:261   cura pronta sul ramo
git branch -r --contains db7dfd11  ->  origin/main       (la cura È in main)
```

⇒ **La stessa affermazione superata viveva in tre documenti, e me n'era stata segnalata
una.** Correggere dove ti viene indicato dà **l'illusione di aver corretto**: è la classe ①
— *una copia invece della superficie unica* — applicata non al codice ma alle affermazioni
di stato. 🔑 **Quando una di queste cade, si cerca la frase, non il documento.**

📌 E la conferma che il metodo conta più della cura: Nadia **ha cercato la stessa forma su
di sé prima di mandarmela** e ha trovato il proprio verde preso su un `main` indietro di
uno — conseguenza nulla, e l'ha scritto lo stesso, *«perché è la differenza fra l'ho
controllato e non poteva succedere»*.
