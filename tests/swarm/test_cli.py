"""Cycle #148.6.b (2026-05-18 sera) — swarm CLI RED phase.

Typer subapp exposes:
    engram swarm run <config.yaml>     end-to-end run
    engram swarm status <run_id>       list active sessions
    engram swarm logs <short_id>       passthrough to ``claude logs``
    engram swarm kill <run_id>         stop all sessions for run
    engram swarm clean <run_id>        rm all sessions for run

Tests use typer.testing.CliRunner. Subprocess calls to ``claude`` are
patched out so unit tests stay fast + deterministic. The end-to-end
integration test with a real haiku swarm lives in cycle 148.7.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from engram.swarm.cli import swarm_app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _ok_run() -> MagicMock:
    cp = MagicMock()
    cp.returncode = 0
    cp.stdout = "ok\n"
    cp.stderr = ""
    return cp


class TestSwarmRunCommand:
    def test_run_loads_yaml_and_calls_orchestrator(
        self, runner: CliRunner, tmp_path: Path,
    ) -> None:
        cfg = tmp_path / "swarm.yaml"
        cfg.write_text(
            "run_id: cycle148-cli-test\n"
            "topic: lab/swarm/cycle148-cli-test\n"
            "timeout_sec: 5\n"
            "agents:\n"
            "  - name: a\n"
            "    prompt: do A\n"
            "    model: haiku\n"
            "  - name: b\n"
            "    prompt: do B\n"
            "    model: haiku\n",
            encoding="utf-8",
        )
        with patch("engram.swarm.cli.run_swarm") as rs:
            from engram.swarm.orchestrator import AgentReport, SwarmReport
            rs.return_value = SwarmReport(
                run_id="cycle148-cli-test",
                topic="lab/swarm/cycle148-cli-test",
                hub_ep_id="hub-id",
                agents=[
                    AgentReport(agent_name="a", short_id="aa", final_state="done"),
                    AgentReport(agent_name="b", short_id="bb", final_state="done"),
                ],
                success_count=2, failure_count=0,
            )
            result = runner.invoke(swarm_app, ["run", str(cfg)])
        assert result.exit_code == 0, result.stdout
        assert rs.called
        cfg_passed = rs.call_args.args[0]
        assert cfg_passed.run_id == "cycle148-cli-test"
        assert len(cfg_passed.agents) == 2

    def test_run_yaml_invalid_path_exits_nonzero(
        self, runner: CliRunner, tmp_path: Path,
    ) -> None:
        bad = tmp_path / "nope.yaml"
        result = runner.invoke(swarm_app, ["run", str(bad)])
        assert result.exit_code != 0


class TestSwarmStatus:
    def test_status_lists_sessions_for_run_id(
        self, runner: CliRunner,
    ) -> None:
        with patch(
            "engram.swarm.cli.list_swarm_sessions",
            return_value=["aaaa1111", "bbbb2222"],
        ):
            result = runner.invoke(
                swarm_app, ["status", "cycle148-cli-test"],
            )
        assert result.exit_code == 0
        assert "aaaa1111" in result.stdout
        assert "bbbb2222" in result.stdout


class TestSwarmLogs:
    def test_logs_passthrough_to_claude_logs(
        self, runner: CliRunner,
    ) -> None:
        cp = MagicMock(returncode=0, stdout="LOG OUTPUT", stderr="")
        with patch(
            "engram.swarm.cli.subprocess.run", return_value=cp,
        ) as run:
            result = runner.invoke(swarm_app, ["logs", "abc12345"])
        assert result.exit_code == 0
        args, _ = run.call_args
        assert args[0] == ["claude", "logs", "abc12345"]
        assert "LOG OUTPUT" in result.stdout


class TestSwarmKill:
    def test_kill_stops_each_session(self, runner: CliRunner) -> None:
        with patch(
            "engram.swarm.cli.list_swarm_sessions",
            return_value=["x1", "x2"],
        ), patch(
            "engram.swarm.cli.stop_session", return_value=True,
        ) as stop:
            result = runner.invoke(swarm_app, ["kill", "cycle148-cli-test"])
        assert result.exit_code == 0
        assert stop.call_count == 2
