# mappa — `verimem/backup.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:26

**546 righe · 12 funzioni · 1 classi.** Contate con `ast`
(`scratchpad/inventario.py`), non con grep. **6 pubbliche, 6 private.**

Metodo e limiti: quelli dichiarati in `semantic.md`. Le quattro trappole già
pagate valgono anche qui — il nome con la parentesi non vede i **callback**;
escludere il file stesso fa sembrare morti gli helper; cercare solo in
`verimem/` e `tests/` dimentica `benchmark/`; il nome nudo dei metodi generici
pesca ogni dizionario.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **6 pubbliche** del backup | `tests/test_backup_all_dbs.py` · `tests/test_engram_backup.py` · `tests/test_backup_follows_the_data_dir.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_backup_all_dbs.py` → `3 passed in 7.75s` EXIT=0 · `test_engram_backup.py` → `11 passed in 13.39s` EXIT=0 |
| le 6 `_private` | via i chiamanti | **NON MISURATE** direttamente | — |

**Zero pubbliche senza test**, e **tre** file di test dedicati — è il file con
la copertura nominale più larga fra i piccoli della mia parte. Ha senso: è ciò
che deve funzionare quando tutto il resto è già andato storto.

## Inventario completo — ogni funzione per nome

**12 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 53 | `default_backup_root` | **pub** | La cartella dei backup DELLO STORE configurato, risolta a  | 1 — `test_backup_follows_the_data_dir.py` |
| 104 | `_ensure_dirs` | priv | Create the four tier subdirectories if missing. | 🔴 **nessuno** |
| 110 | `_hash_cell` | priv | Feed one SQLite cell value into the running hash, type-tag | 🔴 **nessuno** |
| 134 | `_compute_integrity_hash` | priv | Open db read-only and return (row_count, sha256 content fi | 2 — `test_backup_integrity_no_live_race_audit3.py` |
| 174 | `_backup_has_table` | priv | True if the SQLite file at ``path`` is sane AND contains ` | 🔴 **nessuno** |
| 206 | `_sqlite_integrity_ok` | priv | Run ``PRAGMA integrity_check`` on a backup file (read-only | 🔴 **nessuno** |
| 224 | `create_backup` | **pub** | Take an atomic backup via SQLite VACUUM INTO. | 6 — `test_backup_all_dbs.py` |
| 306 | `restore_from_backup` | **pub** | Restore a backup file over the target DB (cycle 14 FIX 4 — | 3 — `test_backup_all_dbs.py` |
| 407 | `create_all_backups` | **pub** | Back up ALL THREE engram stores: semantic, episodes, skill | 1 — `test_backup_all_dbs.py` |
| 454 | `list_backups` | **pub** | List backups (optionally filtered to one tier), newest fir | 1 — `test_engram_backup.py` |
| 482 | `_is_sane_backup` | priv | Cheap sanity check: a non-empty, real SQLite file (100-byt | 1 — `test_backup_rotation_integrity_audit3.py` |
| 496 | `rotate_backups` | **pub** | Apply retention policy. Returns paths deleted. | 2 — `test_backup_rotation_integrity_audit3.py` |

## Le classi di questo file — 1 sulla superficie

Il righello del lead conta le **classi** nel denominatore (480 sui miei 21 file
contro i 449 di sole funzioni): una classe e' superficie, e finche' non e'
nominata qui non e' mappata. Per le dataclass la riga porta il **contratto dei
dati** — i campi, che sono cio' che quella classe promette a chi la legge. Il
verdetto e' **preso in prestito** dai blocchi eseguiti piu' sopra: nessuna classe
riceve qui un verde nuovo, e dove nessun test nomina il nome si scrive NON
MISURATA.

| riga | classe | metodi | contratto / cosa promette | test che la nominano | verdetto |
|---|---|---|---|---|---|
| 94 | `BackupInfo` | 0 | **contratto dei dati**: `path`, `tier`, `created_at`, `size_bytes`, `fact_count`, `integrity_hash` | 1 — `test_backup_all_dbs.py` | esercitata dai blocchi eseguiti sopra |
