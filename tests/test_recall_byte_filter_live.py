"""Harden: the recall byte-filter must be LIVE, not frozen at import.

``semantic._EXPECTED_EMBEDDING_BYTES`` gates every ``np.stack`` recall path
(facts / episodes / skills) by vector byte-length. It used to be a module
constant computed ONCE at import time. That is a production landmine: a runtime
embedding-model/dim switch (e.g. MiniLM-384 -> e5-768) updates
``embedding.model_signature()`` and ``embedding.expected_embedding_bytes()``
LIVE, but a frozen byte-filter stays at the import-time dim -> every new-dim
vector is silently filtered out of recall -> total blackout with zero error.

These tests pin the invariant that the byte-filter tracks the active model at
ACCESS time. They are env-agnostic (they monkeypatch the canonical source
directly), so they hold under the conftest ``HIPPO_EMBEDDING_DIM=384`` session
pin as well as in production (default 768).
"""
from __future__ import annotations

import pytest

from verimem import embedding, semantic


def test_byte_filter_tracks_runtime_model_switch(monkeypatch):
    # at rest the module attr equals the canonical live source
    assert semantic._EXPECTED_EMBEDDING_BYTES == embedding.expected_embedding_bytes()

    # simulate a runtime model/dim switch at the canonical source
    monkeypatch.setattr(embedding, "expected_embedding_bytes", lambda: 9001)

    # the recall byte-filter MUST follow; a frozen import-time int would not
    assert semantic._EXPECTED_EMBEDDING_BYTES == 9001, (
        "byte-filter frozen at import -> a runtime dim change is ignored, "
        "silently excluding every new-dim vector from recall (blackout)"
    )


def test_byte_filter_seen_live_by_from_import_consumers(monkeypatch):
    # memory.py / skill.py do `from .semantic import _EXPECTED_EMBEDDING_BYTES`
    # INSIDE their query methods on every call -> that path must see live too
    monkeypatch.setattr(embedding, "expected_embedding_bytes", lambda: 7777)
    from verimem.semantic import _EXPECTED_EMBEDDING_BYTES as v  # noqa: PLC0415

    assert v == 7777


def test_unknown_module_attr_still_raises():
    # __getattr__ must not mask genuine typos / missing names
    with pytest.raises(AttributeError):
        _ = semantic._THIS_ATTR_DOES_NOT_EXIST  # noqa: B018
