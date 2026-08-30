# Gli episodi si ricordano di essere stati letti, e nessuno li dimentica mai

*ws6/Aldo — 30/08, notte. Perimetro: archivio, memoria, corpus.*

Ultima area del mio perimetro rimasta fuori da questa serie: gli **episodi**.
L'indice della memoria li cita fra gli aperti come «tier episodi fermo», con un
puntatore al fatto `02d16947285b`.

## Il puntatore non punta

Ho letto il fatto invece della sintesi — è la disciplina che stanotte mi ha già
salvato una volta, quando ho scoperto che la lezione su `L1` era di maggio e
misurata su undici casi. Il fatto `02d16947285b` dice:

> *«Su 65 same-source evolution il vincitore cita l'id esatto del fatto che
> ritira in 6 casi.»*

**Non parla di episodi.** È un fatto sulle supersessioni, usato nell'indice come
riferimento per un elenco di aperti eterogenei. Non è un errore grave, ma è la
seconda volta stanotte che una citazione dell'indice non regge alla lettura:
**la sintesi e il fatto vanno riverificati insieme, o il puntatore invecchia
senza che nessuno se ne accorga.**

Quindi la misura l'ho fatta da zero.

## Gli episodi vengono usati — e questo va detto per primo

Alle **22:34:22 del 30/08**, su `~/.engram/episodes/episodes.db` in sola lettura:

    episodi: 470

| accessi | episodi | cumulato |
|---|---|---|
| **0** | **120** | 25,5% |
| 1 | 54 | 37,0% |
| 2 | 76 | 53,2% |
| 3 | 57 | 65,3% |
| 4-6 | 83 | 83,0% |

**Tre episodi su quattro sono stati riletti almeno una volta.** E non è storia
vecchia: l'ultimo accesso cade in **agosto per 170 di essi** (maggio 117, giugno
57, luglio 6), mentre la creazione è concentrata a maggio (386 su 470).

Contro l'intuizione — la mia compresa, prima di misurare — **l'archivio degli
episodi non è un deposito che nessuno interroga**.

## Che cosa conta davvero quel contatore

Prima di fidarmi ho cercato chi lo incrementa. È `_bump_access_tracking` in
`verimem/memory.py:1507`, e il suo docstring dice da dove viene chiamato:

> *«Atomic update of `last_accessed_at` and `access_count` for every recalled
> episode. **Called by `recall()`** after the result set is computed… Ebbinghaus-
> curve recovery (spaced repetition: recall strengthens memory) lives here.»*

Quindi conta le **recall vere**, non i passaggi del consolidamento: il numero
non è gonfiato da processi automatici. **Con una precisazione onesta: misura
«servito», non «usato».** Il contatore sale quando l'episodio finisce nel
risultato, anche se chi ha chiesto poi lo ignora. Il 74,5% è un limite
superiore all'utilità reale.

E non è un contatore decorativo: alimenta la **retention** (`episode.py:127`,
`_RETENTION_GAMMA_ACCESS * float(self.access_count)`), cioè quanto un episodio
resiste al passare del tempo. Ebbinghaus 1885, citato nel codice.

## E qui arriva la parte che conosciamo già

    episodi 470   invalidati 0   pinned 0

| | n | salience media |
|---|---|---|
| mai serviti | 120 | **0,248** |
| serviti | 350 | **0,449** |

*(nessun episodio ha `salience_score` nullo: è calcolata per tutti)*

**La salience funziona.** Discrimina davvero: gli episodi che vengono serviti
valgono quasi il doppio di quelli che nessuno chiede mai. Il meccanismo è
implementato, alimentato da un contatore onesto, e produce un numero sensato.

**E nessun episodio è mai stato dimenticato.** Zero invalidati, su 470, in tre
mesi. L'oblio esiste — il prodotto espone `decay_simulate` e `decay_run` — ma
come **comando manuale**, e non risulta mai eseguito su questo store.

È la stessa forma trovata nel documento 36 per il pavimento di rilevanza: **una
capacità presente, corretta, misurabile e spenta**. Là era un default a `None`;
qui è un comando che nessuno lancia. In entrambi i casi il prodotto **sa fare la
cosa e non la fa**, e in entrambi i casi non se ne accorge nessuno perché non
c'è niente che segnali l'inerzia.

**Non dimenticare non è un difetto in sé** — è conservativo, e su una memoria di
lavoro è probabilmente la scelta giusta. Il difetto è che la salience venga
calcolata per 470 episodi, discrimini correttamente, e **non abbia alcun
consumatore**.

## Per chi riprende

- Il righello è `docs/stato-reale/banchi/ws6-gli-episodi-riletti.py` (sola
  lettura; **nessun `decay_run`**: è una scrittura persistente e non mi è stata
  chiesta).
- **La domanda da porre a chi decide**: la salience deve restare un numero
  informativo, o `decay_run` va messo in un ciclo? Con 120 episodi mai serviti e
  salience media 0,248, il materiale per una prima potatura c'è — ma è una
  decisione, non una misura.
- **Quello che non ho misurato**: `episode_telemetry` ha **652 righe** contro 470
  episodi. Più telemetria che episodi: o registra più eventi per episodio, o
  contiene tracce di episodi non più presenti. Non l'ho aperta.
- **Da correggere nell'indice della memoria**: «tier episodi fermo →
  `02d16947285b`» punta a un fatto sulle supersessioni.

---

**Verifica**: `~/.engram/episodes/episodes.db` in `mode=ro`, sole `SELECT`.
Istante 22:34:22 del 30/08. Nessuna scrittura, nessun `decay_run`.
