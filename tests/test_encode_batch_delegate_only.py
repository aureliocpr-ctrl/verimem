"""Audit#2 2026-06-08 A-2: embedding.encode()'s ITERABLE (batch) branch called
``_model()`` directly, cold-loading the SentenceTransformer under ``_MODEL_LOCK``
(~33s) even when ``HIPPO_ENCODE_DELEGATE_ONLY=1`` forbids in-process loads — the
exact hang the single-text path (`_encode_one`) guards against. A batch encode
(EpisodicMemory.record_episodes_batch -> embedding.encode([...]) at memory.py
643/656) therefore wedged every concurrent recall/save on an MCP server.

Fix: the batch branch now mirrors the single-text DEGRADE contract — in
delegate-only mode with no warm model it routes per-text through the shared
service and raises ``EncodeDelegateUnavailable`` when the daemon is down,
NEVER cold-loading locally.
"""
from __future__ import annotations

import numpy as np
import pytest

from engram import embedding
from engram.config import CONFIG


def _no_coldload():
    raise AssertionError("delegate-only / empty batch path cold-loaded the model")


def test_batch_encode_delegate_only_raises_instead_of_coldload(monkeypatch):
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    # Service unavailable (Aurelio's box runs a real daemon — stub it OFF so the
    # cold-load guard is actually exercised).
    monkeypatch.setattr(embedding, "_encode_via_service", lambda text: None)
    embedding._reset_model_for_tests()  # is_loaded() == False, cache cleared
    monkeypatch.setattr(embedding, "_model", _no_coldload)
    with pytest.raises(embedding.EncodeDelegateUnavailable):
        embedding.encode(["zzz-batch-degrade-a", "zzz-batch-degrade-b"])


def test_batch_encode_delegate_only_uses_service_no_coldload(monkeypatch):
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    fake = np.ones(CONFIG.embedding_dim, dtype=np.float32)
    monkeypatch.setattr(embedding, "_encode_via_service", lambda text: fake.copy())
    embedding._reset_model_for_tests()
    monkeypatch.setattr(embedding, "_model", _no_coldload)  # must NOT be called
    out = embedding.encode(["svc-batch-1", "svc-batch-2", "svc-batch-3"])
    assert out.shape == (3, CONFIG.embedding_dim)
    assert out.dtype == np.float32


def test_batch_encode_empty_no_coldload(monkeypatch):
    embedding._reset_model_for_tests()
    monkeypatch.setattr(embedding, "_model", _no_coldload)  # must NOT be called
    out = embedding.encode([])
    assert out.shape == (0, CONFIG.embedding_dim)
    assert out.dtype == np.float32
