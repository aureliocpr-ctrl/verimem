"""OllamaLLM falls back to its configured default model on a 404 (model not found).

Real bug (2026-06-06, live `engram run` in air-gap mode): the wake loop passed a
provider-incoherent model name to OllamaLLM — a cloud `model_executor`
('claude-opus-4-7') projected from settings while HIPPO_LLM_PROVIDER=ollama —
so Ollama returned 404 and the WHOLE agent run crashed (after 3 retries on the
bad name). Fix: on 404, retry once with the configured local default
(OLLAMA_MODEL / default_model). Hermetic — httpx client monkeypatched.
"""
from __future__ import annotations

import httpx

from engram.llm import OllamaLLM


class _Resp:
    def __init__(self, status: int, payload: dict | None = None) -> None:
        self.status_code = status
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            req = httpx.Request("POST", "http://localhost:11434/api/chat")
            raise httpx.HTTPStatusError(
                f"{self.status_code}", request=req,
                response=httpx.Response(self.status_code, request=req),
            )

    def json(self) -> dict:
        return self._payload


def _make(monkeypatch, available: set[str]):
    llm = OllamaLLM(default_model="qwen2.5:1.5b")
    calls: list[str] = []

    def post(url, json=None, **k):
        m = (json or {}).get("model")
        calls.append(m)
        if m in available:
            return _Resp(200, {"message": {"content": "ok"},
                               "prompt_eval_count": 1, "eval_count": 1})
        return _Resp(404)

    monkeypatch.setattr(llm._client, "post", post)
    return llm, calls


def test_complete_falls_back_to_default_on_404(monkeypatch):
    llm, calls = _make(monkeypatch, available={"qwen2.5:1.5b"})
    r = llm.complete(system="s", messages=[{"role": "user", "content": "hi"}],
                     model="claude-opus-4-7")
    assert r.text == "ok"
    assert calls == ["claude-opus-4-7", "qwen2.5:1.5b"], calls


def test_complete_with_tools_falls_back_on_404(monkeypatch):
    llm, calls = _make(monkeypatch, available={"qwen2.5:1.5b"})
    llm.complete_with_tools(
        system="s", messages=[{"role": "user", "content": "hi"}],
        tools=[{"name": "t", "description": "d", "input_schema": {"type": "object"}}],
        model="gpt-4o",
    )
    assert calls[0] == "gpt-4o" and "qwen2.5:1.5b" in calls


def test_no_fallback_when_model_available(monkeypatch):
    llm, calls = _make(monkeypatch, available={"qwen2.5:1.5b"})
    llm.complete(system="s", messages=[{"role": "user", "content": "hi"}],
                 model="qwen2.5:1.5b")
    assert calls == ["qwen2.5:1.5b"]


def test_fallback_picks_installed_chat_model_skipping_embed(monkeypatch):
    # default_model is NOT installed; the server has an embed model + a chat
    # model — fall back to the installed CHAT model (skip the embedding one).
    llm = OllamaLLM(default_model="llama3.1")  # not installed
    calls: list[str] = []

    def get(url, **k):
        return _Resp(200, {"models": [
            {"name": "nomic-embed-text:latest"},
            {"name": "qwen2.5:7b-instruct"},
        ]})

    def post(url, json=None, **k):
        m = (json or {}).get("model")
        calls.append(m)
        if m == "qwen2.5:7b-instruct":
            return _Resp(200, {"message": {"content": "ok"},
                               "prompt_eval_count": 1, "eval_count": 1})
        return _Resp(404)

    monkeypatch.setattr(llm._client, "get", get)
    monkeypatch.setattr(llm._client, "post", post)
    r = llm.complete(system="s", messages=[{"role": "user", "content": "hi"}],
                     model="claude-opus-4-7")
    assert r.text == "ok"
    assert "qwen2.5:7b-instruct" in calls
    assert "nomic-embed-text:latest" not in calls
