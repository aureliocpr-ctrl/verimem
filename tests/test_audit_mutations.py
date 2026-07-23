"""Universal mutation audit — hash-chained, action-only, fail-closed (0.8 WS step 1).

Design v3, forged against two independent adversaries (GLM-5.2 + deepseek,
convergent 2/2 on the same failure modes of the naive design):

* The chain records the ACTION — ``{ts, principal, action, resource_id,
  detail, outcome}`` — NEVER the content nor a hash of it. Content in an
  immutable chain makes GDPR Art.17 erasure a self-contradiction (deleting
  the data would be tampering), and a bare hash of short text (a name, an
  amount) is brute-forceable, so it IS the data.
* ``principal`` is MANDATORY at the core: ``SemanticMemory.delete/supersede/
  clear`` refuse to run without one. Background jobs pass an explicit
  ``system:*`` principal — absence is an error, never a silent None.
* FAIL-CLOSED in the SAME transaction: if the audit row cannot be appended,
  the destructive operation must not happen either (atomic rollback). An
  attacker who can break audit writes must not gain untracked deletes.
* One chain, ``verimem.tamper_evidence`` primitives, ``verify()`` returns the
  first tampered row.

Out of scope for this cycle (declared, not forgotten): episodic-store deletes,
read/access logging, the externally-anchored signed head (Opus cycle).
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from verimem.semantic import Fact, SemanticMemory


def _sm(tmp_path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


def _store(sm: SemanticMemory, fid: str, proposition: str = "plain note") -> str:
    sm.store(Fact(id=fid, proposition=proposition, topic="t"), embed="sync")
    return fid


def _audit_rows(sm: SemanticMemory) -> list[sqlite3.Row]:
    with sqlite3.connect(sm.db_path) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM audit_mutations ORDER BY rowid ASC").fetchall()


# ---------------------------------------------------------------------------
# Recording: every destructive op leaves exactly one chained action row
# ---------------------------------------------------------------------------

def test_delete_records_chained_action_row(tmp_path) -> None:
    sm = _sm(tmp_path)
    _store(sm, "f1")
    assert sm.delete("f1", principal="sdk:local") is True

    rows = _audit_rows(sm)
    assert len(rows) == 1
    r = rows[0]
    assert r["principal"] == "sdk:local"
    assert r["action"] == "delete"
    assert r["resource_id"] == "f1"
    assert r["outcome"] == "ok"
    assert r["entry_hash"] and len(r["entry_hash"]) == 64
    # atomicity, positive half: mutation AND audit both landed
    assert sm.get("f1") is None
    assert sm.audit_verify() is None  # chain intact


def test_delete_missing_fact_records_nothing(tmp_path) -> None:
    """The chain records mutations that HAPPENED. A no-op delete (row absent)
    is not a mutation; attempt-logging is the access-log's job (later cycle)."""
    sm = _sm(tmp_path)
    assert sm.delete("ghost", principal="sdk:local") is False
    assert _audit_rows(sm) == []


def test_delete_with_undo_records(tmp_path) -> None:
    sm = _sm(tmp_path)
    _store(sm, "f1")
    res = sm.delete_with_undo("f1", principal="cli:local")
    assert res["removed"] is True

    rows = _audit_rows(sm)
    assert len(rows) == 1
    assert rows[0]["action"] == "delete"
    assert rows[0]["principal"] == "cli:local"
    detail = json.loads(rows[0]["detail"])
    assert detail.get("op_id") == res["op_id"]


def test_supersede_records_action_row(tmp_path) -> None:
    sm = _sm(tmp_path)
    _store(sm, "old")
    _store(sm, "new")
    res = sm.supersede("old", "new", principal="sdk:local", reason="update")
    assert res["ok"] is True

    rows = _audit_rows(sm)
    assert len(rows) == 1
    r = rows[0]
    assert r["action"] == "supersede"
    assert r["resource_id"] == "old"
    assert json.loads(r["detail"]).get("new_id") == "new"
    assert sm.audit_verify() is None


def test_supersede_idempotent_noop_records_nothing_new(tmp_path) -> None:
    sm = _sm(tmp_path)
    _store(sm, "old")
    _store(sm, "new")
    sm.supersede("old", "new", principal="sdk:local", reason="r")
    res2 = sm.supersede("old", "new", principal="sdk:local", reason="r")
    assert res2["idempotent_noop"] is True
    assert len(_audit_rows(sm)) == 1  # a noop mutated nothing -> no new row


def test_clear_records_reset_with_row_count(tmp_path) -> None:
    sm = _sm(tmp_path)
    for i in range(3):
        _store(sm, f"f{i}")
    sm.clear(principal="system:agent-reset")

    rows = _audit_rows(sm)
    assert len(rows) == 1
    r = rows[0]
    assert r["action"] == "reset"
    assert r["resource_id"] == "*"
    assert json.loads(r["detail"]).get("rows") == 3
    assert sm.audit_verify() is None


def test_chain_links_across_multiple_mutations(tmp_path) -> None:
    sm = _sm(tmp_path)
    for i in range(3):
        _store(sm, f"f{i}")
    sm.delete("f0", principal="sdk:local")
    sm.delete("f1", principal="sdk:local")
    sm.delete("f2", principal="sdk:local")

    rows = _audit_rows(sm)
    assert len(rows) == 3
    assert len({r["entry_hash"] for r in rows}) == 3
    assert sm.audit_verify() is None
    assert sm.audit_head() == rows[-1]["entry_hash"]


# ---------------------------------------------------------------------------
# Principal: mandatory at the core, never None, never blank
# ---------------------------------------------------------------------------

def test_delete_requires_principal(tmp_path) -> None:
    sm = _sm(tmp_path)
    _store(sm, "f1")
    with pytest.raises(TypeError):
        sm.delete("f1")  # omitted entirely
    with pytest.raises(ValueError):
        sm.delete("f1", principal=None)
    with pytest.raises(ValueError):
        sm.delete("f1", principal="   ")
    with pytest.raises(ValueError):
        sm.delete("f1", principal="x" * 10_000)  # unbounded id = chain DoS
    # and the refused calls must not have touched the row
    assert sm.get("f1") is not None
    assert _audit_rows(sm) == []


def test_supersede_requires_principal(tmp_path) -> None:
    sm = _sm(tmp_path)
    _store(sm, "old")
    _store(sm, "new")
    with pytest.raises(TypeError):
        sm.supersede("old", "new", reason="r")
    with pytest.raises(ValueError):
        sm.supersede("old", "new", principal="", reason="r")
    assert sm.get("old").superseded_by is None


def test_clear_requires_principal(tmp_path) -> None:
    sm = _sm(tmp_path)
    _store(sm, "f1")
    with pytest.raises(TypeError):
        sm.clear()
    assert sm.get("f1") is not None


# ---------------------------------------------------------------------------
# GDPR: no content — and no hash of content — ever enters the chain
# ---------------------------------------------------------------------------

def test_no_content_in_chain_on_delete(tmp_path) -> None:
    pii = "mario.rossi@example.com owes 12.345,67 EUR"
    sm = _sm(tmp_path)
    _store(sm, "f1", proposition=pii)
    sm.delete("f1", principal="sdk:local")

    for r in _audit_rows(sm):
        dump = "|".join(str(r[k]) for k in r.keys())
        assert "mario.rossi" not in dump
        assert "12.345,67" not in dump
        assert pii not in dump


def test_supersede_reason_never_in_chain(tmp_path) -> None:
    """``reason`` is free text (can carry PII); it lives on the mutable facts
    row (erasable), NEVER in the immutable chain."""
    sm = _sm(tmp_path)
    _store(sm, "old")
    _store(sm, "new")
    reason = "correcting mario.rossi@example.com's address"
    sm.supersede("old", "new", principal="sdk:local", reason=reason)

    for r in _audit_rows(sm):
        dump = "|".join(str(r[k]) for k in r.keys())
        assert "mario.rossi" not in dump
    # the reason still works as before, outside the chain
    assert sm.get("old").superseded_reason == reason


# ---------------------------------------------------------------------------
# Fail-closed + atomicity: no audit row => no mutation (same transaction)
# ---------------------------------------------------------------------------

def test_fail_closed_delete_rolls_back_when_audit_breaks(tmp_path) -> None:
    sm = _sm(tmp_path)
    _store(sm, "f1")
    with sqlite3.connect(sm.db_path) as conn:
        conn.execute("DROP TABLE audit_mutations")
    with pytest.raises(Exception):
        sm.delete("f1", principal="sdk:local")
    # the delete must have rolled back WITH the failed audit append
    assert sm.get("f1") is not None


def test_fail_closed_clear_rolls_back_when_audit_breaks(tmp_path) -> None:
    sm = _sm(tmp_path)
    _store(sm, "f1")
    with sqlite3.connect(sm.db_path) as conn:
        conn.execute("DROP TABLE audit_mutations")
    with pytest.raises(Exception):
        sm.clear(principal="system:agent-reset")
    assert sm.get("f1") is not None


# ---------------------------------------------------------------------------
# Tamper detection: edit / interior delete / reorder
# ---------------------------------------------------------------------------

def _three_audit_rows(tmp_path) -> SemanticMemory:
    sm = _sm(tmp_path)
    for i in range(3):
        _store(sm, f"f{i}")
    for i in range(3):
        sm.delete(f"f{i}", principal="sdk:local")
    assert sm.audit_verify() is None
    return sm


def test_verify_detects_edited_row(tmp_path) -> None:
    sm = _three_audit_rows(tmp_path)
    rows = _audit_rows(sm)
    with sqlite3.connect(sm.db_path) as conn:
        conn.execute("UPDATE audit_mutations SET principal='attacker' WHERE id=?",
                     (rows[0]["id"],))
    assert sm.audit_verify() == rows[0]["id"]


def test_verify_detects_interior_delete(tmp_path) -> None:
    sm = _three_audit_rows(tmp_path)
    rows = _audit_rows(sm)
    with sqlite3.connect(sm.db_path) as conn:
        conn.execute("DELETE FROM audit_mutations WHERE id=?", (rows[1]["id"],))
    assert sm.audit_verify() is not None


def test_verify_detects_nulled_hash(tmp_path) -> None:
    """NULLing a row's hash to demote it out of the check is itself tamper.

    The table's NOT NULL constraint blocks a naive UPDATE (defense in depth —
    verified: sqlite3.IntegrityError), so simulate the real adversary: a
    DB-owner rebuilds the table WITHOUT the constraint and NULLs the row.
    ``verify()`` must still flag it — it may never trust the schema."""
    sm = _three_audit_rows(tmp_path)
    rows = _audit_rows(sm)
    with sqlite3.connect(sm.db_path) as conn:
        conn.executescript(
            "ALTER TABLE audit_mutations RENAME TO am_old;"
            "CREATE TABLE audit_mutations (id TEXT PRIMARY KEY, ts REAL, "
            "principal TEXT, action TEXT, resource_id TEXT, detail TEXT, "
            "outcome TEXT, entry_hash TEXT);"
            "INSERT INTO audit_mutations SELECT * FROM am_old;"
            "DROP TABLE am_old;")
        conn.execute("UPDATE audit_mutations SET entry_hash=NULL WHERE id=?",
                     (rows[1]["id"],))
    assert sm.audit_verify() is not None


def test_supersede_chain_rollback_audits_the_restore(tmp_path, monkeypatch) -> None:
    """``supersede_chain`` commits hop-by-hop and, on a mid-chain failure,
    manually restores the already-committed hops. Those hops' audit rows are
    append-only — they cannot be retracted — so the RESTORE itself must be
    recorded, or the chain would describe a state the DB no longer shows
    (indistinguishable from state tampering to an auditor)."""
    sm = _sm(tmp_path)
    for fid in ("a", "b", "c"):
        _store(sm, fid)

    real = sm.supersede
    calls = {"n": 0}

    def fail_second(old_id, new_id, *, principal, reason=""):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom mid-chain")
        return real(old_id, new_id, principal=principal, reason=reason)

    monkeypatch.setattr(sm, "supersede", fail_second)
    res = sm.supersede_chain(["a", "b", "c"], principal="sdk:local",
                             reason="r")
    assert res["ok"] is False
    assert sm.get("a").superseded_by is None  # hop a->b rolled back

    rows = _audit_rows(sm)
    actions = [r["action"] for r in rows]
    assert "supersede" in actions          # the committed hop
    assert "restore" in actions            # ...and its recorded undo
    restore = [r for r in rows if r["action"] == "restore"]
    assert {r["resource_id"] for r in restore} == {"a"}
    assert sm.audit_verify() is None


def test_concurrent_deleters_never_fork_the_chain(tmp_path) -> None:
    """Anti-fork under real concurrency: the prev-head SELECT runs after the
    mutation's own write in the same tx, so SQLite's single-writer lock
    serializes chain appends. A fork (two rows chained off one head) would
    surface as a verify() mismatch — i.e. a FALSE tamper alarm on legitimate
    concurrent use, the worst failure mode an audit can have."""
    import threading

    sm = _sm(tmp_path)
    n = 24
    for i in range(n):
        _store(sm, f"f{i}")

    errors: list[str] = []

    def worker(ids: list[str]) -> None:
        w = SemanticMemory(db_path=sm.db_path)  # own connections, sister-like
        for fid in ids:
            try:
                w.delete(fid, principal="test:stress")
            except Exception as exc:  # noqa: BLE001 — collected, then asserted
                errors.append(f"{fid}: {exc!r}")

    threads = [threading.Thread(target=worker,
                                args=([f"f{i}" for i in range(k, n, 3)],))
               for k in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    rows = _audit_rows(sm)
    assert len(rows) == n
    assert len({r["entry_hash"] for r in rows}) == n
    assert sm.audit_verify() is None


# ---------------------------------------------------------------------------
# Surfaces stamp the principal; background jobs declare a system:* identity
# ---------------------------------------------------------------------------

def test_client_memory_delete_stamps_sdk_principal(tmp_path) -> None:
    """The SDK surface stays non-breaking: ``Memory.delete(fid)`` works with no
    principal argument and stamps the client's own (server-side) identity."""
    from verimem.client import Memory
    mem = Memory(path=tmp_path / "sem" / "sem.db")
    mem.semantic.store(Fact(id="f1", proposition="note", topic="t"),
                       embed="sync")
    assert mem.delete("f1") is True

    rows = _audit_rows(mem.semantic)
    assert len(rows) == 1
    assert rows[0]["principal"] == "sdk:local"
    assert rows[0]["action"] == "delete"


def test_client_purge_history_audits_as_purge(tmp_path) -> None:
    from verimem.client import Memory
    mem = Memory(path=tmp_path / "sem" / "sem.db")
    for fid in ("a", "b"):
        mem.semantic.store(Fact(id=fid, proposition=f"v {fid}", topic="t"),
                           embed="sync")
    mem.semantic.supersede("a", "b", principal="sdk:local", reason="update")
    assert mem.delete("b", purge_history=True) is True

    rows = _audit_rows(mem.semantic)
    purge_rows = [r for r in rows if r["action"] == "purge"]
    assert {r["resource_id"] for r in purge_rows} == {"a", "b"}
    assert all(r["principal"] == "sdk:local" for r in purge_rows)
    assert mem.semantic.audit_verify() is None


@pytest.mark.parametrize("module_name, expected", [
    ("verimem.truth_reconciliation", 'principal="system:reconcile"'),
    ("verimem.legacy_cleanup", 'principal="system:cleanup"'),
])
def test_background_jobs_declare_system_principal(module_name, expected) -> None:
    """Source-level contract: background jobs must call the destructive core
    with an EXPLICIT ``system:*`` principal (adversary finding F3: maintenance
    jobs are the classic audit bypass). Runtime enforcement is separately
    covered — a job that forgot the argument would crash on TypeError."""
    import importlib
    from pathlib import Path

    mod = importlib.import_module(module_name)
    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert expected in src


# ---------------------------------------------------------------------------
# CLI: verimem audit verify
# ---------------------------------------------------------------------------

def test_cli_audit_verify_intact_and_tampered(tmp_path, monkeypatch) -> None:
    from typer.testing import CliRunner

    from verimem.cli import app

    sm = _sm(tmp_path)
    _store(sm, "f1")
    sm.delete("f1", principal="cli:local")

    runner = CliRunner()
    res = runner.invoke(app, ["audit", "verify", "--db", str(sm.db_path)])
    assert res.exit_code == 0, res.output

    with sqlite3.connect(sm.db_path) as conn:
        conn.execute("UPDATE audit_mutations SET principal='attacker'")
    res2 = runner.invoke(app, ["audit", "verify", "--db", str(sm.db_path)])
    assert res2.exit_code != 0
