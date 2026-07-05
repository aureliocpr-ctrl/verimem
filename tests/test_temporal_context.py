"""Answer-with-history (iter 42, mandato "la gemma") — the capability competitors
don't have: we KEEP the supersession chain (who replaced what, when, why), so an
answer can say "changed from X to Y on <date>" instead of serving only the final
value. Root need measured in the Memory-Conflict failure analysis: gold answers
narrate the TRANSITION ("increased from 3500 to 4500") while a reconciled store
serves only the current value — the history exists in the chain; recall must
surface it. Hermetic: no LLM, real SemanticMemory on tmp db.
"""
from __future__ import annotations

from engram.semantic import Fact, SemanticMemory
from engram.temporal_context import (
    fact_history,
    history_line,
    recall_with_history,
)

_BASE = 1_700_000_000.0     # fixed epoch, no wall clock in tests
_DAY = 86400.0


def _store_chain(tmp_path):
    """old --superseded_by--> mid --superseded_by--> new (the live fact).

    Bi-temporal contract (v13): the STORY dates live on asserted_at (event
    time); created_at stays now — backdating created_at would hide the facts
    from recall via the staleness half-life (the exact bug this replaced)."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    old = Fact(id="f-old", proposition="Johnson's monthly income is 3500 USD",
               topic="t", asserted_at=_BASE)
    mid = Fact(id="f-mid", proposition="Johnson's monthly income is 4500 USD",
               topic="t", asserted_at=_BASE + 30 * _DAY)
    new = Fact(id="f-new", proposition="Johnson's monthly income is 5000 USD",
               topic="t", asserted_at=_BASE + 60 * _DAY)
    for f in (old, mid, new):
        sm.store(f, embed="sync")
    sm.supersede("f-old", "f-mid", reason="update")
    sm.supersede("f-mid", "f-new", reason="update")
    return sm


def test_fact_history_walks_backward_most_recent_first(tmp_path) -> None:
    sm = _store_chain(tmp_path)
    hist = fact_history(sm, "f-new")
    assert [f.id for f in hist] == ["f-mid", "f-old"], \
        "predecessors of the live fact, most recent first"


def test_fact_history_bounded_and_empty_for_root(tmp_path) -> None:
    sm = _store_chain(tmp_path)
    assert fact_history(sm, "f-new", max_hops=1) and \
        len(fact_history(sm, "f-new", max_hops=1)) == 1
    assert fact_history(sm, "f-old") == [], "a root fact has no predecessors"
    assert fact_history(sm, "missing") == []


def test_history_line_renders_current_and_transitions(tmp_path) -> None:
    sm = _store_chain(tmp_path)
    new = sm.get("f-new")
    line = history_line(new, fact_history(sm, "f-new"))
    assert "5000" in line and "[current" in line
    assert "PREVIOUSLY" in line and "4500" in line and "3500" in line
    # dates make the transition answerable ("when did it change?")
    assert "2023-" in line or "2024-" in line, "ISO dates from created_at"


def test_history_line_plain_when_no_history(tmp_path) -> None:
    sm = _store_chain(tmp_path)
    old_style = history_line(sm.get("f-old"), [])
    assert "PREVIOUSLY" not in old_style


def test_recall_with_history_enriches_hits(tmp_path) -> None:
    sm = _store_chain(tmp_path)
    ctx = recall_with_history(sm, "Johnson monthly income", k=3)
    assert ctx, "recall returns context lines"
    joined = "\n".join(ctx)
    assert "5000" in joined, "live value present"
    assert "PREVIOUSLY" in joined and "3500" in joined, \
        "the transition story rides along with the live fact"


def test_recall_with_history_marks_unresolved_disputes(tmp_path) -> None:
    from engram.contradiction import Contradiction, ContradictionStore
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    a = Fact(id="d-a", proposition="Johnson works at Albi B&B", topic="t",
             asserted_at=_BASE)
    b = Fact(id="d-b", proposition="Johnson works at Hotel Riva", topic="t",
             asserted_at=_BASE + _DAY)
    sm.store(a, embed="sync")
    sm.store(b, embed="sync")
    cs = ContradictionStore(sm.db_path)
    cs.add(Contradiction(fact_a_id="d-a", fact_b_id="d-b",
                         kind="update-conflict", similarity=0.9))
    ctx = recall_with_history(sm, "where does Johnson work", k=3,
                              with_disputes=True)
    joined = "\n".join(ctx)
    assert "DISPUTED" in joined, "unresolved conflict is DECLARED, not hidden"
    assert "Albi" in joined and "Riva" in joined, "both sides visible"
