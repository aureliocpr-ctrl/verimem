"""Coverage push for verimem.llm — internals + provider helpers.

Strategy:
- All HTTP mocked (httpx via respx, anthropic SDK + openai SDK via patches).
- No real provider calls: never set real API keys; just env stubs.
- Cover: temperature gating, alias resolution, autodetect, is_configured,
  resolve_model precedence, MockLLM, OpenAICompatLLM tool_calls parsing,
  list_providers, list_models_for_provider, scan_all_providers, get_llm modes.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from verimem import llm as llm_mod
from verimem.llm import (
    ALIASES,
    PROVIDERS,
    AnthropicLLM,
    FallbackLLM,
    LLMError,
    LLMResponse,
    LLMToolResponse,
    MockLLM,
    OllamaLLM,
    OpenAICompatLLM,
    ToolCall,
    _autodetect_provider,
    _build,
    _canonical,
    get_llm,
    is_configured,
    list_models_for_provider,
    list_providers,
    resolve_model,
    scan_all_providers,
)


@pytest.fixture
def anthropic_key(request):
    """Fixture for setting/unsetting CONFIG.anthropic_api_key.

    CONFIG is a frozen dataclass, so monkeypatch.setattr fails. This fixture
    uses object.__setattr__ to bypass the lock and registers a teardown.
    Usage:
        def test_x(anthropic_key):
            anthropic_key("sk-test")
            ...
    """
    original = llm_mod.CONFIG.anthropic_api_key

    def setter(value: str) -> None:
        object.__setattr__(llm_mod.CONFIG, "anthropic_api_key", value)

    yield setter
    object.__setattr__(llm_mod.CONFIG, "anthropic_api_key", original)


# ---------------------------------------------------------------------------
# Temperature support detection (Anthropic opus-4-7+)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("model,expected", [
    ("claude-opus-4-7", False),
    ("claude-opus-4-7[1m]", False),
    ("claude-opus-4-8", False),
    ("claude-opus-4-7-20250219", False),
    ("claude-haiku-4-5", True),
    ("claude-sonnet-4-5", True),
    ("claude-3-5-sonnet-20241022", True),
    ("", True),
    ("CLAUDE-OPUS-4-7", False),  # case-insensitive
])
def test_anthropic_supports_temperature(model, expected):
    assert AnthropicLLM._supports_temperature(model) is expected


# ---------------------------------------------------------------------------
# _canonical alias resolution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("alias,canonical", [
    ("kimi", "moonshot"),
    ("KIMI", "moonshot"),
    ("  kimi  ", "moonshot"),
    ("glm", "zhipu"),
    ("chatglm", "zhipu"),
    ("ark", "doubao"),
    ("bytedance", "doubao"),
    ("tencent", "hunyuan"),
    ("step", "stepfun"),
    ("iflytek", "spark"),
    ("google", "gemini"),
    ("lingyi", "yi"),
    ("01ai", "yi"),
    ("01", "yi"),
    ("dashscope", "qwen"),
    ("alibaba", "qwen"),
    ("tongyi", "qwen"),
    ("claude", "anthropic"),
    ("grok", "xai"),
    ("hf", "huggingface"),
    ("lm-studio", "lmstudio"),
    ("lm_studio", "lmstudio"),
    # Known canonical names pass through:
    ("openai", "openai"),
    ("anthropic", "anthropic"),
    # Unknown name: returned as lowercase trimmed
    ("MyCustomProv", "mycustomprov"),
])
def test_canonical_resolution(alias, canonical):
    assert _canonical(alias) == canonical


def test_aliases_table_all_resolve_to_known_canonical():
    """No alias may point to a non-existent canonical."""
    canonicals = set(PROVIDERS.keys()) | {"anthropic", "ollama", "mock"}
    for alias, target in ALIASES.items():
        assert target in canonicals, f"alias {alias!r} → unknown {target!r}"


# ---------------------------------------------------------------------------
# _autodetect_provider — env-driven priority order
# ---------------------------------------------------------------------------


def _wipe_provider_env(monkeypatch):
    """Strip every API key env var so autodetect starts clean."""
    for key in [
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AZURE_OPENAI_API_KEY",
        "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY", "XAI_API_KEY",
        "PERPLEXITY_API_KEY", "FIREWORKS_API_KEY", "TOGETHER_API_KEY",
        "CEREBRAS_API_KEY", "GEMINI_API_KEY", "NVIDIA_API_KEY", "HF_TOKEN",
        "DEEPINFRA_API_KEY", "HYPERBOLIC_API_KEY", "NOVITA_API_KEY",
        "ANYSCALE_API_KEY", "LEPTON_API_KEY",
        "MOONSHOT_API_KEY", "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY",
        "ZHIPU_API_KEY", "BAICHUAN_API_KEY", "YI_API_KEY", "DOUBAO_API_KEY",
        "HUNYUAN_API_KEY", "STEP_API_KEY", "MINIMAX_API_KEY", "SPARK_API_KEY",
        "LMSTUDIO_API_KEY", "VLLM_API_KEY", "LOCALAI_API_KEY", "TABBY_API_KEY",
        "HIPPO_LLM_PROVIDER", "HIPPO_OFFLINE", "HIPPO_MODEL",
        "HIPPO_MODEL_EXECUTOR", "HIPPO_MODEL_DREAMER", "HIPPO_MODEL_CRITIC",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_autodetect_returns_mock_when_nothing_configured(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    # Ensure no anthropic key is read from CONFIG either
    anthropic_key("")
    # Ollama not alive
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: False))
    assert _autodetect_provider() == "mock"


def test_autodetect_picks_anthropic_first(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("sk-ant-xxx")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: False))
    # anthropic comes before openai in AUTODETECT_ORDER
    assert _autodetect_provider() == "anthropic"


def test_autodetect_picks_openai_when_anthropic_absent(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: False))
    assert _autodetect_provider() == "openai"


def test_autodetect_falls_through_to_ollama(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("")
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: True))
    assert _autodetect_provider() == "ollama"


def test_autodetect_picks_china_provider(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("")
    monkeypatch.setenv("MOONSHOT_API_KEY", "sk-moonshot")
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: False))
    assert _autodetect_provider() == "moonshot"


# ---------------------------------------------------------------------------
# is_configured
# ---------------------------------------------------------------------------


def test_is_configured_anthropic(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("")
    assert is_configured("anthropic") is False
    anthropic_key("sk-ant")
    assert is_configured("anthropic") is True


def test_is_configured_ollama(monkeypatch):
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: True))
    assert is_configured("ollama") is True
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: False))
    assert is_configured("ollama") is False


def test_is_configured_mock_always_true():
    assert is_configured("mock") is True


def test_is_configured_openai_compat(monkeypatch):
    _wipe_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert is_configured("openai") is True
    monkeypatch.delenv("OPENAI_API_KEY")
    assert is_configured("openai") is False


def test_is_configured_alias_resolves(monkeypatch):
    _wipe_provider_env(monkeypatch)
    monkeypatch.setenv("MOONSHOT_API_KEY", "sk-moonshot")
    # "kimi" alias → moonshot
    assert is_configured("kimi") is True


def test_is_configured_unknown_provider_returns_false(monkeypatch):
    _wipe_provider_env(monkeypatch)
    assert is_configured("not-a-real-provider-xxx") is False


# ---------------------------------------------------------------------------
# list_providers — sanity
# ---------------------------------------------------------------------------


def test_list_providers_includes_anthropic_and_mock_and_ollama():
    out = list_providers()
    assert "anthropic" in out
    assert "ollama" in out
    assert "mock" in out
    assert "openai" in out
    # No duplicates
    assert len(out) == len(set(out))


# ---------------------------------------------------------------------------
# resolve_model — precedence
# ---------------------------------------------------------------------------


def test_resolve_model_stage_specific_wins(monkeypatch):
    _wipe_provider_env(monkeypatch)
    monkeypatch.setenv("HIPPO_MODEL", "global-model")
    monkeypatch.setenv("HIPPO_MODEL_EXECUTOR", "executor-special")
    assert resolve_model("executor") == "executor-special"


def test_resolve_model_global_when_no_stage(monkeypatch):
    _wipe_provider_env(monkeypatch)
    monkeypatch.setenv("HIPPO_MODEL", "global-model")
    assert resolve_model("dreamer") == "global-model"
    assert resolve_model("critic") == "global-model"


def test_resolve_model_anthropic_default_when_no_env(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("sk-ant")
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: False))
    # When Anthropic is the active provider, return CONFIG.model_<stage>.
    out = resolve_model("executor")
    assert out is not None
    assert isinstance(out, str)


def test_resolve_model_returns_none_for_non_anthropic(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: False))
    assert resolve_model("executor") is None


def test_resolve_model_with_forced_provider(monkeypatch):
    _wipe_provider_env(monkeypatch)
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "openai")
    # openai is not anthropic → returns None
    assert resolve_model("executor") is None


# ---------------------------------------------------------------------------
# MockLLM
# ---------------------------------------------------------------------------


def test_mock_llm_basic_complete():
    m = MockLLM(scripted=["hello", "world"])
    # Use a longer system prompt to ensure input_tokens > 0 (~ chars/4)
    r1 = m.complete(system="system instructions" * 10,
                    messages=[{"role": "user", "content": "hi"}])
    assert r1.text == "hello"
    assert r1.model == "mock"
    assert r1.input_tokens > 0
    r2 = m.complete(system="sys", messages=[{"role": "user", "content": "again"}])
    assert r2.text == "world"


def test_mock_llm_runs_out_of_scripts_returns_default():
    m = MockLLM(scripted=["once"])
    m.complete(system="", messages=[{"role": "user", "content": "x"}])
    r2 = m.complete(system="", messages=[{"role": "user", "content": "y"}])
    assert r2.text == "OK"


def test_mock_llm_records_calls():
    m = MockLLM()
    m.complete(system="sysA", messages=[{"role": "user", "content": "msg1"}],
               model="custom-model")
    assert len(m.calls) == 1
    assert m.calls[0]["system"] == "sysA"
    assert m.calls[0]["model"] == "custom-model"


def test_mock_llm_does_not_support_tools():
    assert MockLLM().supports_tools() is False


def test_mock_llm_response_total_tokens_property():
    r = LLMResponse(text="x", input_tokens=3, output_tokens=4,
                    model="mock", latency_s=0.1)
    assert r.total_tokens == 7


def test_llm_tool_response_helpers():
    tc = ToolCall(id="abc", name="echo", input={"x": 1})
    r = LLMToolResponse(text="t", tool_calls=[tc], input_tokens=10,
                        output_tokens=20, model="m", latency_s=0.0,
                        raw_content=[])
    assert r.has_tool_calls is True
    assert r.total_tokens == 30
    r2 = LLMToolResponse(text="", tool_calls=[], input_tokens=0,
                         output_tokens=0, model="m", latency_s=0.0,
                         raw_content=None)
    assert r2.has_tool_calls is False


# ---------------------------------------------------------------------------
# OpenAICompatLLM — complete + complete_with_tools (mocked SDK)
# ---------------------------------------------------------------------------


def _fake_chat_completion_response(text="hi", in_tok=10, out_tok=5,
                                     tool_calls=None, model="gpt-mock"):
    """Build a duck-typed OpenAI ChatCompletion-like object."""
    msg = MagicMock()
    msg.content = text
    msg.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = MagicMock(prompt_tokens=in_tok, completion_tokens=out_tok)
    resp.model = model
    return resp


def test_openai_compat_constructor_rejects_empty_key():
    with patch("openai.OpenAI"):
        with pytest.raises(LLMError):
            OpenAICompatLLM(api_key="", base_url="http://x", default_model="m",
                            provider_label="test")


def test_openai_compat_complete_returns_llm_response():
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_chat_completion_response(
        text="pong", in_tok=12, out_tok=3,
    )
    with patch("openai.OpenAI", return_value=fake_client):
        c = OpenAICompatLLM(api_key="sk-test", base_url="https://x",
                            default_model="gpt-x", provider_label="openai")
    resp = c.complete(system="sys", messages=[{"role": "user", "content": "hi"}],
                     model="gpt-y", temperature=0.3, max_tokens=200)
    assert isinstance(resp, LLMResponse)
    assert resp.text == "pong"
    assert resp.input_tokens == 12
    assert resp.output_tokens == 3
    assert resp.model == "gpt-y"


def test_openai_compat_supports_tools_default_true():
    with patch("openai.OpenAI"):
        c = OpenAICompatLLM(api_key="sk", base_url="https://x",
                            default_model="m", provider_label="groq")
    assert c.supports_tools() is True


def test_openai_compat_supports_tools_false_for_perplexity():
    with patch("openai.OpenAI"):
        c = OpenAICompatLLM(api_key="sk", base_url="https://x",
                            default_model="m", provider_label="perplexity")
    assert c.supports_tools() is False


def test_openai_compat_complete_with_tools_parses_function_call():
    """Native tool-calls via OpenAI SDK shape."""
    # Build mock tool-call objects (function-style)
    tc_obj = MagicMock()
    tc_obj.id = "call_123"
    tc_obj.function.name = "echo"
    tc_obj.function.arguments = '{"x": 42}'
    fake_resp = _fake_chat_completion_response(
        text="thinking…", tool_calls=[tc_obj],
    )
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_resp
    with patch("openai.OpenAI", return_value=fake_client):
        c = OpenAICompatLLM(api_key="sk-test", base_url="https://x",
                            default_model="gpt-mock", provider_label="openai")
    resp = c.complete_with_tools(
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"name": "echo", "description": "echo it",
                "input_schema": {"type": "object"}}],
    )
    assert isinstance(resp, LLMToolResponse)
    assert resp.text == "thinking…"
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "echo"
    assert resp.tool_calls[0].input == {"x": 42}
    assert resp.tool_calls[0].id == "call_123"


def test_openai_compat_complete_with_tools_no_calls_returns_empty():
    """When response has no tool_calls, return empty list — no crash on serialization."""
    fake_resp = _fake_chat_completion_response(text="just text", tool_calls=None)
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_resp
    with patch("openai.OpenAI", return_value=fake_client):
        c = OpenAICompatLLM(api_key="sk-test", base_url="https://x",
                            default_model="m", provider_label="openai")
    resp = c.complete_with_tools(system="sys", messages=[],
                                  tools=[{"name": "any",
                                          "input_schema": {"type": "object"}}])
    assert resp.tool_calls == []
    assert resp.text == "just text"


def test_openai_compat_complete_with_tools_invalid_json_args_returns_raw():
    """Malformed JSON in tool-call arguments → fallback to {_raw: ...}."""
    tc_obj = MagicMock()
    tc_obj.id = "call_x"
    tc_obj.function.name = "noisy"
    tc_obj.function.arguments = "not-json{{{"
    fake_resp = _fake_chat_completion_response(text="", tool_calls=[tc_obj])
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_resp
    with patch("openai.OpenAI", return_value=fake_client):
        c = OpenAICompatLLM(api_key="sk-test", base_url="https://x",
                            default_model="m", provider_label="openai")
    resp = c.complete_with_tools(system="sys", messages=[],
                                  tools=[{"name": "noisy",
                                          "input_schema": {"type": "object"}}])
    assert resp.tool_calls[0].input.get("_raw") == "not-json{{{"


def test_openai_compat_complete_with_tools_uses_input_schema_or_parameters():
    """If input_schema is missing, it falls back to parameters."""
    fake_resp = _fake_chat_completion_response(text="ok", tool_calls=None)
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_resp
    with patch("openai.OpenAI", return_value=fake_client):
        c = OpenAICompatLLM(api_key="sk-test", base_url="https://x",
                            default_model="m", provider_label="openai")
    c.complete_with_tools(system="sys", messages=[], tools=[
        {"name": "no_schema", "parameters": {"type": "object",
                                              "properties": {"a": {"type": "string"}}}},
    ])
    # Inspect the call to confirm parameters made it through
    args, kwargs = fake_client.chat.completions.create.call_args
    sent_tools = kwargs["tools"]
    assert sent_tools[0]["function"]["parameters"]["properties"]["a"]["type"] == "string"


# ---------------------------------------------------------------------------
# OllamaLLM — alive() probe via respx
# ---------------------------------------------------------------------------


@respx.mock
def test_ollama_alive_true_when_tags_responds_200(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": []}),
    )
    assert OllamaLLM.alive() is True


@respx.mock
def test_ollama_alive_false_when_unreachable():
    respx.get("http://localhost:11434/api/tags").mock(
        side_effect=httpx.ConnectError("nope"),
    )
    assert OllamaLLM.alive() is False


@respx.mock
def test_ollama_alive_uses_explicit_url():
    respx.get("http://example.test:9999/api/tags").mock(
        return_value=httpx.Response(200, json={"models": []}),
    )
    assert OllamaLLM.alive("http://example.test:9999") is True


def test_ollama_supports_tools_default_true(monkeypatch):
    monkeypatch.delenv("HIPPO_OLLAMA_TOOLS", raising=False)
    o = OllamaLLM()
    assert o.supports_tools() is True


def test_ollama_supports_tools_disabled_via_env(monkeypatch):
    o = OllamaLLM()
    for val in ("0", "false", "no", "off", "FALSE"):
        monkeypatch.setenv("HIPPO_OLLAMA_TOOLS", val)
        assert o.supports_tools() is False


# ---------------------------------------------------------------------------
# get_llm + _build entry points
# ---------------------------------------------------------------------------


def test_get_llm_returns_mock_when_use_mock_true():
    out = get_llm(use_mock=True)
    assert isinstance(out, MockLLM)


def test_get_llm_offline_env_returns_mock(monkeypatch):
    _wipe_provider_env(monkeypatch)
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    out = get_llm()
    assert isinstance(out, MockLLM)


def test_get_llm_use_mock_false_raises_if_no_provider(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("")
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: False))
    with pytest.raises(LLMError):
        get_llm(use_mock=False)


def test_get_llm_autodetect_to_mock_when_nothing_available(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("")
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: False))
    out = get_llm()
    assert isinstance(out, MockLLM)


def test_build_unknown_provider_raises():
    with pytest.raises(LLMError):
        _build("not-a-provider-xx")


def test_build_mock():
    assert isinstance(_build("mock"), MockLLM)


def test_build_openai_compat_with_base_url_override(monkeypatch):
    _wipe_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://my-proxy.example/v1")
    fake_client = MagicMock()
    with patch("openai.OpenAI", return_value=fake_client) as mocked:
        out = _build("openai")
    # Verify base_url override was honoured
    _, kw = mocked.call_args
    assert kw["base_url"] == "https://my-proxy.example/v1"
    assert isinstance(out, OpenAICompatLLM)


# ---------------------------------------------------------------------------
# list_models_for_provider
# ---------------------------------------------------------------------------


def test_list_models_for_provider_mock():
    out = list_models_for_provider("mock")
    assert any(m["id"] == "mock-model" for m in out)


def test_list_models_for_provider_unknown_raises():
    with pytest.raises(LLMError):
        list_models_for_provider("totally-bogus-xx")


def test_list_models_for_provider_no_key(monkeypatch):
    _wipe_provider_env(monkeypatch)
    with pytest.raises(LLMError):
        list_models_for_provider("openai")


@respx.mock
def test_list_models_for_provider_openai_compat_normalises(monkeypatch):
    _wipe_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    respx.get("https://api.openai.com/v1/models").mock(
        return_value=httpx.Response(200, json={
            "data": [
                {"id": "gpt-4o", "owned_by": "openai", "object": "model"},
                {"id": "gpt-4o-mini", "owned_by": "openai", "object": "model"},
            ],
        }),
    )
    out = list_models_for_provider("openai")
    assert {m["id"] for m in out} == {"gpt-4o", "gpt-4o-mini"}
    # owned_by is preserved (extra metadata)
    assert out[0]["owned_by"] == "openai"


@respx.mock
def test_list_models_for_provider_handles_string_entries(monkeypatch):
    _wipe_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    respx.get("https://api.openai.com/v1/models").mock(
        return_value=httpx.Response(200, json={"data": ["just-a-string-model"]}),
    )
    out = list_models_for_provider("openai")
    assert out[0]["id"] == "just-a-string-model"


@respx.mock
def test_list_models_for_provider_ollama(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={
            "models": [
                {
                    "name": "qwen2.5:7b",
                    "size": 4_000_000_000,
                    "modified_at": "2025-01-01",
                    "details": {"family": "qwen", "parameter_size": "7B",
                                 "quantization_level": "Q4_0"},
                },
            ],
        }),
    )
    out = list_models_for_provider("ollama")
    assert out[0]["id"] == "qwen2.5:7b"
    assert out[0]["family"] == "qwen"
    assert out[0]["param_size"] == "7B"


def test_list_models_anthropic_no_key_raises(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("")
    with pytest.raises(LLMError):
        list_models_for_provider("anthropic")


# ---------------------------------------------------------------------------
# scan_all_providers
# ---------------------------------------------------------------------------


def test_scan_all_providers_marks_unconfigured(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("")
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: False))
    report = scan_all_providers(timeout=0.5)
    # mock excluded
    assert "mock" not in report
    # All providers reported, all unconfigured
    assert all(v["configured"] is False for v in report.values())


def test_scan_all_providers_handles_error_gracefully(monkeypatch):
    _wipe_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(OllamaLLM, "alive", staticmethod(lambda *a, **kw: False))
    # Make list_models raise
    monkeypatch.setattr(llm_mod, "list_models_for_provider",
                         lambda name, timeout=10.0: (_ for _ in ()).throw(
                             RuntimeError("boom"),
                         ))
    report = scan_all_providers(timeout=0.5)
    # OpenAI is configured but the scan errored — report has "error" key
    assert report["openai"]["configured"] is True
    assert "boom" in report["openai"]["error"]


# ---------------------------------------------------------------------------
# FallbackLLM extra: edge cases not covered by test_fallback.py
# ---------------------------------------------------------------------------


class _StubLLM:
    def __init__(self, name, raises=None, supports=True):
        self.name = name
        self.raises = raises
        self._supports = supports
        self.calls = 0

    def supports_tools(self):
        return self._supports

    def complete(self, system, messages, model=None, temperature=0.0,
                 max_tokens=None, stop_sequences=None):
        self.calls += 1
        if self.raises:
            raise self.raises
        return LLMResponse(text=f"ok-{self.name}", input_tokens=1,
                           output_tokens=1, model=self.name, latency_s=0.0)

    def complete_with_tools(self, system, messages, tools, model=None,
                             temperature=0.0, max_tokens=None):
        self.calls += 1
        if self.raises:
            raise self.raises
        return LLMToolResponse(
            text=f"tool-{self.name}", tool_calls=[],
            input_tokens=1, output_tokens=1, model=self.name,
            latency_s=0.0, raw_content=[],
        )


def test_fallback_supports_tools_aggregate():
    a = _StubLLM("a", supports=False)
    b = _StubLLM("b", supports=True)
    chain = FallbackLLM(a, [b])
    assert chain.supports_tools() is True
    chain2 = FallbackLLM(_StubLLM("a", supports=False),
                         [_StubLLM("b", supports=False)])
    assert chain2.supports_tools() is False


def test_fallback_is_recoverable_classifier():
    """Each error string in the recoverable set should map to True."""
    cases = ("429 rate limit", "503 service unavailable", "timeout",
             "connection error", "quota exceeded", "billing limit",
             "credit out", "overload", "504 gateway")
    for msg in cases:
        assert FallbackLLM._is_recoverable(RuntimeError(msg)) is True
    not_recoverable = ("syntax error", "bad input", "ValueError",
                       "no such model", "invalid_request_error")
    for msg in not_recoverable:
        assert FallbackLLM._is_recoverable(RuntimeError(msg)) is False


def test_fallback_complete_raises_when_all_fail():
    a = _StubLLM("a", raises=RuntimeError("429 rate"))
    b = _StubLLM("b", raises=RuntimeError("503"))
    chain = FallbackLLM(a, [b])
    with pytest.raises(RuntimeError):
        chain.complete(system="x", messages=[{"role": "user", "content": "y"}])
    # Both attempted
    assert a.calls == 1 and b.calls == 1


def test_fallback_complete_with_tools_raises_when_no_supporting_client():
    a = _StubLLM("a", supports=False)
    b = _StubLLM("b", supports=False)
    chain = FallbackLLM(a, [b])
    with pytest.raises(LLMError):
        chain.complete_with_tools(
            system="x",
            messages=[{"role": "user", "content": "y"}],
            tools=[{"name": "t", "input_schema": {"type": "object"}}],
        )


# ---------------------------------------------------------------------------
# Anthropic LLM error paths
# ---------------------------------------------------------------------------


def test_anthropic_constructor_no_key_raises(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("")
    with pytest.raises(LLMError):
        AnthropicLLM()


def test_anthropic_constructor_key_param_overrides(monkeypatch, anthropic_key):
    _wipe_provider_env(monkeypatch)
    anthropic_key("")
    fake_client = MagicMock()
    with patch("anthropic.Anthropic", return_value=fake_client) as mocked:
        c = AnthropicLLM(api_key="sk-explicit")
    assert c.client is fake_client
    _, kw = mocked.call_args
    assert kw["api_key"] == "sk-explicit"


def test_anthropic_complete_strips_temperature_for_opus_47(monkeypatch, anthropic_key):
    """When model is opus-4-7+, temperature MUST NOT be passed."""
    _wipe_provider_env(monkeypatch)
    anthropic_key("sk-x")
    fake_client = MagicMock()
    fake_resp = MagicMock()
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "OK"
    fake_resp.content = [text_block]
    fake_resp.usage = MagicMock(input_tokens=5, output_tokens=2)
    fake_client.messages.create.return_value = fake_resp
    with patch("anthropic.Anthropic", return_value=fake_client):
        c = AnthropicLLM()
    resp = c.complete(system="sys", messages=[{"role": "user", "content": "x"}],
                       model="claude-opus-4-7", temperature=0.5)
    _, kwargs = fake_client.messages.create.call_args
    assert "temperature" not in kwargs
    assert resp.text == "OK"
    assert resp.input_tokens == 5
