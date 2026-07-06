"""Deep recall + as-of recall (iter 46, mandato "ricordo sommerso / 3 mesi fa").

Measured gap: the 45-day freshness half-life hides a dormant fact from default
recall — "Client Rossi set the budget at 500k in March" queried 3 months later
returns an UNRELATED fresh fact instead (empirical 2026-07-05). Right for ops
noise, wrong as the ONLY mode for a professional memory (lawyer / researcher /
real-estate: facts must be findable YEARS later).

* ``recall(deep=True)`` — archaeology mode: age-based hiding OFF; the anti-spoof
  guard (transaction time in the future = tampering) and the valid_until
  hard-expire STAY (they are integrity guards, not freshness).
* ``recall_as_of(sm, query, when)`` — time travel over the bi-temporal store:
  what was CURRENT at ``when`` (asserted before it, not yet superseded by then).
  No competitor can answer "what did we know in March?".

Hermetic, no LLM.
"""
from __future__ import annotations

import time

from engram.semantic import Fact, SemanticMemory

_DAY = 86400.0


def _seed_dormant(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    sm.store(Fact(id="m3", topic="client/rossi",
                  proposition="Client Rossi set the budget at 500k in March",
                  created_at=now - 90 * _DAY,
                  last_verified_at=now - 90 * _DAY), embed="sync")
    sm.store(Fact(id="fresh", topic="client/bianchi",
                  proposition="Client Bianchi prefers morning meetings",
                  created_at=now - 3600), embed="sync")
    return sm, now


def test_default_recall_hides_dormant_fact_but_deep_finds_it(tmp_path) -> None:
    sm, _ = _seed_dormant(tmp_path)
    got_default = {f.id for f, *_ in sm.recall("Rossi budget", k=5)}
    assert "m3" not in got_default, "default view unchanged (45d half-life)"
    got_deep = {f.id for f, *_ in sm.recall("Rossi budget", k=5, deep=True)}
    assert "m3" in got_deep, "deep recall surfaces the submerged memory"


def test_deep_keeps_integrity_guards(tmp_path) -> None:
    """deep lifts the AGE hiding only: a future transaction time (tamper signal)
    and an expired valid_until stay excluded."""
    sm, now = _seed_dormant(tmp_path)
    sm.store(Fact(id="spoof", topic="t",
                  proposition="Client Rossi budget spoofed entry",
                  created_at=now + 365 * _DAY,
                  last_verified_at=now + 365 * _DAY), embed="sync")
    sm.store(Fact(id="expired", topic="t",
                  proposition="Client Rossi budget expired note",
                  created_at=now - 3600, valid_until=now - 60), embed="sync")
    got = {f.id for f, *_ in sm.recall("Rossi budget", k=10, deep=True)}
    assert "spoof" not in got, "future transaction time stays out even in deep"
    assert "expired" not in got, "valid_until hard-expire stays out even in deep"


def test_deep_recall_on_topic_path_too(tmp_path) -> None:
    """The topic-filtered (non-cache) path honours deep as well."""
    sm, _ = _seed_dormant(tmp_path)
    got = {f.id for f, *_ in sm.recall("Rossi budget", k=5,
                                       topic="client/rossi", deep=True)}
    assert "m3" in got


def test_recall_as_of_reconstructs_the_past(tmp_path) -> None:
    from engram.temporal_context import recall_as_of
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    mar = now - 120 * _DAY
    jun = now - 30 * _DAY
    old = Fact(id="f-old", topic="t", asserted_at=mar,
               proposition="Johnson's monthly income is 3500 USD")
    new = Fact(id="f-new", topic="t", asserted_at=jun,
               proposition="Johnson's monthly income is 5000 USD")
    sm.store(old, embed="sync")
    sm.store(new, embed="sync")
    sm.supersede("f-old", "f-new", reason="update")
    # as of APRIL: the 3500 was current (asserted, not yet superseded then)
    april = {f.id for f, *_ in recall_as_of(sm, "Johnson income", when=mar + 30 * _DAY, k=5)}
    assert april == {"f-old"}, f"April view must be the OLD truth, got {april}"
    # as of AFTER the supersede: only the current 5000 (fresh `when`, since the
    # supersede stamp is a few seconds after the test's `now` was captured)
    today = {f.id for f, *_ in recall_as_of(sm, "Johnson income",
                                            when=time.time() + 60, k=5)}
    assert today == {"f-new"}
    # BEFORE anything was asserted: empty
    feb = recall_as_of(sm, "Johnson income", when=mar - 30 * _DAY, k=5)
    assert feb == []


def test_recall_as_of_died_axis_is_event_time(tmp_path) -> None:
    """Review 5-lenti C2: batch-ingested history (asserted_at in the past, the
    supersede executed TODAY) — superseded_at is transaction time, so filtering
    'died' on it makes every version look still-current at any past `when`.
    The event-time death of a fact is its successor's asserted_at."""
    from engram.temporal_context import recall_as_of
    now = time.time()
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(id="roma", topic="user/home",
                  proposition="User lives in Rome",
                  asserted_at=now - 900 * _DAY), embed="sync")
    sm.store(Fact(id="milano", topic="user/home",
                  proposition="User lives in Milan",
                  asserted_at=now - 750 * _DAY), embed="sync")
    sm.supersede("roma", "milano", reason="moved")  # superseded_at = today
    ids = {f.id for f, *_ in recall_as_of(
        sm, "where does the user live", when=now - 560 * _DAY, k=5)}
    assert ids == {"milano"}, \
        "at `when` Rome was already replaced in EVENT time; only Milan was current"
    ids_before = {f.id for f, *_ in recall_as_of(
        sm, "where does the user live", when=now - 800 * _DAY, k=5)}
    assert ids_before == {"roma"}, "before the move only Rome existed"


def test_deep_recall_is_read_only_no_freshness_bump(tmp_path) -> None:
    """Review 5-lenti C3: deep/as-of recall is archaeology — a READ of the past
    must not write last_verified_at=now, or a single time-travel query
    resurrects dormant facts into every subsequent DEFAULT recall (and a
    default recall right after deep would show a different world than before,
    with no write in between)."""
    sm, _ = _seed_dormant(tmp_path)
    assert all(f.id != "m3" for f, *_ in sm.recall("Rossi budget", k=5)), \
        "sanity: dormant fact hidden from default recall"
    got_deep = {f.id for f, *_ in sm.recall("Rossi budget", k=5, deep=True)}
    assert "m3" in got_deep, "sanity: deep surfaces it (the feature)"
    assert all(f.id != "m3" for f, *_ in sm.recall("Rossi budget", k=5)), \
        "deep read must NOT refresh the fact into the live default view"
    lv = sm.get("m3").last_verified_at
    assert lv is not None and time.time() - lv > 80 * _DAY, \
        "last_verified_at untouched by the deep read"
