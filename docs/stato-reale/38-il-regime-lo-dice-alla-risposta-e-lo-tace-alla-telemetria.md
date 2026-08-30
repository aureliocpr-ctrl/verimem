# Il regime lo dice alla risposta e lo tace alla telemetria

*ws6/Aldo — 30/08, sera. Perimetro: archivio, memoria, corpus, recall.*

Nel documento 37 ho lasciato una domanda con dentro un dato: se in una giornata
intera di lavoro non ho mai avuto una finestra a caldo stabile, **quanto spesso
il prodotto risponde in regime degradato a chi lo usa davvero?** Scrivevo, alla
lettera, «non l'ho contato». Questo pezzo è il conteggio. Il numero è arrivato,
ma la cosa che vale è quello che ho trovato mentre lo cercavo.

## Il regime non è registrato da nessuna parte

Il prodotto ha un giornale degli eventi, `~/.engram/events.jsonl` (che **ruota**:
va letto insieme a `.1`, e questa è una trappola che la nostra memoria registra
da tempo). Sono **37.312 righe** e **quattordici tipi di evento**. Le letture
stanno in `flow.recall`: **3.509**.

Ho cercato in tutte e 37.312 le righe qualunque traccia del regime — `ranking`,
`degraded`, `rerank`, `keyword`, `fusion`, `timeout`:

    zero occorrenze.

Non è che sia registrato male: **non è registrato**. Un evento `flow.recall`
porta questo e nient'altro:

```json
{"name": "flow.recall", "payload": {"surface": "unknown", "store": "67712a7ceb5e",
 "build": "48d9165e", "kind": "search", "n": 3, "best": 0.0}, "ts": 1788114905.81}
```

La superficie, lo store, la build, il tipo di chiamata, quanti risultati, e il
punteggio migliore. Non c'è scritto se quella risposta è stata prodotta dalla
somiglianza semantica o dal ripiego lessicale.

Il punto non è che manchi un campo. Il punto è **dove** manca. Quando il
prodotto risponde in regime degradato **lo dice a chi legge la risposta**: ogni
elemento restituito porta `ranking: "keyword"`, e c'è persino una guardia in
`verimem/client.py` che disattiva il pavimento di rilevanza in quel regime,
perché applicarlo sarebbe un errore di categoria (documento 37). Il prodotto,
quindi, **sa** di essere degradato, **e lo dichiara**. Solo che lo dichiara
all'utente singolo, nell'istante singolo, e non lo scrive dove qualcuno
potrebbe contarlo.

**Visibile a chi guarda una risposta. Invisibile a chi ne misura mille.**

## E l'astensione invece sì — su tre porte su quattro

Il confronto che rende la cosa netta. Ci sono quattro punti nel codice che
emettono `flow.recall`:

| punto di emissione | `kind` | registra `abstained`? |
|---|---|---|
| `verimem/client.py:1885` | `explain` | sì |
| `verimem/gateway.py:1237` | `answer` | sì |
| `verimem/gateway.py:1268` | `correct` | sì |
| **`verimem/client.py:1229`** | **`search`** | **no — solo `n` e `best`** |

Nel giornale reale la parola `abstained` compare **186 volte** nel file corrente
e **354** nel ruotato. Il prodotto sa dire «mi sono astenuto». Non sa dire «ho
risposto senza semantica». E `verimem/flow_tail.py:61` stampa `ABSTAIN` sulla
superficie live: quel cruscotto **non potrà mai** mostrare il degrado, perché il
dato non esiste a monte.

La porta che non registra è la più usata: le chiamate `kind=search` con almeno
un risultato sono **2.841 sulle 3.509 totali**, l'**81%**.

Astensione e degrado non sono due dettagli scollegati: sono i due stati che il
pavimento di rilevanza mette in relazione. Il pavimento *produce* l'astensione,
e nel degradato *viene disattivato*. Registriamo l'effetto e non la condizione
che lo sopprime.

## Il numero, con il suo proxy dichiarato

Un modo indiretto per contare c'è, e l'ho usato: nel ramo degradato il punteggio
vale zero per costruzione. Quindi `best = 0.0` con almeno un risultato è la
**firma** del regime keyword. È un proxy, non una misura, e lo dichiaro come
tale.

Su **2.841** chiamate `kind=search`:

| finestra | recall | con punteggio zero | quota |
|---|---|---|---|
| 21-28/08 | 2.367 | 0 | **0,0%** |
| 29/08 | 92 | 1 | 1,1% |
| **30/08** | 382 | 134 | **35,1%** |
| **totale** | **2.841** | **135** | **4,8%** |

Il 4,8% complessivo è un numero che inganna: mescola due ere. La lettura vera è
che per una settimana il degrado **non si è mai visto**, e oggi è un terzo delle
letture.

## Poi ho sbagliato tre volte, e le tre volte contano

**Primo.** Il mio secondo script contava i degradati con
`float(p.get("best") or 0.0) == 0.0`. Ma le chiamate `kind=explain` **non
portano affatto il campo `best`**: quel `or 0.0` ha trasformato *campo assente*
in *punteggio zero*, e mi ha prodotto **279 degradati che non esistono**. La
nostra memoria ha una lezione intitolata «una misura che non c'è si legge come
perfetta». Questa è la stessa lezione al rovescio: **un campo assente si legge
come guasto**. La cura è identica — pretendere che l'assenza sia una categoria
esplicita, mai un valore di comodo.

**Secondo.** Il primo script, che su questo era corretto, teneva però `explain`
nel **denominatore**: 3.120 invece di 2.841. Diluiva la quota di un dieci per
cento. Due script di fila, due difetti nel misuratore, nessuno dei due nel
prodotto.

**Terzo, e il più istruttivo.** Vista la bimodalità — due build al **100%** di
degrado e altre a **0%** — ho formulato l'ipotesi che sembrava ovvia: il degrado
è il *cold start*, un processo che vive poco muore prima che l'embedder si
carichi. Le due build al 100% erano infatti **i miei due banchi di stasera**,
vissuti **1,2 minuti** ciascuno (`fe82c986`, 60 recall su 60 degradate;
`4651182b`, 61 su 61). Tornava tutto.

Ho misurato la relazione invece di dedurla da quattro punti, e **i dati l'hanno
falsificata**:

| build | durata | recall | degradate |
|---|---|---|---|
| `73811acb` | 0,5 min | 255 | **0,0%** |
| `82a724a4` | **1,0 min** | **654** | **0,0%** |
| `fe82c986` | 1,2 min | 60 | **100%** |
| `ecda4655` | 2,9 min | 1.166 | 0,0% |
| `6caedd08` | 4,8 min | 48 | 14,6% |
| `11e98bc8` | 19,4 min | 189 | 2,1% |

Processi **più corti dei miei**, con **dieci volte le query**, non degradano
mai. In aggregato: processi sotto i 3 minuti **5,2%**, processi sopra i 10
minuti **1,9%** — nessuna relazione. Conclusi che l'ipotesi fosse morta.

**Quarto: la falsificazione era rotta, e l'ipotesi era giusta.** La colonna
«durata» qui sopra non è la vita del processo: è `max(ts) − min(ts)` degli
eventi di lettura. Sono due cose diverse. Un processo avviato molto prima, con
il modello **già caldo**, che serve 654 letture in un minuto, mostra esattamente
lo stesso «span» di un processo appena nato che ne serve 60 a freddo. **Ho
falsificato l'ipotesi giusta con un proxy che non misurava la variabile.** Il
sospetto non nasce da un ripensamento: me l'ha detto il prodotto, sotto.

## La causa c'era, e me l'ha detta la porta di scrittura

Mentre salvavo i fatti di questo stesso documento, la ricevuta di
`verimem save` ha stampato, in chiaro:

    store: encode delegate unavailable → il fatto viene scritto SENZA embedding
    (recall keyword finché il daemon non torna)

e, sul moat:

    entailment moat did not run for THIS write. The model is already on disk:
    `verimem warmup` would not help. A shared encode daemon is what makes the
    first write judged — `verimem doctor` says whether one is reachable

Ho eseguito `verimem doctor`, che conferma:

    ! daemon  no shared encode daemon — first encode in each process
              cold-loads the model (~20s)
        fix: run `verimem warmup` once

**Quindi la causa del regime degradato è nota, ed è una sola: non esiste un
daemon di encoding condiviso, e ogni processo deve caricare il modello a freddo,
circa venti secondi.** In quella finestra le letture escono in keyword, le
scritture entrano senza embedding e il moat non gira — i tre fatti che ho
salvato per questo documento sono infatti `admitted` ma **`model_claim` non
giudicati** (`grounding_score=None`), e lo dichiaro qui perché è la stessa causa.

## Il reperto vero: la stessa informazione, esplicita da una porta e assente dall'altra

Il gap non è che il prodotto ignori il proprio degrado. È il contrario, ed è
peggio:

- **Alla porta di scrittura** il prodotto dice *che* è degradato, *perché*
  (`encode delegate unavailable`), *cosa comporta* (`recall keyword`), *fino a
  quando* (`finché il daemon non torna`) e *quale strumento lo verifica*
  (`verimem doctor`). Quattro informazioni e una cura, non richieste.
- **Alla porta di lettura** — l'81% del traffico — non registra nemmeno il
  fatto nudo che stia succedendo.

Un'ora di lavoro per misurare col proxy `best=0` una cosa che il prodotto
scrive in chiaro a ogni salvataggio. La nostra memoria ha una lezione del 27/08
intitolata *«il prodotto lo diceva già e non lo eseguivamo»*: `verimem doctor`
aveva impiegato venti secondi per dire quello che cercavo a mano da un'ora.
**Ci sono ricascato oggi, sullo stesso strumento.** La lezione non mancava:
mancava l'applicazione — che è, alla lettera, la regola M4.

Resta vero, e va corretto in codice da chi possiede quella porta, che
`client.py:1229` non registri il regime: senza quel campo la domanda «quanto
spesso, e quando» resta senza risposta **nella telemetria**, anche adesso che la
causa è nota.

## Per chi riprende

- Il campo da aggiungere è uno solo, in `verimem/client.py:1229`, ed è già
  calcolato lì accanto: il ramo degradato è noto alla funzione che emette
  l'evento. **Non l'ho fatto**: è la porta di lettura, non è mia, e una
  scrittura sulla telemetria va decisa collegialmente.
- Il proxy `best=0` resta valido **solo su `kind=search`**, e **solo
  distinguendo il campo assente dal valore zero**. Chi lo riusa senza questa
  distinzione ottiene il mio 279.
- La curva durata/degrado **non falsifica il cold start**: la colonna misura lo
  span degli eventi, non l'età del processo. Per rifarla serve l'istante di
  avvio, che il journal non porta.
- **Prima di misurare il degrado, esegui `verimem warmup` e verifica con
  `verimem doctor`.** Un banco lanciato senza daemon misura il proprio cold
  start e lo scambia per una proprietà del prodotto — è quello che ho fatto io,
  qui e nel documento 37.
- `verimem doctor` ha segnalato, non richiesto, altri due reperti nel mio
  perimetro che **non ho ancora verificato**: **278 vettori su 16.308 non
  combaciano con il motore e sono «stored but unreachable by semantic search»**,
  e il *topic-crowding* (**1204 su 1724** sopravvivono sui topic già usati,
  contro **1020 su 1125** sui topic usati una volta sola). Il secondo conferma
  dal lato del prodotto la regola «un topic per misura» che avevamo derivato
  dai nostri incidenti.

---

**Verifica**: journal `~/.engram/events.jsonl` + `events.jsonl.1`, 37.312 righe,
letto in sola lettura. Ricerca del regime: `grep -o` per sei stringhe, zero
occorrenze. Punti di emissione: `git grep -n '"flow.recall"'` escludendo
`tests/`.
