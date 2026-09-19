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
> **Il numero che misura davvero la distanza sta in fondo, ed è `3/14`.**

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

## Il numero che conta: `3/14`

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

⇒ **Undici campi su quattordici non arrivano a nessuna porta**, fra cui i
quattro che dicono *come* è stato giudicato (`punteggio`, `soglia`, `scala`,
`modello`) e `margine`.

**Questo è il numero da guardare, non la tabella dei nomi.** Tre misure
indipendenti — tre persone, tre strade — hanno dato `3/14` lo stesso giorno.
Quando la ricevuta unica entra, il criterio è **`14/14` su tutte e tre le
porte**: se non ci arriva, la ricevuta unica non è unica.

---

⚠️ **Questa pagina scade.** È misurata su un wheel preciso, e il wheel cambia a
ogni lotto (tre punti del tronco in una mattina, tre sha diversi). Chi la rilegge
fra un mese **rimisuri prima di fidarsi**: il comando è nello script dei quattro
casi, e il confronto degli sha costa 2 MB.
