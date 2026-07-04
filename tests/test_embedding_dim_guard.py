"""embedding_dim must track embedding_model, not drift silently (bug-hunt F6).

embedding_model and embedding_dim are independent env vars (HIPPO_EMBEDDING_
MODEL / HIPPO_EMBEDDING_DIM, dim default 768). Pointing only
HIPPO_EMBEDDING_MODEL at a model whose dim != 768 (e.g. all-MiniLM-L6-v2,
384-dim) left embedding_dim frozen at 768, so expected_embedding_bytes()
= 3072 while the model emits 1536-byte vectors. Every freshly-stored vector
then mismatched the recall length-filter and was silently excluded — a
total recall blackout with NO error (the worst failure shape).

Fix: derive the dim from the known model when the operator did NOT pin
HIPPO_EMBEDDING_DIM explicitly; warn loudly on a residual mismatch or an
unknown model.

RED marker: pre-fix Config(model=MiniLM, dim unset).embedding_dim == 768.
"""
from __future__ import annotations

import engram.config as cfg

_MINILM = "sentence-transformers/all-MiniLM-L6-v2"   # 384-dim
_E5_BASE = "intfloat/multilingual-e5-base"           # 768-dim (default)


def _fresh_config(monkeypatch, *, model=None, dim=None):
    """Build a fresh Config reading the env as set. NOTE: we construct a NEW
    Config() instance — we do NOT importlib.reload(cfg), which would mutate the
    module-global CONFIG that 35 other modules share and FLAKILY leak the test
    env into unrelated tests (it did: test_longmemeval_runner / test_wake_extra
    read CONFIG.* and saw 'some/unknown-encoder'). Config's field default_factory
    reads os.environ at construction, so monkeypatch.setenv + Config() suffices."""
    monkeypatch.delenv("HIPPO_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("HIPPO_EMBEDDING_DIM", raising=False)
    if model is not None:
        monkeypatch.setenv("HIPPO_EMBEDDING_MODEL", model)
    if dim is not None:
        monkeypatch.setenv("HIPPO_EMBEDDING_DIM", dim)
    return cfg.Config()


def test_dim_derived_from_known_model(monkeypatch):
    c = _fresh_config(monkeypatch, model=_MINILM)  # dim unset
    assert c.embedding_dim == 384, (
        "a 384-dim model with HIPPO_EMBEDDING_DIM unset must derive dim=384, "
        "not leave it frozen at 768 (silent recall blackout)"
    )


def test_explicit_dim_is_respected(monkeypatch):
    c = _fresh_config(monkeypatch, model=_MINILM, dim="512")
    assert c.embedding_dim == 512, (
        "an explicit HIPPO_EMBEDDING_DIM must win over derivation (operator override)"
    )


def test_default_e5_stays_768(monkeypatch):
    c = _fresh_config(monkeypatch)  # nothing set -> e5-base default
    assert c.embedding_model == _E5_BASE
    assert c.embedding_dim == 768, "the default model/dim pair must be unchanged"


def test_known_model_matching_dim_unchanged(monkeypatch):
    c = _fresh_config(monkeypatch, model=_E5_BASE, dim="768")
    assert c.embedding_dim == 768


def test_unknown_model_keeps_configured_dim(monkeypatch):
    c = _fresh_config(monkeypatch, model="some/unknown-encoder")
    # can't derive -> keep the default, the guard only warns
    assert c.embedding_dim == 768
    # the module-global CONFIG must be UNTOUCHED — we never reload(cfg).
    assert cfg.CONFIG.embedding_model != "some/unknown-encoder"
