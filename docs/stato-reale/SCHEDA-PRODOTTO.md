# Verimem — la scheda prodotto

**Livello 1 del disegno esploso, «l'esterno».** Iris (ws7, Product Owner) per la
promessa, l'utente e la prova; Corrado (ws8, Release) per i concorrenti e i
numeri del mondo (`docs/mondo-esterno/2026-09-05-concorrenti-cosa-non-fanno.md`).
**Scritta il 2026-09-04, aggiornata il 2026-09-06, sul pacchetto pubblicato
`verimem==0.7.6`.**

> **Perché questa scheda esiste, ed è il reperto che l'ha fatta scrivere.** Due
> dei sette «difetti da utente» trovati ieri erano **già scritti nel README** —
> i costi su disco stanno alla **riga 397 di 812**, `doctor` è prescritto due
> volte come verifica. Il difetto non è che la verità manchi: **è che stia alla
> riga 397 su 812**, e nessuno legge 812 righe. Questa pagina non riassume il
> README: dice **cosa deve stare nella prima schermata**.
>
> ✅ **La prova che questa scheda funziona è falsificabile**: un utente che non
> ci conosce arriva in fondo ai dieci minuti **senza aprire le altre 780 righe**.
> Se non ci arriva, la scheda è sbagliata — non l'utente.

---

## 1 · La promessa, in una frase

> **Una memoria per agenti che si rifiuta di ricordare ciò che la sua fonte non
> sostiene.**

Non «ricorda di più». **Ricorda di meno, e ti dice quando non sa.** Ogni
scrittura passa un cancello di ammissione; un'affermazione che la fonte non
regge viene **conservata ma non servita** — resta nello store, marcata, fuori
dal richiamo, e la ricevuta dice chi l'ha fermata.

Misurato sul pacchetto pubblicato, non sul repo (Giano, percorso ① del 04/09):

```
self-claim non sostenuta →  status=quarantined  quarantined_by=moat
                            grounding 0.19  layers=['L1.15','L4-grounding','L4-negazione']
```

🔴 **E la condizione senza la quale questa frase non vale, scritta qui e non in
fondo: il giudice deve essere caldo.** Se non lo è, la scrittura con `source`
entra lo stesso — marcata `L4-skipped`, ma entra — e su una macchina nuova via
MCP questo accade **dopo un'attesa che va da 313 secondi a oltre 15 minuti**
(misurato da Corrado e da Tara sul pacchetto pubblicato; il numero è un
intervallo perché **le prime letture erano la finestra di chi guardava**, non la
durata del fenomeno). **Esegui `verimem warmup` prima di scrivere.** Finché non
lo fai, il prodotto non ti sta mentendo — te lo scrive nella ricevuta — ma la
frase qui sopra **non descrive quello che ti sta succedendo**.

---

## 2 · A chi serve, e il minuto esatto in cui se ne accorge

**A chi costruisce agenti che scrivono in memoria quello che credono di aver
fatto.**

Il momento è questo: un agente chiude un compito e salva *«ho migrato il
servizio, i test passano»*. Nessuno ha verificato quella frase. Sei settimane
dopo è **l'unica cosa che resta** di quel lavoro, e ogni agente che legge la
tratta come un fatto. Nessuno saprà mai che era una supposizione — perché una
memoria normale non distingue *«è successo»* da *«credo sia successo»*.

Verimem è per chi ha già pagato quel conto una volta. Se i tuoi agenti scrivono
solo dati che arrivano da fuori (letture di API, log, documenti), **non ti
serve**: paghi un cancello che non hai motivo di attraversare.

**Il secondo momento**, misurato da Giano su un giro reale: il mondo cambia (il
fornitore di pagamenti migra), l'agente richiama, e nella risposta ci sono **il
vecchio e il nuovo insieme** senza un segnale su quale valga. Su quel giro
verimem ha restituito **solo il corrente** (`nuovo: True · vecchio: False`) e
`recall --with-history` ha raccontato la transizione: cosa diceva prima, da
quando, fino a quando ha tenuto.

🔴 **E qui la scheda deve dire una cosa che non le fa comodo, perché è la riga
con cui ci vendiamo.** Un secondo giro — il percorso «un team su uno store»,
eseguito il 06/09 sullo stesso pacchetto — ha dato **l'esito opposto**: dopo una
correzione con la sua fonte, giudicata e ammessa a 99,45, **il fatto vecchio non
è stato superato affatto** (`superseded_by = None`) e i due sono tornati insieme.
⇒ **La stessa capacità si comporta in due modi in due nostri giri**, ed è aperto
come **T14 (P0 sulla porta MCP)**: fino a che quella differenza non ha un nome,
**questa riga non è una garanzia: è un comportamento che dipende da come scrivi
la correzione, e il modo giusto non è documentato da nessuna parte.**

---

## 3 · La prova in dieci minuti

**Misurata due volte, da due persone, in due ambienti — e sta dentro i dieci in
entrambi:**

| chi | quando | tempo | regime |
|---|---|---|---|
| Tara | 04/09 | **6,8 min** | pacchetto PyPI, ma con variabili d'ambiente **ereditate** |
| Iris | 06/09 | **5,9 min** | pacchetto PyPI, **ambiente ripulito di nove variabili** |

`pip install` 280,8 s · `warmup` 28,3 s · `doctor` 7,8 s · Quickstart 16,3 s ·
una scrittura propria + richiamo 16,2 s. Il giro di lavoro vero, dopo
l'installazione, **40 secondi** (Giano, seconda esecuzione; 62 s la prima).

> 🔍 **Perché due numeri e non uno.** Il primo girava con nove variabili
> d'ambiente ereditate — due delle quali puntavano a un altro store. Il secondo
> le toglie tutte. **Non sono in contraddizione, e li teniamo entrambi**: un
> numero senza il suo regime non è una misura, e chi legge deve poter vedere che
> la differenza fra i due è l'ambiente, non il prodotto.

✅ **E la promessa del punto 1 è verificata QUI, non altrove**: nel passo del
Quickstart la falsità entra e **viene fermata** — `status=quarantined`,
`quarantined_by=moat`, grounding **0.69**. *(Il primo assert guardava solo che la
frase non tornasse: sarebbe passato anche se non fosse tornato nulla. Adesso
guarda lo stato.)*

```bash
pip install verimem        # ~5 min, ~1.0 GB su disco (74 pacchetti, torch è più di metà)
verimem warmup             # ← NON SALTARE: 746 MB, il giudice. Senza, il cancello è SPENTO
verimem doctor             # verifica l'installazione — e ti dice QUALE store sta guardando
python -c "..."            # il Quickstart: scrive una falsità, e l'assert non la ritrova
```

🔴 **Una cosa da sapere prima di scrivere la prima riga, e la stiamo insegnando
male noi.** Il Quickstart usa `Memory("memoria.db")` — **un percorso relativo**,
che crea il database **nella cartella in cui ti trovi**, non nello store che
`verimem doctor` e la riga di comando guardano. Misurato il 06/09:

```
Memory("memoria.db") + HIPPO_DATA_DIR impostato
  → i fatti finiscono in ./memoria.db          (98 KB)
  → nello store va solo events.jsonl           (613 byte)
  → poi `verimem recall …` dalla stessa cartella: «no facts found», exit 0
```

⇒ **Scrivi con la libreria e rileggi dalla riga di comando, e non trovi niente**
— senza nessun errore. *(ticket **T16**, **P0**.)*

✅ **La riga che funziona, e l'abbiamo misurata:**

```python
from verimem import Memory
m = Memory()          # ← SENZA argomento: libreria e riga di comando vedono lo stesso store
```

| | SDK | CLI |
|---|---|---|
| `Memory("memoria.db")` | scrive ✅ | **non trova** 🔴 |
| `Memory("memoria.db")` + `recall --db …` | scrive ✅ | **`recall` non accetta `--db`** (exit 2) |
| **`Memory()`** | scrive ✅ | **trova** ✅ |

⇒ **Usa `Memory()` senza argomento** finché T16 non è curato. Se preferisci un
file tuo, resta su **una sola porta**: non mescolare libreria e riga di comando.
E se la CLI ti dice «no facts found», la prima domanda è **dove ha guardato** —
`doctor` te lo dice, `recall` ancora no.

🔴 **`warmup` non è un dettaglio ed è il motivo per cui è la seconda riga**:
finché non lo esegui, ogni scrittura con `source` è ammessa **senza essere
controllata** (la ricevuta lo dice: `layers=[]`, avviso `L4-skipped`). Il
prodotto non mente mai su questo, ma **la promessa del punto 1 non vale finché
non hai eseguito quel comando.**

⚠️ **Quello che oggi può rompere questi dieci minuti**, scritto qui invece che
alla riga 397:

**Se scrivi con `source` dalla porta MCP prima che il giudice sia caldo, la
prima scrittura si blocca a lungo — e può finire senza giudicare.** Misurato fra
**313 secondi e oltre 15 minuti**. Con il daemon già acceso il fatto arriva
giudicato (`judged=True`, 99,92); **su una macchina nuova, senza daemon, arriva
`judged=False`, `layers=['L4-skipped']`, `stored=True`** — cioè hai pagato
l'attesa e **non hai avuto il controllo**. *(ticket T1, il primo della coda.)*
⚠️ **La spiegazione c'è ed è la stessa che dà la CLI in 1,2 secondi** — il
prodotto non tace: **arriva tardi**, quando il tuo client ha già rinunciato.
**Fai `verimem warmup` prima, ed è il motivo per cui è la seconda riga.**

> ⚠️ **`verimem doctor`, e questa riga è IN VERIFICA — la lasciamo aperta invece
> di scegliere il numero che ci fa comodo.**
> · Su **`main`**: esce **`0`** su un'installazione nuova — misurato due volte da
>   Tara (store assente e store vuoto) e riconfermato da Iris il 06/09. L'`exit 1`
>   che avevamo messo a ticket veniva da una variabile d'ambiente **ereditata**
>   che puntava a un altro store, grande e con problemi veri; `doctor` diceva a
>   chiare lettere quale store stava esaminando, e `1` su warning è documentato
>   (`0` ok, `1` warning, `2` errore). **Il ticket è stato ritirato da chi l'aveva
>   aperto.**
> · **Sul pacchetto `0.7.6`, quello che installi tu, esce `1`** — e adesso
>   sappiamo perché (misurato, riga esatta):
>   `! relevance-floor  floor 0.0000 computed on 0 facts` con `fix: verimem warmup`.
>   **Su un'installazione nuova lo store è vuoto per definizione**, il pavimento
>   di rilevanza si calcola su zero fatti, e `doctor` esce `1` proponendoti **il
>   comando che hai appena eseguito**. Tutti gli altri check sono verdi.
> 🟢 **È già curato su `main`**: non serve fare niente, serve che entri nel
> prossimo rilascio. *(ticket `T8-bis`, **P3**.)*
> ⇒ **Se al passo 3 vedi rosso e gli altri check sono verdi, tira dritto**: il
> Quickstart del passo 4 passa, e ci mette 16 secondi.

---

## 4 · Il numero di valore, e il suo prezzo

### Cosa nessun altro fa

**Zero gate di entailment al write, su tredici prodotti letti nel codice e nei
prompt** (Corrado, 04/09: mem0, Zep/Graphiti, Cognee, Hindsight, Supermemory,
MemMachine e altri). Non è che lo facciano peggio: **non c'è una decisione
ammetti/rifiuta al momento della scrittura**. mem0 è dichiaratamente add-only
(*«nothing is overwritten»*); Zep/Graphiti mette la richiesta di fondatezza
**dentro il prompt**, che è un'istruzione, non un controllo; Cognee e Hindsight
tracciano **da dove viene** un dato, non **se regge**; Supermemory manda a una
coda di revisione **umana**. In letteratura la cosa esiste in tre paper da
maggio 2026, **nessuno installabile**.

### Quanto bene lo facciamo — con il prezzo accanto

| | |
|---|---|
| falsità **servita** (la nostra metrica C10, quattro corpora) | **15,9% · 20,0% · 24,7% · 35,7%** |
| il prezzo: **fatti veri persi** | **~29%** (19,0–54,0 sugli stessi quattro) |

⛔ **Il 15,9% da solo non si scrive.** È l'estremo favorevole di quattro corpora
e il valore oscilla **2,25 volte** fra il migliore e il peggiore: citarne uno
significa scegliere quello che fa comodo. **O l'intervallo, o un corpus solo con
il suo nome — e sempre col prezzo accanto**, perché un cancello che ferma le
falsità fermando anche un terzo delle verità non è un affare per tutti.

### E il numero che ci sta contro

**186 download al mese contro 3.452.711 di mem0: 18.563 a 1** (pypistats,
letto il 04/09). **Lo scriviamo noi per primi**, perché chiunque lo trova in
trenta secondi. Il contesto che lo spiega senza cancellarlo: la 0.7.6 è su PyPI
**da oggi**, 9 versioni in tutto. *186 al mese non è un mercato: è un progetto
appena pubblicato. La domanda utile non è come saliamo — è se esiste qualcuno
che ha davvero bisogno della colonna che nessun altro ha.*

⚠️ **Non verificato in esecuzione**: la colonna dei concorrenti è letta dalla
loro documentazione e dal loro codice, **non eseguita**. La riga «su quel loro
metro noi restituiamo solo il corrente» viene dalla definizione di fallimento
che dà mem0 stessa, non da una prova su mem0 in esecuzione. **Prima di metterla
in una pagina pubblica va eseguita.** L'unico confronto oggi *eseguito* è
TrustMem-Bench contro `mem0 2.0.4` (60/60 contro 40/60), e porta la versione
scritta perché una misura su un prodotto altrui senza versione non scade mai.

---

## 5 · Cosa costa, e cosa oggi non funziona

**Costa**, dichiarato: ~1.0 GB di installazione, ~3.3 GB dopo il primo `warmup`
(misurato su Windows/py3.13). E **38.675 token di contesto per sessione** se lo
colleghi via MCP — 249 strumenti esposti, ~19% di una finestra da 200k, prima
che tu scriva una riga.

⚠️ **E quel costo lo paghi quasi tutto per niente**: sui nostri 15.099 usi reali,
**37 strumenti coprono il 90%** delle chiamate e **102 non sono stati chiamati
mai**, in quasi quattro mesi. *(La curva è sul nostro traffico, non sul tuo: se
usi il prodotto in un altro modo può cambiare.)* Un modo di esporne meno **non
c'è ancora**: la manopola che esiste filtra per prefisso, e i più usati hanno
tutti lo stesso prefisso degli altri. **Il design della cura è scritto** — tre
profili da 11, 28 e 37 strumenti — e non è ancora codice.

**Non funziona**, al **06/09**, sul pacchetto pubblicato — e la notte fra il 5 e il 6 ha
aggiunto un P0 e ne ha reso due più precisi:

| difetto | livello | dove morde |
|---|---|---|
| 🔴 **se l'encode non è raggiungibile il fatto entra SENZA embedding e la ricevuta dice `admitted`** — poi la ricerca risponde *«probabilmente la risposta non è in memoria»* **su un fatto che c'è** | **P0** | **chiunque scriva: 13 fatti in 32 minuti, di cinque di noi** |
| 🆕 **scrivi con la libreria e rileggi dalla riga di comando: «no facts found», `exit 0`** — e la riga che lo produce era nel nostro Quickstart *(riga corretta il 06/09; il difetto resta)* | **P0** | **chi segue le nostre istruzioni** |
| **su una macchina nuova la prima scrittura con fonte via MCP** aspetta fino a **903 s** e può entrare `judged=False`: hai pagato l'attesa e non hai avuto il controllo | **P0** | **la promessa del punto 1, per chi installa oggi** |
| una self-claim **preceduta da una frase vera** passa il cancello | **P0** | la promessa del punto 1 |
| **entrambe** le porte MCP accettano `as_of` e **lo ignorano senza dirlo**: chi chiede il passato riceve il presente | **P0** | **curato in `main`** (`db7dfd11`), non ancora in un rilascio |
| 🆕 **correggi un fatto e il vecchio non viene superato** — e sulla **porta degli agenti** non ricevi **nessun avviso**: `ok:true`, `replaced:false`, `moat: judged 99.8` | **P0 su MCP** · P1 su SDK | **un team che si corregge a vicenda** |
| le chiamate **rifiutate** non entrano nel log d'audit, e il log dice **cosa** ma non **chi** | **P1** | un team che vuole sapere cosa ha fatto l'agente |
| 🆕 **chiedi il passato con un filtro e il filtro sparisce**: `as_of` **sostituisce** gli altri filtri invece di comporli — i superati non tornano anche se li chiedi, gli scaduti sono esclusi **senza avviso**. Ricevi meno di quello che hai chiesto, e non te lo dice | **P1** | chi usa il viaggio nel tempo, che è una delle righe con cui ci distinguiamo |
| le porte gemelle divergono su **cinque livelli di contratto** (massimo, nome del parametro, nome del campo, campi della ricevuta) · 248 strumenti su 249 si chiamano `hippo_` · le chiavi dell'output sono in italiano · la CLI non stampa gli id dei fatti · 🆕 **ogni fatto la cui fonte contiene un codice di uscita riceve un avviso falso** che ti dice di correggere, **sotto una ricevuta che accetta** | **P2 / P3** | l'inciampo, non il muro |

> 🔍 **Come sono stati trovati, perché conta più dell'elenco. Due dei sei P0 non li ha
> trovati una revisione del codice: sono usciti USANDO il prodotto.** Quello sulla
> correzione che non supera è uscito **eseguendo il percorso «un team su uno store»**, e
> prima di pubblicarlo **abbiamo falsificato sette volte il banco che lo misurava** — tre
> dei «difetti» che stavamo per attribuirci erano del nostro strumento, non del prodotto.
> Quello sullo store — 🆕 il più grave per chi installa — è uscito **rifacendo il nostro
> stesso Quickstart riga per riga**, e nessuno l'aveva visto leggendo il codice: **uno di
> noi ci era già inciampato due giorni prima e l'aveva attribuito a un proprio errore.**
> ⇒ Un elenco di difetti vale quanto vale il metodo che l'ha prodotto; questo è il nostro,
> ed è **il percorso dell'utente, non la lettura del sorgente.**

*(Scala e argomentazione in `GRAVITA-DIFETTI.md`; i reperti in `00-ESAME.md`.)*

**Perché li scriviamo noi, in una pagina che dovrebbe venderci.** Un prodotto
che vende verificabilità e nasconde ciò che di sé non ha verificato ha già
rotto la sua unica promessa. La riga di sopra è il primo posto in cui questi
difetti compaiono — non l'ultimo.

---

## 6 · Cosa manca a questa scheda

- **Letta e Zep non sono misurati**, solo letti. L'unico confronto eseguito è
  contro `mem0 2.0.4`.
- **Nessuna riga nostra su un banco pubblico nominabile** accanto ai loro
  numeri. Il secondo ciclo dell'Agent Memory Leaderboard apre il **20/09/2026**
  e chiede due endpoint pubblici (`Add`, `Search`): è l'unica classifica non
  gestita da un concorrente. *Informazione con scadenza, non una proposta.*
- **La prova falsificabile della scheda non è ancora stata fatta** — ma dal 06/09
  **non manca più il protocollo, manca solo l'esecuzione**: sta in
  `LA-PROVA-DELLA-SCHEDA.md` (cosa riceve chi esegue, le tre domande, cosa conta
  come passato, e cosa **non** è un fallimento della scheda).
  · **Il soggetto non era nella stanza, e non per caso**: fra noi otto nessuno ha
    più l'ignoranza che serve — è **il motivo per cui questa riga è ferma**, non
    la mancanza di dieci minuti *(diagnosi di @ws4 Nadia)*.
  · **Il candidato è un surrogato dichiarato**: un'istanza fresca, senza il nostro
    contesto. ⚠️ Non è un utente: **è addestrata a colmare l'implicito**, quindi
    dove la scheda tace lei indovina — e indovina bene. ⇒ **un rosso vale
    moltissimo, un verde vale poco.**
  · **Manca solo il via**, perché lanciarla apre un processo che non è nel
    perimetro di chi l'ha proposta né nel mio.
