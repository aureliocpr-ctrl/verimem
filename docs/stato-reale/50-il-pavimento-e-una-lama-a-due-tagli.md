# Il pavimento è una lama a due tagli, e l'ho scoperto cercando altro

*ws6/Aldo — 31/08, notte. Perimetro: archivio, memoria, corpus, recall.*

Il documento 37 si chiudeva con un limite che non ero riuscito a superare in
tutta la giornata: **quante risposte buone farebbe sparire un pavimento a
0,8743?** Serviva una finestra non degradata, e non l'avevo mai avuta.

L'ho trovata stanotte per caso, mentre facevo tutt'altro: un controllo di
ritrovabilità sul mio stesso lavoro.

## La misura, arrivata di traverso

Ho chiesto alla memoria — `hippo_facts_recall`, k=4 — *«pavimento di rilevanza a
zero persistito durante il guasto del daemon»*, per vedere se i fatti che ho
scritto stanotte fossero ripescabili. Il regime era buono:

    ranking: {rerank: "skipped_long_query", fusion: "applied"}

**`fusion: applied`**: non è il ramo degradato che ha rovinato le mie misure di
ieri. E i quattro risultati:

| score | fatto |
|---|---|
| **0,8421** | i due difetti del daemon guadagnati dagli avversari (25/07) |
| **0,8389** | *«Il pavimento stimato passa da 0.0 con un fatto a 0.8956 con due»* (03/08) |
| **0,8389** | il discovery cancellato di un daemon vivo (25/07) |
| **0,8388** | un daemon vivo che teneva spenta la semantica su tutta la macchina (25/07) |

**Sono tutti e quattro pertinenti.** Parlano di daemon che si incastrano, di
pavimenti che vanno a zero, di semantica che si spegne: esattamente il tema
della domanda.

**E sono tutti sotto il pavimento**, che oggi vale **0,8881** (misurato nel
documento 48 su copia). Il più alto sta **46 millesimi** sotto.

> **Con il pavimento acceso, questa ricerca non avrebbe restituito niente.**

## Che cosa aggiunge al documento 36

Il documento 36 mostrava l'altro lato: alla domanda «come si compra un biglietto
per Saturno» il prodotto serviva tre fatti a **0,8119 · 0,7796 · 0,7807**, tutti
sotto il rumore, e il pavimento li avrebbe tagliati **giustamente**.

Questo mostra il taglio opposto: una domanda **con** risposta, quattro fatti
**utili**, e il pavimento li taglierebbe tutti.

**Il pavimento è una lama a due tagli**, e la banda in cui i due casi vivono è
sottilissima: i falsi stanno a 0,78-0,81, i veri a 0,8388-0,8421, la soglia a
0,8881. **Fra i risultati utili e la soglia ci sono 46 millesimi; fra i risultati
inutili e quelli utili, 27.**

*(Due avvertenze, perché il numero non venga usato più di quanto regga: il
`rerank` è stato **saltato** — la query aveva dieci parole — quindi non è il
regime pieno; ed è **un caso singolo**, non una statistica. Dice che il costo
esiste ed è misurabile, non quanto sia grande.)*

## Un precedente che avrei dovuto cercare

Fra i quattro risultati c'è questo, del **3 agosto**:

> *«Il pavimento stimato passa da **0.0 con un fatto** a 0.8956 con due fatti e
> resta fra 0.8599 e 0.8758 fino a dieci fatti.»*

**Qualcuno aveva già osservato che il pavimento vale `0.0` in una condizione
degenere.** La causa lì è diversa dalla mia — corpus minimo, non daemon assente —
ma il valore prodotto è lo stesso, e la conseguenza pure.

**È il dodicesimo scivolone della notte, e viola la nostra prima regola**:
cercare in memoria *prima*. Se l'avessi fatto prima di scrivere il documento 48
avrei avuto in mano, dall'inizio, il fatto che rende generale il reperto:

> **Il pavimento va a `0.0` in più condizioni degeneri diverse, e in nessuna di
> esse il prodotto lo distingue da una stima valida.**

Non è una duplicazione del lavoro altrui: è un precedente che **rafforza** il
mio, e l'ho trovato per caso invece che cercandolo.

## E il test che ero venuto a fare è fallito

L'obiettivo iniziale era un altro: verificare che i **sessantaquattro fatti**
scritti stanotte fossero ritrovabili. **Nessuno di essi compare nei primi
quattro risultati** di una query che descrive esattamente il loro contenuto.

Non ne traggo una conclusione forte — una query, un k=4, e il `rerank` saltato
non bastano — ma il sospetto è il tema di tutta questa serie, ed è scomodo
quando tocca il proprio lavoro: **scrivere in memoria e essere ritrovabili sono
due cose diverse**, e ho passato la notte a misurare la seconda per il prodotto
senza misurarla per me.

## Per chi riprende

- **La misura che manca è la stessa del documento 37**, e ora ha una forma
  precisa: prendere N domande **con risposta nota**, eseguirle in regime pulito
  (`fusion: applied` **e** `rerank` non saltato: query sotto le dieci parole), e
  contare quante risposte corrette starebbero sotto 0,8881. Questo pezzo dice
  che ce ne sono; non dice quante.
- **Il pavimento non va acceso senza quel numero.** Il documento 36 lo mostrava
  utile, questo lo mostra costoso: **la decisione richiede entrambi i lati, e
  finora nessuno dei due è stato misurato in regime pieno.**

---

**Verifica**: `hippo_facts_recall` dalla porta MCP, k=4, `ranking` riportato in
linea; pavimento 0,8881 dal documento 48 (misurato su copia). Nessuna scrittura.
