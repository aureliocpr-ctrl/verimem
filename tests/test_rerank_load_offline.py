"""Il cross-encoder si carica CACHE-ONLY: nessun round-trip a HF Hub.

Parita' con ``embedding._load_model`` (fix 2026-06-04). Un load che va in rete
e' un egress in un prodotto che vende il funzionamento air-gapped, e sotto il
lock del reranker sarebbe anche uno stallo che blocca il recall (la lezione
dell'embedding-hang del 2026-06-05).

RIPUNTATO il 2026-07-31. Questo file provava ``rerank._load_cross_encoder``, e
``rerank.py`` era un layer opt-in del 3 giugno che nessuna superficie importa:
il rerank e' stato poi integrato dentro ``semantic.recall`` (P0.3, 10 giugno,
default AUTO) e quel modulo e' rimasto indietro. Provava la proprieta' giusta
sul modulo sbagliato — e siccome il modulo morto veniva rimosso, la proprieta'
sarebbe sparita insieme al file.

Ora prova ``semantic._load_reranker``, che e' il loader che gira davvero. Che il
fix ci fosse anche li' non era scontato: verificato PRIMA di spostare il test.

Hermetic: ``CrossEncoder`` mockato — nessun load reale (il reranker e' ~2GB).
"""
from __future__ import annotations

import sys
import types

import pytest


def _install_fake_ce(monkeypatch, calls, *, fail_local: bool = False):
    fake = types.ModuleType("sentence_transformers")

    class FakeCE:
        def __init__(self, model, **kw):
            calls.append(kw)
            if fail_local and kw.get("local_files_only"):
                raise OSError("cross-encoder not in local cache")
            self.model = model

        def predict(self, pairs, **kw):
            return [0.0] * len(pairs)

    fake.CrossEncoder = FakeCE
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake)


@pytest.fixture(autouse=True)
def _reranker_pulito(monkeypatch):
    """Il reranker e' un singleton di processo: senza azzerarlo, un test che
    gira dopo un recall vero non caricherebbe nulla e passerebbe a vuoto."""
    from verimem import semantic
    monkeypatch.setattr(semantic, "_RERANKER", None, raising=False)
    yield
    monkeypatch.setattr(semantic, "_RERANKER", None, raising=False)


def test_il_primo_tentativo_e_cache_only(monkeypatch):
    calls: list[dict] = []
    _install_fake_ce(monkeypatch, calls)
    from verimem import semantic
    semantic._load_reranker()
    assert calls and calls[0].get("local_files_only") is True, (
        f"il primo tentativo deve essere cache-only (niente rete a HF): {calls}")


def test_senza_cache_ritenta_con_la_rete(monkeypatch):
    calls: list[dict] = []
    _install_fake_ce(monkeypatch, calls, fail_local=True)
    from verimem import semantic
    monkeypatch.setattr(semantic.embedding, "_offline", lambda: False)
    semantic._load_reranker()
    assert len(calls) == 2, f"cache-only fallito -> ritenta con rete: {calls}"
    assert calls[0].get("local_files_only") is True
    assert not calls[1].get("local_files_only")


def test_in_modalita_offline_non_va_in_rete(monkeypatch):
    """La differenza che il modulo morto NON aveva: con un flag offline attivo
    il fallback di rete non parte affatto, alza. Un prodotto che promette zero
    egress non puo' decidere di uscire perche' gli manca una cache."""
    calls: list[dict] = []
    _install_fake_ce(monkeypatch, calls, fail_local=True)
    from verimem import semantic
    monkeypatch.setattr(semantic.embedding, "_offline", lambda: True)
    with pytest.raises(OSError):
        semantic._load_reranker()
    assert len(calls) == 1, f"offline: nessun secondo tentativo, {calls}"
