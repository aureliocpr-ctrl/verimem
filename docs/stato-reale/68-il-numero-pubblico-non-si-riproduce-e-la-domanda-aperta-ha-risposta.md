# 68 — Il numero pubblico del README, eseguito: la domanda che restava aperta ha una risposta, e la cifra non si riproduce

*ws6/Aldo — 1 settembre 2026, sera. Audit matematico su **un numero non mio**.*

Il `README.md:74-76` porta, sulla lacuna più grande dichiarata del gate:

> **Measured 2026-08-25** (`docs/stato-reale/banco-osservatore-il-tasso.py`, 96
> cases = 8 source types × 6 cases × 2 languages, CE-only judge): **25 of 48**
> such unsupported claims were admitted — IT 54.2%, EN 50.0%, and **8 of the 48
> IT/EN pairs** — true and false alike get the OPPOSITE verdict in the two
> languages, in both directions.

## ① Quello che era già stato fatto, e che non rifaccio

[`la-vetrina-e-stata-corretta-quattordici-volte.md`](la-vetrina-e-stata-corretta-quattordici-volte.md) (§ sulla quarta forma) ha già
auditato questa riga: **il 48 compariva due volte con due significati diversi**
— i claim non sostenuti (24 IT + 24 EN) e le coppie totali del banco (96/2) — e
l'articolo di «*the* 48» diceva al lettore che fossero gli stessi. La correzione
proposta lì è **già applicata** al README di oggi.

✅ **L'aritmetica dichiarata torna**: `96 = 8 × 6 × 2`; e `54,2% di 24 = 13`,
`50,0% di 24 = 12`, totale **25 su 48**.

🔑 **Ma quell'audit è stato fatto leggendo il codice — «si legge nel codice,
senza eseguirlo» — e si chiude su una domanda esplicitamente aperta**:

> «quante delle 8 cadano sui falsi **non è scritto da nessuna parte**. Se
> cadessero tutte lì il tasso sui falsi sarebbe 8/24 = 33%.»

**L'ho eseguito.**

## ② Condizioni dichiarate

Il banco fissa da sé il proprio store (`HIPPO_DATA_DIR` = `store_largo` accanto
al file) e il suo docstring dichiara **«corpus VUOTO»**. ⚠️ Quella cartella nel
repo di lavoro **esiste ed è popolata (2,8 MB, con `dreams/` dentro)**: chi lo
esegue lì, oggi, non è nella condizione dichiarata.

Per non toccare né lo store di Aurelio né file di altre istanze, ho eseguito una
**copia** del banco con l'unica riga dello store parametrizzata, su una
**tempdir mia e vuota** — la condizione che il docstring prescrive.

## ③ Il run di oggi, e la risposta alla domanda aperta

```
IL TASSO — n=96 casi (8 fonti x 6 casi x 2 lingue)
  TOTALE  falsita' ammesse 26/48 = 54.2%   veri rifiutati 7/48 = 14.6%   corretti 63/96 = 65.6%
    IT    falsita' ammesse 14/24 = 58.3%   veri rifiutati 4/24 = 16.7%   corretti 30/48 = 62.5%
    EN    falsita' ammesse 12/24 = 50.0%   veri rifiutati 3/24 = 12.5%   corretti 33/48 = 68.8%

  totale casi con esito DIVERSO fra le due lingue: 9/48
```

| | README (misurato 25/08) | questo run (01/09) |
|---|---|---|
| falsità ammesse | **25/48** | **26/48** |
| IT | 54,2% (13/24) | **58,3% (14/24)** |
| EN | 50,0% (12/24) | **50,0% (12/24)** ✅ |
| divergenze IT/EN | **8/48** | **9/48** |

⚠️ **Attenzione a un tranello di lettura**: `54,2%` compare in entrambe le
colonne ma su **popolazioni diverse** — nel README è **IT** (13/24), qui è il
**TOTALE** (26/48). Due frazioni diverse che danno la stessa percentuale.

### La domanda aperta: dove cadono le divergenze

```
[pytest    V-PARZ] IT quarantined  |  EN admitted
[pytest    F-INV ] IT quarantined  |  EN admitted
[errore    F-INV ] IT admitted     |  EN quarantined
[errore    F-GEN ] IT admitted     |  EN quarantined
[specifica F-AGG ] IT quarantined  |  EN admitted
[tabella   F-INV ] IT admitted     |  EN quarantined
[nota      V-CIT ] IT admitted     |  EN quarantined
[nota      V-PAR ] IT quarantined  |  EN admitted
[nota      F-INV ] IT admitted     |  EN quarantined
```

> **6 delle 9 divergenze cadono sui FALSI** (`F-INV` ×4, `F-GEN`, `F-AGG`), **3
> sui VERI** (`V-PARZ`, `V-CIT`, `V-PAR`).

⇒ La risposta all'ipotesi lasciata aperta: **non cadono tutte sui falsi**, quindi
il «se cadessero tutte lì sarebbe 8/24 = 33%» **non si avvera**: sui falsi sono
**6 su 24 = 25,0%**. ✅ E il «true and false alike» che il README già dichiara è
**confermato dai dati**, non solo dalla lettura del codice.

📌 **`F-INV` da solo fa 4 delle 6**: l'inversione di ruoli o valori è la classe
dove le due lingue si contraddicono di più.

## ④ Un audit che stavo per dichiarare verde, e copriva UNA riga

Mentre il banco girava ho fatto un controllo laterale in sola lettura: **ogni
frazione `N/M` del README accompagnata da una percentuale deve tornare**. Ha
segnalato un solo caso, la riga 100 — `112/112` con `0.0%` — che si è rivelato un
**complemento**, non un errore: `112/112 entailed admitted` **è** lo 0% di
false-block. Nessuna incoerenza.

Stavo per scrivere *«l'audit aritmetico del README non trova incoerenze»*. Poi ho
stampato il denominatore:

```
DENOMINATORE del mio audit: 1 coppie frazione/percentuale esaminate
```

> 🪞 **Una sola.** Il criterio pretendeva frazione **e** percentuale *sulla stessa
> riga*, e nel README quasi nessuna riga ha entrambe. Quel «zero incoerenze» non
> era un risultato: era **una misura che non c'era, e che si legge come
> perfetta** — la stessa forma che questo repo documenta da settimane, commessa
> mentre ne stavo verificando un'altra.

📌 **Non lo raffino qui**: il compito era *un* numero, e quel numero si verifica
eseguendolo, non contando cifre in una pagina. Ma **un controllo automatico su
una pagina di prosa va sempre accompagnato dalla sua copertura**, o dice
«verde» proprio dove non ha guardato.

## ④-bis Il README sa già fare la cosa giusta — altrove

Sulla riga 100-101 c'è il precedente che serve a questo documento:

> «0% false-block *(re-measured 2026-08-25: still 0.0%, 112/112 entailed
> admitted)* / **5.4% escape** *(1.8% was the 2026-07-18 run; the same command
> today reports 5.4%)*»

⇒ Per quella cifra il README **dichiara di averla rimisurata**, riporta il valore
vecchio **e** quello nuovo, e dice che è lo stesso comando. È esattamente ciò che
manca alla riga del `25 of 48` — e il §③ mostra che sarebbe servito.

## ⑤ Il controllo che poteva falsificarmi, fatto prima di pubblicare

## ⑤ Il controllo che poteva falsificarmi, fatto prima di pubblicare

✅ **Prima di tutto: la differenza non può essere rumore.** Il banco non contiene
nessuna sorgente di casualità (`random`, `seed`, `shuffle`, `sample`: zero
occorrenze) e il giudizio CE non campiona (`temperature`, `do_sample`: zero nel
gate). ⇒ **A parità di codice e di stato dello store, il banco è
deterministico**, e una cifra diversa ha una causa, non una varianza.

Due cause la spiegano, e vanno separate **prima** di dire «il numero non si
riproduce»:

1. **il prodotto è cambiato** fra il 25/08 e oggi (in mezzo c'è, fra l'altro, la
   banda a due soglie attiva di default);
2. **il banco non isola**: il run originale può essere avvenuto sullo
   `store_largo` **già popolato**, e non sul corpus vuoto che dichiara.

Ho eseguito lo **stesso banco** una seconda volta, su una **copia** dello
`store_largo` popolato — la condizione (b) — senza toccare l'originale:

```
corpus VUOTO    : falsita' ammesse 26/48   divergenze 9/48
corpus POPOLATO : falsita' ammesse 26/48   divergenze 9/48
```

> ⛔ **Identici in ogni cifra.** La causa (b) è **falsificata**: lo stato dello
> store non sposta il risultato — ogni claim è giudicato contro **la sua
> source**, non contro il corpus.

⇒ Resta la **(a)**: fra il 25 agosto e oggi **il comportamento del gate è
cambiato**, e il numero pubblicato non descrive più ciò che il prodotto fa.

## ⑥ La consegna

✅ **Il README non ha sbagliato**: la riga è **datata** («Measured 2026-08-25»),
l'aritmetica interna torna, e l'ambiguità del doppio `48` era già stata corretta.
**Il numero era vero quando è stato scritto.**

🔴 **Ma oggi lo stesso comando dà cifre diverse, e in direzione peggiore**:

| | 25/08 | 01/09 |
|---|---|---|
| falsità ammesse | 25/48 | **26/48** |
| IT | 13/24 | **14/24** |
| EN | 12/24 | 12/24 |
| divergenze IT/EN | 8/48 | **9/48** |

📌 **La forma della cura esiste già nel README stesso**, dieci righe più su
(§④-bis): *«1.8% was the 2026-07-18 run; the same command today reports 5.4%»*.
La stessa nota, applicata a questa riga, la rimette in pari senza toglierle
nulla — e **il valore da citare resta un limite dichiarato del prodotto**, non
una promessa.

## ⑦ Cosa NON prova

❌ **Non so quale cambiamento** abbia spostato la cifra: **non ho bisecato**. Fra
il 25/08 e oggi c'è, fra l'altro, la banda a due soglie attiva di default, ma
**non l'ho verificato** e non lo attribuisco.
❌ **Non è un peggioramento dimostrato del prodotto**: una falsità ammessa in più
su 48, su un banco di 96 casi costruito a mano, è **un caso**. La direzione va
guardata, la grandezza no — e chi cita `26/48` senza dire che il campione è
questo commette lo stesso errore che questo repo insegue da settimane.
✅ **Quello che è solido**: il banco è **deterministico** (nessun `random`, nessun
campionamento nel CE) e **il risultato non dipende dallo stato dello store** —
misurato, non assunto. Quindi la differenza ha **una causa nel codice**, e non è
varianza né condizione iniziale.
⚠️ **Livello di misura dichiarato**: la porta pubblica `verimem remember
--source`, CE-only, come dichiara il banco. Non l'API interna.
