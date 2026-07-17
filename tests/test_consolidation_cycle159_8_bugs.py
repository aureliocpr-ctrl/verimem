"""Cycle 159.8 (2026-05-19) — empirical bugs in engram/consolidation.py.

Scaling experiment 2: 1 opus single vs 2 sonnet team on the same target.

Result was **MIXED — not a clean scaling win**:
- Arm C (opus single, 7 min, 1 tool call budget): caught the BIG bug —
  `_source_episodes_for_facts` calls ``json.loads`` on a column that
  ``SemanticMemory.store`` writes as a comma-separated string
  (``semantic.py:466``). The bare ``except`` swallowed every decode
  error, so the function always returned ``[]`` and the orchestrator
  always fell back to a single self-edge instead of the documented
  one-edge-per-source-episode. Breaks the orchestrator's core feature.
- Arm D (2 sonnet team via Charter, ~7 min): found 4 real bugs of
  lower-to-medium severity (empty fact_ids → SQL ``IN ()`` crash,
  self-loop fallback, idempotency probe ignores topic, LIKE wildcard
  injection on prefix), BUT **missed the json.loads / comma-separated
  mismatch entirely**.

Falsification: the hypothesis "two communicating sonnets always scale
beyond one opus" is rejected on N=2 (this task + the earlier llm.py
task). Real picture: team wins on recall/precision of varied-severity
bugs; single-opus wins when the bug requires cross-file evidence
(``semantic.py:466`` ↔ ``consolidation.py:204``) inside one context.

This file pins:
1. The opus-found HIGH bug (now fixed in this commit).
2. The team-found ``IN ()`` empty-fact_ids bug (also fixed).

See fact `591a8ea5f8ce` (159.7) and the follow-up 159.8 fact for the
full experimental log.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.consolidation import (
    _source_episodes_for_facts,
    propose_master_node,
)
from verimem.memory import EpisodicMemory
from verimem.semantic import Fact


@pytest.fixture
def mem(tmp_path: Path):
    """Yield a fresh (EpisodicMemory, SemanticMemory) pair.

    Cycle 159.8 tests only need ``sm`` (the SemanticMemory) to round-
    trip a Fact's ``source_episodes``; the EpisodicMemory is irrelevant
    here but kept to mirror the production call shape.
    """
    from verimem.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    ep = EpisodicMemory(db_path=tmp_path / "ep.db")

    class _Pair:
        pass
    pair = _Pair()
    pair.sm = sm
    pair.ep = ep
    return pair


# -----------------------------------------------------------------------
# Bug found by Arm-C opus: json.loads on a comma-separated column.
# -----------------------------------------------------------------------


def test_source_episodes_for_facts_reads_comma_separated_column(
    mem,
) -> None:
    """``SemanticMemory.store`` writes ``source_episodes`` as
    ``",".join(...)`` (semantic.py:466). Pre-fix the consolidation
    module called ``json.loads`` on the same column and silently lost
    every value. Post-fix it splits on commas and returns the real ids.
    """
    fact = Fact(
        proposition="cycle 159.8 bug-A test fact",
        topic="cycle158/test/scope/sub-A",
        confidence=0.9,
        source_episodes=["ep_alpha", "ep_beta", "ep_gamma"],
        status="model_claim",
    )
    mem.sm.store(fact)

    out = _source_episodes_for_facts(mem.sm, [fact.id])
    # Pre-fix: out == [] (json.loads raised, except continued).
    # Post-fix: out contains every stored episode id.
    assert set(out) == {"ep_alpha", "ep_beta", "ep_gamma"}, out


def test_source_episodes_for_facts_handles_single_episode(
    mem,
) -> None:
    """Even a single source_episode (which on disk is the bare token,
    no commas) must come back — pre-fix this also failed because
    ``json.loads("ep_solo")`` raises.
    """
    fact = Fact(
        proposition="cycle 159.8 single source",
        topic="cycle158/test/scope/sub-S",
        confidence=0.9,
        source_episodes=["ep_solo"],
        status="model_claim",
    )
    mem.sm.store(fact)
    out = _source_episodes_for_facts(mem.sm, [fact.id])
    assert out == ["ep_solo"], out


def test_source_episodes_for_facts_empty_fact_ids_returns_empty(
    mem,
) -> None:
    """Bug found by team Arm-D (heidi+ivan): an empty ``fact_ids``
    used to interpolate into ``WHERE id IN ()`` and crash with
    ``OperationalError: near ")"``. Post-fix we short-circuit and
    return ``[]``.
    """
    out = _source_episodes_for_facts(mem.sm, [])
    assert out == []


def test_propose_master_node_empty_fact_ids_does_not_crash(mem) -> None:
    """Falsification of one Arm-D (team) claim.

    Heidi+ivan reported ``propose_master_node`` with empty ``fact_ids``
    as a HIGH bug — they predicted ``SELECT ... IN ()`` would crash
    SQLite with ``OperationalError: near ")"``. We tested it directly
    on the installed SQLite (3.51.1 verified for cycle 156). SQLite
    actually accepts ``IN ()`` as "no match" and returns zero rows.
    The team's prediction was wrong — they confabulated the trigger.

    Pinning the actual behaviour: the call returns a master draft with
    an empty ``key_facts`` list, no exception. If a future SQLite
    version regresses this, the test breaks and we revisit.
    """
    out = propose_master_node(
        mem.sm, {"topic_prefix": "x/y", "fact_ids": [], "fact_count": 0},
    )
    assert out["key_facts"] == []
    assert out["topic"].endswith("auto-MASTER")
