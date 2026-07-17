"""FORGIA pezzo #174 — `EpisodicMemory.synaptic_tag_candidates`.

Synaptic tagging (Frey & Morris 1997): a weak event that occurs
shortly before a strong event on a related substrate gets
"tagged" — its consolidation is rescued from natural decay because
the system retrospectively interprets it as part of a learning
trajectory that ultimately succeeded.

In HippoAgent terms: an episode that *failed* but was followed
soon after by a *success* on at least one shared skill is tagged
for priority replay. The agent thus learns from the *failure*
that immediately preceded the *correct* approach — exactly how
humans do post-mortem reflection.

This module returns the candidate `(weak_id, strong_id)` tuples;
the sleep engine (#175+) will use them to prioritize replay.
"""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(eid: str, *, skills: list[str], outcome: str,
        ts: float) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=list(skills),
        created_at=ts,
    )


def test_synaptic_tag_empty(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    assert mem.synaptic_tag_candidates() == []


def test_synaptic_tag_no_failures(tmp_path: Path):
    """Pure-success memory: no weak events to tag."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    now = time.time()
    mem.store(_ep("s1", skills=["A"], outcome="success", ts=now))
    mem.store(_ep("s2", skills=["A"], outcome="success", ts=now + 100))
    assert mem.synaptic_tag_candidates() == []


def test_synaptic_tag_basic_pair(tmp_path: Path):
    """Failure → success on same skill within window → tag."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    now = time.time()
    mem.store(_ep("f1", skills=["A"], outcome="failure", ts=now))
    mem.store(_ep("s1", skills=["A"], outcome="success", ts=now + 60))
    pairs = mem.synaptic_tag_candidates(window_s=120.0)
    assert pairs == [("f1", "s1")]


def test_synaptic_tag_outside_window(tmp_path: Path):
    """Failure followed by success but beyond window → no tag."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    now = time.time()
    mem.store(_ep("f1", skills=["A"], outcome="failure", ts=now))
    mem.store(_ep("s1", skills=["A"], outcome="success",
                   ts=now + 10_000))
    assert mem.synaptic_tag_candidates(window_s=120.0) == []


def test_synaptic_tag_different_skill(tmp_path: Path):
    """Failure followed by success on a DIFFERENT skill → no tag."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    now = time.time()
    mem.store(_ep("f1", skills=["A"], outcome="failure", ts=now))
    mem.store(_ep("s1", skills=["B"], outcome="success", ts=now + 30))
    assert mem.synaptic_tag_candidates(window_s=120.0) == []


def test_synaptic_tag_multi_failures_one_success(tmp_path: Path):
    """Two failures on skill A, one success — both tagged."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    now = time.time()
    mem.store(_ep("f1", skills=["A"], outcome="failure", ts=now))
    mem.store(_ep("f2", skills=["A"], outcome="failure", ts=now + 30))
    mem.store(_ep("s1", skills=["A"], outcome="success", ts=now + 60))
    pairs = mem.synaptic_tag_candidates(window_s=120.0)
    assert sorted(pairs) == [("f1", "s1"), ("f2", "s1")]


def test_synaptic_tag_failure_after_success_not_tagged(tmp_path: Path):
    """Reverse temporal order — success FIRST, failure AFTER → not tagged.
    The synaptic tag mechanism is causally one-way: the strong event
    rescues PRIOR weak events, not subsequent ones."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    now = time.time()
    mem.store(_ep("s1", skills=["A"], outcome="success", ts=now))
    mem.store(_ep("f1", skills=["A"], outcome="failure", ts=now + 60))
    assert mem.synaptic_tag_candidates(window_s=120.0) == []
