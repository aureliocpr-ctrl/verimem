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

🔗 **E un aggancio**: il motivo che @ws7 ha trovato nel campo —
`heal_contradictions: numeric_clash clash on shared topic` — è **esattamente** il
difetto che il [63](63-la-cura-che-il-quarantadue-proponeva-e-misurabile-e-toglie-l-ottantasei-per-cento.md) misura. `numeric_conflict()` conferma l'84% delle coppie ad
alto jaccard e il 2,8% di quelle a basso: su *«139 contro 1/6 contro 0/6»* —
numeri di **grandezze diverse** — non darebbe conflitto. **Portarlo dentro
`heal_contradictions` eviterebbe proprio queste cancellazioni.**

---
*Banco: `banchi/ws6-quali-ritiri-sono-sbagliati.py`. Store di Aurelio in sola
lettura.*
