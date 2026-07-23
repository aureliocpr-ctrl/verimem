"""Shared helpers for the orchestration layer's gated memory writes.

The swarm and teams bridges relay agent-authored text into verimem. Two
concerns are common to both and live here so they cannot drift apart:

* :func:`agent_principal` — compose the server-side ``writer_principal``
  for an orchestration write, as ``<prefix>:<part>/<part>`` (e.g.
  ``team:alpha/python-engineer``, ``swarm:run1/worker-a``). The trusted
  literal prefix stays verbatim; every attacker-influenced part (an inbox
  ``from`` field, a team name that might contain slashes) is SANITIZED to
  a single ``[A-Za-z0-9_-]`` segment. Adversarial review finding 3: the
  principal records what the native inbox *declared* — surface
  attribution, not a cryptographic binding; the unforgeable-sender
  channel is the cycle-2 HMAC transport. Sanitizing keeps a hostile name
  from smuggling separators/traversal into the identity or colliding with
  another namespace.

* :data:`CHRONICLE_CONFIDENCE` — the fixed low confidence every
  orchestration chronicle row carries, so an archived quotation ranks
  below an ordinary claim and can never masquerade as a strong fact.
"""
from __future__ import annotations

import re

#: Confidence for an inter-agent / orchestration chronicle row. Below the
#: 0.5 default of an ordinary claim: archived context, never a strong fact.
CHRONICLE_CONFIDENCE = 0.3

# One identity SEGMENT: any run of chars outside the unreserved id set is
# collapsed to a single '-'. Bans '/' and ':' (the principal separators)
# and '.' (so no '..' traversal survives), leaving [A-Za-z0-9_-].
_SEG_STRIP = re.compile(r"[^A-Za-z0-9_-]+")


def _sanitize_segment(value: str, *, fallback: str) -> str:
    """Collapse a name to a single safe identity segment.

    Empty / all-illegal input degrades to ``fallback`` so the composed
    principal is never malformed (e.g. ``team:alpha/`` with an empty
    sender).
    """
    cleaned = _SEG_STRIP.sub("-", (value or "").strip()).strip("-")
    return cleaned or fallback


def agent_principal(prefix: str, *parts: str, name_fallback: str = "unknown") -> str:
    """Compose ``<prefix>:<seg>/<seg>/...`` with every part sanitized.

    ``prefix`` is a trusted literal from our own code (``team`` / ``swarm``)
    — kept verbatim, it is the only part carrying the ``:`` namespace
    separator. Each ``part`` (team name, sender, run id, agent) is
    attacker-influenced and reduced to a single safe segment, so no part
    can inject a ``/`` or ``:`` and forge a different identity.
    """
    segs = "/".join(
        _sanitize_segment(p, fallback=name_fallback) for p in parts)
    return f"{prefix}:{segs}"
