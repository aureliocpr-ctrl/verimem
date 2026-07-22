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

        from verimem.config import CONFIG

        hit = try_to_load_from_cache(CONFIG.embedding_model, "config.json")
        return isinstance(hit, str)
    except Exception:  # noqa: BLE001 — any failure → treat as not-cached → skip
        return False


requires_real_model = pytest.mark.skipif(
    not real_model_cached(),
    reason="real embedding model not in local HF cache (run `engram warmup` first)",
)


@functools.lru_cache(maxsize=1)
def real_ce_cached() -> bool:
    """True iff the local CE *gate* model is present (offline-scorable).

    Distinct from the embedding model: the moat judge is the fine-tuned gate CE
    (``local_gate_ce_v2``), which ``verimem warmup`` downloads only WITHOUT
    ``--no-gate``. CI warms with ``--no-gate`` (it historically "doesn't exercise
    the moat"), so CE-moat tests must skip there — the same discipline as
    ``requires_real_model`` for the embedding. Uses the gate's OWN availability
    predicate (never loads the model), so it tracks exactly the code path that
    would otherwise fail with ``ce_unavailable_failopen``.
    """
    try:
        from verimem.local_grounding import local_ce_available

        return bool(local_ce_available())
    except Exception:  # noqa: BLE001 — any failure → treat as unavailable → skip
        return False


requires_real_ce = pytest.mark.skipif(
    not real_ce_cached(),
    reason="local CE gate model not cached (run `verimem warmup` without --no-gate)",
)
