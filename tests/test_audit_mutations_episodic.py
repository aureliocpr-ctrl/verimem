"""Episodic-store mutation audit — same contract as the facts chain (0.8 WS
step 3, closing the 'episodic deletes unaudited' gap declared in step 1).

The design is the facts chain's, verbatim (mutation_audit is
connection-agnostic by construction): one ``audit_mutations`` table INSIDE
episodes.db, rows appended in the SAME transaction as the destructive SQL,
fail-closed, principal keyword-only mandatory, action-only payload (episode
task_text / final_answer never enter the chain). New whitelist action
``decay`` distinguishes the automated retention pruning from a caller's
delete. Declared out of scope, same class as the facts cycle's
_cascade_delete_refs: gc_orphan_causal_edges (derived lineage-graph cleanup)
and the episodes_undo_log pruning (undo bookkeeping, not episodes).
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.memory import Episode, EpisodicMemory


def _em(tmp_path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_path / "episodes.db")


def _store(em: EpisodicMemory, eid: str) -> str:
    em.store(Episode(id=eid, task_text=f"task {eid}",
                     final_answer="done", outcome="success"))
    return eid


def _audit_rows(em: EpisodicMemory) -> list[sqlite3.Row]:
    with sqlite3.connect(em.db_path) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM audit_mutations ORDER BY rowid ASC").fetchall()


def test_delete_records_chained_action_row(tmp_path) -> None:
    em = _em(tmp_path)
    _store(em, "e1")
    assert em.delete("e1", principal="sdk:local") is True

    rows = _audit_rows(em)
    assert len(rows) == 1
    r = rows[0]
    assert r["principal"] == "sdk:local"
    assert r["action"] == "delete"
    assert r["resource_id"] == "e1"
    assert r["entry_hash"] and len(r["entry_hash"]) == 64
    assert em.get("e1") is None
    assert em.audit_verify() is None


def test_delete_requires_principal(tmp_path) -> None:
    em = _em(tmp_path)
    _store(em, "e1")
    with pytest.raises(TypeError):
        em.delete("e1")
    with pytest.raises(ValueError):
        em.delete("e1", principal=None)
    assert em.get("e1") is not None
    assert _audit_rows(em) == []


def test_delete_missing_episode_records_nothing(tmp_path) -> None:
    em = _em(tmp_path)
    assert em.delete("ghost", principal="sdk:local") is False
    assert _audit_rows(em) == []


def test_no_content_in_chain(tmp_path) -> None:
    em = _em(tmp_path)
    em.store(Episode(id="e1", task_text="mario.rossi@example.com asked X",
                     final_answer="secret answer 42", outcome="success"))
    em.delete("e1", principal="sdk:local")
    for r in _audit_rows(em):
        dump = "|".join(str(r[k]) for k in r.keys())
        assert "mario.rossi" not in dump
        assert "secret answer" not in dump


def test_clear_records_reset_with_counts(tmp_path) -> None:
    em = _em(tmp_path)
    for i in range(3):
        _store(em, f"e{i}")
    em.clear(principal="system:agent-reset")

    rows = _audit_rows(em)
    assert len(rows) == 1
    assert rows[0]["action"] == "reset"
    assert rows[0]["resource_id"] == "*"
    import json
    assert json.loads(rows[0]["detail"]).get("episodes") == 3
    assert em.audit_verify() is None


def test_clear_requires_principal(tmp_path) -> None:
    em = _em(tmp_path)
    _store(em, "e1")
    with pytest.raises(TypeError):
        em.clear()
    assert em.get("e1") is not None


def test_decay_prune_records_per_episode(tmp_path) -> None:
    """The retention job's bulk DELETE must leave one 'decay' row per pruned
    episode — a bulk wipe summarised as nothing is exactly the untracked
    deletion class this WS exists to close."""
    em = _em(tmp_path)
    for i in range(2):
        _store(em, f"e{i}")
    pruned = em.decay_prune(retention_threshold=2.0,
                            principal="system:decay")
    assert pruned == {"e0", "e1"}

    rows = _audit_rows(em)
    decay = [r for r in rows if r["action"] == "decay"]
    assert {r["resource_id"] for r in decay} == {"e0", "e1"}
    assert all(r["principal"] == "system:decay" for r in decay)
    assert em.audit_verify() is None


def test_decay_prune_requires_principal(tmp_path) -> None:
    em = _em(tmp_path)
    _store(em, "e1")
    with pytest.raises(TypeError):
        em.decay_prune(retention_threshold=2.0)


def test_delete_by_task_text_propagates_principal(tmp_path) -> None:
    em = _em(tmp_path)
    _store(em, "e1")
    n = em.delete_by_task_text("task e1", principal="cli:local")
    assert n == 1
    rows = _audit_rows(em)
    assert rows and all(r["principal"] == "cli:local" for r in rows)


def test_fail_closed_delete_rolls_back(tmp_path) -> None:
    em = _em(tmp_path)
    _store(em, "e1")
    with sqlite3.connect(em.db_path) as conn:
        conn.execute("DROP TABLE audit_mutations")
    with pytest.raises(Exception):
        em.delete("e1", principal="sdk:local")
    assert em.get("e1") is not None


def test_verify_detects_edited_row(tmp_path) -> None:
    em = _em(tmp_path)
    for i in range(2):
        _store(em, f"e{i}")
        em.delete(f"e{i}", principal="sdk:local")
    rows = _audit_rows(em)
    with sqlite3.connect(em.db_path) as conn:
        conn.execute("UPDATE audit_mutations SET principal='attacker' "
                     "WHERE id=?", (rows[0]["id"],))
    assert em.audit_verify() == rows[0]["id"]


def test_episode_telemetry_cleanup_audits_its_deletes(tmp_path) -> None:
    """The episodic side-door mover (same class as the facts cycle's
    narration/cleanup counterexample): cleanup_episode_telemetry DELETEs
    episodes rows on its own connection and must audit them, same tx."""
    import json

    from verimem._call_telemetry import is_call_telemetry
    from verimem.admission_cleanup import cleanup_episode_telemetry
    em = _em(tmp_path)
    tele_text = "[agy-call 3f2a] prompt=summarize logs"
    assert is_call_telemetry(tele_text), (
        "fixture must match the SAME predicate the mover uses — a non-match "
        "would make every assertion below vacuous")
    # Insert RAW: the live write-gate now routes this straight to
    # episode_telemetry, but this mover exists for the pre-gate BACKLOG —
    # simulate exactly that (a legacy row already sitting in episodes).
    with sqlite3.connect(em.db_path) as conn:
        conn.execute(
            "INSERT INTO episodes (id, task_id, task_text, outcome, "
            "final_answer, tokens_used, skills_used, created_at, notes, "
            "critique, summary_embedding) "
            "VALUES (?, '', ?, 'success', '', 0, '[]', 1.0, '', '', ?)",
            ("t1", tele_text, b""))

    with pytest.raises(TypeError):
        cleanup_episode_telemetry(em.db_path, dry_run=False)

    res = cleanup_episode_telemetry(
        em.db_path, principal="system:telemetry-cleanup", dry_run=False)
    assert res.get("moved", 0) == 1
    rows = _audit_rows(em)
    moved = [r for r in rows if r["action"] == "delete"]
    assert moved and all(
        r["principal"] == "system:telemetry-cleanup" for r in moved)
    assert all(json.loads(r["detail"]).get("moved_to") == "episode_telemetry"
               for r in moved)


@pytest.mark.parametrize("module_name, expected", [
    ("verimem.sleep", 'principal="system:decay"'),
    ("verimem.episode_dedup", 'principal="system:dedup"'),
])
def test_background_jobs_declare_system_principal(module_name, expected) -> None:
    import importlib
    from pathlib import Path

    mod = importlib.import_module(module_name)
    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert expected in src


def test_no_unaudited_destructive_sql_on_episodes() -> None:
    """Class guard, episodic twin of the facts guard: any module issuing raw
    DELETE FROM episodes outside memory.py must wire record_mutation."""
    import re
    from pathlib import Path

    import verimem
    pkg = Path(verimem.__file__).parent
    destructive = re.compile(r"DELETE\s+FROM\s+(?:\w+\.)?episodes\b(?!_)",
                             re.IGNORECASE)
    offenders = []
    for py in pkg.rglob("*.py"):
        if py.name in ("memory.py", "mutation_audit.py"):
            continue
        src = py.read_text(encoding="utf-8")
        if destructive.search(src) and "record_mutation" not in src:
            offenders.append(str(py.relative_to(pkg)))
    assert not offenders, (
        f"raw destructive SQL on episodes without mutation audit: {offenders}")
