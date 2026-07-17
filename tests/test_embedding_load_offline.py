"""``_load_model`` deve caricare CACHE-ONLY (``local_files_only=True``) per
evitare il round-trip di rete a HF Hub ad ogni load.

Motivazione (2026-06-04): il warning "sending unauthenticated requests to the HF
Hub" mostra che ``SentenceTransformer(model)`` PINGA la rete anche a modello già
in cache. Offline / sotto rate-limit quel ping è lento o si blocca → puo' stallare
il PRIMO encode di un server MCP a freddo (hang osservato 2× oggi su recall/write
via MCP). Fix: prova ``local_files_only=True`` (cache, zero rete); fallback al load
con rete SOLO se il modello non è ancora in cache (primo download).

Hermetic: ``SentenceTransformer`` è mockato — nessun load reale, nessuna rete.
"""
from __future__ import annotations

import sys
import types


def _install_fake_st(monkeypatch, calls, *, fail_local: bool = False):
    """Inserisce un finto modulo ``sentence_transformers`` con SentenceTransformer
    che registra i kwargs di costruzione. Se ``fail_local`` e' True, alza quando
    chiamato con ``local_files_only=True`` (simula modello non in cache)."""
    fake = types.ModuleType("sentence_transformers")

    class FakeST:
        def __init__(self, model, **kw):
            calls.append(kw)
            if fail_local and kw.get("local_files_only"):
                raise OSError("model not found in local cache")
            self.model = model

    fake.SentenceTransformer = FakeST
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake)


def test_load_model_prefers_local_files_only(monkeypatch):
    calls: list[dict] = []
    _install_fake_st(monkeypatch, calls)
    from verimem import embedding
    embedding._load_model()
    assert calls, "SentenceTransformer deve essere costruito"
    assert calls[0].get("local_files_only") is True, (
        "il primo tentativo deve essere cache-only (niente rete a HF)"
    )


def test_load_model_falls_back_to_network_when_not_cached(monkeypatch):
    calls: list[dict] = []
    _install_fake_st(monkeypatch, calls, fail_local=True)
    # 2026-06-05: the network fallback is now GATED on offline flags — an
    # offline HF-Hub stall under _MODEL_LOCK was the 4h save/recall hang. This
    # test pins the ONLINE path (not cached -> network download), so make sure
    # no offline flag is set; the OFFLINE path (re-raise, no network) is covered
    # by test_embedding_load_no_hang.test_load_model_offline_reraises.
    for _v in ("HIPPO_OFFLINE", "ENGRAM_OFFLINE", "HF_HUB_OFFLINE",
               "TRANSFORMERS_OFFLINE"):
        monkeypatch.delenv(_v, raising=False)
    from verimem import embedding
    embedding._load_model()  # online + not cached -> retry WITH network
    assert len(calls) == 2, "deve ritentare il load (cache-only fallito -> con rete)"
    assert calls[0].get("local_files_only") is True
    assert not calls[1].get("local_files_only"), (
        "il fallback deve permettere il download di rete (primo scaricamento)"
    )
