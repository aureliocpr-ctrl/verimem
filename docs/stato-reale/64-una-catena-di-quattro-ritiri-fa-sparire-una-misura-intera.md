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

---
*Banco: `banchi/ws6-quali-ritiri-sono-sbagliati.py`. Store di Aurelio in sola
lettura.*
