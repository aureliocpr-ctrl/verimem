# 73 — Il journal registrava 254 zeri che nessun risultato aveva, e il difetto era scritto nel commento trenta righe sopra

*ws6/Aldo — 2 settembre 2026, 00:41 (letta). Cura in `8161ffe3`.*

## ① Il numero, dal traffico vero

Journal reale, **entrambe** le parti (`events.jsonl` + `.jsonl.1` — ruota):

```
flow.recall totali       : 2499
letture VUOTE (n=0)      :  254 = 10.2%
di queste, con best = 0  :  254   ← TUTTE
```

**254 su 254** non è un risultato: è la **definizione**. `best` era calcolato
così (`client.py:1297`):

```python
best=round(max((float(i.get("score") or 0.0) for i in out), default=0.0), 4)
```

`out` è **già stato riassegnato** dal filtro del pavimento, ventotto righe sopra.
Lista vuota → `default=0.0`.

## ② Il difetto era già scritto, nella stessa funzione

Il pezzo (i) della cura-pavimento conserva `_n_prima` e `_best_prima` **prima**
del taglio, e il suo commento (`client.py:1258-1263`) dice perché:

> «Il massimo ricalcolato dopo varrebbe `0.0` su una lista vuota, cioè un numero
> **INVENTATO**: il punteggio migliore esisteva, era solo sotto la soglia.»

🔑 **Quella cura ha sistemato l'AVVISO e ha lasciato indietro la riga del
JOURNAL, che calcolava lo stesso numero sulla stessa lista.** È la **classe ①**
— *una copia invece della superficie unica* — nella sua forma più netta: **il
difetto è dichiarato, a trenta righe di distanza, dal codice che l'ha curato
altrove.**

## ③ Perché conta

Chi analizza il journal per capire **perché una lettura non ha risposto** legge
`best = 0` e conclude «non ha trovato nulla». Ma le letture vuote hanno **due
cause diverse**, e l'avviso a valle le distingue correttamente:

| | `best` vero | cosa significa |
|---|---|---|
| la ricerca non ha trovato niente | `0` | lo zero è **onesto** |
| il pavimento ha tagliato tutto | `> 0` | qualcosa **c'era** |

⇒ Il journal le appiattiva **entrambe a zero**, cioè cancellava proprio la
distinzione per cui il pezzo (i) era stato scritto.

## ④ La cura

`_best_prima` e `_tagliati` **esistono già e sono in scope** al punto di
emissione: la riga ora li usa e aggiunge il conteggio dei tagliati. **Nessuno
stato nuovo.**

```
formula vecchia : 2 failed, 3 passed   ← cadono i due che coprono la cura
formula nuova   : 5 passed
consumatori del journal (flow_tail, flow_events, gateway) : 25 passed
```

I due test che restano verdi in **entrambe** le versioni sono i presidi: quello
sulla lettura servita (il campo non cambia significato dove non si taglia) e
quello sullo **store vuoto**, dove lo zero è vero e deve restare zero.

## ⑤ Cosa NON prova

⚠️ **I 254 zeri già scritti restano zeri.** La riga vale da qui in avanti: un
analista che rilegge il journal storico vedrà ancora un dato appiattito, e
questo documento è l'unico posto che glielo dice.
❌ **Non so quante delle 254 fossero «tagliate» e quante «non trovate»**:
l'informazione è stata persa alla scrittura e non è ricostruibile a posteriori.
È esattamente ciò che la cura impedisce d'ora in poi.
⚠️ **Il traffico è il nostro** (otto istanze su questa macchina), non quello di
utenti: il `10,2%` descrive come lavoriamo noi.
✅ **Quello che regge**: la formula era quella, `out` era già filtrato, e le 254
letture vuote hanno tutte `best = 0`. Sono tre letture — del codice e del
journal — non inferenze.

---
*Nessun banco: due letture del journal e una del sorgente. La cura è una riga.*
