"""Cycle #148.5 (2026-05-18 sera) — swarm lifecycle RED phase.

Wraps the native ``claude stop|respawn|rm`` commands with HippoAgent
audit logging on a chat topic.

API:
    stop_session(short_id, *, topic, sm, agent_name) -> bool
    respawn_session(short_id, *, topic, sm, agent_name) -> bool
    remove_session(short_id, *, topic, sm, agent_name) -> bool
    list_swarm_sessions(run_id, *, jobs_dir) -> list[str]
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from engram.semantic import SemanticMemory
from engram.swarm.lifecycle import (
    list_swarm_sessions,
    remove_session,
    respawn_session,
    stop_session,
)

_TOPIC = "lab/swarm/test-lifecycle"


def _ok_run() -> MagicMock:
    cp = MagicMock()
    cp.returncode = 0
    cp.stdout = "ok\n"
    cp.stderr = ""
    return cp


def _fail_run() -> MagicMock:
    cp = MagicMock()
    cp.returncode = 1
    cp.stdout = ""
    cp.stderr = "no such session\n"
    return cp


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


class TestStopSession:
    def test_invokes_claude_stop(self, sm: SemanticMemory) -> None:
        with patch(
            "engram.swarm.lifecycle.subprocess.run",
            return_value=_ok_run(),
        ) as run:
            ok = stop_session(
                "abc12345", topic=_TOPIC, sm=sm, agent_name="agent-a",
            )
        assert ok is True
        args, _ = run.call_args
        assert args[0][:3] == ["claude", "stop", "abc12345"]

    def test_writes_audit_fact(self, sm: SemanticMemory) -> None:
        with patch(
            "engram.swarm.lifecycle.subprocess.run", return_value=_ok_run(),
        ):
            stop_session(
                "abc12345", topic=_TOPIC, sm=sm, agent_name="agent-a",
            )
        with sm._connect() as conn:  # noqa: SLF001
            rows = conn.execute(
                "SELECT proposition FROM facts WHERE topic = ?",
                (_TOPIC,),
            ).fetchall()
        assert len(rows) == 1
        assert "stop" in rows[0]["proposition"].lower()
        assert "abc12345" in rows[0]["proposition"]

    def test_returns_false_on_failure(self, sm: SemanticMemory) -> None:
        with patch(
            "engram.swarm.lifecycle.subprocess.run",
            return_value=_fail_run(),
        ):
            ok = stop_session(
                "abc12345", topic=_TOPIC, sm=sm, agent_name="agent-a",
            )
        assert ok is False


class TestRespawnSession:
    def test_invokes_claude_respawn(self, sm: SemanticMemory) -> None:
        with patch(
            "engram.swarm.lifecycle.subprocess.run", return_value=_ok_run(),
        ) as run:
            ok = respawn_session(
                "abc12345", topic=_TOPIC, sm=sm, agent_name="agent-a",
            )
        assert ok is True
        args, _ = run.call_args
        assert args[0][:3] == ["claude", "respawn", "abc12345"]


class TestRemoveSession:
    def test_invokes_claude_rm(self, sm: SemanticMemory) -> None:
        with patch(
            "engram.swarm.lifecycle.subprocess.run", return_value=_ok_run(),
        ) as run:
            ok = remove_session(
                "abc12345", topic=_TOPIC, sm=sm, agent_name="agent-a",
            )
        assert ok is True
        args, _ = run.call_args
        assert args[0][:3] == ["claude", "rm", "abc12345"]


class TestListSwarmSessions:
    """List jobs whose `name` matches the run-id prefix."""

    def test_filters_by_run_id_prefix(self, tmp_path: Path) -> None:
        jobs = tmp_path / "jobs"
        jobs.mkdir()
        # Session 1 — belongs to our run
        (jobs / "11111111").mkdir()
        (jobs / "11111111" / "state.json").write_text(
            json.dumps({
                "daemonShort": "11111111",
                "name": "cycle148-test-agent-a",
            }),
            encoding="utf-8",
        )
        # Session 2 — different run
        (jobs / "22222222").mkdir()
        (jobs / "22222222" / "state.json").write_text(
            json.dumps({
                "daemonShort": "22222222",
                "name": "cycle999-other-agent",
            }),
            encoding="utf-8",
        )
        ids = list_swarm_sessions("cycle148-test", jobs_dir=jobs)
        assert ids == ["11111111"], (
            f"cycle 148.5: filter by name prefix, got {ids!r}"
        )

    def test_returns_empty_when_jobs_dir_missing(
        self, tmp_path: Path,
    ) -> None:
        ids = list_swarm_sessions("anything", jobs_dir=tmp_path / "nope")
        assert ids == []
