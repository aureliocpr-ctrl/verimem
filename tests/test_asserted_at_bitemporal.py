"""Bi-temporal asserted_at (v13, iter 42 — mandato "la gemma").

Root-caused today: stuffing the SEMANTIC time into created_at made the
staleness half-life hide backdated-but-current facts and the anti-spoof
fail-closed guard hide future-dated ones (HaluMem u1: 673/807 facts = 83%
invisible in every QA run today — the 0.59 was scored with 17% of the memory).

The honest model is bi-temporal:
  * ``created_at``  = TRANSACTION time (when the system learned it; never
    backdated -> staleness + anti-spoof guards stay sound);
  * ``asserted_at`` = EVENT time (when it was said/true; drives the reconcile
    age-gap and the history story; future values are LEGITIMATE — calendar
    facts — and must not be treated as spoofing).
Hermetic, no LLM.
"""
from __future__ import annotations

import time

from engram.semantic import Fact, SemanticMemory

_DAY = 86400.0


def test_fact_roundtrips_asserted_at(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    ts = 1_700_000_000.0
    sm.store(Fact(id="a", proposition="Johnson income is 3500", topic="t",
                  asserted_at=ts), embed="sync")
    f = sm.get("a")
    assert f is not None and abs(float(f.asserted_at) - ts) < 1.0
    # transaction time stays honest (now-ish), untouched by the event time
    assert float(f.created_at) > time.time() - 3600


def test_recall_serves_past_and_future_asserted_facts(tmp_path) -> None:
    """Event time must NOT feed the staleness/anti-spoof guards: a fact said
    years ago and one about a future appointment are both live memory."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    sm.store(Fact(id="past", proposition="Johnson salary was set in an old chat",
                  topic="t", asserted_at=now - 10 * 365 * _DAY), embed="sync")
    sm.store(Fact(id="fut", proposition="Johnson flight booked for a future date",
                  topic="t", asserted_at=now + 7 * 365 * _DAY), embed="sync")
    got = {f.id for f, *_ in sm.recall("Johnson", k=5)}
    assert {"past", "fut"} <= got, \
        "backdated/future EVENT time must not hide live facts from recall"


def test_reconcile_age_gap_uses_asserted_at(tmp_path) -> None:
    """Two facts ingested in the same batch (created_at ~= now for both) but
    asserted 30 days apart: the update must supersede — the age gap lives in
    EVENT time now, not in transaction time. (Entities linked manually, same
    pattern as test_reconcile_on_write_wiring — the extraction regex is not
    under test here.)"""
    from engram.entity_kg import Entity

    base = time.time() - 60 * _DAY
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    old = Fact(id="old", proposition="config X is 30s", topic="t",
               status="verified", confidence=0.9, asserted_at=base)
    new = Fact(id="new", proposition="config X is 5s", topic="t",
               status="verified", confidence=0.9,
               asserted_at=base + 30 * _DAY)
    sm.store(old)
    sm.store(new)
    es = sm._recall_entity_store()
    eid = es.store(Entity(canonical_name="config_x", type="config"))
    es.link_fact("old", eid)
    es.link_fact("new", eid)
    res = sm.reconcile_new_fact(new, auto_supersede=True)
    assert "old" in res["superseded"], \
        "same-batch ingest with asserted_at gap must still supersede"
    assert sm.get("old").superseded_by == "new"


def test_classify_conflict_prefers_asserted_at() -> None:
    from engram.truth_reconciliation import classify_conflict
    now = time.time()
    # created_at identical (same ingest batch); asserted_at 30 days apart
    old = Fact(id="o", proposition="income is 3500", topic="t",
               created_at=now, asserted_at=now - 30 * _DAY)
    new = Fact(id="n", proposition="income is 5000", topic="t",
               created_at=now, asserted_at=now)
    assert classify_conflict(old, new, now=now) == "update"
    # and the REVERSED event order must not update (newer info is the OLD one)
    assert classify_conflict(new, old, now=now) == "dispute"


def test_classify_conflict_future_assertion_cannot_supersede_present() -> None:
    """Review 5-lenti C6: an asserted_at in the FUTURE is legitimate v13 data
    (appointments, planned moves) but it is NOT yet current truth — it must not
    delete the present fact at write time. Fail-safe direction: dispute
    (recoverable, surfaces in the TrustReport); promoting the fact once its
    time arrives is a re-reconcile concern, not a write-path one."""
    from engram.truth_reconciliation import classify_conflict
    now = time.time()
    old = Fact(id="o", proposition="Aurelio lives in Rome", topic="t",
               created_at=now, asserted_at=now)
    new = Fact(id="n", proposition="Aurelio lives in Milan", topic="t",
               created_at=now, asserted_at=now + 60 * _DAY)
    assert classify_conflict(old, new, now=now) == "dispute", \
        "a future-dated assertion must not supersede present truth"
    # the same pair evaluated once the future date HAS arrived: clean update
    assert classify_conflict(old, new, now=now + 61 * _DAY) == "update"
