# 19 — La cura del ranking peggiora il caso reale, e il difetto vero è più a monte

**ws6 · 30/08 ore 13:49** · corpus servibile **12.232** fatti, `mode=ro`, sole SELECT.

Il [documento 17](17-la-ricerca-ordina-per-data-non-per-pertinenza.md) si chiude con due cure
candidate e la riga «**la cura NON è misurata**». Una delle due l'ho scritta e consegnata
(l'avviso di ripiego). Questa è l'altra — **ordinare per pertinenza invece che per data** — e
**non va scritta**. Qui c'è il perché, coi numeri che me l'hanno impedito.

---

## La predizione, dichiarata prima di eseguire

> Riordinando i candidati per **numero di token agganciati** invece che per `created_at DESC`, i
> fatti **medi e vecchi** devono risalire **da 0/20 a più di 10/20**.

## Banco A — conferma, e sembrava chiusa

Query = **prime otto parole del fatto** + una parola intrusa che nel fatto non c'è (lo stesso
disegno del [banco P2](banchi/ws6-quanto-costa-una-parola-sbagliata.py)).

```
   fascia   per data  per token  pos.mediana   candidati
   recenti        19         20            0        2394
   medi            0         20            0        1903
   vecchi          0         19            0        4985
```

**Medi 0 → 20 su 20. Vecchi 0 → 19 su 20. Posizione mediana: 0, cioè primi.** Contare i token —
nessun modello, nessun BM25 — sembrava recuperare tutto.

⚠️ **Ma il banco misura il caso favorevole per costruzione**: la query è fatta con le parole del
fatto, quindi il target aggancia **otto token su nove** e vince per forza. È lo stesso errore del
primo disegno di P2 («candidati mediani = 1»), in forma più sottile — e la prima volta me n'ero
accorto, la seconda ci sono ricascato.

## Banco B — il caso realistico, che ribalta tutto

Query = **le parole del `topic`**, che chi salva scrive separatamente dal testo. È come si cerca
davvero: si ricorda l'argomento, non la frase.

```
   fascia    usati  per data  per token   mai candidato   candidati
   recenti      20        14          4               6        1595
   medi         20         0          3               4        2200
   vecchi       20         0          0              18           5
```

**Tre risultati, e nessuno è quello atteso:**

1. 🔴 **Sui fatti recenti il ranking per token PEGGIORA: da 14/20 a 4/20.** La cura danneggia
   proprio il caso che oggi funziona.
2. **Sui vecchi non cambia niente: 0 → 0.** Non li recupera.
3. 🔑 **Diciotto vecchi su venti non sono nemmeno CANDIDATI** — con **5 candidati mediani** contro i
   ~2.000 delle altre fasce. Il fatto giusto **non entra nella lista**, quindi nessun ordinamento
   può ripescarlo.

---

## Cosa ne segue

· ❌ **La cura del ranking non si scrive.** Avrei toccato il **percorso caldo di lettura** con una
  modifica che peggiora i fatti recenti, sulla base di un banco che misurava il caso comodo.
· 🔑 **Il difetto vero sta PRIMA dell'ordinamento**: cercando per argomento, il filtro lessicale
  spesso **non aggancia** il fatto. L'ordine per data è il secondo strato del problema, non il primo.
· ⚖️ **Questo ridimensiona il documento 17, non lo smentisce.** Quello che 17 misura resta vero:
  quando l'informazione per distinguere il fatto giusto **è nei candidati**, l'ordinamento per data
  la butta via — un fatto che aggancia otto token su nove sta in posizione 4.965. Ma **nel caso
  realistico il problema arriva prima**, e la cura giusta non è riordinare: è **agganciare**.
· ✅ E spiega un fatto già misurato stamattina: **`recall` (semantico) trova dove `search`
  (lessicale) no**. Non perché ordini meglio — perché **candida** ciò che l'altro non vede.

## Limiti di questo documento

· **n=20 per fascia**, campione mio, non popolazione sistematica.
· Le parole del `topic` sono **un proxy** della domanda reale: sono scritte da chi salva, non da chi
  cerca. Un utente vero userebbe parole ancora più lontane, quindi **questa misura è probabilmente
  ottimista**, non pessimista.
· ⏱️ **La fascia «recenti» non è stabile, e l'ho scoperto rieseguendo.** Due esecuzioni a dieci
  minuti di distanza danno **11** e **14** sui recenti «per data» (corpus servibile 12.232 → 12.237):
  «recenti» è definito rispetto a **ora**, quindi cambia composizione a ogni scrittura. ⇒ **Questo
  banco è riproducibile nella conclusione, non nei numeri esatti** — chi lo riesegue troverà altre
  cifre sulla prima riga, e non è rotto. I numeri qui sopra sono dell'esecuzione delle **14:00**,
  corpus servibile **12.237**.
· Non ho misurato **quale** cura funzionerebbe per l'aggancio. So solo che non è l'ordinamento.
