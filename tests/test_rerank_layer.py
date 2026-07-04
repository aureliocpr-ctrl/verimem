"""TDD del layer rerank opzionale (engram/rerank.py).

Verifica la LOGICA di wiring con uno scorer iniettato (niente download del
cross-encoder reale; quello e' gia' validato da scripts/bench_rerank.py):
  - rerank_hits riordina per punteggio scorer e taglia a top_k
  - fallback A2: scorer che solleva / lunghezza incoerente -> hits invariati
  - recall_reranked: retrieve dense (gate+v9 reali) -> rerank -> top_k
  - rerank_enabled legge l'env HIPPO_RERANK (default OFF)
Hermetic: SemanticMemory su DB temporaneo, zero scrittura live.
"""
from __future__ import annotations

from engram.rerank import recall_reranked, rerank_enabled, rerank_hits
from engram.semantic import Fact, SemanticMemory


def _favor(marker: str):
    """Scorer stub: punteggio alto se il doc contiene il marker."""
    def score(pairs):
        return [10.0 if marker in doc else 0.0 for _q, doc in pairs]
    return score


def test_rerank_hits_reorders_and_truncates():
    hits = [(Fact(id="a", proposition="alpha"), 0.9),
            (Fact(id="b", proposition="beta ZORP"), 0.5),
            (Fact(id="c", proposition="gamma"), 0.1)]
    out = rerank_hits("q", hits, top_k=2, scorer=_favor("ZORP"))
    assert [h[0].id for h in out] == ["b", "a"]  # b sale (marker), poi a; c tagliato


def test_rerank_hits_fallback_on_scorer_error_returns_unchanged():
    hits = [(Fact(id="a", proposition="x"), 0.9), (Fact(id="b", proposition="y"), 0.8)]

    def boom(_pairs):
        raise RuntimeError("reranker giu'")

    out = rerank_hits("q", hits, top_k=2, scorer=boom)
    assert [h[0].id for h in out] == ["a", "b"]  # invariato: reranker best-effort


def test_rerank_hits_fallback_on_length_mismatch():
    hits = [(Fact(id="a", proposition="x"), 0.9), (Fact(id="b", proposition="y"), 0.8)]
    out = rerank_hits("q", hits, top_k=2, scorer=lambda pairs: [1.0])  # len 1 != 2
    assert [h[0].id for h in out] == ["a", "b"]


def test_rerank_hits_empty():
    assert rerank_hits("q", [], top_k=5, scorer=_favor("z")) == []


def test_recall_reranked_end_to_end(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(id="a", proposition="alpha procedura banale", topic="t"))
    sm.store(Fact(id="b", proposition="beta procedura con ZORP dentro", topic="t"))
    sm.store(Fact(id="c", proposition="gamma procedura banale", topic="t"))
    # recall dense ritorna i 3 (pool=10); il rerank stub favorisce 'b'
    out = recall_reranked(sm, "procedura", k=1, pool=10, scorer=_favor("ZORP"))
    assert out and out[0][0].id == "b"


def test_rerank_enabled_reads_env(monkeypatch):
    monkeypatch.delenv("HIPPO_RERANK", raising=False)
    assert rerank_enabled() is False
    monkeypatch.setenv("HIPPO_RERANK", "1")
    assert rerank_enabled() is True
    monkeypatch.setenv("HIPPO_RERANK", "off")
    assert rerank_enabled() is False
