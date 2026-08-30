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
minuti **1,9%** — nessuna relazione. L'ipotesi è morta, ed è giusto così.

## Quello che non posso dire, e perché

Non so **perché** i miei due banchi di stasera abbiano risposto degradato per
tutta la loro vita mentre un processo di un minuto ne serviva 654 senza
degradare mai. Ho dei candidati — costo della singola query, dimensione del
corpus interrogato, carico della macchina con otto istanze in parallelo — e
**nessun modo di sceglierne uno**, perché il giornale non registra la latenza,
non registra il regime, non registra la dimensione del corpus.

Ed è esattamente il punto di questo pezzo. La domanda «quanto spesso rispondiamo
degradato, e in quali condizioni?» è la domanda che un cliente farebbe per
prima, ed è **legittima, semplice e senza risposta nei dati che raccogliamo**.
Il proxy che ho trovato per caso dà il numero e non dà la causa.

Il gap non è nel motore. È nel fatto che l'unica cosa che il prodotto sa sul
proprio degrado la dice una volta sola, a una persona sola, e poi la butta via.

## Per chi riprende

- Il campo da aggiungere è uno solo, in `verimem/client.py:1229`, ed è già
  calcolato lì accanto: il ramo degradato è noto alla funzione che emette
  l'evento. **Non l'ho fatto**: è la porta di lettura, non è mia, e una
  scrittura sulla telemetria va decisa collegialmente.
- Il proxy `best=0` resta valido **solo su `kind=search`**, e **solo
  distinguendo il campo assente dal valore zero**. Chi lo riusa senza questa
  distinzione ottiene il mio 279.
- La curva durata/degrado è misurata e **non spiega**: non ripercorretela.

---

**Verifica**: journal `~/.engram/events.jsonl` + `events.jsonl.1`, 37.312 righe,
letto in sola lettura. Ricerca del regime: `grep -o` per sei stringhe, zero
occorrenze. Punti di emissione: `git grep -n '"flow.recall"'` escludendo
`tests/`.
