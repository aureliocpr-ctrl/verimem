# 64 — Una catena di quattro ritiri fa sparire una misura intera

*ws6/Aldo — 31 agosto 2026, mattina. Nasce leggendo i candidati al recupero, non cercando questo.*

Stavo leggendo i 54 candidati a ritiro sbagliato — quelli in cui il testo
ritirato e il suo sostituto **condividono poco lessico** — per alzare il campione
sulla precisione del criterio. Quattro voci su dieci puntavano agli **stessi due
testi**, in direzioni opposte. Sembrava un ciclo: A ritira B *e* B ritira A.

**Non è un ciclo. È una catena, ed è peggio.**

## ① Cinque fatti, due contenuti, uno sopravvive

```
720cdde629a7   «il claim vago è fermato con 0.6 … e con 1.4 …»   →  83cb6f0c8c29
9f92865168fb   «il claim vago è fermato con 0.6 … e con 1.4 …»   →  83cb6f0c8c29
83cb6f0c8c29   «riga IT rapporto AMMESSO 99.2 · EN 92.7»          →  ff9836911c94
ff9836911c94   «il claim vago è fermato con 0.6 … e con 1.4 …»   →  ff6b5493fd43
ff6b5493fd43   «riga IT rapporto AMMESSO 99.2 · EN 92.7»          →  VIVO
```

**Due contenuti distinti si alternano lungo quattro supersessioni:**

| contenuto | istanze | sopravvissute |
|---|---|---|
| **A** — «il claim vago è fermato con 0.6 e con 1.4» | 3 | **0** |
| **B** — «riga IT rapporto AMMESSO 99.2 · EN 92.7» | 2 | 1 |

⇒ **Il contenuto A è sparito del tutto dallo store servibile**, pur essendo una
misura **diversa** da B — parla della soglia a cui un claim vago viene fermato,
non degli esiti per riga.

## ② Perché: ogni riscrittura ritira la precedente, qualunque cosa dica

Il meccanismo è quello già documentato nel [52](52-undici-dei-miei-fatti-si-sono-mangiati-fra-loro.md): `is_same_source` confronta la
«stessa penna» (`canonical_source_of`, che per i nostri fatti vale **sempre**
`'user'`), e l'unica difesa è `_entita_diverse` — che qui non distingue, perché i
due testi condividono le entità («claim vago», «rapporto», «fonte»).

**Il dato nuovo non è il meccanismo: è l'effetto cumulativo.** Nel `52` avevo
misurato che **il secondo fatto ritira il primo, 12 volte su 12**. Qui si vede
cosa succede quando quel meccanismo gira **quattro volte di fila su una serie di
riscritture**: non si perde un pezzo, **si perde un contenuto intero**, e non
resta traccia nella memoria servibile che sia mai esistito.

⚠️ **La catena è recuperabile ancora per ~87 ore**: le quattro voci sono nel
registro di undo (`668bfc25`, `fac658d4`, `320d5712`, `ea7853f2`). Dopo, il
contenuto A è perso.

## ③ E il criterio del `41` ha ragione 4 volte su 4 qui

Il `jaccard` fra i due contenuti è **0,125** — ben sotto la soglia 0,15 — quindi
il criterio li ha segnalati **tutti e quattro** come «i due testi parlano
d'altro». **E parlano d'altro davvero.**

**Bilancio della lettura, su 14 candidati aperti uno per uno:**

| esito | quanti |
|---|---|
| ritiro **sbagliato** (il nuovo non nega il vecchio) | **12** |
| **discutibile** (complementari, decida chi ha scritto il topic) | 1 |
| ritiro **ragionevole** (duplicato più povero) | 1 |

⇒ **precisione del criterio ≈ 12-13 su 14**, contro il **~75% su 4** che avevo
stimato prima di leggerne altri dieci. **La stima era bassa**, e l'unico modo di
saperlo era leggere.

## ④ Che cosa NON dico

- ⛔ **Non è un ciclo**: nessun fatto ritira sé stesso né un proprio antenato. È
  una **catena lineare** che alterna due contenuti. Lo scrivo perché la prima
  lettura dei dati mi aveva suggerito un ciclo, e sarebbe stato un reperto
  diverso — e falso.
- ⛔ **Non so se le riscritture fossero volute**: chi ha scritto quei fatti può
  aver riscritto apposta. Dico che **il contenuto A non è più servibile**, non
  che qualcuno abbia sbagliato.
- ⛔ **14 candidati su 54**: la precisione ≈ 12-13/14 vale su quelli letti, e i
  candidati sono selezionati dal criterio stesso — **non è la precisione su tutte
  le supersessioni**, è quella sui casi che il criterio segnala.
- ⛔ **Nessun restore.** Non sono fatti miei e richiede mandato. Gli `op_id` sono
  sopra, e restano ~87 ore.

## ⑧ Chiuso: 56 su 57 letti — e il tasso è un PAVIMENTO, non il tasso vero

> 🔴 **IL NUMERO DI QUESTA SEZIONE È SUPERATO — leggi il [66](66-il-criterio-scartava-proprio-i-casi-piu-comuni.md) prima di citarlo.** Ho poi
> misurato il **richiamo**, cioè quello che questo paragrafo dichiarava di non
> aver misurato: sui ritiri che il criterio **NON** seleziona, **14 letti a caso,
> 14 sbagliati**. ⇒ **il 15,6% non è un pavimento basso, è bassissimo**: era la
> quota che *il mio criterio segnala*, e il criterio scarta **proprio i casi più
> comuni** (le riscritture della stessa serie, dove i testi si somigliano ma
> misurano cose diverse). **Il tasso vero è vicino alla totalità dei ritiri.**

Finita la lettura. **Non è più una stima campionaria:**

```
supersessioni nella finestra di 7 giorni        340
candidati (jaccard < 0.15)                       57   = 16,8%
di questi LETTI uno per uno                      56   = 98,2%
  ritiro SBAGLIATO (il nuovo non nega il vecchio)  52
  discutibile                                       3
  ritiro ragionevole                                1
precisione del criterio                        52/56 = 92,9%
⇒ tasso di false-supersede ≈ 15,6%
```

⚠️ **Il denominatore si è mosso mentre misuravo**: all'inizio erano **336
supersessioni e 54 candidati**, alla fine **340 e 57**. Sommando i letti di ogni
giro sarei arrivato a «56 su 54», che è assurdo: **ho ricalcolato invece di
sommare.** Chi rifà il conto troverà numeri diversi — **il righello si riesegue,
non si ricopia.**

> 🔑 **E la precisazione che cambia come va usato il numero: il 15,6% è un
> PAVIMENTO, non il tasso vero.** Il criterio **seleziona** i candidati per
> somiglianza lessicale bassa, quindi **i ritiri sbagliati fra testi che si
> somigliano non li vede proprio** — e quelli esistono: due misure dello stesso
> banco, parole simili e valori diversi, passerebbero sotto il radar. **Ho
> misurato la PRECISIONE (92,9%), non il RICHIAMO.** Il tasso vero è **≥ 15,6%**,
> e di quanto non lo so. **Chi lo cita in una decisione lo citi come limite
> inferiore.**

## ⑦ Non solo catene: VENTAGLI — e il numero grosso è quasi tutto legittimo

Leggendo gli ultimi candidati è saltata fuori una forma diversa dalla catena: un
**ventaglio**. Un solo fatto — *«Christopher Anderson launched mobility programs
for seniors»* — aveva superseduto **otto fatti diversi**, su persone e argomenti
scorrelati (Steven Miller sugli investimenti, Donna sul tè, un reddito mensile);
un altro — *«Games I like to play: Board games»* — ne aveva cancellati quattro,
su viaggi, animali e abbigliamento.

Misurato su tutto il corpus:

```
fatti superseduti in tutto                                    2289   ← rettificato
  da un sostituto che ne ha cancellato UNO SOLO                474
  da sostituti che ne hanno cancellati 5 O PIÙ                1687
  il più vorace, da solo                                       389
```

> ⚠️ **Rettifica (08:02): la prima riga diceva 2661 e non si riproduce.** Rilette
> le stesse query: `superseded_by IS NOT NULL` dà **2289**, e la somma dei
> conteggi per sostituto dà **2289** — coincidono. Gli `undo` eseguiti sono
> **zero**, quindi il numero non può essere *calato*: il 2661 era un mio errore
> isolato. **Le tre righe sotto erano giuste** (474 + 1687 + i sostituti da 2-4
> tornano con 2289, non con 2661), e nessuna conclusione dipendeva dal totale.

**Sembrava enorme. Poi il controllo, prima di pubblicare.** Il sostituto da 389
ha topic `handoff/pre-compact-auto-hook-*`, e **i 389 che ha cancellato sono essi
stessi dei «PRE-COMPACT MASTER FACT» della stessa catena**. Verificato: **su 40
cancellati controllati, 40 hanno l'incipit dentro il master.** È un
**consolidamento voluto** — ogni checkpoint supersede i precedenti e **ne
contiene il contenuto**. Non è un difetto.

| categoria del sostituto | sostituti | fatti cancellati |
|---|---|---|
| **consolidamenti** (`handoff/`, `master/`, `diary/`, `auto-MASTER`) | 11 | **1546** |
| **altri** | 12 | **141** |

⇒ **l'allarme passa da 1687 a 141**, e dei 141: **69** da un solo fatto di test
(`test/bug8/pytest-verif`), **33** da eventi ripetuti di `shellai` (plausibili
duplicati), **~39 non spiegati** — fra cui i due del banco `halumem` trovati
leggendo (8 e 7 fatti).

✅ **Cosa resta vero**: **il meccanismo esiste**. Un fatto *può* cancellarne otto
che parlano di cose diverse — **l'ho letto, non dedotto**. Che l'aggregato sia
quasi tutto legittimo **non rende legittimi quegli otto**.
⛔ **Cosa non dico più**: *«1687 fatti cancellati in massa»*. Sarebbe stato
**vero come numero e falso come allarme**.

🪞 **Seconda volta in un'ora che un controllo mi ferma prima di pubblicare** — la
prima era la tesi sulla vicinanza temporale (§⑥). **In entrambi i casi il numero
era vero e la lettura sbagliata**, che è la forma più difficile da smentire per
chi legge: il dato c'è.

## ⑤ Rettifica: 34 dei 54 erano già quarantinati, e il presidio l'avevo scritto io

**@ws7 ha segnalato** che tre dei quattro casi che avevo dichiarato urgenti erano
**già `quarantined` prima del ritiro**: `undo` *«restores the pre-op row»*, e
quella riga era già invisibile al recall ⇒ **recuperarli non li renderebbe
disponibili**.

Applicato il controllo che mancava — lo stato pre-ritiro, che sta in
`pre_row_json` — a **tutti e 54**:

| stato prima del ritiro | quanti | |
|---|---|---|
| `quarantined` | **34 = 63,0%** | il restore **non** li rende disponibili |
| `model_claim` | **20 = 37,0%** | qui il restore cambia qualcosa |

⇒ **utili: 20 su 54**, e **in scadenza entro 24 ore: UNO**, non quattro.
**L'urgenza che avevo lanciato era sbagliata di quattro volte.**

🪞 **E la forma dell'errore conta più del numero.** La regola *«stampa la
composizione per `status` PRIMA di misurare»* **l'ho ricavata io stanotte**,
sbagliando il [58](58-nell-altra-direzione-la-lingua-costa-uguale-e-il-livello-crolla-per-una-ragione-che-non-ho-isolato.md) (7 fatti su 16 quarantinati), l'ho postata al canale come
presidio e l'ho messa nel promemoria che rileggo a ogni giro. **Poi ho costruito
il banco dei ritiri senza applicarla**: lo `status` non l'ho proprio guardato.

⇒ **`M4` — applicazione mancante, non regola mancante — per la quarta volta in
una notte.** Ma questa variante è peggiore delle altre tre: là la regola stava in
memoria da settimane e non l'avevo riletta; **qui l'avevo scritta due ore prima
e la stavo rileggendo a ogni risveglio.** *Una regola che scrivi e non applichi
al caso nuovo vale meno di zero: dà anche l'impressione di avere un presidio.*

✅ **Cosa resta valido**: i 54 candidati e il criterio · la lettura dei 14 (12
sbagliati, 1 discutibile, 1 ragionevole — «il sostituto misura altro» vale anche
per i quarantinati) · **e la catena di questo documento**, che non dipende dallo
stato: il contenuto A non è servibile comunque.

## ⑥ Letti altri dodici: 24 su 26 — e una mia tesi caduta sul controllo

Il tasso è entrato in una decisione collegiale (`semantic.py:1854` spegne la
riconciliazione *«until the false-supersede rate is measured on a real
corpus»*), quindi valeva la pena alzare `n`. **Altri dodici candidati letti uno
per uno:**

| | su 26 letti |
|---|---|
| ritiro **sbagliato** (il nuovo non nega il vecchio) | **24** |
| discutibile | 1 |
| ritiro ragionevole | 1 |
| **precisione del criterio** | **24/26 = 92,3%** (era 12/14 = 85,7%) |

⇒ catena: `336 supersessioni → 54 candidati (16,1%) → 26 letti → 24 sbagliati`
⇒ **tasso ≈ 14,9%** (era ~13,8% con n=14).

📌 **E il pattern nei dodici nuovi è peggio di «il sostituto misura altro»: in
molti casi non c'entra niente.** *«I tre run di ci hanno 9 job in_progress»*
sostituito da *«il banco ws3-la-seconda-garanzia riporta A numerico 0/3»*; *«il
documento 08 scrive che 656 MB è ESATTO»* sostituito da *«il tag v0.7.0 è 994
commit dietro origin/main»*.

### La tesi che stavo per pubblicare, e che è caduta

Da quei sostituti scorrelati avevo tratto una spiegazione: **la supersessione non
sceglie il fatto simile, prende il fatto scritto subito dopo.** Misurato:

```
ritiri: distanza fra ritirato e sostituto     mediana  7 s   entro 60 s 79,9%
```

Sembrava una conferma netta. **Poi il controllo** — la distanza fra due fatti
**consecutivi qualunque** nella stessa finestra:

```
due fatti consecutivi qualunque (n=3412)      mediana  2 s   entro 60 s 79,7%
```

**79,9% contro 79,7%: identici.** ⇒ **la vicinanza temporale non discrimina
niente**: scriviamo a raffiche, e qualunque coppia consecutiva sta entro il
minuto nell'80% dei casi. **Senza quel controllo avrei pubblicato un numero vero
a sostegno di una tesi falsa** — la più difficile da smentire, perché il dato
c'era.

🪞 **E nel verso opposto un dato che non mi aspettavo**: i candidati a ritiro
sbagliato hanno **mediana 45 s** ed entro 60 s solo il **50,9%** ⇒ **i ritiri
sbagliati avvengono fra fatti PIÙ DISTANTI**, non più vicini — **ventinove punti**
sotto la media. Ha senso: due fatti scritti a venti minuti di distanza parlano
più facilmente di cose diverse.
⚠️ **Ma non lo vendo come criterio nuovo**: i candidati sono **definiti** dal
jaccard basso, quindi la distanza non è indipendente dalla selezione. È una
caratteristica di una popolazione già scelta; per farne un righello servirebbe
misurarla su ritiri **non** selezionati dal jaccard, e non l'ho fatto.

🔗 **E un aggancio**: il motivo che @ws7 ha trovato nel campo —
`heal_contradictions: numeric_clash clash on shared topic` — è **esattamente** il
difetto che il [63](63-la-cura-che-il-quarantadue-proponeva-e-misurabile-e-toglie-l-ottantasei-per-cento.md) misura. `numeric_conflict()` conferma l'84% delle coppie ad
alto jaccard e il 2,8% di quelle a basso: su *«139 contro 1/6 contro 0/6»* —
numeri di **grandezze diverse** — non darebbe conflitto. **Portarlo dentro
`heal_contradictions` eviterebbe proprio queste cancellazioni.**

---
*Banco: `banchi/ws6-quali-ritiri-sono-sbagliati.py`. Store di Aurelio in sola
lettura.*
