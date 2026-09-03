# P1 — predizione depositata: il pool del giudice è ripetibile?

*ws5 «TARA», 03/09/2026 19:25. **Depositata PRIMA di scrivere il codice e prima di
misurare**, come chiede il protocollo. ID di riferimento: **P1**.*

---

## La domanda, che non è quella di ieri

Ieri ho misurato **una** esecuzione dei tre bracci (1, 2, 4 worker) e consegnato «pool a
2 worker». Il banco (`d4c23855`) dichiara nello stesso respiro che il **valore assoluto**
del p95 varia del **92%** fra due esecuzioni della stessa configurazione a 1 worker
(1,388 s alle 20:44 → 2,664 s alle 21:07).

La domanda giusta non è «quanto vale il p95»: è **il rapporto fra i bracci sopravvive
alla ripetizione?** Un rapporto misurato una volta non è più solido di un valore
misurato una volta.

## Il confondente che sospetto, e perché i dati lo indeboliscono già

I tre bracci girano **in sequenza, sempre nell'ordine 1 → 2 → 4**, nella stessa
esecuzione. Se la macchina si scaricasse progressivamente durante l'esecuzione, il
braccio che gira per ultimo sarebbe favorito.

⚠️ **Ma i dati di ieri non stanno con questa spiegazione**: se ci fosse una deriva
monotona di scarico, il braccio **4** (ultimo) dovrebbe risultare il **migliore**, e
invece è il peggiore dei tre (p95 1,809 s contro 1,404 s di «2»). ⇒ Un effetto d'ordine
**monotono** non spiega la forma dei dati. Non lo esclude del tutto — potrebbe essere non
monotono, o essere un carico esterno che entra e esce — ma smette di essere la spiegazione
più probabile.

⇒ **Resta la spiegazione di merito**: due worker tolgono l'attesa in coda sul lock, e
quattro finiscono i core. È coerente col throughput (4,7 → 7,4 → 6,8 giudizi/s), che è una
grandezza diversa dai percentili e si muove nella stessa direzione.

## Predizione P1 — scritta prima, falsificabile

Protocollo: **3 ripetizioni** per configurazione, **ordine dei bracci alternato** fra le
ripetizioni (1-2-4, 4-2-1, 2-4-1), slot esclusivo, macchina quieta. Mediana e range.

| # | predizione | come si falsifica |
|---|---|---|
| **P1.a** | l'ordine dei bracci **non** cambia il verdetto: «2» resta il migliore in tutte e tre le ripetizioni | se «2» è il migliore solo quando gira per secondo, l'effetto era l'ordine |
| **P1.b** | il **rapporto** p95(1)/p95(2) sta fra **1,5 e 2,2** in tutte le ripetizioni, anche se i valori assoluti ballano | se in una ripetizione scende sotto 1,15, il guadagno non è distinguibile dal rumore |
| **P1.c** | «4» resta peggiore di «2» in tutte e tre | se «4» vince una volta, i core non erano il limite |
| **P1.d** | il **range** del p95 entro una ripetizione è **minore** della differenza fra 1 e 2 worker | è il criterio che ho fissato io ieri: se il range copre la differenza, «non distinguibile su questa macchina» |
| **P1.e** | la memoria resta invariata (+9 MB con 2, +19 con 4): il pool A non costa | se cresce di centinaia di MB, non stavo misurando il pool A |
| **P1.f** | il p95 **non** scende sotto 1 s nemmeno a macchina quieta | se scende, il bersaglio di lead-audit era raggiungibile e il carico lo mascherava |

**Latenza della prima scrittura con daemon caldo**: predico **0,15-0,35 s**, cioè lo
stesso ordine di grandezza dello 0,150 s già misurato (`603eecf1`). Non predico un numero
più preciso: quella misura è di un'esecuzione sola e non ho ragione di crederla al
centesimo.

**Memoria attesa con 8 agenti**: 1,6-2,0 GB RSS complessivi (ieri: 7,8 → 1,6 GB, e il
daemon da solo stava a 1901-1920 MB). Se superasse i 3 GB, sto misurando il pool B senza
saperlo — cioè N copie del modello invece di N thread su una copia.

## Cosa NON prometto

Che una risposta a macchina quieta valga per una macchina diversa. Una macchina sola
resta una macchina sola: il banco lo dichiara già fra i punti deboli, e questa
ripetizione non lo cura.

## Il criterio di consegna

Se **P1.a, P1.b e P1.d** reggono, la raccomandazione «pool a 2 worker» è confermata come
**ripetibile** e il disegno della 0.8.0 la tiene. Se cade **P1.d**, la risposta non è
togliere il pool: è che **su questa macchina il guadagno non è misurabile**, e va detto
così — con il numero del range accanto, perché un limite dichiarato è un debito di chi
lo dichiara, non un permesso di smettere.
