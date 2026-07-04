"""Durability of DEFERRED stores: intent journal + boot replay.

Live incident 2026-06-10 (~01:00): ``hippo_remember`` answered
``ok:true + deferred:true`` (write budget exceeded, SQLite lock held by a
dream-length writer), the MCP server process was then terminated, and the
fact (9e4211057e4d) was NEVER persisted anywhere — at-most-once delivery
masked as success. ``store_within_budget``'s docstring promised "durable,
the write is NOT lost", which only held while the interpreter stayed alive
(atexit flush is skipped on TerminateProcess / kill).

Contract under test (RED pre-fix):
  1. When a store is DEFERRED, an intent entry lands in
     ``pending_facts.jsonl`` next to the semantic db (fsync'd) BEFORE the
     caller gets ``{"deferred": True}`` — surviving any later kill.
  2. ``SemanticMemory.__init__`` replays orphan entries: the fact appears
     in the DB and the journal is consumed.
  3. Replay is idempotent: an entry whose fact id already exists is
     skipped (no duplicate, no overwrite of an evolved fact).
  4. When the background thread DOES complete the write, it appends a
     ``done`` marker; a later replay must not re-insert that fact.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict

import engram.semantic as semantic_mod
from engram.semantic import Fact, SemanticMemory, store_within_budget


class _BlockingMemory:
    """Fake memory whose store() blocks until the test releases it."""

    def __init__(self, db_path, release: threading.Event):
        self.db_path = db_path
        self._release = release
        self.stored: list[Fact] = []

    def store(self, fact, **kwargs):
        self._release.wait(timeout=10)
        self.stored.append(fact)
        return None


def _journal(db_path):
    return semantic_mod._journal_path_for(db_path)


def _read_lines(path):
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ── 1. deferred -> intent entry on disk BEFORE the caller's reply ───────────

def test_deferred_store_writes_intent_journal(tmp_path):
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    release = threading.Event()
    mem = _BlockingMemory(db, release)
    fact = Fact(proposition="journal me before you kill me", topic="t/j")

    res = store_within_budget(mem, fact, budget_s=0.05, embed="sync")
    try:
        assert res.get("deferred") is True, "store must report deferred"
        jpath = _journal(db)
        assert jpath.exists(), (
            "a DEFERRED store must journal its intent on disk synchronously"
        )
        entries = _read_lines(jpath)
        pend = [e for e in entries if e.get("kind") == "fact"]
        assert len(pend) == 1
        assert pend[0]["fact"]["id"] == fact.id
        assert pend[0]["fact"]["proposition"] == fact.proposition
    finally:
        release.set()
        time.sleep(0.05)  # let the worker thread drain before tmp cleanup


# ── 2. boot replay: orphan entry -> fact lands in the DB, journal consumed ──

def test_replay_pending_facts_on_init(tmp_path):
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    # Create the DB schema (and prove no fact is present), then close.
    boot = SemanticMemory(db_path=db)
    assert boot.get("deadbeef0000") is None

    orphan = Fact(proposition="i survived a process kill", topic="t/replay")
    _journal(db).write_text(
        json.dumps({"kind": "fact", "fact": asdict(orphan),
                    "store_kwargs": {"embed": "sync"}}) + "\n",
        encoding="utf-8",
    )

    sm = SemanticMemory(db_path=db)  # init must replay
    got = sm.get(orphan.id)
    assert got is not None, "boot replay must persist the orphan intent"
    assert got.proposition == orphan.proposition
    assert not _journal(db).exists(), "journal must be consumed after replay"


# ── 3. idempotent: existing id is skipped, not overwritten ──────────────────

def test_replay_skips_existing_fact_idempotent(tmp_path):
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    sm = SemanticMemory(db_path=db)
    fact = Fact(proposition="original survived version", topic="t/idem")
    sm.store(fact, embed="sync")

    stale = asdict(fact)
    stale["proposition"] = "STALE journal copy - must NOT overwrite"
    _journal(db).write_text(
        json.dumps({"kind": "fact", "fact": stale,
                    "store_kwargs": {"embed": "sync"}}) + "\n",
        encoding="utf-8",
    )

    sm2 = SemanticMemory(db_path=db)
    got = sm2.get(fact.id)
    assert got.proposition == "original survived version", (
        "replay must SKIP an id that already exists (no overwrite)"
    )
    assert not _journal(db).exists()


# ── 4. background completion -> done marker -> later replay does nothing ────

def test_background_completion_marks_done_no_replay_dup(tmp_path):
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    release = threading.Event()
    mem = _BlockingMemory(db, release)
    fact = Fact(proposition="completed late but completed", topic="t/done")

    res = store_within_budget(mem, fact, budget_s=0.05, embed="sync")
    assert res.get("deferred") is True
    release.set()
    deadline = time.time() + 5
    while time.time() < deadline:
        entries = _read_lines(_journal(db)) if _journal(db).exists() else []
        if any(e.get("kind") == "done" and e.get("id") == fact.id
               for e in entries):
            break
        time.sleep(0.02)
    else:
        raise AssertionError(
            "background completion must append a done-marker for the entry"
        )

    sm = SemanticMemory(db_path=db)  # replay: entry is done -> skip + clean
    assert sm.get(fact.id) is None, (
        "done-marked entry must NOT be re-inserted by replay"
    )
    assert not _journal(db).exists()
