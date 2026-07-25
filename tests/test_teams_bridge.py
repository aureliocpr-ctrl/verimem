"""teams bridge → verimem (2026-07-23: gated through the moat).

The bridge mirrors agent-teams Mailbox messages into verimem so the chat
survives ``/resume``, supervisor restarts and post-compact context loss.
As of the orchestration-gating change it goes through ``Memory.add`` — an
inter-agent message is an ATTRIBUTED QUOTATION, stored as a hidden
``user_belief`` (out of default recall) on the narrative lane, stamped a
per-agent ``writer_principal``. Default topic ``lab/teams/<team_name>``.

Idle notifications are skipped by default to keep signal-to-noise high.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.client import Memory
from verimem.teams.bridge import mirror_message
from verimem.teams.inbox import InboxMessage


@pytest.fixture
def memory(tmp_path: Path) -> Memory:
    return Memory(path=tmp_path / "sem.db")


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


def test_mirror_message_creates_hidden_chronicle(memory: Memory) -> None:
    """A normal message yields one hidden ``user_belief`` chronicle row."""
    r = mirror_message(_normal_msg(), memory=memory, team_name="alpha")
    assert isinstance(r, dict) and r["stored"]
    with memory.semantic._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT proposition, topic, status FROM facts WHERE id = ?",
            (r["id"],),
        ).fetchone()
    assert row is not None
    assert "python-engineer" in row["proposition"]
    assert "team-lead" in row["proposition"]
    assert "hello team" in row["proposition"]
    assert row["topic"] == "lab/teams/alpha"
    assert row["status"] == "user_belief"


def test_mirror_message_skips_idle_by_default(memory: Memory) -> None:
    """Idle notifications are not persisted unless explicitly requested."""
    result = mirror_message(_idle_msg(), memory=memory, team_name="alpha")
    assert result is None
    with memory.semantic._connect() as conn:  # noqa: SLF001
        count = conn.execute("SELECT COUNT(*) AS n FROM facts").fetchone()["n"]
    assert count == 0


def test_mirror_message_include_idle_when_requested(memory: Memory) -> None:
    """``include_idle=True`` overrides the default skip."""
    r = mirror_message(
        _idle_msg(), memory=memory, team_name="alpha", include_idle=True,
    )
    assert isinstance(r, dict) and r["stored"]


def test_mirror_message_verified_by_includes_team_and_parties(
    memory: Memory,
) -> None:
    """verified_by carries enough provenance for hippo_lineage_trace."""
    r = mirror_message(
        _normal_msg("provenance test"), memory=memory, team_name="prov-team")
    with memory.semantic._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT verified_by FROM facts WHERE id = ?", (r["id"],),
        ).fetchone()
    vb = row["verified_by"] or ""
    assert "claude:team:prov-team" in vb
    assert "from:python-engineer" in vb
    assert "to:team-lead" in vb


def test_mirror_message_truncates_huge_text(memory: Memory) -> None:
    """Defensive: a 100KB message proposition truncates to a sane bound."""
    huge = "X" * 100_000
    r = mirror_message(_normal_msg(huge), memory=memory, team_name="alpha")
    with memory.semantic._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT proposition FROM facts WHERE id = ?", (r["id"],),
        ).fetchone()
    # We cap the snippet at MAX_PROPOSITION_LEN (assert in implementation).
    assert len(row["proposition"]) < 3000
