"""The fusion must hand the pure function a WORKING scorer.

The unit tests cover `fuse_dense_and_ppr`; this covers the wiring, because
that is where the defect was born: `ppr_seed` still documents "the CE-rerank
downstream re-scores them", while the 2026-06-14 fix moved the fusion AFTER
the rerank — so nothing re-scores anything and the 0.0 placeholder is final.
A test on the pure function alone stays green through exactly that regression.

Deliberately NOT asserting "no returned score is 0.0": under the suite's
stub embedder (a hashing bag-of-tokens) two texts with no shared token have a
cosine that IS exactly 0.0, so such an assertion would confuse a legitimate
zero with a placeholder — the very distinction at issue.
"""
from __future__ import annotations

import pytest

from verimem.semantic import Fact, SemanticMemory

FACTS = [
    "The deploy pipeline retries a failed upload three times.",
    "Rate limiting returns HTTP 429 with a Retry-After header.",
    "The parser rejects malformed headers before validation.",
    "Backups run nightly at 03:00 UTC to the cold bucket.",
    "The scheduler skips a job whose previous run is still active.",
]


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "on")
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "0")   # tiny corpus on purpose
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")      # isolate the fusion
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    for i, p in enumerate(FACTS):
        sm.store(Fact(id=f"f{i}", proposition=p, topic="t"), embed="sync")
    return sm


def test_scorer_reproduces_the_dense_similarity(store):
    """The scorer's number must be the SAME quantity the dense path reports,
    or the fused list would mix two incomparable scales — which is the bug in
    a subtler costume."""
    query = "retry policy on failed upload"
    hits = store.recall(query, k=5)
    assert hits
    scorer = store._extra_similarity_scorer(query)
    for fact, dense_score in hits:
        assert scorer(fact) == pytest.approx(dense_score, abs=2e-3), (
            f"{fact.id}: scorer says {scorer(fact)}, dense path says {dense_score}")


def test_scorer_is_actually_handed_to_the_fusion(store, monkeypatch):
    """The wiring itself. Without this, the scorer could be perfect and never
    called — the failure mode this whole file exists for."""
    from verimem import ppr_seed

    seen: dict = {}
    real_fuse = ppr_seed.fuse_dense_and_ppr

    def _spy(*a, **kw):
        seen["score_extra"] = kw.get("score_extra")
        return real_fuse(*a, **kw)

    monkeypatch.setattr(ppr_seed, "fuse_dense_and_ppr", _spy)
    store.recall("retry policy on failed upload", k=5)
    assert "score_extra" in seen, "the fusion never ran — fixture problem"
    assert callable(seen["score_extra"]), "extra candidates would score 0.0 forever"


def test_scorer_never_raises_on_a_missing_fact(store):
    """A candidate whose row is gone must yield 0.0, not an exception: a score
    is a receipt detail and must never break a recall."""
    scorer = store._extra_similarity_scorer("anything")

    class _Ghost:
        id = "does-not-exist"

    assert scorer(_Ghost()) == 0.0
    assert scorer(object()) == 0.0        # no id at all
