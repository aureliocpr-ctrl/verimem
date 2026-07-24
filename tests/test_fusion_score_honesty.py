"""An extra-only fusion hit must not report similarity 0.0 it never measured.

Found by dogfooding 2026-07-25 on the real store: a recall returns
`(Fact, 0.0)` rows interleaved with `(Fact, 0.85)` ones. The 0.0 is a
PLACEHOLDER — `fuse_dense_and_ppr` adds graph/lexical-only candidates with
`sim=0.0` expecting the CE-rerank downstream to re-score them. When that
re-scoring does not happen (CE over budget, CE disabled, or the candidate sits
past the reranked head), the placeholder reaches the caller, who cannot tell
"not measured" from "measured zero". Isolated by A/B: with the fusion off the
zero-scores vanish entirely (0/40 vs 7/40 on 8 real queries).

Same class as the pin `unresolved` marker shipped earlier tonight: absence
must never be rendered as a value. Here the honest fix is cheaper than a
marker — the similarity is COMPUTABLE. The query vector is already in hand and
the fact carries its embedding, so an extra-only candidate can be scored for
real instead of guessed at.

Back-compat: without a scorer the behaviour is byte-identical (0.0), because
callers that never had one must not change.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from verimem.ppr_seed import fuse_dense_and_ppr


@dataclass
class _F:
    id: str
    proposition: str = ""
    embedding: list[float] = field(default_factory=list)


DENSE = [(_F("d1", embedding=[1.0, 0.0]), 0.91),
         (_F("d2", embedding=[0.9, 0.1]), 0.80)]
EXTRA = {"x1": _F("x1", embedding=[0.6, 0.8]),
         "x2": _F("x2", embedding=[0.0, 1.0])}


def _fetch(fid: str):
    return EXTRA.get(fid)


def _cosine_scorer(query_vec):
    def _score(fact) -> float:
        v = getattr(fact, "embedding", None) or []
        if not v or len(v) != len(query_vec):
            return 0.0
        num = sum(a * b for a, b in zip(query_vec, v, strict=True))
        na = sum(a * a for a in query_vec) ** 0.5
        nb = sum(b * b for b in v) ** 0.5
        return num / (na * nb) if na and nb else 0.0
    return _score


def test_extra_only_hits_get_a_real_similarity():
    out = fuse_dense_and_ppr(DENSE, [["x1", "x2"]], _fetch,
                             score_extra=_cosine_scorer([1.0, 0.0]))
    scores = {f.id: s for f, s in out}
    assert scores["x1"] > 0.0, "graph/lexical hit still reported as zero"
    assert abs(scores["x1"] - 0.6) < 1e-6
    assert scores["x2"] == 0.0, "a genuinely orthogonal fact IS zero"


def test_dense_hits_keep_their_own_score():
    out = fuse_dense_and_ppr(DENSE, [["x1"]], _fetch,
                             score_extra=_cosine_scorer([1.0, 0.0]))
    scores = {f.id: s for f, s in out}
    assert scores["d1"] == 0.91 and scores["d2"] == 0.80


def test_without_a_scorer_nothing_changes():
    """Byte-identical for every existing caller — the parameter is opt-in."""
    out = fuse_dense_and_ppr(DENSE, [["x1", "x2"]], _fetch)
    scores = {f.id: s for f, s in out}
    assert scores["x1"] == 0.0 and scores["x2"] == 0.0


def test_a_failing_scorer_falls_back_to_the_placeholder():
    """Scoring is a receipt detail; it must never break a recall."""
    def _boom(_fact):
        raise RuntimeError("no embedding backend")

    out = fuse_dense_and_ppr(DENSE, [["x1"]], _fetch, score_extra=_boom)
    assert {f.id: s for f, s in out}["x1"] == 0.0


def test_protect_top_path_scores_too():
    """The dense-floor branch recurses — the scorer must survive the recursion,
    or the fix would silently apply only when protect_top is 0."""
    out = fuse_dense_and_ppr(DENSE, [["x1"]], _fetch, protect_top=1,
                             score_extra=_cosine_scorer([1.0, 0.0]))
    assert {f.id: s for f, s in out}["x1"] > 0.0
