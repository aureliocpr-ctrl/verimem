"""Tests for hippoagent/migrations/ — the schema-versioning ladder (HIGH #8)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from engram.migrations import ensure_schema_version, schema_version


@pytest.fixture
def conn(tmp_path: Path):
    db = tmp_path / "x.db"
    c = sqlite3.connect(db)
    yield c
    c.close()


def test_fresh_db_starts_at_version_zero(conn):
    assert schema_version(conn, "test") == 0


def test_ensure_v1_no_migrations_stamps_version(conn):
    final = ensure_schema_version(conn, db_id="test", target_version=1, migrations=[])
    assert final == 1
    assert schema_version(conn, "test") == 1


def test_idempotent(conn):
    ensure_schema_version(conn, db_id="test", target_version=1, migrations=[])
    ensure_schema_version(conn, db_id="test", target_version=1, migrations=[])
    assert schema_version(conn, "test") == 1


def test_gap_in_ladder_is_refused(conn):
    """A migration ladder with a missing version must NOT silently skip.

    This is the property review MAJOR #4 demanded. Scenario: a team adds
    migrations 1 and 3 but forgets 2 (or registers them out of order).
    Running ensure with target=3 from a fresh DB used to succeed by simply
    not running the missing m2 — schema ends up at v3 but in a broken
    half-migrated state. The new validation refuses upfront.
    """
    def m1(_):
        pass

    def m3(_):
        pass

    with pytest.raises(RuntimeError, match="not contiguous"):
        ensure_schema_version(
            conn, db_id="test", target_version=3,
            migrations=[(1, m1), (3, m3)],
        )
    # Schema must remain at 0 — no half-applied state.
    assert schema_version(conn, "test") == 0


def test_empty_pending_with_target_ahead_is_refused(conn):
    """audit#3-r2: an EMPTY (or short) migrations list with target > current+1
    used to fall straight through to the blind stamp, marking the schema at
    `target` while running ZERO DDL — the very gap MAJOR #4 was meant to stop.
    It must refuse, and must NOT stamp the version."""
    with pytest.raises(RuntimeError, match="not contiguous"):
        ensure_schema_version(conn, db_id="test", target_version=9, migrations=[])
    assert schema_version(conn, "test") == 0, "must not stamp on refusal"


def test_single_step_bootstrap_still_allowed(conn):
    # The legitimate no-DDL single-step bootstrap (current+1 == target with no
    # migration registered) must still stamp — the only blind-stamp exception.
    final = ensure_schema_version(conn, db_id="test", target_version=1, migrations=[])
    assert final == 1 and schema_version(conn, "test") == 1


def test_extra_migration_beyond_target_is_refused(conn):
    """If the ladder contains a migration whose version > target, the
    `pending` filter drops it — but we explicitly check for that as part
    of the contiguity rule. Whoever called us asked for `target_version=N`
    and a migration beyond N suggests a copy-paste bug, not progress.
    """
    def m1(_):
        pass

    def m2(_):
        pass

    # Ask for target=1 but pass migrations [1, 2]. Pending will be only
    # [1] which equals expected [1] — this case is OK and should pass.
    final = ensure_schema_version(
        conn, db_id="test", target_version=1,
        migrations=[(1, m1), (2, m2)],
    )
    assert final == 1


def test_runs_migrations_in_order(conn):
    calls: list[int] = []

    def m1(c: sqlite3.Connection) -> None:
        c.execute("CREATE TABLE t1 (id INTEGER)")
        calls.append(1)

    def m2(c: sqlite3.Connection) -> None:
        c.execute("CREATE TABLE t2 (id INTEGER)")
        calls.append(2)

    final = ensure_schema_version(
        conn, db_id="test", target_version=2,
        migrations=[(1, m1), (2, m2)],
    )
    assert final == 2
    assert calls == [1, 2]
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert "t1" in tables
    assert "t2" in tables


def test_partial_upgrade_then_rest(conn):
    """If a DB is at v1, applying target=3 only runs v2+v3 migrations."""
    def m1(c):
        c.execute("CREATE TABLE t1 (id INTEGER)")
    def m2(c):
        c.execute("CREATE TABLE t2 (id INTEGER)")
    def m3(c):
        c.execute("CREATE TABLE t3 (id INTEGER)")

    ensure_schema_version(conn, "test", 1, [(1, m1), (2, m2), (3, m3)])
    assert schema_version(conn, "test") == 1

    # Now bump to 3 — m2 and m3 should run, m1 must NOT re-run.
    calls: list[int] = []
    def m1_b(c):
        calls.append(1)
    def m2_b(c):
        c.execute("CREATE TABLE t2 (id INTEGER)")
        calls.append(2)
    def m3_b(c):
        c.execute("CREATE TABLE t3 (id INTEGER)")
        calls.append(3)
    ensure_schema_version(conn, "test", 3, [(1, m1_b), (2, m2_b), (3, m3_b)])
    assert calls == [2, 3]
    assert schema_version(conn, "test") == 3


def test_failure_rolls_back(conn):
    def m1(c):
        c.execute("CREATE TABLE t1 (id INTEGER)")
    def m2_broken(c):
        c.execute("CREATE TABLE t2 (id INTEGER)")
        raise RuntimeError("simulated failure")

    with pytest.raises(RuntimeError, match="simulated failure"):
        ensure_schema_version(
            conn, "test", 2, [(1, m1), (2, m2_broken)],
        )
    # After rollback, version should still be 0 — neither m1 nor m2 stuck.
    assert schema_version(conn, "test") == 0
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert "t1" not in tables
    assert "t2" not in tables


def test_existing_persistence_modules_stamp_target_version(tmp_path: Path):
    """Confirm memory / skills / semantic stamp themselves at their
    declared target version on init.

    Ogni modulo si timbra alla propria target version dichiarata. Le
    asserzioni usano le COSTANTI source-of-truth (_EPISODES_SCHEMA_VERSION,
    _SKILLS_TARGET_VERSION, _SEMANTIC_TARGET_VERSION) cosi' il test auto-traccia
    i bump invece di diventare stale (skills v2 = colonna embedding_model
    2026-06-03; semantic v9 = isolamento embedding-model per-riga).
    """
    from engram.memory import _EPISODES_SCHEMA_VERSION, EpisodicMemory
    from engram.semantic import SemanticMemory
    from engram.skill import _SKILLS_TARGET_VERSION, SkillLibrary

    em = EpisodicMemory(db_path=tmp_path / "ep.db")
    with em._connect() as c:
        assert schema_version(c, "episodes") == _EPISODES_SCHEMA_VERSION

    sl = SkillLibrary(
        dir_path=tmp_path / "skills_dir",
        db_path=tmp_path / "sk.db",
    )
    with sl._connect() as c:
        assert schema_version(c, "skills") == _SKILLS_TARGET_VERSION

    from engram.semantic import _SEMANTIC_TARGET_VERSION
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    with sm._connect() as c:
        # cycle #78: semantic stepped v1→v2 (supersession cols).
        # cycle #109: semantic stepped v2→v3 (provenance cols).
        # cycle 157: v3→v4 (partial UNIQUE INDEX cross-process).
        # Use the module constant so this test auto-adapts to new
        # migrations (cycle 160 v5 queued behind PR #103).
        assert schema_version(c, "semantic") == _SEMANTIC_TARGET_VERSION


def test_independent_db_ids(conn):
    """Two db_ids on the same connection track their versions independently."""
    ensure_schema_version(conn, "a", 2, [
        (1, lambda c: None), (2, lambda c: None),
    ])
    ensure_schema_version(conn, "b", 1, [(1, lambda c: None)])
    assert schema_version(conn, "a") == 2
    assert schema_version(conn, "b") == 1
