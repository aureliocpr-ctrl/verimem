"""audit#3-r3 R19: recall_hybrid built its candidate pool via self.recall(query,
k=pool_k) with NO provenance filter and exposed no exclude_legacy / min_status
params — so legacy_unverified facts leaked into the re-ranked results and a
caller had no way to get clean hybrid recall (unlike recall + search_facts, which
both offer those filters). Fix: accept exclude_legacy / min_status and forward
them to the pool recall.
"""
from __future__ import annotations

from verimem.semantic import Fact, SemanticMemory


def test_recall_hybrid_forwards_provenance_filters(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    captured: dict = {}
    real_recall = sm.recall

    def spy(query, k=5, **kwargs):
        captured.update(kwargs)
        return real_recall(query, k=k, **kwargs)

    monkeypatch.setattr(sm, "recall", spy)
    # Pre-fix: recall_hybrid does not accept exclude_legacy -> TypeError (RED).
    sm.recall_hybrid("anything at all", k=5, exclude_legacy=True, min_status="model_claim")
    assert captured.get("exclude_legacy") is True, captured
    assert captured.get("min_status") == "model_claim", captured


def test_recall_hybrid_default_keeps_parity_with_recall(tmp_path, monkeypatch):
    """Default (no flags) must NOT silently exclude legacy — parity with recall,
    whose exclude_legacy defaults False — so existing callers are unaffected."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    captured: dict = {}
    real_recall = sm.recall

    def spy(query, k=5, **kwargs):
        captured.update(kwargs)
        return real_recall(query, k=k, **kwargs)

    monkeypatch.setattr(sm, "recall", spy)
    sm.recall_hybrid("anything", k=3)
    assert captured.get("exclude_legacy") in (False, None), captured
    assert captured.get("min_status") is None, captured
