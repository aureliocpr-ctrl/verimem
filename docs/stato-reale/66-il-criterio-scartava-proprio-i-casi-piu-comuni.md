# 66 — Il criterio scartava proprio i casi più comuni, e il tasso che avevo dato è sbagliato di un ordine di grandezza

*ws6/Aldo — 31 agosto 2026, 07:05. Chiude, capovolgendolo, il limite che avevo dichiarato nel [64](64-una-catena-di-quattro-ritiri-fa-sparire-una-misura-intera.md).*

Nel `64` avevo consegnato un numero alla decisione collegiale — **tasso di
false-supersede ≈ 15,6%** — e ne avevo dichiarato il limite con parole mie:

> **È un PAVIMENTO, non il tasso vero.** Il criterio seleziona i candidati per
> somiglianza lessicale bassa, quindi i ritiri sbagliati fra testi che si
> somigliano non li vede proprio. **Ho misurato la PRECISIONE, non il RICHIAMO.**

**Ho misurato il richiamo. Il pavimento non era basso: era bassissimo.**

## ① Quattordici su quattordici

Presi i ritiri che il criterio **NON** seleziona (`jaccard ≥ 0,15`, cioè i due
testi **si somigliano**), campione casuale:

> **14 letti, 14 sbagliati. Nessuna eccezione.**

E sono tutti della stessa forma — **due misure diverse dello stesso banco**:

| jaccard | il fatto **ritirato** | il fatto che l'ha **sostituito** |
|---|---|---|
| 0,667 | «la latenza riporta **mediana 33.0s** su 5 query» | «la latenza riporta **min 16.3s** su 5 query» |
| 0,571 | «il workflow **security** ha `completed_total` 1578» | «il workflow **ci** ha `completed_total` 1121» |
| 0,500 | «lo scambio sulla fonte **nuda** (453 char) score 72.08» | «lo scambio sulla fonte **ricca** (820 char) score 99.98» |
| 1,000 | «con `ENGRAM_ENCODE_SERVICE=0` la **scrittura 2** riporta L1.20» | «… la **scrittura 3** riporta L1.20» |

Il terzo sono **i due bracci di un A/B**. Il secondo sono **due workflow
diversi**. Il quarto **due scritture diverse** dello stesso banco. **Nessuno di
questi fatti nega quello che ha cancellato.**

## ② Il quadro, e il motivo che il prodotto dichiara

```
340 ritiri nella finestra
   57 candidati      (jaccard < 0.15)  → letti 56, sbagliati 52
  283 NON candidati  (jaccard ≥ 0.15)  → letti 14, sbagliati 14

motivo dichiarato dal prodotto:
  same-source evolution                    274
  heal_contradictions: numeric_clash        62
```

⇒ **Il 15,6% era la quota di ritiri che il MIO criterio segnala**, e il criterio
scarta **proprio i casi più comuni**: le riscritture della stessa serie, dove i
testi si somigliano perché parlano dello stesso banco **ma misurano cose
diverse**. Con 14/14 sui non selezionati, **il tasso vero è vicino alla totalità
dei ritiri, non a un sesto.**

📌 **E il motivo dichiarato lo spiega**: **274 su 340 sono `same-source
evolution`** — il meccanismo che sappiamo cieco, perché `is_same_source` guarda
**la penna** (`canonical_source_of`, sempre `'user'`), non il contenuto.

## ③ L'errore mio, e la sua forma

**Ho misurato la precisione su una popolazione che avevo selezionato io, e ho
chiamato «tasso» quello che era «tasso fra i selezionati».**

Il limite l'avevo scritto — **ma scritto in fondo, mentre il numero stava in
cima e in grassetto**.

> ⚠️ **Un limite dichiarato non protegge se il numero viene citato senza di
> esso.** Il richiamo andava misurato **prima** di consegnare la cifra, non dopo:
> finché non sai quanto il tuo criterio *perde*, quello che hai non è un tasso —
> è una proprietà del tuo filtro.

## ④ Che cosa è provato e che cosa no

✅ **Provato**: su **14 ritiri non selezionati presi a caso, 14 sono sbagliati** ·
**274 dei 340 ritiri dichiarano `same-source evolution`** · i quattro esempi
sopra sono testuali.
❌ **Non provato**: **una percentuale nuova.** 14 su 283 sono pochi, e non do una
cifra sostitutiva: do il fatto che **su quattordici presi a caso non ce n'era uno
giusto**. Chi vuole il numero deve leggerne altri.
❌ **Non provato**: che le riscritture fossero *involontarie*. Chi scriveva
aggiungeva misure a una serie; il prodotto le ha lette come sostituzioni.

## ⑤ Conseguenza per la decisione in corso

`semantic.py:1854` spegne la riconciliazione *«until the false-supersede rate is
measured on a real corpus»*. **La misura adesso c'è ed è molto peggiore di quella
che avevo consegnato.** Il verso della conclusione non cambia — riaccendere il
ramo non distruttivo — **ma l'urgenza sì: non è un ritiro sbagliato ogni sei, è
quasi sempre.**

---
*Banco: `banchi/ws6-quali-ritiri-sono-sbagliati.py` per i candidati; il campione
sui non selezionati è la stessa query con `jaccard >= 0.15`. Store di Aurelio in
sola lettura.*
