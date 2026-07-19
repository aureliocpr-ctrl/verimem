"""NLI semantic tier AUTO-ENABLE (0.7.0 — mandate: everything installed is ON).

Previously the semantic-contradiction moat required an explicit
``ENGRAM_SEMANTIC_CONFLICT=1`` even when the local NLI model was already
installed — shipped capability, default off. Now: with the env var UNSET the
tier auto-enables (enforce) iff the model is PRESENT on disk (cheap
filesystem check, no model load); absent model → off, exactly as before.
Explicit values keep full control: ``0`` opts out, ``observe`` observes,
``1`` forces enforce (even to fail loudly if the model is missing).
"""
from __future__ import annotations

from verimem import anti_confab_gate as g
from verimem import local_relation as lr


def test_available_check_is_pure_filesystem(monkeypatch, tmp_path):
    """local_nli_available() must not import torch/transformers — it checks
    the HF cache dir for a non-empty model snapshot."""
    fake_hub = tmp_path / "hub"
    model_dir = fake_hub / ("models--MoritzLaurer--"
                            "DeBERTa-v3-large-mnli-fever-anli-ling-wanli")
    (model_dir / "snapshots" / "abc").mkdir(parents=True)
    (model_dir / "snapshots" / "abc" / "config.json").write_text("{}")
    monkeypatch.setenv("HF_HUB_CACHE", str(fake_hub))
    lr.local_nli_available.cache_clear()
    assert lr.local_nli_available() is True

    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "empty"))
    lr.local_nli_available.cache_clear()
    assert lr.local_nli_available() is False


def test_unset_env_auto_enforces_when_model_present(monkeypatch):
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    monkeypatch.setattr(lr, "local_nli_available", lambda: True)
    assert g._semantic_conflict_mode() == "enforce"


def test_unset_env_stays_off_when_model_absent(monkeypatch):
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    monkeypatch.setattr(lr, "local_nli_available", lambda: False)
    assert g._semantic_conflict_mode() == "off"


def test_explicit_zero_opts_out_even_with_model(monkeypatch):
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "0")
    monkeypatch.setattr(lr, "local_nli_available", lambda: True)
    assert g._semantic_conflict_mode() == "off"


def test_explicit_enforce_and_observe_unchanged(monkeypatch):
    monkeypatch.setattr(lr, "local_nli_available", lambda: False)
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "1")
    assert g._semantic_conflict_mode() == "enforce"
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "observe")
    assert g._semantic_conflict_mode() == "observe"
