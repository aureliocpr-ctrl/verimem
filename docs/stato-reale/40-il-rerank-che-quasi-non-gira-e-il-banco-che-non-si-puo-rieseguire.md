# Il rerank che quasi non gira, e il banco che non si può rieseguire

*ws6/Aldo — 30/08, notte. Perimetro: archivio, memoria, corpus, recall.*

Ci sono arrivato per caso. Interrogavo la memoria su un'altra cosa e la risposta
è tornata con un campo che il documento 37 mi ha insegnato a leggere **prima**
dei punteggi:

```json
"ranking": { "rerank": "skipped_long_query", "fusion": "timeout" }
```

`skipped_long_query`. La mia domanda era troppo lunga perché il cross-encoder
venisse eseguito. Sono andato a vedere quanto lunga.

## La soglia, e perché esiste

`verimem/semantic.py:4537`: in modo `auto`, se la query supera
`_rerank_auto_max_words()` il rerank viene saltato **prima di caricare il
modello**. La soglia di default è **10 parole**.

Il primo istinto è chiamarlo difetto. Sarebbe sbagliato: è la decisione meglio
documentata che abbia incontrato in questo prodotto. Il docstring di
`_rerank_mode` (`semantic.py:1715`) la motiva così, e vale la pena leggerlo per
intero:

- il default fu **ON** dal 10/06, con evidenza reale — *«short paraphrase
  probes, R@1 0.533 → 0.683, p=0.00052 … n=120»*;
- ma quel banco, dice il prodotto stesso, *«sampled only the CE-friendly
  regime»*;
- sul traffico reale (304 query, GT del 26/07) **l'effetto aggregato è nullo**:
  ΔMRR +0,0078, p=0,716;
- e il nullo **non è assenza di effetto**: sono due effetti reali che si
  annullano. Le query **corte/pinpoint guadagnano +0,146 MRR** (47 meglio / 16
  peggio); le **lunghe perdono 0,080** (12 meglio / 38 peggio);
- la soglia regge allo split-half — *«a length-gated policy chosen on either
  half beats both pure modes on the other half — same threshold (≤9 words)
  picked independently by both, wide plateau (10-16)»*;
- e l'always-ON *«costs +2067 ms on EVERY query»*.

Numeri, test statistico, controllo di robustezza, costo, e una manopola
d'ambiente invece di una costante. **Questo è come si prende una decisione.**

## Quanto spesso si attiva, davvero

Il docstring contiene anche il numero che serve per rispondere: la **mediana
delle 304 query reali è 16 parole**. La soglia è 10.

Volevo il dato su query vere, non su un proxy. Il banco del prodotto ne ha 120,
in italiano fluente, costruite come parafrasi dei fatti. Le ho misurate con
`_query_word_count` **del prodotto**, non con una mia versione:

```
query del banco del prodotto (IT fluente): 120
soglia AUTO del rerank: 10 parole
parole per query: mediana 20.0   min 11   max 26
QUERY SOPRA LA SOGLIA: 120 su 120 = 100.0%
```

**Centoventi su centoventi.** La più corta dell'intero banco ne ha **undici**:
una sola parola oltre il limite. Nella distribuzione non esiste nemmeno una
query sotto soglia.

Quindi, su questo tipo di traffico, **il cross-encoder non viene eseguito mai**.
E — questo è il punto che va detto con precisione — **è esattamente ciò che la
cura vuole ottenere**: la mediana reale è 16, il prodotto sa di saltare la
maggioranza dei casi, e lo fa perché lì il CE misurabilmente peggiora. Non è un
effetto collaterale: è lo scopo.

Resta però un fatto di prodotto che vale la pena guardare in faccia: **si
spedisce un modello cross-encoder, con il suo peso e il suo caricamento, per
servire la coda corta del traffico.** Non è un difetto — è un dato per chi
decide cosa mettere nella scatola.

## Il difetto vero: l'evidenza non è rieseguibile

Il docstring di `_rerank_auto_max_words` chiude con un invito esplicito:

> *«Derived from ONE corpus (n=304, one user) — which is why it is an env knob
> and not a constant, and **stays falsifiable by a second corpus**.»*

È la frase giusta. Ma chi accetta l'invito trova questo:

| | in `origin/main`? |
|---|---|
| `scripts/bench_rerank_fair.py` | **sì** |
| `scripts/bench_hybrid_fair.py` | **sì** |
| `scripts/bench_hybrid_fair_queries.json` (le 120 query) | **no** |

Il file dei dati è stato aggiunto il **09/06/2026** dal commit `2f92d9e5`, che
**non è antenato di `origin/main`**: vive solo su rami feature mai integrati
(`feat/ppr-fact-ranking`, `feat/episode-telemetry-separation`, e altri). Ho
potuto misurare le 120 query solo estraendole con
`git show 2f92d9e5:scripts/bench_hybrid_fair_queries.json`.

**Due script in main citano un'evidenza numerica i cui dati non sono in main.**
E quell'evidenza non è decorativa: è il `R@1 0.533 → 0.683, p=0.00052` con cui
il docstring giustifica la storia della decisione.

Va detto per intero, perché il prodotto qui si comporta bene: **lo script lo
dichiara**, non fallisce di nascosto.

```python
if not QUERIES_JSON.exists():
    print(f"missing {QUERIES_JSON}")
    return 1
```

Nessun crash, nessun risultato inventato: dice cosa manca ed esce con 1. **Il
difetto non è di onestà, è di riproducibilità** — e riguarda proprio la
falsificazione che il codice chiede.

## Un'ipotesi mia, falsificata

Ero partito da un'altra idea: la soglia è espressa in **parole**, il modello è
multilingue, e l'italiano usa più parole funzionali dell'inglese — quindi
avrebbe dovuto superare la soglia più spesso, a parità di contenuto. Misurato
sul corpus, isolando la lunghezza in caratteri:

| | n | parole (mediana) | sopra soglia |
|---|---|---|---|
| italiano, 100-200 caratteri | 3.270 | 21 | 99,7% |
| inglese, 100-200 caratteri | 137 | 19 | 100,0% |

**Ventuno contro diciannove.** Nessuna penalizzazione linguistica: la previsione
era sbagliata, e i due gruppi finiscono entrambi sopra soglia quasi sempre.

E il caso multilingue serio il prodotto lo aveva già trovato e curato, in un
punto che non avevo guardato: `_query_word_count` conta **un carattere CJK come
una parola**, perché `len(query.split())` leggeva *«una domanda giapponese di 26
caratteri come UNA parola»* e faceva girare il CE proprio nel regime dove
danneggia. Dichiara pure di **sovrastimare** per il coreano spaziato, e che è
una scelta conservativa deliberata.

## Per chi riprende

- **La cosa da fare, ed è quella che il codice chiede**: rieseguire il gate su
  un secondo corpus. Serve prima portare in `main` i dati del banco, o
  rigenerarli con `scripts/bench_hybrid_fair.py`.
- Il righello delle query è
  `docs/stato-reale/banchi/ws6-la-soglia-in-parole-e-la-lingua.py` (sola
  lettura), che usa `_query_word_count` del prodotto.
- **Quello che non ho misurato**: se il guadagno `+0,146 MRR` sulle query corte
  regga sul nostro corpus. Richiede una finestra non degradata e una ground
  truth nostra — e la prima, oggi, non l'ho avuta (documenti 37 e 38).

---

**Verifica**: `git ls-files`, `git merge-base --is-ancestor 2f92d9e5
origin/main` (esito: non è antenato), `git show -s --format` (data 2026-06-09).
Query estratte da `git show`, misurate con `verimem.semantic._query_word_count`.
Corpus letto `mode=ro`, sole `SELECT`.
