"""Cycle #150 (2026-05-19) — agent-teams inbox watcher RED tests.

Empirical baseline (file letto da ~/.claude/teams/engram-rd-lab/inboxes/
team-lead.json, cycle 145 era): every inbox is a JSON array of objects::

    [
      {
        "from": "python-engineer",
        "text": "Audit complete on hippoagent/...",
        "summary": "Audit complete — 20 ranked issues",
        "timestamp": "2026-05-07T21:38:01.613Z",
        "color": "green",
        "read": true
      },
      {
        "from": "security-architect",
        "text": "{\"type\":\"idle_notification\",\"from\":\"...\",\"timestamp\":\"...\",\"idleReason\":\"available\"}",
        "timestamp": "...",
        "color": "purple",
        "read": true
      }
    ]

This RED test suite locks the contract for the GREEN implementation in
engram/teams/inbox.py:
    - InboxMessage dataclass faithful to the JSON shape
    - is_idle_notification flag derived by parsing ``text`` (JSON envelope)
    - InboxWatcher.poll() incremental delivery via per-file cursor
    - Robustness vs missing / invalid / empty files
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engram.teams.inbox import InboxMessage, InboxWatcher


def _write_inbox(path: Path, msgs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(msgs), encoding="utf-8")


# ----------------------------------------------------------------------
# InboxMessage parsing
# ----------------------------------------------------------------------
def test_inbox_message_from_dict_normal() -> None:
    """A regular text message parses with is_idle_notification=False."""
    raw = {
        "from": "python-engineer",
        "text": "Audit complete on hippoagent/",
        "summary": "Audit done",
        "timestamp": "2026-05-07T21:38:01.613Z",
        "color": "green",
        "read": True,
    }
    msg = InboxMessage.from_raw(raw, recipient="team-lead")
    assert msg.sender == "python-engineer"
    assert msg.recipient == "team-lead"
    assert msg.text.startswith("Audit complete")
    assert msg.summary == "Audit done"
    assert msg.timestamp == "2026-05-07T21:38:01.613Z"
    assert msg.is_idle_notification is False
    assert msg.read is True


def test_inbox_message_from_dict_idle_notification() -> None:
    """An idle_notification envelope is detected via ``text`` JSON parsing."""
    raw = {
        "from": "architect",
        "text": '{"type":"idle_notification","from":"architect",'
                '"timestamp":"2026-05-07T21:37:42.466Z","idleReason":"available"}',
        "timestamp": "2026-05-07T21:37:42.466Z",
        "color": "blue",
        "read": True,
    }
    msg = InboxMessage.from_raw(raw, recipient="team-lead")
    assert msg.is_idle_notification is True
    assert msg.sender == "architect"


def test_inbox_message_missing_optional_fields() -> None:
    """Optional fields (summary, color, read) default sensibly."""
    raw = {
        "from": "x",
        "text": "hi",
        "timestamp": "2026-05-19T00:00:00.000Z",
    }
    msg = InboxMessage.from_raw(raw, recipient="y")
    assert msg.summary == ""
    assert msg.color == ""
    assert msg.read is False


# ----------------------------------------------------------------------
# InboxWatcher behaviour
# ----------------------------------------------------------------------
def test_watcher_first_poll_returns_all_messages(tmp_path: Path) -> None:
    """Initial poll surfaces every message in the file."""
    inbox = tmp_path / "team-x" / "inboxes" / "alice.json"
    _write_inbox(inbox, [
        {"from": "bob", "text": "msg1", "timestamp": "t1"},
        {"from": "carol", "text": "msg2", "timestamp": "t2"},
    ])
    w = InboxWatcher(team_dir=tmp_path / "team-x")
    new = w.poll()
    assert len(new) == 2
    assert new[0].text == "msg1"
    assert new[1].text == "msg2"
    assert all(m.recipient == "alice" for m in new)


def test_watcher_second_poll_returns_only_new(tmp_path: Path) -> None:
    """Cursor advances: re-poll after no change yields []."""
    inbox = tmp_path / "team-y" / "inboxes" / "alice.json"
    _write_inbox(inbox, [{"from": "bob", "text": "msg1", "timestamp": "t1"}])
    w = InboxWatcher(team_dir=tmp_path / "team-y")
    first = w.poll()
    assert len(first) == 1
    again = w.poll()
    assert again == []
    # Append a new message; the watcher should surface only the new one.
    _write_inbox(inbox, [
        {"from": "bob", "text": "msg1", "timestamp": "t1"},
        {"from": "carol", "text": "msg2-NEW", "timestamp": "t2"},
    ])
    third = w.poll()
    assert len(third) == 1
    assert third[0].text == "msg2-NEW"


def test_watcher_handles_missing_team_dir(tmp_path: Path) -> None:
    """No team dir → poll returns [] (does not raise)."""
    w = InboxWatcher(team_dir=tmp_path / "does-not-exist")
    assert w.poll() == []


def test_watcher_handles_invalid_json(tmp_path: Path) -> None:
    """A corrupted inbox JSON file is skipped silently."""
    inbox = tmp_path / "team-z" / "inboxes" / "alice.json"
    inbox.parent.mkdir(parents=True, exist_ok=True)
    inbox.write_text("{ not valid json [", encoding="utf-8")
    w = InboxWatcher(team_dir=tmp_path / "team-z")
    assert w.poll() == []  # graceful: no crash


def test_watcher_multi_inbox_separate_cursors(tmp_path: Path) -> None:
    """Two inbox files have independent cursors."""
    base = tmp_path / "team-multi" / "inboxes"
    _write_inbox(base / "alice.json", [
        {"from": "x", "text": "a1", "timestamp": "t1"},
    ])
    _write_inbox(base / "bob.json", [
        {"from": "y", "text": "b1", "timestamp": "t1"},
    ])
    w = InboxWatcher(team_dir=tmp_path / "team-multi")
    new = w.poll()
    senders = {m.sender for m in new}
    recipients = {m.recipient for m in new}
    assert senders == {"x", "y"}
    assert recipients == {"alice", "bob"}
    # Append only to alice
    _write_inbox(base / "alice.json", [
        {"from": "x", "text": "a1", "timestamp": "t1"},
        {"from": "x", "text": "a2", "timestamp": "t2"},
    ])
    new = w.poll()
    assert len(new) == 1
    assert new[0].text == "a2"
    assert new[0].recipient == "alice"


def test_watcher_filter_skip_idle(tmp_path: Path) -> None:
    """``include_idle=False`` filters out idle_notification messages."""
    inbox = tmp_path / "team-q" / "inboxes" / "alice.json"
    _write_inbox(inbox, [
        {"from": "bob", "text": "real message", "timestamp": "t1"},
        {
            "from": "carol",
            "text": '{"type":"idle_notification","from":"carol",'
                    '"timestamp":"t2","idleReason":"available"}',
            "timestamp": "t2",
        },
    ])
    w = InboxWatcher(team_dir=tmp_path / "team-q")
    new = w.poll(include_idle=False)
    assert len(new) == 1
    assert new[0].text == "real message"


# ----------------------------------------------------------------------
# Misc safety / contract
# ----------------------------------------------------------------------
def test_inbox_message_repr_safe_with_large_text() -> None:
    """repr() does not crash on very long text (defensive bound check)."""
    raw = {"from": "x", "text": "A" * 10_000, "timestamp": "t"}
    msg = InboxMessage.from_raw(raw, recipient="y")
    _ = repr(msg)  # no exception
    assert msg.text.startswith("A")


@pytest.mark.parametrize("bad_input", [
    "[]",  # empty array
    "  [ ] ",  # whitespace
])
def test_watcher_empty_inbox_returns_nothing(
    tmp_path: Path, bad_input: str,
) -> None:
    """An empty JSON array yields no events."""
    inbox = tmp_path / "team-e" / "inboxes" / "alice.json"
    inbox.parent.mkdir(parents=True, exist_ok=True)
    inbox.write_text(bad_input, encoding="utf-8")
    w = InboxWatcher(team_dir=tmp_path / "team-e")
    assert w.poll() == []
