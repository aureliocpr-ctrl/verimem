"""Cycle #150 (2026-05-19) — Engram Teams: bridge agent-teams ↔ HippoAgent.

Cycle 145 ha usato per la prima volta le primitive native ``agent-teams``
(``CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1``, ``TeamCreate``, ``SendMessage``,
``TeamDelete``). Il Mailbox è file-based: ``~/.claude/teams/<name>/inboxes/
<teammate>.json`` (JSON array, append-only). Verificato empiricamente cycle
150 leggendo i file reali del team ``engram-rd-lab`` (2026-05-07).

Cycle 150 NON ricostruisce nessuna primitiva nativa. Aggiunge solo lo
strato mancante:

  • ``InboxWatcher`` — polling incrementale dei file inbox del team
  • ``mirror_message`` — mirror dei messaggi su HippoAgent SemanticMemory
    su topic ``lab/teams/<name>`` per audit/recall/sopravvivenza a ``/resume``
  • CLI ``engram teams watch <team>`` — tail Rich Live multi-inbox
  • CLI ``engram teams send --to <name> --as <human> --message …`` —
    Aurelio inietta messaggi nell'inbox di un teammate dall'esterno
    senza dover possedere una sessione Claude Code

Anti-pattern evitato: NO wrapper su TeamCreate/SendMessage/TeamDelete
(sono già perfetti). NO subprocess spawn (era cycle 148 swarm, primitiva
sbagliata). NO broadcast log mascherato da chat (era cycle 145
incompletezza). Questo è il completamento serio di cycle 145.
"""
from __future__ import annotations

from .bridge import mirror_message
from .harness import CollabHarness
from .inbox import InboxMessage, InboxWatcher
from .protocol import CHARTER_TEMPLATE, TAG_NAMES, parse_protocol_tags

__all__ = [
    "CHARTER_TEMPLATE",
    "CollabHarness",
    "InboxMessage",
    "InboxWatcher",
    "TAG_NAMES",
    "mirror_message",
    "parse_protocol_tags",
]
