"""TDD — _encode_via_service usa il daemon SOLO se serve lo stesso modello di
CONFIG (rescan2 HIGH: corpus poisoning silenzioso).
Bug: _encode_via_service ritornava il vettore del daemon senza verificare il
modello -> un daemon stale/di altra config (altro spazio embedding, stessa dim)
inquinava semantic.db con vettori non comparabili (cosine sballato), non
rilevabile. Il discovery PORTA 'model' (encode_service.py:177) ma nessuno lo
leggeva. Fix: mismatch/assente -> None -> fallback local (modello corretto).
HERMETIC: monkeypatch socket + discovery, nessun daemon reale."""
from __future__ import annotations

import socket

import numpy as np

from verimem import embedding as e
from verimem import encode_service as svc
from verimem.config import CONFIG


class _FakeConn:
    def settimeout(self, *a):
        pass

    def close(self):
        pass


def _wire(monkeypatch, model_name):
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "1")
    monkeypatch.setattr(svc, "read_discovery",
                        lambda *a, **k: {"host": "127.0.0.1", "port": 59999, "model": model_name})
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: _FakeConn())
    monkeypatch.setattr(svc, "send_msg", lambda c, m: None)
    monkeypatch.setattr(svc, "recv_msg", lambda c: {"ok": True, "vec": [0.1] * 384})


def test_rejects_wrong_model_daemon(monkeypatch):
    # daemon che RISPONDE con un vettore ma serve un modello DIVERSO da CONFIG
    _wire(monkeypatch, "WRONG/" + CONFIG.embedding_model)
    out = e._encode_via_service("ciao")
    assert out is None, ("daemon con modello != CONFIG NON deve essere usato "
                         "(poisoning cosine): atteso fallback local (None)")


def test_accepts_matching_model_daemon(monkeypatch):
    # daemon col modello CORRETTO -> il suo vettore e' usato
    _wire(monkeypatch, CONFIG.embedding_model)
    out = e._encode_via_service("ciao")
    assert out is not None and isinstance(out, np.ndarray) and out.shape == (384,)
