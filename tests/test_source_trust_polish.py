"""Source-trust polish (task #20 a+b) — TDD.

(a) dossier transparency: with the flag on, every fact in the explain()
    dossier carries its source's trust — the console/customer sees WHY a
    fact's writer is (dis)trusted, not just the fact's own status.
(b) production loop closure: a SUPERSESSION observed by reconcile-on-write
    feeds the outcome channel automatically — attenuated by the fact's age
    (stale_weight, #18b): an old fact being superseded is the world moving,
    a fresh one being superseded blames the source more. Contested facts
    feed NOTHING (ambiguous, punish no one — guard-rail prudence).
"""
from __future__ import annotations

import time

from engram.client import Memory

DAY = 86400.0


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


def test_supersession_feeds_attenuated_outcome(tmp_path, monkeypatch):
    """Unit + wiring: when store()'s reconcile supersedes an old fact, the
    old fact's SOURCE gets an outcome=False observation whose weight is
    attenuated by the fact's age (old fact → light blame)."""
    _fresh(monkeypatch)
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "1")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "1")
    monkeypatch.setenv("ENGRAM_RECONCILE_AUTO_SUPERSEDE", "1")
    mem = Memory(tmp_path / "m.db")
    now = time.time()
    r_old = mem.add("The access code of vault_9 is mm33nn.", topic="t",
                    verified_by=["source-doc:alice:t0"],
                    asserted_at=now - 14 * DAY)  # two half-lives old
    old_id = r_old["id"]

    # force the supersession outcome deterministically (the suite's embedding
    # stub cannot produce similarity candidates — judged on the real embedder
    # by the mini-world; here we test the OBSERVATION wiring)
    from engram import semantic as sem

    def _mock_reconcile(self, fact, **kw):
        self.supersede(old_id, fact.id, reason="test")
        return {"superseded": [old_id], "contested": []}

    monkeypatch.setattr(sem.SemanticMemory, "reconcile_new_fact",
                        _mock_reconcile)
    mem.add("The access code of vault_9 is pp55qq.", topic="t",
            verified_by=["source-doc:bob:t1"])

    book = mem._source_trust_book()
    led = book._sources.get("alice")
    assert led is not None and led.bad > 0, "alice must carry outcome blame"
    assert led.bad < 0.5, (
        "a 14-day-old fact (2 half-lives, default 7d) must blame lightly "
        f"— got {led.bad}")
    assert "bob" not in book._sources or book._sources["bob"].bad == 0
