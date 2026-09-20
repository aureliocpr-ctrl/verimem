# I verbi delle tre porte — tabella di corrispondenza

> ## ⚠️ QUESTA PAGINA DICE I **NOMI**, NON I COMPORTAMENTI
>
> È una tabella di **corrispondenza fra nomi**: dice *dove guardare* quando
> passi da una porta all'altra, **non che cosa succede** quando chiami. Due
> nomi accanto in una riga possono fare cose diverse, e due nomi diversi la
> stessa cosa.
>
> Il rilievo è di un pari, non mio, ed è arrivato mentre scrivevo questa
> pagina: *«misurare a coppie non ha un bersaglio»*. Aveva ragione, e la
> pagina esiste **solo** perché una corrispondenza fra nomi fa risparmiare
> mezz'ora a chi cambia porta — non perché misuri qualcosa.
>
> **Il numero che misura davvero la distanza sta in fondo, ed è diverso per ogni
> porta: `14/14` alla riga di comando e alla libreria, `3/14` alla porta MCP.**

Misurato il 19/09/2026 sul wheel di `main` (`bdf7453b`), versione `0.7.7`, in
venv pulito. Le celle «non c'è» sono **verificate** (assenza provata eseguendo);
le corrispondenze in riga sono **plausibili**, non provate.

## La tabella

| operazione | CLI (40 comandi) | libreria `Memory` (43 nomi) | porta MCP (247 tool) |
|---|---|---|---|
| **scrivere un fatto** | `remember` | `add` | `hippo_remember` |
| salvare un checkpoint di sessione | `save` | — | — |
| **richiamare i fatti** | `recall` | `recall` | `hippo_facts_recall` |
| richiamare gli episodi | — | — | `hippo_recall` |
| **correggere** | `correct` | `correct` | ❌ **non c'è** |
| **chiedere** | `ask` | `ask`, `answer` | ❌ **non c'è** |
| **spiegare** | ❌ non c'è | `explain` | `hippo_recall_explain` |
| **fiducia** | `trust` | `source_trust`, `consistency_trust` | `hippo_trust_report`, `hippo_trust_stats` |
| **ignoranza** | `ignorance` | `ignorance` | `hippo_ignorance_map` |
| **cercare** | `search-docs` | `search` | `hippo_search`, `hippo_facts_search` |
| il testo si chiama | posizionale | `content=` | `proposition=` |

## Le tre trappole che questa tabella esiste per evitare

**① `save` non scrive un fatto.** L'aiuto lo dice: *«Save a **session
checkpoint** on the lineage chain»*, mentre `remember` è *«Store one **fact**
through the full moat»*. Chi usa `save` credendo di salvare un fatto lo scrive
come nota di sessione — e una scrittura meta-narrativa **salta lo screen
lessicale**. ⚠️ Chi scrive questa pagina ci è cascata per due giorni, misurando
la CLI col verbo sbagliato.

**② `hippo_recall` non torna i fatti, torna gli EPISODI.** Chi arriva dalla CLI
(dove `recall` dà i fatti) chiama `hippo_recall`, riceve `[]` e conclude che la
memoria è vuota. Il tool ha ragione — la sua descrizione dice *«over past
episodes»* — ma la risposta non porta quella ragione. *(È T107; la cura
concordata aggiunge la riga che manca.)*

**③ `correct` e `ask` non esistono sulla porta MCP**, su 247 strumenti.
Correggere un fatto — l'operazione centrale di un agente che lavora — richiede
di comporre `hippo_remember` + `hippo_fact_supersede` sapendo che vanno
composte. È una lacuna, non uno stile.

## Perché i nomi diversi NON si uniformano

`save`/`add`/`hippo_remember` non è un difetto: è il costo di tre interfacce,
e ognuna è idiomatica a casa sua — un comando, un metodo, un tool con prefisso.
Rinominare romperebbe **tutti** i chiamanti per un guadagno estetico, e chi
sbaglia un verbo riceve **subito un errore**.

🔑 **Il criterio, che vale oltre questa pagina**: *un nome diverso grida, un
campo che cambia nome tace*. Sbagliare verbo costa un messaggio d'errore;
leggere `risposta.get("warnings")` su una porta che chiama quel campo
`anti_confab_warnings` costa una lista vuota che si legge come «nessun avviso».
**La prima è una noia, la seconda è un difetto.**

## Il numero che conta: `3/14`, e oggi vale per **una porta sola**

Il nucleo dichiara la propria ricevuta in `verimem/core/ricevuta.py`, costante
`CHIAVI`, **quattordici campi**, e `come_dizionario()` porta scritto: *«L'unica
serializzazione. **Le porte rendono QUESTO, senza ritocchi**»*.

    campo canonico     libreria  MCP        campo canonico      libreria  MCP
    esito                 --      --        livelli                --      --
    id                    SI      SI        fermato_da             --      --
    punteggio             --      --        ritirati               --      --
    soglia                --      --        store                  SI      SI
    margine               --      --        store_decided_by       SI      SI
    scala                 --      --        store_env_ignored      --      --
    modello               --      --
    giudice               --      --        TOTALE            3/14     3/14

⚠️ **LE COLONNE QUI SOPRA SONO DUE, NON TRE**, e la prima stesura di questa
pagina scriveva accanto *«undici campi non arrivano a nessuna porta»*: una
proprietà di **tre** porte affermata avendone misurate **due**. La CLI non era
nella tabella. **Riga corretta il 19/09 la sera, con la misura di un pari.**

### E sul tronco la CLI è già a `14/14`

Misurato sul tronco `c4bec04c` da chi ha curato la prima fetta — **non da chi
scrive questa pagina**:

    CLI        14/14      ← la ricevuta unica è arrivata qui per prima
    libreria   14/14      ← arrivata dopo, misurata sul ramo che la porta
    MCP         3/14      ← l'unica rimasta indietro

⇒ **Il numero non è più uno solo.** Undici campi su quattordici non arrivano
**alla libreria e alla porta MCP** — fra cui i quattro che dicono *come* è stato
giudicato (`punteggio`, `soglia`, `scala`, `modello`) e `margine`. Alla riga di
comando arrivano tutti.

⚠️ E resta un campo che **una porta sola** dichiara: `fermato_da`. Una ricevuta
unica non è unica finché un campo lo dice una porta su tre.

### E `3/14` non vuol dire che la libreria dica poco: dice che **rinomina**

Rimisurato **da chi scrive questa pagina** — non più citato da altri — sul
sorgente del tronco, store temporaneo, una scrittura senza fonte. Il build l'ha
stampato il prodotto stesso (`build=c8f53dfc`):

    presenti: 3 / 14
    mancanti:     esito, fermato_da, giudice, livelli, margine, modello,
                  punteggio, ritirati, scala, soglia, store_env_ignored
    chiavi rese:  adjudication, advice, grounding_score, id, moat, replaced,
                  status, store, store_decided_by, stored, warnings

⚠️ **Undici mancanti, e undici chiavi rese.** La libreria non risponde con
*meno* informazione: risponde con **altri nomi** — `status` dove il nucleo dice
`esito`, `grounding_score` dove dice `punteggio`. Le corrispondenze sono
**plausibili, non provate**: nessuno ha ancora dimostrato che `status` porti
esattamente quello che porta `esito`.

🔑 È **il criterio di questa pagina applicato a questa pagina**: *un nome
diverso grida, un campo che cambia nome tace*. «Undici campi non arrivano» si
legge come un'assenza, e quello che si misura è in gran parte una **rinomina** —
che è peggio, perché `risposta.get("punteggio")` torna `None` senza dire che quel
numero è lì sotto `grounding_score`.


**Questo è il numero da guardare, non la tabella dei nomi.** Tre misure
indipendenti — tre persone, tre strade — avevano dato `3/14` su libreria e MCP
lo stesso giorno, e la quarta misura ha mostrato che la CLI era già oltre.
Quando la ricevuta unica entra, il criterio è **`14/14` su tutte e tre le
porte**: se non ci arriva, la ricevuta unica non è unica.

---

⚠️ **Questa pagina scade, e il `3/14` è già scaduto per la libreria**: era il
numero di ieri, ed è diventato `14/14` con la cura che porta la ricevuta del
nucleo a tutte e quattro le uscite della libreria. Resta `3/14` sulla porta MCP,
che è l'ultima.

**La cura è già aperta**: c'è una richiesta che fa rispondere la libreria con la
ricevuta del nucleo da tutte e quattro le sue uscite (`#96`). ⚠️ **Non è fusa
mentre questa riga viene scritta** — quindi il `3/14` qui sopra è il numero di
adesso, non una condanna, e chi legge dopo deve guardare lì per primo.

**Rimisurare costa quattro righe, e non serve lo script di nessuno** — questo
è il comando che ha prodotto i numeri qui sopra:

    from verimem.core.ricevuta import CHIAVI     # il bersaglio: 14 campi
    from verimem import Memory
    r = Memory("una/cartella/prova.db").add("<il fatto>")
    print(len(set(CHIAVI) & set(r)), "/", len(CHIAVI), sorted(set(CHIAVI) - set(r)))

⇒ Tre avvertenze che costano un giro a chi non le ha:
- il bersaglio si **importa**, non si ricopia: chi conta a occhio i campi
  annotati ne trova 13, perché `margine` è una property;
- `Memory(...)` vuole **un file**, non una cartella: con una cartella risponde
  `sqlite3.OperationalError: unable to open database file`, che non lo dice;
- `Memory()` senza argomenti apre lo **store vero**. Per misurare si passa un
  file temporaneo, altrimenti si scrive nella memoria di produzione.
