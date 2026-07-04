"""OllamaLLM must keep the local model WARM (keep_alive) to avoid the cold-load
cliff in local/air-gap mode.

Empirical RED (2026-06-06, live qwen2.5:1.5b on CPU): first call after the model
unloaded = ~97s; warm = 0.5-2.8s. Ollama's default keep_alive is 5 min, so a
memory system that calls the LLM intermittently (gate-judge per write, periodic
consolidate) hit the 97s cliff on every idle. Fix: send keep_alive on every
request (env HIPPO_OLLAMA_KEEP_ALIVE, default 30m).

Hermetic: the httpx client is monkeypatched — no Ollama server, no network.
"""
from __future__ import annotations

from engram.llm import OllamaLLM, _ollama_keep_alive


class _FakeResp:
    def raise_for_status(self) -> None:  # noqa: D401
        return None

    def json(self) -> dict:
        return {"message": {"content": "ok"}, "prompt_eval_count": 1, "eval_count": 1}


def _capturing_post(captured: dict):
    def fake_post(url, json=None, **kw):
        captured["url"] = url
        captured["body"] = json
        return _FakeResp()
    return fake_post


def test_complete_sends_keep_alive(monkeypatch):
    llm = OllamaLLM()
    cap: dict = {}
    monkeypatch.setattr(llm._client, "post", _capturing_post(cap))
    llm.complete(system="s", messages=[{"role": "user", "content": "hi"}], model="m")
    assert "keep_alive" in cap["body"], "Ollama request must set keep_alive (cold-load fix)"
    assert cap["body"]["keep_alive"], "keep_alive must be non-empty"


def test_complete_with_tools_sends_keep_alive(monkeypatch):
    llm = OllamaLLM()
    cap: dict = {}
    monkeypatch.setattr(llm._client, "post", _capturing_post(cap))
    llm.complete_with_tools(
        system="s", messages=[{"role": "user", "content": "hi"}],
        tools=[{"name": "t", "description": "d", "input_schema": {"type": "object"}}],
        model="m",
    )
    assert cap["body"].get("keep_alive"), "tool calls must also keep the model warm"


def test_keep_alive_env_override(monkeypatch):
    monkeypatch.setenv("HIPPO_OLLAMA_KEEP_ALIVE", "-1")
    assert _ollama_keep_alive() == "-1"
    llm = OllamaLLM()
    cap: dict = {}
    monkeypatch.setattr(llm._client, "post", _capturing_post(cap))
    llm.complete(system="s", messages=[{"role": "user", "content": "hi"}], model="m")
    assert cap["body"]["keep_alive"] == "-1"


def test_default_keep_alive_is_warm(monkeypatch):
    monkeypatch.delenv("HIPPO_OLLAMA_KEEP_ALIVE", raising=False)
    # Must NOT be Ollama's 5-min default that causes the 97s reload.
    assert _ollama_keep_alive() == "30m"
