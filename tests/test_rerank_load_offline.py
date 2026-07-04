"""``rerank._load_cross_encoder`` deve caricare CACHE-ONLY (parità con
``embedding._load_model``): niente round-trip di rete a HF Hub al load del
cross-encoder. Fallback con rete solo se il modello non è ancora in cache.

Hermetic: ``CrossEncoder`` mockato — nessun load reale (il reranker è ~2GB).
"""
from __future__ import annotations

import sys
import types


def _install_fake_ce(monkeypatch, calls, *, fail_local: bool = False):
    fake = types.ModuleType("sentence_transformers")

    class FakeCE:
        def __init__(self, model, **kw):
            calls.append(kw)
            if fail_local and kw.get("local_files_only"):
                raise OSError("cross-encoder not in local cache")
            self.model = model

    fake.CrossEncoder = FakeCE
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake)


def test_load_cross_encoder_prefers_local_files_only(monkeypatch):
    calls: list[dict] = []
    _install_fake_ce(monkeypatch, calls)
    from engram import rerank
    rerank._load_cross_encoder.cache_clear()
    try:
        rerank._load_cross_encoder("model-A")
        assert calls and calls[0].get("local_files_only") is True, (
            "il primo tentativo deve essere cache-only (niente rete a HF)"
        )
    finally:
        rerank._load_cross_encoder.cache_clear()


def test_load_cross_encoder_falls_back_to_network(monkeypatch):
    calls: list[dict] = []
    _install_fake_ce(monkeypatch, calls, fail_local=True)
    from engram import rerank
    rerank._load_cross_encoder.cache_clear()
    try:
        rerank._load_cross_encoder("model-B")  # non deve propagare
        assert len(calls) == 2, "cache-only fallito -> ritenta con rete"
        assert calls[0].get("local_files_only") is True
        assert not calls[1].get("local_files_only")
    finally:
        rerank._load_cross_encoder.cache_clear()
