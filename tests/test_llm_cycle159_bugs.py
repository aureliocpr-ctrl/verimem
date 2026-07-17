"""Cycle 159.7 (2026-05-19) — empirical bugs found by sonnet-duo scaling test.

These tests pin two real bugs in ``engram/llm.py`` that the cycle-159.7
scaling experiment (Arm B, team `cycle159-scale-test-duo`, eve+frank
sonnet duo) found in 5 min via the Real-Collaboration Charter. The
single-sonnet Arm A (acce69bc29ba97b19) missed BUG-B entirely and
included two smell-but-not-bug claims that the duo rejected.

Tests are written RED-first: pre-fix they fail, post-fix they pass.
See fact `591a8ea5f8ce` for the full experimental log.
"""
from __future__ import annotations

from unittest.mock import patch

# -----------------------------------------------------------------------
# BUG-A — ClaudeCLILLM.complete prompt assembly: system messages from
# `messages` list used to land at index 0 via `parts.insert(0, ...)`,
# pushing the primary `system` arg out of position.
# -----------------------------------------------------------------------


def test_claude_cli_prompt_keeps_system_param_in_front_with_extra_system_msgs(
    monkeypatch,
) -> None:
    """The primary ``system`` arg must remain the first block of the
    serialised prompt even when the messages list contains additional
    role=system entries.
    """
    from verimem.llm import ClaudeCLILLM

    captured: dict[str, str] = {}

    class _FakeResult:
        returncode = 0
        stdout = (
            '{"is_error": false, "result": "ok", '
            '"usage": {"input_tokens": 1, "output_tokens": 1}, '
            '"modelUsage": {"claude-cli": {}}}'
        )
        stderr = ""

    def fake_run(cmd, *, input, **_kw):  # noqa: A002 — match subprocess.run
        captured["prompt"] = input
        return _FakeResult()

    monkeypatch.setattr("subprocess.run", fake_run)

    client = ClaudeCLILLM(claude_bin="claude", timeout_s=5)
    client.complete(
        system="PRIMARY-SYSTEM",
        messages=[
            {"role": "system", "content": "EXTRA-1"},
            {"role": "user", "content": "user-question"},
            {"role": "system", "content": "EXTRA-2"},
        ],
    )

    prompt = captured["prompt"]
    # Find the index of each marker in the assembled prompt.
    idx_primary = prompt.index("PRIMARY-SYSTEM")
    idx_extra1 = prompt.index("EXTRA-1")
    idx_extra2 = prompt.index("EXTRA-2")
    idx_user = prompt.index("user-question")

    # Cycle 159.7 invariant: primary system FIRST, then extras in their
    # original order, then user turns. Pre-fix the prompt order was
    # ["EXTRA-2", "EXTRA-1", "PRIMARY-SYSTEM", "user-question"] because
    # of repeated insert(0, ...).
    assert idx_primary < idx_extra1, (
        f"primary system must precede EXTRA-1 in prompt; got {prompt!r}"
    )
    assert idx_extra1 < idx_extra2, (
        f"EXTRA-1 must precede EXTRA-2 (preserve list order); "
        f"got {prompt!r}"
    )
    assert idx_extra2 < idx_user, (
        f"all system blocks must precede user turn; got {prompt!r}"
    )


# -----------------------------------------------------------------------
# BUG-B — MCPSamplingLLM in_tokens char-proxy estimate ignored the
# `system` parameter, undercounting input tokens systematically.
# -----------------------------------------------------------------------


def test_mcp_sampling_in_tokens_includes_system_chars(
    monkeypatch, tmp_path,
) -> None:
    """``in_tokens`` must count the system prompt characters too — checked
    against the REAL ``LLMResponse`` produced by the runtime accounting,
    not by grepping the source.

    BUG-B: pre-fix ``in_chars = sum(len(content) for m in messages)``
    ignored ``system``. With a 4000-char system + 400-char user message
    the runtime ``input_tokens`` was 100 (400/4); post-fix it must be
    1100 (4400/4). This test drives ``MCPSamplingLLM._async_complete``
    end-to-end with a hermetic fake MCP session (no network, no API key,
    no real ``loop``) and asserts on the returned ``input_tokens``.
    Falsifiable: if the bug returns, ``input_tokens`` drops back to 100.
    """
    import asyncio
    import pathlib
    from types import SimpleNamespace

    from verimem.llm import MCPSamplingLLM

    # Redirect the module's forensic debug-log write to a throwaway dir so
    # the test stays hermetic and never touches the real ~/.verimem.
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    captured: dict[str, object] = {}

    class _FakeSession:
        """Minimal stand-in for the MCP ServerSession.

        ``_async_complete`` only calls ``create_message(**kwargs)`` and
        reads ``.content.text`` + ``.model`` off the result.
        """

        async def create_message(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                content=SimpleNamespace(type="text", text="RESP"),
                model="fake-model",
            )

    client = MCPSamplingLLM(loop=None, session=_FakeSession())

    system = "S" * 4000
    messages = [{"role": "user", "content": "U" * 400}]

    resp = asyncio.run(
        client._async_complete(
            system, messages,
            temperature=0.0, max_tokens=64, stop_sequences=None,
        )
    )

    # The fake session must have actually received the system prompt
    # (sanity: the value under test really is wired into the request).
    assert captured.get("system_prompt") == system

    # Runtime invariant: (4000 + 400) // 4 == 1100. Pre-fix this was 100
    # because `system` was excluded from in_chars.
    assert resp.input_tokens == 1100, (
        f"input_tokens must count system chars; got {resp.input_tokens} "
        f"(pre-fix bug value would be 100)"
    )
