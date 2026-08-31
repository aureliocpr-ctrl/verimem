# 60 — La transizione del pavimento, colta mentre avveniva

*ws6/Aldo — 31 agosto 2026, ore 02:52:23. Chiude il [48](48-ventitre-minuti-senza-daemon-hanno-spento-una-promessa-del-readme.md) e il [53](53-il-pavimento-si-ripara-da-solo-fra-centocinque-fatti-e-taglia-il-98-percento.md), con le predizioni verificate una per una.*

Il `48` aveva trovato un `floor.json` degenere — `{"floor": 0.0}` — scritto
durante una finestra senza daemon e **ancora servito a guasto finito**. Il `53`
aveva contato quanto mancava alla sua auto-riparazione (**105 fatti vivi**) e
registrato tre predizioni **prima** dell'evento. Poi ne ho aggiunta una quarta.

**È scattata alle 02:52:23.** Non l'ho ricostruita a posteriori: avevo il
cronometro pronto e l'ho eseguito nell'istante in cui il conteggio ha superato
la soglia.

## ① I numeri

```
floor.json PRIMA : {"floor": 0.0,    "n_facts": 13795}   mtime 30/08 20:32:08
floor.json DOPO  : {"floor": 0.8781, "n_facts": 14485}   mtime 31/08 02:52:23
UNA recall       : 18,44 s          (baseline misurato poco prima: 2,84 s)
```

## ② Le quattro predizioni, una per una

| | predizione registrata prima | esito |
|---|---|---|
| **P1** | il file viene **riscritto** (mtime ≠ 20:32:08) | ✅ **scattata** |
| **P2** | `n_facts` ≥ 14485 | ✅ **regge** (14485) |
| **P3** | `floor` fra **0,87 e 0,89** | ✅ **regge** (**0,8781**) |
| **P4** | la prima recall costerà **> 20 s** | ❌ **CADE** (**18,44 s**) |

**P4 cade, e lo scrivo invece di aggiustarla.** Avevo scelto la soglia dal
numero di @ws2 (ricalcolo 24.169 ms sul corpus vero): il costo vero è **18,44
s** — meno del previsto, **dello stesso ordine**. Il rapporto misurato sulla
stessa macchina e nello stesso minuto è **18,44 / 2,84 = 6,5×**.

📐 **E le tre stime del pavimento convergevano**: 0,8743 · 0,8797 (entrambe mie)
· 0,8853 (@ws2). Il valore vero è **0,8781**. La dispersione delle sonde non
cambiava il verdetto, come avevo scritto nel `53`.

## ③ L'ho innescata io, e l'avevo dichiarato prima

`client.py:1271` chiama `_auto_relevance_floor()` in **ogni** recall, dentro un
`try` non condizionato. Bastava quindi che il corpus arrivasse a 14485 fatti
vivi — e a scrivere il 14485º sono stato io, salvando i fatti della chiusura del
`59`.

**Non ho fabbricato fatti per forzare l'evento**: ho salvato quelli veri del
lavoro in corso, come faccio da ore. Ma l'effetto va detto, ed era **registrato
al canale prima che accadesse**: *«non sono un osservatore neutrale: sarà
probabilmente un mio banco a innescare il ricalcolo, e a pagarlo»*.

⇒ **Il merito dell'osservazione è zero. Il costo di 18,44 secondi, no**: è
quello che pagherebbe **un utente qualunque**, una volta, senza preavviso e
senza spiegazione. È il pezzo che mancava al punto **(iv)** della cura proposta
da @ws2 — «il ricalcolo sta sul percorso di lettura» — ora con un numero
misurato invece che stimato.

## ④ L'avviso si è riacceso

Il `56` mostrava che `_pav` a `0.0` è *falsy*, quindi
`if out and _pav and _best < float(_pav)` **spegneva l'avviso sempre**, anche
con risultati pieni. Con il pavimento a 0,8781:

| query | `best` | avviso |
|---|---|---|
| il pavimento di rilevanza dello store | 0,8860 | no — **sopra** il pavimento |
| quale layer ha quarantinato il fatto | 0,8824 | no — **sopra** |
| come si pota un ulivo in primavera | 0,8086 | **sì** |
| qual è la ricetta della carbonara | 0,8623 | **sì** |

**Il difetto del `56` è confermato in negativo**: spento prima, acceso adesso.
Non serviva altra prova.

## ⑤ Che cosa NON dico, e serve dirlo

⛔ **Non dico che «l'avviso funziona bene» sulla base di quelle quattro query.
Sono mie, e le mie query non sono il traffico.** Le due di dominio stanno a
0,88+, mentre la **mediana dei 2887 `best` storici è 0,850**. Sul traffico
storico la stima del `53` resta in piedi: **2823 su 2887 = 97,8% sotto 0,8781**.

**Le due cose non si contraddicono**: dicono che il mio campione è migliore del
traffico medio. **È la quinta volta stanotte che il campione spiega il numero —
la prima in cui l'ho visto prima di scriverlo invece che dopo.**

## ⑥ Misurato, mezz'ora dopo: 87,5% — e la mia stima era 10 punti troppo alta

Avevo scritto qui sopra *«si potrà contare invece di stimare»*. **Contato**, sui
`best` che il prodotto ha registrato **dopo** le 02:52:23:

```
recall reali dopo il ricalcolo, con best > 0 : 72
  mediana 0.8421   p95 0.8860   max 0.8860
  SOTTO il pavimento 0.8781 : 63/72 = 87,5%
```

| | quota di risposte sotto il pavimento |
|---|---|
| **stima** del `53` (dai 2887 `best` storici) | **97,8%** |
| **misura** sul traffico dopo il ricalcolo (n=72) | **87,5%** |
| | **−10,3 punti** |

**La stima era troppo alta di dieci punti, e la sostanza regge lo stesso:
l'avviso si accende su quasi nove risposte su dieci.** La conclusione del `53`
non cambia — *un avviso che si accende quasi sempre non è un avviso, è rumore* —
ma il numero da citare adesso è **87,5% misurato**, non 97,8% stimato.

📌 **Limiti di questa misura**: **n=72 e venticinque minuti** · e **fra quelle
recall ci sono le mie quattro query di verifica**, che ho fatto io poco prima
(togliendole il quadro non cambia in modo apprezzabile, ma vanno dichiarate) ·
il campione è il traffico di **una manciata di istanze che lavorano di notte**,
non di utenti.
📌 **Va rifatta domani** su qualche ora di traffico: `banchi/ws6-best-reali-dal-journal.py`
con la finestra che parte dalle 02:52:23 e la soglia 0,8781.
📌 **Una sola esecuzione** per il costo di 18,44 s, e su questa macchina.

🔁 **E il costo è UNA TANTUM — verificato subito dopo.** Rieseguito lo stesso
banco a file ormai riscritto: **3,27 s**, cioè il baseline. Il conto completo:

| momento | una recall |
|---|---|
| prima della soglia (file servito) | **2,84 s** |
| **la recall che ha innescato il ricalcolo** | **18,44 s** |
| subito dopo (nuovo file servito) | **3,27 s** |

⇒ **non è un degrado che resta: è una singola richiesta sacrificata.** Il che
non lo rende innocuo — **quella richiesta è di un utente qualunque, che aspetta
sei volte il normale senza sapere perché** — ma cambia la forma del problema per
il pezzo **(iv)**: non «il prodotto è lento», bensì «una lettura ogni ~724 fatti
paga per tutte le altre».
📌 **Il valore 0,8781 non è stabile per sempre**: è la stima di questo corpus a
quest'ora, e si rifarà alla prossima deriva del 5% — cioè fra circa 724 fatti
vivi, in su o in giù.

---
*Banco: `banchi/ws6-cronometro-della-transizione.py` — una esecuzione stampa
floor prima/dopo, il tempo, l'avviso e il verdetto sulle predizioni. Store di
Aurelio in sola lettura: il file l'ha riscritto il PRODOTTO, non io.*
