"""Skip-guard for tests that need the REAL embedding model.

Some tests can't use the in-process 384-d stub: subprocess workers spawn a fresh
Python (no monkeypatch), or the test explicitly exercises the real offline-load
behaviour. On a machine/CI where the model isn't cached, those tests fail with an
HF-offline ``OSError: couldn't connect to huggingface.co``. Skipping when the
model isn't cached keeps the suite green everywhere (CI without a warmed cache, a
fresh contributor) while still RUNNING the tests where the model is present
(local dev, or a CI job whose ``engram warmup`` step populated the HF cache).
"""
from __future__ import annotations

import functools

import pytest


@functools.lru_cache(maxsize=1)
def real_model_cached() -> bool:
    """True iff CONFIG.embedding_model is in the local HF cache (offline-loadable).

    Fast: a cache lookup (``try_to_load_from_cache``), not a model load.
    """
    try:
        from huggingface_hub import try_to_load_from_cache

        from engram.config import CONFIG

        hit = try_to_load_from_cache(CONFIG.embedding_model, "config.json")
        return isinstance(hit, str)
    except Exception:  # noqa: BLE001 — any failure → treat as not-cached → skip
        return False


requires_real_model = pytest.mark.skipif(
    not real_model_cached(),
    reason="real embedding model not in local HF cache (run `engram warmup` first)",
)
