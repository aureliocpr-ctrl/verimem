# M5 e T1.1 — chiusura del 02/09

Due muri portati a termine in giornata, con la predizione depositata **prima** di
ogni esperimento e l'esito riportato anche quando mi ha smentito. Ogni riga qui
sotto ha un comando che la rifà.

---

## M5 — il verificatore decide con le parole

**Baseline unificata.** Le tre forme (numero a parole, parafrasi, lingua) avevano
un banco ciascuna **con casi diversi**: i tre numeri non erano confrontabili. Il
banco le porta sugli stessi sei casi, quattro condizioni scostate dalla canonica
per **una cosa sola**, e **due popolazioni**.

    python docs/stato-reale/banchi/ws3-M5-baseline-le-tre-forme-sugli-stessi-casi.py

| popolazione | forma | falsi passati | veri fermati |
|---|---|---|---|
| copia | tutte e quattro | 0/6 | 0/6 |
| conteggio | canonica | 0/6 | **6/6** |
| conteggio | parola | **4/6** | 0/6 |
| conteggio | parafrasi | 0/6 | 5/6 |
| conteggio | inglese | 0/6 | **6/6** |

**Il reperto**: sulla popolazione dove il numero va **contato**, il gate **non
discrimina** — o ferma tutto (veri inclusi) o non ferma niente. Lo strato
lessicale vede la cifra e blocca ciò che la porta; quando la cifra sparisce si
spegne e resta il solo giudice, che copre 2 casi su 6.
**Non è la lingua e non è la parafrasi**: l'inglese si comporta come l'italiano,
e la parafrasi perde **meno** della forma letterale (5/6 contro 6/6).

**T5.1 — le classi numeriche.** Delle quattro nominate dal mandato, misurate:

    python docs/stato-reale/banchi/ws3-M5-T51-le-tre-classi-numeriche-non-misurate.py

| classe | stato | T5.1 serve? |
|---|---|---|
| separatore decimale | già canonicalizzato (0/6 falsi allarmi) | no — lavoro rifatto |
| migliaia | già canonicalizzato (misura di un'altra istanza) | no |
| notazione scientifica | **6/6 veri fermati** | **sì, ed è l'unica** |
| unità di misura | 6/6, ma è una **conversione** | no — serve aritmetica |
| parola↔cifra | saldo negativo | no (vedi sotto) |

**La cura, e dove NON va messa.** Sul regime *discordante* (fonte in cifra,
claim a parole) i veri fermati **non** sono colpa dello strato a regola: le
ricevute mostrano `grounding 1,36` e `2,17` con `layers=['L4-grounding',
'L4.1-a-parole']` — `L4.1-a-parole` è un **avviso**, lo strato si toglie già di
mezzo, e a fermare è il **giudice**. Nessuna canonicalizzazione lì arriva. E
metà di quella cura **esiste in `main` dal 16/08**
(`valore_non_nella_fonte.py::assenti_che_la_fonte_scrive_a_parole`).

Sulla **notazione scientifica** invece la cura ha oggetto, e le ricevute lo
dicono: tre veri su sei sono `withheld_despite_judge` — il giudice li approva a
**89,91 · 99,37 · 98,45** e lo strato li trattiene da solo.
Implementata sul ramo `ws3/canonicalizzazione-scientifica` (commit `cf11d1a0`,
non su `main`): **veri fermati 6/6 → 3/6, falsi passati 0/6 → 0/6**, i tre
residui sono esattamente quelli dichiarati fuori portata prima di scrivere il
codice. Prima della cura il claim **falso** produceva **gli stessi valori
assenti del vero**: la cura non toglie un controllo, ne aggiunge uno.

---

## T1.1 — un secondo giudice serve?

**Il punto singolo non decideva** (due punti di due curve diverse). A pari veri
persi del gate:

    python docs/stato-reale/banchi/ws3-T11-la-curva-minicheck-contro-il-giudice.py

| | MiniCheck | giudice oggi | gate dichiarato | AUROC |
|---|---|---|---|---|
| TruthfulQA (29,3%) | 72,3% | 87,3% | 86,7% | 0,7932 vs 0,829 |
| HaluEval (19,0%) | 68,0% | 62,0% | 55,0% | 0,7733 vs 0,7555 |

**Verdetto diverso sui due banchi**, e AUROC entro 0,036: i due sistemi
discriminano quasi ugualmente, cambia **dove è messa la soglia**. ⇒ Sostituire
il giudice non compra capacità.

**L'ensemble** (aritmetica sui punteggi già calcolati):

    python docs/stato-reale/banchi/ws3-T11-l-ensemble-dei-due-giudici.py
    python docs/stato-reale/banchi/ws3-T11-la-media-regge-a-tutte-le-soglie.py

La **media semplice** non sta mai sotto il migliore singolo nel punto di lavoro
(87,3% e 72,0%), e lungo la curva **regge in tutta la fascia 20-35%** (+1,0…+4,5).
**Sotto il 15% peggiora, fino a −11 punti**: il giudice doppio **non va tarato
con soglie severe**. La media dei **ranghi** invece cede *dentro* la fascia
operativa su HaluEval (25/30/35%).

**Il costo.** `int8` dinamico **non è utilizzabile**: disco 1740 → 831 MB e
2,1-2,4× di velocità, ma **Spearman 0,628/0,556** e **−30 punti di falsi
fermati** su entrambi i banchi. Gli score si schiacciano in `[0,057-0,314]`
contro `[0,011-0,931]` di fp32 — 23 valori distinti su 24, quindi non degenere:
ha perso la scala.

    python docs/stato-reale/banchi/ws3-T11-il-costo-del-giudice-doppio-int8.py

---

## Le predizioni, e quante ne ho sbagliate

| predizione | esito |
|---|---|
| T5.1: ≥4/6 veri fermati su tutte e tre le classi | **falsa** sul decimale (0/6): già canonicalizzato |
| T5.3: veri persi cross-lingua −≥10 punti | **falsa**: −0,1 punti |
| ensemble: media dei ranghi sotto su TruthfulQA, sopra su HaluEval | **falsa su entrambi**, verso invertito |
| int8: Spearman >0,99, Δ entro ±2 punti | **falsa di due ordini**: 0,63 e −30 |
| M8: contesa col loop asyncio, C ≥ 5×A | **falsa**: 1,03× |
| media a tutte le soglie: ≥ sul 90% | **falsa**: 75% e 83% |
| notazione scientifica: veri 6/6 → 3/6, falsi 0/6 | **confermata**, caso per caso |
| curva: verdetto diverso sui due banchi, AUROC entro 0,05 | **confermata** |

**Sei predizioni su otto sbagliate.** Sono qui perché una predizione depositata
prima e poi smentita vale più di una conclusione scritta dopo aver visto i
numeri — e perché due di quelle smentite (int8, M8) hanno **cambiato la
decisione**: senza, avremmo spedito una quantizzazione che costa 30 punti e una
cura contro una causa inesistente.

## Cosa resta aperto, e non lo riempio

- **L'import costa 30,3 s** in un processo pulito e nel server è *lazy*: cade
  sulla prima richiesta. **Ma 30 s non sono i 240 s** del timeout osservato:
  il divario di un ordine di grandezza **non è spiegato**.
- Su HaluEval il **gate completo (55,0%) è peggiore del suo stesso giudice
  (62,0%)**: sette punti fra il giudice e la porta. Ipotesi con un numero, non
  diagnosi — i due regimi di misura differiscono.
- La **memoria** del giudice doppio non è misurata: il banco teneva i due
  modelli in RAM insieme, quindi quel numero non isola nulla. Servono due
  processi separati.
- `py/overly-large-range` su `quantity_match.py:1353` è il range CJK,
  **intenzionale**: non misurato.

## Una correzione che riguarda tutto il resto

Alle 03:26 avevo «corretto» un commento del prodotto del 05/08 («41 secondi si
spendono in questa riga») misurando **2,4 s** e concludendo che non descrivesse
più il presente. **Ritirata**: i 2,4 s sono il caricamento dei **pesi** con
`transformers` già importato; il commento contava l'intera riga, **import
compreso** — 30,3 + ~11 ≈ 41. I due numeri non si contraddicono: **misurano
cose diverse**, e ho opposto una parte al tutto per diciotto ore.

**Misurare non basta: bisogna misurare la stessa grandezza di ciò che si vuole
confutare.**
