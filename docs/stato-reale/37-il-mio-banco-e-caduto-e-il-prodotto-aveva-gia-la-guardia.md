# 37 — Il mio banco è caduto, e il prodotto aveva già la guardia

**ws6 · 31/08 ore 01:35** · store di Aurelio, sole letture.

Il [documento 36](36-la-promessa-di-astensione-esiste-funziona-ed-e-spenta.md) si chiude con il
limite che serve **per decidere**: *«non ho misurato quante risposte BUONE un pavimento a 0,87
farebbe sparire — il numero misura il rumore, non il costo del silenzio»*. Ho provato a misurarlo.
**Il banco è caduto, e la ragione vale più del banco.**

---

## Il banco, e perché non misura quello che credevo

54 fatti (20 recenti, 18 medi, 16 vecchi), interrogati **con le loro stesse prime dieci parole** —
il caso in cui la risposta giusta **esiste ed è proprio quella**. Esito:

```
   fascia     n   sopra 0,8743   sotto   mediana
   recenti   20        0           20     0,0000
   medi      18        0           18     0,0000
   vecchi    16        0           16     0,0000
```

**Tutti i punteggi sono `0.0000`.** Non «bassi»: **zero esatto, 54 volte su 54.** Un numero così non
è un risultato, è un sintomo — come l'`n=0` che mi aveva già salvato stamattina.

**La causa**: la risposta dichiarava **`ranking: "keyword"`**. Ero sul **ramo degradato**, dove lo
`score` **non è una somiglianza bassa: è una somiglianza non misurata**.

⇒ **Stavo confrontando una soglia di somiglianza con un valore che non è una somiglianza.**

## 🟢 E il prodotto aveva già previsto questo errore — con parole migliori delle mie

`verimem/client.py`, subito prima del filtro:

> *«⚠️ **IL PAVIMENTO NON SI APPLICA A UN RANKING DEGRADATO, ed è un errore di categoria non un caso
> limite**: sul ramo keyword lo `score` è 0.0 **per costruzione** — non «nessuna somiglianza», ma
> «somiglianza NON MISURATA» — e confrontarlo con una soglia di somiglianza **taglia tutto**.»*
>
> *«Misurato il 2026-08-05, stesso store, stessa domanda: a caldo `[0.8995]` risposta giusta ·
> `min_relevance=0.5` → **1**; degradato `[0.0]` **STESSA** risposta · `min_relevance=0.5` → **0**.»*
>
> *«Per un prodotto la cui promessa di punta è "abstention over hallucination" questo è **il modo
> peggiore di sbagliare**: si astiene per un motivo che non ha nulla a che vedere con l'evidenza —
> **l'encoder era lento** — e chi legge non ha modo di distinguerlo da un'astensione vera.
> **Trovato usando il prodotto sul corpus vero**: `[0.00]` su ogni riga.»*

**E non è un commento: è codice.**

```python
if min_relevance and not _degradato:            # ← la guardia
    out = [i for i in out if float(i.get("score") or 0.0) >= pavimento]
if _degradato:                                   # ← e il degrado si dichiara
    for item in out:
        item["ranking"] = "keyword"
```

⇒ **La guardia esiste, e il degrado viene dichiarato in ogni item servito.**

---

## 🔑 Che cosa cambia per la decisione del doc 36

**Il rischio più grosso che il pavimento porta con sé — spegnere tutto quando il sistema è lento —
è GIÀ COPERTO.** Non va progettato: qualcuno l'ha trovato usando il prodotto il **5 agosto**, l'ha
misurato, l'ha curato e ha lasciato scritto perché.

⇒ **La raccomandazione del doc 36 si rafforza**: accendere il pavimento è una decisione **di
default**, e il pericolo che temevo non è tra i suoi costi.

## ⚠️ Ma il limite del doc 36 resta APERTO, e ora so perché

**Non ho ancora misurato quante risposte buone il pavimento farebbe sparire a caldo.** Il mio banco
non poteva: **ero in regime degradato**, e in degradato il pavimento **non si applica affatto**.

📌 E il degrado non è stato un incidente: **`PPR fusion exceeded 2.00s budget` e `rerank: timeout`
sono comparsi in quasi tutte le mie letture di oggi.** ⇒ Per misurare il costo del silenzio serve
**una finestra a caldo**, e in una giornata intera di lavoro **non ne ho avuta una stabile**.
Chi riprende quel filo lo sappia: **il banco va eseguito controllando `ranking` prima di leggere gli
`score`, e scartando le corse degradate** — altrimenti misura zero, come il mio.

## Limiti

· **Il banco non ha prodotto il numero che cercava**: quello che resta è **la causa**, non il costo.
· Non ho verificato **quanto spesso** il ramo degradato scatti su una giornata: l'ho visto in quasi
  tutte le mie letture, **ma non l'ho contato**.
· **L'istante è parte del dato**: 31/08 ore 01:35.
