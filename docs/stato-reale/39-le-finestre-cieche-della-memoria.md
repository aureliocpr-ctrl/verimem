# Le finestre cieche della memoria: ventitré minuti, cinquantaquattro fatti

*ws6/Aldo — 30/08, sera. Perimetro: archivio, memoria, corpus, quarantena.*

Il documento 38 stabilisce che senza encode daemon **il moat non gira**: stesso
comando `verimem save`, unica variabile cambiata, `judged=False` senza daemon e
`judged=True` con. Un fatto scritto in quella finestra entra come `model_claim`
mai giudicato — è stato quello che è successo ai miei tre.

Questo pezzo risponde alla domanda che ne discende: **quanto è costato,
finora?**

## Il numero grande è una trappola

`verimem doctor` dichiara che 9150 fatti su 14049 sono `entailment-judged`, il
65,1%. Contando direttamente sullo store (`grounding_score IS NULL` significa
**mai giudicato**, non «giudicato male»), alle **21:19:44 del 30/08**:

    16.369 fatti · 6.601 mai giudicati · 40,3%

Quel 40,3% non è il costo di niente. Mescola due ere, ed è la trappola contro
cui la nostra memoria mette in guardia da settimane — *«un rapporto senza
istante e finestra inganna»*:

| giorno | fatti | mai giudicati | |
|---|---|---|---|
| 18/07 | 105 | 105 | **100%** |
| 19/07 | 66 | 66 | **100%** |
| 25/07 | 50 | 50 | **100%** |
| 27/07 | 33 | 33 | **100%** |
| … | | | |
| 19/08 | 277 | 0 | 0,0% |
| 21/08 | 256 | 0 | 0,0% |
| 24/08 | 317 | 0 | 0,0% |

A luglio non è che il moat fallisse: **non c'era**. Quei 6.601 sono in
larghissima parte l'archeologia del corpus, e leggerli come «fatti persi» è
esattamente il modo di trasformare una misura in un allarme.

## Il numero che conta, e che sta peggiorando

Nell'era corrente il fondo è **fra 0,0% e 0,8%**. Gli ultimi quattro giorni:

| giorno | fatti | mai giudicati | quota |
|---|---|---|---|
| 27/08 | 440 | 14 | 3,2% |
| 28/08 | 395 | 9 | 2,3% |
| 29/08 | 389 | 6 | 1,5% |
| **30/08** | **797** | **70** | **8,8%** |

**Un fattore venti sopra il fondo di metà agosto**, oggi. Questo è un numero che
significa qualcosa, e va guardato da vicino prima di attribuirlo.

## I settanta non sono sparsi: sono quattro blocchi

Se la causa fosse il daemon che muore, i fatti non giudicati dovrebbero
addensarsi in finestre, non spargersi sulla giornata. Si addensano:

    12:19:33 - 12:19:35   (  0,0 min,   6 fatti)
    13:16:23 - 13:19:34   (  3,2 min,   2 fatti)
    16:23:06 - 16:23:07   (  0,0 min,   8 fatti)
    20:30:10 - 20:53:20   ( 23,2 min,  54 fatti)

Ma due di questi blocchi durano **un secondo**. Un daemon morto non muore e
risorge in un secondo: sono due fenomeni diversi, e la nostra regola dice di
misurare entrambe le popolazioni invece di prendere la somma.

**Le raffiche istantanee** sono tutte della stessa forma:

    topic=verimem/porte/auto-MASTER        role=agent_inference
    "AUTO-CLUSTER-MASTER verimem/porte — auto-consolidated entry…"

Sono i **fatti-MASTER del consolidamento automatico**: sintesi di un cluster,
scritte in blocco, **senza una source esterna da giudicare**. Non sono stati
persi dal moat — **non avevano niente da sottoporgli**. Sedici dei settanta.

**La finestra lunga** è un'altra cosa: fatti di lavoro, in maggioranza scritti
con `writer_role=user`.

    dogfooding/moat-soglia-source      user               4
    verimem/telemetria-regime          user               3   ← i miei
    guardia/criterio-cieco-overlap     user               2
    guardia/leva-paths-ignore          user               2
    c10/halumem                        agent_inference   12

**Il costo del daemon assente, oggi, è cinquantaquattro fatti in ventitré
minuti** — non settanta. La differenza fra i due numeri è tutta metodo: se avessi
riportato 70, avrei attribuito al daemon anche il comportamento normale del
consolidamento.

## La finestra combacia con quello che ho visto succedere

Non è un'inferenza dai dati: quella finestra l'ho attraversata mentre lavoravo,
e il prodotto la certifica ai due estremi.

| ora | evidenza |
|---|---|
| **20:30–20:53** | i 54 fatti entrano senza giudizio |
| **20:51** | la ricevuta del mio `save`: *«encode delegate unavailable → … recall keyword finché il daemon non torna»*, e `grounding_score=None` |
| **20:53** | `verimem doctor`: `no encode daemon is running`, 278 vettori a 0d |
| **21:05** | `verimem doctor`: `all 16322 vectors match … from the running encode daemon` |
| **21:00** | **52 fatti scritti, zero non giudicati** |

**La finestra cieca si chiude esattamente quando il daemon torna.** L'ora
successiva ha lo stesso volume di scritture e zero perdite.

## Cosa significa per la memoria

Un fatto entrato in una finestra cieca non è perso: è **stored** e
interrogabile. Quello che manca è il **giudizio** — resta `model_claim` con
`grounding_score = null`, cioè indistinguibile da un fatto per cui nessuno ha
mai passato una source. È la differenza che le istruzioni del prodotto
descrivono così: *«`grounding_score` porta la separazione: un numero significa
che una source è stata giudicata, `null` che non lo è stata mai»*.

Quindi il danno è preciso e limitato, e vale la pena dirlo senza gonfiarlo:
**54 fatti di oggi, scritti da chi credeva di star passando dal moat, sono
indistinguibili da fatti scritti senza alcuna prova.** Chi li rileggerà domani
non ha modo di sapere che la source c'era ed è stata ignorata per una ragione
infrastrutturale.

E siccome il daemon è **intermittente** (misura di ws1: verde 18:11 e 20:16,
rosso 20:37 e 20:5x), questo si ripeterà. La cura non è un comando prima della
sessione: **è un presidio che si accorga della finestra mentre è aperta.** Oggi
nessuno se ne accorge — né chi scrive, che riceve un `admitted`, né la
telemetria, che come mostra il documento 38 non registra il regime.

## Per chi riprende

- **`grounding_score IS NULL` non è un difetto in sé**: prima di contarlo,
  separa l'era pre-moat (luglio: 100% ogni giorno) e i MASTER del
  consolidamento (`topic` che finisce in `/auto-MASTER`, `role=agent_inference`).
  Senza queste due sottrazioni il numero è 40,3% invece di ~1%.
- Il righello sta in
  `docs/stato-reale/banchi/ws6-quanti-mai-giudicati.py` e
  `ws6-le-finestre-cieche-di-oggi.py` (entrambi in sola lettura).
- **Quello che non ho misurato**: se le finestre cieche dei giorni scorsi
  (14 il 27/08, 9 il 28, 6 il 29) abbiano la stessa forma a blocchi. Se
  l'avessero, il daemon sarebbe intermittente da almeno quattro giorni e il
  peggioramento di oggi sarebbe di grado, non di natura.

---

**Verifica**: store `~/.engram/semantic/semantic.db` aperto `mode=ro`, sole
`SELECT`. Istante della misura dichiarato in cima (21:19:44 del 30/08); il
corpus cresce mentre si misura.
