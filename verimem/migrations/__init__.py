"""Lightweight SQLite migration framework (HIGH #8 in ARCHITECTURE_AUDIT.md).

Why not Alembic?
  • Alembic is great for one centralised schema, but Engram has THREE SQLite
    DBs (episodes, skills_index, semantic) with independent lifecycles.
  • The existing schemas use `CREATE TABLE IF NOT EXISTS`, so the v0 → v1
    upgrade is a no-op for fresh installs. Only future schema changes will
    use the upgrade ladder.
  • A 100-line dependency-free framework is auditable; Alembic adds 3 deps.

How it works:
  • Each DB carries a `_schema_version` (key, value) table.
  • `ensure_schema_version(conn, db_id, target_v, migrations)` reads the
    current version and runs upgrade migrations in order from `current+1`
    up to `target_v`.
  • Each migration is a callable `(sqlite3.Connection) -> None`.
  • The whole upgrade runs in a single transaction; rollback on error.

Adding a migration:
  1. Bump `CURRENT_VERSION_<DB>` in the appropriate persistence module.
  2. Append `(version, callable)` to its migrations tuple.
  3. Update `tests/test_migrations.py` to assert the new version applies.
  4. Document the schema delta in `docs/MIGRATIONS.md`.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable

# Migration callable: (conn) -> None
Migration = Callable[[sqlite3.Connection], None]


_VERSION_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS _schema_version (
    db_id TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    upgraded_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _read_version(conn: sqlite3.Connection, db_id: str) -> int:
    """Return the current schema version for `db_id` (0 if unknown)."""
    conn.execute(_VERSION_TABLE_DDL)
    cur = conn.execute(
        "SELECT version FROM _schema_version WHERE db_id = ?",
        (db_id,),
    )
    row = cur.fetchone()
    return int(row[0]) if row else 0


def _write_version(conn: sqlite3.Connection, db_id: str, version: int) -> None:
    conn.execute(
        "INSERT INTO _schema_version (db_id, version) VALUES (?, ?) "
        "ON CONFLICT(db_id) DO UPDATE SET "
        "version = excluded.version, upgraded_at = datetime('now')",
        (db_id, version),
    )


#: Il db che porta il nucleo. Per gli altri (`episodes`, `skills_index`) non
#: esiste un criterio di schema, quindi il controllo qui sotto non si applica:
#: rifiutare senza un criterio sarebbe rumore, non protezione.
_DB_ID_DEL_NUCLEO = "semantic"


def _file_della_connessione(conn: sqlite3.Connection) -> str:
    """Il percorso del db principale, o `?` se non si legge.

    Serve al messaggio di rifiuto: chi lo riceve deve sapere SU QUALE file,
    perché un processo che ne apre tre (semantic, episodes, skills) altrimenti
    va a cercare.
    """
    try:
        for _, nome, file in conn.execute("PRAGMA database_list"):
            if nome == "main":
                return file or "(in memoria)"
    except sqlite3.DatabaseError:
        pass
    return "?"


def _rifiuta_una_stampa_infondata(
    conn: sqlite3.Connection,
    db_id: str,
    target_version: int,
    current: int,
) -> None:
    """La stampa cieca a un passo è legittima solo se il presupposto regge.

    Il presupposto è scritto qui sopra: «no DDL yet», cioè la versione nuova
    non chiede colonne che non ci sono. Su un bootstrap fresco è vero e la
    stampa è giusta. Su uno store che un nucleo ce l'ha già, nessuno lo
    verificava: il numero saliva e le colonne restavano quelle di prima, così
    due store che dichiarano la stessa versione possono avere schemi diversi —
    e chi legge la versione per decidere si fida di un'etichetta.

    Verificarlo si può perché il nucleo dichiara cosa si aspetta a ogni
    versione. Dove il criterio non c'è (altro db, versione non mappata, nucleo
    ancora assente) il comportamento resta quello di prima: non si inventa un
    rifiuto su una domanda a cui non si sa rispondere.
    """
    if db_id != _DB_ID_DEL_NUCLEO:
        return
    from verimem.schema import (
        ATTESE_PER_VERSIONE,
        colonne_del_nucleo,
        schema_corrisponde_su,
    )

    if target_version not in ATTESE_PER_VERSIONE:
        return
    presenti = colonne_del_nucleo(conn)
    if not presenti:
        return
    if schema_corrisponde_su(conn, target_version):
        return

    mancanti = sorted(ATTESE_PER_VERSIONE[target_version] - presenti)
    percorso = _file_della_connessione(conn)
    # ⚠️ LA VIA D'USCITA È QUELLA CHE ESISTE OGGI, non quella che vorremmo.
    # `schema.COMANDO_DI_MIGRAZIONE` nomina `verimem store migrate`, che la CLI
    # non ha: un rimedio che manda a un comando inesistente è peggio del
    # silenzio, perché il silenzio non promette e manda comunque a cercare —
    # e chi cerca nel momento sbagliato apre lo store a mano, cioè fa la cosa
    # che questo rifiuto esiste per impedire. Una cella tiene fermo che ogni
    # comando nominato qui esista davvero.
    raise RuntimeError(
        f"refusing to stamp db_id={db_id!r} from version {current} to "
        f"{target_version} with zero DDL applied: version {target_version} "
        f"declares columns the file does not have ({mancanti}). "
        f"File: {percorso}. "
        f"The one-step stamp exists for a fresh bootstrap, where there is "
        f"nothing to apply; here it would promote the number while leaving "
        f"the schema behind. Register the migration for {target_version}; to "
        f"migrate this store instead, back the file up first and then open it "
        f"with the product, which applies the ladder."
    )


def ensure_schema_version(
    conn: sqlite3.Connection,
    db_id: str,
    target_version: int,
    migrations: list[tuple[int, Migration]],
) -> int:
    """Migrate `conn` to `target_version` for the database identified by `db_id`.

    `migrations` is a list of `(version, callable)` pairs ordered by version.
    Each callable receives the live connection and applies its DDL/DML.

    Returns the final version after migration. Idempotent: running twice on
    an already-current DB is a no-op.

    Atomicity: the entire ladder runs inside one IMMEDIATE transaction; if
    any migration raises the whole upgrade is rolled back and the DB stays
    at the pre-call version.
    """
    current = _read_version(conn, db_id)
    if current >= target_version:
        return current

    # Filter and sort migrations
    pending = sorted(
        ((v, m) for v, m in migrations if current < v <= target_version),
        key=lambda pair: pair[0],
    )

    # Gap validation (review MAJOR #4; extended audit#3-r2 2026-06-09): the
    # pending versions must be a contiguous run from current+1 up to
    # target_version. A gap means a migration was forgotten or registered
    # out-of-order; running anyway would silently leave the schema mid-state.
    # This check now ALSO covers the EMPTY-pending case: an empty/short list
    # with target > current+1 used to fall straight through to the blind stamp
    # below, marking the schema as `target` while applying ZERO DDL (defeating
    # the very gap protection MAJOR #4 added). The only blind stamp still
    # allowed is a genuine single-step bootstrap (target == current+1 with no
    # migration registered for it) — the legitimate "no DDL yet" case.
    expected = list(range(current + 1, target_version + 1))
    actual = [v for v, _ in pending]
    if actual != expected and not (
        not pending and target_version == current + 1
    ):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise RuntimeError(
            f"migration ladder for db_id={db_id!r} is not contiguous: "
            f"current={current}, target={target_version}, "
            f"got versions={actual}, missing={missing}, "
            f"unexpected={extra}. Refusing to upgrade with gaps."
        )

    # ⚠️ DI CHI E' LA TRANSAZIONE. Se il CHIAMANTE ne aveva gia' una aperta, il
    # `BEGIN IMMEDIATE` qui sotto fallisce e il `commit()` finale renderebbe
    # definitive anche le SUE scritture, che lui non aveva ancora deciso di
    # rendere tali — e dopo non puo' nemmeno annullarle («cannot rollback - no
    # transaction is active»). Va letto PRIMA di tentare il BEGIN: dopo, il
    # solo messaggio dell'eccezione non distingue «ero gia' in transazione» da
    # «il database e' occupato», e nel secondo caso il commit serve eccome.
    altrui = conn.in_transaction

    if not pending:
        # No migrations defined yet; just stamp the version.
        _rifiuta_una_stampa_infondata(conn, db_id, target_version, current)
        try:
            conn.execute("BEGIN IMMEDIATE")
            _write_version(conn, db_id, target_version)
            conn.commit()
        except sqlite3.OperationalError:
            # Already in a transaction? Stamp without one.
            _write_version(conn, db_id, target_version)
            if not altrui:
                conn.commit()
        return target_version

    try:
        try:
            conn.execute("BEGIN IMMEDIATE")
            in_tx = True
        except sqlite3.OperationalError:
            in_tx = False
        # La versione va RILETTA qui, non fuori: fra il `_read_version` in
        # cima e il `BEGIN IMMEDIATE` appena eseguito c'e' una finestra in cui
        # un altro processo puo' aver migrato e committato. Chi si fida della
        # lettura di prima riesegue una migrazione gia' applicata, e il DDL
        # delle migrazioni e' `ALTER TABLE ... ADD COLUMN` nudo: rieseguirlo
        # non e' un no-op, alza `duplicate column name`.
        applicata = _read_version(conn, db_id)
        if applicata >= target_version:
            if in_tx or not altrui:
                conn.commit()
            return applicata
        for version, fn in pending:
            if version <= applicata:
                # gia' applicata dall'altro processo mentre aspettavamo il lock
                continue
            fn(conn)
            _write_version(conn, db_id, version)
        if in_tx or not altrui:
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:  # pragma: no cover
            pass
        raise

    return _read_version(conn, db_id)


def schema_version(conn: sqlite3.Connection, db_id: str) -> int:
    """Public read accessor — does not mutate the DB."""
    return _read_version(conn, db_id)


__all__ = [
    "Migration",
    "ensure_schema_version",
    "schema_version",
]
