"""Cycle #150 (2026-05-19) — engram teams CLI RED tests.

Two commands:
    engram teams send --team <t> --to <name> --as <human> --message "..."
        Appends one JSON object to ~/.claude/teams/<t>/inboxes/<name>.json
        (creates dir/file if absent). Aurelio (the human operator) can
        inject a message into a teammate's mailbox from a separate CLI
        without owning a Claude Code session — exactly what cycle 145
        could not do.

    engram teams watch <team> [--max-sec N] [--refresh-sec 0.5]
        Rich Live tail of all inboxes/*.json for the named team. Smoke
        tested only: we just verify the typer command resolves and exits
        cleanly within max-sec.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from engram.teams.cli import teams_app


def test_send_command_creates_inbox_and_appends(tmp_path: Path) -> None:
    """``engram teams send`` writes a JSON message to the recipient inbox."""
    team_dir = tmp_path / "alpha"
    runner = CliRunner()
    result = runner.invoke(
        teams_app,
        [
            "send",
            "--team-dir", str(team_dir),
            "--to", "architect",
            "--as", "aurelio",
            "--message", "ciao architect, prova message",
        ],
    )
    assert result.exit_code == 0, result.output
    inbox = team_dir / "inboxes" / "architect.json"
    assert inbox.is_file()
    data = json.loads(inbox.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["from"] == "aurelio"
    assert data[0]["text"] == "ciao architect, prova message"
    assert "timestamp" in data[0]


def test_send_command_appends_to_existing_inbox(tmp_path: Path) -> None:
    """Subsequent send appends to the existing array (no overwrite)."""
    team_dir = tmp_path / "beta"
    inbox = team_dir / "inboxes" / "architect.json"
    inbox.parent.mkdir(parents=True, exist_ok=True)
    inbox.write_text(
        json.dumps([{"from": "old", "text": "older", "timestamp": "t0"}]),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        teams_app,
        [
            "send",
            "--team-dir", str(team_dir),
            "--to", "architect",
            "--as", "aurelio",
            "--message", "secondo messaggio",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(inbox.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["text"] == "older"
    assert data[1]["text"] == "secondo messaggio"
    assert data[1]["from"] == "aurelio"


def test_watch_command_smoke(tmp_path: Path) -> None:
    """``engram teams watch`` exits cleanly with --max-sec 0.1 on empty dir."""
    team_dir = tmp_path / "smoke"
    team_dir.mkdir()
    (team_dir / "inboxes").mkdir()
    runner = CliRunner()
    result = runner.invoke(
        teams_app,
        [
            "watch",
            "--team-dir", str(team_dir),
            "--max-sec", "0.1",
            "--refresh-sec", "0.05",
        ],
    )
    # Smoke: must not raise. Exit code 0 expected. We allow any non-crash.
    assert result.exit_code == 0, result.output


def test_watch_mirror_smoke_empty_dir(tmp_path: Path) -> None:
    """``--mirror-to-memory`` on empty dir exits clean (no fact created)."""
    team_dir = tmp_path / "smoke-mirror"
    (team_dir / "inboxes").mkdir(parents=True, exist_ok=True)
    runner = CliRunner()
    result = runner.invoke(
        teams_app,
        [
            "watch",
            "--team-dir", str(team_dir),
            "--max-sec", "0.1",
            "--refresh-sec", "0.05",
            "--mirror-to-memory",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "mirror_to_memory ENABLED" in result.output


def test_watch_mirror_persists_real_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integration: a non-idle inbox message is mirrored to a HippoAgent
    Fact on topic ``lab/teams/<team_dir.name>`` when ``--mirror-to-memory``
    is enabled. Closes the cycle 150 gap (messages were volatile before)."""
    # Isolate SemanticMemory storage to tmp so the test does not pollute
    # the user's real engram DB.
    hippo_dir = tmp_path / "hippo"
    hippo_dir.mkdir()
    monkeypatch.setenv("HIPPO_DATA_DIR", str(hippo_dir))

    team_dir = tmp_path / "alpha-mirror"
    inbox = team_dir / "inboxes" / "bob.json"
    inbox.parent.mkdir(parents=True, exist_ok=True)
    inbox.write_text(
        json.dumps([
            {
                "from": "alice",
                "text": "hello bob mirrored",
                "timestamp": "2026-05-19T01:00:00.000Z",
            },
        ]),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        teams_app,
        [
            "watch",
            "--team-dir", str(team_dir),
            "--max-sec", "0.5",
            "--refresh-sec", "0.05",
            "--mirror-to-memory",
        ],
    )
    assert result.exit_code == 0, result.output

    # Verify the fact landed in semantic memory at the right topic.
    from engram.semantic import SemanticMemory
    sm = SemanticMemory()
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT proposition, topic FROM facts WHERE topic = ?",
            ("lab/teams/alpha-mirror",),
        ).fetchall()
    assert len(rows) >= 1, (
        f"Expected >=1 fact on 'lab/teams/alpha-mirror', got {len(rows)}. "
        f"CLI output:\n{result.output}"
    )
    propositions = " | ".join(r["proposition"] for r in rows)
    assert "alice" in propositions
    assert "hello bob mirrored" in propositions
