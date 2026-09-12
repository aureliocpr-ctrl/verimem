# T51 — piano di ripristino dei fatti ritirati per errore

*Scritto dal ruolo Dati, 12 settembre 2026, ore 18:40 lette. Chi esegue è
l'operatore Piattaforma: qui non c'è nessuna esecuzione, solo il comando, i
conteggi attesi e i limiti.*

> ⚠️ **La finestra di undo NON si tocca in questo piano.** Allungare o rendere
> configurabile `UNDO_TTL_SECONDS` è un ticket separato (T67). Qui si usa la
> finestra com'è: sette giorni.

---

## 1. La porta, e le tre porte gemelle

Il prodotto espone la stessa operazione su tre superfici, e tutte e tre
chiamano `SemanticMemory.undo_destructive_op` (`verimem/semantic.py:5601`):

| superficie | comando |
|---|---|
| riga di comando | `verimem facts undo <op_id>` |
| server di strumenti | `hippo_undo_destructive_op` |
| libreria | `Memory.undo(op_id)` |

**Per questo ripristino si usa la riga di comando**: è la porta che un utente
ha, ed è l'unica delle tre che stampa, accanto a ogni ritiro, **sia l'esito
sia la maniglia per annullarlo**.

## 2. Che cosa fa, esattamente

`undo_log.undo_op` (`verimem/undo_log.py:199`) rilegge lo snapshot
`pre_row_json` e lo riscrive con `INSERT OR REPLACE`, **tollerante allo
schema**: rilegge le colonne vive con `PRAGMA table_info(facts)` prima di
ricostruire la riga, quindi una migrazione avvenuta dopo l'operazione non
rompe il ripristino. Poi stampa `undone_at`, così un secondo undo è un no-op.

Lo snapshot è preso **prima** dell'UPDATE e nella **stessa transazione**
(`verimem/semantic.py:5944-5946`): la riga salvata è quella di un fatto
**vivo**, con `superseded_by` nullo. Ripristinarla è ciò che rimette il fatto
in circolo.

Il campo che conta nella risposta è `action`, con quattro valori
(`verimem/cli.py:3756-3771`):

| `action` | significato | uscita |
|---|---|---|
| `restored` | fatto rimesso com'era prima del ritiro | 0 |
| `already_undone` | già ripristinato: `undone_at` valorizzato | 0 |
| `expired` | la finestra di sette giorni è passata | 0 |
| `not_found` | handle inesistente | **1** |

⚠️ **Tre dei quattro esiti escono con 0.** Un lotto che stampa `expired` su
tutte le righe termina «bene»: l'esito si legge **riga per riga**, non
dall'uscita del processo.

## 3. Il comando, in quattro passi

**Passo 0 — la copia di sicurezza, e non è una formalità.** L'undo dell'undo
**non esiste** (§6b: `INSERT OR REPLACE` riscrive la riga intera). Questa copia
è l'unica marcia indietro del lotto:

```
verimem facts backup --tier manual
verimem facts safety
```

Il primo stampa `backup ok: <path>` con `size`, **`facts: <n>`** e `tier`, e
verifica un'impronta di integrità contro il DB vivo prima di dichiarare
riuscito (`verimem/cli.py:4019-4030`). ⚠️ **Il `facts: <n>` si confronta con il
`written` del passo 1**: se i due numeri non coincidono, la copia è di un altro
store — è la trappola dei due DB, e qui si accende prima di fare danni.

Il secondo elenca l'ultimo backup per tier con la sua età e il numero di
maniglie annullabili (`verimem/cli.py:4077-4083`): è il controllo che la copia c'è
**dalla porta**, non guardando una cartella.

📌 Il tier `manual` **non viene ruotato**: `DEFAULT_POLICY`
(`verimem/backup.py:84-88`) ha solo `daily`/`weekly`/`monthly`, e la rotazione
itera su quelle chiavi (`verimem/backup.py:513`). ⇒ La copia resta finché non
la si toglie a mano — voluto qui, ma è un file che nessuno cancella per te.

**La via di ritorno, se il lotto va storto:**

```
verimem facts restore <il path stampato dal backup> --yes
```

Tiene una **copia pre-restore** e stampa `facts: <n>` alla fine
(`verimem/cli.py:4070-4074`); **rifiuta** un backup che non è di questo store o
non è un DB SQLite, senza toccare il bersaglio (`verimem/cli.py:4066-4069`).
Senza `--yes` chiede conferma: in coda a un lotto automatico, si passa `--yes`
**solo dopo aver riletto il path**.

🔑 **Il registro delle maniglie sta nello stesso file dei fatti** — `undo_op`
scrive `facts_undo_log` sulla connessione di `facts`
(`verimem/undo_log.py:248-251`, `verimem/semantic.py:5609-5610`). ⇒ Un
restore riporta indietro **anche gli `undone_at`**: il lotto non resta a
metà, si rifà da capo con le stesse maniglie.

**Passo 1 — la fotografia PRIMA, dalla porta.** Il quartetto canonico, che
porta con sé la propria definizione di «servibile»:

```
verimem facts retirement-log --counts
```

stampa `written / servable / retired / quarantined` più la formula
(`verimem/retirement_log.py:756`). ⚠️ **Si annota `retired` E `servable`**: il
ripristino tocca `superseded_by`, non `status`, e il predicato di servibilità
è `superseded_by IS NULL AND status NOT IN ('quarantined')`
(`verimem/retirement_log.py:80`). Sono due numeri diversi e si muovono di
quantità diverse — §4.

**Passo 2 — il lotto, con la maniglia nella stessa riga:**

```
COLUMNS=200 verimem facts retirement-log --reason "same-source evolution" --limit 100
```

La colonna `undo` porta **l'op_id se il ritiro è reversibile, altrimenti il
perché no** — «nessuno scatto», «finestra scaduta», «già annullato»
(`verimem/cli.py:3982-3983`). Il filtro `--reason` è un confronto **esatto** su
`superseded_reason` (`verimem/retirement_log.py:157-159`) e la stringa scritta
dal prodotto è esattamente `same-source evolution` (`verimem/client.py:982`,
`verimem/mcp_server.py:13956`).

> ⚠️ **Perché NON `facts undo-list`.** Quel comando elenca le maniglie valide
> ma **non porta il motivo del ritiro** (`verimem/cli.py:3778-3804`): con esso
> il lotto si seleziona incrociando a mano una tabella di op_id con una query
> SQL sui fact_id. `retirement-log --reason` restituisce le righe già filtrate
> **e** l'op_id, da una porta sola, senza SQL. La capacità c'era: non era usata.

**Passo 3 — il ripristino, uno per volta**, sugli op_id raccolti al passo 2:

```
verimem facts undo <op_id>
```

## 3bis. Le tre trappole della copia (tutte e tre stanno fra il passo 2 e il 3)

1. **L'op_id è lungo 16 caratteri esadecimali** (`uuid4().hex[:16]`,
   `verimem/undo_log.py:176`). La tabella è una griglia Rich su console a
   larghezza automatica (`verimem/cli.py:202`) e su terminale stretto tronca
   con un'ellissi — il difetto è dichiarato nel prodotto stesso
   (`verimem/cli.py:3740-3744`: incollare ciò che si vede risponde «not
   found»). ⇒ **`COLUMNS=200` davanti al comando**, e il controllo prima di
   incollare: **16 caratteri, tutti in `0-9a-f`, nessun «…»**.
2. **Il prefisso risolve solo fra le 200 maniglie valide più recenti**
   (`verimem/cli.py:3746`: `list_undoable_ops(limit=200)`). Sotto quella
   soglia il prefisso è comodo; sopra, un prefisso legittimo risponde
   `not found` **senza dire perché**. ⇒ Con 90 maniglie valide (misura del 10
   settembre) siamo dentro, ma **si incolla l'op_id intero**, non il prefisso:
   costa niente e toglie il caso ambiguo.
3. **Un prefisso che matcha più di una maniglia esce con 2** e non ripristina
   niente (`verimem/cli.py:3749-3752`). È un esito distinto da `not_found` e
   va contato a parte.

## 4. Il conteggio atteso dopo — la predizione, e il comando che la smentisce

Sia **R** il numero di righe che hanno stampato `restored`. Dopo il lotto, con
`verimem facts retirement-log --counts` rieseguito:

| grandezza | prima | dopo, atteso |
|---|---|---|
| `retired` | N | **N − R** |
| voci `facts_undo_log` con `undone_at` valorizzato | M | **M + R** |
| `servable` | S | **S + R − q** |
| `written` | W | **W** (invariato) |
| righe rese da una ricerca sul contenuto ripristinato | 0 | **≥ 1** |

dove **q** = quanti dei fatti ripristinati erano `quarantined` **al momento
dello scatto**. Lo snapshot rimette la riga com'era, `status` compreso: un
fatto fermato dal gate e poi ritirato torna con `superseded_by` nullo **e
ancora quarantinato** — esce dai `retired` e non entra nei `servable`.

🔑 **`q` è la ragione per cui la prima riga e la terza non sono la stessa
riga.** Se si annota solo `retired`, un lotto che non ha restituito **nessun
fatto all'utente** mostra lo stesso calo. Predizione dichiarata: **q = 0** su
questo lotto (un fatto quarantinato non arriva alla politica della
supersessione), ed è **falsificabile dal comando stesso** — se `servable` sale
di meno di `R`, la predizione è sbagliata e il numero di `q` è la differenza.

**I due conteggi centrali si muovono della stessa quantità in direzioni
opposte.** Se non lo fanno, qualcosa fuori dal lotto ha scritto durante
l'esecuzione, e il lotto va rimisurato prima di dichiararlo.

**L'ultima riga è quella che conta per chi usa il prodotto:** il fatto non
deve solo tornare nella tabella, deve tornare **quando lo si chiede**.

```
verimem recall "<una parola del fatto ripristinato, scelta PRIMA di eseguire>"
verimem facts search "<la stessa parola>"
```

⚠️ **Si sceglie prima**, non dopo: una parola scelta guardando l'esito misura
la propria memoria, non il prodotto. **Due comandi e non uno**: `recall` è la
porta che un utente usa (`verimem/cli.py:1573`), `facts search` la rotta sui
soli fatti (`verimem/cli.py:3375`) — se il fatto torna da una e non
dall'altra, il ripristino è a metà e lo si sa subito.

**E l'indice non va ricostruito a mano.** `INSERT OR REPLACE` passa per un
DELETE e un INSERT sulla tabella `facts`, e i trigger `facts_fts_ad` /
`facts_fts_ai` (`verimem/bm25_rank.py:165-177`) rifanno la riga indicizzata;
l'embedding è una **colonna di `facts`** (`verimem/semantic.py:668`), quindi
lo snapshot lo riporta con sé.
📌 **NON VERIFICATO da esecuzione** — letto nel codice, non eseguito: il
controllo è la ricerca qui sopra, che è rossa se questa lettura è sbagliata.

### I numeri di riferimento, e perché non sono l'attesa

🔴 **Vanno RILETTI al momento dell'esecuzione.** La finestra scorre: ogni ora
una fetta di maniglie scade. Fotografia del **10 settembre alle 21:27**:

```
ritiri nel corpus                        : 2414
maniglie di undo valide                  :   90
riparabili fra i «same-source evolution» :   62   (su 530)
```

**Atteso il 12 settembre**: meno di 90 e meno di 62, perché due giorni di
finestra sono passati. **Se il numero fosse uguale o maggiore, il righello è
sbagliato** — è il controllo che questo piano porta con sé.

## 5. Che cosa NON si ripristina, e perché

1. **I ritiri più vecchi di sette giorni.** `undo_op` risponde `expired` e non
   tocca niente. È la maggioranza: al 10 settembre, 468 dei 530 ritiri
   `same-source evolution` non avevano più una maniglia valida.
2. **I ritiri per cui la maniglia non è mai stata creata.** La voce più
   vecchia nel registro è del 3 settembre: tutto ciò che è stato ritirato prima
   non ha snapshot, e nessun comando lo riporta indietro.
3. **I fatti fermati dal gate** (`quarantined`). Non sono ritiri e non hanno
   una voce in questo registro: restano dove sono, ed è la promessa del
   prodotto che lo vuole.
4. **La potatura volontaria** (gli snapshot di sessione, la deduplicazione di
   testo identico). Ripristinarli peggiorerebbe il corpus invece di ripararlo.

## 6. Le due conseguenze da mettere in conto

**(a) Dopo il ripristino i due fatti sono entrambi vivi.** Lo snapshot rimette
il vecchio com'era; **il nuovo non viene toccato** — l'undo scrive una riga
sola, quella del perdente. Se erano davvero in contraddizione, la memoria ne
serve due invece di uno.

Per i ritiri di questo lotto è l'esito **voluto**: sono letture complementari
della stessa evidenza (la mediana e il minimo della stessa esecuzione, i due
bracci dello stesso confronto), e tenerle entrambe è la riparazione. Ma va
dichiarato prima di eseguire, non scoperto dopo: **chi ripristina un ritiro
legittimo si ritrova due valori dello stesso dato**, e nessuno dei due dichiara
di essere il più recente. ⇒ Per questo il lotto è ristretto ai ritiri con
`superseded_reason` esattamente `same-source evolution`, e non esteso a tutti i
ritiri con una maniglia valida.

**(b) Il ripristino sovrascrive la riga INTERA, non solo le tre colonne del
ritiro.** `INSERT OR REPLACE` riscrive tutte le colonne dallo snapshot: ciò che
è cambiato su quel fatto **dopo** il ritiro — un `last_verified_at`
aggiornato, una quarantena decisa da un triage, un `grounding_score` arrivato
più tardi — **torna al valore di prima e non è recuperabile**. Sul lotto di
ritiri automatici questo è improbabile ma non impossibile, e non esiste un
comando che lo annulli: l'undo dell'undo non c'è. ⇒ **È la ragione del
passo 0**: la copia di sicurezza è l'unica marcia indietro che questo
lotto ha.

## 7. Il criterio di fine

Il ripristino è finito quando:

- la copia del passo 0 esiste e il suo `facts:` coincideva con `written`
  **prima** di iniziare (dopo non prova più niente);
- ogni op_id del lotto ha un esito letto (`restored`, `expired`,
  `already_undone`, `not_found` o prefisso ambiguo), e il conto dei cinque
  torna al totale del lotto;
- `retired` e le voci con `undone_at` valorizzato si sono mossi **della stessa
  quantità** e in direzioni opposte;
- `servable` è salito di `R`, oppure la differenza è spiegata da `q` **con i
  fatti nominati**, non stimata;
- una ricerca dalla porta su un fatto ripristinato lo rende;
- l'esito è scritto con l'output, compresi gli `expired`: **un ripristino
  parziale annunciato come completo è peggio di nessun ripristino**, perché
  chiude la domanda invece di lasciarla aperta.
