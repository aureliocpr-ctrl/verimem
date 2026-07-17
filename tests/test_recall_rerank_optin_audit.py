"""P0.3 (2026-06-09) + default-ON flip (2026-06-10): stage-2 CE rerank in recall().

Default ON since 2026-06-10: the top-``ENGRAM_RERANK_TOPN`` bi-encoder
candidates are re-ordered by a cross-encoder on every semantic recall.
Opt-out with ``ENGRAM_RECALL_RERANK=0`` (also: off/false/no) = byte-identical
bi-encoder ranking. The returned score stays the ORIGINAL cosine (downstream
thresholds untouched). On ANY reranker failure (model load OR scorer raise)
the bi-encoder order is preserved — never a crash, never the primitive's old
id-sort.

Evidence for the default flip (both paired McNemar, COPY of live corpus):
  HARD n=300 (scripts/bench_rerank_n300_fast.py): R@1 0.520->0.810, p<1e-5.
  FAIR n=120 paraphrases (scripts/bench_rerank_fair.py): R@1 0.533->0.683
  p=0.00052, R@10 0.750->0.817 p=0.013 — survives the regime that refuted
  recall_hybrid. Cost: ~1.6s/probe CPU (mmarco-mMiniLMv2-L12 pool=20).

THIS file guards the WIRING only. Baselines inside each test pin the flag
explicitly ("0") so no assertion ever depends on the ambient default —
only the two default_* tests exercise the unset-env behaviour.

The injected scorers below monkeypatch ``verimem.semantic._load_reranker`` —
no real CrossEncoder model is ever loaded in tests.
"""
from __future__ import annotations

import math

import pytest

import verimem.semantic as semantic_mod
from verimem.semantic import Fact, SemanticMemory

_QUERY = "blue-green deployment on aws"


def _seed(sm: SemanticMemory, topic: str | None = None) -> None:
    props = [
        "the deployment uses blue-green rollout on aws",
        "carbonara needs guanciale eggs pecorino black pepper",
        "sqlite backup integrity is verified with pragma integrity_check",
        "the recall path ranks facts by cosine over embeddings",
        "skills are consolidated during the dream rem stage",
    ]
    for i, p in enumerate(props):
        sm.store(
            Fact(proposition=p, topic=topic or f"t/{i}", source_episodes=["e"]),
            embed="sync",
        )


def _ids(res: list[tuple]) -> list[str]:
    return [f.id for f, _ in res]


def _reversing_loader():
    """Fake CE loader: later pair index -> higher score, so the reranked
    order is exactly the REVERSE of the bi-encoder pool order."""
    return lambda pairs: [float(i) for i in range(len(pairs))]


# ── 0. Flag semantics: default ON, explicit opt-out values OFF ───────────────

@pytest.mark.parametrize("val", ["0", "off", "OFF", "false", " no "])
def test_rerank_flag_explicit_optout_values_are_off(monkeypatch, val):
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", val)
    assert semantic_mod._rerank_enabled() is False


@pytest.mark.parametrize("val", [None, "", "1", "on", "true", "yes"])
def test_rerank_flag_default_and_legacy_on_values_are_on(monkeypatch, val):
    if val is None:
        monkeypatch.delenv("ENGRAM_RECALL_RERANK", raising=False)
    else:
        monkeypatch.setenv("ENGRAM_RECALL_RERANK", val)
    assert semantic_mod._rerank_enabled() is True


# ── 1a. DEFAULT (no env): rerank applied — the 2026-06-10 flip ──────────────

def test_rerank_default_on_reorders_without_flag(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base_ids = _ids(sm.recall(_QUERY, k=5))
    assert len(base_ids) >= 3, "need a multi-candidate pool"

    monkeypatch.setattr(
        semantic_mod, "_load_reranker", _reversing_loader, raising=False,
    )
    monkeypatch.delenv("ENGRAM_RECALL_RERANK", raising=False)
    res = sm.recall(_QUERY, k=5)
    assert _ids(res) == list(reversed(base_ids)), (
        "with NO flag set the cross-encoder must be applied (default ON)"
    )


# ── 1b. Explicit OFF: order unchanged, reranker never touched ────────────────

def test_rerank_explicit_off_order_unchanged_and_loader_untouched(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    calls = {"n": 0}

    def _sentinel():
        calls["n"] += 1
        raise AssertionError("reranker loader must not be touched when OFF")

    monkeypatch.setattr(semantic_mod, "_load_reranker", _sentinel, raising=False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    res = sm.recall(_QUERY, k=5)
    assert res, "explicit-OFF recall must return results"
    assert all(math.isfinite(s) for _, s in res)
    scores = [s for _, s in res]
    assert scores == sorted(scores, reverse=True), (
        "OFF must keep the pure descending-cosine bi-encoder order"
    )
    assert calls["n"] == 0, "loader called with flag OFF"


# ── 2. ON: injected scorer's order is reflected (rerank really applied) ─────

def test_rerank_on_reorders_with_injected_scorer(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base = sm.recall(_QUERY, k=5)
    base_ids = _ids(base)
    base_score = {f.id: s for f, s in base}
    assert len(base_ids) >= 3, "need a multi-candidate pool"

    monkeypatch.setattr(
        semantic_mod, "_load_reranker", _reversing_loader, raising=False,
    )
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "on")
    res = sm.recall(_QUERY, k=5)
    assert _ids(res) == list(reversed(base_ids)), (
        "flag ON must reflect the injected cross-encoder order"
    )
    # Requirement: the score stays the ORIGINAL cosine, not the CE score.
    for f, s in res:
        assert s == pytest.approx(base_score[f.id]), (
            "hit score must remain the bi-encoder cosine after rerank"
        )


# ── 3a. Fallback: scorer raises -> bi-encoder order (no crash, no id-sort) ──

def test_rerank_scorer_raise_falls_back_to_biencoder_order(
    tmp_path, monkeypatch,
):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base_ids = _ids(sm.recall(_QUERY, k=5))
    calls = {"n": 0}

    def _loader():
        def _boom(pairs):
            calls["n"] += 1
            raise RuntimeError("scorer boom")
        return _boom

    monkeypatch.setattr(semantic_mod, "_load_reranker", _loader, raising=False)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "on")
    res = sm.recall(_QUERY, k=5)
    assert _ids(res) == base_ids, (
        "scorer failure must preserve bi-encoder order (not crash/id-sort)"
    )
    assert calls["n"] == 1, "rerank must have been ATTEMPTED (else vacuous)"


# ── 3b. Fallback: model LOAD raises -> bi-encoder order (no crash) ──────────

def test_rerank_loader_raise_falls_back_to_biencoder_order(
    tmp_path, monkeypatch,
):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base_ids = _ids(sm.recall(_QUERY, k=5))
    calls = {"n": 0}

    def _loader():
        calls["n"] += 1
        raise RuntimeError("model not in HF cache (offline)")

    monkeypatch.setattr(semantic_mod, "_load_reranker", _loader, raising=False)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "on")
    res = sm.recall(_QUERY, k=5)
    assert _ids(res) == base_ids, (
        "loader failure must preserve bi-encoder order (not crash)"
    )
    assert calls["n"] == 1, "loader must have been ATTEMPTED (else vacuous)"


# ── 4. Legacy SQL path (topic filter): same wiring ───────────────────────────

def test_rerank_on_legacy_topic_path_reorders(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm, topic="same/topic")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    base_ids = _ids(sm.recall(_QUERY, k=5, topic="same/topic"))
    assert len(base_ids) >= 3, "need a multi-candidate pool on the SQL path"

    monkeypatch.setattr(
        semantic_mod, "_load_reranker", _reversing_loader, raising=False,
    )
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "on")
    res = sm.recall(_QUERY, k=5, topic="same/topic")
    assert _ids(res) == list(reversed(base_ids)), (
        "legacy/topic path must apply the same rerank wiring"
    )
