"""Delegate-only encode mode — the real root fix for the recurring recall/save
hang (empirical hang-trace 2026-06-06: a server cold-loading the model
in-process ran `import sentence_transformers` (~33.7s) UNDER _MODEL_LOCK, so
every concurrent recall/save blocked on that lock).

Cure: an MCP server runs in DELEGATE-ONLY mode — it NEVER cold-loads the model
in-process. It delegates to the shared encode daemon; on a daemon miss it raises
EncodeDelegateUnavailable instead of paying the 33s in-process import under the
lock. Recall then degrades to keyword (f377ee5) and save defers (4ae96a1). Only
the daemon (which does NOT set the flag) ever loads the model — once.
"""
from __future__ import annotations

import pytest

import verimem.embedding as emb


def test_delegate_only_raises_instead_of_cold_loading(monkeypatch):
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    monkeypatch.setattr(emb, "_MODEL", None)  # not warm → a cold-load would be needed
    monkeypatch.setattr(emb, "_encode_via_service", lambda _t: None)  # daemon miss
    loaded = {"v": False}

    def _must_not_load():
        loaded["v"] = True
        raise AssertionError("delegate-only must NOT cold-load the model in-process")

    monkeypatch.setattr(emb, "_load_model", _must_not_load)
    emb.encode_cache_clear()  # avoid an lru_cache hit masking the call

    with pytest.raises(emb.EncodeDelegateUnavailable):
        emb.encode("a fresh query that is not cached")
    assert loaded["v"] is False


def test_delegate_only_still_uses_daemon_when_available(monkeypatch):
    import numpy as np
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    vec = np.ones(8, dtype=np.float32)
    monkeypatch.setattr(emb, "_encode_via_service", lambda _t: vec)  # daemon hit
    monkeypatch.setattr(emb, "_load_model",
                        lambda: (_ for _ in ()).throw(AssertionError("must not load")))
    emb.encode_cache_clear()
    out = emb.encode("query via daemon")
    assert out is not None and len(out) == 8


def test_default_mode_still_cold_loads_for_daemon_and_cli(monkeypatch):
    # Without the flag (daemon process / CLI), the in-process fallback MUST stay
    # — that path is how the daemon itself loads the one shared model.
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    monkeypatch.setattr(emb, "_encode_via_service", lambda _t: None)  # daemon miss
    import numpy as np
    monkeypatch.setattr(emb, "_load_model", lambda: _FakeModel())
    emb.encode_cache_clear()

    class _Probe:
        pass

    out = emb.encode("loads locally when not delegate-only")
    assert out is not None


class _FakeModel:
    def encode(self, text, **_kw):
        import numpy as np
        return np.ones(8, dtype=np.float32)
