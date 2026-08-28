# 00 — L'ESAME DEL PRODOTTO

> **Registro unico delle celle misurate.** Istituito dalla direttiva di Aurelio del
> 27/08 (trasmessa da `lead-audit`, messaggio A2A `d2d5c2944c8f457e`), nelle sue parole:
> *«cosa dovrebbe avere teoricamente un progetto del genere? Le ha? Rispetta quello che
> promette? **Lo fa davvero?**»*
>
> Questo file **non giudica il codice: registra le misure**. È il posto dove un referto
> smette di essere un messaggio sul canale e diventa una riga che qualcun altro può
> attaccare.

## ⏸️ Coda delle misure — REGIME RAM (ordine di Aurelio, 28/08 ~20:55)

> **Aurelio sta giocando e la RAM è al 70%.** Sospese le esecuzioni: banchi, `verimem save`
> (carica il giudice), `pytest`, processi nuovi. **Il registro si aggiorna normalmente: è testo.**
> Il custode tiene questa lista perché **alla finestra macchina si parta ordinati** invece che
> tutte insieme.
>
> ⚠️ **Righe scritte da me da ciò che avete DICHIARATO** (claim attivi e banchi annunciati in
> canale). **Non deduco cosa avete in coda: correggetele o aggiungete la vostra.**

| # | misura sospesa | di chi | perché è pesante | fonte della riga |
|---|---|---|---|---|
| 1 | **C7 · smoke TestPyPI pre-tag** — venv nuova e incontaminata con `verimem==0.7.0` | @ws1 | una venv + `pip install` + modello | claim `6e036cfddc3f` |
| ~~2~~ | ~~**C2 · classi core in IT e EN**~~ ✅ **ESEGUITA PRIMA DEL FERMO, 20:55** — @ws5: **6 buchi su 16 celle (37,5%)**, 3 falsi positivi, **2 classi rotte in entrambe le direzioni**. *(Denominatore corretto da lei alle 20:59: erano 16, non 14 — il numeratore regge, la proporzione scende da 43% a 37,5%.)* | @ws5 | — | referto in canale |
| 3 | **`W2-9`** — l'ultima delle tre celle ad alto rischio sull'asse A | @ws2 | due A/B con e senza la variabile | censimento 20:09, esito parziale 20:46 |
| ~~4~~ | ~~**asse B · `PYTHONUTF8=1`**~~ ✅ **CHIUSO 21:2x — INNOCUO su questa classe**: 7 righe su 7 **identiche** nei due regimi d'interprete ⇒ **le dieci celle NON vanno rifatte per questa ragione**. Controllo positivo: il separatore `·` si stampa `?` senza la variabile, quindi l'interprete era davvero diverso. ⚠️ **Limite**: misura il giudizio del gate su testo accentato, **non** prova che la variabile sia inerte altrove (il 20/08 causò un rosso in CI) | @ws7 | — | banco `ws7-asse-b-pythonutf8.py` |
| 5 | **`scripts/banco_a2.py`** — 81 righe, `21 Aug 10:11`, mai committato | *da rivendicare* | è un banco | `git log --all` vuoto |
| 6 | **il numero VERO dei comandi assenti da `0.7.0`** — col parser del presidio `test_i_comandi_che_il_readme_insegna_esistono` | @ws8 | scarica l'artefatto da PyPI + parsing | **i miei due righelli non concordano**: 37 (`grep -c '^@app\.command'`) vs 34 (parser per nomi) ⇒ non pubblico il numero. ✅ **I NOMI reggono già**: `save · ask · correct · digest · ignorance · recent · telemetry · tiers · tip` assenti in 0.7.0 |
| 7 | **verifica della cura di `L1.20`** — con `encode_service.daemon_usable()` nel guard, e **daemon attivo**, `L1.20` deve comparire dalla **PRIMA** scrittura | @ws8 | carica il gate | banco **già scritto e pubblicato** (20:13); si esegue quando @ws3/@ws1 applicano la cura |
| 8 | **censimento dei verdi ALTRUI** in regime utente — `ENGRAM_ENCODE_SERVICE=0 env -u HIPPO_ENCODE_DELEGATE_ONLY` | *da rivendicare* | 23 celle × 2 regimi | **i miei quattro sono FATTI**: 12 misure, 3 regimi, **zero cambiamenti** |
| ~~6~~ | ~~**cosa vede `L4.1`**~~ ✅ **CHIUSO — e il gate aveva ragione: il difetto era nel MIO FATTO.** Il claim diceva *dove* lo script era stato eseguito (`00-ESAME.md`) e **quella stringa non è nella fonte**; tolta, la scrittura passa. ⇒ nuova cella **`LANT-27`** | @ws7 | — | stesso banco |
| 7 | **un fatto con punteggio FRA 40 e 99,64** — il solo caso che distingue le due soglie | @ws1 | richiede una scrittura | referto 21:05 |

🔎 **Perché la riga 6 è cambiata, e lo devo a @ws1.** Le mie tre scritture di stasera hanno
`grounding_score` **99,87–99,98** e `withheld_despite_judge=True`: leggevo quel campo come «il
gate non crede alla fonte». **Falso.** @ws1 ha letto il punto che decide: il campo `layers`
risponde a *«quale difesa ha AGITO»*, non *«chi ha parlato»* — e la soglia del giudice, se il
`gate_config` la porta sopra 90, **viene deliberatamente riportata a 40** (`grounding_gate.py:510`,
sanity cap: 99,64 è il max-F1 del **val set**, e a quella soglia **si quarantinano fatti veri**).
⇒ **Il giudice mi diceva di sì, e a fermarmi è stato un layer lessicale.** La domanda giusta è
**cosa vede `L4.1` nelle mie frasi**, e non è la stessa cosa.
✅ **E un dato a favore del rilascio, sempre da @ws1**: quel sanity cap **è già nel pubblicato** —
4 marcatori su 4 nella 0.7.0, cura del 18/07 contro un pacchetto del 22/07 ⇒ **un utente della
0.7.0 non rischia di vedersi quarantinare fatti veri per la soglia del modello.**

🪞 **DIFETTO DI QUESTA TABELLA, TROVATO SUBITO E VALE PIÙ DELLA TABELLA: un claim attivo NON è
una misura pendente.** La riga 2 l'ho scritta dal claim `9b0bb46473df` di @ws5 — **ma la misura
era già stata eseguita alle 20:55**, prima che il fermo arrivasse. Il claim resta attivo finché
chi lo tiene non lo rilascia, quindi **la lista dei claim dice chi sta lavorando su cosa, non
cosa manca.** ⇒ **Le altre righe hanno lo stesso rischio**: sono ipotesi finché non le confermate.

⏱️ **Quanto costa davvero un `verimem save`, e spiega perché è nella lista dei sospesi** — @ws1,
20:57: **carica il cross-encoder da 1,9 GB**. *(È anche il motivo per cui le mie tre scritture
quarantinate di stasera restano ferme: per riaprirle serve il giudice.)*

📌 **Chi ha una misura pronta ma ferma: una riga in canale e la aggiungo.** 📌 **Chi ne esegue una
alla finestra: cancelli la riga con l'esito**, così la coda si accorcia da sola.

## Se hai trenta secondi

> Solo fatti contati e puntatori. **Nessun aggettivo**: il registro è il posto dove una frase
> più larga del dato fa più danno che altrove.
> ⚠️ **QUI NON C'È PIÙ IL CONTEGGIO, e il motivo è misurato.** Ci è stato due volte e due volte
> è invecchiato in poche ore: alle 12 diceva **53** quando erano **84**; l'ho riscritto, e alle
> **21:00 diceva 85 quando erano 108** (🔴 60 · 🟢 29 · 🟡 17 · ⛔ 1 · 🚫 1). In mezzo c'era
> già l'avviso *«chi la legge la ricalcoli»*, **e non è bastato**: un avviso chiede a chi legge
> un lavoro che nessuno fa.
> 🔑 **In un file che otto mani modificano, un numero scritto a mano nella sintesi inganna più
> di quanto informi** — e chi legge trenta secondi legge **solo** questo. ⇒ La cura non è
> riscriverlo meglio: è **non tenerlo qui**.
>
> ```bash
> python scripts/conta_celle_esame.py
> ```
>
> 🪞 **E un secondo difetto trovato qui il 28/08 21:08, peggiore del conteggio**: questa sezione
> citava **`LANT-1`**, un id **che non esiste**. La cella c'è ed è **`W7-1`** — **di @ws8**: nel
> riassumerla le avevo messo la MIA sigla, cioè **l'avevo attribuita a me**. Corretto.
> 🔑 **Prima di uniformare una sigla, guarda la colonna dell'autrice**: stavo per «sistemare»
> un'incoerenza mia riscrivendo l'identificativo di una cella altrui. ⇒ **Righello per chiunque
> tocchi la sintesi: ogni id citato qui deve comparire nella colonna id della tabella.**
> **Un comando, esce da solo, e dice anche gli id duplicati.** *(Falsificabile: se fra tre ore
> questa sezione contiene di nuovo un numero sbagliato, la cura non ha funzionato.)*

**Cosa il prodotto fa, misurato**: ferma la contraddizione in tutti i regimi provati (0/12,
riga 29) · pretende che il soggetto del claim stia nella fonte (31) · regge il carico di un
servizio — 258 ms, 14,3 op/s, zero errori (10) · gestisce un valore che evolve (LANT-4) · dà
a un agente una ricevuta su cui può agire (38) · **protegge la cifra assente a ogni lunghezza
provata, fino a 3.516 caratteri** (ws4).

**Cosa non fa, misurato**: nessun presidio ferma un claim che **aggiunge** un dettaglio assente
dalla fonte (12/12, riga 30) · un vero può essere scartato (≥12 su 58, LANT-3) · uno scambio di
attribuzione entra 3 volte su 7 e **cancella il fatto vero** nello stesso topic (LANT-7) · il
consiglio dato a un agente rifiutato non è eseguibile (W7-1, **di @ws8**) · **bastano 17 parole di
intestazione** perché un valore sostituito passi da 7,9 a 99,1 (22).

🎯 **LA 0.7.0 SU PyPI HA UN DIFETTO SOLO, NON DUE — chiuso il 28/08 alle 19:50 (ws1, venv mai
toccata).** Per settimane la voce di testa diceva «rotta due volte»: **mcp che non parte** *e*
**moat muto**. ⇒ **Il secondo non esiste**: quel `grounding_score` nullo veniva da
`HIPPO_ENCODE_DELEGATE_ONLY=1`, **una variabile delle NOSTRE shell** ereditata senza
accorgersene — senza di essa la 0.7.0 dà **99,92, `tier=high`**. **Il moat gira, per chi
installa.** ✅ **Resta e regge il tetto `mcp`**: su venv mai toccata `verimem mcp` esce **1**.
🩹 **Questa riga ha rischiato di far decidere il falso**: alle 19:28 stava scritta qui come
«il difetto più grave», e la decisione di ritiro era fra i pendenti. **La cicatrice resta
apposta** — chi legge questa sezione la legge per decidere.

**Cosa non siamo in grado di dire**: se il gate abbia avuto ragione nei casi contestati — **la
prova che conserva è troncata a 400 caratteri** (LANT-5), e la cura costa zero.

**Cosa manca del tutto**: il vertice — *un agente con verimem sbaglia meno di uno senza* —
**non ha una riga**. Finché non ce l'ha, questo registro dice come si comporta il prodotto,
non se serve.

## I quattro livelli di ogni domanda

| livello | domanda | chi lo può dire |
|---|---|---|
| ① | dovrebbe averlo? | discussione |
| ② | ce l'ha? | `git grep` |
| ③ | lo **promette**? | README / CLI / docstring |
| ④ | **lo fa davvero**, misurato **alla porta** *e nel regime che un utente userebbe*? | solo un'esecuzione |

> 🔴 **«Alla porta» da solo non basta — obiezione di ws3, accolta il 27/08, e nasce da un
> errore pagato la sera stessa.** Il «muro» dei 24 secondi è stato misurato **alla porta**,
> correttamente, e il verdetto era **falso lo stesso**: la porta era giusta, il **regime** era
> l'anti-pattern che il repo dichiara tale (riga 8 contro riga 10, **1,5 → 14,3 ops/s**).
> ⇒ **Una misura alla porta nel regime sbagliato non è una misura debole: è un verdetto
> invertito.** Chi compila una cella dichiara il regime **accanto** alla porta, e se il regime
> non è quello di un utente lo scrive nel verdetto, non nelle note.


> 🔴 **Una promessa senza il livello ④ verde è marketing.** Questa è la riga che
> l'esame esiste per far rispettare, e vale anche per le righe scritte qui dentro.

## Come si scrive una riga — le regole pagate, non inventate

1. **Il REGIME è obbligatorio e va scritto per PRIMO** nell'ultima colonna — *ratificato da
   `lead-audit` il 27/08 come quinto livello dell'esame, su obiezione di ws3.* Non è un dettaglio
   della cella: è ciò che decide se il verdetto vale.
2. **Il regime sta nell'intestazione, non nella memoria di chi ha misurato.** Macchina,
   variabili d'ambiente, versione, `n`. *(Un verde senza regime vale come un numero senza
   unità: misurato il 20/08, due istanze hanno contato «caduto» un bersaglio che nel
   regime giusto era verde **prima** della cura.)*
3. **Niente numeri nei titoli.** Un titolo con una cifra invecchia e nessuno lo rilegge;
   la cifra sta nella cella, dove ha accanto il suo denominatore.
3. **Il denominatore accanto alla cifra, sempre.** *(Dei sei difetti di vetrina trovati
   in due giorni, **cinque erano la stessa cosa**: un numero corretto sotto un'etichetta
   che non definisce la popolazione.)*
4. **Dichiara il livello a cui hai misurato.** Regex interna < funzione pubblica < porta
   che il prodotto usa — e ogni salto può ribaltare il verdetto, **in entrambe le
   direzioni**.
5. **Un controllo che DEVE fallire**, o «4 su 4» non distingue un presidio che funziona
   da uno spento.
6. 🔴🔴 **MISURIAMO CON UN PRESIDIO IN PIÙ DI CHI INSTALLA — e questo gonfia i VERDI.**
   `L1.20`, il selfclaim semantico, **è attivo da noi e assente da chi installa**. *(ws8, 28/08,
   A/B in due sottoprocessi: con `HIPPO_ENCODE_DELEGATE_ONLY=1` i layer sono
   `['L1.10','L1.13','L1.15','L1.20']`, senza sono tre.)*
   ✏️ **Meccanismo preciso, chiuso da ws8 alle 20:05 — e NON è «manca la variabile»**:
   `_encode_one` (`embedding.py:240`) prova **tre vie** — *servizio condiviso per primo*,
   in-process caldo, cold-load — mentre il guard (`semantic_selfclaim.py:263`) ne controlla
   **due**: `is_loaded() or _delegate_only()`. **Il servizio condiviso non compare.** ⇒ Col
   daemon attivo **l'encoding riesce** (misurato: `embedding` valorizzato **1 su 1**) **e il
   guard declina lo stesso**, perché `is_loaded()` resta `False` per sempre — il modello può
   caricarsi **solo nel processo daemon**. 🔑 **`L1.20` si disarma proprio quando l'encoding
   sarebbe disponibile e gratuito, e non si riarma mai.**
   ⚠️ **Perché la precisione conta qui**: con il meccanismo sbagliato la cura sembra «accendere
   la variabile per tutti»; con quello giusto è **far contare al guard la via che già funziona**.
   ⇒ **Ogni cella che dice «il gate ferma X con questi layer» va letta chiedendosi se quel
   presidio esista dalla parte dell'utente.**
   📌 **Censite il 28/08**: **2 celle nominano `L1.20`** (`W2-5`, `W2-10`) · **9 nominano altri
   `L1.*`** · **27 celle sono verdi.** ⚠️ **La direzione dell'errore è la peggiore possibile:
   un presidio in più rende i nostri verdi OTTIMISTICI**, e un verde ottimistico non lo corregge
   nessuno — al contrario di un rosso, che qualcuno viene a contestare.
   ✅ **Il controllo costa un secondo**, ed è quello di ws1: `env | grep -iE 'hippo|engram|verimem'`
   accanto al comando. **ws8 l'ha eseguito su di sé al primo colpo e ha trovato questo.**

7. **Se la fonte è `git log` o il journal, FISSALA A UNO SHA.** *(ws4, 28/08: la sua fonte è
   cambiata di sei commit in tre minuti e il risultato è diventato non riproducibile. Applicato
   subito a una misura mia: «65 commit» delle 19:45 era **datato senza dirlo** — rifatto con lo
   SHA fissato dà **87**, e venti erano arrivati nel frattempo.)* ⇒ **In questo repo la copia si
   muove sotto i piedi: otto istanze scrivono.**

8. **Verifica QUALE versione stai misurando, e non con `pip`.** Su questa macchina
   `importlib.metadata.version("verimem")` risponde **`0.7.0` mentre l'interprete esegue
   HEAD** — è un *editable install*: i metadati sono fermi, il codice no. *(Trovato da ws1 il
   28/08; i nostri stessi server MCP girano su HEAD, non sulla 0.7.0.)*
   ```
   python -c "import verimem,os; print(verimem.__version__, os.path.dirname(verimem.__file__))"
   ```
   Se il percorso finisce in `Code\HippoAgent`, **stai eseguendo il repo, qualunque cosa dica
   `pip`**. Per misurare il pubblicato serve **una venv separata** con `pip install
   verimem==0.7.0`. 📌 **Censite il 28/08: cinque celle nominano la 0.7.0, quattro dichiarano
   il regime che le protegge, una (la 20) è da confermare.**

7. **Un metadato non è il contenuto.** Un orario, un nome, una versione sono indizi; la prova
   è il **diff dell'artefatto**. *(Il 27/08 «il tag è posteriore all'upload di 1h27» — fatto vero —
   ha quasi invalidato tutte le misure sul tag; il confronto file per file ha dato 397 su 397
   identici.)*
7. **Se le colonne non sommano al totale, il difetto è nel misuratore.** *(ws1 se n'è accorta
   dall'aritmetica, non dal codice: «366 identici + 9 diversi + 22 assenti» su 397 file — gli
   identici superavano gli esistenti perché il confronto andava per nome base.)*
8. **Chi riporta la misura di un altro lo scrive.** La colonna `misurata da` non è un
   credito: è il modo di sapere a chi chiedere quando la riga verrà attaccata.
12. **La seconda firma migliore non è rifare la stessa misura: è firmarla dal VERSO OPPOSTO** —
   @ws6, 28/08 21:04, che ha firmato la `W2-4` di @ws2 *«tu la concordanza sul rifiuto, io
   sull'ammissione»*. 🔑 Rifare la stessa misura conferma che il righello è ripetibile; misurare
   **l'altra popolazione** conferma che il righello **discrimina**. ⇒ È la lezione «misura
   entrambe le popolazioni» applicata alla revisione fra noi.

11. **Nominare una classe di errore non immunizza dal caderci** — @ws1, 28/08 21:05, e l'ha
   scritta contro sé stessa: un'ora dopo aver **nominato** la classe *«un sensore corretto usato
   come proxy di una domanda che non risponde»*, ha chiamato «difetto» un campo corretto **perché
   gli stava facendo la domanda sbagliata**. 🔑 **Il presidio non è ricordarsi la lezione: è
   LEGGERE FINO IN FONDO IL PUNTO CHE DECIDE.** *(Le sono servite tre volte in un giorno: la
   risposta stava una riga sotto quella che aveva letto.)*
   ⚖️ **E qui il registro deve dire una cosa su sé stesso**: queste regole sono scritte perché
   qualcuno le ha pagate — **non perché averle scritte protegga.**

10. **Committa con i path espliciti, anche per `docs/`** — regola di @ws2, 28/08 20:43, pagata
   da lei e **anche da me un'ora prima**. `git add -A` o `git commit -a` **si portano dentro il
   lavoro non committato di chi sta scrivendo in quel momento**: la sua cella `W2-16` è finita
   su `origin` dentro il commit di un'altra, integra ma sotto un messaggio che parla d'altro.
   *(Io con lo stesso comando avevo preso `scripts/banco_a2.py`, che non è mio.)*
   🔑 **E la distinzione che serve per non allarmarsi troppo, misurata**: il commit che l'ha
   portata **è firmato** — `Agent: Curie` — e **18 degli ultimi 20 sono firmati** (Curie, Varco,
   Galileo, TARA, Paragone, Lanterna; gli altri due sono un merge e uno senza variabile).
   ⇒ **Il `git log` conserva l'autore del COMMIT; quello che non conserva è l'autore del
   CONTENUTO.** Sono due cose diverse e solo la seconda è il difetto.
   ⚖️ *La simmetria la nota @ws2 e vale la pena tenerla: passiamo la serata a misurare che il
   prodotto non conserva il motivo delle proprie decisioni, mentre il nostro registro non
   conserva l'autore delle celle. Stessa classe, due sistemi.* ⇒ **La colonna «misurata da» non
   è una cortesia: è l'unico posto dove quell'informazione esiste.**
9. **Un elenco di layer non si scrive senza il regime che l'ha prodotto** — regola di @ws1,
   28/08 20:19, e non è una precauzione: **il nostro elenco ha un layer in più di quello
   dell'utente.** Misurato da lei su cinque scritture in regime utente (venv dedicata, `pip
   install verimem==0.7.0`, cache HF vuota): senza la variabile i layer sono
   `['L1.10','L1.13','L1.15']` in tutte e cinque, con la variabile compare anche `L1.20`.
   🔑 **E il modo in cui sparisce è peggio della sparizione**: il moat, quando si astiene,
   *lo dichiara* (`L4-skipped`); `L1.20` **esce dall'elenco e basta**. ⇒ È la forma che
   conosciamo — *una misura che non c'è si legge come una misura perfetta* — applicata al
   posto dove fa più danno: **la ricevuta che consegniamo all'utente.**

## Triage delle rosse — F2, richiesto da `lead-audit` il 28/08

> **Conta contata**: `python scripts/conta_celle_esame.py` → **38 rosse** su 69 celle.
> ⚠️ *Il numero «36 rosse» dell'ordine del giorno veniva dal conto vecchio, che sbagliava di
> tre celle: il righello contava rossa ogni cella che **contiene** 🔴, incluse le tre che
> dicono «🟢 sì, dopo cura (era 🔴)».*
>
> **Etichetta = che TIPO di intervento serve, non quanto è grave.** Una `decisione-CEO` può
> essere il difetto peggiore del registro; una `cura-quick` può restare aperta per mesi.
> **L'owner è PROPOSTO da chi tiene il registro, non assegnato**: lo conferma chi lo prende.

### 🔵 decisione-CEO — non si curano, si scelgono (3)

| cella | la scelta, in una riga | owner |
|---|---|---|
| **2** | la 0.7.0 su PyPI non avvia il server MCP: **yank · avviso sulla pagina · release accelerata**. È la VOCE 0 | **Aurelio** |
| **27** | il gate lancia `claude -p` **senza `--model`**: fissare il modello del giudice (e scriverlo nella ricevuta) cambia i punteggi già emessi | **Aurelio** |
| **W7-10** | `backup-all` copre 3 tier su 9: **rinominare** il comando (rompe chi lo invoca) **o estenderlo** (cambia cosa produce) | **Aurelio**, proposta da ws5 |

### 🟢 cura-quick — la cura è nota e il costo è dichiarato (8)

| cella | cura | costo dichiarato da chi ha misurato | owner proposto |
|---|---|---|---|
| **W7-1** | l'advice di `L1.9` suggerisce una forma che non passa mai | «**una riga di testo**» | ws8 |
| **W7-5** | span della prova troncato a 400 | «**una riga**, variabile già esistente; **verdetto identico** con 400 contro 932» | ws1 |
| **W7-6** | `correct` chiede un id che `recall` non stampa | «**la cura è una riga**» | ws5 |
| **7** | SDK dice `warnings`, MCP dice `anti_confab_warnings` | allineare **un nome** (o esporre entrambi) | ws2 |
| **26** | il parser del punteggio rifiuta `**55**` e la prosa | allargare **un pattern** | ws4 |
| **50** | la ricevuta di `add()` non ha la chiave `layers` | aggiungere **una chiave** già calcolata a monte | ws3 |
| **W7-15** | `confidence` anti-correlata · `last_seen` = «letto» | rinominare **o** documentare nel punto d'uso | ws5 |
| **W7-16** | `file:` non è nella lista dei prefissi accettati | aggiungerlo **alla lista** | ws8 |

### 🟠 strutturale · lo strato soggetto-valore (12) — **è F1, la cura che ne chiude tre**

> 🔒 **Queste dodici sono marcate `BLOCCATA-DA-F1` nella tabella** (direzione di `lead-audit`,
> 28/08 19:02). **Non è un'etichetta di gravità: è una dipendenza.** Curarne una singola senza
> lo strato significa spostare il difetto, non chiuderlo — ed è successo: ogni volta che una di
> queste è stata «ristretta», il buco è ricomparso da un'altra faccia (`22` è passata da
> «ripetizione» a «lunghezza» a «contenuto del contorno» in un'ora, sempre restando aperta).

`30` omissione senza presidio · `49` chi decide sullo scambio · `W7-13` `L4.1` tace 0/12 ·
`W7-7` attribuzione 3/7 · `W7-8` conta il **contorno** · `W7-9` (ws4) l'**unità** ·
`W7-14` il contorno ribalta in **entrambe** le direzioni · `3` numeri comuni ·
`5` l'unità non entra nel confronto · `13` il ricalco con clausola cambiata ·
`22` è la **ripetizione**, non la lunghezza · `W7-2` cifra assente 9/10.

> 🔑 **Dodici rosse su trentotto sono lo stesso buco visto da dodici lati.** È il motivo per cui
> `lead-audit` mette F1 davanti a tutto, ed è il miglior rapporto costo/beneficio del registro.
> **Owner: ws3 + ws5 in coppia** (design falsificabile prima, poi review, poi implementazione).

### 🟠 strutturale · architettura del gate (6)

| cella | il nodo | owner proposto |
|---|---|---|
| **37** | **nove chiamanti** validano le scritture, nessuna superficie unica | ws2 |
| **28** | i nove passano **quattro argomenti in comune su diciannove** | ws2 |
| **23** | `verimem save` passa `meta_narrative=True` e **spegne `L1`** | ws8 |
| **21** · **35** | l'attestazione è onorata su SDK e non su MCP (causa: `repo_root`) | ws2 |
| **W7-11** | una quantificazione universale non passa | ws8 |

### 🟠 strutturale · gli altri (9)

`6` grounding non monotono · `12` la negazione non esplicita 46/108 ·
`19` l'affidabilità varia 10× per classe e lingua · `36` la rete sugli errori ad alto punteggio ·
`45` · `W7-17` **N record distinti nello stesso topic** · `47` lo stesso fatto cambia verdetto ·
`W7-3` `L4.1` ferma anche il vero · `W7-12` il gate insegna a chi lo usa.

> ⚠️ **`45` e `W7-17` sono la stessa domanda scritta due volte** («N record distinti nello stesso
> topic coesistono?» / «tre record distinti…»), da due mani in due momenti. **Non le fondo io**:
> i regimi vanno confrontati da chi li ha misurati — @ws2, sono entrambe tue.

### Cosa dice il triage, letto tutto insieme

- **3 rosse su 38 non sono difetti**: sono scelte che aspettano una decisione, e **due
  aspettano Aurelio da ieri**.
- **8 hanno una cura che chi l'ha misurata ha già scritto** — costo dichiarato, nessuna
  richiede progettazione. **Sono il lavoro più a portata di mano del registro.**
- **27 sono strutturali, e 12 di quelle sono la stessa falla.** ⇒ Chiudere F1 non toglie 12
  righe dal registro: **toglie un buco solo, che si presenta con dodici facce**.

## Il ponte con `RELEASE_GATE.md` — quali celle toccano quali cancelli

> `RELEASE_GATE.md` è il gate del **tag**; questo file è la **mappa**, di cui il gate è il
> sottoinsieme bloccante. Finora i due non si parlavano: i dieci cancelli sono stati scritti
> prima delle celle e **non sanno nulla di ciò che è stato misurato il 27/08**.
>
> ⚠️ **Questa tabella NON decide che cosa blocchi il rilascio.** Dice soltanto quale cella
> porta informazione a quale cancello. **La colonna «blocca?» è vuota apposta: la riempie
> Aurelio.** È la differenza fra dargli un criterio di uscita e dargli una lista che si allunga.

| cancello | celle che lo toccano | cosa dicono | blocca? |
|---|---|---|---|
| **G2** install-from-scratch (include «MCP server start») | 2 · 1 · 11 · 20 | il server MCP **non parte** per chi installa da PyPI (controllo positivo: con `mcp<2` parte) · la CLI mantiene **14 promesse su 14** · il moat non giudica **finché non si esegue `verimem warmup`** | |
| **G8** fresh-environment model download | 20 · 11 | un utente nuovo completa scrittura+lettura in **8 s** ma con **zero byte scaricati**: quel regime **è** «senza warmup», e spiega G2 | |
| **G10** multilingual validation | 19 · 12 · 4 · W7-8 | l'affidabilità **varia di 10×** per classe e lingua (negazione IT 0/10 · EN 0/10 · TH 6/10) · la negazione non esplicita passa **46 su 108**, IT 30/54 contro EN 16/54 · tre record distinti si cancellano **in inglese e non in italiano** | |
| **G4** benchmark riproducibili da un comando | 9 · 10 | il banco del **regime reale** esisteva dal 21/07 e non era **mai stato eseguito**; eseguito il 27/08 dà **258 ms · 14,3 op/s · zero errori** | |
| **G6** README claim audit: zero claim non verificati | 1 · 31 · 32 | i comandi promessi dal README pubblicato ci sono **tutti** · il gate **pretende che il soggetto stia nella fonte**, e l'accusa contraria è stata ritirata dall'autrice | |
| **G1** suite intera verde su un run pulito | LANT-24 | *(sweep del 28/08 20:20)* la CI **non produce verdetti da 22 ore e mezza**, e chi aspetta troppo viene **cancellato** ⇒ questo cancello non è rosso: **è muto**, e non per causa sua | |
| **G9** CI cross-platform | LANT-24 | stessa cella, altro cancello: senza run conclusi non esiste né una matrice verde né una rossa | |
| **G7** identità PyPI + install da venv pulita | 2 · 11 | *(già usate per G2/G8 — una cella può servire più cancelli)* la clausola «install verified from a clean venv» oggi **non regge sul server MCP**, mentre il moat per chi installa **gira** | |
| **G3** crash durability · **G5** invarianti hypothesis | *(nessuna cella)* | **e qui l'assenza non è un buco**: sono i due che alla riverifica del 26/08 **reggevano**, e da allora nessuno li ha rimessi in discussione | |

📌 **Quello che questa tabella rende visibile e prima non lo era**: dopo lo sweep del 28/08,
**otto cancelli su dieci** hanno almeno una cella; i due che non ne hanno sono i due che reggono.

🚨 **IL LIMITE DI TUTTA QUESTA TABELLA, e non è una cella: è il meccanismo** — misura di @ws8,
28/08 20:30. `publish.yml` ha **7 run in tutto** e l'ultimo è del **22/07**: **37 giorni**. Dopo
quella data sono stati fatti **8 commit** su quel file, per ⚠️ **due conti, li porto entrambi**: **219 aggiunte su 264 (83,0%)** secondo @ws8, **225
aggiunte e 6 rimosse (85,2%)** secondo @ws1 che ha verificato per via indipendente e osserva
che `225-6=219`, cioè che il primo è probabilmente **il NETTO chiamato «aggiunte»**. *(Non
scelgo io: il numero è di @ws8 e l'etichetta la mette lei.)* In entrambi i casi ⇒
**l'83% del workflow di rilascio non è mai stato eseguito nemmeno una volta.** E i titoli dicono
che sono protezioni, non ritocchi: *«a tag alone could ship to PyPI, with the CI red»*, *«the
gate asked whether the CI was green, not whether the commit was on main»*, *«lo scavalcamento
del cancello non lasciava traccia»*.
🔑 **Il ponte dice quali celle toccano quali criteri; questo dice che il CODICE CHE APPLICA i
criteri partirà per la prima volta il giorno del tag.** Sono due cose diverse e vanno lette
insieme: **un cancello verde applicato da un esecutore mai eseguito non è un cancello chiuso.**
⚖️ Ciò che @ws8 **ha** potuto verificare senza eseguire, e che va detto accanto: i 6 blocchi
`run:` passano `bash -n` **6 su 6**, con il controllo che deve fallire superato ⇒ **non è rotto:
è non provato.** Sono due affermazioni distinte e la seconda non implica la prima.

🚨🔑 **E POI @ws1 HA ESEGUITO IL CANCELLO, alle 20:34 — non previsto: MISURATO.** Il blocco 1
chiede a GitHub la `conclusion` del run di `ci` per lo sha che si sta pubblicando; eseguito
**com'è scritto** sullo sha di `origin/main` dà `verde=false` ⇒ **se Aurelio taggasse adesso il
publish si fermerebbe.** ⚠️ **Ma il messaggio direbbe la causa sbagliata**: stampa *«la CI non è
verde (nessun run su main)»* mentre la verità su quello sha è **un run, su main,
`status=queued`, `conclusion=null`** — il `// ""` schiaccia `null` a stringa vuota e **«in coda»
diventa «inesistente»**.
🔑 **Per il ponte questo vale più di un verde o di un rosso**: il cancello **fa la cosa giusta
per la ragione sbagliata**, e chi legge il messaggio va a cercare un run che c'è. ⇒ È la forma
già registrata oggi — *un'assenza raccontata come un fatto* — e qui la racconta **il cancello
del rilascio**, al lettore che conta di più.

⚠️ **Come è stato fatto lo sweep, perché il righello ha sbagliato e non l'ho consegnato.** Ho
cercato per parole chiave nella colonna «domanda» e ho ottenuto **sette candidati**: leggendoli,
**tre erano falsi positivi dello stesso tipo** — il pattern `ci` per «CI» pesca il **pronome
italiano** («quanto **ci** mette», «quando **ci** sono i metadati», «quello che **ci** scrivono»)
— e uno lo era per un'altra ragione (la cella `13` nomina una **licenza come fonte di prova**,
G7 nomina le **licenze dei modelli inclusi**: stessa parola, due cose). ⚠️ **E il righello ha
anche MANCATO** il collegamento più importante: `LANT-24` → **G1**, che ho visto leggendo e non
contando, perché il pattern di G1 cercava «suite» e la cella dice «la CI produce verdetti?».
🔑 **Un righello che sbaglia in entrambe le direzioni non si consegna: si usa per fare la lista
da leggere.** ⇒ Questa tabella riporta ciò che ho **letto**, non ciò che ha **contato**.

🛑 **RITIRO UNA MIA INFERENZA (ws7, 22:22).** Avevo scritto qui che «*le celle che toccano G2 e
G8 descrivono la stessa condizione — chi installa e non esegue `verimem warmup`*». **Si
appoggiava sulla riga 20, che l'autrice del dato ha falsificato alle 22:18**: il giudice è
presente anche con zero byte scaricati. ⇒ **G2 e G8 restano collegati dalla cella 11, non dalla
20, e non sono lo stesso fatto.** 🔑 **Avevo costruito un'inferenza su una cella riportata da
altri, ed è caduta con lei**: è la ragione per cui in questo file il custode non deve dedurre —
solo collegare.

## Come si prende un numero di cella — **letto prima di aggiungere una riga**

🔴 **Il progressivo condiviso COLLIDE, e non è teoria: il 27/08 alle 21:30 due autrici hanno
pubblicato una riga `34` nello stesso minuto** e sono finite entrambe su `origin`. Ognuna ha poi
rinumerato la propria, quindi **il numero 34 resta vuoto: non è una riga persa** (verificato nella
storia del file — chi lo cerca non deve rifare il controllo che ho già fatto io).

🔴🔴 **AGGIORNAMENTO 28/08 19:17 — DOPO LA QUINTA COLLISIONE HO CAMBIATO LA MIA SIGLA.**
Ri-spiegare la regola non ha funzionato (l'ho fatto tre volte). **Le celle di ws7 non si
chiamano più `W7-n` ma `LANT-n`**, stesso numero: `W7-14` → `LANT-14`. **Chi cerca un vecchio
`W7-n` in un messaggio del canale lo trova come `LANT-n`.**
⇒ **Perché funziona dove la spiegazione non funzionava**: `W7-…` **somigliava a una
numerazione** e veniva continuata per riflesso; `LANT-…` è visibilmente un nome, e **nessuno
continua per sbaglio la serie di un altro**. *Le `W7-n` rimaste nella tabella sono di ws4,
che le ha misurate: quelle restano sue.*

✅ **Per una cella NUOVA usa `<la TUA sigla>-<n>`** — ws2 scrive `W2-1`, ws4 scrive `W4-1`,
ws6 scrive `W6-3`. **La sigla è la FIRMA di chi scrive la riga, non il nome della serie.**

🔴🔴 **QUESTO SCHEMA HA FALLITO QUATTRO VOLTE** (`W7-8`, `W7-9`, `W7-10`… sempre ws4), e le
prime tre volte l'ho curato **riscrivendo la spiegazione**. Non ha funzionato: **il difetto non
è che la regola sia poco chiara, è che `W7-…` SEMBRA una numerazione.** ⇒ **Se stai per scrivere
una cella e la tua sigla non è `W7`, usa la tua** — e se leggendo il file ti viene naturale
continuare la serie `W7`, **quello è il difetto che sto descrivendo, non un tuo errore.**
📌 **Il controllo che li trova tutti costa un secondo**: `python scripts/conta_celle_esame.py`
stampa gli id duplicati. **Eseguilo dopo aver aggiunto una riga** — è così che ho trovato le
ultime tre.

🔴 **La prima volta, per la cronaca**: il 27/08
ws4 ha scritto una propria cella come `W7-8` — leggendo il file aveva visto `W7-1`, `W7-2`… e
l'aveva presa per la numerazione corrente invece che per la mia firma. Risultato: **due W7-8**.
⇒ **Ho ceduto il numero alla cella che qualcuno ha MISURATO** (quella di ws4) e rinominato la
mia, che era solo *riportata*: **chi riporta cede, chi misura tiene**. 🔑 *Se lo schema non è
auto-evidente, il difetto è dello schema — non di chi lo sbaglia.* I numeri interi già assegnati restano come sono: sono citati nei
messaggi del canale e rinumerarli romperebbe i riferimenti.

📌 **I numeri che compaiono due volte nella tabella «Verdetti che sono cambiati» non sono
duplicati**: sono *riferimenti* alla cella omonima.

## Le celle misurate

Legenda verdetto: 🟢 fa quello che promette · 🔴 non lo fa · 🟡 lo fa in parte / con limite
· **⛔ NON MISURABILE su quella porta** (il presidio non viene proprio chiamato lì: scriverci 🟢
sarebbe *assenza di misura letta come verde*) · **🚫 RITIRATA** (la misura non regge e l'autrice
l'ha tolta: **la riga resta, con il perché e il rimando a quella che la sostituisce**).

> 📌 **`🚫` è stato aggiunto il 28/08 perché mancava.** ws4 aveva scritto `⚪` su una cella
> ritirata — l'unico simbolo che le somigliasse — e lo script l'ha segnalata come «senza
> verdetto». **Non ha sbagliato lei: la legenda non copriva il suo caso**, ed è la seconda volta
> oggi che un simbolo mancante diventa un errore di chi scrive.

> ⚠️ **`⚪` NON è un verdetto**: si usa solo nell'elenco delle **celle scoperte** più sotto, per
> ciò che *nessuno ha ancora misurato*. Una cella della tabella ha sempre uno fra 🔴 🟢 🟡 ⛔.
> *(Il 28/08 una cella aveva `⚪` nel verdetto e `scripts/conta_celle_esame.py` l'ha trovata:
> i due simboli erano troppo vicini, ed è un difetto della legenda — non di chi l'ha scritta.)*

| # | domanda | classe | lingua | porta | verdetto | misurata da | **regime** + limite |
|---|---|---|---|---|---|---|---|
| 1 | i comandi che il README pubblicato promette esistono nel pacchetto? | — | EN | CLI | 🟢 **14 su 14** | ws7 | `git show v0.7.0:`. ✅ **Il limite che avevo dichiarato è CADUTO**: ws1 ha confrontato **l'artefatto installato da PyPI** contro il tag, file per file — **397 identici · 0 diversi · 0 assenti** (perimetro: i `.py` sotto `verimem/`) ⇒ **il tag *è* ciò che sta su PyPI**, e la misura vale per il pubblicato. ⚠️ Il timestamp anomalo di ws6 (tag posteriore di 1h27) **resta un fatto vero**: cade l'inferenza «orario diverso ⇒ contenuto diverso»  ⚠️ **ATTENZIONE DI LETTURA (custode, 28/08 19:15) — TERZA istanza del pattern, e stavolta la cella verde è la mia.** ws1 ha annunciato sul canale che **«13 comandi mancano a chi installa»**. **Non è un conflitto col mio 14 su 14**, quasi certamente: io misuro *ciò che il README **pubblicato** promette*, lei *ciò che main ha e il pacchetto no* — **due popolazioni**. 🔑 **Ma chi legge solo questa riga conclude «la CLI pubblicata è completa», e quella conclusione NON è sostenuta.** @ws1 il numero è tuo: **scrivi la tua cella e collegala qui** ✅ **FATTO (ws1, 28/08 20:52): vedi la cella «I 13 COMANDI MANCANO PER ETÀ» in fondo al file. E la tua lettura era giusta: due popolazioni, nessun conflitto. In più il mio numero si DECLASSA — non è un difetto del pacchetto, è che quei comandi non erano ancora scritti quando la 0.7.0 è uscita.** |
| 2 | il server MCP parte, per chi installa da PyPI? | — | — | MCP | 🔴 **no** | ws1 | venv pulito, `pip install verimem==0.7.0` → `mcp 2.1.1` → `verimem mcp` **exit 1**, `AttributeError`. **Controllo positivo**: forzando `mcp<2` nello stesso venv → **exit 0** |
| 3 | il gate vede un numero inventato dentro una fonte lunga? | C4 | — | — | 🔴 **no, se il numero è comune** | ws5 | A/B a fonte fissa: `3`,`7`,`9` collidono a **200 parole**; `47`,`617`,`4291` mai in 7000. **Non è la lunghezza: è la rarità**  🔒 **BLOCCATA-DA-F1** — non si cura da sola: è una delle facce dello **strato soggetto-valore** (marcatura di ws7 su direzione di lead-audit, 28/08 19:02) |
| 4 | il gate ferma un numero **inventato** scritto all'italiana? | C4 | IT | SDK | 🟢 **sì** | ws8 | **regime**: A/B end-to-end nella stessa esecuzione, porta SDK, store di Aurelio, source fissa, 4 claim. A/B end-to-end, source fissa, cambia solo il separatore: vero-punto e vero-virgola **admitted**, inventato-punto e inventato-virgola **quarantined**. ⚠️ **Riga ribaltata**: alle 20:48 era 🔴 sulla *regex interna* (3 famiglie su 3 spente dalla virgola — vero e ancora vero); alla **porta** il verdetto si inverte perché `L1` non veta e il grounding ferma comunque. **La difesa non è a punto singolo** |
| 5 | l'unità di misura entra nel confronto? | C4 | IT | — | 🔴 **no** | ws5 | una «penale del **7%**» nella fonte valida «**7 giorni**» nel claim; il campo `.unita` esiste e viene ignorato. Bastano due frasi  🔒 **BLOCCATA-DA-F1** — non si cura da sola: è una delle facce dello **strato soggetto-valore** (marcatura di ws7 su direzione di lead-audit, 28/08 19:02) |
| 6 | il punteggio di grounding cresce con il contesto? | — | IT | SDK | 🔴 **non è monotono** | ws4 | **CASO MINIMO**: claim `Il file wake.py conta 9999 LOC.` · fonte = primi N caratteri di `docs/archive/2026-05-13_FORGIA.md` (che dice «wake.py (1143 LOC)») · `mem.add(claim, source=fonte, validate="full")`. **N=1000 → 0.3 · N=2000 → 55.2 · N=3000 → 20.8 · N=4000 → 98.2 · N=6000 → 99.3 · N=10000 → 98.6 · N=14000 → 0.2**. ⚠️ **REGIME**: fuori da pytest (sotto pytest l'embedder è lo stub SHA-256 di `conftest.py:121`), codice `Code/HippoAgent` `6cbeb283`, `client.py` e `anti_confab_gate.py` puliti. **Deterministico**: due esecuzioni, stessi valori a tutte le cifre. Banco: `banchi/la-forma-della-curva-a-passo-fine.py` |
| 7 | le due porte restituiscono gli avvisi con lo stesso nome? | — | — | SDK vs MCP | 🔴 **no** | ws2 | SDK → `warnings` · MCP → `anti_confab_warnings`. Chi cambia porta legge una lista vuota e conclude che il gate taceva |
| 8 | quanto costa davvero una scrittura? | — | — | processo singolo | 🟡 **il costo è di NASCERE, non di scrivere** | ws3, ws6, ws2 | primo write ~26 s / 1,9 GB · dal terzo **0,4–0,5 s** (**23,7×**). Regime: N processi effimeri, ognuno carica i propri modelli — **il repo lo chiama anti-pattern dal 21/07** |
| 9 | il banco del regime che un utente userebbe è mai stato eseguito? | — | — | gateway | 🟢 **eseguito il 27/08** (era 🔴 «mai, dal 21/07») | ws7 (trovato), ws3 (eseguito) | `benchmark/concurrency_shared_server.py` aveva **1 commit · 0 artefatti · 0 citazioni** dal 21/07. Commit dell'esecuzione: `f8836233` |
| 10 | il sistema regge il carico nel regime di un servizio? | — | — | gateway | 🟢 **sì** | ws3 | `--workers 2 --secs 60`, uvicorn in un processo suo, store `mkdtemp`: **654 letture · 217 scritture · 0 errori** · `write_p50` **258,3 ms** · `write_p99` 575,8 · **14,3 ops/s** · **ops > 5 s: 0**. 🔑 La predizione scritta nel docstring il 21/07 (*«writes stay in the hundreds-of-ms range»*) era **esatta** |
| 11 | sulla versione **installata da PyPI** il moat giudica la fonte? | — | EN | SDK | 🟡 **per chi installa il moat GIRA — `99.91928100585938`, `tier=high`. NON gira SOLO sotto `HIPPO_ENCODE_DELEGATE_ONLY=1`, ed è già curato su main** *(ws1: 🟡→🔴 alle 19:07 su un regime contaminato, 🔴→🟡 alle 19:33 col regime STAMPATO — ritiro in fondo al file)* | ws1 (misura), ws3 (correzione) | ⚠️ **Riga corretta il 27/08 e resa MENO grave: eravamo troppo severi con noi stessi.** Il modello del giudice non è nel pacchetto (`local_grounding.py:48` → cache in `~/.cache/verimem/models/`, **~2,3 GB**, scaricati da `verimem warmup`) ⇒ senza warmup `judged=False`, `grounding_score=None` — **la misura di ws1 regge**. **Ma è dichiarato in tre punti del README** (righe 57, 120, 336) **e a runtime nella ricevuta** (`anti_confab_gate.py:1806`: «*source provided but the grounding judge failed to load*»). 🔑 **È un passo d'installazione dichiarato, non una promessa non mantenuta.** ⇒ Scriverlo «il moat non giudica sul pubblicato» **darebbe a un analista un'arma che i fatti non gli danno**. 📌 Spiega la riga 20 (8 s con **zero byte scaricati**: quel regime *è* «senza warmup»)  ⚠️ **Vincolo aggiunto dall'autrice (22:02)**: il confronto era **0.7.0-in-venv-nuovo contro HEAD-nel-suo-albero** — **due variabili insieme**. **Resta vero che chi installa ottiene `grounding None`**; escluse CLI e firma. ⚠️ **RITIRATA LA TESI «è il warmup» (ws1, 28/08 19:07)**: `model_dir` **identico** nelle due installazioni e `local_ce_available()` è **`True`** anche sulla 0.7.0 ⇒ **il giudice c'è e il moat non gira lo stesso**; provato a variabile singola (stessa superficie `remember`, store isolati) → DB: 0.7.0 `grounding_score=None`/`tier=unverified` vs HEAD `99.91928100585938`/`tier=high`. **Il vincolo «due variabili» che avevo messo il 27/08 alle 22:02 è PAGATO.** Dettaglio, le tre leve morte e ciò che il dato NON prova: blocco in fondo al file |
| 12 | il gate rifiuta un claim che la fonte **nega**? | C7 | IT+EN | SDK | 🔴 **no: 46 su 108 (42,6%)** | ws6 | **sei schemi × 18**: «non» esplicito **0/18** ✅ · quantificatore zero 8 · assenza 9 · **stato («il registro è vuoto») 12/18** 🔴 · sostituzione 8 · cessazione 9. **IT 30/54 · EN 16/54**. 🔑 **Il gate riconosce la parola «non», non la negazione**: «*il registro ALFA è vuoto*» è giudicato una **prova** di «*il registro ALFA elenca le misure*», 12 volte su 18, con punteggi 96–99,99. Commit `f51f9845`. ⚠️ Era 5/24 con **un solo** schema: il numero è raddoppiato allargando il banco. 🤝 **Riconcilia il verde di ws8** («L3 negazione ribaltata → `quarantined` in entrambe le modalità»): il suo attacco è *«The release **WAS** approved»* contro *«was **NOT** approved»*, cioè **lo schema 1**, l'unico su cui anch'io misuro **0 errori su 18**. ⇒ **Le due misure non si contraddicono**: il moat ferma la negazione **quando è scritta con la particella**. Sugli altri cinque modi di dire la stessa cosa: **46 su 90**. 🔑 Da un verde sullo schema 1 **non segue** un verde sulla classe |
| 13 | su una licenza reale il gate ferma un claim che **ricalca** la fonte cambiando un numero di clausola? | C4 | EN | — | 🔴 **no, 2 su 3** | ws5 | «section 7» al posto di «section 10» entra a **99.1 senza alcun layer**. Il rischio è la **congiunzione** (ricalco + numero comune), non `L4.1` da solo  🔒 **BLOCCATA-DA-F1** — non si cura da sola: è una delle facce dello **strato soggetto-valore** (marcatura di ws7 su direzione di lead-audit, 28/08 19:02) |
| 14 | il presidio metrico riconosce la copula italiana in tutte le sue scritture? | C4 | IT | SDK | 🟢 **sì, dopo cura** (era 🔴) | ws2 | 5 forme dello stesso claim senza attestazione: `è`, `e` nudo, senza copula e l'inglese cadevano; **`e'` con l'apostrofo passava**. Sul corpus prima della cura: **48** claim metrici scritti con `e'` e **0** quarantinati, contro **8 su 31** (25,8%) di quelli con `è`, su una quota complessiva dell'8,5%. Curato in `f5dedf34`, TDD senza stash: RED `5 failed EXIT=1` → GREEN `11 passed EXIT=0`, non-regressione `tests/test_l1_quantitative_detector.py` `19 passed`. ⚠️ Limite: misurato sulla porta SDK, **non** su MCP/CLI/gateway |
| 15 | il pattern delle percentuali riconosce i sostantivi italiani? | C4 | IT | SDK | 🟢 **sì, dopo cura** (era 🔴) | ws2 | i sei sostantivi erano **tutti inglesi** (`coverage|uptime|availability|accuracy|precision|recall`) mentre la copula accanto era italiana ⇒ quella `è` era **codice irraggiungibile**: il pattern accettava «coverage è 42.6%», che nessuno scrive, e rifiutava «la copertura è 42.6%». Delle 5 scritture dello stesso claim passava **solo l'inglese**. Trovato dal test, non cercato. Stesso commit `f5dedf34` |
| 16 | posizione e lunghezza della fonte spostano il verdetto del giudice? | C4 | IT | SDK | 🟢 **no — decide il rumore numerico** | ws2 | matrice 2×2, stesso claim vero: coda+numeri **0,13** · coda+**senza** numeri (fonte **più lunga**, 4075 char) **99,98** · testa+numeri 99,98 · testa+senza 99,98. ⇒ posizione ininfluente, lunghezza ininfluente, **collide il numero**. Rinforzo indipendente della riga 3 (ws5), arrivato cercando altro |
| 17 | il prodotto mantiene, **all'agente dell'utente**, la quarantena che gli promette? | — | EN | SDK | 🟢 **sì, e meglio di quanto prometta** | ws8 | **regime**: SDK, store temporaneo pulito (`HIPPO_DATA_DIR`), un processo, nessuna source, 1 claim. «*It works, verified, all tests pass, done*» su SDK → **`quarantined`, 4 layer** (`L1.10/13/15/20`), dove la guida ne promette uno. ⚠️ **Riga corretta dall'autrice**: alle 20:58 diceva «promette una quarantena che non avviene» — **falso**, era misurata sulla porta CLI e sullo store di Aurelio, due variabili confuse. **Ciò che regge è la riga 23** |
| 18 | su un testo normativo reale il gate ferma un valore inventato? | C4 | EN | — | 🟢 **sì, 3 su 3** | ws5 | GDPR art. 33: protegge i valori **affermati** («72 ore») e non i **riferimenti** («articolo 10»). ⚠️ **Terza restrizione consecutiva dello stesso allarme** dell'autrice — il difetto è reale e più stretto di come è nato |
| 19 | l'affidabilità è la stessa per ogni **classe di falsità** e lingua? | C7, C5 | IT+EN+8 | — | 🔴 **no, varia di 10×** | ws3 | negazione **IT 0/10 · EN 0/10 · TH 6/10** · entità scambiata IT 1/10 · EN 2/10 · **TH 10/10** · implicita IT 3/10 · EN 0/10 · **AR 4/5** · dettaglio IT 8/10 · EN 9/10 · passiva IT **2/10 veri rifiutati**. 🔑 Omissione, vaghezza e numerali-a-parole sono **una classe sola**: in nessuno il claim porta una cifra  ⚠️ **ATTENZIONE DI LETTURA, aggiunta dal custode il 28/08 su proposta dell'autrice**: «*entità scambiata IT 1/10*» **non copre l'intera classe C5**. Le righe **W7-7** (scambio di **attribuzione**: **3 su 7** entrano, ground 99,7–100) e **W7-13** (`L4.1` **tace 0 volte su 12**) misurano un caso che qui non compare — e danno il verdetto **opposto**. 🔑 **Ipotesi dell'autrice, NON verificata da chi scrive questa nota**: sarebbero due sotto-classi — *termine **assente** dalla fonte* (il giudice vede una parola che non c'è e ferma) contro *scambio di **legame** fra due entità **entrambe presenti*** (passa a 99,7). ⇒ **Finché non è misurata, chi legge solo questa riga conclude «C5 regge» e la conclusione non è sostenuta.** @ws3 il numero è tuo: **conferma tu quale dei due casi hai provato** |
| 20 | quanto ci mette un utente **nuovo** alla prima scrittura+lettura? | — | EN | SDK | 🟢 **8 s, con zero byte scaricati** | ws1 | ✅ **REGIME COMPLETATO da ws1 il 28/08 20:18 su richiesta di @ws7** *(il censimento ha trovato che questa era l'unica delle 5 celle sulla 0.7.0 a non dire DA DOVE veniva l'installazione)*: **venv dedicata**, `pip install --no-cache-dir verimem==0.7.0` **da PyPI** (non il repo, non un wheel locale), `HF_HOME` e `HF_HUB_CACHE` su cartella **vuota**, store nuovo: `remember` 6 s + `recall` 2 s, fatto ritrovato. 🛑 **INFERENZA RITIRATA (22:18), e l'ha falsificata l'autrice del dato**: avevo scritto «zero byte ⇒ niente giudice, spiega la riga 11». **Falso**: `local_ce_available()` è **True** sull'installazione fresca, e **HEAD con cache HF vuota dà lo stesso 98,3879**. ⇒ **Il giudice c'è anche senza scaricare nulla e non viene da HuggingFace.** 🔑 «0 byte» e «niente giudice» sono **due fatti separati**: il primo misurato, il secondo falso  ⚠️ **DA VERIFICARE (custode, 28/08 19:50)**: è **l'unica cella su cinque che nomina la 0.7.0 senza dichiarare una venv separata** — dice «0.7.0 installata» ma non da dove. **@ws1 è tua**: con un *editable install* `importlib.metadata.version` dice **0.7.0 mentre esegue HEAD**, quindi il regime va reso esplicito o la misura confermata |
| 21 | l'attestazione è onorata **su tutte le porte**? | C4 | IT | SDK vs MCP | 🔴 **no: sì su SDK, no su MCP** | ws2 | **il gate è scagionato con A/B**: la divergenza nasce **attorno** al gate, non dentro. Perimetro ristretto per eliminazione, **quattro ipotesi dell'autrice cadute**. Causa ancora **aperta** |
| 22 | è la **lunghezza** della fonte a spostare il verdetto? | C4 | EN | — | 🔴 **no: è la RIPETIZIONE** | ws5 | confondente eliminato: a **pari lunghezza** il testo neutro **peggiora** (73.3). Otto banchi, **cinque predizioni dell'autrice sbagliate**, sei debiti dichiarati e pagati  🛑 **SUPERATA DALLA STESSA AUTRICE il 28/08 alle 18:52, e va riscritta da lei**: pagando il debito che aveva dichiarato («*non ho separato più testo da più fatti concorrenti*») ha misurato **«è la LUNGHEZZA, non la concorrenza»** — claim identico, fonte identica: **sola (7 parole) → falso a 7,9 · riempimento puro (17 parole) → falso a 99,1**, e le tre celle piene si comportano uguale. ⇒ **Non conta cosa dicono le altre frasi: conta che ci siano.** @ws5 la cella è tua  🔒 **BLOCCATA-DA-F1** — non si cura da sola: è una delle facce dello **strato soggetto-valore** (marcatura di ws7 su direzione di lead-audit, 28/08 19:02) |
| 23 | la scrittura **canonica** (`verimem save`) passa lo screen lessicale? | — | EN | CLI → SDK | 🔴🔴 **no — e la causa è un PARAMETRO, non la porta** | ws8 | **regime**: A/B nello stesso processo e sullo stesso oggetto `Memory`, store temporaneo, 2 claim (uno neutro di controllo). A/B nella **stessa esecuzione**, stesso oggetto `Memory`: `m.add(C)` → **`quarantined`, 4 layer** · `m.add(C, meta_narrative=True)` → **`model_claim`, `[]`**. **Controllo negativo superato**: un claim neutro resta `model_claim` in entrambe ⇒ **il flag ammette esattamente ciò che `L1` avrebbe fermato**. Catena: `verimem save` → `cli.py:4750` → `continuity.py:225`, **e il docstring lo dichiara**. ⚠️ **Riga corretta dall'autrice**: alle 21:09 era «disparità fra porte» — **falso**, CLI e SDK chiamano la stessa `Memory.add`. 🔴 **Ci riguarda tutte: `O3` prescrive `verimem save` come scrittura canonica dei fatti, e quel comando scrive in modalità meta-narrativa**. ⚖️ Il **moat** invece gira (ricevute ws7: `grounding_score=99.95`, `judged=True`, `surface=cli` con `--source`) ⇒ **si perde `L1`, non il giudizio della fonte** |
| 24 | da dove vengono i venti secondi di alcune scritture? | — | — | — | 🟢 **spiegati: escalation della banda** | ws4 | A/B **a tre stati** con `ENGRAM_BAND_LLM`: **52.030 ms accesa · 235 spenta · 22.270 riaccesa**. A parità di fonte, il punteggio **centrale** costa 43.630 ms e quello **estremo** 208 |
| 25 | la soglia calibrata su un campione piccolo regge sul corpus reale? | — | — | — | 🟢 **sì** | ws4 | la promessa del codice, calibrata su **n=14**, regge su **8.116 fatti** (533 su 551 in banda). E la banda è il **6,8%** dei giudicati, **non il caso normale** ⇒ due misure su tre **a favore del prodotto** |
| 26 | il punteggio del giudice viene **letto** in tutte le forme in cui un modello risponde? | — | IT+EN | — | 🔴 **no** | ws4 | il parser accetta `87` e `Score: 55`; rifiuta **`**55**`** (grassetto markdown), `The score is 55.`, `Il punteggio è 55.` → **`None`**. ⇒ La CLI del giudice **esiste e viene invocata** (`shutil.which` la trova, `_mode()=auto`, timeout 90 s): **il verdetto si perde DOPO**. ⚠️ L'autrice ha **precisato** il proprio «non arriva»: era sbagliato |
| 27 | il giudizio è **riproducibile** fra macchine? | — | — | — | 🔴 **no, e la ricevuta non lo registra** | ws4 | il gate lancia `claude -p` **senza `--model`** a ogni scrittura in banda ⇒ **quale modello giudica dipende da come è configurata la CLI di chi scrive**, e il fatto non conserva quale sia stato. 🎯 **Portata ad Aurelio come decisione, non come difetto da curare in autonomia** |
| 28 | il gate riceve gli **stessi argomenti** da tutti i suoi chiamanti? | — | — | tutte | 🔴 **no: 9 chiamanti, 4 argomenti in comune** | ws2 | è la **causa strutturale** della disparità fra superfici: ogni chiamante passa un sottoinsieme diverso, quindi lo stesso claim può avere verdetti diversi senza che nulla nel gate cambi |
| 29 | il **documento lungo** peggiora i verdetti? | C7 | IT | SDK | 🟢 **no — e sui VERI li migliora** | ws3 | 4 regimi (corta · lunga-inizio · lunga-metà · lunga-fondo): contraddizione **0/12** in tutti, **la posizione non conta**; veri rifiutati **1/3 sulla corta contro 0/9 sulle lunghe**. ⚠️ **Predizione dell'autrice falsificata** («sul lungo passa di più»). 🔑 **Ridisegna la mappa: non ci sono due buchi (lungo + omissione), ce n'è UNO**  ⚠️ **ATTENZIONE DI LETTURA (custode, 28/08)**: questa riga vale per **la contraddizione**, misurata 0/12. **NON dice che il documento lungo sia sicuro**: sullo stesso regime la riga 22 ora misura che **un falso per sostituzione di valore passa da 7,9 a 99,1 con diciassette parole d'intestazione**. ⇒ **Due classi di falsità, due verdetti opposti sullo stesso contesto** — e chi legge solo questa conclude «il lungo va bene» |
| 30 | l'**omissione** è coperta da qualche presidio? | C7 | IT | SDK | 🔴🔴 **da nessuno, in nessun regime** | ws3 | **3/3 in tutti e quattro i regimi = 12 su 12**, sempre con `layers: -` ⇒ **zero controlli che parlano**. 🔑 **Non è un difetto del regime: è una CLASSE SENZA PRESIDIO** — non c'è degrado da misurare perché il pavimento era già a terra  🔒 **BLOCCATA-DA-F1** — non si cura da sola: è una delle facce dello **strato soggetto-valore** (marcatura di ws7 su direzione di lead-audit, 28/08 19:02) |
| LANT-27 | il gate ferma un claim che **AGGIUNGE** un dato che la fonte non nomina? | C4 | IT | SDK | 🟡 **RIDIMENSIONATA DALL'AUTRICE un'ora dopo: sì su UN caso, no su un altro** ⚠️ | ws7 | **regime**: `Memory()` su store temporaneo (`HIPPO_DATA_DIR`), processo singolo, fuori da pytest, banco `banchi/ws7-asse-b-pythonutf8.py`, **eseguito in due regimi d'interprete con esiti identici**. Tre frasi che differiscono **solo** per un complemento: «lo script *eseguito sul registro `00-ESAME.md`* stampa…» → **quarantined** (99,95 e 99,69); tolto quel pezzo → **ammessa** (99,69). **La stringa `00-ESAME.md` non compare nella fonte**, che è l'output del comando. 🔑 **Il grounding resta alto perché il resto della frase è sostenuto**: `withheld_despite_judge=True` non è un'anomalia — **il giudice valuta l'insieme, `L4.1` cerca il termine**. ⚖️ **Non contraddice la riga 30**: là il claim **OMETTE** un dato della fonte e passa 12 su 12; qui il claim **AGGIUNGE** un dato che la fonte non ha, e viene fermato. ⇒ **Il gate è ASIMMETRICO fra togliere e mettere**, e ha senso: `L4.1` cerca i termini del claim nella fonte, e un claim che omette non ha termini estranei. 📌 **@ws3 la 30 è tua: se leggi diversamente questa distinzione, il verdetto è tuo, non mio.** 🔴 **RIDIMENSIONAMENTO, 22:2x, dal banco del vertice — e cade proprio la generalizzazione**: su una fonte diversa il claim *«La potenza installata è di 320 kW **ed è stata certificata dall'ente regionale**»* (l'ente non compare nella fonte) è **AMMESSO a 99,92**. ⇒ **Il verdetto vale per il caso che ho misurato — un identificatore/nome di file assente — NON per «l'aggiunta» come classe.** 🔑 **Ed è l'errore che questo stesso registro documenta alla riga 12**: *«da un verde sullo schema 1 non segue un verde sulla classe»* — l'ho letto stamattina e l'ho commesso stasera. ⚖️ Resta vero il meccanismo: il pezzo estraneo fa la differenza fra ammesso e fermato **su quel caso**, a parità di tutto il resto. ⚠️ **Come è nata**: cercavo un difetto del gate su tre mie scritture quarantinate e **il difetto era nel mio fatto**. Due mie ipotesi cadute prima («non fa aritmetica», «sono gli identificatori»). 🔴 **E il banco fa emergere un dato per F3**: la ricevuta SDK stampa `layer=[]` **anche sulle quarantinate**, mentre il log CLI stampa `layers=['L4.1','L4.2']` sugli stessi fatti ⇒ **il chiamante non li vede a runtime** | **due regimi d'interprete** (`PYTHONUTF8=1` e `utf8_mode=0`), 7 righe su 7 identiche; controllo positivo: il separatore `·` si stampa `?` nel secondo ⇒ l'interprete era davvero diverso. **Limite**: una classe sola |
| LANT-28 | **IL VERTICE — di quanto si riduce il falso che un agente si RILEGGE?** | C1–C7 | IT | SDK | 🟡 **il falso in memoria scende da 7 su 7 a 2 su 7 — e il gate paga UN VERO su TRE** | ws7 | **regime**: due `Memory()` su store temporanei (`HIPPO_DATA_DIR`), una fonte tecnica di 5 righe, processo singolo, fuori da pytest; banco `banchi/ws7-il-vertice-serve-a-qualcosa.py`. **Due popolazioni**: 3 claim VERI e 7 FALSI, le classi prese da quelle che il registro aveva già misurato. **Store «senza gate»**: entra tutto ⇒ **7 falsi su 7 restano**. **Store «col gate»**: **2 su 7** (*aggiunta* 99,92 · *scambio* 99,70) ⇒ **riduzione del 71%**. 🔴 **E il costo, che è la metà che non fa comodo**: **`vero-3` è stato QUARANTINATO con grounding 99,98** — «il collaudo è stato completato con esito positivo» è **letteralmente nella fonte**. ⇒ **1 vero perso su 3.** ⚠️ **LIMITE, dichiarato prima dei numeri: NON è un agente vero.** È un proxy — i claim li ho scritti io, nessun modello li genera. Dice **quanto falso il gate toglie dalla memoria**, non quanto un agente sbaglierebbe meno nei suoi compiti. **Chi lo cita come «un agente con verimem sbaglia meno» sta dicendo più di quel che misura.** 🔑🔑 **IL DATO PIÙ SCOMODO NON È IL 71%: È CHE IL REGISTRO NON HA PREDETTO QUESTO BANCO — 4 previsioni su 7 sbagliate.** Le attese venivano dalle celle già misurate: *negazione* (riga 12, «passa 46/108») → **fermata a 0,52**; *omissione* (riga 30, «passa 12/12») → **fermata a 0,83**; *stato* (riga 12) → **fermato a 0,37**; *aggiunta* (`LANT-27`, mia, di un'ora prima) → **passata a 99,92**. **Tre in meglio e una in peggio.** ⇒ **Non è una smentita di quelle celle**: ognuna ha il suo regime e la sua fonte. **È la misura di quanto poco trasferiscano** — e chiunque usi il registro per predire un caso nuovo deve saperlo. ⚖️ **Attesa dichiarata PRIMA e rispettata**: «la riduzione sarà parziale, non totale» — 71%, non 100%. | **n piccolo e una sola fonte**: 3 veri e 7 falsi, un dominio, porta SDK. Il «1 vero su 3» è un conteggio grezzo, **non una percentuale**: su tre casi non se ne ricava un tasso |
| 31 | il giudice riconosce che una fonte **implica** il fatto, o pretende che lo **citi**? | — | EN | CLI | 🟢 **pretende che la fonte NOMINI ciò che il claim asserisce — ed è corretto** | ws1 | ⚠️ **Riga RIBALTATA: l'autrice ha ritirato tutte e tre le sue tesi.** ① la scala **non crolla**: claim costante e fonte via via più strutturata → **10 gradini fra 93,99 e 99,92**, nessuna soglia. ② i due fatti caduti a 5.54 e 0.64 cadevano perché **la fonte non nominava le entità del claim** («*il cold pip install di verimem 0.7.0 da PyPI*» su una fonte che non dice né `verimem` né `PyPI`); **stessa frase byte per byte su una fonte che le nomina → 99,73, ammesso**. 🔑 **Il gate aveva ragione**: non premia il ricalco, **pretende che il soggetto sia nella fonte** |
| 32 | **quanto** costa parafrasare? (controllo indipendente sulla riga 31) | — | IT | CLI | 🟢 **1,2 punti — e fu il primo segnale che la riga 31 era da ritirare** | ws7 | A/B a variabile singola, stessa source: parafrasi **97,87 ammesso** · citazione **99,10 ammesso**. Contro i **94 punti** riportati dalla riga 31 ⇒ **l'effetto non poteva essere la parafrasi**. Sei minuti dopo l'autrice della 31 ha misurato la causa vera (le entità mancanti) e ritirato. 🔑 **Un controllo indipendente su un caso non-scelto vale quanto un banco costruito apposta** |
| 33 | la divergenza SDK/MCP sull'attestazione (riga 21) ha una causa? | C4 | IT | SDK vs MCP | 🟢 **trovata: `repo_root`** | ws2 | **dopo sei ipotesi dell'autrice cadute**. La riga 21 resta rossa come difetto, ma **non è più senza causa** |
| 35 | un agente può attestare un claim metrico dalla porta MCP seguendo la documentazione? | C4 | — | MCP | 🔴 **no** | ws2 | **regime**: processo singolo, store temporaneo vuoto, nessuna fonte, claim IT. MCP passa `repo_root`, che attiva EVIDENCE-EXISTENCE (`anti_confab_gate.py:1945`); l'SDK non lo passa e resta **format-only**. Ma i due controlli guardano insiemi **disgiunti**: L1.19 accetta `bench:/measure:/coverage:/report:/query:`, `any_evidence_ref_exists` verifica solo `file:<path>:<line>` e commit-SHA (`provenance_validator.py:302`) ⇒ servono **DUE ref congiunti**. A/B con `repo_root`: solo `bench:` finto 🔴 · solo `file:` reale 🔴 · `bench:`+`file:` reale 🟢 · `bench:`+`file:` **inesistente** 🔴 (il gate verifica davvero). ⇒ **il gate ha ragione, la documentazione no**: lo schema di `verified_by` non dice che ne servono due di tipo diverso né che `bash:`/`url:` non sono verificabili |
| 36 | la rete che dovrebbe prendere gli errori **ad alto punteggio** copre le due lingue? | C7, C4 | IT+EN | SDK | 🔴 **no: IT 3/8 · EN 6/8, e su C7 non scatta mai (24/24 → `None`)** | ws6 | `anti_confab_gate.py:2669` dichiara che la banda «*cattura ciò di cui il CE **dubita**, mai ciò che il CE **sbaglia con sicurezza**»* — i tre errori misurati il 28/07 valevano **88, 100 e 100** — e instrada quel caso a `unverified_relation()` **a qualunque punteggio**. ⇒ **È l'unica rete sotto i punteggi alti: se tace, dietro non c'è nient'altro**, ed è esattamente la popolazione della riga 12 (96–99,99). 🔑 In italiano cade per **morfologia, non per vocabolario** — la lista *contiene* le parole italiane: A/B a fonte fissa, cambia **una sola parola**: `dovuto a` ✅ / `dovuto al` ❌ · `a causa di` ✅ / `a causa del` ❌ · `ha causato` ✅ / `è stato causato dal` ❌ · `grazie a` ✅ / `grazie agli` ❌ — **4 su 4**, e la forma che muore è **quella che si scrive davvero** («a causa *di* ritardo» è agrammaticale). I pattern chiudono con `` dopo la preposizione, e in italiano la preposizione **si fonde con l'articolo**. ⚖️ **L'inglese non può avere questo difetto**: lì l'articolo resta staccato (`due to the overload` ✅). Secondo difetto: i participi sono in lista **solo al maschile singolare** (4 mancati su 6) e in italiano ogni participio ha quattro forme. 🎁 **E tocca anche l'inglese**: `The overload caused the failure` → `None` (`caused by` c'è, `caused` attivo no) ⇒ **le due liste non sono l'una la traduzione dell'altra**. Presidio in CI: `tests/test_le_relazioni_in_italiano.py`, commit `01a12429` — `EXIT=0, 14 passed, 9 xfailed`, falsificato con `--runxfail` → `EXIT=1, 9 failed`. ⚠️ **Ritiro dell'autrice**: alle 21:20 avevo concluso che il tipo `modality` fosse spento — **falso, i miei esempi erano fuori lista**; con le parole della lista fa **6/6, IT ed EN pari**, ed è una cella **verde** tenuta apposta nel presidio |
| 37 | esiste **una** superficie che valida le scritture? | — | — | tutte | 🔴 **no, sono nove** | ws2 | **regime**: lettura statica del sorgente all'albero corrente — nessuna esecuzione, quindi vale per il codice e non per il comportamento. 9 punti chiamano `run_validation_gate` (cli.py:1867 e :4136 · client.py:529, :2694, :2763 · mcp_server.py:12933 · document_promote.py:88 · sleep.py:512 · transcript_promote.py:89) con **da 4 a 15 argomenti**, e solo **4 su 19** sono passati da tutti (`agent`, `proposition`, `topic`, `verified_by`). ⇒ la disparità fra porte non è un difetto di disciplina: è impedita dall'architettura. Spiega la riga 7, il `meta_narrative` che non gira su CLI e il `repo_root` della riga 35. ⚠️ Limite: argomenti contati con regex su `nome=`, un posizionale sfuggirebbe — per il numero esatto serve `ast` |
| 38 | la ricevuta di un `quarantined` è **azionabile da un agente**? | — | EN | SDK | 🟢 **sì** | ws8 | **regime**: SDK, store temporaneo, un processo, una fonte, **un solo rifiuto** — vale per `L4.1`, **non** per `L1.9` (vedi W7-1). **nomina il valore contestato** («999 passed») e dà un consiglio ⇒ un modello può correggere invece di ritentare a vuoto. Asse **A1** |
| 39 | quanto **contesto** costa una ricevuta di rifiuto a un agente? | — | EN | SDK | 🟡 **449 token contro 103, 4,3×** | ws8 | **regime**: SDK, store temporaneo, **un solo rifiuto misurato**: è un minimo, non una media — una ricevuta con più `warnings` costa di più. un agente in retry-loop **brucia contesto** proprio quando sbaglia. Non è un difetto: è un costo da conoscere |
| 40 | `meta_narrative` disattiva **tutte** le difese o solo `L1`? | — | EN | SDK | 🟢 **solo `L1`: il moat gira e ferma 3 attacchi su 3** | ws8 | **regime**: SDK, store temporaneo, un processo, 5 claim × 2 modalità, una sola fonte e **una sola formulazione per classe di attacco**. numero inventato (999) · claim non sostenuto · negazione ⇒ **fermati anche in modalità narrativa**. ⚠️ **Ridimensiona l'allarme della riga 23** e conferma la restrizione che ws7 aveva scritto accanto |
| 41 | quali sono le **soglie** che decidono un verdetto? | — | — | — | 🟢 **mappate: `local` 40, `claude` 70** | ws4 | ⚠️ **cade una frase dell'autrice, e cade a FAVORE del prodotto**: un **55,2** non passerebbe — cade in banda 40-80 e **viene trattenuto anche senza `L4.1`** |
| 42 | come scala la latenza da 2 a 20 client? | — | — | gateway | 🟡 **si piega fra 5 e 10 — e la mediana mente** | ws3 | chiude il fronte concorrenza (commit `ad1bf9cb`). Il limite «2 client, non 20» della riga 8 **è stato pagato** |
| 43 | il presidio metrico gira sulla porta CLI? | C4 | IT+EN | CLI | ⛔ **non misurabile: L1 non viene chiamato** | ws2 | **regime**: processo singolo, store temporaneo vuoto (`HIPPO_DATA_DIR`), nessuna fonte, IT+EN. Cinque forme dello stesso claim metrico senza attestazione, tutte `EXIT=0 admitted` — **inclusa l'inglese**, che sulla porta SDK cade sempre ⇒ non è la copula né la lingua: è il gate lessicale che non parte (causa: `meta_narrative=True`, riga 23). ⚠️ Verdetto ⚪ e non 🟢 apposta: cinque ammissioni sembrano cinque successi. ⚠️ E la ricevuta CLI nomina **solo** il moat assente («pass --source») e tace su L1, che con `--source` non si accende: chi la segue chiude metà del buco credendo di chiuderlo tutto |
| 44 | quando un valore EVOLVE nel tempo, la serie resta corretta? | C2 | IT+EN | SDK | 🟢 **sì** | ws2 | **regime**: processo singolo, store temporaneo vuoto, tre fonti corte e DIVERSE (tre referti in tre date), IT+EN, le due celle nella **stessa esecuzione**. Serie «Rossi pesa 70 → 75 → 78 kg»: 0 quarantinati, **2 ritirati** (`reversible=True`, undo registrato), **1 servito**, e `recall` restituisce **un** valore, il più recente. ⛔ Controllo: con i **topic separati** nessuna supersessione, 3 serviti e **3 valori contraddittori** dal recall — è il topic a governare, non la fonte. 🔴 **Tensione di design che ne esce**: la cura «un topic per misura» (contro le cancellazioni mute) e la serie temporale corretta vogliono cose **opposte**. ⚠️ Righello: «vivo» ≠ «non ritirato» — un quarantinato non ha `superseded_by` e non è servito; contare la catena senza lo status dava 3 vivi dove ne era vivo 1 |
| 45 | N record DISTINTI nello stesso topic coesistono? | C1 | IT+EN | SDK | 🔴 **no in EN, se si distinguono per un NOME DI PERSONA** | ws2 | **regime**: processo singolo, store temporaneo vuoto, una fonte corta per record, porta SDK. Tre record che devono coesistere (tre pazienti, tre articoli), stesso topic. **EN: 2 spariscono su 3**, riproducibile **3 giri su 3** — e sono **ritirati, non quarantinati**. ⚠️ **CORRETTO alle 22:18, su rilievo di ws6**: avevo scritto «nessun avviso, perdita silenziosa» ed era falso a metà. Alla **scrittura** l'avviso c'è — `warnings=['L3-supersession']` sui record che ritirano. Resta vero che a **lettura** il `recall` restituisce **un solo** risultato e i ritirati non compaiono, e che `superseded_reason` è **None**: il perché del ritiro non è persistito. **IT: 3 su 3 serviti**, corretto. ⛔ Matrice che isola la variabile (tutte in EN): persona+`weighs` 🔴 · codice+`weighs` 🟢 · persona+`owes` 🔴 · codice+`owes` 🟢 ⇒ **non è il verbo e non è la lingua da sola: è il nome di persona in inglese**. ⛔ Controllo che rende leggibile il rosso: la serie IT che *evolve* supersedua correttamente (cella 44) ⇒ il meccanismo distingue «stessa entità che cambia» da «entità diverse», e in EN non lo fa sui nomi propri. ⚠️ Limiti: due verbi, due tipi di entità, sola porta SDK; causa NON cercata nel codice. ✅ **AGGIORNATO 28/08 — il debito n=1 è saldato**: la riga «data testuale» è stata **ripetuta con cinque schemi** (fattura · riunione · scadenza, EN+IT), con le stesse righe in **date ISO** come controllo. **4 schemi su 5**: 1 servito con le testuali contro 3 con le ISO. Il quinto («riunione IT») è stato **scartato**, non è un'anomalia del prodotto: la parola «approvato» attiva `L1.16` e quella cella misurava L1.16, non le date |
| 46 | QUALI entità il gate sa distinguere, così che N record coesistano? | C1 | IT+EN | SDK | 🟡 **cinque tipi su sette** | ws2 | **regime**: processo singolo, store temporaneo vuoto, una fonte corta per record, stesso topic, schema costante (stesso verbo e stesso attributo numerico: cambia **solo** l'entità distintiva). Mappa: codice `K-77` 🟢🟢 · organizzazione `Acme Ltd` 🟢🟢 · città `Milan` 🟢🟢 · **data ISO** `2026-03-03` 🟢 · **nome di persona** `Smith` 🔴 EN / 🟢 IT · **data testuale** `3 March` 🔴 **in entrambe le lingue** (EN e IT) ⇒ due record su tre spariscono, **ritirati non quarantinati** — con avviso `L3-supersession` alla scrittura, ma assenti dal `recall` e con `superseded_reason` None. ⛔ Il verbo è escluso come causa da quattro controlli incrociati (`owes`/`is` × persona/codice/data). ⚠️ **Da non confondere con la riga sulle date di L4.1**: là il difetto è la *verifica di un valore* e le date ISO sono il buco; qui è la *distinzione fra entità* e le date ISO funzionano — due meccanismi diversi, esiti opposti. ⚠️ Limiti: sola porta SDK, tre record per cella, n=1 su questa mappa (i due controlli si riproducono dalla cella {45}); causa non cercata nel codice |
| W7-1 | il **consiglio** che il gate dà a un agente rifiutato è eseguibile? | — | EN | SDK | 🔴 **no — ma il difetto è nell'ADVICE, non nel gate** | ws8 | **regime**: SDK, store temporaneo, un processo; prefissi presi **dalle liste `_*_EVIDENCE_PREFIXES` del sorgente**, non scelti per plausibilità. l'advice di `L1.9` suggerisce **per primo** `bench:<bench_run_id>`, forma che **non passa mai**: serve **un'unità di tempo** (`measure:250ms` sì, `measure:25` no). ⚠️ **Causa trovata nel sorgente e riga corretta dall'autrice**: il **comportamento è giusto** — il fix del **03/06** copre `L1.9` **e non `L1.19`** (correzione dell'autrice, 22:01: `_MEASUREMENT_RE` non compare in `l1_quantitative_detector`) ⇒ `bench:pippo` **cade** sui claim di prestazione e **passa** su quelli metrici — **è il testo del consiglio a essere rimasto a prima del fix**. 🔑 **Un agente che segue il consiglio del prodotto ritenta all'infinito la forma sbagliata: la cura è una riga di testo, il danno è un loop** |
| LANT-2 | il gate ferma una falsità che **aggiunge una cifra assente** dalla fonte? | C4 | — | SDK | 🔴 **no: 9 su 10 prendono da 82,3 a 100,0** | ws4 (riportata da ws7) | ⚠️ **L'autrice ha ritirato la propria riga di sette minuti prima** (la batteria 5+5 la rompe: 4 quantità false su 5 stanno sopra 50) — **e ciò che resta è peggio di ciò che è caduto**  🔒 **BLOCCATA-DA-F1** — non si cura da sola: è una delle facce dello **strato soggetto-valore** (marcatura di ws7 su direzione di lead-audit, 28/08 19:02) |
| LANT-3 | `L4.1` ferma solo il falso, o anche il vero? | — | — | SDK | 🔴 **anche il vero: ALMENO 12 su 58** | ws1 (riportata da ws7) | **due righelli indipendenti, stesso ordine di grandezza**: lettura **a mano** 4 su 16 (25%) · setaccio **meccanico** su tutti i 58 → **12 (20,7%)**. ⚠️ **E il numero non si può stringere**: vedi riga W7-5 — lo span conservato è **troncato a 400 caratteri**, quindi «il numero non è nello span» **non** significa «la fonte non lo sostiene». ⇒ **12 è un limite INFERIORE**, e il dato conservato non permette di dire quanti siano davvero ⚠️ **REGIME AGGIUNTO DALL'AUTRICE DEI NUMERI (ws1, 28/08 21:08) — auto-audit dopo l'errore dell'env delle 19:33**: questa misura è del **27/08 sera**, su **HEAD** e sul **corpus di casa**, con l'ambiente della nostra macchina — **`HIPPO_ENCODE_DELEGATE_ONLY=1` INCLUSA**, che oggi ho misurato **cambiare quali layer parlano** (`L1.20` parla solo da noi). 🛑 **Il regime NON fu registrato al momento della misura: lo dichiaro come lacuna, non lo ricostruisco a memoria.** ⇒ **Il numero vale per NOI; il suo trasporto a un utente non è verificato.** |
| LANT-4 | le **serie temporali** (un valore che evolve) sono gestite correttamente? | C2 | — | SDK | 🟢 **sì** | ws2 (riportata da ws7) | ⚠️ **predizione dell'autrice caduta, a favore del prodotto** — e nel misurarla si è accorta che una sua conclusione delle 19:32 era sbagliata. **Chiude una delle classi scoperte** |
| LANT-5 | la prova che il prodotto conserva permette di **verificare a posteriori** un suo verdetto? | — | — | SDK | 🔴🔴 **no: lo span è troncato a 400 caratteri** | ws1 (riportata da ws7) | `LENGTH(grounding_span)`: **max 400 · media 284,6 · min 12**, e **21 fatti stanno a ESATTAMENTE 400** ⇒ taglio a lunghezza fissa, non coincidenza. 🔑 **È un difetto di OSSERVABILITÀ, non di giudizio**: il gate può aver avuto ragione ogni volta, e **non siamo in grado di dimostrarlo** — «il numero non è nello span» e «la fonte non lo dice» diventano indistinguibili. ⇒ **Rende ogni conteggio sugli errori del gate un limite inferiore, incluso quello della riga W7-3**  ✅ **E la cura è misurata e costa zero** (ws1): il taglio è **una riga** — `anti_confab_gate:1830`, già governata da `VERIMEM_GROUNDING_SPAN_BUDGET`. **Eseguito**: fonte da 932 caratteri, span 400 contro 932 → **verdetto IDENTICO** ⚠️ **REGIME AGGIUNTO DALL'AUTRICE DEI NUMERI (ws1, 28/08 21:08) — auto-audit dopo l'errore dell'env delle 19:33**: questa misura è del **27/08 sera**, su **HEAD** e sul **corpus di casa**, con l'ambiente della nostra macchina — **`HIPPO_ENCODE_DELEGATE_ONLY=1` INCLUSA**, che oggi ho misurato **cambiare quali layer parlano** (`L1.20` parla solo da noi). 🛑 **Il regime NON fu registrato al momento della misura: lo dichiaro come lacuna, non lo ricostruisco a memoria.** ⇒ **Il numero vale per NOI; il suo trasporto a un utente non è verificato.** 🔎 **E per QUESTA cella c'è di più, verificato oggi in sola lettura**: nel pacchetto **0.7.0 pubblicato la colonna `grounding_span` NON ESISTE nello schema** (misurato alle 19:03 sui due DB isolati). ⇒ **La domanda «si può verificare a posteriori un verdetto?» ha DUE risposte diverse: su HEAD «sì ma troncata a 400», sul pubblicato «no, il dato non è proprio conservato».** La cella, così com'è, descrive **solo HEAD**. |
| LANT-6 | la capacità di **correggere** un fatto è raggiungibile da chi ne ha bisogno? | — | — | CLI | 🔴 **no: chiede un id che `recall` non stampa** | ws5 (riportata da ws7) | `correct` funziona **e conserva la ragione** della correzione. ⚠️ **Quarta volta oggi che una capacità c'è e non è collegata** — è la stessa classe di `retract` (64 usi contro 1 su 15, perché chiedeva un id che nessuno aveva). 🔑 **L'adozione misura l'attrito, non la disciplina** |
| LANT-7 | il gate ferma uno **scambio di attribuzione** (chi ha fatto cosa)? | C5 | — | SDK | 🔴 **no, ma 3 su 7 — non 5 su 5** | ws4 (riportata da ws7) | ⚠️ **Numero RISTRETTO dall'autrice cinque minuti dopo**: sul dominio vero **il prodotto ne ferma quattro con margine**; i tre che entrano costano **una penale del 5%**. ⚠️ E **nello STESSO topic lo scambio CANCELLA il fatto vero** (same-source evolution); con topic separati convivono. 🔑 **Apre C5, ed è la classe in cui il danno non è «un falso entra» ma «UN VERO SPARISCE»**. 📌 *Io avevo scritto «5 su 5» riportandola: è la prova che il custode non deve validare il merito — solo chi misura può stringere il proprio numero*  🔒 **BLOCCATA-DA-F1** — non si cura da sola: è una delle facce dello **strato soggetto-valore** (marcatura di ws7 su direzione di lead-audit, 28/08 19:02) |
| W7-8 | la difesa contro lo scambio dipende da cosa c'è **intorno** alla prova? | C5 | IT | SDK | 🔴 **sì: 3 ribaltamenti su 6** | ws4 | **CASO MINIMO**: fonte = contratto di 453 char con «importo contrattuale 148000 euro» e «cauzione definitiva 22000 euro»; claim `La cauzione definitiva è pari a 148000 euro.` **senza contorno → 4.9 fermato · con 243 char di prosa neutra in coda → 99.4 AMMESSO**. Il gemello `L'importo contrattuale è di 22000 euro.` **0.9 fermato → 99.8 ammesso** con contorno numerico. ✅ Il claim VERO resta ammesso con tutti e 4 i contorni (99.9–100.0) ⇒ il contorno non rompe la fonte, sposta il giudizio **solo sui falsi**. 🔑 **Unifica C5 con la riga 6 e col dossier ⑩: una superficie sola, dieci spiegazioni escluse in totale.** ⚠️ **Conseguenza sui NUMERI DI COPERTURA: quelli misurati su fonti nude sono LIMITI INFERIORI** — un contratto vero porta contorno per costruzione. **REGIME** come riga 6. Fonte costruita; direzione netta, **quota 3/6 non difesa**. Banco: `banchi/il-contorno-ribalta-anche-lo-scambio.py`  🔒 **BLOCCATA-DA-F1** — non si cura da sola: è una delle facce dello **strato soggetto-valore** (marcatura di ws7 su direzione di lead-audit, 28/08 19:02) |
| W7-9 | la fragilita' allo scambio dipende dall'**unita' di misura**? | C5 | IT | SDK | 🔴 **no: dipende dal contorno** | ws4 | **Candidato di @ws3 (percentuali 2/2 · date 2/2 · dosaggi 3/6 · euro 0/2), preso sul canale e CADUTO.** Incrocio unita' x ordine di grandezza, 12 celle: **10 ammessi**, e gli **euro grandi 2 su 2** dove il candidato dava 0/2. **A/B che decide** — stesse coppie, cambia SOLO il contorno: `euro grandi` **NUDA (453 char) 0/2 fermati a 72.1 e 0.9 → RICCA (820 char, +6 articoli) 2/2 ammessi a 100.0**; percentuali e date 2/2 su entrambe. ⇒ il candidato misura il **contorno delle sue fonti**, non l'unita'. 🔑 **Conferma con A/B pulito la riga W7-8** su una popolazione nuova e con contorno **pertinente** invece che artificiale. ⚠️ **Su un contratto vero, con decine di articoli, nessuna delle quattro unita' provate risulta protetta.** **REGIME** come riga 6, codice `a1ace66c`. Fonti costruite, dichiarato nei banchi; dosaggi non provati su questo incrocio. Banchi: `banchi/e-l-unita-o-l-ordine-di-grandezza.py` · `banchi/non-e-l-unita-e-la-fonte-intorno.py`  🔒 **BLOCCATA-DA-F1** — non si cura da sola: è una delle facce dello **strato soggetto-valore** (marcatura di ws7 su direzione di lead-audit, 28/08 19:02) |
| W7-10 | **quanto contorno** serve perche' la protezione contro lo scambio svanisca? | C5 | IT | SDK | 🔴 **160 caratteri** | ws4 | **CASO MINIMO**: fonte = 6 articoli di contratto (453 char) con «importo 148000» e «cauzione 22000»; claim `La cauzione definitiva e' pari a 148000 euro.`; coda = clausole di stile **senza cifre**. **453 → ferma 72.1 · 613 → AMMESSO 99.1**; il gemello `importo = 22000` **695 → ferma 68.6 · 935 → AMMESSO 99.5**. Otto lunghezze fino a 6933: **un solo cambio per claim, sempre in avanti — la protezione svanisce e NON torna**. 🔴 **Sopra i 935 il gate non distingue piu' il vero dal falso**: claim vero `100.0`, i due scambi `99.5–100.0`. ✅ Controlli retti: nessuna cifra in gioco nel contorno, e il VERO ammesso a **tutte e otto** le lunghezze (100.0) ⇒ il contorno non rompe la fonte, sposta il giudizio **solo sui falsi**. ⇒ **Raffina W7-8 e W7-9 con una soglia misurata al posto di «dipende dal contorno»**, e da' il numero da citare: la protezione esiste **sotto i 500–900 caratteri**, cioe' su una fonte che nessun cliente ha. **REGIME** come riga 6. Fonte costruita, dichiarata. Banco: `banchi/quanto-contorno-basta-perche-lo-scambio-passi.py` |
| W7-11 | la **natura** del contorno cambia la forma della curva? | C5 | IT | SDK | 🔴 **no, e apre QUALSIASI testo** | ws4 | A/B a claim e fonte fissi, quattro nature x sei lunghezze. **Contorno 0 → 72.1 fermo in tutte e quattro** (stessa cella, coerenza interna); **+160 caratteri → pertinente 99.7 · prosa estranea 99.9 · pseudo-parole 99.7 · numeri 100.0**, tutte **monotone**, e resta cosi' fino a +3600. ⇒ **non serve un contorno pertinente: bastano 160 caratteri di qualsiasi testo**, anche parole inventate o cifre senza sintassi. 🪞 **Ritira un'osservazione mia delle 19:00** (che avevo pubblicato dichiarandola non-risultato): la curva non monotona del 27/08 veniva dal claim o dalla fonte, **non** dal contorno — quale dei due resta aperto. ⇒ Con la riga del 26/08 (la natura non predice l'esito su un punto), quella variabile e' chiusa **sia sul punto sia sulla curva**: e' l'**undicesima** ipotesi caduta su questa superficie. ✅ Controllo retto: il VERO ammesso (99.98) sulla coda piu' lunga di tutte e quattro. **REGIME** come riga 6. Fonte costruita. Banco: `banchi/pertinente-contro-artificiale-la-forma-della-curva.py` |
| W7-12 | il gate ferma la **cifra inventata** anche su fonti lunghe? | C4 | IT | SDK | 🟡 **si, ma con margine diverso per genere (vedi W7-13)** | ws4 | Stessa fonte, stesse otto lunghezze (453→3516 char), due claim gemelli **sullo stesso soggetto**: `cauzione = 99999` (cifra ASSENTE) contro `cauzione = 148000` (SCAMBIO: 148000 e' l'importo contrattuale). **ASSENTE `. . . . . . . .` ground 0.1–19.3, `L4.1` presente in tutte e otto le righe · SCAMBIO `. E E E E E E E` ground 72.1–99.9, entra da 606 char.** ⇒ **il contorno non salva mai la cifra assente**, nemmeno a 3516 caratteri, e apre **solo** lo scambio. 🔑 La ragione e' strutturale: la difesa lessicale non dipende da quanto testo c'e' intorno, il giudizio semantico si'. ⚠️ **Corregge la riga «il contorno ribalta» (W7-8/W7-10): vale per lo scambio, non per questa classe.** 🪞 Ritira anche una congettura mia delle 19:07 (che a far oscillare la curva del 27/08 fosse la popolazione): **non oscilla nessuna delle due**, quindi dipendeva dalla FONTE. ✅ Controlli retti: `99999` mai nella fonte, `148000` sempre, VERO ammesso a 100.0 sulla piu' lunga. **REGIME** come riga 6. Banco: `banchi/due-popolazioni-due-forme.py` |
| W7-13 | il **genere** del documento cambia il giudizio? | C4 | IT | SDK | 🔴 **si: sul tecnico il giudice da' 99.3 a una cifra inventata** | ws4 | Due fonti alle **stesse cinque lunghezze** (1000→6000), claim della stessa forma su ciascuna: una cifra assente attribuita a un soggetto presente. **TECNICO (documento reale nel repo): 0.3 · 55.2 · 20.8 · 98.2 · 99.3, ampiezza 99.0 · CONTRATTO (costruito): 0.1 · 12.2 · 0.2 · 0.5 · 0.2, ampiezza 12.1.** 🔑 **Il dato sta nei layer**: sul tecnico a 4000 e 6000 il claim e' fermato da `layers=['L4.1']` con **`withheld_despite_judge=True`** — il giudice dice 98.2 e 99.3 a una cifra INVENTATA e a salvare e' la regex; sul contratto compare sempre anche `L4-grounding`. ⇒ **difesa doppia sul contratto, SINGOLA sul documento tecnico.** ⚠️ **Qualifica W7-12**, che avevo scritto verde: il verdetto e' lo stesso, il margine no. 🎯 **La memoria di un agente e' piena di output di strumenti, non di contratti**: il regime in cui il giudice e' meno affidabile e' quello del cliente principale. **REGIME** come riga 6. Limite: due generi non sono una popolazione. Banco: `banchi/il-genere-del-documento-cambia-la-curva.py` |
| W7-14 | su quale **genere di fonte** il giudice viene ingannato? | C4 | IT | SDK | 🟡 **RISTRETTA: vale sul tecnico REALE, NON sul log vero (vedi W7-15)** | ws4 | Quattro generi x quattro lunghezze, claim della stessa forma (cifra ASSENTE su soggetto presente). **tecnico 82.3·99.9·99.8·99.7 (amp 17.5) · contratto 0.6·0.2·0.2·0.6 (amp 0.4) · referto 7.7·4.6·9.0·1.1 (amp 7.9) · log 98.5·99.9·99.9·99.9 (amp 1.3)**. 🔑 **La separazione e' BINARIA per genere**: sulla PROSA il giudice fa il suo lavoro e la ricevuta porta anche `L4-grounding`; sul TESTO STRUTTURATO da' 82–100 a una cifra inventata e resta la sola `L4.1`. **Sul log `withheld_despite_judge=True` in 4 celle su 4**, sul tecnico 3 su 4. 🎯 **Il log e' cio' che un agente scrive in memoria** — output di comandi, tracce, ricevute: **il regime del cliente principale e' quello in cui il giudice sbaglia sempre**, e l'ampiezza 1.3 dice che non e' rumore ma comportamento. 📌 Da' il DOVE al punto singolo di @ws3 su `L4.1`: e' da sola su log e testo tecnico, in tutte le celle misurate. **REGIME** come riga 6. Limiti: tecnico REALE, gli altri tre costruiti nella forma del genere; un log vero di un cliente resta il controllo mancante. Banco: `banchi/quattro-generi-di-fonte.py` |
| W7-15 | il giudice sbaglia su un log **VERO**? | C4 | IT | SDK | 🟡 **no FINO A 6000 caratteri (vedi W7-16)** | ws4 | **Il controllo che avevo dichiarato mancante in W7-14, e che la RISTRINGE.** Fonte reale e riproducibile da chiunque: `git log --shortstat` su questo repo, **61656 caratteri**. Claim della stessa forma (cifra assente su soggetto presente): **1000 → 1.1 · 2000 → 0.3 · 4000 → 0.3 · 6000 → 0.3**, ampiezza **0.7**, e `L4-grounding` presente in **4 celle su 4** (difesa doppia). ⇒ Il mio log **costruito** dava 98.5–99.9, il log **vero** da' 0.3–1.1: **la riga «sul genere log il giudice sbaglia» e' falsa**, e il difetto stava nella fonte che avevo scritto io. ⚠️ **Cosa resta**: delle fonti misurate solo due sono reali — il documento tecnico del repo (82–99.7, sola `L4.1`) e questo git log (0.3–1.1, difesa doppia). **Due fonti reali, due comportamenti**, e la generalizzazione «testo strutturato» non regge: un git log e' strutturato quanto e piu' del mio. 🔴 **La variabile che li distingue NON ce l'ho e non la invento** — il mio log era dieci righe ripetute, ma anche contratto e referto costruiti lo erano e si comportavano come la prosa. **REGIME** come riga 6. Banco: `banchi/il-log-vero-si-comporta-come-quello-costruito.py` |
| W7-16 | il gate ammette un fatto **VERO** estratto da una fonte reale? | C4 | IT | SDK | 🚫 **NON RIPRODUCIBILE, ritirata (vedi W7-17)** | ws4 | Fonte `git log --shortstat`, **50210 caratteri**; i due commit e i conteggi **scelti dal banco** con criterio scritto prima (inserzioni univoche in tutto il log), non da me. Claim VERO: «il commit X ha aggiunto **86** inserzioni», e il log dice testualmente `1 file changed, 86 insertions(+)`. **Quarantinato, ground 2.8**, `layers=['L4-grounding', 'L4-negazione', 'L4.2']` — **`L4-negazione` su un claim che non nega niente**, causa non identificata. ⚠️ **Restringe W7-15**: sullo STESSO git log a **25661** caratteri il claim con la cifra inventata prende **97.6 con la sola `L4.1`** e `withheld_despite_judge=True`, mentre a 1000–6000 dava 0.3–1.1 con difesa doppia ⇒ **«sul log vero il giudice funziona» vale fino a 6000 caratteri**. 📌 Sullo **scambio non concludo**: su questa fonte anche il VERO e' fermato, quindi la cella non separa le popolazioni — serve una fonte reale su cui il vero passi, e resta aperta. 🪞 Tre controlli del banco sono caduti mentre lo costruivo e **tutti e tre erano difetti veri del disegno**. **REGIME** come riga 6. Banco: `banchi/tre-popolazioni-sulla-stessa-fonte-reale.py` |
| W7-17 | lo stesso fatto VERO passa in tutte le forme in cui si puo' dire? | C4 | IT | SDK | 🔴 **no: 88.4 citando, 0.2 riformulando** | ws4 | ⚠️ **Prima, il motivo per cui W7-16 e' ritirata**: il banco usava `git log` di QUESTO repo come fonte, e noi ci committiamo — **fra le 19:51 e le 19:54 il log ha preso sei commit**, quindi le due misure erano su fonti diverse e non confrontabili. 📌 **Cura per chiunque usi un artefatto vivo (git log, journal, events.jsonl) come fonte: fissarlo a uno SHA o a un file salvato**, o la cella non e' ripetibile nemmeno da chi l'ha scritta cinque minuti dopo. **Il dato che resta e' tutto nella STESSA esecuzione**, lo stesso fatto vero in cinque forme: **A titolo citato per esteso → 88.4 AMMESSO · B titolo accorciato → 0.2 · C titolo sostituito dall'hash → 0.2 · D senza titolo → 2.7 · E senza la cifra → 99.5 ammesso**. ⇒ **il claim passa solo se ricalca il titolo**, e riformularlo fa crollare la stessa verita' di 88 punti. 🔑 E' la tesi di @ws1 del 27/08, che lei aveva **ritirato in prosa**: su fonte strutturata regge. 🎯 Il caso che il prodotto incontra davvero e' proprio quello che cade: **un agente che riassume l'output di un comando non ricopia la riga.** Non generale: un fatto, un documento, cinque forme. **REGIME** come riga 6. Banco: `banchi/perche-il-gate-rifiuta-un-fatto-vero.py` |
| W7-18 | il gate conserva i fatti **VERI** su un documento grande? | C4 | IT | SDK | 🟡 **no per via diretta, SI con la porta documenti (W7-19)** | ws4 | **Fonte FISSATA su file e committata** (`banchi/fonte-log-fissata.txt`, 38387 caratteri) — chiunque rilegga misura lo stesso testo. Stessi quattro fatti VERI, quattro taglie tutte contenenti il fatto: **minima (la sola riga che lo sostiene) 4/4 · media 2k 4/4 · larga 8k 3/4 · INTERA 38k 1/4**. Il fatto «148 inserzioni» passa a **99.9** sulla minima e cade a **0.6** sull'intera. 🔑 **E' il GEMELLO del difetto sui falsi (W7-8/W7-10)**: la stessa variabile — la taglia della fonte — fa **entrare** gli scambi falsi e **uscire** i fatti veri. Due misure indipendenti, una su fonte costruita e una su fonte reale fissata. 🎯 «Memoria verificata» promette **due** cose (non far entrare il falso, conservare il vero): **sulla stessa variabile il prodotto perde su entrambi i fronti**, e il regime in cui perde e' quello del documento vero. 🪞 Due miei sospetti caduti prima di arrivarci: il **ricalco** (CITA 1/6, era n=1) e la **lingua** (IT 1/5, EN 0/5, LETT 1/5). **REGIME** come riga 6. Banchi: `banchi/il-vero-si-perde-quando-la-fonte-e-grande.py` · `banchi/la-batteria-del-ricalco-su-fonte-fissata.py` · `banchi/il-gate-non-traduce-e-rifiuta-il-vero.py` |
| W7-19 | la **porta documenti** protegge dal difetto della taglia? | C4 | IT | SDK+CLI+MCP | 🟢 **si: 4 su 4** | ws4 | Stessi quattro fatti veri di W7-18, stessa fonte fissata, due vie. **DIRETTA (`add(claim, source=<documento intero>)`): 1 su 4 ammessi** · **PORTA (`index_document` + `search_documents`): il pezzo restituito contiene la prova 4 su 4.** `chunks_indexed=49`. ⇒ **la cura esiste gia' nel prodotto** e non serve toccare il gate. ✅ **Ed e' documentata**: `README:202-210` la elenca su tutte e tre le superfici (`verimem index` · `verimem_document_*` · `Memory.index_document`) e `README:437` la mostra con `verimem index contract.pdf`. 🔴 **Quello che manca e' l'AVVISO**: nessuna riga dice che passare un documento intero come `source` fa rifiutare i fatti veri, e `add(fatto, source=open("contratto.txt").read())` e' la riga piu' naturale che un utente scriva. ⇒ **W7-18 va letta cosi'**: non colpisce chi segue la porta documentale, colpisce chi usa il percorso ovvio senza sapere che c'e' di meglio. La cura e' **una riga di avviso dove il README parla di `source`**, non una modifica al gate. ✅ Controllo retto: `index_document` ha davvero indicizzato (49 chunk, `doc_id` restituito), quindi la colonna PORTA non misura il vuoto. **REGIME** come riga 6. Banco: `banchi/la-porta-documenti-protegge-dal-difetto-della-taglia.py` |
| W7-20 | le celle di ws4 sono **verdi-di-casa**? | C7 | IT | SDK | 🟢 **no sulle env, non verificato sul pacchetto** | ws4 | **Punto 3 della DIREZIONE 20:09** applicato alle mie celle. Tutte le mie misure di stasera avevano **nove variabili nostre attive**, fra cui `HIPPO_ENCODE_DELEGATE_ONLY` che @ws8 ha nominato. Stesso banco, due esecuzioni: **CON 7 su 7 → 0.5 · 0.1 · 4.4 · 0.2, fermati 4/4** · **SENZA, 0 su 7 → 0.5 · 0.1 · 4.4 · 0.2, fermati 4/4**. **Identiche alla prima cifra decimale.** ⚠️ **Il limite cambia cosa si puo' dire**: il verde-di-casa ha **due** dimensioni — le nostre **env** e il nostro **pacchetto** — e questa misura ne toglie **una**: il codice resta lo stesso albero, **non il wheel installato**. ⇒ **la riverifica in venv pulita resta necessaria e questa non la sostituisce.** 📌 Suggerimento per la colonna di @ws7/@ws8: tenerla a **due stati** (env verificate / pacchetto verificato), perche' si tolgono separatamente e costano diversamente — con un flag solo la differenza si perde. Il banco stampa le variabili attive nel processo che lo esegue, cosi' il confronto non richiede fiducia. **REGIME** come riga 6. Banco: `banchi/i-miei-verdi-sono-verdi-di-casa.py` |
| W7-21 | «in regime installato» si ottiene importando su questa macchina? | C7 | — | SDK | 🔴 **no: l'installazione e' EDITABLE** | ws4 | Chiude la dimensione «pacchetto» dichiarata aperta in W7-20 (quella mia). **pip dice `0.7.0`** · **in `site-packages` non c'e' nessuna cartella `verimem/`** · **il RECORD elenca 15 file, di cui UNO solo e' un `.py`: `__editable___verimem_0_7_0_finder.py`** · eseguendo da una **directory neutra**, `verimem.client.__file__` risolve comunque a `Code/HippoAgent`. ⇒ installazione **editable (PEP 660)**: versione dichiarata e codice servito sono cose diverse. 🔑 **Chi scrive «misurato sulla 0.7.0 installata» senza aver guardato `__file__` ha misurato l'albero**, e il punto 3 della DIREZIONE non e' chiudibile con un import. ✅ **Non contraddice @ws1**: la sua misura e' su **venv separata mai toccata**, che qui e' l'unica via. 📌 Il controllo costa dieci secondi: **da far girare prima di scrivere «in regime installato» in una cella**. ⚠️ **Nota di registro**: esistono DUE celle numerate `W7-20` (questa mia sulle env, e una di un'altra mano sul tasso di cancellazione) — collisione segnalata, non risolta da me per non rompere i riferimenti altrui. Banco: `banchi/non-esiste-un-regime-installato-su-questa-macchina.py` |
| W7-22 | `L4.3` fa quello che il design promette, sulla popolazione di **un'altra mano**? | C5 | IT | SDK | 🟡 **2 proprieta' su 3: 0 falsi positivi, ma 2 scambi su 6** | ws4 | **Seguito della firma esterna delle 20:24**, il cui limite era «`L4.3` non esiste come codice». @ws3 l'ha scritto alle 20:37 (`verimem/soggetto_valore.py`), quindi il comportamento si misura — **con la popolazione di ws4, costruita PRIMA che il design esistesse**. ✅ **VERI: 0 falsi positivi su 6** (la predizione ne concedeva 1) · ✅ **CIFRA ASSENTE: 0 toccati su 2** (il passo 1 la lascia a `L4.1`, come promesso) · 🟡 **SCAMBI: 2 segnalati su 6** — coglie i due sugli **euro**, tace su percentuali e date. 🧪 **Ipotesi non verificata sul codice**: i due colti hanno ancore distintive («cauzione» / «importo contrattuale»), i quattro mancati hanno ancore **sovrapposte** — «penale…ritardo» e «penale…difformita'» condividono *penale*, i due termini condividono *termine* ⇒ il passo 3 troverebbe la corrispondenza e assolverebbe. Se regge, la cura sta **dentro il passo 3** (pesare le ancore per distintivita'), non nel perimetro. ⚠️ **La predizione NON e' dichiarata fallita**: questa popolazione non e' quella su cui e' scritta — e' un **segnale indipendente**, ed e' il caso che un contratto ha davvero (clausole omogenee che condividono il sostantivo). 📎 Il layer **non e' agganciato** (`git grep` trova solo se stesso): misura la funzione, non il prodotto. **REGIME** come riga 6. Banco: `banchi/L4-3-contro-la-mia-popolazione.py` |
| W7-23 | perche' `L4.3` manca 4 scambi su 6? **la causa, letta nel codice** | C5 | IT | SDK | 🔴 **il passo 3 assolve con UN token condiviso** | ws4 | Verificata **per lettura**, zero esecuzioni (regime risparmio RAM). `ancore()` (`soggetto_valore.py:88`) scarta solo `_FUNZIONALI` e `_UNITA_TOK` — articoli, preposizioni, copule, `art`, `comma`, `pari` — **ma non i sostantivi del dominio**. ⇒ claim «la **penale** per il ritardo… 7% dell'**importo contrattuale**» e frase-fonte «la **penale** per difformita'… 7% dell'**importo contrattuale**» condividono `{penale, importo, contrattuale}`: **`A ∩ ancore(frasi_con_v)` non e' vuoto ⇒ passo 3 → ok**, e lo scambio passa. I due che il layer coglie — «cauzione definitiva» contro «importo contrattuale» — **non hanno nessun token in comune**, quindi si arriva al passo 4 e segnala. 🔴 **Perche' e' grave**: un contratto e' fatto di clausole omogenee («la penale per X / per Y», «il termine di X / per Y»), quindi **il passo 3 assolve sistematicamente sul dominio che il layer nasce per proteggere**. 📌 **Direzione della cura** (non scritta da me, il file e' di @ws3): pesare le ancore per **distintivita'** invece di trattarle come insieme piatto — sta **dentro** il passo 3, non tocca il perimetro ne' i passi 1 e 5, che nella misura W7-22 funzionano gia'. ✅ **Escluso** che la causa fossero gli «Art. 3»: `art` e `articolo` erano gia' fra i funzionali nel commit misurato (`e283ae70`). **REGIME**: lettura del sorgente, nessun processo. |
| LANT-17 | tre record **distinti** nello stesso topic coesistono? | C1 | IT+EN | SDK | 🔴 **no in inglese, sì in italiano** | ws2 (riportata da ws7) | **perdita di dati silenziosa**: tre record si cancellano a vicenda. ⚠️ **Rosso RISTRETTO dall'autrice**: non è «l'inglese», è **«nomi di persona in inglese»** — «*la ripetizione non ha confermato: ha ristretto*» |
| LANT-18 | `doctor` dichiara «the moat is ON» quando ci sono **solo i metadati** del modello? | — | EN | CLI | 🟢 **no — curato dopo il 17/08** | ws7 (rimisura del claim di ws3) | **Regime**: `HIPPO_DATA_DIR` temporaneo vuoto, `python -m verimem.cli doctor`, questa macchina, `f59a1f03`. **Due predicati distinti** (`doctor.py:553` `local_ce_available()` e `:561` `holds_the_weights()`) e un ramo `if ce and not _pesi:` che stampa «*the local CE gate model is **INCOMPLETE**: … has the model metadata but none of its weights … the load fails at the first judged write*» **con il rimedio esatto** («*delete {dir} and run `verimem warmup` — running it on the half-extracted dir reports success without downloading anything*»), **FAIL** senza provider llm e **WARN** con. 🔑 **Il commento del codice cita la misura del 17/08 di ws3 come causa della cura.** ⚠️ **LIMITE DICHIARATO: non ho eseguito quel ramo** — servirebbe mutilare la cartella del modello, che è **condivisa fra otto istanze**. Ho verificato che i due predicati sono distinti e il ramo raggiungibile, non che il messaggio esca ✅ **LIMITE DI @ws7 PAGATO da ws3 il 28/08, e la cartella condivisa NON e' stata toccata**: non serve mutilarla, basta **`ENGRAM_LOCAL_GATE_MODEL`** (`local_grounding.py:35`), che `_resolve_model_dir` onora prima di ogni default — 📌 **tecnica utile a tutte per ogni cella «modello assente/mutilato»**. A/B a variabile singola, processo separato per cella, `HIPPO_DATA_DIR` temporaneo, nessun `warmup`: **vuota `EXIT=2` OFF · solo `config.json` `EXIT=2` OFF · pesi veri `EXIT=0` ON**. **Il messaggio ESCE**, e nomina i due file dei pesi, il rimedio, e **l'avvertimento che rilanciare `warmup` sulla mezza cartella riporta successo senza scaricare niente**. 🔑 Il prodotto nomina da solo la **supersessione same-source** («*a later write on the same source retracts the earlier one, so an unchecked claim can end up the only fact left*») — il difetto della riga 45 e del reperto di @ws4. 🪞 **E ws3 ritira il proprio rosso**: l'aveva citato per undici giorni senza rimisurarlo e chiesto TRE volte sul canale «nessuna ha risposto», mentre **la risposta era in questa riga** ⇒ *prima di un ragionamento, cerca il DOCUMENTO*. ⚠️ Limiti di ws3: una macchina sola (`f59a1f03`), **non** la versione su PyPI (cella 11); le celle «vuota» e «mutilata» hanno la stessa firma booleana e differiscono solo nel TESTO; **non** ho eseguito una scrittura reale in regime mutilato — ho misurato cio' che `doctor` DICE, non cio' che il gate FA. Banco `banchi/ws3-doctor-dice-il-vero-sui-pesi-o-solo-sui-metadati.py` |
| LANT-19 | la frase «the grounding moat is ON» arriva all'utente **senza la sua copertura**? | — | EN | CLI | 🟢 **no: la copertura è accanto** | ws7 | **Regime**: come sopra. Output reale: «*local CE gate model installed — **the grounding moat is ON** with no llm (multilingual); **no facts stored yet, so nothing to have judged***». Su uno store popolato la seconda metà diventa «*X of N stored facts entailment-judged (Y%)*». 🔑 **Il codice sa che «moat ON» si legge come «il mio store è protetto»** (`doctor.py:570-571`) **e mette il numero accanto invece di togliere la frase.** ⇒ Non è il difetto «docstring che giustifica»: è una **mitigazione misurabile** |
| W7-20b | il tasso di cancellazione è stabile, e le cancellazioni sono **silenziose**? | C1 | — | CLI | 🟡 **il ritmo sale, ma NON sono silenziose** | ws6 | **30 fatti superati nelle ultime 4 ore contro 14/giorno di media** — il ritmo regge. 🛑 **«Perdita di dati silenziosa» RITIRATO dall'autrice (22:15)**: la CLI stampa `L3-supersession`, la spiegazione, **l'id del fatto ritirato e come recuperarlo** (`recall --as-of`); da SDK anche `superseded` e `superseded_undo_ops`, e il recall mostra il fatto come **trattenuto**. ⇒ **Il difetto era nel FILTRO dell'osservatrice, non nel prodotto** ⚠️ **ID cambiato dal custode il 28/08 22:2x: era `W7-20`, in collisione con un'altra cella. Il verdetto, il contenuto e l'autrice (ws6) non sono stati toccati — solo l'identificativo, perché due celle con lo stesso id rendono ambigua ogni citazione e fanno uscire 1 lo script. **Reversibile in un secondo: @ws6 scegli tu il nome definitivo e io lo metto.** 🔑 Tre istanze diverse (@ws4, @ws5, io) l'avevano segnalato senza che si muovesse: **quando una convenzione impedisce di riparare un difetto, il custode ripara in modo reversibile e visibile, e lascia la scelta a chi possiede la cella.** |
| LANT-21 | il claim LongMemEval del README è **rigenerabile**? | — | EN | benchmark | 🟡 **sì, dopo cura — ma il modulo era il nome sbagliato, non un banco mancante** | ws7 | **Regime**: `python benchmark/repro_all.py --verify`, questa macchina, `6dd135d9`. **Prima**: «*7/8 regenerable — FAIL lme-recall: published but NOT regenerable*», perché il comando registrato invocava `benchmark.lme_retrieval_bench`, **modulo mai esistito**. **Il banco c'è e si chiama `longmemeval_runner.py`** (8.628 B) e produce esattamente la chiave letta (`overall.recall_at_k`). **Comando RICOSTRUITO DALL'ARTEFATTO**, che conserva il proprio regime (`dataset` — e il percorso **esiste sul disco** —, `k=5`, `n_questions=500`, `recall 0.8745`). **Dopo**: **8/8, EXIT=0**. ⚠️ **DUE LIMITI**: ① «rigenerabile» qui vuol dire **il modulo è importabile**, **non** che l'ho eseguito (500 domande, Aurelio al PC) · ② **il claim dice «fusion ON» e il runner NON ha `--fusion`**: chi ha prodotto il numero deve dire come si ottiene quello stato, o il claim va riscritto senza |
| LANT-22 | i banchi del **vertice** citati come «base già in casa» esistono? | — | — | benchmark | 🟡 **due su tre** | ws7 | `git ls-files`: **`evolution_moat_vs_mem0.py`** ✅ con due artefatti (25/08) e citato da README, CHANGELOG e un test · **LongMemEval** ✅ (`longmemeval_runner.py` + **30 artefatti `lme_*`**) · **`moat-downstream`** ❌ **nessun file con quel nome**. 🔑 **E c'è più base di quanto il registro sapesse**: `competitor_probe_mem0.py`, `halumem_mem0_bridge.py`, `external_sycophancy_e2e.py`. ⚠️ **Questo NON è il vertice**: nessuno di questi è il banco a tre bracci (senza memoria / verimem / mem0) — dice solo **da dove partirebbe chi lo compone** |
| LANT-23 | `backup-all` fa il backup di **tutto**? | — | — | CLI | 🔴 **no: 3 tier su 9** | ws5 (riportata da ws7) | fuori **28.132 righe** fra entità e trascrizioni. 🔑 **Il docstring elenca corretto: è il NOME a essere invecchiato** ⇒ chi si fida del nome crede di avere una copia che non ha. **Governance: la promessa qui non è nel README, è nell'identificatore** |
| W8-1 | la **vetrina pubblica** (README = pagina PyPI) dichiara la distanza GIUSTA dal pacchetto? | — | EN | — | 🔴 **no: dice «994 commits», sono 1347** | ws8 | **regime**: `git rev-list` con **SHA fissato `1da01881d003`** (regola @ws4), 28/08 20:49; **secondo righello indipendente** `--since=2026-07-22` → **1344** ⇒ concordano ±3. `README.md:290`, **testo VISIBILE su PyPI**. ⇒ **+353 commit in due giorni, scarto 36%**. ✅ Il blocco `⛔ RILASCIO` è in un **commento HTML chiuso** (`:280-288`) ⇒ **non esce su PyPI**: il cancello ⑦ fa quello che promette. 🔑 **IL PARADOSSO**: quel blocco avverte che la nota *«diventa FALSA nel momento in cui si pubblica»* — **prevede un solo modo di sbagliare, e il TEMPO l'ha battuto sul tempo**: è invecchiata senza che nessuno pubblicasse. **Un presidio che nomina un modo di sbagliare rende invisibile l'altro.** 🔴 E **nessun test copre quel numero**, mentre `test_il_pacchetto_ha_cio_che_promettiamo.py` **calcola già la distanza in commit** per l'altro test ⇒ cura piccola, perimetro @ws7. ⚠️ **Limite**: il conteggio dipende dal tag `v0.7.0` **locale** — il controllo `--since` lo rende improbabile, non impossibile |
| W8-2 | il **pacchetto che si costruirebbe oggi** passa il veto del publish? | — | — | wheel | 🔴 **no: EXIT=1, 7 identificativi in 3 file** | ws8 | **regime**: `python -m build --wheel --outdir $(mktemp -d)` (⛔ `dist/` non toccata) + `scripts/controlla_registro.py` **sull'ARTEFATTO**, EXIT letto dal comando. **Tre perimetri CONCORDANO**: cartella `verimem/` 420 file · sdist 422 · **wheel 422** → sempre **7 in 3 file** (il 27/08 lo stesso confronto dava **418 contro 1**: la concordanza non era scontata). **I sette**: `anti_confab_gate.py:2403`[@ws3] · `doctor.py:396`[@ws1] · `supersession_policy.py:235`[@ws3] `:246`[@ws2] `:251` `:252` `:256`[@ws3]. 🔑 **QUATTRO su sette sono NOMI DI FILE di banco** (`ws3-la-batteria-italiana-…`) ⇒ non si curano riformulando: **finché i banchi si chiamano `wsN-<argomento>.py`, ogni citazione richiude il cancello** — **settimo giro**, il difetto è la **CONVENZIONE**, non le righe. ⚠️ E la **stessa causa** tiene spento il ramo «SDIST PULITO» di `publish.yml:258`, che il commento dichiara *«nessuno l'ha ancora visto accendersi»*: sdist 0.7.6 → **EXIT=1, stessi 7** ⇒ **una cura sola apre un VETO e accende un PRESIDIO**. **Limite**: wheel costruito **in locale**; quello del workflow nasce su ubuntu da albero pulito ⇒ il mio 7 è un **minimo** |
| W8-3 | un run di `ci` lanciato **a mano** aprirebbe il cancello del rilascio? | — | — | CI→publish | 🔴 **sì — ed è una GIUNTURA, non un difetto di uno dei due file** | ws8 | **regime**: lettura di `ci.yml:986` e `publish.yml:117-122` all'albero corrente + `gh run list --limit 60 --json event`. ⛔ **Non ho lanciato il dispatch nemmeno per provarlo**: sarebbe stato il modo più veloce di dimostrarlo e il più stupido di farlo scattare. `ci.yml:986` porta `&& (github.event_name == 'push' \|\| github.event_name == 'pull_request')` ⇒ **su `workflow_dispatch` `build` e `wheel-install` NON girano**; `publish.yml:118` filtra per **nome e ramo, MAI per evento** ⇒ un run lanciato a mano risulta `success` e **quel `success` il cancello lo accetta**, pur essendo un verdetto in cui il pacchetto non è mai stato costruito né installato. ✅ **Controllo**: su **60 run l'evento è `push` 60 volte, `workflow_dispatch` ZERO** ⇒ **non è mai successo**. ⚠️ **Ma `ci.yml:7` RACCOMANDA il dispatch** (*«un verdetto si deve poter chiedere, non solo provocare»*) **proprio per la coda satura** ⇒ **la prima che segue quel consiglio per sbloccarsi produce il verdetto incompleto**. ⚖️ Non pubblicherebbe da solo (il publish parte al tag, e il tag lo mette Aurelio): **verrebbe a mancare la protezione**, non uscirebbe un pacchetto a sorpresa. **Limite**: la conseguenza è **dedotta dai due file**, non osservata — osservarla richiede l'azione che sto dicendo di non fare |
| LANT-24 | la **CI** produce verdetti? | — | — | CI | 🔴🔴 **no da 22 ore e mezza — e chi aspetta troppo viene CANCELLATO** | ws8 (riportata da ws7) | ⚠️ **Numeri CORRETTI dall'autrice alle 19:22**: `--limit 20` tagliava la finestra e le aveva fatto scrivere «0 completed · 0 in_progress · 20 queued». Con `--limit 60`, solo workflow `ci`: **24 completed · 5 in_progress · 31 queued** ⇒ **qualcosa gira (5) e la coda è più grande (31)**. 🔑 **Ma il fatto principale regge**: gli ultimi quattro `ci` completati sono **tutti del 27/08 fra le 20:23 e le 20:25** ⇒ **nessun verdetto da 22h30**. 🔴 **E cade la sua cura precedente («aspettare funziona»)**: `ci.yml:165` dà a macOS un tetto di **35 minuti**, e il job del 16:38 ha girato **36** ⇒ **`cancelled`**. **Controllo**: nei tre run conclusi ieri sera **zero job cancellati su 27** ⇒ **non è sistematico, è cambiato OGGI** (macOS dichiarato 22,1 min, oggi 36: **+63%**). ⚖️ **Non è un difetto del prodotto**  📈 **AGGIORNATO 19:36 (ws8): la coda CRESCE mentre lavoriamo — 31 → 49 `queued` in DODICI minuti, ~1,5 run/minuto**, e il `ci` completato più recente resta quello di ieri alle 20:25 (**23 ore**). 🔑 **È un circolo, e va detto come tale: più lavoriamo, meno possiamo sapere se il lavoro regge.** ⇒ **Ogni commit di stasera aumenta la coda che dovrebbe verificarlo**  📌 **E il ritmo dei commit, FISSATO A UNO SHA** (`00d572f6`, su avviso di ws4 delle 19:59: *chi usa `git log` come fonte la fissi a uno SHA*): **87 commit dalle 18:35**, di cui **20 nei soli 17 minuti dopo la mia misura precedente** — che diceva 65 ed **era datata senza dirlo**. ⇒ **~1 commit al minuto contro 49 run in coda e zero verdetti da 23 ore** ⏱️ **AGGIORNATO 28/08 22:2x (autrice)**: **20 run su 20 in `queued`**, zero conclusi, il più vecchio fermo da **1h22m** (`19:03Z`). ⚖️ **Popolazione di controllo, e restringe il campo**: nello stesso ambiente `presidi-lenti.yml` conclude **9 su 9 `success`** e `security.yml` 9 su 9 (`cancelled` per la sua politica di concorrenza) ⇒ **non è l'infrastruttura**. 🔑 **Durata reale misurata, non dedotta dal nome**: `presidi-lenti` gira in **4,5–5,1 minuti**, e **uno è passato in 26,6** ⇒ **la soglia si stringe fra 26,6 e ~45 minuti**, contro il «fra 6 e 23» del 20/08. 🪞 **Quasi-errore dell'autrice, dichiarato**: stavo per scrivere «`presidi-lenti` gira, quindi la durata non c'entra» **fidandomi del NOME** — che dice «lenti» mentre il fatto dice 4,7 minuti. *Un nome non è una misura, come un docstring non è una specifica.* |
| LANT-25 | il nostro **dogfooding** conserva i referti che produce? | C1 | — | CLI | 🔴 **no: se li mangia** | ws6 (riportata da ws7) | allarme promosso a cella su direzione di `lead-audit` (28/08 19:02). ⚠️ **Da leggere insieme a W7-20**, che ha già ristretto la parte «silenziosa»: **le cancellazioni sono annunciate**, il problema è **il ritmo** con cui il nostro uso reale supera i propri fatti. 🔑 **È l'unica cella misurata su NOI come utenti**, e nessun banco l'avrebbe prodotta |
| LANT-26 | il claim «recall@5 0,8745 **fusion ON**» descrive uno stato **ottenibile**? | — | EN | benchmark | 🟡 **sì — è il DEFAULT — ma l'artefatto non lo prova** | ws7 (compito assegnato da lead-audit) | **Regime**: lettura del sorgente, `792888d5`, nessuna esecuzione. **«Fusion» non è un'opzione**: è l'env **`ENGRAM_PPR_FUSION`** (`semantic.py:2534`), e il **default è `on`** ⇒ **il comando registrato riproduce già lo stato del claim**, il runner chiama `recall()` senza parametri. 🔴 **Il difetto resta e si sposta sull'ARTEFATTO**: il json conserva `dataset`, `k`, `n_questions`, `embedding_model` **e nessuna env** ⇒ **chi avesse `ENGRAM_PPR_FUSION=0` otterrebbe un altro numero senza accorgersene**. 🔑 **Stessa classe che ws1 ha pagato oggi alle 19:31** (`HIPPO_ENCODE_DELEGATE_ONLY` ereditata): **l'env è regime, e un artefatto che non la registra non è riproducibile** — due strade indipendenti, stesso difetto |
| LANT-11 | una **quantificazione universale** passa il gate? | — | IT | CLI | 🔴 **no, e non serve che sia aritmetica** | ws8 (riportata da ws7) | «*tutti e quattro*» → **3 fatti su 4 quarantinati**; riscritti **caso per caso**, **4 su 4 ammessi**. 📌 Regola già in `O3` e non applicata: **spezzare vale anche per i quantificatori, non solo per le somme** |
| LANT-12 | il modo di scrivere di chi salva cambia l'esito? | — | EN | CLI | 🔴 **sì, e l'A/B è involontario** | ws1 (riportata da ws7) | i due lotti della serata sono un A/B sul proprio modo di scrivere: **9 fatti con claim che nominavano entità assenti dalla fonte → 2 quarantinati**; i **6** scritti con la fonte che le nomina → nessuno. 🔑 **Il gate insegna a chi lo usa**, ed è la stessa proprietà che rende pericolosa la riga 31 ⚠️ **REGIME AGGIUNTO DALL'AUTRICE DEI NUMERI (ws1, 28/08 21:08) — auto-audit dopo l'errore dell'env delle 19:33**: questa misura è del **27/08 sera**, su **HEAD** e sul **corpus di casa**, con l'ambiente della nostra macchina — **`HIPPO_ENCODE_DELEGATE_ONLY=1` INCLUSA**, che oggi ho misurato **cambiare quali layer parlano** (`L1.20` parla solo da noi). 🛑 **Il regime NON fu registrato al momento della misura: lo dichiaro come lacuna, non lo ricostruisco a memoria.** ⇒ **Il numero vale per NOI; il suo trasporto a un utente non è verificato.** |
| LANT-13 | sullo **scambio di attribuzione** parla qualche layer lessicale? | C5 | — | SDK | 🔴 **no: `L4.1` tace 0 volte su 12 — decide il giudice da solo** | ws3 (riportata da ws7) | regime: 12 scambi, porta SDK. ⚠️ **L'autrice dichiara tre difetti trovati nel PROPRIO misuratore** durante la misura. 🔑 Compone con W7-3 e W7-7: **su questa classe non c'è rete lessicale, il verdetto sta tutto sul punteggio**  🔒 **BLOCCATA-DA-F1** — non si cura da sola: è una delle facce dello **strato soggetto-valore** (marcatura di ws7 su direzione di lead-audit, 28/08 19:02) |
| LANT-14 | il **contorno** del claim sposta il verdetto su uno scambio? | C5 | — | SDK | 🔴 **sì, in entrambe le direzioni** | ws4 (riportata da ws7) | uno scambio fermato a **4,9** entra a **99,4** con della **prosa neutra** attorno; un altro fermato a **0,9** entra a **99,8** col **contorno numerico**. 🔑 **Unisce due fronti che sembravano distinti**: non conta solo *dove* sta la cifra, conta *cosa le sta intorno*  🔒 **BLOCCATA-DA-F1** — non si cura da sola: è una delle facce dello **strato soggetto-valore** (marcatura di ws7 su direzione di lead-audit, 28/08 19:02) |
| LANT-15 | i **nomi** dei campi dicono ciò che i campi fanno? | — | — | SDK+CLI | 🔴 **no, in tre casi** | ws5 (riportata da ws7) | `confidence` è **anti-correlata** · `last_seen` significa «**letto**», non «visto vivo» · `backup-all` copre **3 tier su 9** (riga W7-10). 🔑 **Nessun docstring mente: mentono i nomi** ⇒ chi legge il codice è informato, chi legge l'identificatore no |
| LANT-16 | il prefisso `file:` verifica che il file **esista**? | — | EN | SDK | 🔴 **no** | ws8 (riportata da ws7) | `file:` **cade anche con un percorso REALE** ⇒ non è una verifica di esistenza: **è che `file:` non è nella lista dei prefissi accettati** da `documentation`. ⚠️ **L'autrice ha RITIRATO la conferma che aveva dato a ws2** su questa base: la tesi di ws2 regge, cade il supposto meccanismo |
| 47 | lo stesso fatto, sulla stessa fonte, ha lo stesso verdetto se cambio **l'ordine delle parole**? | C7, C4 | IT | CLI | 🔴 **no: verdetto opposto** | ws6 | A/B a **fonte identica** e contenuto identico, cambia solo la sintassi: *«Su 12 celle in cui la fonte nega il claim in italiano, 2 sono state ammesse»* → **`quarantined`** (`cd9bc69f20cb`) · *«In italiano le negazioni ammesse per errore sono 2 su 12 celle»* → **`model_claim`, grounding 99,93** (`aa7a04fd2be4`). ⇒ **La seconda non è più vera della prima: è più simile in superficie alla riga della fonte.** 🔑 È **l'altro lato della riga 12**: là una fonte che NEGA passa perché condivide le parole del claim, qui un claim VERO cade perché le dispone in un altro ordine — **una misura di sovrapposizione non distingue *dire la stessa cosa* da *usare le stesse parole*, e sbaglia in entrambe le direzioni**. ⚠️ **Non è la W7-12**: là (ws1) cambia **cosa** il claim nomina — entità assenti o presenti nella fonte; qui contenuto, entità e fonte sono **identici** e cambia solo la disposizione. **Le due si completano: una isola il contenuto, l'altra la sintassi.** Si salda con la riga 31 (ws1, «premia il ricalco») e con la 32 (ws7, che ne ha ridotto l'effetto a 1,2 punti in prosa): **qui l'effetto è un ribaltamento di verdetto, non un delta di punteggio**. **REGIME**: porta CLI (`verimem save --source`), store **principale** in scrittura reale (sono due nostri fatti di stasera, non un banco), build `19d7e6ea`, un processo. ⚠️ **APERTO e dichiarato**: **n=2**, incontrati salvando i risultati, **non un banco** — non ho un tasso, ho un caso pulito. Chi lo ripete su una batteria chiude la riga |
| 48 | la soglia con cui il prodotto giudica è quella che ha calibrato? | — | — | tutte | 🟡 **no, e lo dichiara da sé a ogni avvio** | ws6 | `anti_confab_gate.py:2376` stampa a **ogni caricamento del giudice**, verbatim: «*local grounding judge **ships an unusable cut** (99.6 > 90, a val-set F1 artifact) — using the validated local CE moat cut **40***». ⇒ **Il taglio in uso è 40**, non quello spedito. 🔑 Perché conta per le righe 12 e 36: i cinque errori di C7 valgono **95,84 · 99,36 · 99,91 · 99,80 · 99,91**, cioè **più del doppio della soglia** — **non la sfiorano, la superano larghi**. ⇒ Nessuna taratura della soglia può curare quella classe, e **chiunque pubblichi un numero sul grounding deve dire contro quale taglio l'ha misurato**. ⚖️ Verdetto 🟡 e non 🔴 **perché il prodotto lo dichiara invece di nasconderlo**, e il taglio che usa è quello descritto come *validated*. **REGIME**: osservato su ogni esecuzione dei miei banchi di stasera (SDK e CLI), build `ec969569` e `19d7e6ea`. ⚠️ **APERTO**: **non ho verificato** se il taglio 40 sia quello giusto né come sia stato validato — ho misurato che *quello spedito non è in uso* e che *il prodotto lo dice*. Il fronte del gate è di @ws1/@ws3 e non l'ho toccato |
| 49 | sullo **scambio di attribuzione**, CHI decide: uno strato deterministico o il giudice? | C7 | IT | SDK | 🔴 **il giudice, da SOLO: `L4.1` non parla MAI, 0 su 12** | ws3 | **regime**: i **12 casi esatti di ws4** (`lo-scambio-e-simmetrico-o-no.py`) copiati alla lettera · `PYTHONUTF8=1`, `utf8mode=1` misurato · python 3.13.12 · store temporaneo vuoto (`Memory(path=…)`) · **un solo processo** · `validate="full"` · build `ec969569`. **AMMESSI 7/12 con zero strati · FERMATI 5/12, tutti e cinque solo `L4-grounding`** — che **non è deterministico**: è l'etichetta del **giudice** (`anti_confab_gate.py:2630`, «*source does not entail the proposition, grounding N below threshold*» — letto nel sorgente, non dedotto dal nome). ⇒ **la separazione 7/5 la produce interamente il modello: nessuno strato deterministico contribuisce** ⇒ **la cura non è «aggiustare `L4.1`»** — non partecipa — ma **costruire uno strato soggetto-valore che oggi non esiste** ⇒ e se decide il solo modello, **una regolarità nella FORMA del claim può non esistere**: le 4 ipotesi cadute di ws4 cercavano forse una cosa che non è lì. ✅ **Controllo positivo che rende leggibile lo zero** (stesse fonti, cifra del tutto assente): `391000 euro` 0.4 **L4.1**+L4-grounding · `73 mg` 0.7 **L4.1**+L4-grounding · `7%` 92.1 L4.2 **ed ENTRA** ⇒ **3 su 3 parlano, lo strumento vede**. ✅ **I 12 esiti di ws4 riprodotti UNO PER UNO**, punteggi compresi, in processo indipendente ⇒ **il suo 3-su-7 non è un artefatto di esecuzione**. ⚠️ **Limiti**: due fonti sole, corte (≈450 e ≈230 char), **solo italiano** — le sue, per rendere i banchi confrontabili: la scelta compra il confronto e costa la generalità · n=12 · una esecuzione per caso · il `7%` che prende **L4.2** e non L4.1 **non so spiegarlo**, è un caso solo. 📌 **Candidato dichiarato NON provato** (n=2 per cella): per **unità di misura**, percentuali 2/2 ENTRA · date 2/2 · dosaggi 3/6 · **importi in euro 0/2**. Se reggesse toccherebbe **la penale e il termine**. **NON è l'ipotesi «specie» di ws4**: la sua chiedeva se lo scambio avviene *dentro* una specie, questa **quale specie è fragile**. Commit `c568783c`  🔒 **BLOCCATA-DA-F1** — non si cura da sola: è una delle facce dello **strato soggetto-valore** (marcatura di ws7 su direzione di lead-audit, 28/08 19:02) |
| 50 | la ricevuta consegnata al chiamante dice **quale difesa ha agito**? | — | — | SDK | 🔴 **no: la chiave `layers` NON esiste nella ricevuta** | ws3 | **regime**: come la 47. Le chiavi vere di `add()` sono `adjudication · advice · grounding_score · id · moat · quarantined_by · status · stored · warnings`; gli strati stanno **dentro `warnings`**, sotto `layer`. ⇒ **chi legge `receipt["layers"]` ottiene `[]` per QUALUNQUE scrittura e crede di aver misurato** — è la quinta forma di «*una misura che non c'è si legge come una misura perfetta*». **Tre superfici lo dicono, la quarta no**: log ✅ (`client.py:725`, riporta chi ha AGITO) · registro di fiducia ✅ · righe di quarantena ✅ · **ricevuta SDK ❌**. 🪞 **L'autrice ci è cascata nella prima stesura del banco 47** (il log diceva `['L4-grounding','L4.1']`, il banco stampava vuoto) e il **controllo positivo** l'ha fermata **prima** del verdetto. ✅ **Verificate le righe che potevano dipenderne**: la **30** (omissione, «sempre `layers: -`») **REGGE** — quel banco scrapa i nomi degli strati con una regex su **tutto l'output**, riga di log compresa (`ws3-il-documento-lungo…py:195`), cioè la superficie buona; e il «zero layer» di **ws4 REGGE** — legge `warnings` (`lo-scambio-di-attribuzione-elude-la-regex.py:85`). 🔑 **Non è un difetto di giudizio, è di OSSERVABILITÀ** — famiglia del reperto di ws7 sulla prova troncata a 400. Commit `c568783c` |
| W2-1 | la ricevuta spiega **perché** un fatto è stato ritirato? | C1 | EN | SDK | 🔴 **no: nomina il fatto, sbaglia il motivo** | ws2 | **regime**: processo singolo, store temporaneo vuoto, tre record EN distinti da un nome di persona, **fonti diverse** (`File A/B/C`), porta SDK. ✅ Il **cosa** c'è ed è ricco: `warnings` con `L3-supersession`, più i campi **`superseded`** e **`superseded_undo_ops`** che portano l'**id del ritirato** e l'undo. 🔴 Il **perché** è falso: `reason` = «a newer **same-source** value» e `advice` = «updates an earlier value **from the same source**» — mentre le tre fonti sono diverse. È la **stessa stringa** già misurata nel log (`flow.supersession branch='same-source evolution'`): due superfici indipendenti, stessa bugia. E l'`advice` è azionabile **al contrario** — rassicura («stai aggiornando un valore precedente») mentre ha cancellato il record di un'altra persona. 🔴 Dopo: `superseded_reason` = **None**, `recall` **1 su 3**, ritirato **non** nel recall di default. ✅ **CORRETTO — «solo per id» era falso**: su rilievo di ws6 ho verificato `as_of` **sulla porta SDK** e il ritirato **torna** — `recall(as_of=<istante prima della seconda scrittura>)` restituisce «70 kg» mentre il recall di adesso dà «78 kg» (⛔ controllo: senza `as_of` il ritirato non compare). ⇒ È raggiungibile **anche per tempo**, senza conoscere l'id: **cade «irrecuperabile in pratica»**. Resta che chi **non sa** che quel fatto è esistito non ha ragione di cercarlo a un istante passato. ⚠️ Limiti: un solo caso (supersessione), una sola porta, n=1 — regge di più il fatto che la bugia **coincida** con quella del log, misurata ieri e in un'altra superficie |
| W2-2 | la stessa scrittura ha lo **stesso esito** su tutte le porte? | C1 | EN | SDK · MCP · CLI | 🔴 **no: su SDK un record viene cancellato, su MCP i due coesistono** | ws2 | **regime**: un processo, store temporaneo vuoto, due record EN distinti da un nome di persona, fonti **diverse** (`File A/B`), stesso topic. **MCP** → 2 serviti su 2, `superseded_by=None` su entrambi, `replaced=False`, nessun avviso · **SDK** → **1 su 2**, `L3-supersession` + `superseded`/`superseded_undo_ops` · **CLI** → annuncia come SDK. ⛔ Controllo: la cella SDK **riproduce W2-1**, quindi il banco è confrontabile. ⇒ **Il difetto delle celle 45/46 è della porta SDK, non del prodotto** — e resta grave perché l'SDK è la porta che un'applicazione usa: la stessa app che scrive tre pazienti ne conserva uno, lo stesso codice via MCP li conserva tutti. 🪞 Stavo per scrivere «MCP tace»: falso, verificato prima di pubblicare — non tace, non succede niente da annunciare, e `replaced=False` era **un'informazione corretta**. 🔗 La cella 37 (nove chiamanti, 4 argomenti su 19 comuni) lo prediceva: questa è la prima istanza misurata sul **comportamento**, non sulla ricevuta. ⚠️ Limiti: due record, una lingua, n=1. ✅ **RIVERIFICATA 28/08 22:10 dopo un sospetto MIO che il banco fosse viziato**: ieri il ramo SDK usava un tempdir esplicito e il ramo MCP lo store di default ⇒ potevano essere **store diversi**, e MCP non avrebbe superseduato solo perché non vedeva il primo fatto. Rifatto con **entrambe le porte sullo stesso store**, e con il controllo che mancava — *«il primo fatto è visibile alla seconda porta?»*: `SDK→SDK` visibile **True**, ritirati **1** · `SDK→MCP` visibile **True**, ritirati **0** · `MCP→MCP` visibile **True**, ritirati **0**. ⇒ **Lo store non è la spiegazione e la disparità è reale**; il caso `SDK→MCP` è il più netto: fatto scritto da SDK, **visibile**, e MCP non lo ritira. 🔎 **Caso minimo, per chi cura**: NON è `meta_narrative` (aggiunto a `Memory.add` la supersessione resta) · NON è il percorso di persistenza — `mcp_server.py:13229` dichiara «*Mirrors Memory.add() (SDK)*» e ha lo stesso admit-guard di `client.py:778` ⇒ **la differenza è a monte: il gate chiamato dalla porta MCP non produce `supersede_fact_ids`**. Quale argomento lo spenga resta da isolare |
| W2-3 | il conflitto che il prodotto **rileva** arriva a chi scrive? | C8 | EN | MCP · SDK | 🔴 **no — e il rilevatore stesso sbaglia** | ws2 | **regime**: un processo, store temporaneo vuoto, due fatti in conflitto numerico sullo stesso soggetto, porta MCP (su SDK il caso **non è osservabile**, vedi limite sotto). ① Il prodotto emette `coherence_warning kind=numeric_clash` **nel log** a ogni coppia in conflitto, ma nella ricevuta: `anti_confab_warnings=[]` e **nessun campo** `coher*`/`contrad*`/`clash*` ⇒ sa che due fatti **serviti** si contraddicono e non lo dice a nessuna porta. ② 🔴 E il rilevatore **non guarda né il soggetto né la grandezza**: «Patient **Clark** is on **ward 3**» contro «Patient **Jones** weighs **91 kg**» → `numbers=[3.0] vs [91.0] sim=0.83 numeric_clash` — il numero di un reparto contro il peso di un'altra persona. 🔗 Stessa famiglia di L4.2 (celle 45/46): criteri numerici che non sanno di cosa parla il numero. ⇒ **«Una cosa accesa che non fa niente»**: il falso positivo non fa danno **solo perché** il warning non raggiunge nessuno — ⚠️ **collegarlo così com'è peggiorerebbe il prodotto**, la cura è prima misurarne la precisione. ⛔ **Limite del banco, ed è una regola generale**: su SDK questo caso **non è misurabile**, perché due record distinti producono supersessione lo stesso (cella 45) e la supersessione avviene prima del clash ⇒ **una porta con un difetto noto non può fare da banco per un altro difetto: il primo maschera il secondo**. ⚠️ n=1 per cella |
| W2-4 | la QUARANTENA è spiegata allo stesso modo su tutte le porte? | C4 | EN | SDK · MCP · CLI | 🟢 **sì** | ws2 | **regime**: un processo, store temporaneo vuoto, claim EN con un valore **assente** dalla fonte («…and has **9 loading bays**»), porta per porta. Tutte e tre: `quarantined` · layer **L4.1** · **stessa `reason` parola per parola**. ⛔ Controllo: lo stesso claim col valore **presente** passa su tutte e tre — senza, una porta che quarantina tutto sembrerebbe «coerente». ⇒ **La disparità fra porte NON è generale**: è localizzata alla supersessione (W2-2) e ai nomi dei campi (riga 7). ⚠️ n=1, un solo layer di quarantena ✍️ **SECONDA FIRMA — ws6, 28/08 21:07.** Non ho ripetuto il banco di ws2: ho verificato **la stessa proprietà dal verso opposto**, che è più forte di una ripetizione. Il suo banco prova che le tre porte concordano **su un RIFIUTO** (valore assente → `quarantined`, `L4.1`, stessa `reason` parola per parola); il mio (`c015fd3a`, C7 negazione con riempitivo 200) prova che concordano **su un'AMMISSIONE**: **SDK 5/6 · CLI 5/6 · MCP 5/6**, e **coincide anche CHI sbaglia** — `OMEGA` è l'unico giudicato correttamente su tutte e tre. ⇒ **Le porte concordano in entrambi i versi**, e due conteggi uguali qui non nascondono popolazioni diverse perché coincide il caso. ⚠️ **Cosa la mia firma NON copre**: lei verifica che la `reason` sia **identica parola per parola**, io ho confrontato **status e punteggio**, non il testo della spiegazione ⇒ **quel pezzo resta su una firma sola.** |
| W2-5 | la ricevuta parla la lingua di chi scrive? | C4 | EN | SDK | 🔴 **no: L4 risponde in italiano** | ws2 | **regime**: un processo, store temporaneo vuoto, quattro claim **tutti in inglese** che fanno scattare layer diversi. `L4.1` → **IT** («il claim afferma un valore che la fonte non contiene…») · `L1.15` → EN · `L1.9` → EN · `L1.20` → EN. ⛔ Il controllo è **dentro il dato**: tre layer su quattro rispondono in inglese ⇒ non è che il prodotto sappia una lingua sola, è **L4.x** a rispondere sempre in italiano. Coerente con tutte le `reason` di L4.2 raccolte il 27/08. ⚠️ **Limite, e conta**: volevo confermarlo anche **staticamente** contando le stringhe nei detector e **due righelli di fila si sono rotti** — il primo dava `0` ovunque (pretendeva `reason =` sulla stessa riga), il secondo dava numeri **plausibili** (IT=20/EN=110) ma le presunte italiane erano `")[:_LEXICAL_SCAN_CAP]` e docstring inglesi. **Il conteggio statico non esiste e non è stato consegnato**: chi lo vuole usi `ast`, non `grep`. 4 layer, n=1 ciascuno |
| W2-6 | quando il moat **non gira**, il chiamante lo sa? | C4 | EN | SDK · MCP · CLI | 🟢 **sì, su tutte e tre** | ws2 | **regime**: un processo, store temporaneo vuoto, claim EN **senza fonte** (il moat non ha nulla da controllare). `SDK` → `grounding=None`, `moat='not_run:no_source'` · `MCP` → «not run — no source, so the entailment moat had nothing to check» · `CLI` → «not verified — no source, so the entailment moat did not run; pass --source». ⛔ Controllo: **con** la fonte tutte e tre mostrano che è girato (`moat='passed'` / «judged 99.0» / «grounded 99.0», e `grounding_score=99.02` identico su SDK e MCP) — senza, non distinguerei «non gira» da «non lo dice mai». 📌 I **registri** differiscono e ha senso: l'SDK dà token macchina (`not_run:no_source`, `passed`), MCP e CLI danno prosa esplicativa — la prima è per un programma, le altre per un agente. **Lo annoto come design, non come difetto.** ⚠️ n=1; e su SDK il punteggio non sta nel campo `moat` ma solo in `grounding_score` |
| W2-7 | la ricevuta distingue un **avviso** da un **veto**? | C8 | EN | SDK | 🔴 **no** | ws2 | **regime**: un processo, store temporaneo vuoto, **un claim per volta** (un banco a più scritture nello stesso topic non isola il claim — misurato). Un veto (`L4.1`, → `quarantined`) e un avviso (`L1.16`, → `model_claim`) hanno la **stessa identica struttura**: `advice`, `layer`, `matched_text`, `reason`. **Nessun campo di gravità/blocco** in nessuno dei due. ⇒ L'unico segnale è `status`, che però sta a livello di **ricevuta**, non di avviso: con più avvisi il chiamante non può sapere quale abbia bloccato. ⛔ Controllo: un claim pulito non produce nessuno dei due. ⚠️ n=1 per cella, porta SDK |
| W2-8 | `quarantined_by` nomina il layer che ha **davvero** vetato? | C8 | EN | SDK | 🔴 **no: dà una famiglia, e quella sbagliata** | ws2 | **regime**: come sopra. Con **un solo** layer è corretto: `layers=['L4.1']` → `quarantined_by='L4.1'` ⛔ (è il controllo, e passa). Con **quattro**: `['L1.16','L4.1','L4-relazione','L1-domain-precision-observe']` → `quarantined_by='**L1**'` — che **non è nessuno dei quattro**: è un prefisso di famiglia. E la famiglia **sbagliata**, perché `L1.16` da solo **non veta** (dà `model_claim`) mentre `L4.1` sì. ⇒ **Il campo funziona quando è banale e sbaglia quando serve.** 🤝 Conferma per un'altra via il rilievo di ws4 («`quarantined_by` sbaglia CHI: primo layer invece del decisore») e lo precisa: non solo sbaglia, **restituisce un prefisso invece di un layer**. ⚠️ n=1 |
| W2-9 | l'`advice` di una quarantena è **eseguibile**? | C4 | EN | SDK | 🟢 **sì su L4.1** | ws2 | **regime**: un processo, store temporaneo vuoto, un claim per volta. Non «l'advice è chiaro?» ma **seguendolo alla lettera il claim passa?**. `L4.1` respinge «…and has **9 loading bays**» e consiglia «correggi il valore, **oppure** passa la fonte che sostiene questo valore». Eseguite **entrambe** le strade: ② fonte che contiene le 9 bays → `model_claim`, `layers=[]` · ③ claim corretto togliendo il valore → `model_claim`, `layers=[]`. ⛔ Controllo: un claim già valido passa senza bisogno di advice. ⚠️ **Ma non è uniforme fra layer**: su `L1.9` un'altra istanza ha misurato un advice che suggerisce per primo un prefisso che **non può mai** passare ⇒ la qualità dell'advice **varia per layer**, e questo verde vale per L4.1. 📌 E la `reason` è in **italiano** su un claim inglese (vedi W2-5). ⚠️ n=1 |
| W2-10 | `matched_text` cita **davvero** il testo che ha fatto scattare il layer? | C8 | EN | SDK | 🟡 **sì sui lessicali, assente sul semantico** | ws2 | **regime**: un processo, store temporaneo vuoto, un claim per volta, quattro layer diversi. ⛔ Controllo scelto perché **falsificabile**: il testo citato dev'essere una **sottostringa** del claim — se non lo è, il campo non cita, parafrasa. `L4.1` → `'9 loading'` ✅ · `L1.16` → `'approved'` ✅ · `L1.9` → `'Latency is 240 ms'` ✅ · `L1.20` → **`None`**. ⇒ Sui tre layer **lessicali** il campo fa esattamente ciò che promette, ed è il pezzo su cui un agente si baserebbe per sapere **cosa** correggere. 📌 Il `None` di `L1.20` **non è un difetto**: è il layer *semantico* («semantic self-claim»), che per costruzione non ha un testo matchato. ⚠️ **Ma il chiamante non sa in anticipo quale layer sia lessicale e quale semantico**: lo scopre ricevendo `None`, e un agente che si aspetta sempre una citazione va gestito. `'9 loading'` non è troncato: è esattamente il match del pattern (numero + parola adiacente), coerente con le celle 45/46. ⚠️ n=1 per layer |
| W2-11 | chi **legge** distingue un fatto giudicato da uno **mai giudicato**? | C4 | EN | SDK | 🟡 **sì, ma non dal campo che sembra dirlo** | ws2 | **regime**: un processo, store temporaneo vuoto, due fatti — uno **con** fonte (moat girato) e uno **senza** (mai giudicato). ✅ La distinzione **c'è ed è leggibile**: `grounding_score` = `99.02` contro **`None`**, e `source_signature` presente contro assente. ✅ E il **`recall`** — la superficie che un'app usa davvero — **restituisce `grounding_score` nei risultati**, quindi la distinzione arriva a chi legge. ⛔ Controllo: i due differiscono in **due** campi, non zero. 🔴 **Prima riserva**: `status` vale `model_claim` per **entrambi** ⇒ chi guarda il campo dal nome più ovvio **non distingue** un fatto verificato da uno mai controllato. 🔴 **Seconda**: nel recall il primo risultato era quello **mai giudicato** — il ranking segue la similarità, non la verifica, quindi **un agente che prende il primo risultato può prendere il non verificato**. ⚠️ n=1; due fatti, una query |
| W2-12 | chi **rilegge** un fatto quarantinato sa **perché** lo è? | C4 | EN | SDK | 🔴 **no: il motivo esiste nella ricevuta e vale `None` nel fatto** | ws2 | **regime**: un processo, store temporaneo vuoto, un claim per volta. ✅ Il quarantinato **è raggiungibile per id** e `status='quarantined'` lo dichiara · ✅ il `recall` lo **esclude** (1 risultato su 2 scritture), che è esattamente la promessa «kept out of default recall» ⛔ e il controllo — il fatto ammesso — è raggiungibile **e** compare nel recall, quindi «non lo trovo» significa davvero «è quarantinato». 🔴 **Ma `quarantined_by` vale `None` nel fatto**, mentre nella **ricevuta** dello stesso claim vale `'L4.1'` (W2-8): **il motivo vive tre secondi e non viene persistito**. 🔴 **E il fatto porta `grounding_score = 98.20`** — alto: chi rilegge vede un fatto **ben sostenuto dal giudice e respinto lo stesso**, senza nulla che spieghi la contraddizione apparente (la respinge un layer deterministico, non il giudice). 🔴 **RIDIMENSIONATO SUL CORPUS REALE, e in mio sfavore**: «il motivo non è persistito» è vero **nel mio banco** e **falso nel corpus**. Su agosto — l'unica era in cui il campo esiste — `quarantined_by` è popolato su **473 quarantinati su 679 (69,7%)**; nelle ere precedenti è **0 su 1703**, quindi il campo è stato **attivato ad agosto**. E la ripartizione **rovescia** l'ipotesi che avevo scritto: fra i **discordanti** manca solo nel **16,5%** (37 su 224), fra i **concordi** nel **37,1%** (169 su 455) ⇒ **il prodotto registra il motivo PIÙ spesso proprio nei casi difficili**, non meno. ⛔ Il controllo che l'ha catturato: le due quote sono molto diverse (16,5 contro 37,1), quindi la relazione c'è — solo **inversa** a come l'avevo prevista. 📌 Resta aperto **perché il 37,1% dei concordi taccia**: sono i casi in cui a vetare è il giudice da solo, e l'ipotesi da provare è che `quarantined_by` registri i layer e non il giudice. 🔗 Confronto che regge: i **ritiri** conservano il motivo nel **100,0%** (2151 su 2152), le quarantene nel **19,9%** sull'intero corpus. ⚠️ n=1 nel banco, corpus intero nella misura |
| W2-13 | il campo `adjudication` è **coerente al suo interno**? | C8 | EN | SDK | 🔴 **no: mescola due decisori** | ws2 | **regime**: un processo, store temporaneo vuoto, un claim per volta, claim respinto da `L4.1`. ✅ Il campo è **ricco e nessuno l'aveva aperto**: `disposition` · `judge` (backend, modello: `local_gate_ce_v2`) · `score` · `threshold` · `margin` · `reason` · `evidence_class` · `confidence_tier`. ⛔ Controllo: su quattro casi diversi (ammesso, quarantinato, con avviso, senza fonte) dà **3 valori distinti su 4** ⇒ porta informazione, non è una costante. 🔴 **Ma è incoerente**: `disposition='quarantined'` con `score=98.17` e `threshold=40.0` — **il punteggio supera la soglia di 58 punti e il fatto è respinto lo stesso**. La `reason` è quella di **L4.1** (deterministico), mentre `score`, `threshold`, `margin` e `judge` sono del **cross-encoder**, che *non* ha vetato. ⇒ **Chi legge il campo conclude che il gate è rotto**, mentre il gate sta funzionando: due decisori diversi in una struttura che ne descrive uno. 🔗 È la spiegazione del `grounding 98.20` su un fatto quarantinato (W2-12). 🔴 E `adjudication` **non sopravvive nel fatto**: conferma W2-12 — il motivo c'è, nella ricevuta, e sparisce. ⚠️ n=1 |
| W2-14 | **quando** `adjudication` diventa incoerente? | C8 | EN | SDK | 🟡 **solo quando i decisori discordano — 2 casi su 3 coerenti** | ws2 | **regime**: un processo, store temporaneo vuoto, un claim per volta, stessa fonte per tutti e tre. Criterio di coerenza fissato prima: `score ≥ threshold` ⇔ `disposition='admitted'`. **Fermato dal GIUDICE** (claim falso): `quarantined`, `score=0.53`, `thr=40` ✅ coerente · **fermato da `L4.1`**: `quarantined`, `score=98.17`, `thr=40` 🔴 **incoerente** · **ammesso** (⛔ controllo): `admitted`, `score=99.02` ✅ coerente. ⇒ **Il campo è corretto in 2 casi su 3**, e l'incoerenza compare **solo quando il giudice e il layer deterministico discordano**: allora mostra i **numeri del giudice** con la **disposizione del layer**. 📌 Precisazione rispetto a W2-13: non è «un decisore contro due» — nel caso verde parlano **due** layer (`L4.1` + `L4-grounding`) e sono **concordi** (0.53). È la **discordanza** a rompere il campo. 🔑 E la discordanza è esattamente il caso in cui chi legge ha **più** bisogno di capire. ⚠️ n=1 per cella |
| W2-15 | quanti quarantinati **reali** sono in discordanza? | C8 | — | corpus | 🔴 **224 su 2378 (9,4%), e 127 con grounding ≥ 99** | ws2 | **regime**: corpus reale `~/.engram/semantic/semantic.db` in **sola lettura**, sqlite puro, 14.975 fatti · soglia `40.0` presa da `adjudication.threshold` misurato oggi (W2-13/W2-14). Dei **2378** quarantinati: **1691 (71,1%) mai giudicati** (`grounding_score` NULL) · **463 (19,5%) concordi** (giudicati, sotto soglia) · **224 (9,4%) DISCORDANTI** — giudicati **sopra** soglia e respinti lo stesso. ⛔ Controllo: le tre classi sono **tutte popolate** e la somma fa esattamente 2378 ⇒ il filtro discrimina, non sta etichettando tutto allo stesso modo. 🔑 Fra i discordanti: **≥80 → 140 · ≥90 → 140 · ≥95 → 137 · ≥99 → 127** — **nessun fatto fra 80 e 90**, la distribuzione è **bimodale**: quando il giudice e una regola discordano, il giudice non è incerto, è **quasi certo**. ⇒ Sono i 224 fatti su cui la ricevuta mente (W2-13/W2-14) e su cui il motivo non è persistito (W2-12). 🔴 **CORRETTO SUBITO DOPO — il 9,4% è una media che DILUISCE**: rifatta la ripartizione **per era**, i discordanti sono **tutti di agosto** (221 su 224) e lì la quota è **32,7%** — `2026-05: 1579 quarantinati → 0 discordanti` · `06: 47 → 0` · `07: 77 → 3 (3,9%)` · `08: 675 → 221 (32,7%)`. I 1579 di maggio sono **di prima del giudice** (mai giudicati) e abbassano la media. ⇒ **Il numero da usare è: nell'era attuale un quarantinato su tre è respinto contro il parere quasi certo del giudice.** Il «9,4%» sull'intero corpus è vero e fuorviante. ⚠️ Il limite dichiarato (soglia `40.0` misurata oggi) resta e **è servito**: è proprio guardando le ere che il numero è cambiato di segno |
| W2-16 | `quarantined_by` parla **un vocabolario solo**? | C8 | — | corpus | 🔴 **no: quattro livelli di specificità in sette valori** | ws2 | **regime**: corpus reale in **sola lettura**, sqlite puro, i **473** quarantinati che hanno il campo popolato (agosto, unica era in cui esiste). Valori: `moat` **308** · `L4.1` 68 · `gate` 55 · `L4-review` 29 · `L3-coexistence` 10 · `L1` **2** · `store-screen` 1. ⇒ Il campo mescola un **meccanismo** (`moat`, `gate`), un **layer** (`L4.1`, `L3-coexistence`), un **prefisso di famiglia** (`L1`) e una **superficie** (`store-screen`): **chi legge non sa a quale livello sta guardando**. 🪞 **Due mie ipotesi cadute qui**: (a) «il campo registra i layer e non il giudice» — **falso**, `moat` è il valore **più frequente** (65%); (b) e **ridimensiona W2-8**: il prefisso `L1` al posto di un layer esiste ma è **2 casi su 473 (0,4%)**, non la regola — nel mio banco l'avevo incontrato al primo colpo e ne avevo tratto il caso generale. ⇒ **Il difetto non è che sbagli il nome: è che non esiste un vocabolario.** ⚠️ Limite: solo agosto (altrove il campo è vuoto), e non ho letto nel codice chi scrive ciascun valore |
| W2-17 | la cura `f5dedf34` (sostantivi italiani nel pattern percentuale) vale su **tutte** le porte? | C4 | IT | SDK · MCP · CLI | 🟡 **sì su SDK e MCP · ⚪ non misurabile su CLI** | ws2 | **regime**: un processo, store condiviso di default, claim IT «La copertura e' 42.6%», un claim per volta. `SDK` **senza** attestazione → `quarantined ['L1.19']`, **con** → `model_claim []` · `MCP` **identico** · `CLI` → `admitted` in **entrambi** i casi. ⇒ **La cura è attiva su SDK e MCP**; su CLI la cella non è leggibile per il difetto già registrato (riga 43: L1 non viene chiamato), non per la cura. 🔑 **Pezzo nuovo e utile**: **su MCP l'attestazione È onorata** — conferma la cella W2-35 *da un'altra porta*, perché qui ho passato i **due ref congiunti** che quella cella ha scoperto servire (`bench:` + `file:` esistente). 🪞 E una svista mia, corretta leggendo `--help` invece di dedurre: `--verified-by` è **«repeatable»**, va **ripetuto** — il mio primo tentativo passava due valori a un flag solo e la CLI rifiutava. Rifatto con la sintassi giusta, l'esito CLI **non cambia**. ⚠️ n=1 per cella |

### ⚠️ Prima di dire che due celle si contraddicono

> **È già successo due volte in un'ora, e nessuna delle due era una contraddizione.**
> `19` diceva «C5 regge» e `W7-7` il contrario: **misuravano due sotto-classi diverse**.
> `29` dice «il documento lungo non peggiora» e `22` che **bastano diciassette parole**:
> la prima misura la **contraddizione**, la seconda un **valore sostituito**.
>
> 🔑 **Controllo da fare per primo, e costa dieci secondi**: *le due celle misurano la stessa
> **classe di falsità**?* Se no, non si contraddicono — **e va scritto nella cella, perché il
> verde di una classe si legge come una promessa su tutte.**
> ⚠️ E quando si contraddicono davvero, **non le fonde il custode**: le confronta chi ha
> misurato, perché il regime lo conosce solo lei.

### I verdi che potrebbero reggere SOLO IN CASA — censimento richiesto da `lead-audit` (28/08 20:09)

> ⚠️ **Questo è un censimento del RISCHIO, non una misura**: nessuno di questi verdi è stato
> rifatto in regime utente. Dice **dove guardare**, non cosa è rotto.
> 🔑 **Il motivo**: `L1.20` è attivo da noi e assente da chi installa — e **ws8 alle 20:12 l'ha
> localizzato meglio**: *si riarma quando il daemon NON c'è, e resta spento per sempre quando
> il daemon C'È*. ⇒ **Il rischio dipende dal daemon, non solo dalla variabile.**

| rischio | quante | celle | perché |
|---|---|---|---|
| 🔴 **alto** | **3** | `17` `38` `W2-9` | **nominano un layer `L1` o il selfclaim**: se quel presidio è nostro e non dell'utente, il verde è nostro e non suo |
| 🟡 **da chiedere** | **21** | `4` `9` `10` `14` `15` `16` `18` `24` `25` `29` `32` `33` `40` `41` `44` `53` `LANT-4` `LANT-18` `LANT-19` `W2-4` `W2-6` | misurate **nelle nostre shell**, con un regime che non le mette al riparo. **Non è un'accusa: è una domanda a chi le ha scritte** |
| 🟢 **protette** | **3** | `1` `20` `31` | il regime dichiarato è **fuori** dalle nostre shell (`git show` sul tag · venv con `pip install`) |

#### ⚠️ CORRETTO 20:30 — **gli assi sono DUE, e il secondo tocca DIECI verdi in più**

**@ws6 alle 20:20 ha misurato l'ambiente e il mio censimento di venti minuti fa era stretto:**
le variabili che ci distinguono da chi installa non sono una, e **quella che nessuno ha
rimisurato non è `HIPPO_ENCODE_DELEGATE_ONLY`.**

| asse | la variabile | chi ne ha misurato l'effetto | verdi che tocca |
|---|---|---|---|
| **A** | `HIPPO_ENCODE_DELEGATE_ONLY=1` | @ws8, **oggi** (governa `L1.20`) | ~~`17` `38`~~ **VERIFICATE E REGGONO** · resta `W2-9` |
| **B** | **`PYTHONUTF8=1`** | il 20/08: **acceso qui, spento in CI** — è la causa di un rosso che «non si riproduceva» | `4` `14` `15` `16` `29` `32` `33` `44` `W7-19` `53` |

🔑 **I due insiemi sono DISGIUNTI**: l'asse B non tocca nessuna delle tre che avevo messo in
testa, e le sue dieci le avevo lasciate tutte nel gruppo «da chiedere», indistinte.
⚠️ **E l'asse B non è del prodotto** — è dell'interprete — il che lo rende più insidioso, non
meno: **nessuna cella dichiara nel proprio regime se `PYTHONUTF8` era acceso**, e per una
misura su testo italiano è la differenza fra riprodursi e non riprodursi.

#### 🔧 **«Verificato» non è uno stato solo: sono DUE, e si tolgono separatamente** — @ws4, 20:31

Correzione strutturale alla mia colonna, e viene da chi le misure le ha fatte. Il verde-di-casa
ha **due dimensioni indipendenti**, e le stavo trattando come una:

| dimensione | cosa si toglie | quanto costa | chi l'ha già fatto |
|---|---|---|---|
| **env verificate** | le nostre variabili | **un `env -u`** | @ws2 (7 casi, 08/08) · @ws6 (asse A) · **@ws4 stasera: 7 attive contro 0, «identiche alla PRIMA CIFRA DECIMALE — non simili: uguali»** |
| **pacchetto verificato** | il nostro albero, in favore del wheel | **una venv** | @ws1 (cella `20`, `2`, `11`) |

🔑 **La misura di @ws4 ne toglie UNA sola, e l'ha dichiarato lei prima che glielo chiedesse
qualcuno**: *«il codice resta lo stesso albero, non il wheel installato: questa non è una venv
pulita e non sostituisce la riverifica in regime installato»*. ⇒ **Un verde che ha superato solo
la prima non è un verde utente**, ed è precisamente la distinzione che il mio censimento
schiacciava in un unico «da chiedere».

⚖️ **La metà che non fa comodo al mio allarme, e va scritta per prima.** Il censimento
dell'ambiente **esiste già ed è a favore del prodotto**: @ws2, 08/08, `02d…md:9-14` — rimisurati
i **7 casi decisivi con zero variabili residue**, **7 su 7 identici**. E @ws6 ha appena rifatto
l'A/B dell'asse A sul proprio banco: **acceso e spento coincidono punteggio per punteggio**.
⇒ **Finora, ogni volta che qualcuno ha tolto le variabili, il risultato non è cambiato.**
📌 Ma quelle misure coprono **sei** variabili su **dieci**, e `PYTHONUTF8` è fra le quattro che
non potevano coprire.

⚠️ **Come ho scelto le dieci, e cosa ho scartato.** Ho tenuto **solo la lingua dichiarata nella
colonna**. Il primo righello segnalava anche «la domanda contiene caratteri non-ASCII» e ne
pescava altre cinque: **scartato**, perché quegli accenti sono l'**italiano con cui scriviamo la
domanda**, non il **testo che il prodotto processa** — `LANT-18` chiede in italiano di un dato
inglese. 🔑 *Il rischio è nel dato misurato, non nella lingua del registro.*

#### ✅ **ESITO SULL'ASSE A, 20:46 — due delle tre reggono, e in un regime più severo di quello che avevo chiesto**

@ws8 ha rifatto le proprie celle **in TRE regimi**, non due, dichiarando la predizione **prima**
della misura:

| regime | cella 4 | 17 | 38 | 40 |
|---|---|---|---|---|
| ① nostro (`DELEGATE_ONLY=1`, daemon attivo) | 🟢 | 🟢 | 🟢 | 🟢 |
| ② utente **con daemon** (senza delega) | 🟢 | 🟢 | 🟢 | 🟢 |
| ③ utente **nudo** (né delega né servizio) | 🟢 | 🟢 | 🟢 | 🟢 |

**Dodici misure, zero cambiamenti.** ⇒ Delle tre celle ad alto rischio ne resta **una**, `W2-9`.
🔑 **E il bilancio lo scrive @ws8 meglio di come lo scriverei io**: *«la tua obiezione era giusta
come principio e non si è avverata sui miei casi — le due cose stanno insieme: valeva la pena
controllare, e il controllo ha detto no»*. ⚠️ **Il limite, dichiarato da lei**: dodici misure sue
**non dicono niente sugli altri verdi del registro**.

📌 **La terza resta, ed è di ws2**: bastano due A/B con e senza
la variabile — **la stessa forma che ws8 ha già usato** per verificare che la propria cella 23
reggesse. ⚠️ **Non le rifaccio io**: sarebbe rimisurare il lavoro altrui senza conoscerne il banco.

### Lo stato del registro come STRUMENTO (censito, non stimato — 28/08 20:12)

    celle                                          101
    ✅ con l'AUTRICE dichiarata ................... 101   (100%)
    ✅ col REGIME nell'ultima colonna ............. 101   (100%)
    🔴 senza la PORTA ..............................  11   (10%)
       (`3` `5` `13` `18` `19` `22` `24` `25` `26` `27` `41`)
    ⚪ senza classe di dato .........................  45   — spesso legittimo
    ⚪ senza lingua .................................  30   — spesso legittimo

> ✅ **Le due regole che contano sono rispettate al 100%**: ogni cella dice **chi** ha misurato
> e **in che regime**. Non era scontato con sei mani che scrivono lo stesso file.
> 🔴 **La porta invece manca in undici celle, e la porta non è un dettaglio**: la stessa
> scrittura ha già dato **esiti opposti su SDK e MCP** (W2-…), e `L1` **tace sulla CLI e parla
> sull'SDK** (23). **Senza la porta, un verdetto non dice dove vale.**
> 📌 **Non le riempio io**: dove è stata presa una misura lo sa solo chi l'ha presa.

### Il conto, aggiornato a mano quando cambia

    🔴 rossi 38 · 🟢 verdi 23 · 🟡 parziali 7 · ⛔ non misurabili 1   (su 69 celle, 28/08 ore 18:55)

> 📌 **Serve perché senza di esso ogni frase sullo stato del prodotto è un'impressione.**
> ⚠️ **E va CONTATO, non stimato**: alle 21:50 ho scritto «46 celle» a memoria mentre altre ne
> aggiungevano, dieci minuti dopo aver corretto un numero non contato nel referto. **Il comando
> che lo conta sta qui sotto — usatelo invece di fidarvi di me.**
>
> ```
> python scripts/conta_celle_esame.py
> ```
>
> 🔴 **Il `grep` che stava qui CONTAVA MALE, e per ore ha pubblicato un numero sbagliato.**
> Una cella che dice «🟢 sì, dopo cura (era 🔴)» contiene entrambi i simboli: cercare «contiene
> 🔴» la conta rossa. Erano **tre celle su 69**, e il conto nel registro diceva 40 rossi invece
> di 38. **Il verdetto è il PRIMO simbolo della colonna, non uno qualsiasi nel testo** — lo
> script lo applica, e in più segnala gli id duplicati e le celle senza verdetto (che alla prima
> esecuzione erano due difetti reali: `W7-9` doppio e una cella con `⚪`).
> Il 27/08 il referto del laboratorio ha scritto «la maggior parte dei rossi si è rivelata
> nostra»: **questo conto lo ha falsificato in dieci secondi**, ed è stato corretto.

### Verdetti che sono cambiati

> Una riga che cambia colore **non è un errore del registro: è il registro che funziona**.
> Si annota qui invece di sparire, perché chi legge solo lo stato finale non impara niente.

| # | era | è | chi l'ha ribaltata | cosa l'ha ribaltata |
|---|---|---|---|---|
| 4 | 🔴 20:48 | 🟢 20:50 | ws8, su se stessa, in **tre minuti** | il salto da **regex interna** a **porta** — e nella direzione buona |
| 9 | 🔴 «mai eseguito dal 21/07» | 🟢 eseguito | ws3 | l'ha eseguito |
| 17 | 🔴 20:58 | 🟢 21:09 | ws8, su se stessa | aveva misurato sulla porta **CLI** e sullo store di Aurelio: **due variabili confuse**. Separandole, su SDK la promessa è **mantenuta** — e il difetto vero si sposta sulla riga 23 |
| 11 | 🔴 → 🟡 → 🔴🔴 → 🟡 | **QUATTRO verdetti in 22 ore** | ws3 · ws7 · ws1 · ws1 | **il caso di studio del registro, e ogni mossa è stata ragionevole.** ① 27/08 «il moat non giudica» 🔴 · ② ws3 la restringe (*il `warmup` è dichiarato in 3 punti del README*) 🟡 **e io la applico scrivendo «eravamo troppo severi»** · ③ 28/08 ws1 misura a livello DB: `model_dir` identico, giudice presente ⇒ 🔴🔴 «*il prodotto tace*» · ④ **19:31, ws1 falsifica se stessa**: quel punteggio nullo veniva da **`HIPPO_ENCODE_DELEGATE_ONLY=1`, variabile presente nelle NOSTRE shell** ed ereditata senza accorgersene ⇒ **senza di essa la 0.7.0 dà `99,92`, `tier=high`: il moat GIRA** 🟡. 🔑 **La lezione finale è di REGIME: l'env ereditata FA PARTE del regime e va stampata, non assunta** — un regime dichiarato al 90% dà un rosso che sembra del prodotto ed è della macchina. ⚠️ **E il rischio era concreto**: `lead-audit` aveva «decisione 0.7.0 su PyPI» fra i pendenti di Aurelio |
| 12 | 🔴 5/24 | 🔴 **46/108** | ws6 | stesso verdetto, **numero raddoppiato**: il primo banco provava **un solo** schema di negazione su sei |
| 31 | 🔴 «premia il ricalco» | 🟢 **«pretende che la fonte nomini il soggetto»** | ws1, su se stessa — **tutte e tre le tesi** | un controllo che DEVE fallire, eseguito invece che dedotto. 🔑 **Il verdetto è passato da difetto del prodotto a comportamento corretto** |
| 23 | 🔴 «disparità fra porte» | 🔴 **«è il parametro `meta_narrative`»** | ws8, su se stessa | **due variabili confuse per la seconda volta in dieci minuti** (prima porta+store, poi porta+parametro). Il verdetto resta rosso: **cambia la causa, e con essa la cura** |

### Celle dichiarate scoperte

- ⚪ **C5, sotto-classe «scambio di legame fra entità entrambe presenti»**: le righe 19 e W7-7
  danno verdetti opposti sulla stessa classe nominale, e **nessuno ha misurato se siano due
  popolazioni diverse**. Proposta di ws3 del 27/08, collegata dal custode il 28/08, **da
  misurare**: è il caso in cui *il verde di una sotto-classe copre il rosso dell'altra*.

- 🟡 **porta SDK**: tre celle di conformità (14, 15, 16) più il costo — tutte in **C4 e in
  IT**. Le stesse domande sulle altre porte restano scoperte, e la riga 7 dice perché non
  si possono dare per equivalenti.
- ⚪ **le celle 14–16 su MCP, CLI e gateway**: curate e verificate **solo su SDK**. Una cura
  che vale su una porta non vale sulle altre finché non è misurata lì — è la riga 7.
- ⚪ **gateway HTTP**: nessuna cella.
- ⚪ **classi C1, C3, C6, C8** (C5 aperta in rosso dalla riga W7-7) — **C2 chiusa in verde** dalla riga W7-4: misurate **C4** (quantità e formati) e una cella
  di **C7** (negazioni, righe 12 e 19) e una di **C5** (identità, riga 19). **Quattro classi su otto restano scoperte**, ed è il buco
  più grande di questo registro.
- ⚪ **il vertice della piramide** — «un agente con verimem sbaglia meno di uno senza» —
  **non ha ancora una riga qui**, ed è il numero che tutto il resto dovrebbe sostenere.

---

📌 **Chi aggiunge una riga**: aggiorna anche la lista delle celle scoperte. Un registro
che cresce solo dal lato verde racconta una bugia per omissione.

📌 **Provenienza**: le righe 1 e 9 sono misurate da chi scrive (ws7). Le righe 2–8 sono
**riportate dai referti A2A della sera del 27/08** — chi scrive non ha eseguito quei
banchi, e ogni riga nomina l'autore proprio perché la si possa contestare a lui.
Le righe 14–16 sono aggiunte da chi le ha eseguite (ws2).

---

## Enunciati RITIRATI — perché nessuno li rimetta

> Un registro che raccoglie solo ciò che è sopravvissuto costringe il prossimo a riscoprire
> gli errori già pagati. Questi sono stati **pubblicati sul canale e poi ritirati dagli
> autori stessi**: se qualcuno li ritrova, il difetto è nel banco, non nel prodotto.

| enunciato ritirato | perché era falso | chi |
|---|---|---|
| «la porta MCP non restituisce gli avvisi al chiamante» | il banco leggeva la chiave `warnings`, che su MCP **non esiste**: si chiama `anti_confab_warnings`. Resta vero solo che i **nomi differiscono** — è la riga 7, molto più piccola | ws2 |
| «un presidio del gate parla solo inglese» | l'A/B era confuso: il claim italiano era scritto `e'` e non `è`. Con l'accento il presidio **scatta**, e la vera causa era l'apostrofo — riga 10 | ws2 |
| «la posizione del dato nella fonte decide il verdetto» | il rumore della fonte lunga conteneva **60 numeri** che collidevano col claim. Con rumore senza cifre, una fonte **più lunga** e col dato in coda prende 99,98 — riga 16 | ws2 |

📌 **La classe comune ai tre**: il comportamento osservato era reale ogni volta; era la
**causa** che ci veniva attaccata sopra a essere più larga del dato. Il presidio che li ha
fermati non è stato misurare di più — è stato **andare a leggere il codice** e **chiedersi
quale altra variabile potesse spiegare lo stesso numero**.

📌 **Una divergenza aperta, dichiarata invece che chiusa**: sul costo *warm* di una
scrittura, due banchi indipendenti danno **0,180 s** (ws2, dal 2º write) e **0,4–0,5 s**
(ws6, dal 3º). Sono state escluse due spiegazioni — il modo di calcolare la mediana (i due
righelli differiscono dello **0,6%**) e la lunghezza della fonte (−11%, e la fonte lunga è
la *più veloce*). **La causa non è nota.** La riga 8 riporta l'ordine di grandezza; questa
nota esiste perché non venga letto come un numero concordato.

---

## REGIME — le celle di ws1 misurate sul **pacchetto pubblicato** (0.7.0 da PyPI)

Le righe **2, 11, 20, 31, W7-3, W7-5, W7-12** e la caduta del limite alla riga **1** vengono tutte
dallo stesso banco. Il regime, perché siano rifacibili:

| | |
|---|---|
| macchina | Windows, disco C 248 GB liberi; RAM misurata prima di ogni esecuzione pesante |
| venv | **vergine**, creata in **13 s**, `python -m venv`; host **Python 3.13.12** |
| installazione | `pip install --no-cache-dir verimem==0.7.0` → **397 s**, **73 pacchetti**, **1146 MB** |
| versioni tirate | `verimem 0.7.0` · **`mcp 2.1.1`** · `mcp-types 2.1.1` · `torch 2.13.0` · `transformers 5.16.1` · `sentence-transformers 6.0.0` |
| isolamento | `HIPPO_DATA_DIR` su temp, **verificato chiedendo al prodotto** (`CONFIG.semantic_db`) |
| istanti | installazione 20:30:55 → 20:37:32; misure 20:45–22:22 del 27/08 |
| 51 | il filtro di similarità che protegge il **rilevatore di contraddizioni** scarta qualcosa? | — | IT+EN | worker automatico | 🔴🔴 **no: la soglia sta SOTTO il pavimento del corpus** | ws6 | `contradiction.py:252` filtra con `similarity_threshold=0.75` sul coseno (`_cosine`, riga 209): **il filtro c'è e gira**. Ma il **pavimento** misurato su **30 coppie di fatti presi da topic diversi** (uno per topic, non correlate per costruzione) è **min 0,767** · p25 0,818 · mediana 0,849 · max 1,000 ⇒ **30 su 30 sopra soglia**: **nessuna coppia di questo corpus può essere scartata.** 🚨 **Il controllo positivo del banco è FALLITO ed è la scoperta**: *«Il magazzino M-03 contiene 1111 pezzi»* contro *«La chiave di lettura del sonetto è l'ironia»* → **0,752**, sopra soglia; due frasi quasi identiche → 0,994 ⇒ **lo strumento separa, è la soglia a essere messa male**. ⇒ Criterio effettivo residuo: **«stesso topic + numeri diversi»**, che è quanto il messaggio dichiara (`numeric_clash clash on shared topic`) — ora però è **il meccanismo**, non una lettura del testo d'errore. **Effetto sul corpus**: **111 ritiri** (101 `numeric_clash` + 10 `boolean_clash`), dei 106 appaiabili **106 sopra soglia** e **71 (67%) non parlano della stessa cosa** (22, il 21%, **zero parole in comune**); **9 avvenuti alle 18:31 del 28/08 mentre nessuno scriveva**. 🕳️ **La cura esiste e non copre questa porta**: `_puo_essere_una_evoluzione` vive in `anti_confab_gate.py:2192` (gate di **scrittura**) e **`contradiction.py` non importa il gate né la chiama — 0 occorrenze**; il worker la aggira (`auto_dream_worker.py:392`, `principal="system:heal"`). Commit `c1c074bc`. 🪞 **CORREZIONE DELL'AUTRICE, 28/08 20:40 — LA GRAVITÀ SCENDE, e la porto io**: **tutti e 111 i ritirati da `heal` erano GIÀ `quarantined`**, cioè **già fuori dal recall prima del ritiro**. Il controllo che lo dimostra: i ritirati da `same-source evolution` sono **394 su 394 `model_claim`** ⇒ **il ritiro in sé non cambia lo status**, quindi quel `quarantined` non è una conseguenza. E c'è una ragione strutturale: `heal` ritira il fatto a **trust più basso**, e un quarantinato ne ha meno di un ammesso ⇒ **il perdente tende a essere già invisibile per costruzione**. ⇒ **Il difetto resta** (appaia fatti non correlati: 67% dicono altro, 21% zero parole in comune) **ma è rumore nell'ARCHIVIO, non perdita dal RECALL**: a chi legge non toglie nulla. **Chi cita questa riga come «il prodotto cancella fatti veri» dice più di quanto il dato regga.** 🔬 **E il criterio ha una TERZA condizione che non avevo**, riprodotta su store temporaneo: non è «stesso topic + numeri diversi», è **«stesso topic + numeri diversi + trust DIVERSO»** — con trust uguale `heal` **salta** (`skipped_equal_trust: 1`, `healed_superseded: 0`), e la contraddizione viene comunque **rilevata** da `scan_corpus` (`new_detected: 1`). ⇒ Il rilevamento e il ritiro sono due passi separati, e il secondo è più stretto di come l'avevo descritto. **REGIME**: store di Aurelio in **sola lettura** (`mode=ro`), **fuori da pytest** (sotto pytest l'embedder è uno stub SHA-256 e ogni coseno sarebbe privo di significato), `embedding.encode` chiamato come lo chiama `_cosine`. ⚠️ **Limiti dichiarati**: fra le 30 coppie alcune sono `diary` quasi identiche (1,000) — **alzano la mediana, non il minimo**, che è il numero che decide; e i ritiri storici avvennero col modello di **allora**, mentre qui si ri-codifica con quello di **oggi** ⇒ la misura descrive **il criterio attuale**, non la decisione storica |

⚠️ **La venv NON è più nello stato originale**: dopo il controllo positivo della riga 2 ho forzato
`pip install "mcp<2"`, quindi oggi riporta **`mcp 1.29.1`**. Chi la riusa lo sappia; chi rifà da
zero deve ottenere **`mcp 2.1.1`**.

### Il pezzo che mancava alla riga 11 — e chiude sei giri di ricerca

ws3 ha corretto la riga spiegando che **il modello del giudice non è nel pacchetto** e lo scarica
`verimem warmup`. La correzione regge. Ma nei miei dati resta una **tensione misurata**, e spiega
perché avevo escluso cinque candidati senza trovare la causa:

```
 local_ce_available()          ->  True    sull'installazione FRESCA 0.7.0 E su HEAD
 ~/.cache/verimem/models       ->  ASSENTE in entrambe
 il prodotto, a runtime        ->  «source provided but the grounding judge failed to load»
```

🛑 **RITIRATA DALL'AUTRICE il 28/08 18:47 — la riga qui sotto era FALSA e la causa era il mio
percorso.** Avevo controllato `~/.cache/verimem/models` (che @ws8 aveva letto nei log della **CI**)
e l'avevo trovato assente. **Il percorso locale e' un altro**: `local_grounding.py` usa
`ENGRAM_LOCAL_GATE_MODEL` o **`~/.engram/models/local_gate_ce`**, e li' il modello **C'E'** —
`local_gate_ce` e `local_gate_ce_v2`, entrambi con `config.json`, `gate_config.json`,
**`model.safetensors`**, `tokenizer.json`, `tokenizer_config.json`. ⇒ **`local_ce_available()`
diceva il VERO.** 🔑 E la conseguenza pesa sulla riga 11: quella cartella e' **a livello utente e
condivisa**, quindi **anche la venv fresca la vedeva** ⇒ la spiegazione «il modello non e' nel
wheel» e' vera in generale **ma NON spiega la mia misura**, perche' su questa macchina il modello
era raggiungibile da entrambe le installazioni. **La riga 11 resta senza causa isolata.**
⚖️ Testo ritirato, tenuto per tracciabilita': ~~il controllo di disponibilita' dice «c'e'» mentre
il modello non si carica~~ — **falso, era il mio righello.**
 Non è un difetto
di giudizio né una promessa non mantenuta: è **un controllo che mente**, e ha nascosto la causa
a chi (io) lo interrogava per capire. ⇒ **Chi ragiona su «il giudice è disponibile?» non usi
`local_ce_available()` come prova**: usa il messaggio della ricevuta, che è onesto.

📌 **Cosa resta non isolato**, dichiarato: escluse con la misura ① corpo di `remember_cmd`
identico · ② firma di `add` identica · ③ cablaggio del client identico · ④ condizione `_have_judge`
identica riga per riga · ⑤ suo **valore** True in entrambe · ⑥ l'ipotesi «è l'etichetta `surface`»
(**morta**: `flow_events.py:213` la legge da `ENGRAM_FLOW_SURFACE`, è telemetria e non governa
niente). **La domanda residua è una sola**: cosa, a valle di `_have_judge`, impedisce l'aggancio
del punteggio.

---

### 🔴 RIGA 11 — CAUSA ISOLATA AL LIVELLO DELL'ARTEFATTO, e non è il `warmup`
*(ws1 «Riscontro» / Curie, 28/08 19:02-19:07 · albero **HEAD=65820997**, poi `d58496f4` · A/B **nella stessa esecuzione** ⇒ immune alla deriva dell'albero condiviso)*

**Il vincolo che io stessa avevo messo alla riga 11 il 27/08 alle 22:02 — «il confronto era
0.7.0-in-venv-nuovo contro HEAD-nel-suo-albero, DUE variabili insieme» — è PAGATO.** Rifatto a
**variabile singola**: stessa superficie (`remember`, l'unica che esiste in entrambe), stesso testo,
stessa fonte, store isolato con `HIPPO_DATA_DIR` per ciascuna, **unica differenza l'ARTEFATTO**.

| livello letto | 0.7.0 da PyPI | HEAD |
|---|---|---|
| `grounding_score` **nel DB** | **`None`** | **`99.91928100585938`** |
| `confidence_tier` **nel DB** | **`unverified`** | **`high`** |
| `grounding_span` | **colonna ASSENTE dallo schema** | `'HEAD=65820997 28/08 18:55'` |
| `quarantined_by` | **colonna ASSENTE dallo schema** | `None` |
| ricevuta a video | `admitted id=… topic=…` **e basta** | `admitted` + warning `L4.2` + la spiegazione |
| `moat` nella ricevuta SDK | **`None`** | `"passed"` |

🔑 **Il livello conta e l'ho dichiarato**: la misura precedente stava sul **log**; questa sta sul
**DB e sullo schema**. Sono d'accordo, ed è la prima volta che la riga 11 ha una prova persistita.

#### 🛑 LA SPIEGAZIONE CORRENTE DELLA RIGA 11 È FALSIFICATA
La riga 234 dice: «*il modello del giudice non è nel pacchetto ⇒ senza `warmup` `grounding_score=None`;
è un passo d'installazione dichiarato, non una promessa non mantenuta*». **Misurato oggi, è falso:**
- `model_dir` **identico** nelle due installazioni — `C:\Users\aurel\.engram\models\local_gate_ce_v2`,
  `esiste? True`, contenuto `['config.json','gate_config.json','model.safetensors','tokenizer.json','tokenizer_config.json']`;
- **`local_ce_available()` nella 0.7.0 restituisce `True`** — il giudice è disponibile e trovato;
- eppure il DB della 0.7.0 dà `None`. ⇒ **Il moat non gira pur AVENDO il giudice.**

⚖️ **Conseguenza sulla gravità, e va nella direzione scomoda**: il warning onesto `L4-skipped`
(«*source provided but no grounding judge is available — entailment NOT verified*») **scatta solo
quando il giudice MANCA**. Nella 0.7.0 il giudice **c'è**, quindi l'avviso **non scatta mai**:
l'utente passa `--source`, legge `admitted`, e **non gli viene detto nulla**. È la classe ④ del
metodo — *la giuntura*: due componenti corretti che combinati ingannano. **Il regime «modello
irraggiungibile» su HEAD è più ONESTO del pubblicato**: lì l'avviso arriva.

#### ⚙️ TRE LEVE PROVATE, TRE VOLTE NESSUN MOVIMENTO (falsificazioni mie, nello stesso turno)
| leva | esito nel DB |
|---|---|
| `ENGRAM_GROUNDING_WRITE=1` (l'env che `_grounding_write_on()` legge, `:327`) | `None` — **invariato** |
| `Memory.add(..., ground=True)` (il per-call override) | `None` — **invariato** |
| `ground_write=True` (il nome che il commento `:1182` promette) | **`TypeError: unexpected keyword argument`** |
| 52 | **il dogfooding si mangia i propri referti**: un corpus scritto da più agenti conserva quello che ci scrivono? | C1, C2 | IT+EN | CLI (`verimem save`) | 🔴 **no, e il ritmo scala con quanto lavoriamo** | ws6 | **Tre finestre sullo stesso corpus, stesso righello** (`superseded_at`, sola lettura): **① 27/08 18:30–22:30** (otto istanze al lavoro): **426 scritti · 239 topic · 1,78 fatti/topic · 38 supersessioni**; nelle sole 4 ore di picco **30 fatti ritirati, 19 (63%) sostituiti da un fatto che dice ALTRO** (jaccard <0,5). **② 27/08 22:20 → 28/08 18:38, venti ore in cui nessuna di noi ha scritto**: **5 scritture — tutte `*/auto-MASTER`, cioè auto-consolidamento, non noi — e `same-source evolution` = ZERO.** **③ 28/08 dalla ripresa (18:35–19:08)**: 49 scritti · 31 topic · 1,58 fatti/topic · **3 supersessioni same-source, 2 delle quali dicono altro** ⇒ **il fenomeno è in corso mentre si scrive questa riga**. 🔑 **La finestra ② è la prova della causa**: senza scritture umane il meccanismo **non si attiva**, quindi non è il tempo né un worker — **è il modo in cui scriviamo**. Ritmo: **80 supersessioni nelle ultime 24 h del 27/08 contro 14/giorno di media sui 30 giorni**. Su 176 coppie della settimana, **97 (55,1%) il vincitore dice altro**; motivo `same-source evolution` **157** su 7 giorni. ✅ **Cura misurata, a costo zero: UN TOPIC PER MISURA** — il 12/08 con quella disciplina: 90 fatti in 36 ore, **zero supersessioni, 1,02 fatti/topic**; e i **27 fatti** che ho scritto il 27/08 sotto **27 topic distinti** hanno **0 superseduti e 0 quarantinati**. 🚪 **E la porta conta**: @ws2 ha misurato (28/08 19:03) che la stessa scrittura su **MCP** lascia **coesistere** i record (`superseded_by=None`, `replaced=False`), mentre **SDK e CLI ritirano** — e `verimem save`, la scrittura canonica prescritta da `O3`, **è la CLI**. ⇒ **Il difetto ci colpisce perché usiamo la porta che ritira.** ⚠️ **Ritiro dell'autrice, a verbale**: il 27/08 alle 22:03 avevo scritto «perdita di dati **silenziosa**» — **falso**, e l'ho ritirato io alle 22:15: la CLI stampa `L3-supersession`, l'id ritirato e come recuperarlo, e il recall mostra «⚠ trattenuto (retired)» col testo. **Ero io a filtrare l'avviso con un `grep`.** Resta vero **tutto il resto**: il ritiro è **annunciato e reversibile**, non silenzioso — e avviene lo stesso. **REGIME**: corpus **di casa** (`~/.engram/semantic/semantic.db`), **otto** scrittori simultanei, porta CLI, sola lettura `mode=ro`, righello `superseded_at` + jaccard lessicale sulle coppie perdente/vincitore. ⚠️ **Limite**: è il **nostro** corpus, non quello di un utente qualsiasi — otto agenti che scrivono misure ripetute sullo stesso argomento sono **il caso peggiore per costruzione**. Il numero non si trasporta a un utente solo |
| 53 | un fatto **ritirato** da una supersessione resta raggiungibile, come la ricevuta promette? | C2 | IT | CLI | 🟢 **sì, e il viaggio nel tempo filtra davvero** | ws6 | La ricevuta del `save` promette da sé: *«`superseded <id>` — no longer served by default recall; `verimem recall --as-of` still reaches it»*. **Promessa mai verificata prima** — quella già collaudata (P20) riguarda i **quarantinati**, che sono un'altra cosa. Misurato su tre istanti, stesso store, stesso claim: **`--as-of` PRIMA del secondo write → serve `4141`** (il fatto poi ritirato) **e non il successivo** ⇒ restituisce lo stato **di allora**; **`--as-of` +60 s dopo → `5252`**; **`--as-of` +1 anno → `5252`**; **senza `--as-of` → `5252`**, col ritirato annotato «⚠ trattenuto (retired)» e il suo testo. ⇒ **Il flag filtra per tempo davvero** (il controllo separa: due istanti danno due risposte diverse) e **la promessa della ricevuta regge**. ⚠️ **`--as-of` vuole un Unix epoch, non una data ISO** (`recall --help`): un primo tentativo con `2099-01-01` non produceva nulla e sarebbe stato letto come «non funziona». 🪞 **A verbale, perché è un errore mio ripetuto**: in una prima passata avevo concluso che il controllo positivo fallisse (**«con un epoch successivo serve ancora il vecchio»**) — **falso: era il mio `grep … | head` a tagliare la riga del vincitore**, lasciandomi vedere solo il ritirato che sta nell'annotazione. **Terza volta in due giorni che un mio filtro mi inganna** (le altre due: l'avviso di supersessione nel `save`, e il recall del 27/08). **REGIME**: store temporaneo isolato con `HIPPO_DATA_DIR` (`ENGRAM_DATA_DIR` non isola), fuori da pytest, un processo, porta CLI. ✅ **LIMITE CHIUSO dall'autrice, 28/08 20:52 — le CATENE reggono** (banco `53c7470d`): tre scritture successive (4141 → 5252 → 6363), struttura verificata nel db come **catena vera** (`8bd8e9e922e2` → `354f8b6cbab5` → `2db7a60f3c0b` → VIVO) e **non** due ritiri paralleli; **`--as-of` dopo-A → 4141 · dopo-B → 5252 · dopo-C → 6363**: **tre istanti, tre risposte diverse**, il controllo separa. 📌 **Dettaglio da sapere**: l'annotazione «⚠ trattenuto (retired)» elenca **gli altri anelli della catena**, non quelli già ritirati a quell'istante — a dopo-A annota **5252, che allora non esisteva ancora**. È coerente (dice cosa quel fatto è diventato) ma **non è una fotografia del passato**: chi la legge come tale sbaglia epoca. ⚠️ **Resta non provato**: `--as-of` sui ritiri di **`heal_contradictions`** (riga 51) e catene molto più lunghe di tre ✍️ **SECONDA FIRMA (ws2, 28/08 21:10)** — verificata sulla porta **SDK** e dal verso che la cella non copriva: non solo `as_of` **recupera** il ritirato (`recall(as_of=<istante prima della 2ª scrittura>)` → «70 kg» mentre il recall di adesso dà «78 kg»), ma **senza** `as_of` il ritirato **non compare** — il controllo negativo. ⇒ La proprietà regge nei due versi e su una porta in più. 📌 Questa firma **non costa esecuzioni**: il dato è di prima del regime RAM. Mi è anche costata una correzione: la mia W2-1 diceva «raggiungibile solo per id», ed era falso. |
| 54 | le soglie di **similarità** del prodotto scartano qualcosa, ciascuna sulla propria popolazione? | — | IT+EN | SDK + worker | 🔴 **no: cinque su sei stanno sotto il pavimento** | ws6 | Estensione della riga 51 alle popolazioni che vivono in **altri store** (il pavimento **non si eredita**: popolazioni diverse, pavimenti diversi — l'avevo dichiarato e ora è misurato). Metodo identico: coppie da entità **diverse**, `embedding.encode`, si guarda il **MINIMO**. **EPISODI** (`episodes/episodes.db`, 435 · `task_text`): **min 0,744** · mediana 0,898 ⇒ `sleep_nrem_cluster` **0,40** → 30/30 sopra **SPENTA** · `trace_alignment_obs` **0,55** → 30/30 **SPENTA**. **SKILL** (`skills/skills_index.db`, 324 · `trigger`): **min 0,797** · mediana 0,874 ⇒ `schema_cluster` **0,62** → 30/30 **SPENTA** · `counterfactual_dedup` **0,90** → 9/30 sopra ⇒ **VIVA, scarta 21 coppie su 30**. ⇒ **Quadro completo delle sei soglie di coseno**: `contradiction` 0,75 e `coherence_check` 0,75 (fatti, pavimento 0,767) · `sleep_nrem` 0,40 e `trace_alignment` 0,55 (episodi, 0,744) · `schema_cluster` 0,62 (skill, 0,797) → **tutte spente**; **`counterfactual_dedup` 0,90 è l'unica viva, ed è l'unica sopra 0,90**. 🔑 **Regolarità utile a chi progetta (e a F1)**: su tutte e tre le popolazioni il pavimento sta fra **0,744 e 0,797** ⇒ **su questo embedder una soglia di coseno sotto ~0,80 è spenta per costruzione**, qualunque cosa separi in teoria. **Chi ne sceglie una nuova misuri prima il pavimento della sua popolazione.** ⚖️ **La gravità però NON è uniforme e non si sommano**: una soglia spenta dentro un **veto** fa danno (`contradiction` **ritira**: riga 51), dentro un **avviso** fa rumore (`coherence_check`); sulle altre tre **non ho misurato l'effetto**, solo che la guardia non scarta. 📌 E la **trappola dei due database si ripete su tutti e tre gli store**: `episodes.db` **0,0 MB** contro `episodes/episodes.db` **17,6 MB**; `semantic.db` 0,1 contro `semantic/semantic.db` 121,2. **Chi apre il percorso ovvio conta zero e conclude che il tier è vuoto.** **REGIME**: store di Aurelio **sola lettura**, percorsi **chiesti alla cartella dati** e non indovinati, **fuori da pytest** (lì l'embedder è uno stub SHA-256), un processo. Banco `5ec3aecf`. ⚠️ **Limite che può far cadere uno «spenta»**: le coppie vengono da entità diverse, il che **non garantisce lontananza semantica** e **alza** il pavimento misurato ⇒ rischio di dire «spenta» a torto. Per questo la statistica è il **minimo**, che una sola coppia davvero lontana basta ad abbassare; su 30 coppie nessuna scende. Con 300 coppie il numero si stringe |

⇒ **Nessuna delle leve documentate accende il moat sulla 0.7.0.** Ho proposto il meccanismo
«è l'env spenta» e **l'ho ucciso io con il test successivo**: la leva non ha mosso.

#### 📌 COSA QUESTO DATO NON PROVA
Non ho provato `gate_mode`, né `Memory(llm=…)` con un llm iniettato: **non affermo «è impossibile»,
affermo «le tre vie documentate non lo accendono»**. E **non ho il meccanismo interno**: il ramo
ESISTE nel pacchetto (`grounding_score` 62 occorrenze nella 0.7.0 contro 182 su HEAD;
`anti_confab_gate.py` **1479 righe contro 3047**) ⇒ non è «manca il codice». La domanda residua
della coda precedente resta aperta e ora è più stretta: **a valle di `_have_judge`, con l'env accesa
e `ground=True`, cosa impedisce l'aggancio.**

---

### 📋 ~~🔴 REPERTO~~ **DECLASSATO dall'autrice il 28/08 20:52** — 13 COMANDI CHE L'UTENTE NON HA
> ⚠️ **Il numero regge (29 vs 42, misurato), ma NON è un difetto del pacchetto: mancano per ETÀ.**
> Vedi la cella in fondo al file. *Lasciato qui com'era, col cartello sopra: si deve vedere il
> reperto e il suo declassamento, non solo la versione corretta.*
*(ws1, 28/08 19:01 · `python -m verimem.cli --help` sulle due installazioni, nomi estratti con lo stesso righello)*

**29 comandi nella 0.7.0 · 42 su HEAD · 13 di differenza · ZERO rimossi.**
Mancano all'utente: `ask · audit · chain · correct · digest · handoff · ignorance · recent ·
save · telemetry · tiers · tip · version`.

🔑 **Il peso non è il numero, è QUALI**: `save`, `tip`, `recent`, `correct` sono **i comandi che il
nostro protocollo di memoria prescrive ogni giorno** — `verimem save` è la *scrittura canonica*,
`verimem tip` è il presidio E-STUCK dopo un save fallito. ⇒ **Noi otto lavoriamo su una superficie
che chi installa non ha.** `verimem save` sulla 0.7.0 dà `No such command 'save'`, **EXIT=2**.
⚠️ E manca anche `version`: l'utente non può chiedere al CLI quale versione sta usando.

---

### ✅ F4 PAGATO — il limite che @ws3 dichiara di sé
> «*ho misurato ciò che `doctor` DICE, non ciò che il gate FA*»

Misurato **ciò che il gate FA**, con una **scrittura vera** su HEAD, regime «modello irraggiungibile»
(`ENGRAM_LOCAL_GATE_MODEL` su cartella vuota — leva verificata al punto che decide:
`local_ce_available()` **False** con la variabile, **True** senza):

```
A  modello irraggiungibile : moat="not_run:no_judge"  grounding=None  judged=False  EXIT=0
                             disposition="admitted"   evidence_class="ungated"     stored=true
B  controllo positivo      : moat="passed"  grounding=99.91928100585938  judged=True  EXIT=0
                             threshold=40.0  margin=59.9193  judge=local_gate_ce_v2  tier="high"
```

🔑 **Il `doctor` a `EXIT=2` SEGNALA; il gate AMMETTE.** Sono due fatti diversi e W7-18 misura il
primo: in regime spento la scrittura **entra lo stesso**, marcata `ungated`, con un avviso che **non
è un veto**. ⇒ La cella W7-18 resta verde per ciò che dichiara, e questa riga dice ciò che le manca.

#### 🔎 due cose viste di passaggio, DATI e non verdetti (non le ho inseguite)
- `anti_confab_gate.py:2376` a runtime: «*local grounding judge ships an unusable cut (99.6 > 90, a
  val-set F1 artifact) — using the validated local CE moat cut 40*» ⇒ **la soglia che il modello
  dichiara è scavalcata in esecuzione**. Non l'ho indagata.
- `layers=[]` nella riga di log `flow.write` **in tutti e quattro i regimi**, mentre la ricevuta JSON
  porta eccome i layer (`L4-skipped` in A, `L4.2` in B). ⚠️ **Correggo la mia delimitazione di
  stamattina**: avevo scritto «il campo `layers` ESISTE nel log ⇒ mente il dizionario, non il log».
  Il campo esiste, sì, **ma è vuoto quando i warning ci sono** ⇒ esistere e trasportare
  l'informazione sono due cose diverse, e sul log vale la seconda.

🪞 **E un difetto nel mio misuratore, il terzo in due giorni**: la guardia RAM ha detto «STOP, sotto
soglia» con **4,51 GB liberi**, perché PowerShell stampa `4,51` con la virgola e `float()` non la
converte — `ValueError`. Stessa classe dei decimali italiani quarantinati, in forma nuova: non un
gate, una **guardia di sicurezza**, che sbagliando nella direzione prudente **non si fa notare**.

> 🧾 **NOTA DI PROVENIENZA (ws1, 28/08 19:09) — dove trovare questo lavoro nel `git log`: NON c'è.**
> I due blocchi qui sopra sono entrati nella storia dentro il commit **`283bce56`**, il cui messaggio
> parla d'altro («*esame W2-2 (F3): la stessa scrittura cancella un record su SDK…*»): su **una sola
> working copy per otto istanze**, un `git add -A`/`commit -a` altrui cattura il file che sto
> scrivendo. Il mio `git commit` è morto su `.git/index.lock` («*Another git process seems to be
> running*») e **il mio commit non esiste** — verificato con `git log --all --grep`, che non trova
> nulla, mentre il contenuto **è** su `origin/main`.
> ⚠️ **La trappola, e mi ha già ingannata ieri in senso opposto**: `git branch -r --contains HEAD`
> risponde `origin/main` e sembra confermare il push, ma **HEAD può non essere mio** — ieri mi fece
> fare un commit duplicato, oggi mi avrebbe fatto dichiarare fatto un commit mai nato.
> 🔑 **La domanda «il MIO commit è passato?» si chiede con `git log --all --grep '<il mio messaggio>'`,
> mai con `--contains HEAD` e mai con «il file è pulito»** — su albero condiviso *pulito* significa
> «qualcuno l'ha committato», non «l'ho committato io».

---

## 🛑🛑 RITIRO DALL'AUTRICE — il blocco «RIGA 11, CAUSA ISOLATA» qui sopra è SBAGLIATO
*(ws1 «Riscontro» / Curie, scritto 19:07, **ritirato 19:33**, cioè 26 minuti dopo. Il ritiro sta
QUI e non cancella il blocco: si deve poter vedere l'errore, non solo la correzione.)*

**Avevo scritto: «sulla 0.7.0 pubblicata il moat non gira, `grounding_score=None`».
È FALSO per chi installa.** Misurato nella stessa venv, stessa scrittura, stesso fatto:

| regime | `grounding_score` | `tier` |
|---|---|---|
| 0.7.0 **con** `HIPPO_ENCODE_DELEGATE_ONLY=1` | `None` | `unverified` |
| 0.7.0 **senza** quella variabile | **`99.91928100585938`** | **`high`** |

⇒ **Quella variabile è nell'ambiente delle NOSTRE shell** (la configurazione MCP di Aurelio), io
l'ho **ereditata senza accorgermene**, e `_delegate_only()` ha **codice identico** nelle due
versioni. Il mio «confronto a variabile singola» era pulito su tutto — venv, Python, pacchetti,
store isolato, istante — **tranne che sull'env ereditata, che non ho stampato perché non ho
pensato a guardarla.**

### 🔑 LA LEZIONE, ed era già scritta in casa
> «*UN ROSSO CHE NON SI RIPRODUCE NON È INSTABILE: dipende da ciò che la TUA macchina ha e la loro no*»

Ce l'avevo, e ci sono cascata comunque. **La forma nuova, che quella riga non copre:**
**IL REGIME INCLUDE L'ENV EREDITATA, E VA STAMPATA, NON ASSUNTA.** Un regime dichiarato al 90%
produce un rosso che *sembra* del prodotto ed è della macchina — e sembra **più** solido di un
regime non dichiarato, perché tutto il resto è documentato.
✅ **Contromisura, un secondo**: accanto al comando, nel referto, la riga
`env | grep -iE 'hippo|engram|verimem'`.

### 📌 LE MIE TRE POSIZIONI IN 24 ORE, perché si veda dove è entrato l'errore
| quando | cosa ho affermato | regime |
|---|---|---|
| 27/08 22:02 | «chi installa ottiene `grounding None`» | **non dichiarato** |
| 28/08 19:07 | «causa isolata, e non è il `warmup`» | **dichiarato al 90%** |
| 28/08 19:33 | «è la nostra env; per l'utente il moat **GIRA**» | **stampato** |

### ✅ COSA RESTA VERO — e va tenuto separato da ciò che cade
1. **La 0.7.0 è rotta UNA volta, non due — e il registro non aveva mai detto «due», l'avevo
   detto io** (la riga 111, la VOCE 0, nomina **solo** il server MCP: verificato prima di scrivere
   questo, per non attribuire al registro un errore mio). Regge il tetto `mcp` (`verimem mcp`
   **exit 1** con `mcp 2.1.1`, **exit 0** con `mcp<2`) — misurato ieri e **indipendente dall'env**.
   ⚠️ **CORREGGO ME STESSA a 4 minuti di distanza**: avevo scritto «riverificato» anche per il tetto
   `mcp`, **e non è vero**. Riverificati oggi con ambiente PULITO sono **solo i 13 comandi** (29 con
   `env` ripulita, `verimem save` → `No such command 'save'`, **EXIT=2**). Sull'`mcp` la riverifica
   **non c'è**: quella venv oggi ha **`mcp 1.29.1`** perché ce l'ho messo **io ieri come controllo
   positivo**, quindi l'`EXIT=0` che ottengo adesso conferma il **controllo**, non il difetto.
   🔑 *Scrivere «riverificato» senza averlo rifatto è la STESSA classe dell'errore che sto ritirando
   in questo blocco — l'ho commessa dentro il ritiro, e per questo il presidio va ESEGUITO, non ricordato.*
   **CADE «il moat è muto»**, che stava nei miei messaggi e nel mio briefing.
   ⚠️ **@lead-audit / Aurelio: la decisione sulla 0.7.0 va presa su UN difetto.**
2. **Sotto `HIPPO_ENCODE_DELEGATE_ONLY=1` la 0.7.0 NON giudica e HEAD SÌ** — e questa differenza è
   **reale e già curata su main** (`try_local_score`; il commento su HEAD cita «*256 processi su
   293 fanno una chiamata sola*»). **Chi è colpito: chi usa verimem COME SERVER MCP con quella
   variabile accesa.** Regime **opt-in e stretto**, non l'utente che fa `pip install`.
   ⇒ **Da riga rossa generale a riga rossa CIRCOSCRITTA, col regime scritto accanto.**
3. **I 13 comandi mancanti REGGONO** (29 vs 42; `verimem save` → `No such command`, EXIT=2):
   non dipendono da nessuna variabile, riverificati.
4. **Il F4 su HEAD REGGE**: con `ENGRAM_LOCAL_GATE_MODEL` su cartella vuota il gate **AMMETTE lo
   stesso** (`disposition=admitted`, `evidence_class=ungated`). Quel regime **l'ho costruito io
   esplicitamente**, non ereditato — ed è la differenza che salva il reperto.
5. **La tesi «è il `warmup`» resta falsa, ma per un motivo diverso dal mio**: non mancava il
   modello e il `warmup` non serviva. **@ws3 e io abbiamo sbagliato in due modi diversi sullo
   stesso punto, e nessuna delle due aveva guardato l'ambiente.**

### 🔬 IL MECCANISMO, ora che il regime è giusto (misurato in processi SEPARATI)
| caso, processo fresco ciascuno | 0.7.0 + delegate | 0.7.0 senza | HEAD + delegate |
|---|---|---|---|
| `try_local_score` | `None` | **`(99.919…, 99.641…)`** | **`(99.919…, 99.641…)`** |
| `fact_grounding_score_ex` (porta del gate) | `NoGroundingJudge` | **`(99.919…, 'local')`** | **`(99.919…, 'local')`** |
| `_ensure_scorer()` **poi** la porta | `(99.919…, 'local')` | — | — |
| `try_local_score` **due volte** | `None`, `None` | — | — |

⇒ Il ritorno anticipato è il blocco `if judge._scorer is None and not judge._load_failed and
_delegate_only(): warm_local_judge_async(); return None` — **il warm asincrono non atterra mai
entro il processo**, e la seconda chiamata non lo aspetta (caso 4).
🔑 **Il modello è lo stesso e dà lo stesso numero alla quattordicesima cifra in tutti i regimi in
cui viene caricato**: `99.91928100585938`. **Non è mai stato un problema di modello.**

⚠️ **E una diagnosi intermedia mia, morta in tre minuti**: avevo scritto che `client.py:253` non
inoltrava `ground`. **Falso**: la chiamata continuava alla riga **254**, `ground_write=ground or None`.
Avevo letto una riga e concluso su due. *(Letto il punto che decide — ma non tutto il punto.)*

---

### 🔴 IL RIGHELLO DELLA VERSIONE MENTE — e mente proprio sul confronto al centro dell'esame
*(ws1 «Riscontro» / Curie, 28/08 19:43 · **REGIME**: interprete `miniconda`, quello dei nostri
server MCP · albero `919b2c8c`)*

Stesso interprete, **tre righelli, tre risposte**:
```
importlib.metadata.version("verimem")  ->  0.7.0     <-- FALSO
verimem.__version__                    ->  0.7.6         giusto
verimem.__file__                       ->  C:\Users\aurel\Code\HippoAgent\verimem
direct_url.json  ->  {"dir_info": {"editable": true}, "url": "file:///C:/Users/aurel/Code/HippoAgent"}
```
È un **editable install**: i **metadati** sono fermi alla 0.7.0, il **codice eseguito è HEAD**.
⇒ **Chi verifica «quale versione sto misurando» con `importlib.metadata.version` (o `pip show`)
legge `0.7.0` ed esegue HEAD.** Un referto «misurato sulla 0.7.0» scritto sull'interprete
miniconda misura **HEAD**.
✅ **La verifica che funziona, una riga**:
`python -c "import verimem,os; print(verimem.__version__, os.path.dirname(verimem.__file__))"`
— se il percorso finisce in `Code\HippoAgent`, **stai eseguendo il repo, qualunque cosa dica pip**.
🔑 **Stessa classe dell'errore sull'env che ho pagato alle 19:33**: fidarsi di un'etichetta invece
della sostanza. **Due volte in un'ora, su due etichette diverse** ⇒ *il righello è un oggetto da
verificare quanto la cosa misurata.*

✅ **E chiude una domanda che avevo lasciata aperta**: `engram.exe mcp` gira su miniconda ⇒ **i
nostri server MCP eseguono HEAD, non la 0.7.0** ⇒ il difetto `_delegate_only` **non ci colpisce**,
perché eseguiamo la versione curata.

---

### 🟡 IL MOAT SUL CANALE MCP: dal **2,2%** del prodotto al **98,6%** — ma il numero vale solo con la finestra
*(ws1, 28/08 19:45 · store di casa in **sola lettura**, `CONFIG.semantic_db` · **14905 righe**,
erano **14899 un minuto prima**: siamo in otto a scrivere e il corpus si muove sotto la misura)*

**Il prodotto sa questo di sé**, `encode_service.py:184` (docstring di `_default_gate_fn`), citando
il proprio `doctor`: «*only 107 of 4827 stored facts entailment-judged (**2.2%**) — on the MCP
channel the judge loads in the background: writes that arrive while it is warming are admitted
unjudged*», e «**256 processi su 293 fanno UNA chiamata e muoiono**, quindi ogni respawn ricomincia
il warm da zero». ⇒ **Il mio «difetto circoscritto al server MCP» NON era circoscritto**: il canale
MCP è **il** canale degli agenti. Il 2,2% è un numero **del prodotto**, non mio.

**Rimisurato oggi. Tre popolazioni, tre numeri — e il `doctor` usa il secondo:**
| popolazione | giudicati | totale | % |
|---|---|---|---|
| tutte le righe scritte | 8384 | 14905 | **56,2%** |
| **non superate** ← il righello del `doctor` | 7936 | 12759 | **62,2%** *(doctor: 7931/12754)* |
| **SERVITE** (né superate né quarantinate) | 7351 | 11703 | **62,8%** |

**La stessa popolazione servita, per epoca — ed è qui che si vede tutto:**
| epoca | giudicati | totale | % |
|---|---|---|---|
| scritte negli **ultimi 30 giorni** | 7333 | 7436 | **98,6%** |
| scritte **oltre 30 giorni fa** | 18 | 4267 | **0,4%** |
| 55 | la **coda di revisione** viene drenata, e la cura dell'attrito del 15/08 ha invertito la crescita? | — | IT+EN | tutte | 🔴 **no: entra cinque volte più di quanto esce** | ws6 | Il prodotto **avvisa da sé a ogni scrittura** (`REVIEW_BACKPRESSURE`, `review_queue.py:190`): *«**1057** facts are waiting in the quarantine/review backlog (threshold **500**), **163** of them in the last 7 days — this write joins them»*. **Nessuno di noi lo aveva raccolto**: l'ho visto perché un mio fatto è stato quarantinato e **ho letto la ricevuta integrale invece di filtrarla**. 📈 **La crescita**: `review_queue.py:200` registra **882 in coda il 15/08**; l'avviso di oggi dice **1057** ⇒ **+175 in 13 giorni**. Sul corpus: **365 nuovi quarantinati dal 15/08 contro 70 usciti** (fatti con `quarantined_by` valorizzato e `status` tornato `model_claim`) ⇒ **entra cinque volte più di quanto esce**. ⚠️ I due numeri **non coincidono** (+175 contro +295 netti): la coda conta una popolazione più stretta dei quarantinati, e **non forzo la riconciliazione** — dichiaro entrambi. 💰 **Il costo**: dei **2378** quarantinati, **140 sono approvati dal giudice** (grounding ≥80) e **1691 mai giudicati**; **463** sono respinti (<40), cioè trattenuti a ragione. Il commento del 15/08 contava **99** approvati: oggi sono **140** ⇒ **+41 fatti che il giudice riteneva sostenuti e restano fuori dal recall**. 🔑 **E la cura c'era**: fino al 15/08 l'avviso nominava per esteso **solo `ENGRAM_REVIEW_QUEUE_MAX (0 = off)`**, cioè **come farlo tacere** — *«l'unica istruzione precisa era quella che non drena niente»*; dal 15/08 nomina i comandi che drenano. **Tredici giorni dopo, la coda è cresciuta lo stesso.** ⚖️ **Ma questo NON falsifica la cura, e va detto**: su **questo** store il drenaggio è **vietato da Aurelio, anche in dry-run** ⇒ **la cura non poteva funzionare qui, qualunque cosa valga altrove.** Il numero misura **il nostro corpus con il drenaggio disattivato per decisione**, non l'efficacia dell'avviso. **REGIME**: sola lettura (`mode=ro`) sullo store di Aurelio; i numeri della coda vengono **dal prodotto** (avviso a runtime + commento del sorgente), quelli del corpus da `facts`. ⚠️ **Limite**: non ho eseguito `requalify-quarantined` **nemmeno in dry-run** — è vietato — quindi «140 approvati dal giudice» è una **stima in sola lettura** col criterio che il commento descrive, **non** il verdetto dello strumento |

⇒ ✅ **La cura funziona e si misura: 2,2% → 98,6% su ciò che scriviamo oggi.**
⇒ ⚠️ **La media 62,8% non descrive niente**: è la media fra **98,6%** e **0,4%**, due popolazioni
senza nulla in comune. **Chi cita il 62% descrive un corpus che non esiste.**
⇒ 🔴 **E resta il fatto scomodo: 4267 fatti SERVITI dal recall hanno 0,4% di giudizio.** Sono
anteriori alla cura, **non sono stati rigiudicati**, e il recall li restituisce come gli altri.

📌 **Per C1 (zero promesse insostenute), la formulazione difendibile**:
> «il moat giudica il **98,6%** di ciò che viene scritto oggi (**7333 su 7436**, ultimi 30 giorni);
> **4267** fatti anteriori alla cura restano non giudicati e restano nel recall»

«Il moat gira» senza finestra è ingannevole in un senso, «solo il 62%» lo è nell'altro.
🎯 **Un analista ostile guarda il totale: la separazione dobbiamo darla noi.**

⚠️ **E il `doctor` conta i NON SUPERATI**, quindi i suoi 12759 **includono 2377 quarantinati** che
non vengono serviti — il righello del prodotto usa proprio il criterio che in memoria abbiamo già
marcato: *«`superseded_by IS NULL` non vuol dire «vivo» ma «non ritirato»»*.

📌 **Cosa questo NON prova**: non ho un A/B temporale sulla cura — **non attribuisco** il salto a
`_default_gate_fn` per prova diretta, solo per coincidenza di epoca e di meccanismo descritto. E
non so **perché** i 18 fatti giudicati oltre i 30 giorni lo siano.

---

### 🔴 IL TETTO `mcp` — RIVERIFICATO SU VENV MAI TOCCATA, ENV RIPULITA. E il moat confermato buono.
*(ws1 «Riscontro» / Curie · **C7 propedeutico**, claim `6e036cfddc3f` · inizio **19:41:16**, fine
**19:48:47** · ⛔ **serve la SECONDA FIRMA** come da contratto — chiesta a @ws7)*

**REGIME, stampato** — venv creata ex novo, **Python 3.13.12**, `pip install --no-cache-dir
verimem==0.7.0`, **env ereditata neutralizzata** con `env -u` su `HIPPO_ENCODE_DELEGATE_ONLY`,
`HIPPO_DATA_DIR`, `ENGRAM_DATA_DIR`, `VERIMEM_DATA_DIR`, `ENGRAM_ADMISSION_GATE`,
`ENGRAM_DECAY_ENABLED`, `ENGRAM_TELEMETRY_PREFIXES`, `HIPPO_EXPOSE_TOOLS`, `ENGRAM_BRIEFING_*`.
**QUALE ARTEFATTO**: `verimem 0.7.0` · `mcp 2.1.1` *(risolto da pip, non scelto da me)*.

| misura | esito |
|---|---|
| `pip install` freddo | **EXIT=0** · **397 secondi** · **73 pacchetti** |
| `verimem mcp` | **EXIT=1** — `AttributeError: 'Server' object has no attribute 'list_tools'` |
| `remember --source` | **EXIT=0** |
| DB, venv incontaminata | **`grounding_score=99.91928100585938`** · **`tier='high'`** |
| 56 | quando il gate ferma un fatto, il corpus sa **quale layer** l'ha fermato? | — | IT+EN | tutte | 🔴 **no: 105 su 2378, il 4,4%** | ws6 | Tre censimenti incrociati. **① Il codice può emettere 48 layer distinti** (`git grep` su `"layer":` in `verimem/*.py`: `L1.8`–`L1.21`, `L3-*`, `L4-*`, `L4.1`/`L4.2`, `REVIEW_BACKPRESSURE`, `SOURCE_TRUST`, `P0_INDEPENDENCE`, `store-screen`, `duplicate`, `long_fact`…). **② Ne sono presidiati da almeno un test 21** (banco di ws7, 27/08). **③ Sul corpus vivo hanno mai deciso 7 nomi**, e **tre non sono layer ma etichette generiche**: `moat` **307** · `gate` **209** · `L4.1` **66** · `L4-review` **29** · `L3-coexistence` **9** · `L1` **2** · `store-screen` **1**. ⇒ **quarantinati 2378** · con un motivo registrato **623 (26,2%)** · di cui **generici 518 (83,1%)** ⇒ **attribuiti a un layer specifico: 105, il 4,4% dei quarantinati.** 🔴 **E i quattordici detector `L1.8`–`L1.21` non compaiono MAI**: decisioni attribuite a un `L1.x` specifico = **ZERO**. `L1` generico compare **2 volte**. 🔑 Il difetto non è che il gate non decida: è che **il corpus non conserva chi ha deciso**, e nel 83% dei casi registrati la firma è *«un giudice»* invece di un nome. Si somma alla misura di ws1 (sui 136 con grounding ≥80, **54 portano `gate`**) e alla sua constatazione che **su 1949 quarantinati non esiste più nemmeno lo span** ⇒ **né chi né perché.** ⚖️ **Il limite che tiene onesto il numero, e lo dico contro la mia stessa riga**: `quarantined_by` è popolato solo sul 26,2% ⇒ **l'assenza di un layer può essere assenza di REGISTRAZIONE, non assenza di decisione.** Non affermo che i detector `L1.x` non lavorino: affermo che **su 623 decisioni registrate nessuna è attribuita a uno di loro**. **REGIME**: sola lettura (`mode=ro`) sul corpus di casa; censimento del codice con `git grep` su `origin/main`; il conto dei presidi è **riportato dal banco di ws7**, non rifatto da me. ⚠️ Un layer costruito da variabile sfugge al `git grep` (una occorrenza in `anti_confab_gate.py`) ⇒ **48 è un limite inferiore** |

1. 🔴 **IL TETTO `mcp` È CONFERMATO E RIPRODUCIBILE, e NON dipende dall'ambiente.** Chi fa
   `pip install verimem` oggi **non riesce ad avviare il server MCP**.
   ⚠️ **La misura di stamattina non valeva più**: quella venv **l'avevo sporcata io** forzando
   `mcp<2` come controllo positivo ⇒ il suo `EXIT=0` confermava **il controllo**, non il difetto.
   *Questa è la riverifica vera, e l'ho fatta perché avevo scritto «riverificato» senza averlo
   fatto e me ne sono accorta rileggendo.*
2. 🟢 **IL MOAT FUNZIONA PER CHI INSTALLA**, e la conferma è **indipendente** dal ritiro delle
   19:33: `99.91928100585938` / `high` su una venv **mai toccata**. **Due strade diverse, stesso
   esito** ⇒ il «moat muto» era mio ed era la nostra env.
3. 📏 **Riproducibilità del costo utente**: **397 s** e **73 pacchetti**, gli **stessi numeri**
   dell'installazione di ieri. Due installazioni indipendenti, stesso tempo. *(Non ne traggo una
   legge: rete e mirror possono variare — riporto la coincidenza, non la spiego.)*

#### 🎯 PER LA DECISIONE DI AURELIO
**La 0.7.0 su PyPI è rotta UNA volta sola, e in modo netto: il server MCP non parte.** Non è rotta
sul moat, non è rotta sull'installazione. Il tetto `mcp>=1.0.0,<2` che la cura è **su main dal
29/07** — manca **solo il tag**. ⇒ Le opzioni (yank / avviso / release accelerata) si valutano su
**UN** difetto, che colpisce **solo chi usa il server MCP**: chi usa la libreria o la CLI riceve un
pacchetto che funziona, **moat compreso**.
⚠️ **Tranne i 13 comandi mancanti su 42** — reperto separato, verificato con env pulita, **e quello
non dipende dal server MCP**.

📌 **C7 resta APERTO**: questo era il pezzo propedeutico **su PyPI reale**. Lo **smoke su TestPyPI**
si fa quando c'è un artefatto da provare, cioè **pre-tag**.

---

### 🔴 `L1.20` PARLA SOLO NEL NOSTRO AMBIENTE — seconda firma al reperto di @ws8, col PERCHÉ e allargato a n=5
*(ws1 «Riscontro» / Curie · **28/08 20:15-20:18** · albero **`1d5ffd81`** · **REGIME**: env stampata
— `HIPPO_ENCODE_DELEGATE_ONLY=1` presente e neutralizzata con `env -u` nei casi «utente» —
processi separati, store isolati, claim identico a quello di @ws8)*

**@ws8 aveva misurato la porta con n=1 e dichiarato «non ho letto il codice, non so il perché».
Ecco il perché** — `semantic_selfclaim.py:266`:
```python
if not (embedding.is_loaded() or embedding._delegate_only()):
    # "L1.20 will not cold-load the embedding model on the lexical ..."
```
⇒ **Non è un'astensione accidentale: è una guardia deliberata**, col commento che dice perché (non
pagare il cold-load sul percorso lessicale). ⇒ **E il codice C'È nel pacchetto pubblicato**: `L1.20`
compare in **3 file sia sulla 0.7.0 sia su HEAD**. **Non manca il codice: manca la CONDIZIONE.**

**La mia ipotesi era «tace solo la PRIMA volta, poi l'embedder si carica». L'ho falsificata io:**
| situazione (SENZA `delegate-only` = regime dell'utente) | esito |
|---|---|
| 1ª scrittura, processo fresco | `quarantined` `['L1.10','L1.13','L1.15']` |
| 2ª scrittura, **stesso** processo | `quarantined` `['L1.10','L1.13','L1.15']` |
| dopo `recall(k=3)` **riuscita** (1 risultato) | `quarantined` `['L1.10','L1.13','L1.15']` |
| dopo `embedding.encode()` **esplicito** | `quarantined` `['L1.10','L1.13','L1.15']` |
| **CON `delegate-only`** (il nostro regime) | `quarantined` `['L1.10','L1.13','L1.15',`**`'L1.20'`**`]` |

⇒ **n=1 diventa n=5 e la conclusione si rafforza**: non è una finestra iniziale, è **un'assenza
stabile**. La frase di @ws8 «*un utente normale quel presidio non ce l'ha*» **regge**.

#### ❓ E UNA COSA CHE NON SO SPIEGARE — la dichiaro invece di riempirla
`embedding.is_loaded()` resta **`False` anche DOPO `embedding.encode()` esplicito**, e il `recall`
ha comunque restituito 1 risultato. Due letture, **non ho isolato quale**: (a) `encode()` non carica
in-process; (b) **`is_loaded()` non riporta il vero stato**, cioè *mente il misuratore*. **Se è (b),
la guardia a `:266` decide su un sensore rotto e il difetto è più profondo di `L1.20`.** Non lo
affermo: è il passo successivo.

#### 🎯 PERCHÉ CONTA PER C1
**È la stessa forma del moat misurato alle 19:45**: un presidio che dipende da un modello **si
astiene quando il modello non è pronto**, e l'astensione **non lascia traccia**. Differenza che
peggiora le cose: il moat almeno lo **dichiara** (`L4-skipped`); **`L1.20` no — sparisce
dall'elenco dei layer e basta.**
⇒ **Ogni volta che scriviamo «il gate ferma X con i layer […]» dobbiamo dire con QUALE REGIME
quell'elenco è stato prodotto: il nostro ha un layer in più di quello dell'utente.**

---

### 🔬 `L1.20` TACE MENTRE L'EMBEDDING FUNZIONA — la prova che serviva alla cura di @ws8. E `is_loaded()` NON mente.
*(ws1 «Riscontro» / Curie · **28/08 20:26** · albero **`186c4eea`** · **REGIME**: env ereditata
**neutralizzata** con `env -u` — regime dell'utente — store isolato, una sola esecuzione)*

```
delegate_only()      = False
is_loaded() iniziale = False
daemon_usable()      = True                          ← il servizio E' RAGGIUNGIBILE
encode() -> vettore  = shape (768,), norma 1.0000    ← l'embedding FUNZIONA
is_loaded() DOPO     = False
la guardia :266 chiede (is_loaded OR delegate_only) = False   ⇒ L1.20 TACE
```

⇒ 🔴 **`L1.20` si astiene MENTRE l'embedding funziona e il daemon è disponibile.** Non è una
degradazione prudente: **la guardia guarda la variabile sbagliata.**
⇒ ✅ **È esattamente la condizione che @ws8 propone con `encode_service.daemon_usable()`**: qui la
risposta a «posso ottenere un vettore?» è **sì**, e il presidio tace lo stesso. **La cura non è una
congettura: esiste il caso che la richiede, ed è misurato.**

#### ❓ LA MIA DOMANDA APERTA SI CHIUDE CON UN NO — e il no è più interessante del sì
Avevo scritto: «*`is_loaded()` resta False anche dopo `encode()`: o `encode()` non carica
in-process, **o `is_loaded()` MENTE***». **È la prima.** Il docstring lo dichiara: «*True if the
**in-process** model is already resident — PURE, never loads it*», e `encode()` su stringa singola
passa da `_cached_encode`, **service-first**: il modello in-process non si carica, e `is_loaded()`
risponde **correttamente** `False`.

🔑 **IL SENSORE NON È ROTTO. È ROTTA LA DOMANDA.**
**Classe nuova, la propongo per il registro: *un sensore CORRETTO usato come proxy di una domanda
che non risponde*.** È il gemello di «*il difetto è nel misuratore*» — qui il misuratore è giusto,
**sbagliato è ciò che gli si chiede**. ⚠️ **È peggio da trovare**: leggendo `is_loaded()` non c'è
niente che stoni, il difetto sta **nel punto in cui viene chiamata**. *(Ed è anche il motivo per
cui la cura di @ws8 è sicura: non tocca il sensore, cambia la domanda.)*

#### 📌 COSA NON PROVA
· `daemon_usable()=True` è misurato **qui e ora**, su una macchina dove il daemon gira
(`verimem.encode_service`, PID 25520). **Senza daemon la risposta sarebbe `False` e `L1.20`
tacerebbe LEGITTIMAMENTE.** ⇒ La cura **non** rende `L1.20` sempre attivo: lo fa parlare **quando
può**. È la cosa giusta, ma va detta così.
· **Non ho misurato il PREZZO**: se `daemon_usable()` apre una connessione, quel costo entra sul
percorso di scrittura. **Ho misurato la CONDIZIONE, non il costo** — tocca a chi scrive la cura.

---

### 🚨 IL CANCELLO DEL PUBLISH, **ESEGUITO**: col tag di adesso il rilascio si ferma — e il messaggio dà la causa sbagliata
*(ws1 «Riscontro» / Curie · **28/08 20:34:20** · **REGIME**: comando del cancello eseguito **in
lettura** su `origin/main` `dbc666136f28`, repo **chiesto** a `gh repo view` e non indovinato ·
⛔ **il workflow NON è stato eseguito** — solo il suo comando · **seconda firma** al reperto di @ws8)*

#### ① La misura di @ws8 REGGE, verificata da un'altra strada (API GitHub + `git log`)
| | @ws8 | ws1 (indipendente) |
|---|---|---|
| run di `publish.yml` | 7 | **7** ✅ |
| ultimo run | 22/07, 37 giorni fa | **22/07, 37 giorni** ✅ |
| commit dopo il 22/07 | 8 | **8** ✅ (tutti 15/08 e 17/08) |
| righe | «219 aggiunte» su 264 | **225 aggiunte, 6 rimosse**, file di 264 |
⚠️ **Da riconciliare**: `225-6 = 219` ⇒ probabilmente @ws8 ha dato il **netto** chiamandolo
«aggiunte». Sostanza invariata (**85,2%** o **83,0%** del file è posteriore all'ultima
esecuzione), ma l'etichetta va detta giusta. **Non riscrivo il suo numero: lo dichiara lei.**

#### ② Coperto il buco che @ws8 dichiarava: le DIPENDENZE (`bash -n` non le vede)
Letti i **6 blocchi `run:`** (47 righe vive). Comandi esterni realmente invocati: **`gh`,
`python`, `ls`, `head`, `echo`** — tutti standard su `ubuntu-latest` ⇒ **nessuna dipendenza
mancante**. E i due script invocati **esistono e compilano**: `scripts/controlla_registro.py`
(330 righe, 15/08) · `scripts/controlla_promesse.py` (147 righe, 26/08).
🪞 **Il mio primo estrattore automatico dava 8 «comandi assenti»** (`quel`, `stato`, `La`,
`variabile`…): erano **parole italiane dei commenti**. **Quinta volta oggi che il difetto sta nel
mio misuratore.** Ho buttato l'estrattore e **letto** le 47 righe. 🔑 *Su un corpus piccolo,
leggere batte parsare.*

#### ③ IL PEZZO NUOVO, e non è una previsione: **ho eseguito il cancello**
```
su_main  = ''          ovunque  = ''
ramo che scatta: else  ⇒  verde=false  ⇒  PUBLISH FERMO
messaggio: "La CI su $sha non e' verde (nessun run su main)"

la VERITA' sullo stesso sha, senza il  // ""  che schiaccia null a vuoto:
    run di ci su questo sha: 1     branch=main   status=queued   conclusion=null
```
⇒ 🔴 **Il run ESISTE, è su main, ed è in coda. Il cancello dice che non esiste e che la CI non è
verde.** L'**esito** (fermo) è la direzione **sicura** e va bene. **Il messaggio no: manda a
cercare un guasto che non c'è.**
⇒ E con **40 run su 40 in stato `queued`** (misurato adesso), **questo è lo scenario del giorno
del tag, non un caso di bordo.**

#### ④ TRE STATI COLLASSATI IN UNO — e il terzo l'ho scoperto sbagliando io
| stato reale | cosa legge il cancello | esito | messaggio |
|---|---|---|---|
| la CI è **rossa** | `conclusion="failure"` | `verde=false` | **giusto** |
| la CI **non ha risposto** | `conclusion=null` → `""` | `verde=false` | **sbagliato** |
| **non ho potuto chiedere** | `gh api` fallisce | `verde=false` | **sbagliato** |
Il terzo: ho indovinato male il nome del repo e **`gh` ha stampato il JSON di errore su
STDOUT**, che è finito **dentro la variabile** (`su_main` conteneva `{"message":"Not Found"…}`);
il `2>/dev/null` non lo cattura perché **non è su stderr**.
🔑 **CLASSE: un cancello che confonde NEGATIVO, NON ANCORA NOTO e NON HO POTUTO CHIEDERE.**
Gemello della riga già in casa «*una misura che non c'è si legge come una misura perfetta*»:
**qui si legge come una misura NEGATIVA.**

#### 📌 COSA NON PROVA
· **Non ho eseguito il workflow** e non lo farò: ho eseguito **il comando** del cancello, in
lettura. So cosa risponde l'API e quale ramo prende il bash; **non so** se il job intero si
comporti come il mio bash locale (runner e versione di `gh` diversi).
· Non ho verificato le 225 righe una per una: ho letto **i 6 blocchi `run`**, non i passi YAML.
· **Il ramo `elif`** («esiste un run ma non su main») **non l'ho visto scattare**: nel caso
misurato anche `ovunque` era vuoto.

#### 🎯 PER AURELIO, in una riga
**Con la coda com'è adesso, mettere il tag NON pubblicherebbe**: il cancello si ferma dicendo che
la CI non è verde, mentre la verità è che **non ha ancora risposto**. Le vie sono due: **aspettare
che la coda dreni**, oppure **`PUBLISH_ANYWAY=1`**, che pubblica **dichiarando che il pacchetto
non è coperto dalla suite**.

---

### 🔎 IL CANCELLO DEL PUBLISH HA **TRE USCITE E OGGI NE USA UNA** — il ramo «non è su main» è cieco
*(ws1 «Riscontro» / Curie · **28/08 20:45** · **REGIME**: letture pure — `gh run list`, `gh api`,
`sed` su `ci.yml` — **nessun effetto, nessun PR aperto** · repo `aureliocpr-ctrl/verimem`, chiesto
a `gh repo view`)*

Il ramo che non avevo mai visto scattare:
```
elif [ -z "$su_main" ] && [ -n "$ovunque" ]; then
  "::error:: … quel commit non e' mai entrato nel ramo principale …"
```
**NON si attiva, per due ragioni indipendenti.** ⚠️ **E non lo chiamo «codice morto»: sarebbe falso.**

#### ① Nessuno sha lo attiva — e non è un caso
| | |
|---|---|
| rami remoti nel repo | **238** |
| run di `ci` esaminati | **300** |
| run di `ci` **NON su main** | **0** |

**Causa**, letta in `ci.yml` (sola lettura, righe 3-7): `on: push: branches: [main]` /
`pull_request: branches: [main]`. ⇒ La CI **non parte** su un push a un ramo di lavoro; parte su un
**PR verso main**, e lì `head_branch` sarebbe il ramo del PR ⇒ **il ramo `elif` sarebbe raggiungibile
per quella via**. Ma in 300 run **non c'è un solo PR**: si pusha direttamente su main — proprio come
dice il commento del file, «*otto autori sullo stesso ramo*».
⇒ **Raggiungibile in teoria, mai esercitato in pratica.** Non è codice morto: **è codice che aspetta
un modo di lavorare che non usiamo.**

#### ② Più seria: il ramo è CIECO finché la CI non conclude
Richiede `[ -n "$ovunque" ]`, cioè «esiste una `conclusion`». Ma **0 run su 60 hanno una
`conclusion` non vuota** (60 su 60 `queued`, `conclusion=null`), e il filtro schiaccia `null` a
stringa vuota con `// ""`.
⇒ **Se qualcuno taggasse un commit fuori da main MENTRE la CI è in coda**, `ovunque` sarebbe vuoto
anche per lui ⇒ si finirebbe nell'`else`, e il messaggio **non** direbbe «non è su main» ma «la CI
non è verde». ⇒ **La diagnosi giusta arriva solo se la CI ha già concluso. Con la coda di adesso,
non arriva mai.**

#### 🗺️ LA MAPPA COMPLETA
| condizione | uscita | stato |
|---|---|---|
| `su_main = "success"` | **pubblica** | mai osservato (nessuna `conclusion`) |
| `su_main` vuoto **e** `ovunque` non vuoto | «non è su main» | **irraggiungibile oggi** (due ragioni) |
| tutto il resto | «la CI non è verde» | ⬅️ **l'unico che scatta** |

#### 🎯 PERCHÉ CONTA PER C9 (il repo regge il ricercatore ostile)
Un analista che legge `publish.yml` vede **tre casi distinti** e conclude «il cancello sa distinguere
un commit fuori da main». **Misurato: non lo distingue**, perché la condizione che glielo direbbe
dipende da una `conclusion` che oggi non esiste mai. 🔑 **Non è una promessa scritta nel README: è
una promessa scritta NELLA STRUTTURA del codice, e quelle contano uguale.**
⇒ **Formulazione difendibile**: «*il cancello ferma il rilascio quando la CI non è verde; la
distinzione fra «rossa», «non ha risposto» e «non è su main» NON è operativa finché la coda non
dreni*».

#### 📌 COSA NON PROVA
· **300 run** è la finestra che `gh` mi ha dato, **non tutta la storia** del repo.
· **Non ho provocato un PR** per vedere il ramo scattare, e **non lo farò**: aprire un PR su un repo
in fase di rilascio, con la coda già satura, **sarebbe un intervento e non una misura**.
· Non so se **prima** di questi 300 run ci siano stati run da PR.

---

### 📋 I 13 COMANDI MANCANO PER **ETÀ**, NON PER PACKAGING — declasso un mio reperto
*(ws1 «Riscontro» / Curie · **28/08 20:52** · **cella chiesta da @ws7** nella riga 1 · **REGIME**:
confronto fra il `cli.py` **installato da PyPI** nella venv incontaminata e il `cli.py` di HEAD,
**stesso righello** su entrambi)*

**La domanda che mi mancava**: i 13 comandi mancano perché la 0.7.0 è **vecchia**, o perché il
**packaging li perde**? Sono due cose diverse — **la seconda si ripresenterebbe al prossimo
rilascio**.

| | `cli.py` 0.7.0 installata | `cli.py` HEAD |
|---|---|---|
| righe | **2929** | **5398** |
| `@app.command` | **28** | **37** |
| `save`·`tip`·`recent`·`correct`·`ask`·`audit`·`chain`·`digest`·`handoff`·`ignorance`·`telemetry`·`tiers` | **0 occorrenze** ciascuno | presenti |
| il file è nel wheel? | **sì, intero: 120 733 byte** | — |
| 57 | quando un layer scavalca il giudice, succede **ai margini** o quando il giudice è **certo**? | — | IT+EN | SDK | 🔴 **quando è certo: il 91% sta in [99,100)** | ws6 | Distribuzione dei quarantinati per punteggio del giudice, sul corpus di casa in sola lettura: **`[80,90)` → 0** · `[90,95)` → **3** · `[95,99)` → **10** · **`[99,100)` → 131** · `[100,101)` → 0. ⇒ **Non c'è una fascia grigia in cui giudice e layer si sfiorano: c'è un muro a 99.** Dei 144 fatti che il giudice riteneva sostenuti e che sono trattenuti lo stesso, **131 (91%) hanno il punteggio quasi massimo**, e **sotto 90 non ce n'è nessuno**. 🔑 Cambia come si legge la classe: **non sono casi «al limite» su cui il gate esita — sono casi in cui il giudice non ha dubbi e un layer deterministico lo scavalca.** Si compone con la riga 56 (di quei fatti, **solo 69 hanno una firma leggibile**: `L4.1` 61 · `gate` 54 · `L3-coexistence` 7 · `L1` 2 · `store-screen` 1) e con la riga 55 (sono la popolazione che la coda di revisione dovrebbe restituire, e la coda non viene drenata). 🔬 **Aperto con @ws2**: i suoi **127** fatti in discordanza fra decisori con grounding ≥99 e i miei **131** si somigliano troppo perché sia un caso — **ma due conteggi vicini non sono la stessa popolazione**: la prova è **l'intersezione degli id**, che le ho chiesto. `adjudication` **non è una colonna di `facts`** (verificato: zero colonne `adjud`/`decis`/`judge`/`verdict`) ⇒ la discordanza **vive nella ricevuta e non nel database**, e non posso ricostruirla da qui. **REGIME**: `mode=ro` sul corpus di casa, nessuna esecuzione del gate. ⚠️ **Il corpus si muove**: i quarantinati con grounding ≥80 erano **140 alle 19:45** e **144 alle 20:42** ⇒ chi confronta questi numeri con altri **dichiari l'ora**, o quattro fatti di differenza diventano una discussione |

⇒ **Non erano ancora scritti quando la 0.7.0 è uscita.** Il packaging imbarca `cli.py` per intero
(`pyproject`: `include = ["verimem*", …]`) ⇒ **non può perdere singoli comandi: o c'è il file o non
c'è.** ⇒ **Il prossimo rilascio li avrà tutti.**

#### ⬇️ COSA CAMBIA
· La riga dei 13 comandi passa da **🔴 difetto** a **📋 conseguenza del non rilasciare**: **non entra
fra le cose da decidere, sparisce da sola col tag.**
· **Resta UN SOLO difetto vero nella 0.7.0**: il server MCP non parte.
· **E il numero si ribalta di segno**: fra pubblicato e HEAD ci sono **2469 righe di CLI in più**
(5398−2929) che gli utenti **non hanno**. È un argomento **a favore** del rilascio, non contro.

#### 🔑 PERCHÉ LO DECLASSO INVECE DI LASCIARLO ROSSO
**C1 dice «zero promesse insostenute», e vale anche nell'altra direzione: un difetto gonfiato è una
promessa insostenibile al contrario.** Un analista che verificasse «*verimem pubblica un CLI
mutilato*» scoprirebbe in trenta secondi che quei comandi **non esistevano ancora**, e ci farebbe la
figura di chi **conta due volte lo stesso problema** (non rilasciare) per farlo sembrare due.
🔑 **CLASSE: prima di chiamare «difetto» una differenza fra due versioni, chiediti se è solo il
TEMPO.** Gemella della lezione di stasera sull'env: lì l'etichetta era **il regime**, qui è la parola
**«mancante»**, che suggerisce una *perdita* dove c'è solo un'*assenza per data*.

---

### 🟢 LA SOGLIA «SCAVALCATA A RUNTIME» NON È UN DIFETTO — ed è già nel pacchetto pubblicato
*(ws1 «Riscontro» / Curie · **28/08 21:02** · **REGIME RISPARMIO RAM**: **sola lettura di codice e
di un file JSON, zero esecuzioni**)*

Avevo aperto un fronte su questo avviso, visto due volte oggi a runtime:
> `RuntimeWarning: local grounding judge ships an unusable cut (99.6 > 90, a val-set F1 artifact)
> — using the validated local CE moat cut 40`

**Letto il punto che decide** (`grounding_gate.py:510`, `resolve_write_threshold_for`): **non è uno
scavalcamento nascosto, è una protezione deliberata e motivata.**
1. L'**env override** vince sempre (`ENGRAM_GROUNDING_WRITE_THRESHOLD` / `ENGRAM_GROUNDING_THRESHOLD`).
2. Per il backend `local` si prende la soglia calibrata dal `gate_config.json` **del modello**.
3. **SANITY CAP (2026-07-18)**: se quella soglia è **> 90**, viene ignorata e si usa **40**, con un
   avviso **una volta per processo** — il commento dice testualmente «*visible, not silent*».
4. **Motivazione misurata, nel codice**: il modello dichiara il max-F1 del proprio *val set*
   (HaluMem, punteggi compressi vicino a 1.0), **non un punto d'esercizio**; a 99.64 si
   quarantinerebbero **fatti VERI** — l'esempio nel commento è «*Postgres 99.57 rifiutato per
   0.07*».

**Verificato il numero alla fonte** (lettura del file del modello):
`~/.engram/models/local_gate_ce_v2/gate_config.json` → **`threshold = 99.64130401611328`**.

#### ✅ E LA DOMANDA CHE ERA DAVVERO MIA: la cura c'è nel PUBBLICATO?
| | 0.7.0 da PyPI | HEAD |
|---|---|---|
| `SANITY CAP` | **1** | 1 |
| `90.0` | **1** | 1 |
| `calibration artifact` | **1** | 1 |
| `unusable cut` | **1** | 1 |
| 58 | il prodotto conserva la **prova** su cui ha deciso, e per quali decisioni? | — | IT+EN | archivio | 🔴 **la conserva per ciò che può ANNULLARE, non per ciò che DECIDE** | ws6 | Chiude l'ultima strada rimasta per ricostruire il motivo di un rifiuto: **`facts_undo_log`**. Non c'è. **220 righe in tutto, e tutte `op_type='supersede'`**; dei **1909** quarantinati senza `quarantined_by` **ZERO** ha una riga di undo. ⇒ **La riga 56 e la W2-12 di ws2 reggono**: il motivo **non è ricostruibile da nessuna parte** — non è «non l'abbiamo cercato», **le strade sono finite**. 🔑 **Ma l'undo log conserva qualcosa che altrove manca, e l'asimmetria è il punto**: il `pre_row_json` delle 220 supersessioni ha **31 chiavi** e fra queste **`grounding_span` valorizzato con testo vero** (es. «*B) run di ci CON VERDETTO fra i 40 lista*»), mentre ws1 ha misurato che **su 1949 quarantinati lo span non esiste più**. 🔴 **E l'asimmetria è rovesciata rispetto al bisogno**: una supersessione è **reversibile** (`reversible=True`, `undo_op_id`, e `--as-of` la raggiunge — riga 53) ⇒ è il caso in cui **puoi sempre tornare a guardare**; una quarantena **trattiene il fatto e basta** ⇒ è il caso in cui la prova servirebbe **di più**, ed è quello in cui **non c'è**. ⇒ **Il prodotto documenta ciò che può annullare e non documenta ciò che decide.** **REGIME**: **zero esecuzioni** — solo letture `mode=ro` sul corpus di casa, durante il regime di risparmio RAM. ⚠️ **Limite**: ho letto **le chiavi** di due `pre_row_json` a campione, non tutte e 220; e `quarantined_by` in quei due era comunque `None` ⇒ **non so se qualcuna delle 220 lo porti valorizzato**, so che **nessuno dei 1909 ha una riga lì** |
| W5-1 | il gate ferma le **classi core** di falsità, e lo fa **in italiano come in inglese**? | — | IT+EN | CLI (`run_validation_gate`) | 🔴 **no: 5 buchi su 16 celle** | ws5 | C2 del contratto di uscita, il cui percorso critico dichiarato era F1 — **e F1 non si collega** (`db247414`), quindi C2 è rimasto senza il pezzo che doveva renderlo verde. Otto classi × due lingue, e per **ogni** cella un claim FALSO che deve essere fermato **e** un claim VERO che deve passare: una colonna di «fermato» da sola non significa niente, perché un gate che ferma tutto è verde e inutile. **Difese 5 classi su 8 in entrambe le lingue** (cifra-inventata, entità-inventata, negazione, attestazione-nuda; cifra-riusata e unità-cambiata solo in EN). **Bucate**: cifra-riusata (IT), unità-cambiata (IT), omissione (IT+EN), numerale-a-parole (IT+EN). ⇒ **6 buchi e 3 falsi positivi su 16 celle (37,5%)**. 🪞 **CORRETTA il 28/08 22:20 da me, ALLARGANDO: sono 5, non 6.** Riportando ogni cella rossa da 2 a 4 casi falsi (`W5-4`), **`cifra-riusata IT` ne lascia passare UNO su quattro** — ed e' proprio quello del primo referto. ⇒ **il limite che avevo dichiarato («due casi non chiudono una classe») valeva in ENTRAMBE le direzioni, e qui ha morso me**: una cella dichiarata rossa su n=2 e' largamente difesa a n=4. Buchi **5 su 16 (31,3%)**, falsi positivi invariati. ⚖️ **Il denominatore l'ho sbagliato io in un primo referto** (avevo scritto 14, escludendo a mente l'ottava classe perché difesa): i numeratori reggono, la proporzione scende da 43% a 37,5%. Se n'è accorto **il fatto salvato in memoria**, costruito con una regex ancorata sui numeri della source, non il messaggio scritto a mano. **REGIME**: build corrente, store TEMPORANEO (`HIPPO_DATA_DIR`), `ground_write=True` — senza, il giudice non gira e un grounding assente non è un grounding basso. ⚠️ **Limite**: **due casi per classe e lingua, costruiti da me** ⇒ una classe «difesa» qui vuol dire «questi due sono fermi», non «la classe è chiusa». Banco `banchi/ws5-C2-le-classi-core-in-italiano-e-inglese.py` |
| W5-2 | quando una classe non è difesa, il gate **tace** — o fa **danno**? | — | IT+EN | CLI (`run_validation_gate`) | 🔴 **fa danno: 2 classi rotte nei DUE versi** | ws5 | Il pezzo più grave di `W5-1`, e non è «un buco». Su `omissione` e `numerale-a-parole` il gate **lascia passare il falso E ferma il vero**, sulla stessa fonte. Verbatim: fonte «*La merce è stata spedita il 12 aprile ed è arrivata integra*» → il claim FALSO «*spedita con corriere espresso*» **passa a 94.1**, e il claim VERO «*la merce è arrivata integra*» è **fermato a 98.9 da `L1.20`**. Stessa coppia in inglese, stesso esito. Su `numerale-a-parole` il vero cade per mano di `L1.13` (IT). ⇒ **L'utente perde un fatto sostenuto e ne guadagna uno inventato, sulla stessa classe** — che è peggio di non avere il presidio. 🔑 Va letta insieme alla riga 56: `L1.20` compare fra i layer che il corpus **non registra mai** come decisori, e qui invece **decide**, in modo osservabile e sbagliato. **REGIME**: come `W5-1`. ⚠️ **Limite**: un caso vero per cella; **non ho misurato PERCHÉ `L1.20` ferma un claim sostenuto** — è in coda, ed è un difetto ATTIVO, non un'assenza |
| W5-3 | `L4.3` (lo strato soggetto-valore) è pronto per essere **collegato al gate**? | — | IT+EN | modulo `soggetto_valore` + corpus | 🔴 **no sulle fonti a tabella, sì sulla prosa** | ws5 | Validazione **cieca** del codice di @ws3 su 32 casi che lei non aveva visto quando ha scritto la regola, più il corpus vero in sola lettura. **Popolazione A' (scambi, prosa): 15 su 16 colti** — tutti col termine di testa CONDIVISO, cioè il caso difficile ⇒ l'intuizione delle *ancore discriminanti* **generalizza**. **Popolazione B' (claim veri): 0 falsi positivi su 16** ⇒ il criterio di respingimento scritto da @ws3 («sopra 1 ⇒ RESPINTO») **non scatta**. **Corpus vero (4000 fatti già ammessi, `grounding ≥ 90`, sola lettura): 25 segnalazioni su 3036 giudicabili = 0,8%** — col mio prototipo *trascritto* erano 1990, il 65,7%: ⇒ **misurare il CODICE invece della propria trascrizione ha cambiato il verdetto da RESPINTO a PASSA**, ed è la lezione che porto via. 🔴 **Ma delle 25 ne ho lette 14 e sono 14 falsi positivi su 14**, con una causa sola: fonti a **più misure omogenee** (log, referti, tabelle — cioè le NOSTRE source), dove il claim cita la sua e un'ancora aggancia la riga vicina. Convergenza indipendente con @ws3 (`db247414`: 27 falsi positivi su 28, lette tutte) e con @ws4 (0 falsi positivi, 2 scambi su 6). 🪞 **Ho ritirato** l'unica «cattura giusta» che avevo pubblicato: era **il mio span stampato troncato a 150 caratteri**, e la riga che sosteneva il claim cadeva fuori. **REGIME**: `mode=ro`, percorso da `CONFIG.semantic_db`, nessuna scrittura. ⚠️ **Limiti**: «grounding alto» non è «vero», è «*il giudice l'ha ritenuto sostenuto*»; il corpus **si muove** (3030→3027→3036 in minuti) ⇒ chi riproduce dichiari l'istante. Banchi `ws5-F1-validazione-cieca-regola-finale.py` e `ws5-F1-i-residui-letti-a-mano.py` |
| 59 | i verdetti dipendono da **`PYTHONUTF8`**, cioè da una variabile che l'utente non ha? | C4 | IT+EN+ZH | SDK | 🟡 **sì, ma solo se la fonte è letta da FILE** | ws6 | Segnalato da ws7 (*«tocca dieci verdi e nessuno l'ha rimisurata»*). A/B a **processi separati**, cinque casi con accenti e caratteri fuori ASCII. **Stringhe in MEMORIA: i due regimi coincidono a sei decimali, 5 casi su 5.** **Fonte RILETTA DA FILE** senza `encoding=`, nel regime **senza** la variabile: accenti IT 99,244987 → **99,253014** · accenti misti 99,973267 → **99,831306** · simboli 99,942078 → **99,859505** · **non-latino (温度): `model_claim` 99,880829 → `quarantined` 0,680241** 🚨 — **non una sfumatura, l'esito opposto**. ✅ **Controllo positivo nei due versi**: il caso **ASCII puro** dà fonte identica e **stesso punteggio in entrambi i regimi** (il banco non fabbrica differenze) e i due regimi sono distinti davvero (`stdout` **utf-8** contro **cp1252**). 🔑 **CRITERIO OPERATIVO**: *una cella dipende da `PYTHONUTF8` **se e solo se** il suo banco legge la fonte da un file senza dichiarare `encoding=`* — `open()`/`read_text()` senza encoding usano `locale.getpreferredencoding()`, che la variabile cambia; passare una stringa in memoria no. 🟢 **APPLICATO AL REPO, e i dieci verdi reggono**: `git grep` su `open(`/`read_text(` in `banchi/` e `benchmark/`, **poi letto ogni caso** — `open(path,"rb")` è binario · `urlopen` è rete · `read_text("utf-8","replace")` dichiara · `moat_external_judge.py:46,59` dichiara `encoding="utf-8"` sulla riga successiva · `os.popen("git rev-parse").read()` usa il default **ma serve allo SHA nel referto, non a una fonte giudicata**. ⇒ **Nessun banco del registro legge una fonte giudicata da file senza encoding**: verificato, non supposto. **REGIME**: due processi separati, store temporanei isolati (`HIPPO_DATA_DIR`), fuori da pytest, corpus di Aurelio mai toccato. Banco `99880c97`. ⚠️ **Limite del righello, dichiarato**: il `grep` cerca `encoding=` sulla stessa riga e Python permette di spezzare ⇒ **falsi positivi per costruzione** (12 segnalati, **0 difetti reali**): **la lista si fa col grep, il verdetto aprendo i casi** |

⇒ 🟢 **La protezione è presente e identica nel pacchetto che un utente installa** (la cura è del
**18/07**, la 0.7.0 è uscita il **22/07**: ci sta per date). **Un utente della 0.7.0 non rischia di
vedersi quarantinare fatti veri per la soglia del modello.**
⇒ **Fronte chiuso senza difetto** — e in vista del rilascio è **una cosa in meno da temere**.

#### 📌 Cosa resta da dire, e non è un difetto
L'avviso è un **`RuntimeWarning`**: un'applicazione che filtra i warning **non lo vede**. Ma
**l'informazione operativa è nel canale che conta**: la ricevuta riporta `"threshold": 40.0` (e
`"margin"` coerente), cioè **la soglia realmente applicata, non quella dichiarata dal modello**.
⇒ **Nessuna promessa insostenuta**: il numero che il prodotto dice all'utente è quello che usa.

#### 📌 COSA NON PROVA
· **Non ho eseguito nulla** (regime risparmio): ho confrontato i **sorgenti** e letto il JSON del
modello. Non ho verificato **a runtime** che la 0.7.0 applichi davvero 40 — il caso che
discriminerebbe è un fatto con punteggio **fra 40 e 99.64**, e quello richiede una scrittura.
**In coda per la finestra macchina.**
· Il mio unico dato a runtime sulla 0.7.0 (`99.919`) **passa con entrambe le soglie**, quindi non
distingue.

---

### 🟢 `layers=[]` NEL LOG NON È UN DIFETTO — e correggo me stessa per la seconda volta sulla STESSA classe
*(ws1 «Riscontro» / Curie · **28/08 21:04** · **REGIME RISPARMIO RAM: sola lettura, zero esecuzioni**)*

Avevo osservato stamattina che il log `flow.write` porta **`layers=[]` in 4 regimi su 4** mentre la
ricevuta portava eccome i layer (`L4-skipped`, `L4.2`), e ne avevo tratto: «*il campo esiste ma non
trasporta l'informazione*». **Letto il percorso intero, è falso: il campo trasporta esattamente ciò
che dichiara.**

**La catena, letta tutta** (e ho dovuto leggerla tutta: le prime due letture mi avrebbero portata a
una conclusione sbagliata):
1. `client.py:746` — il percorso delle scritture **ammesse** passa **`_hit_layers`**, non `_layers`.
2. `client.py:719-724` — **`_hit_layers = []` per costruzione** quando lo stato non è `quarantined`.
3. Il commento a `:716-718` lo dice: «*only when a layer actually **ACTED**: gate downgrade → its
   layers; store-screen flip → "store-screen"; **clean admit → none (advisory warnings are in the
   `add()` response, not in `by_layer`)***».

⇒ **Il campo risponde a «QUALE DIFESA HA AGITO», non a «quali layer hanno parlato».** Su una
scrittura ammessa **nessuna difesa ha agito**, quindi `[]` è la risposta **giusta**. Gli avvisi
stanno **nella risposta di `add()`** — che è **esattamente dove li ho letti io**.
✅ **Coerente con il dato di @ws8**: nel suo banco la scrittura era **`quarantined`** e i layer nel
log **c'erano** (`['L1.10','L1.13','L1.15','L1.20']`).

#### 🔑 LA CLASSE — ed è la SECONDA volta oggi, sulla stessa forma, e la seconda volta è colpa mia
Un'ora fa ho nominato io la classe: **«un SENSORE CORRETTO usato come PROXY di una domanda che non
risponde»** (per `is_loaded()`). ⚠️ **Poi ci sono ricascata dentro**: ho chiamato «difetto» un campo
corretto perché gli stavo facendo la domanda sbagliata. **Nominare una classe non immunizza dal
caderci** — il presidio è **leggere il punto che decide fino in fondo**, non ricordarsi la lezione.
📌 Per **C9**: qui il difetto **non c'era**, e toglierlo dalla lista vale quanto aggiungercene uno.

#### 📌 COSA NON PROVA
· **Zero esecuzioni** (regime risparmio): questa è **lettura di codice**, non un A/B. Non ho
verificato a runtime che una scrittura **quarantinata** popoli davvero `layers` — **il dato di @ws8
lo mostra**, ma è suo, non mio, e va citato come tale.
· Non ho letto il percorso `routed_telemetry` (riga 697, `layers=["admission-route"]` fisso).

---

### 🔴 `L1.20` RIESEGUITO SU CODICE NUOVO: l'esito è identico, ma il commento promette un riarmo che la misura non vede
*(ws1 «Riscontro» / Curie · **28/08 22:12** · albero **`e761200e`** · **REGIME**: env stampata,
`env -u HIPPO_ENCODE_DELEGATE_ONLY …` per i casi «utente», store isolati, stesso claim di @ws8 ·
**RIESEGUITO, non riletto**)*

`semantic_selfclaim.py` **è cambiato** dal mio reperto delle 20:15 (c'è un `_ColdEncoderDeclined`
che prima non esisteva), quindi ho **rimisurato invece di rileggere** — un reperto su codice
cambiato va rimisurato **prima** che qualcuno lo citi.

| regime | esito |
|---|---|
| **senza** `delegate-only`, 1ª scrittura, processo fresco | `quarantined` `['L1.10','L1.13','L1.15']` — **niente `L1.20`** |
| **senza**, 2ª scrittura **stesso processo** | `quarantined` `['L1.10','L1.13','L1.15']` — **niente `L1.20`** |
| `is_loaded()` dopo la 1ª | **`False`** |
| **con** `delegate-only` (controllo) | `quarantined` `['L1.10','L1.13','L1.15',`**`'L1.20'`**`]` |

⇒ **Il reperto REGGE su codice nuovo.** 🔑 **Ed è il valore della riesecuzione**: rileggendo avrei
visto il file cambiato e **non avrei saputo se l'esito era cambiato**. Era uguale.

#### ⚠️ E IL PEZZO CHE VA A CHI STA SCRIVENDO LA CURA
Il commento **nuovo** dice testualmente: «*the very next write **re-arms** the detector; … this
only ever skips the **literal FIRST** write of a cold, daemon-less SDK process*».
**La misura non lo vede**: la **seconda** scrittura nello stesso processo **non ha `L1.20`**, e
`is_loaded()` è ancora `False` dopo la prima. **Non «solo la prima»: tutte e due.**

#### 📌 COSA NON PROVA — e lo dico prima che diventi un veto
· Due scritture **consecutive** nello stesso processo, **senza pausa**. Se «*warms via storage*»
significa un riscaldamento **asincrono** o in **un altro processo**, la mia misura non lo cattura:
servirebbe una terza scrittura dopo un'attesa. **Non l'ho fatta.**
· ⇒ **Non dico «il commento è falso».** Dico: **nel regime che ho misurato la promessa non si
avvera**, e chi consegna la cura deve sapere che quel pezzo di docstring **non è coperto da una
misura che lo confermi**.
🔑 Classe già in casa: **un commento che GIUSTIFICA invece di specificare è un indizio A FAVORE del
difetto**; la prova che il riarmo funziona sarebbe **un test che diventa rosso se sparisce**, non
la prosa.

---

### 📊 IL COSTO IN RAM DELLA NOSTRA INFRASTRUTTURA — 4,4 GB in DUE daemon che fanno lo stesso mestiere
*(ws1, **28/08 22:11**, PowerShell · dato **operativo**, non di prodotto — ma tocca chi installa)*

```
RAM: 3,59 GB liberi | 88,5% usata
python/pythonw: 58 processi = 13.726,3 MB
  PID 26608   2328 MB   pythonw -m verimem.encode_service          ← il servizio nuovo
  PID 26336   2051 MB   pythonw ~/.engram/bin/engram_embedding_daemon.py   ← quello vecchio
  PID 23232    695 MB   engram.exe mcp        (≥4 fra i primi sei, ~693 MB l'uno)
  non-python: dwm 935 MB · claude 835 MB · MsMpEng 780 MB
```
⇒ **Due daemon di encoding vivi insieme, 4,4 GB in due.** Se uno è un residuo, **sono 2 GB
liberabili senza toccare nulla di nostro**. ⛔ **Non ho ucciso niente**: porto **numero e
proprietario**, decide chi li ha aperti. ⚠️ E per dichiararne uno morto servono **due gambe**
(padre morto **e** zero porte in ascolto), **mai per nome**.
📌 Conferma indipendente del numero di @ws4 sui server MCP: **~693 MB l'uno**, misurato di nuovo.

---

### 🟢 LA CURA DI `L1.20` FUNZIONA — seconda firma, **rieseguendo**, con predizione dichiarata prima
*(ws1 «Riscontro» / Curie · **28/08 22:16** · albero **`d5705286`** · **REGIME**: env stampata
(`HIPPO_ENCODE_DELEGATE_ONLY=1`, `HIPPO_DATA_DIR`) **neutralizzata con `env -u`** nei casi utente ·
store isolati per caso · claim identico a quello di @ws8 · **RAM 3,23 GB liberi, 89,7%** — il banco
è leggero, per questo eseguibile anche a macchina piena)*

**Predizione, scritta PRIMA di guardare l'esito**: «*se la cura passa da `daemon_usable()`, nel
regime UTENTE con daemon vivo `L1.20` DEVE comparire; se non compare, la cura non morde dove
serve*».

| caso (regime UTENTE, senza `delegate-only`) | esito |
|---|---|
| 1ª scrittura, processo fresco | `['L1.10','L1.13','L1.15',`**`'L1.20'`**`]` ✅ |
| 2ª scrittura, stesso processo | `['L1.10','L1.13','L1.15',`**`'L1.20'`**`]` ✅ |
| 2ª **dopo pausa di 4 s** | `['L1.10','L1.13','L1.15',`**`'L1.20'`**`]` ✅ |
| controllo **con** `delegate-only` | `['L1.10','L1.13','L1.15','L1.20']` ✅ |

**Confronto col PRIMA** (stesso banco, albero `e761200e`, un'ora prima): **`L1.20` non compariva in
nessuno dei casi utente**. ⇒ 🟢 **DIFETTO CHIUSO**: un utente col servizio di encoding vivo ha il
presidio che prima aveva **solo la nostra macchina**.

#### 🛑 E RITIRO UNA MIA OBIEZIONE DELLE 22:12
Avevo segnalato che il commento prometteva «*the very next write re-arms the detector*» mentre
`is_loaded()` restava `False`. **Ora**: `is_loaded` **`True`** dopo le due scritture e dopo i 4 s.
**La promessa è diventata vera con la cura** — e col nuovo comportamento **il riarmo non serve
nemmeno più**, perché `L1.20` compare già alla prima scrittura. **Obiezione ritirata.**

#### 🔎 CASO DI BORDO CERCATO APPOSTA — e ne esce una discrepanza, NON isolata
`encode_service.py:889` legge **`ENGRAM_ENCODE_SERVICE`** (default `"1"`): messa a **0** spegne
l'**uso** del servizio **senza toccare il processo** (che non è mio).
```
con ENGRAM_ENCODE_SERVICE=0 : daemon_usable = True   delegate_only = False
banco, regime utente + SERVICE=0 : ['L1.10','L1.13','L1.15']   ← L1.20 TACE
```
⇒ **`daemon_usable()` dice `True` e `L1.20` tace lo stesso.** Due letture, **non ho isolato quale**:
**(a)** la cura non passa da `daemon_usable()` sul percorso che conta; **(b)** `SERVICE=0` blocca
l'**uso** ma non il **discovery** — `daemon_usable()` legge `read_discovery()`, che è un **file**,
non prova la connessione. La **(b)** mi sembra più probabile leggendo la firma, **ma non l'ho
verificata**.

#### ⚠️ IL LIMITE PIÙ IMPORTANTE: NON HO RAGGIUNTO IL REGIME CHE VOLEVO
Un utente **senza daemon** non avrebbe nemmeno il **file** di discovery ⇒ `daemon_usable()` direbbe
`False` e `L1.20` tacerebbe **per la ragione giusta**. Io ho un file di discovery **valido** (il
daemon gira qui) e ho spento solo l'uso. ⇒ **Il mio non è «utente nudo»: è un TERZO regime,
artificiale.** 🛑 **Non usatelo per dire «la cura non regge da un utente».**
📌 Se il banco «utente NUDO» di @ws8 esiste già, **il suo copre il caso vero e questo è solo un
bordo in più**.
