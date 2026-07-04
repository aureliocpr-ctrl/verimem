"""audit#3-r2 (2026-06-09): rotate_backups must be integrity-aware — a newer
EMPTY/CORRUPT backup (from the opt-in --no-verify path or on-disk corruption)
must NEVER evict the last known-good copy. Pre-fix it kept the N newest by
mtime regardless of validity, so a corrupt newest could delete a good older one.
"""
from __future__ import annotations

import os
from pathlib import Path

from engram.backup import _is_sane_backup, rotate_backups

_SQLITE_HEADER = b"SQLite format 3\x00"


def _write_good(path: Path) -> None:
    # A plausible non-empty SQLite file: header magic + padding past 100 bytes.
    path.write_bytes(_SQLITE_HEADER + b"\x00" * 200)


def _write_corrupt(path: Path, *, empty: bool = True) -> None:
    path.write_bytes(b"" if empty else b"not a sqlite file at all")


def _set_mtime(path: Path, mtime: float) -> None:
    os.utime(path, (mtime, mtime))


def test_is_sane_backup_detects_header_and_size(tmp_path: Path) -> None:
    good = tmp_path / "g.db"
    _write_good(good)
    empty = tmp_path / "e.db"
    _write_corrupt(empty, empty=True)
    short = tmp_path / "s.db"
    _write_corrupt(short, empty=False)  # wrong header + < 100 bytes
    assert _is_sane_backup(good) is True
    assert _is_sane_backup(empty) is False
    assert _is_sane_backup(short) is False


def test_rotation_never_evicts_good_copy_for_newer_corrupt(tmp_path: Path) -> None:
    tier = tmp_path / "daily"
    tier.mkdir()
    good_old = tier / "2026-06-01.db"
    good_new = tier / "2026-06-02.db"
    corrupt_newest = tier / "2026-06-03.db"
    _write_good(good_old)
    _write_good(good_new)
    _write_corrupt(corrupt_newest, empty=True)
    # corrupt is the NEWEST by mtime -> pre-fix it would be kept, evicting good_old.
    _set_mtime(good_old, 1_000_000)
    _set_mtime(good_new, 2_000_000)
    _set_mtime(corrupt_newest, 3_000_000)

    deleted = rotate_backups(tmp_path, policy={"daily": 2})

    assert good_old.exists(), "rotation must not delete a known-good backup"
    assert good_new.exists(), "rotation must keep the good backups"
    assert not corrupt_newest.exists(), "the corrupt newest must be the one dropped"
    assert corrupt_newest in deleted


def test_rotation_count_retention_unchanged_when_all_sane(tmp_path: Path) -> None:
    # Backward-compat: when every backup is sane, keep the N newest as before.
    tier = tmp_path / "daily"
    tier.mkdir()
    files = []
    for i in range(4):
        f = tier / f"2026-06-0{i + 1}.db"
        _write_good(f)
        _set_mtime(f, 1_000_000 + i * 1000)
        files.append(f)
    rotate_backups(tmp_path, policy={"daily": 2})
    survivors = sorted(p.name for p in tier.glob("*.db"))
    # the 2 newest (index 2,3) survive
    assert survivors == ["2026-06-03.db", "2026-06-04.db"], survivors
