"""ENGRAM_MODE single-knob deployment mode (subscription | byok | local).

One env var derives the lower-level flags, but NEVER clobbers an explicit one
(setdefault precedence). Pure over the passed env dict — no os.environ, no
network.
"""
from __future__ import annotations

from verimem.airgap import airgap_status
from verimem.mode import apply_engram_mode, engram_mode


def test_local_mode_derives_airgap_env():
    env = {"ENGRAM_MODE": "local"}
    r = apply_engram_mode(env)
    assert r["mode"] == "local" and r["valid"]
    assert env["HIPPO_LLM_PROVIDER"] == "ollama"
    assert env["HF_HUB_OFFLINE"] == "1"
    assert env["TRANSFORMERS_OFFLINE"] == "1"
    assert "HIPPO_HOSTED" not in env  # local is not hosted


def test_subscription_mode_sets_hosted():
    env = {"ENGRAM_MODE": "subscription"}
    apply_engram_mode(env)
    assert env["HIPPO_HOSTED"] == "1"


def test_explicit_provider_wins_over_local_default():
    # operator forces an OpenAI-compatible local endpoint — local must NOT
    # clobber it to ollama, but still derives the offline flags.
    env = {
        "ENGRAM_MODE": "local",
        "HIPPO_LLM_PROVIDER": "openai",
        "OPENAI_BASE_URL": "http://localhost:8000/v1",
    }
    apply_engram_mode(env)
    assert env["HIPPO_LLM_PROVIDER"] == "openai"
    assert env["HF_HUB_OFFLINE"] == "1"


def test_unset_mode_is_noop():
    env: dict[str, str] = {}
    r = apply_engram_mode(env)
    assert r["mode"] is None and r["applied"] == {} and env == {}


def test_byok_mode_no_derivation():
    env = {"ENGRAM_MODE": "byok", "HIPPO_LLM_PROVIDER": "groq"}
    r = apply_engram_mode(env)
    assert r["applied"] == {} and env["HIPPO_LLM_PROVIDER"] == "groq"


def test_invalid_mode_flagged():
    assert apply_engram_mode({"ENGRAM_MODE": "banana"})["valid"] is False


def test_local_mode_is_air_gapped_end_to_end():
    # The whole point: ONE var -> airgap_status says air_gapped.
    env = {"ENGRAM_MODE": "local"}
    apply_engram_mode(env)
    st = airgap_status(env)
    assert st["air_gapped"] is True, st
    assert engram_mode(env) == "local"
