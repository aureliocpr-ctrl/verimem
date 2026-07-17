"""Correction-velocity SEMANTIC relevance (2026-06-13).

Token-overlap relevance misses paraphrased tasks: Aurelio's episodes are unique
narratives ("resolve the vector store cold-load hang") that don't share 4 tokens
with how he phrases the next attempt ("fix the embedding recall blocking bug"),
even though they are the SAME work. Validated on the real corpus: 25 semantic
clusters of >=3 episodes at cosine>=0.85 that the token signature missed.

detect_correction_pattern now accepts `relevant_ids` — the set of episode ids the
caller selected by MEANING (get_briefing supplies it via the bounded
memory.recall cosine). When given, correction is detected over those; when None,
it falls back to the token signature (kept pure for unit tests).
"""
from __future__ import annotations

import time
import types

from verimem.correction_velocity import detect_correction_pattern

_DAY = 86400.0


def _ep(task_text, *, outcome="success", age_days=1.0, now=None, id="e"):
    now = now or time.time()
    return types.SimpleNamespace(
        task_text=task_text, outcome=outcome,
        created_at=now - age_days * _DAY, id=id,
    )


def test_relevant_ids_finds_correction_token_overlap_would_miss():
    now = time.time()
    eps = [
        _ep("resolve the vector store cold-load hang", outcome="failure", age_days=5, now=now, id="f1"),
        _ep("resolve the vector store cold-load hang", outcome="success", age_days=2, now=now, id="s1"),
        _ep("write the unrelated quarterly finance report", outcome="failure", age_days=1, now=now, id="x1"),
    ]
    # Task phrased with DIFFERENT words (no 4-token overlap with the episodes);
    # the SEMANTIC selection (what memory.recall returns) picks f1+s1, not x1.
    out = detect_correction_pattern(
        "fix the embedding recall blocking issue", eps, now=now, relevant_ids={"f1", "s1"},
    )
    assert out["has_correction"] is True, "semantic relevance must find the paraphrased correction"
    assert out["success"]["id"] == "s1"
    assert out["failures_before_success"] == 1
    assert all(f["id"] != "x1" for f in out["recent_failures"]), "non-relevant failure must not leak"


def test_token_path_would_have_missed_it():
    # Same data, but WITHOUT relevant_ids -> token fallback -> no overlap -> nothing.
    now = time.time()
    eps = [
        _ep("resolve the vector store cold-load hang", outcome="failure", age_days=5, now=now, id="f1"),
        _ep("resolve the vector store cold-load hang", outcome="success", age_days=2, now=now, id="s1"),
    ]
    out = detect_correction_pattern("fix the embedding recall blocking issue", eps, now=now)
    assert out["has_correction"] is False, "token overlap can't connect different words (the gap we fix)"


def test_empty_relevant_ids_means_no_correction():
    now = time.time()
    eps = [_ep("a", outcome="failure", age_days=3, now=now, id="f"),
           _ep("a", outcome="success", age_days=1, now=now, id="s")]
    out = detect_correction_pattern("anything", eps, now=now, relevant_ids=set())
    assert out["has_correction"] is False


def test_none_relevant_ids_preserves_token_behaviour():
    now = time.time()
    eps = [_ep("fix embedding recall bug model", outcome="failure", age_days=4, now=now, id="f"),
           _ep("fix embedding recall bug model", outcome="success", age_days=2, now=now, id="s")]
    out = detect_correction_pattern(
        "fix the embedding recall bug in the model", eps, now=now, relevant_ids=None,
    )
    assert out["has_correction"] is True
    assert out["failures_before_success"] == 1


# --- wiring: get_briefing supplies relevant_ids from memory.recall ------------

class _FakeMemWithRecall:
    def __init__(self, eps, recall_ids):
        self._eps = eps
        self._recall_ids = recall_ids

    def all(self, limit=None):
        return self._eps if limit is None else self._eps[:limit]

    def count(self):
        return len(self._eps)

    def recall(self, query, k=5, min_similarity=0.0, **kw):
        return [(e, 0.9) for e in self._eps
                if getattr(e, "id", None) in self._recall_ids][:k]


def test_get_briefing_correction_uses_semantic_recall():
    from verimem.briefing import get_briefing
    now = time.time()
    eps = [
        _ep("resolve the vector store cold-load hang", outcome="failure", age_days=5, now=now, id="f1"),
        _ep("resolve the vector store cold-load hang", outcome="success", age_days=2, now=now, id="s1"),
    ]
    agent = types.SimpleNamespace(
        memory=_FakeMemWithRecall(eps, {"f1", "s1"}), skills=None, semantic=None,
    )
    # Task worded differently from the episodes (token path would find nothing) —
    # semantic recall connects them, so the correction fires.
    out = get_briefing(agent=agent, task_text="fix the embedding recall blocking bug")
    assert out["correction"]["has_correction"] is True
    assert out["correction"]["success"]["id"] == "s1"


def test_get_briefing_correction_without_recall_falls_back_to_token():
    from verimem.briefing import get_briefing

    class _Mem:
        def __init__(self, eps): self._eps = eps
        def all(self, limit=None): return self._eps if limit is None else self._eps[:limit]
        def count(self): return len(self._eps)

    now = time.time()
    eps = [
        _ep("fix embedding recall bug model", outcome="failure", age_days=4, now=now, id="f"),
        _ep("fix embedding recall bug model", outcome="success", age_days=2, now=now, id="s"),
    ]
    agent = types.SimpleNamespace(memory=_Mem(eps), skills=None, semantic=None)
    out = get_briefing(agent=agent, task_text="fix the embedding recall bug in the model")
    assert out["correction"]["has_correction"] is True  # token fallback still works
