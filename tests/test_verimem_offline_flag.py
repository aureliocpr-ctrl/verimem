"""The primary brand's offline flag must actually work (rename completeness).

A user who `pip install verimem` and, following the brand, sets
``VERIMEM_OFFLINE=1`` for an air-gapped deployment expects it to be honored —
exactly like the legacy ``HIPPO_OFFLINE``/``ENGRAM_OFFLINE``. Before this fix the
new brand name was recognised NOWHERE: the embedding loader still hit the HF Hub,
``get_llm`` still tried a cloud provider, and ``verimem airgap`` reported "not
pinned offline". This pins the gap (found by walking the CLI as an outside user,
2026-07-18).
"""
from __future__ import annotations

import verimem.airgap as airgap
import verimem.embedding as embedding
import verimem.llm as llm


def test_verimem_offline_is_an_honored_embedding_flag():
    assert "VERIMEM_OFFLINE" in embedding._OFFLINE_ENV_VARS
    assert "VERIMEM_OFFLINE" in airgap._OFFLINE_FLAGS


def test_embedding_offline_true_with_only_verimem_offline(monkeypatch):
    for v in ("HIPPO_OFFLINE", "ENGRAM_OFFLINE", "HF_HUB_OFFLINE",
              "TRANSFORMERS_OFFLINE"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("VERIMEM_OFFLINE", "1")
    assert embedding._offline() is True


def test_get_llm_returns_mock_with_only_verimem_offline(monkeypatch):
    for v in ("HIPPO_OFFLINE", "ENGRAM_OFFLINE", "HIPPO_LLM_PROVIDER"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("VERIMEM_OFFLINE", "1")
    # make a REAL provider look available so a false fall-through to mock (no API
    # keys) can't green this — ONLY the VERIMEM_OFFLINE short-circuit may return
    # MockLLM here.
    monkeypatch.setattr(llm, "_autodetect_provider", lambda: "anthropic")
    monkeypatch.setattr(llm, "_build", lambda p: "REAL-CLIENT")
    client = llm.get_llm()
    assert type(client).__name__ == "MockLLM"


def test_airgap_advisory_advertises_the_brand_flag(monkeypatch):
    # empty env → embeddings not pinned → the advisory must NAME the brand flag,
    # not only the legacy aliases. Pure over env, no network.
    report = airgap.airgap_status(env={})
    blob = str(report).upper()
    assert "VERIMEM_OFFLINE" in blob, f"advisory hides the brand flag: {report}"
