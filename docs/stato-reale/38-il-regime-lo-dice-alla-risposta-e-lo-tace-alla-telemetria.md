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

**Quarto: la falsificazione era rotta.** La colonna «durata» qui sopra non è la
vita del processo: è `max(ts) − min(ts)` degli eventi di lettura. Sono due cose
diverse. Un processo avviato molto prima, con il modello **già caldo**, che
serve 654 letture in un minuto, mostra esattamente lo stesso «span» di un
processo appena nato che ne serve 60 a freddo. **Il proxy non misurava la
variabile**, quindi quella tabella non falsifica niente — né in un senso né
nell'altro.

*(Per un'ora ho scritto qui che «l'ipotesi era giusta» e che il degrado fosse un
cold start. **Non lo è**: vedi la sezione sulla congiunzione, più sotto. La
variabile che conta è la presenza del daemon, e il cold start non c'entra —
perché in questo ambiente il caricamento a freddo **non è nemmeno permesso**.)*

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

Da qui avevo concluso che la causa fosse una sola — nessun daemon condiviso,
ogni processo carica il modello a freddo in una ventina di secondi — e che la
cura fosse `verimem warmup`. **L'ho scritto qui e l'ho mandato al canale. Era
incompleto, e la metà che mancava ribalta la cura.**

### La causa è una congiunzione, e la seconda metà sta nel codice

Me l'ha segnalata **ws1**, e l'ho verificata prima di riscriverla.
`verimem/embedding.py:283-286`:

```python
if _delegate_only() and not is_loaded():
    raise EncodeDelegateUnavailable(
        "encode daemon unavailable and in-process cold-load is disabled "
        "(HIPPO_ENCODE_DELEGATE_ONLY=1) — caller must degrade"
    )
```

e nel mio processo `HIPPO_ENCODE_DELEGATE_ONLY` vale `1`.

**Quindi non c'è nessun cold start.** Senza daemon la funzione non carica il
modello lentamente: **solleva**, e il chiamante degrada. Non «venti secondi e
poi va» — **degradato finché il daemon non torna**, per tutta la vita del
processo. La causa è la congiunzione di due condizioni: **daemon assente E
caricamento locale vietato**. Nessuna delle due, da sola, spiega perché non si
recuperi dopo venti secondi.

Questo chiude anche la faccenda della tabella qui sopra: i processi che non
degradavano mai non erano «più caldi», **avevano il daemon vivo**; i miei
avevano il daemon morto e nessuna via di riserva.

**E allora il presidio dichiara un fallback che l'ambiente proibisce.** La riga
di `verimem doctor` — *«first encode in each process cold-loads the model
(~20s)»* — **è falsa in questo ambiente**, e il doctor non legge la variabile
che decide il comportamento che sta descrivendo. È lo stesso difetto che questo
documento contesta alla telemetria, in un altro punto del prodotto: **una
dichiarazione che non guarda lo stato di cui parla.**

**Sesto difetto mio**: quella riga l'ho ripetuta — nel documento e al canale —
**senza aprire il codice**. Un referto è un claim come un altro, e la regola che
applico agli altri («output del modello = claim finché non verificato») vale
anche quando il claim viene dal prodotto.

Va aggiunto, come misura di ws1 e non mia, che **il daemon è intermittente**:
verde alle 18:11 e alle 20:16, rosso alle 20:37 e alle 20:5x. Quindi
**`verimem warmup` una volta non basta**: se il daemon muore si torna degradati
senza che nessuno se ne accorga — la cura è un presidio, non un comando. E ws1
dichiara anche ciò che non torna, che riporto senza chiudere il cerchio a forza:
**togliendo quella variabile l'embedding non è tornato** (timeout 180 s). La
congiunzione spiega il degrado, non spiega quel test. Manca un pezzo.

Resta vero che in quella finestra le scritture entrano senza embedding e il moat
non gira: i tre fatti che avevo salvato per questo documento sono `admitted` ma
**`model_claim` non giudicati** (`grounding_score=None`), ed è la stessa causa.

### E poi il daemon è tornato, mentre guardavo

La ricevuta non promette solo il danno: promette anche la fine del danno —
*«recall keyword **finché il daemon non torna**»*. Ho potuto osservare tutte e
due, per caso, in dodici minuti. Tre istanti, con il prodotto come unico
testimone:

| ora | chi | referto |
|---|---|---|
| **20:53** | `verimem doctor` | `16030 vectors match the engine and 278 do not … 768d: 16030 · 0d: 278`, e `expected dimension NOT known here — **no encode daemon is running** to declare it` |
| **21:02** | il mio banco, che replica `doctor.py:791-804` sullo stesso file | **16.317 vettori, tutti a 768d, zero «0d»** |
| **21:05** | `verimem doctor` | `✓ all 16322 vectors match the engine in use (768d: 16322); expected 768 (**from the running encode daemon**)` |

Il daemon è passato da assente a presente, e i **278 vettori vuoti sono stati
completati**. Non è un bug del referto e non è un backfill che ho ordinato io:
**è la riparazione che la ricevuta aveva annunciato, osservata mentre avveniva.**

**Quinto difetto mio, e il più istruttivo dei cinque.** Alle 21:02, vedendo i
miei tre fatti con `LENGTH(embedding) = 3072`, avevo concluso che la ricevuta
dicesse il falso — che l'avviso fosse «più grave del vero», la classe che noi
chiamiamo *«i presidi gridano sul sano»*. Stavo per scriverlo. Era sbagliato:
**avevo misurato dopo la riparazione**. La lezione *«un rapporto senza istante e
finestra inganna»* è nella nostra memoria da settimane; ci sono cascato oggi, e
stavolta il costo sarebbe stato accusare il prodotto di mentire su una promessa
che invece aveva mantenuto.

Quello che resta vero, e va detto per intero: il degrado esiste, ha una causa
sola, **si ripara da solo quando il daemon torna**, e la porta di lettura
continua a non registrare niente di tutto questo.

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
- **Non fidarti di `verimem warmup` come garanzia.** Il daemon è intermittente e
  non c'è caricamento locale di riserva: un banco può partire caldo e finire
  degradato senza segnale. **Leggi il campo `ranking` di ogni risposta e scarta
  le corse degradate**, invece di mediarle — è quello che non ho fatto io, qui e
  nel documento 37.
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
