#!/usr/bin/env python3
"""Cycle #109 S3 — migrate live corpus to provenance schema v3.

The semantic.db on disk (Aurelio production) already has schema_version=2
(cycle #78 supersession in production via PR #43 deployment). The cycle
#109 provenance migration (this branch) cannot run via ensure_schema_version
because target=2 is already stamped.

This script is the ONE-OFF bridge: it ADDs the 3 provenance columns
(verified_by/status/source_signature) to the existing facts table, marks
all pre-existing rows as 'legacy_unverified', and creates idx_facts_status.

It is IDEMPOTENT: re-running on an already-migrated DB is a no-op.
It is REVERSIBLE: SQLite ALTER TABLE does not support DROP COLUMN portably,
so revert = restore from backup (pre-condition).

USAGE:
    # Dry-run (default — prints actions, no writes):
    python scripts/cycle109_migrate_corpus_provenance.py

    # Apply:
    python scripts/cycle109_migrate_corpus_provenance.py --apply

    # Custom path:
    python scripts/cycle109_migrate_corpus_provenance.py --db /path/to/sm.db

PRE-CONDITION: backup the DB before --apply.
    cp ~/.engram/semantic/semantic.db ~/.engram/semantic/semantic.db.backup

Refs:
- Aurelio sfida 2026-05-16 memoria compromessa
- MemoryGraft 2512.16962 (persistent poisoning via embedding-only)
- ProvSEEK 2508.21323 (row_id verification pattern)
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".engram" / "semantic" / "semantic.db"


def get_existing_columns(conn: sqlite3.Connection) -> set[str]:
    """Return the set of column names currently in `facts` table."""
    return {row[1] for row in conn.execute("PRAGMA table_info(facts)")}


def get_schema_version(conn: sqlite3.Connection) -> int | None:
    """Return the stamped semantic schema version, or None if absent."""
    try:
        row = conn.execute(
            "SELECT version FROM _schema_version WHERE db_id = 'semantic'"
        ).fetchone()
        return int(row[0]) if row else None
    except sqlite3.OperationalError:
        return None


def get_fact_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]


def status_distribution(conn: sqlite3.Connection) -> dict[str, int]:
    """Return {status: count} if status column exists, else {}."""
    cols = get_existing_columns(conn)
    if "status" not in cols:
        return {}
    rows = conn.execute(
        "SELECT status, COUNT(*) FROM facts GROUP BY status"
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def migrate(db_path: Path, dry_run: bool = True) -> dict:
    """Add provenance columns to the facts table if missing.

    Returns a dict with action summary:
        {db_path, dry_run, schema_version_pre, schema_version_post,
         columns_pre, columns_post, n_facts, columns_added,
         n_marked_legacy, status_distribution_post}
    """
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    result: dict = {
        "db_path": str(db_path),
        "dry_run": dry_run,
        "ts": time.time(),
    }

    with sqlite3.connect(db_path, timeout=10.0) as conn:
        conn.execute("PRAGMA busy_timeout=10000;")
        conn.row_factory = sqlite3.Row

        result["schema_version_pre"] = get_schema_version(conn)
        cols_pre = get_existing_columns(conn)
        result["columns_pre"] = sorted(cols_pre)
        result["n_facts"] = get_fact_count(conn)
        result["status_distribution_pre"] = status_distribution(conn)

        # Detect which provenance columns are missing.
        target_cols = {
            "verified_by": (
                "ALTER TABLE facts ADD COLUMN verified_by "
                "TEXT NOT NULL DEFAULT '[]'"
            ),
            "status": (
                "ALTER TABLE facts ADD COLUMN status "
                "TEXT NOT NULL DEFAULT 'model_claim'"
            ),
            "source_signature": (
                "ALTER TABLE facts ADD COLUMN source_signature TEXT"
            ),
        }
        missing = [c for c in target_cols if c not in cols_pre]
        result["columns_to_add"] = missing

        if not missing:
            result["already_migrated"] = True
            result["columns_added"] = []
            result["n_marked_legacy"] = 0
            result["columns_post"] = result["columns_pre"]
            result["status_distribution_post"] = status_distribution(conn)
            return result
        result["already_migrated"] = False

        if dry_run:
            # Report what WOULD happen.
            result["columns_added"] = []  # not applied
            # Estimate legacy-marking impact: all existing rows would be
            # marked legacy_unverified (because status column is being
            # added with default 'model_claim', then UPDATEd).
            result["n_marked_legacy_would"] = result["n_facts"]
            result["columns_post"] = sorted(cols_pre | set(missing))
            return result

        # APPLY mode — perform DDL + DML.
        for col_name in missing:
            ddl = target_cols[col_name]
            conn.execute(ddl)
        result["columns_added"] = missing

        # Mark all pre-existing rows as legacy_unverified IFF we just
        # added the status column (otherwise status was already set).
        if "status" in missing:
            cur = conn.execute(
                "UPDATE facts SET status = 'legacy_unverified' "
                "WHERE status = 'model_claim'"
            )
            result["n_marked_legacy"] = cur.rowcount
        else:
            result["n_marked_legacy"] = 0

        # Create idx_facts_status if absent.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_facts_status ON facts(status)"
        )
        conn.commit()

        result["schema_version_post"] = get_schema_version(conn)
        result["columns_post"] = sorted(get_existing_columns(conn))
        result["status_distribution_post"] = status_distribution(conn)
        return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cycle #109 S3 — migrate corpus to provenance schema.",
    )
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB_PATH,
        help=f"path to semantic.db (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="apply changes (default is dry-run)",
    )
    args = parser.parse_args()

    dry_run = not args.apply
    print(f"[cycle109] db_path={args.db}")
    print(f"[cycle109] mode={'DRY-RUN' if dry_run else 'APPLY'}")

    try:
        report = migrate(args.db, dry_run=dry_run)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print()
    print("== Pre-migration ==")
    print(f"  schema_version: {report['schema_version_pre']}")
    print(f"  n_facts: {report['n_facts']}")
    print(f"  columns: {report['columns_pre']}")
    print(f"  status_dist: {report['status_distribution_pre']}")

    print()
    print("== Plan ==")
    print(f"  columns_to_add: {report['columns_to_add']}")
    if report.get("already_migrated"):
        print("  ALREADY MIGRATED — nothing to do.")
    elif dry_run:
        print(
            f"  would mark {report.get('n_marked_legacy_would', 0)} "
            "rows as legacy_unverified"
        )
        print(f"  columns_post (predicted): {report['columns_post']}")
    else:
        print(f"  columns_added: {report['columns_added']}")
        print(f"  marked legacy_unverified: {report['n_marked_legacy']}")

    if not dry_run and not report.get("already_migrated"):
        print()
        print("== Post-migration ==")
        print(f"  schema_version: {report['schema_version_post']}")
        print(f"  columns: {report['columns_post']}")
        print(f"  status_dist: {report['status_distribution_post']}")

    if dry_run and not report.get("already_migrated"):
        print()
        print(
            "  re-run with --apply to actually migrate (BACKUP DB FIRST!)."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
