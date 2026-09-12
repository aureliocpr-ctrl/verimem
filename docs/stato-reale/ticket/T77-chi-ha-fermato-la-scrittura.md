# T77 — «chi ha fermato la scrittura» dice due cose diverse su due porte

*Ticket, 12/09/2026. **Seconda stesura, un'ora dopo la prima**: la prima aveva il
bersaglio sbagliato, e il modo in cui l'ho sbagliato è metà del valore di questa
pagina. Letto nel codice; **nessuna esecuzione**.*

---

## 0. La correzione, prima di tutto: la cura c'è già

La prima stesura diceva *«il campo che nomina chi ha fermato scrive un generico»*.
**Non è più vero dal 21/08.** La funzione che decide (`verimem/client.py:464`) nomina
il layer per davvero:

    store-screen  ->  'store-screen'     uno screen dentro store() ha ribaltato il fatto
    moat fallito  ->  'moat'
    L1 non-observe->  'L1'               (i marcatori `*-observe` esclusi, presidio 03/09)
    altrimenti    ->  il layer bloccante, con la precedenza di `_BLOCK_LAYER_PRIORITY`
    nessuno       ->  'gate'             <- ULTIMA riga: «nessun layer in mano»

E **la chiave non compare affatto** quando non c'è niente da dire
(`client.py:1178`: la si aggiunge solo `if _out_qb`). Cioè il contratto che questa
pagina voleva proporre — *nomina il layer vero, e dove non c'è resta vuoto* — **era
già stato scritto e curato**, con i suoi presidi.

🔁 **E il caso che ci ha messi in moto è il COMMENTO CHE DOCUMENTA QUELLA CURA.** Le
righe che riportano *«moat 99,89 · warning `layer='L4.1'` · scritto
`quarantined_by='gate'`»* stanno **dentro** il commento sopra quel `for`, insieme
alle misure del 21/08 che l'hanno motivato. Chi le legge trova un difetto raccontato
al **presente** e non ha modo di sapere che è passato.

> ⚠️ **La classe, e vale oltre questo ticket**: *un commento che spiega una cura
> descrive il difetto al presente.* L'unico modo di sapere se è vivo è leggere **il
> codice sotto il commento**. Oggi ci siamo cascati in più d'uno, su file diversi, e
> chi scrive questa pagina per primo.

## 1. Il difetto vivo, e sta su UNA porta sola

La funzione riceve i layer che hanno agito nel parametro `agito`. I tre chiamanti lo
riempiono in tre modi diversi:

| porta | cosa passa in `agito` | che cosa scrive |
|---|---|---|
| libreria (`client.py:1158`) | i layer che hanno colpito | **il layer vero** |
| porta esposta all'agente (`mcp_server.py:13871`) | i layer **bloccanti** | **il layer vero** |
| riga di comando (`cli.py:4763`) | `['store-screen']`, oppure **niente** | **`'gate'`** |

⇒ Sulla riga di comando i layer bloccanti **non arrivano mai**: quando il ramo è
`downgrade` la lista è vuota, il ciclo non trova nulla e la funzione cade
sull'ultima riga. **Lo stesso claim, sulla stessa fonte, lascia due nomi diversi a
seconda della porta da cui è entrato.**

📌 Non è un caso isolato su quella porta: sul **contrassegno del disaccordo interno**
(il campo che dice *«il giudice aveva approvato e qualcos'altro ha trattenuto»*) il
nostro registro annotava già «ricevuta sulle due porte … **manca sulla riga di
comando**». **Stessa porta, secondo campo.**

🔍 È la classe ① delle nostre: **una copia invece di una superficie unica**. La
funzione è unica proprio per non avere tre comportamenti — e ne ha tre perché
l'ingresso è riempito in tre posti.

## 2. Perché conta per chi usa la memoria

Perché la domanda «perché questo fatto non è stato scritto?» riceve **una risposta
diversa a seconda di come l'hai scritto**, e una delle tre non nomina il decisore.
Chi indaga con la riga di comando — la via più comune per guardare uno store —
riceve l'etichetta che **non dice chi**, e da un'etichetta generica si deduce.

## 3. La cura

1. **La riga di comando passa i layer bloccanti**, come fanno le altre due, unendoli
   al marcatore dello screen invece di sostituirli.
2. **Se c'è una ragione per non farlo, va scritta lì**: oggi quella riga non la dà, e
   una differenza fra porte senza una ragione scritta si legge come una svista — o,
   peggio, si copia.
3. Nessun campo nuovo, nessun contratto nuovo: **il contratto esiste**, va esteso
   alla terza porta.

## 4. Il RED — una promessa, non un campo

> **Lo stesso claim, con la stessa fonte, scritto dalle TRE porte, deve lasciare lo
> stesso nome in «chi ha fermato la scrittura».**

    ARRANGIA   una fonte e un claim che differiscono per UN VALORE (la fonte dice 162,
               il claim dice 160): il giudice semantico resta sopra il taglio e a
               fermare e' il layer lessicale
    AGISCI     scrivi lo stesso fatto DALLE TRE PORTE, su tre store isolati
    PRETENDI   i tre nomi sono uguali        <- oggi CADE: due dicono il layer, una 'gate'

**Controllo positivo, obbligatorio nello stesso braccio**: una seconda scrittura
fermata **davvero dal moat** deve dare `moat` su tutte e tre. Senza, un campo che
scrivesse sempre il layer lessicale passerebbe lo stesso.

🚧 **Non consegnato eseguito**: chi scrive questa pagina oggi non esegue. Il banco va
visto rosso da chi ha il cartellino **prima** che entri in `tests/`: un test non
provato che nasce verde è il modo in cui i presidi muoiono.

## 5. Quello che questo ticket NON dice

- **Non dice che la riga di comando sbagli di proposito**: la scelta è **letta**, non
  discussa con chi l'ha fatta, e un presidio vicino suggerisce che quel percorso sia
  stato pensato per altro.
- **Non misura quanti fatti ne portino il segno**: sul corpus il campo ha un debito
  storico già contato altrove, e questo ticket parla del **comportamento di oggi**.
- **Non tocca la precedenza** fra i decisori: quella ha i suoi presidi e resta com'è.
