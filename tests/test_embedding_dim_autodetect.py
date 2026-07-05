"""Auto-dim detection (iter 31) — kills the silent-empty-recall trap.

Found the hard way (2026-07-05 embedder sweep): a custom HIPPO_EMBEDDING_MODEL
outside the known-dim table, with HIPPO_EMBEDDING_DIM unset, got the assumed
768 while the model emits 1024-d vectors -> every stored vector fails the
recall length-filter -> recall silently EMPTY (n_hits=0 on all 726 probes).

Fix: config marks the dim as ASSUMED in that case; the embedding loader adopts
the model's true dimension at first load (the length-filter reads
CONFIG.embedding_dim per access, so the late update takes effect). A pinned
HIPPO_EMBEDDING_DIM or a known-table model is never overridden.
"""
from __future__ import annotations

import engram.embedding as emb
from engram.config import Config


def _cfg(monkeypatch, model: str, dim_env: str | None):
    monkeypatch.setenv("HIPPO_EMBEDDING_MODEL", model)
    if dim_env is None:
        monkeypatch.delenv("HIPPO_EMBEDDING_DIM", raising=False)
    else:
        monkeypatch.setenv("HIPPO_EMBEDDING_DIM", dim_env)
    return Config()


def test_unknown_model_unpinned_dim_is_marked_assumed(monkeypatch) -> None:
    cfg = _cfg(monkeypatch, "acme/made-up-encoder", None)
    assert cfg.embedding_dim == 768                  # the documented assumption
    assert cfg.embedding_dim_assumed is True         # ...now explicit


def test_known_model_dim_not_assumed(monkeypatch) -> None:
    cfg = _cfg(monkeypatch, "intfloat/multilingual-e5-base", None)
    assert cfg.embedding_dim_assumed is False


def test_pinned_dim_never_assumed(monkeypatch) -> None:
    cfg = _cfg(monkeypatch, "acme/made-up-encoder", "1024")
    assert cfg.embedding_dim == 1024
    assert cfg.embedding_dim_assumed is False


class _FakeST:
    def __init__(self, dim):
        self._dim = dim

    def get_sentence_embedding_dimension(self):
        return self._dim


def _with_config(dim: int, assumed: bool):
    """Set the CONFIG singleton's dim state and return a restore fn.
    (conftest autouse-stubs embedding._model, so the adopt hook is unit-tested
    directly on _adopt_true_dim; the loader wiring is one line, verified by the
    live repro that motivated this fix.)"""
    from engram.config import CONFIG
    prev = (CONFIG.embedding_dim, getattr(CONFIG, "embedding_dim_assumed", False))
    object.__setattr__(CONFIG, "embedding_dim", dim)
    object.__setattr__(CONFIG, "embedding_dim_assumed", assumed)

    def restore():
        object.__setattr__(CONFIG, "embedding_dim", prev[0])
        object.__setattr__(CONFIG, "embedding_dim_assumed", prev[1])
    return CONFIG, restore


def test_adopt_takes_true_dim_when_assumed() -> None:
    cfg, restore = _with_config(768, assumed=True)
    try:
        emb._adopt_true_dim(_FakeST(1024))
        assert cfg.embedding_dim == 1024, "true dim must be adopted"
        assert cfg.embedding_dim_assumed is False
    finally:
        restore()


def test_adopt_never_overrides_pinned_or_known() -> None:
    cfg, restore = _with_config(768, assumed=False)   # pinned/known
    try:
        emb._adopt_true_dim(_FakeST(1024))
        assert cfg.embedding_dim == 768, "explicit dim must never be touched"
    finally:
        restore()


def test_adopt_survives_model_errors() -> None:
    class _Boom:
        def get_sentence_embedding_dimension(self):
            raise RuntimeError("no dim api")

    cfg, restore = _with_config(768, assumed=True)
    try:
        emb._adopt_true_dim(_Boom())          # must not raise
        assert cfg.embedding_dim == 768       # assumption left in place
    finally:
        restore()
