"""`engram warmup` must also pre-load the stage-2 cross-encoder reranker (the R@1
lever) when rerank is enabled — otherwise every fresh process serves rerank-cold
recalls for ~33s. Hermetic: stub the model loaders, assert the reranker load is invoked
and that a missing reranker never fails warmup."""
from __future__ import annotations

import numpy as np
import pytest

from engram import cli


def _patch_embedding(monkeypatch):
    from engram import embedding
    monkeypatch.setattr(embedding, "_model", lambda: object(), raising=True)
    monkeypatch.setattr(embedding, "encode", lambda *a, **k: np.zeros(8, dtype=np.float32),
                        raising=True)


def test_warmup_preloads_reranker_when_enabled(monkeypatch):
    from engram import semantic
    _patch_embedding(monkeypatch)
    monkeypatch.setattr(semantic, "_rerank_enabled", lambda: True)
    called = {"n": 0}

    def _fake_load():
        called["n"] += 1
        return object()  # a non-None scorer

    monkeypatch.setattr(semantic, "_load_reranker", _fake_load)
    cli.warmup(daemon=False)
    assert called["n"] == 1  # reranker was pre-loaded


def test_warmup_skips_reranker_when_disabled(monkeypatch):
    from engram import semantic
    _patch_embedding(monkeypatch)
    monkeypatch.setattr(semantic, "_rerank_enabled", lambda: False)
    called = {"n": 0}
    monkeypatch.setattr(semantic, "_load_reranker", lambda: called.__setitem__("n", called["n"] + 1))
    cli.warmup(daemon=False)
    assert called["n"] == 0  # opt-out honored


def test_warmup_survives_reranker_load_failure(monkeypatch):
    from engram import semantic
    _patch_embedding(monkeypatch)
    monkeypatch.setattr(semantic, "_rerank_enabled", lambda: True)

    def _boom():
        raise RuntimeError("offline, model not cached")

    monkeypatch.setattr(semantic, "_load_reranker", _boom)
    cli.warmup(daemon=False)  # must NOT raise — reranker is best-effort
