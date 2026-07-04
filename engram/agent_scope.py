"""R4: Multi-agent memory namespacing — zero-schema convention.

When you have multiple specialised agents (pentester, reviewer,
architect, …) writing into the same HippoAgent instance, you want:

  - Per-agent scoping: pentester reads its own memories first
  - Shared knowledge: anyone can write to `shared/*`
  - Discoverability: filter, count, list by agent

We implement this via **topic prefix convention**:
  - Per-agent topic: `agent:<id>/<rest-of-topic>`
  - Shared topic:    `shared/<rest>` or any non-prefixed topic
  - Legacy topic:    `nexus/cve/...` — counts as "shared" if not under `agent:`

This needs no DB schema change. Works today with hippo_remember.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

_AGENT_PREFIX = "agent:"


def tag_for_agent(topic: str, *, agent_id: str) -> str:
    """Return the agent-scoped topic for `topic` under `agent_id`.

    Idempotent: if the topic is already scoped to the same agent,
    returns the input unchanged. Rejects agent_id containing `/`
    or other separators that would break parsing.
    """
    if not agent_id or "/" in agent_id or ":" in agent_id:
        raise ValueError(
            f"agent_id must be a simple identifier, got {agent_id!r}"
        )
    existing = agent_id_from_topic(topic)
    if existing == agent_id:
        return topic
    if existing is not None:
        # Different agent already — rewrap (rare but defensible)
        inner = topic.split("/", 1)[1] if "/" in topic else ""
        return f"{_AGENT_PREFIX}{agent_id}/{inner}"
    return f"{_AGENT_PREFIX}{agent_id}/{topic}"


def agent_id_from_topic(topic: str | None) -> str | None:
    """Extract agent_id from a topic, or None if not scoped.

    audit#3-r3 R14: delegate to :func:`engram.scope.parse_scope` so BOTH the
    legacy ``agent:<id>/...`` form AND the canonical B-1 form
    ``user:<u>/agent:<id>/...`` are recognized. The old ``^agent:`` regex only
    matched a LEADING ``agent:`` segment, so every canonically-scoped fact was
    misattributed to ``(shared)`` — blinding hippo_count_by_agent /
    hippo_agent_workload / hippo_agent_specialization / hippo_cross_agent_consensus
    (all of which route through this primitive) to multi-tenant memory.
    """
    if not topic:
        return None
    from .scope import parse_scope
    return parse_scope(topic).get("agent_id")


def filter_facts_by_agent(
    facts: list[Any],
    *,
    agent_id: str | None,
    include_shared: bool = False,
) -> list[Any]:
    """Filter facts by agent scope.

    Args:
      - `agent_id`: only return facts under `agent:<id>/...`.
        If None, returns facts WITHOUT any agent prefix (legacy + shared).
      - `include_shared`: when filtering by agent_id, also include facts
        without any agent prefix (treated as shared by convention).
    """
    out: list[Any] = []
    for f in facts:
        topic = getattr(f, "topic", "") or ""
        owner = agent_id_from_topic(topic)
        if agent_id is None:
            # Legacy / no-prefix mode
            if owner is None:
                out.append(f)
        else:
            if owner == agent_id:
                out.append(f)
            elif include_shared and owner is None:
                out.append(f)
    return out


def count_by_agent(facts: list[Any]) -> dict[str, int]:
    """Count facts per agent_id. Un-prefixed facts grouped as '(shared)'."""
    counter: Counter[str] = Counter()
    for f in facts:
        topic = getattr(f, "topic", "") or ""
        owner = agent_id_from_topic(topic)
        counter[owner if owner else "(shared)"] += 1
    return dict(counter)


__all__ = [
    "tag_for_agent",
    "agent_id_from_topic",
    "filter_facts_by_agent",
    "count_by_agent",
]
