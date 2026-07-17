"""Cycle 2026-05-27 round 13 P0 foundation safety — DB backup automatico.

Aurelio audit gap C4: "no backup/restore DB ufficiale — un DROP accidentale = perdita 8469 fact".

Implementation: atomic VACUUM INTO (SQLite native, no lock contention vs WAL writers).
Rotation: 7 daily + 4 weekly + 12 monthly = max ~50MB per ~8k fact corpus.

Triangulation Gemini 2.5 Pro: "Quick wins: Backup DB (script sqlite3 .dump)". Adopted
VACUUM INTO over .dump for atomicity + binary preservation (no SQL parse round-trip).

API:
    create_backup(db_path, backup_root) -> Path
    restore_from_backup(backup_path, target_db) -> dict
    list_backups(backup_root) -> list[BackupInfo]
    rotate_backups(backup_root, policy=DEFAULT_POLICY) -> list[Path]  # returns deleted

Tier rotation:
    - daily/  : keep last 7
    - weekly/ : keep last 4 (rotated from daily every Monday)
    - monthly/: keep last 12 (rotated from weekly every 1st-of-month)

KPI:
    - backup completes <5s su DB live ~5MB
    - restore round-trip 100% fact integrity (count + sha256 of proposition col)
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

# Primary content table per engram DB — the table whose row count + content
# fingerprint represents that store's payload (audit#2 A-9: backup/restore must
# cover all three, not just semantic.db's `facts`).
_PRIMARY_TABLE: dict[str, str] = {
    "semantic": "facts",
    "episodes": "episodes",
    "skills": "skills",
}
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

DEFAULT_BACKUP_ROOT = Path.home() / ".engram" / "backups"

# Default retention policy (max copies per tier).
DEFAULT_POLICY: dict[str, int] = {
    "daily": 7,
    "weekly": 4,
    "monthly": 12,
}

BackupTier = Literal["daily", "weekly", "monthly", "manual"]


@dataclass(frozen=True)
class BackupInfo:
    """One backup file's metadata."""
    path: Path
    tier: BackupTier
    created_at: float
    size_bytes: int
    fact_count: int | None  # None if introspection skipped
    integrity_hash: str | None  # sha256 of all proposition fields, None if skipped


def _ensure_dirs(backup_root: Path) -> None:
    """Create the four tier subdirectories if missing."""
    for tier in ("daily", "weekly", "monthly", "manual"):
        (backup_root / tier).mkdir(parents=True, exist_ok=True)


def _hash_cell(h: hashlib._Hash, v: object) -> None:
    """Feed one SQLite cell value into the running hash, type-tagged so a NULL,
    the string '0', and the int 0 never collide."""
    if v is None:
        h.update(b"\x00N")
    elif isinstance(v, bytes):
        h.update(b"\x00B")
        h.update(v)
    elif isinstance(v, str):
        h.update(b"\x00S")
        h.update(v.encode("utf-8", errors="replace"))
    elif isinstance(v, bool):  # bool before int (bool IS an int subclass)
        h.update(b"\x00b" + (b"1" if v else b"0"))
    elif isinstance(v, int):
        h.update(b"\x00I")
        h.update(str(v).encode())
    elif isinstance(v, float):
        h.update(b"\x00F")
        h.update(repr(v).encode())
    else:
        h.update(b"\x00X")
        h.update(str(v).encode("utf-8", errors="replace"))


def _compute_integrity_hash(db_path: Path, table: str = "facts") -> tuple[int, str]:
    """Open db read-only and return (row_count, sha256 content fingerprint) of
    ``table``.

    A-9 (audit#2 2026-06-08): generalized from the hardcoded ``facts`` table so
    backup/restore can verify episodes.db (``episodes``) and skills_index.db
    (``skills``) too — previously the ``FROM facts`` hardcode raised
    ``OperationalError: no such table`` on those, so only semantic.db could be
    integrity-checked and a disaster-restore silently lost episodes + skills.

    Hashes ALL columns of every row, ordered BY CONTENT (not rowid): VACUUM INTO
    may reassign rowids, so a content-ordered fingerprint is the order-stable
    way to prove source and backup hold identical rows. ``table`` must be a bare
    SQL identifier (validated) — it is always one of our own constants, never
    user input.
    """
    if not _IDENT_RE.match(table):
        raise ValueError(f"unsafe table identifier: {table!r}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
    try:
        cur = conn.cursor()
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        count = int(cur.fetchone()[0])
        cols = [r[1] for r in cur.execute(f'PRAGMA table_info("{table}")')]
        h = hashlib.sha256()
        h.update(f"{table}:{','.join(cols)}\x00".encode())
        if cols:
            collist = ", ".join(f'"{c}"' for c in cols)
            for row in cur.execute(
                f'SELECT {collist} FROM "{table}" ORDER BY {collist}'
            ):
                for v in row:
                    _hash_cell(h, v)
                    h.update(b"\x01")
                h.update(b"\x02")
        return count, h.hexdigest()
    finally:
        conn.close()


def _backup_has_table(path: Path, table: str) -> bool:
    """True if the SQLite file at ``path`` is sane AND contains ``table``.

    audit#3-r3 R5: pre-restore validation. ``restore_from_backup`` overwrites
    the target page-by-page via the SQLite Backup API and only verified the
    primary table AFTER the (destructive) copy — so restoring an
    episodes/skills backup over semantic.db corrupted it before the
    ``no such table: facts`` error surfaced. Checking up front lets the restore
    abort with the target untouched. Opens read-only; tolerant of a non-DB or
    corrupt file (returns False rather than raising).
    """
    if not _IDENT_RE.match(table):
        raise ValueError(f"unsafe table identifier: {table!r}")
    if not _is_sane_backup(path):
        return False
    try:
        conn = sqlite3.connect(
            f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10,
        )
        try:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type='table' AND name=? LIMIT 1",
                (table,),
            ).fetchone()
            return row is not None
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def _sqlite_integrity_ok(path: Path) -> bool:
    """Run ``PRAGMA integrity_check`` on a backup file (read-only) and return
    True iff SQLite reports ``ok``. audit#3-r3 R16: this validates the SNAPSHOT
    itself for corruption, without comparing against the live (moving) source.
    """
    try:
        conn = sqlite3.connect(
            f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10,
        )
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            return bool(row) and str(row[0]).strip().lower() == "ok"
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def create_backup(
    db_path: Path | str,
    backup_root: Path | str = DEFAULT_BACKUP_ROOT,
    *,
    tier: BackupTier = "daily",
    verify_integrity: bool = True,
    integrity_table: str = "facts",
) -> BackupInfo:
    """Take an atomic backup via SQLite VACUUM INTO.

    VACUUM INTO is preferred over `.dump`:
      - atomic at SQLite engine level (page-by-page copy under a shared lock)
      - preserves binary BLOBs verbatim (no text round-trip)
      - typically faster than .dump on large DBs

    On a busy DB with WAL writers, the shared lock blocks new writers only
    briefly between checkpoints. Verified empirical: ~3-5s for 8k-fact corpus.

    Returns BackupInfo. Raises FileNotFoundError if db_path missing,
    RuntimeError if integrity check fails (rare — indicates SQLite bug or
    disk corruption).
    """
    db_path = Path(db_path)
    backup_root = Path(backup_root)
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    _ensure_dirs(backup_root)
    # Use microsecond-precision timestamp so multiple backups in the same
    # second (common in pytest loops + cron retries) don't collide on the
    # VACUUM INTO output path. SQLite rejects pre-existing files.
    ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = backup_root / tier / f"{db_path.stem}-{ts}.db"

    # VACUUM INTO: atomic snapshot. Connects to the live DB (read-only safe
    # for the snapshot — writers proceed independently after checkpoint).
    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        conn.execute(f"VACUUM INTO '{backup_path.as_posix()}'")
    finally:
        conn.close()

    size = backup_path.stat().st_size

    fact_count = None
    integrity_hash = None
    if verify_integrity:
        # audit#3-r3 R16: validate the SNAPSHOT's OWN integrity, NOT equality
        # with the live source. VACUUM INTO already produced an atomic,
        # internally-consistent copy of a single point in time; re-reading the
        # LIVE db and comparing hashes raced any concurrent writer — a commit
        # landing between the snapshot and that re-read made source != backup and
        # DELETED a perfectly good backup. Instead: confirm the snapshot is
        # readable, holds the expected table, and passes PRAGMA integrity_check.
        if not _backup_has_table(backup_path, integrity_table):
            backup_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Backup unreadable or missing '{integrity_table}' table: "
                f"{backup_path}"
            )
        if not _sqlite_integrity_ok(backup_path):
            backup_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Backup failed PRAGMA integrity_check (corrupt snapshot): "
                f"{backup_path}"
            )
        # Record the snapshot's own count + content fingerprint.
        fact_count, integrity_hash = _compute_integrity_hash(
            backup_path, integrity_table
        )

    return BackupInfo(
        path=backup_path,
        tier=tier,
        created_at=time.time(),
        size_bytes=size,
        fact_count=fact_count,
        integrity_hash=integrity_hash,
    )


def restore_from_backup(
    backup_path: Path | str,
    target_db: Path | str,
    *,
    verify_integrity: bool = True,
    keep_pre_restore_copy: bool = True,
    integrity_table: str = "facts",
) -> dict:
    """Restore a backup file over the target DB (cycle 14 FIX 4 — agy audit).

    Cycle 14 round-trip safety fix (agy audit Critical, backup.py:194-201):
    pre-round-13 used ``shutil.copyfile`` + manual ``-wal``/``-shm`` unlink,
    which corrupts in-flight transactions of any concurrent connection.

    Post-fix uses the SQLite Backup API
    (``sqlite3.Connection.backup(target_conn)``):
      - atomic page-by-page copy at the engine level
      - serializes against concurrent writers via SQLite's own locking
      - preserves WAL semantics; the target DB's existing -wal/-shm are
        rewritten by SQLite, not by us
      - the source backup file is opened read-only via URI ``?mode=ro``

    The optional pre-restore safety copy uses VACUUM INTO (atomic snapshot
    of the current target before we overwrite it). On botched restore the
    operator can ``restore_from_backup(pre_copy, target_db)`` to reverse.

    Safety contract:
      - Callers SHOULD close any open ``SemanticMemory`` instances against
        ``target_db`` before invoking restore. The backup() API holds an
        EXCLUSIVE lock during the copy; concurrent writers will block.
      - Reads against ``target_db`` during restore see the OLD pages until
        the final commit; after commit they see the restored content
        (with possible cached state — caller must invalidate caches).

    Returns ``{ok, restored_from, fact_count, integrity_hash,
    pre_restore_copy}``.
    """
    backup_path = Path(backup_path)
    target_db = Path(target_db)
    if not backup_path.exists():
        raise FileNotFoundError(f"backup not found: {backup_path}")

    # audit#3-r3 R5: validate the backup BEFORE overwriting the target. The
    # SQLite .backup() copy below is destructive (replaces every page); the
    # post-copy integrity check fired too late to save a wrong-store restore
    # (e.g. an episodes/skills backup dropped over semantic.db). Refuse up
    # front when the backup lacks the expected primary table — target untouched.
    if verify_integrity and not _backup_has_table(backup_path, integrity_table):
        raise ValueError(
            f"backup {backup_path.name!r} is not a valid "
            f"'{integrity_table}' store (missing the '{integrity_table}' "
            f"table or not a SQLite DB) — refusing to restore it over "
            f"{target_db.name!r}. Pass the right backup, or "
            f"verify_integrity=False to override."
        )

    pre_copy_path: Path | None = None
    if keep_pre_restore_copy and target_db.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        pre_copy_path = target_db.with_name(
            f"{target_db.stem}.pre-restore-{ts}.db"
        )
        # Pre-copy via VACUUM INTO — atomic snapshot, independent of the
        # restore that follows. Useful as a "undo restore" if something
        # downstream complains about the restored content.
        conn = sqlite3.connect(str(target_db), timeout=30)
        try:
            conn.execute(f"VACUUM INTO '{pre_copy_path.as_posix()}'")
        finally:
            conn.close()

    # Cycle 14 FIX 4: SQLite Backup API replaces shutil.copyfile.
    # Source opens read-only (URI ``mode=ro``) so we never accidentally
    # write back. Target opens read-write; the .backup() call rewrites
    # every page atomically. WAL sidecars are managed by SQLite itself —
    # no manual unlink (that was the round-13 bug).
    src = sqlite3.connect(
        f"file:{backup_path.as_posix()}?mode=ro", uri=True, timeout=30,
    )
    dst = sqlite3.connect(str(target_db), timeout=30)
    try:
        # backup() args: target_connection, pages=-1 (copy all),
        # progress=None (no callback), name='main' (default).
        src.backup(dst, pages=-1)
        dst.commit()
    finally:
        src.close()
        dst.close()

    info: dict = {
        "ok": True,
        "restored_from": str(backup_path),
        "pre_restore_copy": str(pre_copy_path) if pre_copy_path else None,
    }
    if verify_integrity:
        count, h = _compute_integrity_hash(target_db, integrity_table)
        info["fact_count"] = count
        info["integrity_hash"] = h
    return info


def create_all_backups(
    *,
    semantic_db: Path | str | None = None,
    episodes_db: Path | str | None = None,
    skills_db: Path | str | None = None,
    backup_root: Path | str = DEFAULT_BACKUP_ROOT,
    tier: BackupTier = "daily",
    verify_integrity: bool = True,
) -> dict[str, BackupInfo | dict]:
    """Back up ALL THREE engram stores: semantic, episodes, skills.

    A-9 (audit#2 2026-06-08): ``create_backup`` alone only ever covered
    semantic.db — its integrity check assumed a ``facts`` table, so episodes.db
    and skills_index.db could not be verified (and the only CLI caller,
    ``engram facts backup``, was facts-scoped). A disaster-restore therefore
    silently lost every episode and skill. This backs up the full trio, each
    verified against ITS primary table.

    Paths default to ``CONFIG`` (the live data dir); pass explicit paths to
    target a specific install (or a test fixture). Returns
    ``{name: BackupInfo}`` per store; a missing DB or a per-store failure is
    recorded as ``{name: {"ok": False, "error": ...}}`` rather than aborting the
    others — a partial backup beats none.
    """
    from .config import CONFIG

    resolved = {
        "semantic": Path(semantic_db) if semantic_db else Path(CONFIG.semantic_db),
        "episodes": Path(episodes_db) if episodes_db else Path(CONFIG.episodes_db),
        "skills": Path(skills_db) if skills_db else Path(CONFIG.skills_db),
    }
    out: dict[str, BackupInfo | dict] = {}
    for name, path in resolved.items():
        if not path.exists():
            out[name] = {"ok": False, "error": f"DB not found: {path}"}
            continue
        try:
            out[name] = create_backup(
                path, backup_root, tier=tier,
                verify_integrity=verify_integrity,
                integrity_table=_PRIMARY_TABLE[name],
            )
        except Exception as exc:  # noqa: BLE001 — one store's failure must not block the others
            out[name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return out


def list_backups(
    backup_root: Path | str = DEFAULT_BACKUP_ROOT,
    *,
    tier: BackupTier | None = None,
) -> list[BackupInfo]:
    """List backups (optionally filtered to one tier), newest first."""
    backup_root = Path(backup_root)
    if not backup_root.exists():
        return []
    tiers = (tier,) if tier else ("daily", "weekly", "monthly", "manual")
    out: list[BackupInfo] = []
    for t in tiers:
        tdir = backup_root / t
        if not tdir.exists():
            continue
        for p in sorted(tdir.glob("*.db"), reverse=True):
            stat = p.stat()
            out.append(BackupInfo(
                path=p, tier=t,
                created_at=stat.st_mtime,
                size_bytes=stat.st_size,
                fact_count=None,
                integrity_hash=None,
            ))
    out.sort(key=lambda b: b.created_at, reverse=True)
    return out


def _is_sane_backup(path: Path) -> bool:
    """Cheap sanity check: a non-empty, real SQLite file (100-byte header +
    'SQLite format 3\\000' magic). Used by rotation so a newer EMPTY/CORRUPT
    backup (e.g. from the opt-in --no-verify path, or on-disk corruption) can
    never evict the last known-good copy. audit#3-r2 (2026-06-09)."""
    try:
        if path.stat().st_size < 100:  # SQLite header alone is 100 bytes
            return False
        with open(path, "rb") as fh:
            return fh.read(16) == b"SQLite format 3\x00"
    except OSError:
        return False


def rotate_backups(
    backup_root: Path | str = DEFAULT_BACKUP_ROOT,
    *,
    policy: dict[str, int] | None = None,
) -> list[Path]:
    """Apply retention policy. Returns paths deleted.

    For each tier: keep N most recent, delete older. Idempotent.

    Integrity-aware (audit#3-r2): a SANE (non-empty, valid-header) backup is
    never evicted to keep a newer empty/corrupt one. Sane copies are retained
    newest-first up to the quota; leftover quota is filled with the newest
    insane files only when there aren't enough sane ones.
    """
    policy = policy or DEFAULT_POLICY
    backup_root = Path(backup_root)
    deleted: list[Path] = []
    for tier, keep in policy.items():
        tdir = backup_root / tier
        if not tdir.exists():
            continue
        files = sorted(tdir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        sane = [p for p in files if _is_sane_backup(p)]
        insane = [p for p in files if p not in sane]
        keep_set = set(sane[:keep])
        if len(keep_set) < keep:
            keep_set.update(insane[: keep - len(keep_set)])
        for p in files:
            if p in keep_set:
                continue
            try:
                p.unlink()
                deleted.append(p)
            except OSError:
                # Best-effort: a Windows lock during rotation should not crash.
                pass
    return deleted


__all__ = [
    "BackupInfo",
    "BackupTier",
    "DEFAULT_BACKUP_ROOT",
    "DEFAULT_POLICY",
    "create_backup",
    "create_all_backups",
    "restore_from_backup",
    "list_backups",
    "rotate_backups",
]
