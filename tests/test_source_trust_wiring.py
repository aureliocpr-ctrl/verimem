"""Source-trust wiring in the write-gate (task #17 step 2) — TDD.

Contract: behind ENGRAM_SOURCE_TRUST=1, default OFF.
  * OFF → byte-identical behaviour, the book is never consulted;
  * ON → a source whose PERSISTED trust is below threshold gets its write
    quarantined with an explicit SOURCE_TRUST warning (transparency: the
    dossier shows status + the add() response says why);
  * unknown sources (neutral prior) are untouched — the gate must never
    punish a source it knows nothing about;
  * the book persists in the store's own SQLite (a new client on the same
    path remembers reputations).
Observations reach the book via an explicit API in this step; automatic
reconciliation hooks arrive with the mini-world reproduction.
"""
from __future__ import annotations

from engram.client import Memory

BAD_REF = ["source-doc:shady-vendor:7"]
GOOD_TEXT = "The quarterly report was filed on May 3rd."


def _sink_source(mem: Memory, source: str, n: int = 8) -> None:
    for _ in range(n):
        mem.source_trust_observe(contradiction=source)


def test_flag_off_book_never_consulted(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_SOURCE_TRUST", raising=False)
    mem = Memory(tmp_path / "m.db")
    _sink_source(mem, "shady-vendor")
    res = mem.add(GOOD_TEXT, topic="wire", verified_by=BAD_REF)
    assert res["status"] != "quarantined", "flag OFF must change nothing"
    assert not any(w.get("layer") == "SOURCE_TRUST"
                   for w in res.get("warnings", []))


def test_flag_on_sunk_source_is_quarantined_with_warning(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "1")
    mem = Memory(tmp_path / "m.db")
    _sink_source(mem, "shady-vendor")
    assert mem.source_trust("shady-vendor") < 0.25
    res = mem.add(GOOD_TEXT, topic="wire", verified_by=BAD_REF)
    assert res["status"] == "quarantined"
    assert any(w.get("layer") == "SOURCE_TRUST"
               for w in res.get("warnings", []))


def test_flag_on_unknown_source_untouched(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "1")
    mem = Memory(tmp_path / "m.db")
    res = mem.add(GOOD_TEXT, topic="wire",
                  verified_by=["source-doc:never-seen:1"])
    assert res["status"] != "quarantined", (
        "neutral prior (0.5) must clear the 0.25 threshold")


def test_book_persists_across_clients(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "1")
    mem1 = Memory(tmp_path / "m.db")
    _sink_source(mem1, "shady-vendor")
    sunk = mem1.source_trust("shady-vendor")
    mem2 = Memory(tmp_path / "m.db")  # fresh client, same store
    assert mem2.source_trust("shady-vendor") == sunk


def test_retro_demotion_on_threshold_crossing(tmp_path, monkeypatch):
    """Judge finding (seeds 12-13): a liar's EARLY writes stay admitted
    because reputation crosses the floor only after ~3 contradictions. On
    the crossing, the source's already-admitted facts must be re-evaluated:
    quarantined (rehabilitable — never deleted), clean sources untouched."""
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "1")
    mem = Memory(tmp_path / "m.db")
    r1 = mem.add("The code of alpha is aaa111.", topic="t",
                 verified_by=["source-doc:sinker:t0"])
    r2 = mem.add("The code of beta is bbb222.", topic="t",
                 verified_by=["source-doc:sinker:t1"])
    r3 = mem.add("The code of gamma is ccc333.", topic="t",
                 verified_by=["source-doc:clean:t0"])
    assert all(r["status"] != "quarantined" for r in (r1, r2, r3))
    _sink_source(mem, "sinker")   # crossing below the floor
    assert mem.get(r1["id"])["status"] == "quarantined"
    assert mem.get(r2["id"])["status"] == "quarantined"
    assert mem.get(r3["id"])["status"] != "quarantined", (
        "a clean source's facts must never be touched")


def test_retro_demotion_inert_when_flag_off(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_SOURCE_TRUST", raising=False)
    mem = Memory(tmp_path / "m.db")
    r1 = mem.add("The code of alpha is aaa111.", topic="t",
                 verified_by=["source-doc:sinker:t0"])
    _sink_source(mem, "sinker")
    assert mem.get(r1["id"])["status"] != "quarantined"


def test_confirmation_api_reaches_persisted_book(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "1")
    mem = Memory(tmp_path / "m.db")
    mem.source_trust_observe(confirmation=["alice", "bob"])
    assert mem.source_trust("alice") > 0.5
    mem.source_trust_observe(outcome=("alice", False, 0.25))  # stale-attenuated
    assert mem.source_trust("alice") < mem.consistency_trust("alice")
