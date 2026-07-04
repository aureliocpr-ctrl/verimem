# Cycle 156 — Design doc: chiusura del gap cross-process per HIGH#2 TOCTOU

**Status**: DESIGN (no implementation in this cycle)
**Author**: Senior Engineer cycle 156 (2026-05-19)
**Predecessor**: cycle 155 (`threading.Lock` in-process, `engram/consolidation.py:80`)
**Successor**: cycle 157 implementation (TDD)

---

## 1. Problema empirico

### 1.1 Stato attuale post-cycle 155
Il fix cycle 155 ha introdotto un **module-level `threading.Lock`** (`engram/consolidation.py:80`, variabile `_CONSOLIDATE_LOCK`) con pattern double-checked locking dentro `auto_consolidate` (linee 324–362). Il blocco serializza, **per singolo processo Python**, la sequenza `_cluster_already_consolidated → _persist_master`.

Test `tests/test_consolidation_toctou.py` copre il caso 2 thread paralleli stesso interprete con `threading.Barrier`.

### 1.2 Gap residuo
Due processi Python **separati** (es. due cron job, due MCP server in parallelo, una sessione interattiva + un hook SessionStart) che aprono lo stesso `data/semantic/semantic.db` non condividono la `_CONSOLIDATE_LOCK` — la `threading.Lock` vive nello spazio di indirizzamento del singolo interprete. La race window `_preload_consolidated_prefixes → _persist_master` rimane aperta cross-process.

Conseguenza misurabile: dopo 2 chiamate parallele cross-process, `_count_masters_for_prefix(prefix)` può tornare `2` invece di `1` per lo stesso cluster. Duplicato master Fact + duplicato master Episode + edge duplication.

### 1.3 Limiti del test cycle 155
`tests/test_consolidation_toctou.py:75–126` usa `threading.Thread`. Impossibile testare cross-process da Python threading: serve `subprocess.Popen` o `multiprocessing.Process`. **Il gap è non solo nel codice, ma anche nella copertura di test.**

### 1.4 Evidenza on-disk
Probe empirico sul `data/semantic/semantic.db` in questo checkout: schema **v1** (cycle 155 non è ancora stato eseguito su questa copia), zero righe AUTO-CLUSTER-MASTER. Verifica empirica della consistenza cross-process **da rifare** sul DB di Aurelio post-deploy cycle 155 (`SELECT topic, COUNT(*) FROM facts WHERE topic LIKE '%/auto-MASTER' AND superseded_by IS NULL GROUP BY topic HAVING COUNT(*) > 1`).

---

## 2. Tre alternative architetturali

### A. UNIQUE INDEX condizionale (schema migration v4)
**DDL**:
```sql
CREATE UNIQUE INDEX idx_facts_auto_master_unique
ON facts(topic)
WHERE superseded_by IS NULL
  AND proposition LIKE 'AUTO-CLUSTER-MASTER%';
```
- **Pro**: vincolo at-rest, cross-process by design (SQLite enforce a write time). Nessun lock applicativo necessario. Fail-fast con `IntegrityError` su seconda write.
- **Contro**: schema migration richiesto. Se DB pre-cycle 156 contiene **già duplicati**, la creazione dell'indice fallisce. Necessario pre-clean (vedi §2.A.1).

#### 2.A.1 Pre-clean richiesto in migration
Prima di `CREATE UNIQUE INDEX`:
```sql
-- mark all duplicates beyond the oldest as superseded_by=oldest
UPDATE facts SET superseded_by = (
  SELECT MIN(id) FROM facts f2
  WHERE f2.topic = facts.topic AND f2.superseded_by IS NULL
    AND f2.proposition LIKE 'AUTO-CLUSTER-MASTER%'
), superseded_at = strftime('%s','now'), superseded_reason = 'cycle156-dedup'
WHERE id IN (
  SELECT id FROM facts
  WHERE proposition LIKE 'AUTO-CLUSTER-MASTER%' AND superseded_by IS NULL
    AND id NOT IN (
      SELECT MIN(id) FROM facts WHERE proposition LIKE 'AUTO-CLUSTER-MASTER%'
        AND superseded_by IS NULL GROUP BY topic
    )
);
```
Costo: una sola SELECT/UPDATE pass, idempotente.

### B. `BEGIN IMMEDIATE` nello slow-path di `_persist_master`
**Pattern**:
```python
with sm._connect() as conn:
    conn.execute("BEGIN IMMEDIATE")  # writer lock cross-process
    # re-check exists
    # if not exists → store fact + ep + edges
    # commit
```
- **Pro**: nessun schema change. SQLite file-lock writer-exclusive cross-process (WAL mode: writer lock).
- **Contro**: `sm.store(fact)` apre la propria connessione (`semantic.py:451 with self._connect() as conn`). Per usare `BEGIN IMMEDIATE` correttamente serve refactor — il transaction stesso deve abbracciare Episode.store + Fact.store + edge insert su **una sola connessione condivisa**. Cycle 155 commenta esattamente questo (`consolidation.py:14-16`: "non-banale perché sm.store apre la sua connessione interna"). Refactor estensivo, alto rischio di regressione su semantic v3 gate logic (`semantic.py:362-489`).
- Performance: tutte le auto_consolidate cross-process sequenzializzate via file lock. WAL `busy_timeout=60000` (semantic.py:327) significa fino a 60s di attesa prima dell'errore.

### C. File system advisory lock (msvcrt/fcntl + lockfile)
**Pattern**:
```python
lock_path = sm.db_path.with_suffix(".consolidate.lock")
with open(lock_path, "w") as lf:
    msvcrt.locking(lf.fileno(), msvcrt.LK_LOCK, 1)  # Windows
    # fcntl.flock(lf, fcntl.LOCK_EX) on POSIX
    # ...auto_consolidate body...
```
- **Pro**: zero schema change, indipendente da SQLite internals. Funziona cross-process out-of-the-box.
- **Contro**: piattaforma-specifico (msvcrt ≠ fcntl). Lockfile orfani se processo crasha senza unlock (su Linux `LOCK_EX` viene rilasciato a process exit, su Windows `LK_LOCK` parimenti — **da verificare empiricamente** su Windows 11). Aggiunge artefatto FS estraneo al modello concettuale "DB SQLite single source of truth". Maintenance burden: chi capisce il pattern in 6 mesi deve conoscere semantiche FS locking di entrambi gli OS.

---

## 3. Trade-off matrix

| Asse | A. UNIQUE INDEX | B. BEGIN IMMEDIATE | C. Advisory lock |
|------|-----------------|--------------------|--------------------|
| **Backward compat** | richiede pre-clean migration (duplicati pre-existing) | nessun problema (no DDL) | nessun problema |
| **Migration risk** | medio (v3→v4 + UPDATE pre-clean), reversibile (DROP INDEX) | nessuno | nessuno (file lock indipendente) |
| **Perf overhead** | trascurabile: 1 index B-tree lookup per write, costo amortizzato | high: cross-process write serialization, busy_timeout fino a 60s | medio: file-lock acquire ~µs locale, ma serializza tutto auto_consolidate |
| **Maintenance** | basso: pattern SQL standard, ben documentato | alto: refactor di `_persist_master` per condividere `conn` tra Episode/Fact/edges; rischio rottura semantic gate v3 | medio: due API OS-specifiche (msvcrt + fcntl); pattern non standard nel resto del codebase |
| **Test coverage** | facile: `subprocess.Popen` × 2 → assert COUNT=1, oppure spawn diretto con `multiprocessing` | medio: serve forzare race su file-lock writer, timing-sensitive | medio: stesso pattern di B, più test cross-OS |

---

## 4. Falsifiabilità (B2)

### A. UNIQUE INDEX — counterexample
> **Falsificato se** la SQLite linkata da Python è < **3.8.0** (partial unique index non supportato pre-3.8.0, vedi https://sqlite.org/partialindex.html).
>
> **Verifica empirica eseguita**: `python -c "import sqlite3; print(sqlite3.sqlite_version)"` → **3.51.1** sul build corrente (riga 1, Python harness 3.13). Verifica runtime: test `CREATE UNIQUE INDEX … WHERE … AND … LIKE …` con doppia INSERT → seconda solleva `sqlite3.IntegrityError: UNIQUE constraint failed: t.k`. **A non è falsificato sull'ambiente target.**
>
> Falsificazione residua: deployment futuri su sistemi con sqlite < 3.8.0 (poco probabile, 3.8.0 è del 2013) o build Python con vecchio bundled sqlite (es. AWS Lambda runtime obsoleti — **da verificare empiricamente per ogni target**).

### B. BEGIN IMMEDIATE — counterexample
> **Falsificato se** il refactor di `_persist_master` per condividere `conn` tra `mem.store(ep)` + `sm.store(f)` + `_wire_edges` rompe almeno uno dei seguenti gate testati: il provenance gate `verified_by` (`semantic.py:385-406`), gli L1/L1.5/L1.7 anti-confab warning (`semantic.py:418-448`), il `coherence_hook` (`semantic.py:477-484`).
>
> Tutti questi gate **dipendono dal fatto che `store()` apra la propria connessione** e committi atomicamente la singola riga. Passare una connessione esterna richiede di esporre un `_store_on_conn` private helper duplicato per `SemanticMemory` e `EpisodicMemory`, raddoppiando la superficie testabile. B è **probabilmente falsificato dal costo di regressione**.

### C. Advisory lock — counterexample
> **Falsificato se** su Windows 11 (env corrente di Aurelio, vedi `env.OS`) un processo che crasha mid-`auto_consolidate` lascia il lockfile bloccato e blocca processi futuri.
>
> Documentazione Microsoft (`msvcrt.locking` LK_LOCK): "If the file is unlocked or owned by another process, locking causes ... waiting up to 10 seconds." Il rilascio automatico al process exit non è formalmente garantito su Windows pre-Vista; su versioni moderne avviene tramite kernel cleanup ma **da verificare empiricamente** con script `import os; os.kill(os.getpid(), signal.SIGKILL)` mid-lock. Se non si rilascia, occorre logica di stale-lock cleanup (timestamp + TTL) che aggiunge complessità.

---

## 5. Raccomandazione finale

**Scelta: A — UNIQUE INDEX condizionale**.

### 5.1 Razionale
1. **Solo alternativa con vincolo at-rest**: il DB stesso garantisce l'invariante "≤1 master live per `(topic, AUTO-CLUSTER-MASTER prefix)`", indipendente da come/quanti processi tocchino il DB.
2. **SQLite 3.8.0+ è già il floor**: il bundled sqlite Python su tutti i target ragionevoli è ≥ 3.8.0. Verifica empirica: **3.51.1** sull'ambiente di sviluppo corrente.
3. **Costo migration controllato**: pre-clean + `CREATE UNIQUE INDEX` in una migration `_migrate_v3_to_v4` seguendo il pattern di `engram/semantic.py:192-252` (cycle #78, #109). Reversibile: `DROP INDEX` in caso di rollback.
4. **Backward-compat con cycle 155**: la `threading.Lock` di cycle 155 può **restare** come ottimizzazione single-process (evita di sprecare round-trip su SQL IntegrityError nel caso comune). UNIQUE INDEX è il **fallback fail-fast** per il caso cross-process. Difesa in profondità.
5. **Test coverage netta**: 2 sub-process via `subprocess.Popen` su lo stesso db_path, ognuno chiama `auto_consolidate`. Post-run: `SELECT COUNT(*) WHERE topic = … AND superseded_by IS NULL` deve essere = 1. Il sub-process che perde la race riceve `IntegrityError` da SQLite → catch + log + return graceful.

### 5.2 Plan di implementazione cycle 157 (TDD strict)

**Step 1 — write failing tests first** (~30 righe `tests/test_consolidation_cross_process.py`):
- `test_unique_index_enforced_cross_process`: spawn 2 `subprocess.Popen` con script che chiama `auto_consolidate` su stesso db_path, assert COUNT=1 master post-join.
- `test_pre_migration_duplicates_cleaned`: seed manuale 2 master facts con stesso topic, run migration, assert 1 live + 1 superseded.

**Step 2 — minimal impl** (~50 righe):
- `engram/semantic.py`: aggiungi `_migrate_v3_to_v4(conn)` che (a) marca duplicati come superseded, (b) `CREATE UNIQUE INDEX idx_facts_auto_master_unique ON facts(topic) WHERE superseded_by IS NULL AND proposition LIKE 'AUTO-CLUSTER-MASTER%'`.
- Bump `target_version=4` in `__init__`.
- `engram/consolidation.py:_persist_master`: wrap `sm.store(f)` in `try/except sqlite3.IntegrityError` → log + return graceful (race perdente).

**Step 3 — verify**: pytest tests/test_consolidation_*.py, manual run su data/semantic/semantic.db reale.

**Step 4 — doc update**: `docs/MIGRATIONS.md` aggiunge sezione "v4 — auto-cluster-master unique index".

---

## 6. Anticonformismo scientifico (B4)

**Tesi nova falsificabile** (concatena WAL + UNIQUE INDEX condizionale + `threading.Lock` cycle 155):

> **In SQLite WAL mode con `busy_timeout=60000` e UNIQUE INDEX condizionale `WHERE superseded_by IS NULL AND proposition LIKE 'AUTO-CLUSTER-MASTER%'`, la `sqlite3.IntegrityError` sollevata dalla seconda write cross-process è la signature fail-fast canonica per distinguere "race detected" da "deadlock/timeout". Non serializza le letture (WAL permette read concorrenti), serializza solo la sequenza commit-su-stesso-predicato. La `threading.Lock` cycle 155 nello stesso processo riduce il tasso di IntegrityError attesi a zero nel caso single-process, ma resta load-bearing come ottimizzazione perché evita il roundtrip SQL nel fast-path.**

**Falsificazione**: se in benchmark cycle 157 si osserva `OperationalError: database is locked` invece di `IntegrityError` nel ≥10% dei casi cross-process, la tesi cade — il busy_timeout sta serializzando i writer prima che SQLite valuti il UNIQUE constraint, quindi non riusciamo a distinguere race da contention. In quel caso, bisogna abbassare `busy_timeout` per esporre la race, oppure ammettere che il segnale "race detected" è invisibile al codice applicativo e affidarsi solo all'invariante at-rest.

**Verifica empirica suggerita cycle 157**: contatori `n_integrity_error` vs `n_operational_error` su 100 run cross-process di stress test.

---

## 7. Open questions / verifica empirica residua
- DB reale di Aurelio: post-cycle 155 e prima di cycle 157, contiene già duplicati `AUTO-CLUSTER-MASTER`? Eseguire: `SELECT topic, COUNT(*) FROM facts WHERE topic LIKE '%/auto-MASTER' AND superseded_by IS NULL GROUP BY topic HAVING COUNT(*) > 1`.
- Sqlite version sul target deploy Aurelio (laptop Windows 11): assumere 3.51.1 come da env corrente, **da riconfermare** prima di cycle 157.
- Misurare overhead UNIQUE INDEX su write throughput in `tests/perf/`: ipotesi non verificata che il costo sia trascurabile per `auto_consolidate` (call rate basso, ~1/cron).
- File `docs/cycle153_honeycomb_review.md` citato nel briefing **non esiste** sul filesystem; il contesto è ricostruito dai commenti inline in `consolidation.py:74-79` e `tests/test_consolidation_toctou.py:1-26`. **Da verificare empiricamente** la fonte originale del review honeycomb.
