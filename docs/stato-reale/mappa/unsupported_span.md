# `verimem/unsupported_span.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## Il claim del README

**NESSUNO.**

Cercato nel README con i termini del modulo (`grep -in`) e **nessuna
riga lo copre**. Il claim `README:704` è della famiglia dei detector
L1 e questo file non è uno di quelli: attribuirglielo sarebbe
inventare l'attribuzione — in un documento fatto per collegare i
claim al codice, l'errore peggiore.

⇒ come `ide.py` e `sandbox.py`: **superficie viva fuori dalla
vetrina**. Non è un difetto; è un dato per chi decide che cosa il
prodotto dichiara di essere.

## La copertura di esecuzione

```
perimetro: 51 file di test che nominano i detector L1
copertura: 77.8%
statement non eseguiti: 93, 98, 100
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/unsupported_span.py:86` `split_claim_clauses` | funzione: The proposition's clauses, or a single-element list when it makes one | `verimem/anti_confab_gate.py:2891`; `verimem/anti_confab_gate.py:2892`; `verimem/anti_confab_gate.py:2898` (+3) | `tests/test_l_advice_nomina_la_grandezza_che_ha_contato.py`; `tests/test_unsupported_span.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 3/12 statement del corpo scoperti (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.


---

## Il banco nel merito: nove promesse del docstring, nove confermate

Questo modulo è **il più scoperto dei 30** (77,8%), e le righe non eseguite
sono `93`, `98` e **`100`** — quest'ultima è la guardia che il docstring
descrive per esteso:

> «Short fragments are merged back into the previous clause rather than dropped
> — a dangling ", e i due" is part of what came before, and counting it alone
> **would inflate the number of assertions**.»

Il numero che `split_claim_clauses` produce dice a chi scrive **in quanti pezzi
spezzare** un fatto che il moat ha rifiutato. Se si gonfia, manda a spezzare più
del necessario. Nessun test lo esercita, quindi l'ho esercitato io:

```
OK  A  lista con `e` nudo → UNA clausola          → 1 (atteso 1)
OK  A' lista lunga, sempre una                    → 1 (atteso 1)
OK  B  `mentre` apre una nuova asserzione         → 2 (atteso 2)
OK  B' `perché` idem                              → 2 (atteso 2)
OK  B'' virgola + coordinante                     → 2 (atteso 2)
OK  B'''punto e virgola                           → 2 (atteso 2)
OK  C  frammento corto RIASSORBITO (riga 100)     → 1 (atteso 1)
OK     vuoto → nessuna clausola (riga 93)         → 0 (atteso 0)
OK     solo spazi → nessuna clausola              → 0 (atteso 0)

9 casi · tutte le promesse reggono                              EXIT=0
```

⇒ **il 77,8% non è un buco di comportamento: è un buco di presidio.** Il codice
fa quello che promette — comprese le tre righe scoperte — ma **nessun test lo
custodisce**, e se qualcuno rompesse la riga 100 il conteggio si gonfierebbe in
silenzio. Il banco è pronto in `<scratchpad>/banco_unsupported_span.py`, nove
casi, gira in un secondo: chi vuole promuoverlo a `tests/test_unsupported_span.py`
lo trova lì. **Non lo promuovo io** (regola 2).

## E una cosa che questo modulo insegna, al di là della sua tabella

Il docstring **racconta due cure tentate e fallite**, coi numeri:

- assegnare un punteggio a ogni clausola contro la fonte: **al contrario** —
  `40.6` alla clausola colpevole, `0.1` a quella che la fonte *dimostra*, perché
  la clausola isolata perde il contesto e il CE legge la sovrapposizione
  lessicale;
- l'ablazione (ricalcolare senza ciascuna clausola): **0 su 2**.

E la conclusione: «*pointing at the wrong clause is worse than pointing at none,
because it sends the writer to delete the part that was true*».

📌 È il modulo meglio scritto che ho letto stasera, e la ragione è che **il suo
docstring pubblica i fallimenti con i numeri**, invece di descrivere solo la
soluzione. Chi lo legge sa cosa NON riprovare — che è la stessa funzione della
nostra lista delle strade già falsificate.
