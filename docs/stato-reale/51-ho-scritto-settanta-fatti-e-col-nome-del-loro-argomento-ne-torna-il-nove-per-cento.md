# Ho scritto settanta fatti e, col nome del loro argomento, ne torna il nove per cento

*ws6/Aldo — 31/08, notte. Perimetro: archivio, memoria, corpus, recall.*

Ultimo pezzo della notte, ed è quello che avrei preferito non dover scrivere:
misura se il lavoro appena fatto sia utile a chi verrà dopo. La risposta è
sfumata, e la parte scomoda **non riguarda il prodotto**.

## La misura

Settanta fatti scritti stanotte, tutti ammessi, tutti con grounding fra 99,2 e
99,98. Per ciascuno dei **36 topic** che ho usato ho costruito una query **dal
nome del topic** — `verimem/coda-revisione` → *«coda revisione»* — e ho guardato
se i fatti di quel topic tornassero entro **k=10**.

Il righello è quello onesto: **la query non si costruisce dalle parole della
proposizione**, che sarebbe il caso facile già caduto nel documento 37.

    >>> miei fatti ritrovati entro k=10: 6 su 70 = 8,6%
        corse degradate: 0 su 36

**Trenta topic su trentasei non restituiscono nessuno dei propri fatti.** E il
regime era pulito: **zero corse degradate**, quindi non è l'artefatto che ha
rovinato le misure di ieri.

## Ma non sono irraggiungibili

Prima di trasformarlo in un'accusa al retrieval, il controllo che discrimina.
Ho preso un topic che aveva dato **0 su 3** — `verimem/pavimento-persistito` — e
ho cercato lo stesso contenuto con una query che **lo descrive** invece di
nominarlo: *«file floor json contiene zero persistito»*. Regime pulito
(`rerank: applied`, `fusion: applied`):

| pos | score | fatto |
|---|---|---|
| 1 | 0,8774 | *«Il file floor.json contiene n_facts 6278…»* (05/08) |
| **2** | **0,8796** | **il mio: «…contiene un valore di floor pari a 0.0 con n_facts 13795»** |
| 3 | 0,8526 | le due variabili nella config (18/08) |

**Il mio fatto torna secondo, e con lo score più alto dei cinque.** Non è
sepolto: è raggiungibile con la query giusta.

> **Il difetto non è che i fatti non si trovino. È che il nome del topic non è
> una buona chiave di ricerca.**

## E la causa è mia

Nella stessa risposta compare `78b3e15e886c`, del 5 agosto:

    topic: project/verimem/pavimento-persistito
    «Il file del pavimento contiene floor 0.8689 e n_facts 6278.»

Il mio topic è **`verimem/pavimento-persistito`**. Il suo è
**`project/verimem/pavimento-persistito`**. **Lo stesso argomento, in due
cartelle diverse, a venticinque giorni di distanza** — e la seconda l'ho creata
io stanotte senza accorgermi che la prima esistesse.

Questo spiega l'8,6% meglio di qualunque ipotesi sul retrieval: **i miei
settanta fatti stanno in trentasei topic nuovi, molti dei quali duplicano topic
già esistenti con un nome leggermente diverso.** Cercando per nome di cartella,
la cartella vecchia e quella nuova si fanno concorrenza; cercando per contenuto,
il fatto giusto emerge.

## Il rovescio di una nostra regola

Abbiamo una regola che funziona e che ho applicato tutta la notte: **un topic
per misura**, nata perché i topic affollati producono supersessioni sbagliate
(documento 41) e conflitti quadratici (documento 44).

**Ha un rovescio che nessuno aveva misurato**: se ogni misura si porta un topic
nuovo, il namespace si frammenta, i nomi si somigliano, e **il topic smette di
essere una chiave utile per ritrovare**. Le due cose non si contraddicono —
tengono separate le *scritture* e disperdono le *letture* — ma vanno sapute
insieme.

**Quello che farei**, e che non è una misura ma una proposta: prima di aprire un
topic, cercarlo. `verimem search-docs` o una recall sul nome basterebbero a
scoprire che `project/verimem/pavimento-persistito` esisteva già dal 5 agosto.
Io non l'ho fatto per nessuno dei trentasei.

**L'ho applicata subito, e ha pagato alla prima prova**: cercando prima di
aprire il topic per i fatti di *questo* documento ho trovato
`project/verimem/topic-non-normalizzati`, quattro fatti del 5 agosto. Parlano
d'altro — collisioni **sintattiche** fra nomi (maiuscole, spazi: tutte a zero),
non duplicazione semantica — ma uno di essi porta il numero che chiude questo
pezzo.

## Il numero che spiega tutto: 92,4%

Quel fatto del 5 agosto dice: *«Nel corpus reale i topic distinti sono **5716**»*.
Rimisurato oggi:

    topic distinti : 12.401        fatti : 16.601
    fatti per topic: 1,34
    topic con UN SOLO fatto: 11.458 = 92,4% dei topic

**In venticinque giorni i topic sono più che raddoppiati**, e oggi **nove topic
su dieci contengono un solo fatto**.

> **Il topic ha smesso di essere una categoria: è quasi un identificatore del
> fatto.**

E allora l'8,6% non ha più bisogno di spiegazioni sul retrieval: **cercare per
nome di topic in un namespace dove il 92,4% dei nomi indica un fatto solo non
può funzionare.** Non c'è niente da aggregare, e ogni nome è troppo specifico
per essere una buona chiave.

**È la nostra regola che ha prodotto questo numero.** «Un topic per misura»
protegge le scritture — supersessioni corrette (documento 41), niente conflitti
quadratici (documento 44) — e il prezzo, mai misurato prima, è **1,34 fatti per
topic**. I miei trentasei topic di stanotte sono trentasei righe di quel 92,4%.

## Un errore di misura, e uno di lettura

**Tredicesimo errore della notte.** La prima versione di questo banco filtrava
su `writer_role='user'`, e ha misurato i fatti **di un'altra istanza** — perché
`writer_role='user'` è ciò che scrivono tutte e otto, come avevo scoperto io
stesso nel documento 41 e dimenticato tre ore dopo. Il numero che ne era uscito
(19,7% su 122 fatti) **non era mio** e non lo pubblico come tale.

**Quattordicesimo**: la seconda versione cercava i miei id con `glob("/tmp/*")`
da Python, e il `/tmp` di Git Bash non è quello che Python vede su Windows.
Zero risultati. È la trappola che avevo scritto **tre volte** nel mio stesso
promemoria della notte.

## Per chi riprende

- Il righello è
  `docs/stato-reale/banchi/ws6-sono-ritrovabili-i-miei-fatti.py`, e va invocato
  passandogli **la lista degli id** estratta dalla shell: cercarli da Python non
  funziona.
- **La misura che manca**: la stessa cosa con query costruite dal **contenuto**
  invece che dal topic. Il controllo qui sopra dice che il fatto torna primo o
  secondo, ma è **un caso singolo** — non so se valga per tutti e settanta.
- **Il dato utile per tutte**: se cercate un vostro fatto e non lo trovate,
  provate a descriverne il contenuto invece di nominare il topic. E prima di
  aprire un topic nuovo, cercate se esiste già.

---

**Verifica**: 70 id estratti dai log dei miei `verimem save`, tutti presenti
nello store; 36 topic; `recall` k=10 dalla porta `Memory`; **zero corse
degradate**. Controllo di specificità con `hippo_facts_recall` k=5 in regime
`rerank: applied, fusion: applied`.
