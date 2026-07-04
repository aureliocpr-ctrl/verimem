"""Cycle #150 (2026-05-19) — teams bridge HippoAgent RED tests.

The bridge mirrors agent-teams Mailbox messages into HippoAgent
SemanticMemory facts so the chat survives ``/resume``, supervisor
restarts, and post-compact context loss. Default topic format::

    lab/teams/<team_name>

Each Fact has:
    proposition = "[teammate X → teammate Y @HH:MM:SS] <text snippet>"
    topic = lab/teams/<team_name>
    verified_by = [
        "claude:team:<team_name>",
        "from:<sender>",
        "to:<recipient>",
    ]
    status = "model_claim"

Idle notifications are skipped by default to keep signal-to-noise high.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engram.semantic import SemanticMemory
from engram.teams.bridge import mirror_message
from engram.teams.inbox import InboxMessage


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


def _normal_msg(text: str = "hello team") -> InboxMessage:
    return InboxMessage.from_raw(
        {
            "from": "python-engineer",
            "text": text,
            "summary": "preview",
            "timestamp": "2026-05-19T00:00:00.000Z",
            "color": "green",
            "read": False,
        },
        recipient="team-lead",
    )


def _idle_msg() -> InboxMessage:
    return InboxMessage.from_raw(
        {
            "from": "architect",
            "text": '{"type":"idle_notification","from":"architect",'
                    '"timestamp":"t","idleReason":"available"}',
            "timestamp": "2026-05-19T00:00:01.000Z",
        },
        recipient="team-lead",
    )


def test_mirror_message_creates_fact(sm: SemanticMemory) -> None:
    """A normal message yields one Fact with the expected proposition."""
    msg = _normal_msg()
    fid = mirror_message(msg, sm=sm, team_name="alpha")
    assert isinstance(fid, str) and len(fid) > 0
    with sm._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT proposition, topic, status FROM facts WHERE id = ?",
            (fid,),
        ).fetchone()
    assert row is not None
    assert "python-engineer" in row["proposition"]
    assert "team-lead" in row["proposition"]
    assert "hello team" in row["proposition"]
    assert row["topic"] == "lab/teams/alpha"
    assert row["status"] == "model_claim"


def test_mirror_message_skips_idle_by_default(sm: SemanticMemory) -> None:
    """Idle notifications are not persisted unless explicitly requested."""
    msg = _idle_msg()
    result = mirror_message(msg, sm=sm, team_name="alpha")
    assert result is None
    with sm._connect() as conn:  # noqa: SLF001
        count = conn.execute("SELECT COUNT(*) AS n FROM facts").fetchone()["n"]
    assert count == 0


def test_mirror_message_include_idle_when_requested(sm: SemanticMemory) -> None:
    """``include_idle=True`` overrides the default skip."""
    msg = _idle_msg()
    fid = mirror_message(
        msg, sm=sm, team_name="alpha", include_idle=True,
    )
    assert isinstance(fid, str)


def test_mirror_message_verified_by_includes_team_and_parties(
    sm: SemanticMemory,
) -> None:
    """verified_by carries enough provenance for hippo_lineage_trace."""
    msg = _normal_msg("provenance test")
    fid = mirror_message(msg, sm=sm, team_name="prov-team")
    with sm._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT verified_by FROM facts WHERE id = ?", (fid,),
        ).fetchone()
    vb = row["verified_by"] or ""
    assert "claude:team:prov-team" in vb
    assert "from:python-engineer" in vb
    assert "to:team-lead" in vb


def test_mirror_message_truncates_huge_text(sm: SemanticMemory) -> None:
    """Defensive: a 100KB message proposition truncates to a sane bound."""
    huge = "X" * 100_000
    msg = _normal_msg(huge)
    fid = mirror_message(msg, sm=sm, team_name="alpha")
    with sm._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT proposition FROM facts WHERE id = ?", (fid,),
        ).fetchone()
    # We cap the snippet at MAX_PROPOSITION_LEN (assert in implementation).
    assert len(row["proposition"]) < 3000
