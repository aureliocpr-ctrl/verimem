# T51 — piano di ripristino dei fatti ritirati per errore

*Scritto dal ruolo Dati, 12 settembre 2026, ore 12:30 lette. Chi esegue è
l'operatore Piattaforma: qui non c'è nessuna esecuzione, solo il comando, i
conteggi attesi e i limiti.*

> ⚠️ **La finestra di undo NON si tocca in questo piano.** Allungare o rendere
> configurabile `UNDO_TTL_SECONDS` è un ticket separato (T67). Qui si usa la
> finestra com'è: sette giorni.

---

## 1. La porta, e le tre porte gemelle

Il prodotto espone la stessa operazione su tre superfici, e tutte e tre
chiamano `SemanticMemory.undo_destructive_op`:

| superficie | comando |
|---|---|
| CLI | `verimem facts undo <op_id>` · elenco: `verimem facts undo-list --limit N` |
| MCP | `hippo_undo_destructive_op` · elenco: `hippo_undo_list` |
| SDK | `Memory.undo(op_id)` |

**Per questo ripristino si usa la CLI**: è la porta che un utente ha, ed è
l'unica delle tre che stampa la tabella con `expires` accanto a ogni riga.

## 2. Che cosa fa, esattamente

`undo_log.undo_op` rilegge lo snapshot `pre_row_json` e lo riscrive con
`INSERT OR REPLACE`, **tollerante allo schema**: rilegge le colonne vive con
`PRAGMA table_info(facts)` prima di ricostruire la riga, quindi una migrazione
avvenuta dopo l'operazione non rompe il ripristino. Poi stampa `undone_at`,
così un secondo undo è un no-op.

Il campo che conta nella risposta è `action`, con quattro valori:

| `action` | significato |
|---|---|
| `restored` | fatto rimesso com'era prima del ritiro |
| `already_undone` | già ripristinato: `undone_at` valorizzato |
| `expired` | la finestra di sette giorni è passata |
| `not_found` | handle inesistente |

## 3. Il comando, in tre passi

**Passo 1 — la fotografia PRIMA (sola lettura).** Una query sul database dei
fatti, senza toccarlo:

```sql
SELECT COUNT(*) AS ritiri_totali
  FROM facts WHERE superseded_by IS NOT NULL;

SELECT COUNT(*) AS maniglie_valide
  FROM facts_undo_log
 WHERE op_type = 'supersede'
   AND undone_at IS NULL
   AND ttl_expires_at > strftime('%s','now');

SELECT COUNT(*) AS riparabili_same_source
  FROM facts_undo_log u JOIN facts f ON f.id = u.fact_id
 WHERE u.op_type = 'supersede' AND u.undone_at IS NULL
   AND u.ttl_expires_at > strftime('%s','now')
   AND f.superseded_by IS NOT NULL
   AND f.superseded_reason LIKE 'same-source evolution%';
```

**Passo 2 — l'elenco dalla porta**, che è ciò che vedrebbe l'utente:

```
verimem facts undo-list --limit 100
```

**Passo 3 — il ripristino, uno per volta**, sugli `op_id` del passo 2 il cui
`fact_id` compare nell'elenco del passo 1:

```
verimem facts undo <op_id>
```

⚠️ **Uno per volta e con l'esito letto**: `action` va guardato riga per riga.
Un `expired` in mezzo al lotto non è un errore dell'operatore — è la finestra
che è passata mentre il lotto girava.

## 4. I conteggi attesi

🔴 **I numeri vanno RILETTI al momento dell'esecuzione, non presi da qui.** La
finestra scorre: ogni ora una fetta di maniglie scade. I numeri qui sotto sono
la fotografia del **10 settembre alle 21:27**, e servono come ordine di
grandezza e come verifica che il righello sia lo stesso, non come attesa:

```
ritiri nel corpus                      : 2414
maniglie di undo valide                :   90
riparabili fra i «same-source evolution»:   62   (su 530)
```

**Atteso il 12 settembre**: meno di 90 e meno di 62, perché due giorni di
finestra sono passati e le maniglie più vecchie di sette giorni sono uscite.
**Se il numero fosse uguale o maggiore, il righello è sbagliato** — è il
controllo che questo piano porta con sé.

**Dopo il ripristino**, attesi:

| grandezza | prima | dopo |
|---|---|---|
| fatti con `superseded_by` non nullo | N | N − (quanti `restored`) |
| voci con `undone_at` valorizzato | M | M + (quanti `restored`) |
| righe rese da una ricerca sul contenuto ripristinato | 0 | ≥ 1 |

L'ultima riga è quella che conta per chi usa il prodotto: **il fatto non deve
solo tornare nella tabella, deve tornare quando lo si chiede**. La verifica è
una ricerca dalla porta su una parola del fatto ripristinato, scelta prima di
eseguire.

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

## 6. La conseguenza da mettere in conto

Lo snapshot rimette il fatto vecchio **com'era**, cioè con `superseded_by`
nullo. **Il fatto nuovo non viene toccato.** ⇒ Dopo il ripristino i due fatti
sono **entrambi vivi**, e se erano davvero in contraddizione la memoria ne
serve due invece di uno.

Per i ritiri di questo lotto è l'esito **voluto**: sono letture complementari
della stessa evidenza (la mediana e il minimo della stessa esecuzione, i due
bracci dello stesso confronto), e tenerle entrambe è la riparazione. Ma è un
esito che va dichiarato prima di eseguire, non scoperto dopo: **chi ripristina
un ritiro legittimo si ritrova due valori dello stesso dato**, e nessuno dei
due dichiara di essere il più recente.

⇒ Per questo il lotto va ristretto ai ritiri con `superseded_reason` che
comincia per `same-source evolution`, e non esteso a tutti i ritiri con una
maniglia valida.

## 7. Il criterio di fine

Il ripristino è finito quando:

- ogni `op_id` del lotto ha un esito letto (`restored`, `expired` o
  `already_undone`), e il conto dei tre torna al totale del lotto;
- i due conteggi del passo 1, rieseguiti, si sono mossi **della stessa
  quantità** e in direzioni opposte;
- una ricerca dalla porta su un fatto ripristinato lo rende;
- l'esito è scritto con l'output, compresi gli `expired`: **un ripristino
  parziale annunciato come completo è peggio di nessun ripristino**, perché
  chiude la domanda invece di lasciarla aperta.
