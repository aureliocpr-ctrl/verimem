# 67 — La data nella domanda spegne la risposta, e il silenzio non ha un avviso

*ws6/Aldo — 1 settembre 2026, 19:37. Filone «letture che non trovano», aperto dal
[61](61-il-punteggio-separa-benissimo-e-per-questo-l-avviso-ha-ragione.md).*

Il `61` aveva stabilito che il difetto è il **retrieval**, non la soglia. Cercando
quali letture non trovano ne è saltata fuori una che non trova **niente**:

```
domanda:  «il 18 luglio 2026 quanti fatti scritti e quanti mai giudicati»
risposta: 0 risultati, nessun avviso
```

La stessa domanda, con una riga di differenza, risponde benissimo.

## ① L'A/B che isola la causa, nella stessa esecuzione

```
1. as_of="auto"  (come lo chiama il prodotto)   n=0
2. as_of=None                                   n=6   best=0.8790
3. as_of=None + min_relevance=0.0001            n=6   best=0.8790   <- identico
4. as_of="auto" + min_relevance=0.0001          n=0
```

⇒ **Il pavimento non c'entra**: abbassarlo a zero non cambia né il braccio buono
né quello vuoto. **La causa è tutta nel routing temporale.**

📌 E il `best` senza routing è **0,8790**, cioè **sopra il pavimento 0,8781**:
senza il routing questa sarebbe una lettura buona, **senza nemmeno l'avviso**.

## ② La catena, letta nel codice

| dove | cosa fa |
|---|---|
| `client.py:1117` | `as_of == "auto"` → `extract_as_of(query)` |
| `temporal_context.py:132` | estrae «18 luglio 2026» → epoch di **fine giornata** |
| `client.py:1128` | `recall_as_of(..., when=<18 luglio>)` |
| `temporal_context.py:218` | `recall(k*6, include_superseded=True)` e **poi** scarta chi ha `born > when` |

🔑 **Il filtro è POST-RETRIEVAL su un pool oversampled ×6.** Non interroga lo
store al passato: prende i primi `k×6` di **oggi** e poi butta via i nati dopo. Se
i 60 più simili sono tutti recenti, non resta nulla.

> ⚠️ E il docstring di `recall_as_of` promette esattamente ciò che non regge:
> *«oversampled so the as-of filter doesn't starve top-k»*. **Il top-k è affamato.**

E i tre fatti che rispondono alla domanda mostrano perché:

| fatto | parla del | **scritto il** | esito |
|---|---|---|---|
| `0ebe9e824198` | 18 luglio 2026 | 30/08 21:25:31 | **perso** |
| `758425daf047` | 19 agosto 2026 | 30/08 21:25:41 | **perso** |
| `a9186a0a3ab9` | 30 agosto 2026 | 30/08 21:25:41 | trovato |

Sono tre righe dello stesso banco, scritte **nello stesso minuto**. Torna solo
quello la cui data coincide col giorno in cui l'abbiamo scritto.

## ③ Quanto spesso — e il denominatore giusto non è quello ovvio

A/B su domande costruite dal **testo del fatto** (frammento di 12 parole), fatti
**vivi e non quarantinati**, `k=10`, stessa esecuzione:

```
il fatto torna in ENTRAMBI i casi                : 27 = 87.1%
TORNA SENZA ROUTING E NON CON -> LO SPEGNE LUI   :  3 =  9.7%
torna SOLO col routing -> LO ACCENDE (a favore)  :  0 =  0.0%
non torna in nessuno dei due (altra causa)       :  1 =  3.2%
```

> 🪞 **Il 9,7% è di nuovo un tasso su una popolazione mista** — l'errore del
> [66](66-il-criterio-scartava-proprio-i-casi-piu-comuni.md), commesso ieri e riconosciuto qui **prima** di pubblicare. Il filtro
> scarta chi ha `born > when`: **un fatto scritto nel giorno che nomina non può
> essere colpito.** Il denominatore vero sono i **retrospettivi**.

```
retrospettivi (scritti DOPO la data che nominano) : 16
contemporanei (scritti nel giorno, o prima)       : 15

spenti fra i RETROSPETTIVI :  3/16 = 18.8%
spenti fra i CONTEMPORANEI :  0/15 =  0.0%   <- l'altra popolazione
```

✅ **Lo zero sui contemporanei non è un risultato deludente: è la conferma del
meccanismo.** Se il fenomeno fosse rumore, colpirebbe entrambe le popolazioni.

🔴 **E le tre letture spente erano tutte al RANGO 1.** Il routing temporale non
degrada la classifica: **toglie la risposta migliore.**

## ④ La funzione non è rotta — misurata sulla popolazione per cui esiste

Il braccio che mancava al mio banco, e senza il quale avrei accusato una
funzione sana. Su 25 fatti **superseduti**, domanda dal loro testo, `as_of` a un
minuto dopo la loro nascita:

| | col time travel | nella recall di oggi |
|---|---|---|
| il fatto ritirato torna | **2 = 8,0%** | **0 = 0,0%** |

⇒ **Fa il suo mestiere**: recupera fatti ritirati che oggi non tornerebbero
affatto. Poco, ma nel verso giusto, e la recall normale dà zero.

📌 **Il difetto non è la funzione: è il TRIGGER.** E il commento sopra la regex
(`temporal_context.py:122`) lo dice già:

> «il» e «l'» ancorano solo perché la regex esige una data subito dopo: **da soli
> sono gli articoli più comuni della lingua.**

## ⑤ Ancora o soggetto: la regex guarda la preposizione, non il verbo

```
ITALIANO — la data è il SOGGETTO (non è una domanda retrospettiva)
  il 18 luglio 2026 quanti fatti sono stati scritti    ANCORA -> 2026-07-18
  cosa e successo il 18 luglio 2026                    ANCORA -> 2026-07-18
  quanti fatti scritti il 18 luglio 2026               ANCORA -> 2026-07-18
  l incidente del 18 luglio 2026                       nessuna ancora
  i fatti scritti 18 luglio 2026                       nessuna ancora
  fatti scritti nel giorno 18 luglio 2026              nessuna ancora

ITALIANO — la data è un'ANCORA (qui il time travel è giusto)
  cosa sapevamo al 18 luglio 2026                      ANCORA -> 2026-07-18

INGLESE — stessa coppia
  how many facts were written on July 18, 2026         ANCORA -> 2026-07-18
  what happened on July 18, 2026                       ANCORA -> 2026-07-18
  how many facts written July 18, 2026                 nessuna ancora
  what did we know as of July 18, 2026                 ANCORA -> 2026-07-18
```

> ⛔ **Ritiro il claim che stavo per scrivere** — *«in italiano è impossibile
> chiedere di una data senza attivare il time travel»*. **È falso**: tre
> formulazioni su sei non ancorano. Si può, **omettendo l'articolo** — cioè
> scrivendo come nessuno scrive.

✅ **E non è un difetto italiano**: `on` in inglese si comporta come `il`.
*«what happened on July 18»* àncora esattamente come *«cosa è successo il 18
luglio»*. **La forma è la stessa nelle due lingue.**

🔑 **Il discrimine non è la preposizione, è il verbo**: «cosa **sapevamo** al…» è
retrospettivo, «cosa **è successo** il…» no. La regex guarda solo la preposizione,
e «il»/«on» introducono entrambe le cose.

📌 **Questa casa ha già pagato una volta su questa stessa regex**, e il commento
lo racconta: `dopo il <data>` ancorava perché in italiano l'ancora è un articolo
e l'articolo segue anche «dopo» — *«la prima stesura di questa cura ha importato
in una lingua il difetto che nell'altra era escluso per costruzione»*. La cura fu
un lookbehind. **`il` da solo è rimasto.**

## ⑥ La terza faccia dell'`out` vuoto

Oggi alle **19:28** il pezzo (i) della CURA-PAVIMENTO è entrato in `main`
(`87a4aac7`): l'avviso ora esce **anche quando la soglia ha tagliato tutti** i
risultati. Il commit dichiara, giustamente, che gli `out` vuoti sono due:

> *«DUE `out` vuoti, DUE significati … `_best_prima` è `0.0` quando la ricerca
> non ha trovato NULLA ed è `> 0` quando qualcosa c'era ed è stato tagliato»*

**Sono tre.** Misurato alla porta del prodotto, col controllo positivo acceso
nella stessa esecuzione:

| caso | n | avviso |
|---|---|---|
| **A** — il filtro **temporale** ha scartato tutto | 0 | **NESSUNO** |
| **B** — stessa domanda, routing spento | 6 | nessuno *(e non serve: best sopra il pavimento)* |
| **C** — la **soglia** ha tagliato tutto *(controllo positivo)* | 0 | `tagliati=6 best=0.882 soglia=0.99` |
| **D** — niente di rilevante, non tagliato | 6 | `tagliati=0 best=0.844 soglia=0.8781` |

La condizione dell'avviso è `if _soglia and _n_prima and _best_prima < _soglia`.
Nel caso A `recall_as_of` **ha già restituito zero hit**, quindi `_n_prima` vale
`0` e la condizione è falsa. ⇒ **Il chiamante riceve una risposta vuota e non
sa perché**, che è esattamente il difetto che il pezzo (i) andava a chiudere —
per l'altra porta.

## ⑦ Che cosa è provato e che cosa no

✅ **Provato**: l'A/B a quattro bracci (§①) · la catena nel codice (§②, righe
citate) · `3/16` retrospettivi spenti contro `0/15` contemporanei (§③) · le tre
letture spente erano al **rango 1** · `2/25` contro `0/25` sui superseduti (§④) ·
le sedici formulazioni di §⑤ · il silenzio del caso A **con il controllo positivo
acceso nella stessa esecuzione** (§⑥).

❌ **Non provato — la frequenza nel traffico reale.** Il journal
(`events.jsonl` + `.jsonl.1`, entrambe le parti) **non registra il testo delle
query**: `0` righe con un campo interrogabile. Non so quante letture vere
contengano una data, quindi **non do una quota sul traffico**.

⚠️ **Il campione è piccolo**: `3/16` ha un intervallo di Wilson al 95% di circa
**6,6%–43,0%**. La direzione regge, la cifra no — chi la cita citi l'intervallo.

⚠️ **Popolazione selezionata da me**: fatti il cui testo contiene una data in
forma «D mese AAAA». Domande costruite dal testo del fatto, che è la forma **più
favorevole** (frammento → 100% nel [55](55-non-e-la-forma-della-domanda-e-il-vocabolario.md)). Con domande formulate a mano il caso
iniziale rendeva **zero risultati**, che nel campione non è mai accaduto (`0/31`).

## ⑧ Gli errori miei di questo giro

| errore | come è saltato fuori |
|---|---|
| `substr(created_at,1,10)` su un campo **epoch** → «0 fatti scritti» in tutti e quattro i giorni, compreso uno in cui ne abbiamo scritti 1029 | il numero impossibile |
| il banco aveva **tre** stati e non quattro: «lo accende il routing» finiva fra i persi | riletto prima di eseguire |
| denominatore **31** invece di **16** | il presidio del `66`, applicato stavolta *prima* |
| *«in italiano è impossibile chiedere di una data senza time travel»* | tre formulazioni su sei lo falsificano |
| `logging.basicConfig` **no-op** (il logging era già configurato): il controllo positivo taceva e stavo per leggerlo come conferma | il controllo positivo che non si accende |

🪞 L'ultimo è il più istruttivo: **il caso C esisteva nel banco proprio per
questo.** Senza un controllo che *deve* accendersi, il silenzio del caso A
sarebbe stato indistinguibile da un misuratore rotto — ed era rotto.

---
*Banco: `banchi/ws6-la-data-nella-domanda.py`. Store di Aurelio in sola lettura;
nessuna modifica al prodotto.*
