"""Cycle #150 (2026-05-19) — teams ↔ HippoAgent semantic-memory bridge.

Why this exists: agent-teams Mailbox è in-memory + file-based locale al
supervisor. Sopravvive a /resume? Sì se i file inbox non vengono
cancellati con ``TeamDelete``. Ma per audit cross-session, recall via
``hippo_facts_search`` e lineage trace, ogni messaggio meritevole
diventa un :class:`verimem.semantic.Fact` su topic ``lab/teams/<name>``.

Format proposition::

    "[<sender> → <recipient> @<HH:MM:SS>] <text snippet, max ~2K>"

Format verified_by::

    ["claude:team:<name>", "from:<sender>", "to:<recipient>"]

Idle notifications skippate by default (signal-to-noise). Pass
``include_idle=True`` per un audit completo (es. debug timing
inter-agent).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..orchestration import CHRONICLE_CONFIDENCE, agent_principal
from .inbox import InboxMessage

if TYPE_CHECKING:  # avoid a hard import cycle at module load
    from ..client import Memory

# Truncation bound for the proposition snippet. The store does not enforce
# a hard limit, but giant propositions hurt embedding quality and clutter
# ``hippo_facts_search`` output. 2000 chars ≈ 500 BPE tokens.
_MAX_PROPOSITION_LEN = 2000


def _short_ts(timestamp: str) -> str:
    """Extract ``HH:MM:SS`` from an ISO8601 timestamp; passthrough else."""
    if len(timestamp) >= 19 and timestamp[10] == "T":
        return timestamp[11:19]
    return timestamp


def mirror_message(
    msg: InboxMessage,
    *,
    memory: Memory,
    team_name: str,
    include_idle: bool = False,
) -> dict[str, Any] | None:
    """Mirror one inbox message into verimem THROUGH the moat.

    The message is an ATTRIBUTED QUOTATION of what a teammate said, so it
    goes through ``Memory.add(chronicle=True)``: stored as a hidden
    ``user_belief`` (out of default recall — the moat never returns an
    agent's unverified assertion AS a fact), on the narrative lane (the
    L1 self-claim family is a category error on a quotation) but with the
    injection screen live (a poisoned message is quarantined). The row is
    stamped a server-composed per-agent ``writer_principal``.

    Returns the adjudication receipt dict (``{stored, id, status, ...}``
    from ``Memory.add``) — the NEW contract; ``None`` when the message is
    an ``is_idle_notification`` skipped by default.
    """
    if msg.is_idle_notification and not include_idle:
        return None

    snippet = msg.text[:_MAX_PROPOSITION_LEN]
    ts = _short_ts(msg.timestamp)
    proposition = f"[{msg.sender} → {msg.recipient} @{ts}] {snippet}"

    return memory.add(
        proposition,
        topic=f"lab/teams/{team_name}",
        verified_by=[
            f"claude:team:{team_name}",
            f"from:{msg.sender}",
            f"to:{msg.recipient}",
        ],
        principal=agent_principal("team", team_name, msg.sender),
        chronicle=True,
        meta_narrative=True,
        confidence=CHRONICLE_CONFIDENCE,
    )
