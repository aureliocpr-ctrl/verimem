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

    if not pending:
        # No migrations defined yet; just stamp the version.
        try:
            conn.execute("BEGIN IMMEDIATE")
            _write_version(conn, db_id, target_version)
            conn.commit()
        except sqlite3.OperationalError:
            # Already in a transaction? Stamp without one.
            _write_version(conn, db_id, target_version)
            conn.commit()
        return target_version

    try:
        try:
            conn.execute("BEGIN IMMEDIATE")
            in_tx = True
        except sqlite3.OperationalError:
            in_tx = False
        for version, fn in pending:
            fn(conn)
            _write_version(conn, db_id, version)
        if in_tx:
            conn.commit()
        else:
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
