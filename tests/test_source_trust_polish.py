"""Source-trust polish (task #20) — TDD.

(a) dossier transparency: with the flag on, every fact in the explain()
    dossier carries its source's trust — the console/customer sees WHY a
    fact's writer is (dis)trusted, not just the fact's own status.
(c) rehabilitation: a source demoted below the floor records the exact facts
    it demoted; when it recovers ABOVE the floor those return — never an
    L1/L4 quarantine (content, not source).

NOTE — task #20b (automatic supersession → outcome penalty) was REVERTED:
feeding temporal supersessions into the outcome channel is an attribution
error (law L3). Under churn an honest source's fact is superseded by newer
truth constantly — the world moving, not the source lying — which sank
honest sources (mini-world stale 0.10 → 1.00). Caught by the mini-world
regression. The outcome channel needs an INDEPENDENT-VERIFICATION signal,
not a temporal one.
"""
from __future__ import annotations

from engram.client import Memory


def _fresh(monkeypatch):
    from engram import source_trust
    source_trust.reset_book_cache()


def test_explain_exposes_source_trust_when_enabled(tmp_path, monkeypatch):
    _fresh(monkeypatch)
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "1")
    mem = Memory(tmp_path / "m.db")
    mem.source_trust_observe(confirmation=["acme-registry", "other-src"])
    mem.add("The office code of building_7 is kk11aa.", topic="t",
            verified_by=["source-doc:acme-registry:r1"])
    report = mem.explain("What is the office code of building_7?", k=3)
    entries = report.get("facts") or []
    assert entries, "the fact must be retrievable"
    st = entries[0].get("source_trust")
    assert st and st["source"] == "acme-registry"
    assert st["trust"] > 0.5


def test_explain_no_source_trust_when_disabled(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_SOURCE_TRUST", raising=False)
    mem = Memory(tmp_path / "m.db")
    mem.add("The office code of building_7 is kk11aa.", topic="t",
            verified_by=["source-doc:acme-registry:r1"])
    report = mem.explain("What is the office code of building_7?", k=3)
    entries = report.get("facts") or []
    assert entries and "source_trust" not in entries[0]


def test_retro_demoted_facts_rehabilitate_when_source_recovers(tmp_path, monkeypatch):
    """A source demoted below the floor sinks its facts (retro-demote); when
    independent confirmations lift it back ABOVE the floor, ONLY the facts it
    demoted for source-trust return — never a fact L1/L4 quarantined for its
    own content."""
    _fresh(monkeypatch)
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "1")
    mem = Memory(tmp_path / "m.db")
    r_ok = mem.add("The shelf code of aisle_3 is qq88rr.", topic="t",
                   verified_by=["source-doc:flip:t0"])
    # an L1-quarantined fact from the SAME source (unsupported self-claim)
    r_l1 = mem.add("the migration works perfectly and is fully tested",
                   topic="t", verified_by=["source-doc:flip:t1"])
    assert mem.semantic.get(r_l1["id"]).status == "quarantined"

    for _ in range(8):
        mem.source_trust_observe(contradiction="flip")   # sink → retro-demote
    assert mem.semantic.get(r_ok["id"]).status == "quarantined"

    for _ in range(30):
        mem.source_trust_observe(confirmation=["flip", "witness"])  # recover
    assert mem.source_trust("flip") > 0.25
    assert mem.semantic.get(r_ok["id"]).status != "quarantined", (
        "source-trust demotion must reverse when the source recovers")
    assert mem.semantic.get(r_l1["id"]).status == "quarantined", (
        "an L1-quarantined fact must NEVER be rehabilitated by source trust")
