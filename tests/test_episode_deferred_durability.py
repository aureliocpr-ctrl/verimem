"""Deferred EPISODE writes must survive a hard kill (bug-hunt F2/F4).

The fact write-path journals a deferred store to pending_facts.jsonl and
replays it on boot (SemanticMemory.__init__), so a kill between the
"ok_deferred" ack and the background write never loses the fact. The
EPISODE path reused store_within_budget (mcp_server hippo_record_episode)
but the replay half was wired ONLY for SemanticMemory: EpisodicMemory
never called _replay_pending_facts, and the journal entry was tagged
kind="fact" + rebuilt as a Fact — so a deferred episode that didn't
complete before a kill was silently lost despite the success ack.

Fix: store_within_budget tags the journal entry by object type
(episode vs fact); _replay_pending_facts reconstructs an Episode (with
its nested Trace list) for kind="episode"; EpisodicMemory.__init__
replays its own journal on boot.

RED marker: pre-fix EpisodicMemory.__init__ does not replay, and the
journal/replay only understands Facts.
"""
from __future__ import annotations

import dataclasses as dc
import json
import time
from pathlib import Path

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory
from engram.semantic import store_within_budget


def _journal(db: Path) -> Path:
    return db.parent / "pending_facts.jsonl"


def _orphan_episode_entry(ep: Episode) -> str:
    return json.dumps({
        "kind": "episode", "ts": time.time(),
        "episode": dc.asdict(ep),
        "store_kwargs": {"embed": "sync"},
    })


# ── boot replay of an orphaned episode intent ───────────────────────────────

def test_episode_replayed_on_init(tmp_path: Path) -> None:
    db = tmp_path / "episodes" / "episodes.db"
    db.parent.mkdir(parents=True)
    boot = EpisodicMemory(db_path=db)            # create schema
    assert boot.get("ep-survives-0001") is None

    ep = Episode(id="ep-survives-0001", task_text="kill-survivor task",
                 final_answer="the deferred episode came back",
                 traces=[Trace(step=1, thought="t", action="a",
                               action_input="i", observation="o")])
    _journal(db).write_text(_orphan_episode_entry(ep) + "\n", encoding="utf-8")

    mem = EpisodicMemory(db_path=db)             # __init__ must replay
    got = mem.get("ep-survives-0001")
    assert got is not None, "boot replay must persist the orphaned episode"
    assert got.final_answer == "the deferred episode came back"
    assert not _journal(db).exists(), "journal consumed after replay"


def test_episode_replay_reconstructs_traces(tmp_path: Path) -> None:
    db = tmp_path / "episodes" / "episodes.db"
    db.parent.mkdir(parents=True)
    EpisodicMemory(db_path=db)
    ep = Episode(id="ep-trace-0002", task_text="t",
                 traces=[Trace(step=1, thought="th", action="ac",
                               action_input="ai", observation="ob")])
    _journal(db).write_text(_orphan_episode_entry(ep) + "\n", encoding="utf-8")

    got = EpisodicMemory(db_path=db).get("ep-trace-0002")
    assert got is not None
    assert got.traces and isinstance(got.traces[0], Trace), (
        "nested traces must be rebuilt as Trace objects, not dicts"
    )
    assert got.traces[0].observation == "ob"


def test_episode_replay_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "episodes" / "episodes.db"
    db.parent.mkdir(parents=True)
    mem = EpisodicMemory(db_path=db)
    ep = Episode(id="ep-idem-0003", task_text="orig", final_answer="original")
    mem.store(ep, embed="sync")

    stale = dc.asdict(ep)
    stale["final_answer"] = "STALE must not overwrite"
    _journal(db).write_text(json.dumps({
        "kind": "episode", "ts": time.time(), "episode": stale,
        "store_kwargs": {"embed": "sync"}}) + "\n", encoding="utf-8")

    got = EpisodicMemory(db_path=db).get("ep-idem-0003")
    assert got is not None and got.final_answer == "original", (
        "replay must skip an episode id that already exists"
    )


# ── store_within_budget tags episodes correctly ─────────────────────────────

def test_store_within_budget_journals_episode_kind(tmp_path: Path) -> None:
    """Under a held write lock, a deferred episode store journals with
    kind=episode (not fact) so the replay can rebuild it."""
    import sqlite3

    db = tmp_path / "episodes" / "episodes.db"
    db.parent.mkdir(parents=True)
    mem = EpisodicMemory(db_path=db)
    ep = Episode(id="ep-journal-0004", task_text="held",
                 final_answer="deferred under lock")

    holder = sqlite3.connect(str(db), timeout=30)
    holder.execute("PRAGMA journal_mode=WAL;")
    holder.execute("BEGIN IMMEDIATE")
    holder.execute("UPDATE episodes SET notes = notes WHERE 1=0")
    try:
        res = store_within_budget(mem, ep, budget_s=0.5, embed="sync")
    finally:
        holder.rollback()
        holder.close()

    assert res.get("deferred") is True, "held lock must force a deferral"
    lines = _journal(db).read_text(encoding="utf-8").splitlines()
    entries = [json.loads(ln) for ln in lines]
    kinds = {e.get("kind") for e in entries}
    assert "episode" in kinds, f"episode intent must be journaled, got {kinds}"
    ep_entry = next(e for e in entries if e.get("kind") == "episode")
    assert ep_entry["episode"]["id"] == "ep-journal-0004"
