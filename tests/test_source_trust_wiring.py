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

from verimem.client import Memory

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


def test_independence_flag_off_copies_still_confirm(tmp_path, monkeypatch):
    """Backward-compat: without ENGRAM_SOURCE_INDEPENDENCE, distinct IDs confirm
    even if their report vectors are identical (the pre-existing behaviour)."""
    monkeypatch.delenv("ENGRAM_SOURCE_INDEPENDENCE", raising=False)
    mem = Memory(tmp_path / "m.db")
    reports = {s: {"k1": "A", "k2": "B", "k3": "C"} for s in ("c1", "c2", "c3")}
    mem.source_trust_observe(confirmation=["c1", "c2", "c3"], reports=reports)
    assert mem.consistency_trust("c1") > 0.5


def test_independence_flag_on_copies_cannot_self_confirm(tmp_path, monkeypatch):
    """The product hole closed: 3 copies of one feed (identical report vectors)
    collapse to ONE witness and do NOT self-confirm; two genuinely independent
    sources (differing vectors) still do."""
    monkeypatch.setenv("ENGRAM_SOURCE_INDEPENDENCE", "1")
    mem = Memory(tmp_path / "m.db")
    copies = {s: {"k1": "A", "k2": "B", "k3": "C"} for s in ("c1", "c2", "c3")}
    mem.source_trust_observe(confirmation=["c1", "c2", "c3"], reports=copies)
    assert mem.consistency_trust("c1") == 0.5   # manufactured consensus blocked

    indep = {"x": {"k1": "A", "k2": "B", "k3": "C"},
             "y": {"k1": "A", "k2": "Q", "k3": "R"}}   # agree on k1 only
    mem.source_trust_observe(confirmation=["x", "y"], reports=indep)
    assert mem.consistency_trust("x") > 0.5     # real corroboration still rises


def test_deconfound_flag_honest_agreement_still_confirms(tmp_path, monkeypatch):
    """P88 end-to-end: two honest sources agreeing on TRUE values are NOT false-merged
    (raw agreement would have blocked them) — the caveat fixed on the live path."""
    monkeypatch.setenv("ENGRAM_SOURCE_INDEPENDENCE", "1")
    monkeypatch.setenv("ENGRAM_SOURCE_INDEPENDENCE_DECONFOUND", "1")
    mem = Memory(tmp_path / "m.db")
    truth = {s: {"k1": "T1", "k2": "T2", "k3": "T3"} for s in ("h_a", "h_b")}
    mem.source_trust_observe(confirmation=["h_a", "h_b"], reports=truth)
    assert mem.consistency_trust("h_a") > 0.5


def test_deconfound_flag_blocks_colluders_who_admit_falsehoods(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_INDEPENDENCE", "1")
    monkeypatch.setenv("ENGRAM_SOURCE_INDEPENDENCE_DECONFOUND", "1")
    mem = Memory(tmp_path / "m.db")
    for k, v in {"k1": "F1", "k2": "F2"}.items():        # the audit reveals them false
        mem.source_trust_observe(audited_false=(k, v))
    lie = {s: {"k1": "F1", "k2": "F2"} for s in ("c_a", "c_b")}
    mem.source_trust_observe(confirmation=["c_a", "c_b"], reports=lie)
    assert mem.consistency_trust("c_a") == 0.5           # co-admitted falsehood -> blocked
