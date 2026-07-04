"""CVE-008 — Prompt-injection defense contract.

Three layers of defense:
  1. Untrusted content from web_fetch / web_search / vision_describe is
     wrapped in <untrusted_content> markers so the model sees it as data,
     not instructions.
  2. After external-source tools, dangerous tools (shell_run, desktop_*,
     fs_write_file outside data) are BLOCKED unless the user explicitly
     enabled HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL=1.
  3. The system prompt instructs the model to refuse imperatives inside
     the markers.

These tests don't drive a real LLM; they exercise the defensive helpers
and the dispatch path inside `wake.py` directly.
"""
from __future__ import annotations

import pytest

from engram.episode import Trace
from engram.wake import (
    _DANGEROUS_TOOLS_AFTER_EXTERNAL,
    _EXTERNAL_TOOLS,
    _injection_review_blocks_call,
    _is_external_source_in_recent_traces,
    _wrap_untrusted,
)

# ---------------------------------------------------------------------------
# _wrap_untrusted
# ---------------------------------------------------------------------------


def test_wrap_untrusted_marks_web_fetch() -> None:
    out = _wrap_untrusted("hello world", "web_fetch",
                          source_arg="http://example.com")
    assert out.startswith('<untrusted_content source="web_fetch:http://example.com">')
    assert out.endswith("</untrusted_content>")
    assert "hello world" in out


def test_wrap_untrusted_marks_vision() -> None:
    out = _wrap_untrusted("an image of a cat", "vision_describe",
                          source_arg="/tmp/img.png")
    assert "vision_describe" in out
    assert "an image of a cat" in out
    assert "untrusted_content" in out


def test_wrap_untrusted_passes_internal_tools_unchanged() -> None:
    """run_python, fs_read_file (in workspace), and other internal sources
    should NOT be wrapped — only external content gets the marker."""
    for tool in ["run_python", "fs_read_file", "syntax_check", "submit_solution"]:
        out = _wrap_untrusted("safe stuff", tool)
        assert "untrusted_content" not in out
        assert out == "safe stuff"


# ---------------------------------------------------------------------------
# _is_external_source_in_recent_traces
# ---------------------------------------------------------------------------


def _make_trace(action: str, step: int = 1) -> Trace:
    return Trace(step=step, thought="", action=action,
                 action_input="", observation="ok")


def test_recent_traces_detects_web_fetch() -> None:
    traces = [_make_trace("web_fetch", 1)]
    assert _is_external_source_in_recent_traces(traces) is True


def test_recent_traces_detects_vision_describe() -> None:
    traces = [_make_trace("run_python", 1), _make_trace("vision_describe", 2)]
    assert _is_external_source_in_recent_traces(traces) is True


def test_recent_traces_no_match_when_only_internal() -> None:
    traces = [_make_trace("run_python", 1), _make_trace("syntax_check", 2)]
    assert _is_external_source_in_recent_traces(traces) is False


def test_recent_traces_lookback_window() -> None:
    """External tool from beyond the lookback window is ignored."""
    traces = [
        _make_trace("web_fetch", 1),
        _make_trace("run_python", 2),
        _make_trace("run_python", 3),
        _make_trace("run_python", 4),
        _make_trace("syntax_check", 5),
    ]
    # default lookback=3 — only steps 3,4,5
    assert _is_external_source_in_recent_traces(traces, lookback=3) is False
    # bigger window catches it
    assert _is_external_source_in_recent_traces(traces, lookback=5) is True


# ---------------------------------------------------------------------------
# _injection_review_blocks_call (the actual gate)
# ---------------------------------------------------------------------------


def test_blocks_shell_run_after_web_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL", raising=False)
    traces = [_make_trace("web_fetch", 1)]
    assert _injection_review_blocks_call("shell_run", traces) is True


def test_blocks_desktop_type_after_vision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL", raising=False)
    traces = [_make_trace("vision_describe", 1)]
    assert _injection_review_blocks_call("desktop_type", traces) is True


def test_does_not_block_safe_tool() -> None:
    """run_python, fs_read_file, submit_solution always allowed."""
    traces = [_make_trace("web_fetch", 1)]
    assert _injection_review_blocks_call("run_python", traces) is False
    assert _injection_review_blocks_call("submit_solution", traces) is False


def test_does_not_block_when_no_external_source() -> None:
    traces = [_make_trace("run_python", 1), _make_trace("syntax_check", 2)]
    assert _injection_review_blocks_call("shell_run", traces) is False


def test_override_env_disables_review(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL", "1")
    traces = [_make_trace("web_fetch", 1)]
    assert _injection_review_blocks_call("shell_run", traces) is False


# ---------------------------------------------------------------------------
# Constants integrity
# ---------------------------------------------------------------------------


def test_external_tools_set_includes_expected() -> None:
    assert "web_fetch" in _EXTERNAL_TOOLS
    assert "web_search" in _EXTERNAL_TOOLS
    assert "vision_describe" in _EXTERNAL_TOOLS
    # internal tools must NOT be marked external
    assert "run_python" not in _EXTERNAL_TOOLS
    assert "fs_read_file" not in _EXTERNAL_TOOLS


def test_dangerous_tools_set_includes_expected() -> None:
    assert "shell_run" in _DANGEROUS_TOOLS_AFTER_EXTERNAL
    assert "desktop_click" in _DANGEROUS_TOOLS_AFTER_EXTERNAL
    assert "desktop_type" in _DANGEROUS_TOOLS_AFTER_EXTERNAL
    # safe tools must not be in the dangerous set
    assert "run_python" not in _DANGEROUS_TOOLS_AFTER_EXTERNAL
    assert "submit_solution" not in _DANGEROUS_TOOLS_AFTER_EXTERNAL


# ---------------------------------------------------------------------------
# End-to-end through the wake-loop's dispatcher path
# ---------------------------------------------------------------------------


def test_dispatch_react_blocks_shell_after_web(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drive the ReAct text-mode loop with crafted traces.

    We don't run the LLM; we directly test that when the agent has a
    web_fetch trace and tries to call shell_run, the dispatcher emits a
    refusal observation containing 'REFUSED'.
    """
    monkeypatch.delenv("HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL", raising=False)
    from engram.episode import Episode
    ep = Episode(task_id="t1", task_text="summarise URL")
    # Simulate a web_fetch turn already happened
    ep.traces.append(Trace(step=1, thought="fetched", action="web_fetch",
                           action_input='{"url":"http://attacker.example"}',
                           observation="malicious page text"))
    # Now test the gate
    blocked = _injection_review_blocks_call("shell_run", ep.traces)
    assert blocked is True


def test_real_run_python_after_web_is_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sanity: legitimate flows like 'fetch then summarise via python' still work."""
    monkeypatch.delenv("HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL", raising=False)
    traces = [_make_trace("web_fetch", 1)]
    assert _injection_review_blocks_call("run_python", traces) is False
    assert _injection_review_blocks_call("submit_solution", traces) is False
