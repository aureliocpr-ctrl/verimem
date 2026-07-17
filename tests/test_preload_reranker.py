"""The MCP server preload must also warm the stage-2 reranker (its own thread/lock),
so the R@1 lever is resident for live recalls — not just after `engram warmup`.
Hermetic: stub the loader; assert it's called when enabled, skipped when disabled,
and that a load failure never propagates (boot must not crash)."""
from __future__ import annotations

from verimem import preload


def test_warm_reranker_loads_when_enabled(monkeypatch):
    from verimem import semantic
    monkeypatch.setattr(semantic, "_rerank_enabled", lambda: True)
    called = {"n": 0}
    monkeypatch.setattr(semantic, "_load_reranker", lambda: called.__setitem__("n", called["n"] + 1))
    preload._warm_reranker()
    assert called["n"] == 1


def test_warm_reranker_skipped_when_disabled(monkeypatch):
    from verimem import semantic
    monkeypatch.setattr(semantic, "_rerank_enabled", lambda: False)
    called = {"n": 0}
    monkeypatch.setattr(semantic, "_load_reranker", lambda: called.__setitem__("n", called["n"] + 1))
    preload._warm_reranker()
    assert called["n"] == 0


def test_warm_reranker_swallows_failure(monkeypatch):
    from verimem import semantic
    monkeypatch.setattr(semantic, "_rerank_enabled", lambda: True)

    def _boom():
        raise RuntimeError("offline")

    monkeypatch.setattr(semantic, "_load_reranker", _boom)
    preload._warm_reranker()  # must not raise


def test_preload_embedding_starts_reranker_thread(monkeypatch):
    """preload_embedding spawns a reranker warm thread WHEN opted in.

    Since 3dbbcda (2026-07-10 RAM incident) the CE preload is opt-in via
    HIPPO_RERANK_PRELOAD=1 — default OFF (~450MB × N idle MCP servers). The
    thread must still spawn and warm the reranker when the operator opts in;
    this test pins the opt-in path (the default-off path is covered by the
    recall-time lazy load)."""
    from verimem import semantic
    monkeypatch.setenv("HIPPO_EAGER_PRELOAD", "1")
    monkeypatch.setenv("HIPPO_PRELOAD_BACKGROUND", "1")
    monkeypatch.setenv("HIPPO_RERANK_PRELOAD", "1")  # opt-in (default off since 3dbbcda)
    # neutralize the embedding path so the test is about the reranker thread
    monkeypatch.setattr(preload, "_warm", lambda: None)
    monkeypatch.setattr(preload, "_service_enabled", lambda: False)
    from verimem import embedding
    monkeypatch.setattr(embedding, "_delegate_only", lambda: True, raising=False)
    monkeypatch.setattr(semantic, "_rerank_enabled", lambda: True)
    seen = {"n": 0}
    monkeypatch.setattr(semantic, "_load_reranker", lambda: seen.__setitem__("n", seen["n"] + 1))
    t = preload.preload_embedding()
    if t is not None:
        t.join(timeout=5)
    # the reranker thread is separate; give it a moment to run
    import time
    for _ in range(50):
        if seen["n"]:
            break
        time.sleep(0.05)
    assert seen["n"] == 1
