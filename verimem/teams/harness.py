"""Cycle #159 (2026-05-19) — CollabHarness: measures real collaboration.

Sits on top of :class:`verimem.teams.inbox.InboxWatcher` and classifies
each new message via :func:`verimem.teams.protocol.parse_protocol_tags`.
Aggregates counters per session, decides ``converged`` / ``deadlocked``,
and emits a compact report dict that a CLI can render or a fact-store
can persist.

Design notes:
- **Stateless across processes**. The cursors live in ``InboxWatcher``
  in-memory, so two CollabHarness instances over the same team_dir
  give consistent answers only within a single process. That's fine
  for the cycle-159 use case (one CLI process tails one team).
- **Idle filter on by default.** Idle notifications are inflating
  counters in cycle-150 demos; we filter them at the watcher level
  via ``include_idle=False``.
- **Convergence is rolling**, not historical. We count *distinct
  senders* who have voted at any point since the harness started.
  A teammate vote that arrives in poll #3 still counts on poll #50.
"""
from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .inbox import InboxMessage, InboxWatcher
from .protocol import parse_protocol_tags


@dataclass
class CollabHarness:
    """Measures collaboration progress on an agent-team's inboxes.

    Parameters
    ----------
    team_dir:
        Path to ``~/.claude/teams/<name>`` (the parent of ``inboxes/``).
    members:
        Active teammate names (filename stems under ``inboxes/``).
        Used to compute the majority threshold for convergence.
    deadlock_after_sec:
        Silence (no non-idle messages) longer than this is reported as
        ``deadlocked``. Default 120 s — matches the Mailbox idle ping
        cadence cycle 150 measured empirically.
    """

    team_dir: Path
    members: list[str]
    deadlock_after_sec: float = 120.0

    _watcher: InboxWatcher = field(init=False)
    _started_at: float = field(init=False)
    _last_activity_at: float = field(init=False)

    # Counters
    _total_msgs: int = 0
    _per_tag: Counter = field(default_factory=Counter)
    _senders: Counter = field(default_factory=Counter)
    _voters: set[str] = field(default_factory=set)
    _refers: list[str] = field(default_factory=list)
    _claims: list[tuple[str, str]] = field(default_factory=list)  # (sender, body)
    # Cycle 159.5 opus-review finding #3a: per-member stall detection.
    # Without this dict the team-level ``_last_activity_at`` cannot tell
    # *which* teammate has gone silent — only that ≥1 message arrived
    # somewhere. ``stalled_members(threshold)`` walks this dict.
    _last_seen: dict[str, float] = field(default_factory=dict)
    # Cycle 159.5 opus-review finding #3c: outsiders who try to vote.
    # When a sender not in ``self.members`` emits VOTE-CONVERGED we
    # record them here for the report but never count them toward
    # ``converged``. Prevents an off-team eve@spoof from spoofing
    # convergence.
    _outsider_voters: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self._watcher = InboxWatcher(team_dir=self.team_dir)
        self._started_at = time.time()
        self._last_activity_at = self._started_at

    # ------------------------------------------------------------------ poll

    def poll(self) -> list[InboxMessage]:
        """Pull new messages and update counters. Returns them for echoing."""
        new_msgs = self._watcher.poll(include_idle=False)
        for msg in new_msgs:
            self._classify(msg)
        if new_msgs:
            self._last_activity_at = time.time()
        return new_msgs

    def _classify(self, msg: InboxMessage) -> None:
        self._total_msgs += 1
        self._senders[msg.sender] += 1
        self._last_seen[msg.sender] = time.time()
        is_member = msg.sender in self.members
        tags = parse_protocol_tags(msg.text)
        for tag, bodies in tags.items():
            n = len(bodies)
            if not n:
                continue
            self._per_tag[tag] += n
            if tag == "vote-converged":
                if is_member:
                    self._voters.add(msg.sender)
                else:
                    # Off-team senders are tracked but cannot drive
                    # convergence — opus-review #3c.
                    self._outsider_voters.add(msg.sender)
            elif tag == "refer":
                self._refers.extend(bodies)
            elif tag == "claim":
                for b in bodies:
                    self._claims.append((msg.sender, b))

    # ----------------------------------------------------- stall detection

    def stalled_members(
        self, threshold_sec: float | None = None,
    ) -> list[str]:
        """Members that haven't emitted a non-idle message in
        ``threshold_sec`` (default = ``self.deadlock_after_sec / 2``).

        A member with no entry in ``_last_seen`` at all is treated as
        stalled the moment ``threshold_sec`` has elapsed since the
        harness started — the timer is "since the team began", not
        "since the member last spoke" when the member has never spoken.
        Cycle 159.5 opus-review #3a: the Charter promises to detect
        silent teammates; this exposes them.
        """
        thr = (
            self.deadlock_after_sec / 2.0
            if threshold_sec is None else threshold_sec
        )
        now = time.time()
        stalled: list[str] = []
        for m in self.members:
            last = self._last_seen.get(m, self._started_at)
            if (now - last) >= thr:
                stalled.append(m)
        return stalled

    # -------------------------------------------------------- state queries

    @property
    def converged(self) -> bool:
        """Strict-majority voting: ``len(voters) > N/2``.

        For N=2 → ≥2; N=3 → ≥2; N=4 → ≥3; N=5 → ≥3.
        """
        n = max(1, len(self.members))
        threshold = (n // 2) + 1
        return len(self._voters) >= threshold

    def is_deadlocked(self, now: float | None = None) -> bool:
        """True iff no new message has arrived for ``deadlock_after_sec``.

        Caller may inject ``now`` (testing). When ``self._total_msgs == 0``
        the count starts at construction time — a team that never
        spoke at all is *also* deadlocked after the threshold.
        """
        ts = time.time() if now is None else now
        return (ts - self._last_activity_at) >= self.deadlock_after_sec

    # ------------------------------------------------------------- reporting

    def report(self) -> dict[str, Any]:
        """Compact JSON-friendly snapshot of harness state."""
        return {
            "team_dir": str(self.team_dir),
            "members": list(self.members),
            "total_msgs": self._total_msgs,
            "claims": self._per_tag.get("claim", 0),
            "questions": self._per_tag.get("question", 0),
            "votes_converged": self._per_tag.get("vote-converged", 0),
            "blocked": self._per_tag.get("blocked", 0),
            "refers": self._per_tag.get("refer", 0),
            "senders": dict(self._senders),
            "voters": sorted(self._voters),
            "outsider_voters": sorted(self._outsider_voters),
            "stalled": self.stalled_members(),
            "converged": self.converged,
            "deadlocked": self.is_deadlocked(),
            "elapsed_sec": round(time.time() - self._started_at, 2),
            "last_activity_at": self._last_activity_at,
            "refer_links": list(self._refers),
        }
