"""G5 (RELEASE_GATE): property-based invariants on core paths (hypothesis).

Two of the three gate invariants land here:
- tier classification is TOTAL and prefix-stable (the reconcile guard relies
  on it: a misclassified telemetry topic re-enters the judge);
- supersession never deletes and never loops (lineage code follows
  ``superseded_by`` chains; a cycle would hang or corrupt truth-maintenance).

Gate-admission monotonicity (L1) is tracked separately in RELEASE_GATE.
"""
from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from engram._telemetry_prefixes import (
    DIALOG_TOPIC_PREFIX,
    TELEMETRY_TOPIC_PREFIXES,
    TEST_TOPIC_PREFIXES,
    TIER_DIALOG,
    TIER_KNOWLEDGE,
    TIER_TELEMETRY,
    TIER_TEST,
    classify_tier,
)

_TIERS = {TIER_KNOWLEDGE, TIER_TELEMETRY, TIER_TEST, TIER_DIALOG}


@given(st.one_of(st.none(), st.text(max_size=80)))
def test_classify_tier_is_total(topic) -> None:
    assert classify_tier(topic) in _TIERS


@given(st.sampled_from(sorted(TELEMETRY_TOPIC_PREFIXES)),
       st.text(alphabet=st.characters(exclude_categories=("Cs",)), max_size=30))
def test_telemetry_prefix_always_telemetry(prefix, suffix) -> None:
    """Any topic under a telemetry prefix is telemetry no matter the suffix —
    the reconcile guard's contract."""
    assert classify_tier(prefix + suffix) == TIER_TELEMETRY


@given(st.text(alphabet=st.characters(exclude_categories=("Cs",)), max_size=30))
def test_dialog_voice_stays_telemetry_docs_stay_dialog(suffix) -> None:
    assert classify_tier("dialog/voice" + suffix) == TIER_TELEMETRY
    doc_topic = DIALOG_TOPIC_PREFIX + "doc" + suffix
    if classify_tier(doc_topic) != TIER_TELEMETRY:  # unless a telemetry prefix matches
        assert classify_tier(doc_topic) == TIER_DIALOG


# ---- supersession: never deletes, never cycles ------------------------------

@settings(max_examples=25, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.lists(st.tuples(st.integers(0, 7), st.integers(0, 7)),
                min_size=1, max_size=12))
def test_supersede_never_deletes_and_never_loops(tmp_path_factory, pairs) -> None:
    """Random sequences of supersede(old, new) over 8 facts: whatever the
    system ACCEPTS must (a) keep every fact retrievable by id and (b) leave
    ``superseded_by`` chains acyclic — lineage consumers follow them."""
    from engram.semantic import (
        Fact,
        SemanticMemory,
        SupersedeConflict,
        SupersedeError,
    )

    base = tmp_path_factory.mktemp("g5")
    mem = SemanticMemory(db_path=base / "semantic" / "semantic.db")
    ids = []
    for i in range(8):
        f = Fact(proposition=f"g5 invariant fact {i}", topic="t/g5")
        mem.store(f, embed="defer")
        ids.append(f.id)

    for a, b in pairs:
        try:
            mem.supersede(ids[a], ids[b], reason="g5-prop")
        except (SupersedeError, SupersedeConflict):
            pass  # rejected operations are fine; accepted ones must hold below

    # (a) nothing deleted
    for fid in ids:
        assert mem.get(fid) is not None, "supersede must never delete"

    # (b) no cycle when following superseded_by
    import sqlite3
    conn = sqlite3.connect(mem.db_path)
    try:
        succ = dict(conn.execute(
            "SELECT id, superseded_by FROM facts WHERE superseded_by IS NOT NULL"
        ).fetchall())
    finally:
        conn.close()
    for start in ids:
        seen = set()
        cur = start
        while cur is not None:
            assert cur not in seen, f"supersession cycle through {cur}"
            seen.add(cur)
            cur = succ.get(cur)


def test_long_ring_closure_rejected_no_hop_escape(tmp_path) -> None:
    """Adversarial-review counterexample (2026-07-04): a 70-hop chain closed
    into a ring through the old `hops <= 64` cap — all 70 facts vanished from
    default recall. The check must reject ring closure at ANY chain length."""
    import pytest

    from engram.semantic import Fact, SemanticMemory, SupersedeError

    mem = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    ids = []
    for i in range(70):
        f = Fact(proposition=f"ring fact {i}", topic="t/ring")
        mem.store(f, embed="defer")
        ids.append(f.id)
    for i in range(69):
        mem.supersede(ids[i], ids[i + 1], reason="chain")
    with pytest.raises(SupersedeError, match="cycle"):
        mem.supersede(ids[69], ids[0], reason="ring closure")
    # the head must still be live (nothing vanished)
    assert mem.get(ids[69]) is not None
