"""Cycle #150 (2026-05-19) — agent-teams inbox parser + watcher.

Empirical schema (verbatim da ``~/.claude/teams/engram-rd-lab/inboxes/
team-lead.json`` letto durante audit cycle 150)::

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
        "text": "{\"type\":\"idle_notification\",\"from\":\"security-architect\",
                 \"timestamp\":\"...\",\"idleReason\":\"available\"}",
        "timestamp": "2026-05-07T21:36:53.167Z",
        "color": "purple",
        "read": true
      }
    ]

Il campo ``text`` può essere o un messaggio testuale libero (vero
contenuto inter-agent) o una busta JSON di sistema (``idle_notification``,
``shutdown_request`` ecc.). Il watcher distingue i due via parse difensivo
di ``text`` come JSON.

``InboxWatcher.poll()`` è progettato per loop di polling: mantiene un
cursore per file (recipient) e ritorna solo i messaggi nuovi rispetto
all'ultima call. Cursori in-memory → ogni nuova istanza riparte da 0
(comportamento utile per la CLI ``engram teams watch`` che vuole vedere
lo storico al primo frame, poi solo i delta).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InboxMessage:
    """One message read out of a teammate inbox file.

    ``is_idle_notification`` is set when ``text`` parses as a JSON
    envelope with ``type == 'idle_notification'`` — these are the noisy
    system-level pings that Claude emits between turns and that should
    be filtered out of a chat UI by default.
    """

    sender: str
    recipient: str
    text: str
    summary: str = ""
    timestamp: str = ""
    color: str = ""
    read: bool = False
    is_idle_notification: bool = False

    @classmethod
    def from_raw(cls, raw: dict, *, recipient: str) -> InboxMessage:
        """Build from one raw entry of the inbox JSON array."""
        text = raw.get("text") or ""
        if not isinstance(text, str):
            text = str(text)

        # Try to detect the idle_notification JSON envelope.
        is_idle = False
        if text and text.startswith("{"):
            try:
                parsed = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                parsed = None
            if isinstance(parsed, dict) and parsed.get("type") == "idle_notification":
                is_idle = True

        return cls(
            sender=str(raw.get("from") or ""),
            recipient=recipient,
            text=text,
            summary=str(raw.get("summary") or ""),
            timestamp=str(raw.get("timestamp") or ""),
            color=str(raw.get("color") or ""),
            read=bool(raw.get("read", False)),
            is_idle_notification=is_idle,
        )


class InboxWatcher:
    """Incremental poller over a team's ``inboxes/*.json`` files.

    Usage::

        w = InboxWatcher(team_dir=Path.home() / ".claude" / "teams" / "alpha")
        while running:
            for msg in w.poll(include_idle=False):
                render(msg)
            time.sleep(0.5)

    Each call to :meth:`poll` returns only messages not yet surfaced for
    that watcher instance. Cursors are kept in-memory; constructing a
    new watcher restarts from the head of each file.
    """

    def __init__(self, team_dir: Path | str) -> None:
        self.team_dir = Path(team_dir)
        # recipient name (== filename stem) → last index already returned
        self._cursors: dict[str, int] = {}

    def poll(self, *, include_idle: bool = True) -> list[InboxMessage]:
        """Return new messages from every inbox file since the last poll.

        Ordering: messages are emitted in (filename, file-index) order —
        deterministic and matches the on-disk write order within a single
        inbox. Cross-inbox ordering is by alphabetical filename; if a
        chronological global view matters, the caller should sort by
        ``timestamp``.
        """
        inboxes_dir = self.team_dir / "inboxes"
        if not inboxes_dir.is_dir():
            return []

        out: list[InboxMessage] = []
        for inbox_file in sorted(inboxes_dir.glob("*.json")):
            recipient = inbox_file.stem
            try:
                raw_text = inbox_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                arr = json.loads(raw_text) if raw_text.strip() else []
            except json.JSONDecodeError:
                continue
            if not isinstance(arr, list):
                continue

            cursor = self._cursors.get(recipient, 0)
            for item in arr[cursor:]:
                if not isinstance(item, dict):
                    continue
                msg = InboxMessage.from_raw(item, recipient=recipient)
                if not include_idle and msg.is_idle_notification:
                    continue
                out.append(msg)
            # Always advance the cursor past the full file length, even
            # when some entries were filtered out — otherwise a filtered
            # idle would resurface on the next poll.
            self._cursors[recipient] = len(arr)

        return out
