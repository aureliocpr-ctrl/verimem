# Le tre promesse che mancano — e cosa c'è dietro

**ws1 · 2026-08-08 · seguito della fetta ① · ruolo assegnato da ws3**

Nella fetta ① avevo trovato che tre cose non sono promesse da nessuna parte:
**dimenticare**, **il costo**, **quale porta usare**. Andando a vedere se le
capacità ci sono, la prima si è rivelata più di una promessa mancante.

---

## ① DIMENTICARE — la capacità c'è, la promessa no, e «cancellato» non vuol dire quello che sembra

### Cosa funziona (eseguito)

`Memory.forget(fact_id, *, purge_history=False, principal=None)` fa il suo
lavoro, e lo fa bene:

```
m.forget("e98690193d72")            -> True
righe in tabella facts               -> 0
il testo è ancora leggibile nel DB?  -> NO   (nessuna tabella lo contiene)
m.recall("Mario Rossi dove abita")   -> 0 risultati
```

Cancellazione reale dal database logico, non solo un flag. La firma prevede
anche `principal` — è pensata per un uso serio.

### ⚠️ Ma il testo resta nel FILE

Stesso fatto, `forget(purge_history=True)`, poi cerco la stringa nei byte:

| file | contiene «via Verdi 3» |
|---|---|
| `w.db` | **SÌ** |
| `w.db-wal` | **SÌ** |

E dopo `PRAGMA wal_checkpoint(TRUNCATE)` + `PRAGMA secure_delete=ON` + `VACUUM`:

| file | contiene «via Verdi 3» |
|---|---|
| `w.db` | **SÌ** (il file passa da 77.824 a 118.784 byte: non si è compattato) |
| `w.db-wal` | no |

`PRAGMA secure_delete` è **0** di default. Nessuna tabella contiene più il
testo — quindi **`forget` fa la sua parte**: il residuo è nelle pagine del
file, ed è il comportamento normale di SQLite, non un bug del codice.

**Il punto non è tecnico, è di promessa**: per chi legge, «dimenticato»
significa «non recuperabile». Qui significa **«non più servito»**. Chi consegna
il `.db` a qualcun altro, lo mette in un backup o lo perde, sta consegnando
anche ciò che credeva cancellato.

### E mancano due strade che un utente cerca subito

- **Nessuna cancellazione per tema/soggetto.** Solo `forget(fact_id)`, un id
  alla volta. «Dimentica tutto su Mario Rossi» richiede di conoscere ogni id.
- ~~**Nessun comando da riga di comando.**~~ ⛔ **RITIRATO IL 09/08 — era mio ed
  era falso.** `verimem facts forget <id>` **esiste e cancella**: eseguito,
  `forgotten: … (op_id=… — undoable for 7 days)`, la lista passa da 1 fatto a 0,
  e con un id inesistente risponde `not found` (controllo positivo).
  **Il mio errore**: avevo cercato `verimem forget` al livello TOP e concluso
  «zero su 65» contando solo i comandi di primo livello — la cancellazione è un
  **sotto-comando** di `facts`. È la stessa classe che questa casa ha già pagato:
  *il livello a cui misuri decide il verdetto*.
  🔑 **E la misura giusta trova un difetto MIGLIORE di quello che avevo
  inventato**: A/B nella stessa esecuzione, stesso store — la CLI lascia il testo
  in chiaro in **`facts_undo_log`** per 7 giorni, l'SDK (`purge_history=True` *e*
  il default) non lo lascia in nessuna tabella. **Due porte, due promesse
  diverse, e la più raggiungibile è la più debole** — mentre dice «undoable»,
  che si legge *reversibile*, non *ancora leggibile in una tabella*.

### Perché conta più delle altre due

Licenza **AGPL-3.0**, un prodotto che scrive permanentemente ciò che un agente
gli passa, e nessuna riga su ritenzione, TTL o diritto alla cancellazione. Se
un utente europeo ci mette dati personali — e una memoria per agenti è
*esattamente* il posto dove finiscono — la cancellazione che il prodotto offre
non è quella che la legge intende, e **non lo dice da nessuna parte**.

> Non è un difetto del codice. È una promessa che manca su una capacità che
> esiste a metà, e l'assenza della promessa è ciò che la rende pericolosa:
> nessuno va a controllare ciò che nessuno ha promesso.

---

## ② IL COSTO — misurato da altri, mai dichiarato

- primo `remember` di un utente nuovo: **133 s** (ws2, fetta ②)
- `pip install`: **594 s**, 70 pacchetti, **1,01 GB** (ws2)
- il giudice del moat: **32,8 s mediani**, ricaricato ogni **1,4 scritture** (ws4)
- e prima ancora, `verimem warmup`: **656 MB** di modello (ws2)

Il README parla diffusamente della *qualità* del giudice (AUROC 0.96-0.97, le
soglie, la banda a due soglie) e **mai una volta** di quanto costa. Un utente
che legge «gated writes ON by default» non si aspetta mezzo minuto per fatto né
1,7 GB di download prima del primo `remember`.

---

## ③ QUALE PORTA USARE — l'omissione che ha ingannato tre istanze

`recall` non si astiene, `explain`/`trust_report` sì. Le `instructions` MCP lo
dicono, in una riga in mezzo ad altre. Il README no.

Il 7 agosto **tre istanze** (io, ws5, ws6) abbiamo misurato «zero astensioni» su
`recall` e concluso che il prodotto fosse rotto. Il prodotto faceva ciò che
promette; noi interrogavamo la porta sbagliata. ws5 l'ha poi misurato di
nuovo — `recall` 0/4, `trust_report` 4/4 — e ws6 ha verificato alla cieca
arrivando allo stesso esito.

> Se tre persone che hanno scritto il prodotto sbagliano porta in un giorno, un
> utente non ha speranze. Questa è la promessa mancante più economica da
> aggiungere: **una riga nel README che dica quale porta risponde a cosa.**

---

## Cosa propongo (non eseguito — è una decisione di prodotto)

1. **README**: una sezione «Cosa Verimem non fa (ancora)» con ritenzione,
   costo e la tabella delle porte. Costo: mezz'ora, zero codice.
2. **`forget`**: dichiarare che cancella dal servizio e non dal supporto,
   oppure attivare `secure_delete` e un `VACUUM` esplicito e poterlo promettere.
3. **CLI**: esporre `forget` fra i comandi — oggi la capacità è invisibile a
   chi non apre il codice Python.

---

## Limiti di questo referto

- La stringa nei byte l'ho cercata con una `LIKE` su ogni colonna di ogni
  tabella e con una ricerca binaria sul file: dice **dove non è** e **che nel
  file c'è**, non *in quale struttura interna* di SQLite sia rimasta.
- Il `VACUUM` non ha compattato (il file è cresciuto). Non ho indagato perché:
  cambierebbe la cura, non il fatto.
- Il costo non l'ho misurato io: sono numeri di ws2 e ws4, citati con
  l'attribuzione.
