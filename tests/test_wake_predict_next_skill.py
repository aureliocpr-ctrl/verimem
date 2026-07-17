"""Tests for FORGIA pezzo #24: `WakeAgent.predict_next_skill` API.

Pezzo #20 forged the SR primitive. Pezzo #23 added SR-clustering.
This pezzo wires SR into the wake as a query API: given the current
sequence of used skills, what skills are most likely to come next?

Use cases:
- Wake loop hint generation (inject "expected next: X" in prompt).
- Programmatic introspection (debugging, dashboard).
- Programmatic planning (an external orchestrator can ask the agent
  what it would do next).

Three measurable invariants:

  1. PREDICT FROM HISTORY: with past episodes A→B, querying with
     ['A'] returns 'B' as the top candidate.

  2. EMPTY HISTORY OR EMPTY CORPUS returns [].

  3. RESPECTS top_k LIMIT: with multiple successors, requesting
     top_k=2 returns 2 candidates ordered by transition probability.
"""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(*, ep_id: str, skills: list[str]) -> Episode:
    return Episode(
        id=ep_id, task_id=ep_id, task_text="task",
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="A",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=skills,
        created_at=time.time(),
    )


def _build_wake(memory):
    from verimem.wake import WakeAgent, WakeConfig
    wake = object.__new__(WakeAgent)
    wake.memory = memory  # type: ignore[misc]
    wake.cfg = WakeConfig(max_steps=4, self_critique=False)
    return wake


# ---------- Test 1: predict from past transitions ---------------------


def test_predict_next_skill_from_past_transitions(tmp_path: Path):
    """3 episodes with A→B trajectory. Asking the wake for the next
    skill after A should return B at top-1."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i in range(3):
        mem.store(_ep(ep_id=f"e{i}", skills=["A", "B"]))
    # Add some noise.
    mem.store(_ep(ep_id="n0", skills=["C", "D"]))

    wake = _build_wake(mem)
    out = wake.predict_next_skill(["A"], top_k=1)
    assert out, "no prediction returned"
    assert out[0] == "B", f"expected 'B', got {out}"


# ---------- Test 2: empty corpus or empty history --------------------


def test_predict_next_skill_empty_corpus(tmp_path: Path):
    """Empty memory -> []."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    wake = _build_wake(mem)
    assert wake.predict_next_skill(["A"], top_k=3) == []


def test_predict_next_skill_empty_history(tmp_path: Path):
    """Empty `used_skills` -> [] (no anchor to predict from)."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep(ep_id="e0", skills=["A", "B"]))
    wake = _build_wake(mem)
    assert wake.predict_next_skill([], top_k=3) == []


# ---------- Test 3: top_k limit ---------------------------------------


def test_predict_next_skill_top_k(tmp_path: Path):
    """With multiple successors, top_k bounds the result count."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # A is followed by B (3x), C (2x), D (1x).
    for _ in range(3):
        mem.store(_ep(ep_id=f"ab{_}", skills=["A", "B"]))
    for _ in range(2):
        mem.store(_ep(ep_id=f"ac{_}", skills=["A", "C"]))
    mem.store(_ep(ep_id="ad", skills=["A", "D"]))

    wake = _build_wake(mem)
    out = wake.predict_next_skill(["A"], top_k=2)
    assert len(out) == 2
    # B should be first (3 vs 2 vs 1).
    assert out[0] == "B"


# ---------- Test 4: unknown current skill ----------------------------


def test_predict_next_skill_unknown_current(tmp_path: Path):
    """Querying with a skill that has no past episodes -> []."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep(ep_id="e0", skills=["A", "B"]))
    wake = _build_wake(mem)
    out = wake.predict_next_skill(["UNKNOWN"], top_k=3)
    assert out == []
