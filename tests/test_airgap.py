"""Air-gap self-verification (engram.airgap.airgap_status).

For the sovereign / air-gapped enterprise segment: a deployment that must run
with ZERO network egress (local LLM + local embeddings). This pins the verdict
logic derived from the 2026-06-06 LLM leak-audit. Pure over the passed env —
no network, no model load.
"""
from __future__ import annotations

from engram.airgap import airgap_status


def test_ollama_offline_is_air_gapped():
    env = {"HIPPO_LLM_PROVIDER": "ollama", "HF_HUB_OFFLINE": "1"}
    st = airgap_status(env)
    assert st["air_gapped"] is True, st
    assert st["llm"]["local"] is True
    assert st["embeddings"]["offline_pinned"] is True
    assert st["leaks"] == []


def test_anthropic_cloud_llm_leaks():
    env = {"HIPPO_LLM_PROVIDER": "anthropic", "HF_HUB_OFFLINE": "1"}
    st = airgap_status(env)
    assert st["air_gapped"] is False
    assert st["llm"]["local"] is False
    assert any("egress" in leak.lower() or "cloud" in leak.lower() for leak in st["leaks"])


def test_hosted_mode_leaks_even_with_local_provider():
    # HIPPO_HOSTED routes consolidate/run to the host LLM (cloud) — breaks air-gap.
    env = {"HIPPO_LLM_PROVIDER": "ollama", "HF_HUB_OFFLINE": "1", "HIPPO_HOSTED": "1"}
    st = airgap_status(env)
    assert st["air_gapped"] is False
    assert st["hosted_mode"] is True
    assert any("HIPPO_HOSTED" in leak for leak in st["leaks"])


def test_openai_compatible_local_endpoint_is_local():
    # vLLM / LM Studio / llama.cpp exposed on localhost.
    env = {
        "HIPPO_LLM_PROVIDER": "openai",
        "OPENAI_BASE_URL": "http://localhost:8000/v1",
        "TRANSFORMERS_OFFLINE": "1",
    }
    st = airgap_status(env)
    assert st["llm"]["local"] is True, st["llm"]
    assert st["air_gapped"] is True


def test_openai_cloud_base_url_is_not_local():
    env = {
        "HIPPO_LLM_PROVIDER": "openai",
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
        "HF_HUB_OFFLINE": "1",
    }
    st = airgap_status(env)
    assert st["llm"]["local"] is False
    assert st["air_gapped"] is False


def test_embeddings_not_pinned_offline_is_a_leak():
    env = {"HIPPO_LLM_PROVIDER": "ollama"}  # no offline flag
    st = airgap_status(env)
    assert st["embeddings"]["offline_pinned"] is False
    assert st["air_gapped"] is False
    assert any("offline" in leak.lower() for leak in st["leaks"])


def test_no_provider_is_not_air_gapped():
    # Empty config must NOT claim air-gap (auto-detect may pick cloud/hosted).
    st = airgap_status({})
    assert st["air_gapped"] is False
    assert st["llm"]["local"] is False
