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

from ..semantic import Fact, SemanticMemory
from .inbox import InboxMessage

# Truncation bound for the proposition snippet. SemanticMemory does not
# enforce a hard limit, but giant propositions hurt embedding quality
# and clutter ``hippo_facts_search`` output. 2000 chars ≈ 500 BPE tokens.
_MAX_PROPOSITION_LEN = 2000


def _short_ts(timestamp: str) -> str:
    """Extract ``HH:MM:SS`` from an ISO8601 timestamp; passthrough else."""
    if len(timestamp) >= 19 and timestamp[10] == "T":
        return timestamp[11:19]
    return timestamp


def mirror_message(
    msg: InboxMessage,
    *,
    sm: SemanticMemory,
    team_name: str,
    include_idle: bool = False,
) -> str | None:
    """Persist one inbox message as a HippoAgent Fact.

    Returns the newly-stored Fact id, or ``None`` if the message was
    skipped (currently: ``is_idle_notification`` with ``include_idle=False``).
    """
    if msg.is_idle_notification and not include_idle:
        return None

    snippet = msg.text[:_MAX_PROPOSITION_LEN]
    ts = _short_ts(msg.timestamp)
    proposition = f"[{msg.sender} → {msg.recipient} @{ts}] {snippet}"

    fact = Fact(
        proposition=proposition,
        topic=f"lab/teams/{team_name}",
        confidence=1.0,
        verified_by=[
            f"claude:team:{team_name}",
            f"from:{msg.sender}",
            f"to:{msg.recipient}",
        ],
        status="model_claim",
    )
    sm.store(fact)
    return fact.id
