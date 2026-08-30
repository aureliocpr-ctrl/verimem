# Il prodotto avvisa a ogni scrittura da un mese, e l'inerzia è nostra

*ws6/Aldo — 31/08, notte. Perimetro: archivio, memoria, quarantena.*

Ho passato la notte a documentare capacità che il prodotto ha e non usa. Questo
pezzo è il rovescio, e lo scrivo perché senza di esso la serie mente per
omissione: **c'è un avviso che il prodotto ci dà a ogni singola scrittura, da
circa un mese, e nessuno di noi ha fatto niente.**

L'ho trovato per caso, in fondo alla ricevuta di un fatto che stavo salvando:

    REVIEW_BACKPRESSURE — 1272 facts are waiting in the quarantine/review
    backlog (threshold 500), 357 of them in the last 7 days — this write
    joins them
       drain the backlog — `verimem facts quarantine-log` to see it,
       `verimem facts requalify-quarantined` (dry run by default) to
       re-admit what a …

## I numeri

Alle **23:14:20 del 30/08**, con la stessa query che il prodotto usa
(`review_queue.py:78-80`: `status='quarantined' AND superseded_by IS NULL`):

    backlog: 1.272        soglia: 500        →  2,5 volte la soglia
    quarantinati totali: 2.621
    usciti dalla coda (superati da un fatto nuovo): 1.349

**Il meccanismo di uscita funziona**: più della metà dei fatti mai quarantinati
è già uscita dalla coda, perché un fatto successivo ha risposto al loro posto.
Non è un buco che non drena mai.

Ma la coda che resta è sopra soglia **da circa un mese**: il cinquecentesimo
fatto ancora in attesa risale al **1º agosto, ore 21:10**.

| mese di creazione | in coda oggi |
|---|---|
| 2026-05 | 384 |
| 2026-06 | 22 |
| 2026-07 | 74 |
| **2026-08** | **792** |

**Agosto vale il 62% della coda.** È il mese in cui abbiamo lavorato di più — e
in cui abbiamo scritto di più senza rileggere quello che veniva trattenuto.

## Perché questo pezzo è diverso dagli altri

La sintesi del documento 47 dice che il difetto ricorrente è *«il prodotto sa
fare la cosa e non la fa, e nulla segnala che non la sta facendo»*.

**Qui non è così, ed è il contrario:**

- il prodotto **conta** il backlog a ogni scrittura;
- **lo dichiara** con il numero, la soglia e quanti sono entrati negli ultimi
  sette giorni;
- dice **che quella scrittura si sta unendo a loro** (*«this write joins them»*);
- e indica **i due comandi** per guardarlo e per drenarlo.

Non manca un segnale. **Manca un lettore.** In una notte in cui ho salvato
cinquanta fatti, quell'avviso mi è passato sotto gli occhi ogni volta, e l'ho
letto solo quando un fatto è stato quarantinato per un altro motivo.

Va detto con chiarezza, perché è la cosa più facile da non dire: **su questo
punto il prodotto si comporta come vorremmo che si comportasse, e i lenti siamo
noi.**

## Cosa non ho fatto, e perché

**Non ho eseguito `verimem facts requalify-quarantined`**, nemmeno nella sua
forma `dry run`. Drenare la coda di revisione significa decidere quali fatti
trattenuti tornano a essere serviti come veri: è una decisione sul contenuto
della memoria di Aurelio, non una misura, e non mi è stata chiesta.

Quello che si può dire dai numeri è dove guardare per primo: **792 dei 1.272
sono di agosto**, e agosto è il mese di cui ricordiamo il contesto. La parte
vecchia (480 fatti fra maggio e luglio) è archeologia e costerà di più
giudicarla.

## Per chi riprende

- La coda si guarda con `verimem facts quarantine-log`, e la sua profondità è
  `SELECT COUNT(*) FROM facts WHERE status='quarantined' AND superseded_by IS
  NULL`.
- La soglia è configurabile (`ENGRAM_REVIEW_QUEUE_MAX`), e il codice dichiara
  una cosa che merita di essere copiata altrove: *«a malformed or negative value
  falls back to the default: **a typo must not silently switch an alarm off**.
  Only an explicit `0` does that»*. **È l'esatto opposto del difetto del
  documento 48**, dove un valore degenere ha spento un presidio senza dirlo.
- **Quello che non ho misurato**: quanti dei 1.272 passerebbero una
  riqualificazione. Lo direbbe il `dry run`, che è sicuro — ma è un'azione sulla
  memoria e la lascio a chi ha il mandato.

---

**Verifica**: `~/.engram/semantic/semantic.db` in `mode=ro`, sole `SELECT`, con
la stessa condizione usata da `verimem/review_queue.py:78-80`. Istante 23:14:20
del 30/08. Nessun `requalify`, nemmeno in dry run.
