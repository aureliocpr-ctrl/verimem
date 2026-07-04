"""Length guard on the stage-2 CE rerank (comparative bench finding 2026-06-10).

LongMemEval n=100: rerank ON scored recall@5 0.723 vs 0.800 base — the
mmarco CE truncates inputs at 512 tokens, so on LONG documents (session
transcripts) it judges only the head and SCRAMBLES an already-good
bi-encoder ranking. On the real corpus (short facts) the CE is validated
twice (HARD n=300, FAIR n=120). Principled rule: never let the CE rank
what it cannot read — skip stage-2 when the pool's median document length
exceeds the CE's effective window.

Env: ENGRAM_RERANK_MAX_DOC_CHARS (default 2000 ~= 512 tokens; 0 = guard off).
"""
from __future__ import annotations

import engram.semantic as semantic_mod
from engram.semantic import Fact, SemanticMemory

_QUERY = "blue-green deployment on aws"

_LONG_PAD = (
    " The deployment pipeline then proceeds through staging validation,"
    " canary analysis, traffic shifting, rollback rehearsal and a final"
    " compliance checkpoint before completion." * 20
)  # ~2.9k chars of filler -> median length far beyond the CE window


def _seed(sm: SemanticMemory, *, long_docs: bool) -> None:
    props = [
        "the deployment uses blue-green rollout on aws",
        "carbonara needs guanciale eggs pecorino black pepper",
        "sqlite backup integrity is verified with pragma integrity_check",
        "the recall path ranks facts by cosine over embeddings",
        "skills are consolidated during the dream rem stage",
    ]
    for i, p in enumerate(props):
        text = p + (_LONG_PAD if long_docs else "")
        sm.store(Fact(proposition=text, topic=f"t/{i}",
                      source_episodes=["e"]), embed="sync")


def _ids(res: list[tuple]) -> list[str]:
    return [f.id for f, _ in res]


def _reversing_loader():
    return lambda pairs: [float(i) for i in range(len(pairs))]


def test_long_docs_skip_rerank_and_never_load_ce(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm, long_docs=True)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base_ids = _ids(sm.recall(_QUERY, k=5))

    # NON-VACUOUS: count loader calls. A bare order==base check would pass
    # even WITHOUT the guard, because _rerank_stage2 catches the loader
    # error and falls back to bi-encoder order anyway. The guard's contract
    # is that the CE is NEVER LOADED for long docs (no wasted ~1.6s/q).
    calls = {"n": 0}

    def _counting_loader():
        calls["n"] += 1
        return lambda pairs: [float(i) for i in range(len(pairs))]

    monkeypatch.setattr(semantic_mod, "_load_reranker", _counting_loader,
                        raising=False)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    res = sm.recall(_QUERY, k=5)
    assert calls["n"] == 0, (
        "median doc length >> CE window: loader must NEVER be called"
    )
    assert _ids(res) == base_ids, "long-doc recall must keep bi-encoder order"


def test_short_docs_still_rerank(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm, long_docs=False)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base_ids = _ids(sm.recall(_QUERY, k=5))

    monkeypatch.setattr(semantic_mod, "_load_reranker", _reversing_loader,
                        raising=False)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    res = sm.recall(_QUERY, k=5)
    assert _ids(res) == list(reversed(base_ids)), (
        "short facts (the validated domain) must still go through the CE"
    )


def test_guard_disabled_with_zero(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm, long_docs=True)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base_ids = _ids(sm.recall(_QUERY, k=5))

    monkeypatch.setattr(semantic_mod, "_load_reranker", _reversing_loader,
                        raising=False)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    monkeypatch.setenv("ENGRAM_RERANK_MAX_DOC_CHARS", "0")
    res = sm.recall(_QUERY, k=5)
    assert _ids(res) == list(reversed(base_ids)), (
        "MAX_DOC_CHARS=0 must disable the guard (CE forced even on long docs)"
    )


def test_guard_threshold_env_tunable(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm, long_docs=False)  # short docs
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base_ids = _ids(sm.recall(_QUERY, k=5))
    calls = {"n": 0}

    def _counting_loader():
        calls["n"] += 1
        return lambda pairs: [float(i) for i in range(len(pairs))]

    monkeypatch.setattr(semantic_mod, "_load_reranker", _counting_loader,
                        raising=False)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    monkeypatch.setenv("ENGRAM_RERANK_MAX_DOC_CHARS", "10")
    res = sm.recall(_QUERY, k=5)
    assert calls["n"] == 0, "tiny threshold must skip the CE even on short docs"
    assert _ids(res) == base_ids
