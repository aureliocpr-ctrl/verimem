"""TDD — the minimal composition loop (ORGANISM plan -> product, 2026-07-13).

compose_once: from pairs of LIVE facts sharing a pivot term, derive a NEW
candidate by declared substitution (copula syllogism v1), push it through the
SAME anti-confab gate as every writer (L4 source⊢fact entailment against the
two parents — no privileges), and admit survivors SIGNED (actor:composer,
P85), TRACED (derives_from=[a,b], the P78 chain) and LABELED (epistemic proven
with the declared check ref). Few-but-zero-false: rejected candidates stay
quarantined by the gate, never silently admitted.
"""
from __future__ import annotations

import pytest

from verimem.composer import _copula_parse, compose_once


class _FakeJudge:
    """Deterministic L4 judge: entailed iff every content word of the fact
    appears in the source (enough to separate the test cases); score is fixed
    by the constructor otherwise."""

    def __init__(self, score_entailed: float = 90.0, score_not: float = 5.0):
        self.calls: list[tuple[str, str]] = []
        self.score_entailed = score_entailed
        self.score_not = score_not

    def complete(self, system, messages, **kw):
        content = messages[0]["content"]
        src = content.split("Source:", 1)[1].split("Candidate fact:", 1)[0].lower()
        fact = content.split("Candidate fact:", 1)[1].lower()
        words = [w for w in "".join(c if c.isalnum() else " " for c in fact).split()
                 if w not in ("a", "an", "the", "is", "score")]
        ok = all(w in src for w in words)

        class _R:  # noqa: N801 — tiny stub
            text = f"Score: {self.score_entailed if ok else self.score_not:.0f}"
        self.calls.append((src.strip(), fact.strip()))
        return _R()


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "claude")  # use injected judge
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from verimem.client import Memory
    return Memory(tmp_path / "compose.db", grounding_llm=_FakeJudge())


def test_copula_parse():
    assert _copula_parse("Rex is a labrador.") == ("rex", "labrador", "a labrador")
    assert _copula_parse("A labrador is a dog.") == ("a labrador", "dog", "a dog")
    assert _copula_parse("The Colosseum is in Rome.") is None   # not a copula NP
    assert _copula_parse("Run the tests.") is None
    assert _copula_parse("") is None


def test_syllogism_admitted_signed_traced_labeled(mem):
    a = mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    b = mem.add("A labrador is a dog.", topic="pets", verified_by=["source-doc:kb:t1"])
    rep = compose_once(mem, run_id="t1")
    assert rep["admitted"] == 1 and rep["rejected_gate"] == 0
    fid = rep["admitted_ids"][0]
    fact = mem.semantic.get(fid)
    assert fact.proposition == "Rex is a dog."
    assert set(fact.derives_from) == {a["id"], b["id"]}          # P78 trace
    assert any(r.startswith("actor:composer:") for r in fact.verified_by)  # P85
    assert fact.epistemic and fact.epistemic["kind"] == "proven"
    assert "l4_entail" in fact.epistemic["proof"]
    assert fact.status != "quarantined"


def test_unrelated_pair_yields_no_candidates(mem):
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    mem.add("Mercury is a planet.", topic="space", verified_by=["source-doc:kb:t1"])
    rep = compose_once(mem, run_id="t2")
    assert rep["candidates"] == 0 and rep["admitted"] == 0


def test_already_known_candidate_is_skipped(mem):
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    mem.add("A labrador is a dog.", topic="pets", verified_by=["source-doc:kb:t1"])
    mem.add("Rex is a dog.", topic="pets", verified_by=["source-doc:bob:t1"])
    rep = compose_once(mem, run_id="t3")
    assert rep["admitted"] == 0
    assert rep["skipped_known"] >= 1


def test_gate_rejects_unsupported_composition(tmp_path, monkeypatch):
    """A candidate the judge does NOT entail stays out of the live store —
    quarantined by the same gate that guards every writer (zero-false)."""
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "claude")
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from verimem.client import Memory
    m = Memory(tmp_path / "rej.db",
               grounding_llm=_FakeJudge(score_entailed=5.0, score_not=5.0))
    m.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    m.add("A labrador is a dog.", topic="pets", verified_by=["source-doc:kb:t1"])
    rep = compose_once(m, run_id="t4")
    assert rep["admitted"] == 0 and rep["rejected_gate"] == 1
    # the rejected candidate is not among LIVE facts
    live = [f.proposition for f in m.semantic.all()
            if f.status != "quarantined"]
    assert "Rex is a dog." not in live


def test_noncommittal_judge_never_admits(tmp_path, monkeypatch):
    """A broken/unreadable judge yields the gate's non-committal 50. That is
    below BOTH the composer's own floor (55) AND — since the moat recalibration
    2026-07-17 — the write threshold (70), so a DERIVED fact scored by a dead
    judge is never admitted: it is quarantined (by whichever gate catches it
    first). The safety invariant is 'a dead judge cannot flood the store with
    unverified compositions', asserted on the OUTCOME, not on which counter
    fires (the write gate now subsumes the composer floor for grounded facts)."""
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "claude")
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from verimem.client import Memory

    class _Garbage:
        def complete(self, system, messages, **kw):
            class _R:  # noqa: N801
                text = "I cannot help with that."
            return _R()

    m = Memory(tmp_path / "gj.db", grounding_llm=_Garbage())
    m.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    m.add("A labrador is a dog.", topic="pets", verified_by=["source-doc:kb:t1"])
    rep = compose_once(m, run_id="t6")
    assert rep["admitted"] == 0
    # rejected on the write path: the L4 write gate (rejected_gate, score 50 < 70)
    # OR the composer's own non-committal floor (rejected_noncommittal, < 55).
    # Post-recalibration the write gate catches it first; either way it is >=1.
    assert rep["rejected_gate"] + rep["rejected_noncommittal"] >= 1
    # the safety invariant (threshold-independent): the derived fact is NEVER live
    live = [f.proposition for f in m.semantic.all() if f.status != "quarantined"]
    assert "Rex is a dog." not in live


def test_composer_facts_cannot_selfconfirm_via_source_trust(mem):
    """P85 closure: even if a later observation pass sees composer-written
    facts, the actor source earns no consistency reputation."""
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    mem.add("A labrador is a dog.", topic="pets", verified_by=["source-doc:kb:t1"])
    compose_once(mem, run_id="t5")
    book = mem._source_trust_book()
    assert all(not s.startswith("actor:") for s in book.to_dict())


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
