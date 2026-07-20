"""The session-start banner must not re-surface memory the moat already rejected.

The pre-tool-use hook recalls through the real retrieval path, which hides
superseded and low-trust facts (semantic.py: `WHERE superseded_by IS NULL`,
status rank). The SESSION-START hook did NOT — it ran a raw SQL SELECT that
bypassed the moat and ordered by created_at, so at the top of every session it
re-injected:

  * QUARANTINED facts — the anti-confab gate flagged them at write time as
    suspect/contradictory and hid them from recall;
  * SUPERSEDED facts — an old value already replaced by a newer one (the tank
    holds 500 → 750; the 500 came back as if current).

That is memory poisoning its own context in good faith: the gate does its job on
write, and the startup hook then serves the rejects back as current knowledge —
the failure mode where a wrong recall compounds into a wrong decision.

Fix: the startup banner goes through the SAME trust filter as recall — exclude
superseded, and exclude the statuses recall hides (orphaned / quarantined /
user_belief). Schema-tolerant: a legacy DB without those columns still works.
"""
from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

_HOOK = Path(__file__).resolve().parents[1] / "hooks" / "hippo_session_start.py"
_spec = importlib.util.spec_from_file_location("hippo_session_start", _HOOK)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def _make_db(path: Path, rows: list[tuple]) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE facts (proposition TEXT, topic TEXT, created_at REAL, "
        "writer_role TEXT, status TEXT, superseded_by TEXT)"
    )
    conn.executemany("INSERT INTO facts VALUES (?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()


def _props(rows) -> str:
    return " | ".join(r[0] for r in rows)


def test_quarantined_and_superseded_never_surface(tmp_path):
    db = tmp_path / "facts.db"
    _make_db(db, [
        ("Tank holds 750 liters.", "ops", 100, "agent_inference", "verified", None),
        ("Tank holds 500 liters (OLD).", "ops", 90, "agent_inference",
         "verified", "id-new"),                                   # superseded
        ("Suspect contradictory claim.", "ops", 110, "agent_inference",
         "quarantined", None),                                    # quarantined
        ("Orphaned scrubbed row.", "ops", 111, "agent_inference",
         "orphaned", None),                                       # orphaned
        ("An unverified user belief.", "ops", 112, "agent_inference",
         "user_belief", None),                                    # user_belief
    ])
    out = _props(hook._safe_recent_facts(db))
    assert "OLD" not in out, f"superseded fact re-surfaced: {out}"
    assert "Suspect" not in out, f"quarantined fact re-surfaced: {out}"
    assert "Orphaned" not in out, f"orphaned fact re-surfaced: {out}"
    assert "user belief" not in out, f"user_belief re-surfaced: {out}"


def test_trustworthy_current_facts_still_surface(tmp_path):
    """Narrowness: the useful memory must still come through."""
    db = tmp_path / "facts.db"
    _make_db(db, [
        ("Tank holds 750 liters.", "ops", 100, "agent_inference", "verified", None),
        ("Deploy is green.", "ci", 101, "agent_inference", "model_claim", None),
        ("A provisional hypothesis.", "r", 102, "agent_inference",
         "provisional", None),
    ])
    out = _props(hook._safe_recent_facts(db))
    assert "750" in out and "Deploy is green" in out and "hypothesis" in out, out


def test_legacy_schema_without_status_columns_does_not_crash(tmp_path):
    """Schema tolerance: a pre-migration DB (no status/superseded_by) still
    returns rows instead of raising."""
    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE facts (proposition TEXT, topic TEXT, created_at REAL)")
    conn.execute("INSERT INTO facts VALUES ('legacy fact', 't', 1.0)")
    conn.commit()
    conn.close()
    out = _props(hook._safe_recent_facts(db))
    assert "legacy fact" in out, out
