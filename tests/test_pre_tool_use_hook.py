"""Cycle 169 (2026-05-20) — PreToolUse hook that consumes StepInjector.

ROADMAP-2026-05-19.md Priority 1 #2: closes the critic finding from PR
#108 ("StepInjector dead code = no MCP wrapper / no consumer"). This
file pins the contract of ``engram.hooks.pre_tool_use``:

  * ``extract_step_text(tool_name, tool_input) → str`` — pure function,
    returns the per-tool sub-goal we want to recall against.
  * ``run(payload, agent_factory=None) → str`` — pure function, returns
    the ``<engram-step-recall>...</engram-step-recall>`` banner or
    empty string when nothing useful to inject.
  * ``main_stdin_stdout(stdin=None, stdout=None) → int`` — CLI entry,
    reads JSON from stdin, writes banner to stdout, exits 0 on success
    or graceful no-op.

RED→GREEN — this file must fail import on ``engram.hooks.pre_tool_use``
(does not yet exist on this branch).
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

# RED MARKER
from engram.hooks.pre_tool_use import (
    extract_step_text,
    main_stdin_stdout,
    run,
)
from engram.memory import EpisodicMemory
from engram.semantic import Fact, SemanticMemory


@pytest.fixture
def populated_sm(tmp_path: Path) -> SemanticMemory:
    """A SemanticMemory pre-seeded with facts that match specific
    queries so the hook can produce non-empty banners deterministically.
    """
    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    sm.store(Fact(
        proposition="pytest auto_consolidate orchestrator avoids self-loop",
        topic="project/hippoagent/cycle170-arm-d-self-loop-fix-pr109",
        confidence=0.95,
        source_episodes=["ep_seed_1"],
        trigger_keywords=["pytest", "consolidate", "self-loop", "edge"],
        status="model_claim",
    ))
    sm.store(Fact(
        proposition="ruff check engram/ catches I001 import sort errors",
        topic="lessons/ci/ruff-import-sort",
        confidence=0.9,
        source_episodes=["ep_seed_2"],
        trigger_keywords=["ruff", "import", "sort", "lint"],
        status="model_claim",
    ))
    return sm


@pytest.fixture
def agent_factory(populated_sm: SemanticMemory, tmp_path: Path):
    """A factory the hook can call to obtain a lightweight agent shim
    carrying the populated SemanticMemory. The hook MUST NOT instantiate
    a full HippoAgent under test — agent_factory is the seam for DI.
    """
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")

    class _AgentShim:
        semantic = populated_sm
        memory = mem

    def _factory() -> _AgentShim:
        return _AgentShim()
    return _factory


# -----------------------------------------------------------------------
# extract_step_text — pure per-tool extractor
# -----------------------------------------------------------------------

class TestExtractStepText:
    """One small extractor per common Claude Code tool. Unknown tools
    return empty so the hook is silent on them."""

    def test_bash_uses_command(self) -> None:
        assert extract_step_text(
            "Bash", {"command": "pytest tests/test_x.py -v"},
        ) == "pytest tests/test_x.py -v"

    def test_edit_uses_file_path_with_verb(self) -> None:
        s = extract_step_text(
            "Edit", {"file_path": "engram/foo.py", "old_string": "x"},
        )
        assert "edit" in s.lower()
        assert "engram/foo.py" in s

    def test_write_uses_file_path_with_verb(self) -> None:
        s = extract_step_text(
            "Write", {"file_path": "engram/bar.py", "content": "..."},
        )
        assert "write" in s.lower()
        assert "engram/bar.py" in s

    def test_grep_uses_pattern(self) -> None:
        s = extract_step_text(
            "Grep", {"pattern": "auto_consolidate", "path": "engram/"},
        )
        assert "auto_consolidate" in s

    def test_glob_uses_pattern(self) -> None:
        s = extract_step_text(
            "Glob", {"pattern": "**/*.py"},
        )
        assert "**/*.py" in s

    def test_read_uses_file_path(self) -> None:
        s = extract_step_text(
            "Read", {"file_path": "engram/semantic.py"},
        )
        assert "engram/semantic.py" in s

    def test_unknown_tool_returns_empty(self) -> None:
        assert extract_step_text(
            "SomeRandomTool", {"foo": "bar"},
        ) == ""

    def test_hippoagent_mcp_tool_returns_empty(self) -> None:
        """Cycle 169 anti-loop: hook MUST NOT recall before calling its
        own backing store. Any tool whose name starts with
        ``mcp__hippoagent__`` is dropped (the host would otherwise spam
        proactive injections for its own MCP calls).
        """
        assert extract_step_text(
            "mcp__hippoagent__hippo_remember",
            {"proposition": "x"},
        ) == ""
        assert extract_step_text(
            "mcp__hippoagent__hippo_facts_search",
            {"query": "x"},
        ) == ""

    def test_empty_tool_input_returns_empty(self) -> None:
        assert extract_step_text("Bash", {}) == ""
        assert extract_step_text("Bash", None) == ""  # type: ignore[arg-type]

    def test_long_step_truncated_at_500(self) -> None:
        cmd = "echo " + ("x" * 1000)
        out = extract_step_text("Bash", {"command": cmd})
        assert len(out) <= 500


# -----------------------------------------------------------------------
# run — full hook logic with injected agent
# -----------------------------------------------------------------------

class TestRun:
    """``run`` consumes the Claude Code PreToolUse payload + optional
    agent factory, returns the banner string (or empty)."""

    def test_no_payload_returns_empty(self) -> None:
        assert run({}, agent_factory=lambda: None) == ""

    def test_unknown_tool_returns_empty(self, agent_factory) -> None:
        out = run(
            {"tool_name": "UnknownTool", "tool_input": {"foo": "x"}},
            agent_factory=agent_factory,
        )
        assert out == ""

    def test_hippoagent_tool_returns_empty_no_loop(
        self, agent_factory,
    ) -> None:
        """Anti-loop: own MCP tools never trigger a recall."""
        out = run(
            {
                "tool_name": "mcp__hippoagent__hippo_facts_search",
                "tool_input": {"query": "anything"},
            },
            agent_factory=agent_factory,
        )
        assert out == ""

    def test_short_step_returns_empty(self, agent_factory) -> None:
        out = run(
            {"tool_name": "Bash", "tool_input": {"command": "ls"}},
            agent_factory=agent_factory,
        )
        assert out == ""

    def test_relevant_step_emits_banner(self, agent_factory) -> None:
        """A Bash command whose keywords match a seeded fact must yield
        a non-empty banner with the fact's proposition.
        """
        out = run(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "pytest tests/test_consolidate.py "
                               "-k 'self loop edge'",
                },
            },
            agent_factory=agent_factory,
        )
        # Banner shape
        assert "<engram-step-recall" in out
        assert "</engram-step-recall>" in out
        # Contains at least one of the seeded facts.
        assert (
            "auto_consolidate" in out or "self-loop" in out
        )

    def test_banner_includes_tool_name_and_hit_count(
        self, agent_factory,
    ) -> None:
        out = run(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "ruff check engram/ for import sort lint",
                },
            },
            agent_factory=agent_factory,
        )
        assert "tool=Bash" in out
        assert "hits=" in out

    def test_no_match_returns_empty(self, agent_factory) -> None:
        """A step text with zero keyword overlap and weak semantic match
        must produce no banner (empty string), not a stub.
        """
        out = run(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "echo zzz qqq unrelated gibberish gibberish",
                },
            },
            agent_factory=agent_factory,
        )
        assert out == ""

    def test_agent_factory_returning_none_is_silent(self) -> None:
        """If the host has no HippoAgent available (e.g. data dir
        missing), the hook degrades to silent — no exception, no
        banner.
        """
        out = run(
            {"tool_name": "Bash", "tool_input": {
                "command": "pytest tests/test_consolidate.py"}},
            agent_factory=lambda: None,
        )
        assert out == ""

    def test_agent_factory_raising_is_silent(self) -> None:
        """Same fail-soft contract when the factory itself raises."""
        def _broken() -> Any:
            raise RuntimeError("simulated")
        out = run(
            {"tool_name": "Bash", "tool_input": {
                "command": "pytest tests/test_consolidate.py"}},
            agent_factory=_broken,
        )
        assert out == ""


# -----------------------------------------------------------------------
# main_stdin_stdout — CLI entry that the .claude/hooks wrapper invokes
# -----------------------------------------------------------------------

class TestMainStdinStdout:
    """Drives the hook from a real stdin/stdout pair — same shape Claude
    Code uses (JSON in, banner text out, exit code 0 always)."""

    def test_writes_banner_for_relevant_step(self, agent_factory) -> None:
        payload = {
            "session_id": "s1",
            "tool_name": "Bash",
            "tool_input": {
                "command": "pytest tests/test_consolidate.py "
                           "-k 'self loop edge'",
            },
        }
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()
        rc = main_stdin_stdout(
            stdin=stdin, stdout=stdout, agent_factory=agent_factory,
        )
        assert rc == 0
        out = stdout.getvalue()
        assert "<engram-step-recall" in out

    def test_empty_stdin_returns_zero_silent(self) -> None:
        stdin = io.StringIO("")
        stdout = io.StringIO()
        rc = main_stdin_stdout(stdin=stdin, stdout=stdout)
        assert rc == 0
        assert stdout.getvalue() == ""

    def test_malformed_stdin_returns_zero_silent(self) -> None:
        stdin = io.StringIO("{not json")
        stdout = io.StringIO()
        rc = main_stdin_stdout(stdin=stdin, stdout=stdout)
        assert rc == 0
        assert stdout.getvalue() == ""

    def test_factory_default_used_when_not_passed(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If no ``agent_factory`` arg is given, the function must fall
        back to a default loader. We only check that the call returns 0
        and does not raise — the default loader uses the live data dir
        which may not exist in CI, so we accept either banner or empty.
        """
        # Force the default loader path: HIPPO_DATA_DIR pointing nowhere
        # — fallback must NOT raise and return 0.
        monkeypatch.setenv("HIPPO_DATA_DIR", "/nonexistent/path")
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/test_x.py"},
        }
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()
        rc = main_stdin_stdout(stdin=stdin, stdout=stdout)
        assert rc == 0
