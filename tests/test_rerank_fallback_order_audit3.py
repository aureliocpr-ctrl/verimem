"""Found by a sister-CLI during independent review (2026-06-09):
cross_encoder_rerank.rerank_candidates documents "Graceful fallback: preserve
input order" on scorer failure, but the code sets all scores to 0.0 and then
sorts by ``(-score, fact_id)`` — so on a scorer error the candidates are
re-ordered by fact_id, NOT left in the first-stage (bi-encoder) order. A failing
reranker would therefore SCRAMBLE good retrieval results instead of degrading
gracefully to them. Fix: stable tiebreak on the original input index.
"""
from __future__ import annotations

from verimem.cross_encoder_rerank import rerank_candidates
from verimem.semantic import Fact, SemanticMemory


def test_scorer_error_preserves_input_order(tmp_path):
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    # Explicit ids whose lexical order differs from the input order below.
    sm.store(Fact(id="c3", proposition="gamma proposition", topic="t",
                  source_episodes=["e"]), embed="defer")
    sm.store(Fact(id="a1", proposition="alpha proposition", topic="t",
                  source_episodes=["e"]), embed="defer")
    sm.store(Fact(id="b2", proposition="beta proposition", topic="t",
                  source_episodes=["e"]), embed="defer")

    # First-stage (bi-encoder) order — deliberately NOT id-sorted.
    candidates = ["c3", "a1", "b2"]

    def boom(_pairs):
        raise RuntimeError("reranker model unavailable")

    out = rerank_candidates(
        "query", candidates, semantic_db=db, scorer=boom, top_n=10
    )
    assert [fid for fid, _ in out] == candidates, (
        "on scorer error the fallback must PRESERVE the bi-encoder input order, "
        f"not re-sort by fact_id; got {[fid for fid, _ in out]}"
    )
