"""Cycle 161 (2026-05-19) — hybrid recall (semantic + keyword overlap).

Empirical motivation: cycle 160 bench fact 9379c8141a3e showed semantic-
only retrieval reaches TPR@5 = 40% on production store. Cycle 160 fact
7defa6248327 showed a keyword-overlap pass over ``trigger_keywords``
(populated on 5 pattern cards) lifts that to 80% on the same query set.
This module wires the two signals into ``SemanticMemory.recall_hybrid``:

  final_score = semantic_weight * cosine + (1-semantic_weight) * kw_overlap_norm

  where ``kw_overlap_norm`` = (#tokens shared between query and the fact's
  ``trigger_keywords``) / max(1, #unique-query-tokens).

Default ``semantic_weight=0.6`` follows cycle 160 fact 7defa6248327's
recommendation. Both signals are normalized to [0, 1] so the linear
combo is well-defined.

These tests pin the desired ranking behaviour against a tiny corpus
where the right answer differs depending on whether keyword overlap is
honoured.
"""
from __future__ import annotations

from pathlib import Path


def _make_fact_with_kw(*, prop: str, kw: list[str] | None = None,
                      topic: str = "test") -> object:
    from engram.semantic import Fact
    return Fact(
        proposition=prop,
        topic=topic,
        trigger_keywords=kw or [],
    )


# -----------------------------------------------------------------------
# R1: hybrid scoring uses keyword overlap when present
# -----------------------------------------------------------------------


def test_hybrid_recall_promotes_keyword_match(tmp_path: Path) -> None:
    """A fact whose trigger_keywords overlap the query MUST out-rank
    a fact with a closer cosine score but no keyword overlap, when
    the kw weight is non-zero. Pin the hybrid behaviour.
    """
    from engram.semantic import SemanticMemory

    sm = SemanticMemory(db_path=tmp_path / "semantic.db")
    # Two facts. Fact A is verbose, semantic-close to "AM-GM" query.
    # Fact B has only the keyword "AM-GM" in trigger_keywords.
    sm.store(_make_fact_with_kw(
        prop="generic notes about inequalities and bounding",
        kw=[],  # no kw
    ))
    f_kw = _make_fact_with_kw(
        prop="short note",
        kw=["AM-GM", "pairing", "factorial bound"],
    )
    sm.store(f_kw)
    hits = sm.recall_hybrid("AM-GM pairing closure", k=2,
                             semantic_weight=0.3)
    # f_kw must be first because the keyword signal dominates at 0.7.
    assert hits[0][0].id == f_kw.id, [h[0].id for h in hits]


# -----------------------------------------------------------------------
# R2: semantic_weight=1.0 ≡ classic recall (no kw contribution)
# -----------------------------------------------------------------------


def test_hybrid_recall_weight_1_matches_plain_recall(tmp_path: Path) -> None:
    from engram.semantic import SemanticMemory

    sm = SemanticMemory(db_path=tmp_path / "semantic.db")
    sm.store(_make_fact_with_kw(prop="AM-GM pairing closure proof", kw=[]))
    sm.store(_make_fact_with_kw(prop="unrelated", kw=["AM-GM"]))
    plain = sm.recall("AM-GM pairing closure", k=2)
    hybrid = sm.recall_hybrid("AM-GM pairing closure", k=2,
                               semantic_weight=1.0)
    assert [f.id for f, _ in plain] == [f.id for f, _ in hybrid]


# -----------------------------------------------------------------------
# R3: facts without trigger_keywords are NOT penalized by hybrid
# -----------------------------------------------------------------------


def test_hybrid_recall_facts_without_kw_get_zero_kw_score(tmp_path: Path) -> None:
    """Pre-cycle-160 facts have ``trigger_keywords=[]``. Their hybrid
    score must equal ``semantic_weight * cosine + (1-w) * 0`` — they
    are not actively penalized, just not boosted.
    """
    from engram.semantic import SemanticMemory

    sm = SemanticMemory(db_path=tmp_path / "semantic.db")
    # Very semantically similar fact with no kw — must still appear.
    sm.store(_make_fact_with_kw(
        prop="AM-GM pairing closure technique",
        kw=[],
    ))
    hits = sm.recall_hybrid("AM-GM pairing closure", k=1,
                             semantic_weight=0.5)
    assert len(hits) == 1
    # Score is non-zero (cosine contribution alone).
    assert hits[0][1] > 0.0


# -----------------------------------------------------------------------
# R4: empty query returns empty
# -----------------------------------------------------------------------


def test_hybrid_recall_empty_query(tmp_path: Path) -> None:
    from engram.semantic import SemanticMemory

    sm = SemanticMemory(db_path=tmp_path / "semantic.db")
    sm.store(_make_fact_with_kw(prop="x", kw=["a"]))
    assert sm.recall_hybrid("", k=5) == []
    assert sm.recall_hybrid("   ", k=5) == []
