"""Cycle #148.2 (2026-05-18 sera) — swarm spawn RED phase.

``spawn_agent`` invokes ``claude --bg`` with arguments composed from an
AgentSpec, captures stdout, parses the short session ID, and returns a
SpawnResult. Subprocess is mocked here for determinism; the integration
test in cycle 148.7 exercises a real ``claude --bg`` haiku call.

Empirical evidence (Fase 0, session d3ffcf29):
    backgrounded · d3ffcf29
      claude agents             list sessions
      claude attach d3ffcf29    open in this terminal
      ...

Short ID regex: r"backgrounded\\s*[·.]\\s*([a-f0-9]{8})"

API contract:
    spawn_agent(spec: AgentSpec, *, run_id: str, swarm_cwd: Path|None=None,
                env_overrides: dict|None=None) -> SpawnResult

    SpawnResult.short_id: str  (8 hex chars)
    SpawnResult.command: list[str]  (exact argv used)
    SpawnResult.stdout: str
    SpawnResult.spawned_at: float  (time.time())

    SpawnError on non-zero exit or unparseable output.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from engram.swarm.schemas import AgentSpec
from engram.swarm.spawn import SpawnError, SpawnResult, spawn_agent

SAMPLE_OUTPUT = (
    "Starting background service…\n"
    "backgrounded · d3ffcf29\n"
    "  claude agents             list sessions\n"
    "  claude attach d3ffcf29    open in this terminal\n"
    "  claude logs d3ffcf29      show recent output\n"
    "  claude stop d3ffcf29      stop this session\n"
)


def _mock_run(stdout: str = SAMPLE_OUTPUT, returncode: int = 0):
    """Build a fake CompletedProcess for subprocess.run."""
    cp = MagicMock()
    cp.stdout = stdout
    cp.stderr = ""
    cp.returncode = returncode
    return cp


class TestSpawnAgent:
    """Argument composition + ID parse."""

    def test_returns_short_id_from_output(self) -> None:
        spec = AgentSpec(name="agent-a", prompt="hello")
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run()) as run:
            r = spawn_agent(spec, run_id="cycle148-test")
        assert isinstance(r, SpawnResult)
        assert r.short_id == "d3ffcf29", (
            f"cycle 148.2: short_id must parse from 'backgrounded · <id>', "
            f"got {r.short_id!r}"
        )
        assert run.called

    def test_command_includes_bg_and_print_disabled(self) -> None:
        spec = AgentSpec(name="agent-a", prompt="hello")
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run()):
            r = spawn_agent(spec, run_id="cycle148-test")
        assert "--bg" in r.command, (
            f"cycle 148.2: --bg required, got {r.command!r}"
        )
        # --print MUST NOT be present (bg is its own non-interactive mode).
        assert "--print" not in r.command and "-p" not in r.command, (
            f"cycle 148.2: --print conflicts with --bg, got {r.command!r}"
        )

    def test_command_passes_model_flag(self) -> None:
        spec = AgentSpec(name="a", prompt="x", model="sonnet")
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run()):
            r = spawn_agent(spec, run_id="r")
        assert "--model" in r.command
        idx = r.command.index("--model")
        assert r.command[idx + 1] == "sonnet"

    def test_command_passes_max_budget_flag(self) -> None:
        spec = AgentSpec(name="a", prompt="x", max_budget_usd=2.5)
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run()):
            r = spawn_agent(spec, run_id="r")
        assert "--max-budget-usd" in r.command
        idx = r.command.index("--max-budget-usd")
        assert r.command[idx + 1] == "2.5"

    def test_command_passes_permission_mode(self) -> None:
        spec = AgentSpec(name="a", prompt="x", permission_mode="acceptEdits")
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run()):
            r = spawn_agent(spec, run_id="r")
        assert "--permission-mode" in r.command
        idx = r.command.index("--permission-mode")
        assert r.command[idx + 1] == "acceptEdits"

    def test_command_passes_name_as_run_id_agent_name(self) -> None:
        """display name = <run_id>-<agent_name> for searchability."""
        spec = AgentSpec(name="reviewer", prompt="x")
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run()):
            r = spawn_agent(spec, run_id="cycle148-test")
        assert "--name" in r.command
        idx = r.command.index("--name")
        assert r.command[idx + 1] == "cycle148-test-reviewer"

    def test_command_passes_worktree_flag_when_true(self) -> None:
        spec = AgentSpec(name="a", prompt="x", worktree=True)
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run()):
            r = spawn_agent(spec, run_id="r")
        assert "--worktree" in r.command or "-w" in r.command

    def test_command_skips_worktree_flag_when_false(self) -> None:
        spec = AgentSpec(name="a", prompt="x", worktree=False)
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run()):
            r = spawn_agent(spec, run_id="r")
        assert "--worktree" not in r.command and "-w" not in r.command

    def test_command_passes_allowed_tools_when_set(self) -> None:
        spec = AgentSpec(
            name="a", prompt="x", allowed_tools=["Read", "Grep"],
        )
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run()):
            r = spawn_agent(spec, run_id="r")
        # allowedTools is a space- or comma-separated list, single flag.
        assert "--allowedTools" in r.command
        idx = r.command.index("--allowedTools")
        joined = r.command[idx + 1]
        assert "Read" in joined and "Grep" in joined

    def test_command_passes_bare_flag_when_true(self) -> None:
        spec = AgentSpec(name="a", prompt="x", bare=True)
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run()):
            r = spawn_agent(spec, run_id="r")
        assert "--bare" in r.command

    def test_prompt_is_last_positional(self) -> None:
        spec = AgentSpec(name="a", prompt="DO THE THING")
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run()):
            r = spawn_agent(spec, run_id="r")
        assert r.command[-1] == "DO THE THING"

    def test_enables_agent_teams_env_var(self) -> None:
        spec = AgentSpec(name="a", prompt="x")
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run()) as run:
            spawn_agent(spec, run_id="r")
        # subprocess.run called with env containing the flag
        _, kwargs = run.call_args
        env = kwargs.get("env", {})
        assert env.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1", (
            f"cycle 148.2: must set agent-teams env var, got env={env!r}"
        )

    def test_raises_on_subprocess_nonzero_exit(self) -> None:
        spec = AgentSpec(name="a", prompt="x")
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run(returncode=1, stdout="boom")):
            with pytest.raises(SpawnError):
                spawn_agent(spec, run_id="r")

    def test_raises_on_unparseable_output(self) -> None:
        spec = AgentSpec(name="a", prompt="x")
        with patch("engram.swarm.spawn.subprocess.run",
                   return_value=_mock_run(stdout="garbage no id here")):
            with pytest.raises(SpawnError):
                spawn_agent(spec, run_id="r")
