"""Cycle #80 — project-scoped briefing aggregator.

Resolves P1 from cycle 2026-05-16 stress-test (fact c019d5a21be6):
engram-proactive UserPromptSubmit hook uses cosine top-3 only, too
narrow when the user mentions a SPECIFIC project. This tool pulls
together every fact under ``project/<name>/*`` plus the episodes
touched by their lineage plus the visible supersession chains, and
returns them in one structured payload with a deterministic narrative
summary string.

Companion to:
  - hippo_briefing (FORGIA #214): generic, cross-project session start
  - hippo_summary_topic (cycle #79): generic topic glob aggregator

This tool is more opinionated: it assumes the standard topic naming
convention ``project/<name>/*`` and the agent shape (semantic +
episodic memory). Pure-local, no LLM call.
"""
from __future__ import annotations

from typing import Any


def _safe_get_episode(memory: Any, ep_id: str) -> dict[str, Any] | None:
    """Best-effort fetch one episode by id from any duck-typed memory.

    Returns a small dict — id + created_at + task_text + outcome — when
    found, None otherwise. Resilient to memory implementations that
    raise on missing ids.
    """
    if memory is None:
        return None
    try:
        ep = memory.get(ep_id) if hasattr(memory, "get") else None
    except Exception:
        return None
    if ep is None:
        return None
    return {
        "id": getattr(ep, "id", ep_id),
        "task_text": getattr(ep, "task_text", "") or "",
        "outcome": getattr(ep, "outcome", "") or "",
        "created_at": float(getattr(ep, "created_at", 0.0) or 0.0),
    }


def _render_summary(
    *, project: str, n_total: int, n_live: int, n_superseded: int,
    n_episodes: int, n_topics: int, n_chains: int,
) -> str:
    """Deterministic single-line narrative summary."""
    if n_total == 0:
        return (
            f"Project '{project}': 0 fact in memoria. Nessun lavoro "
            "ancora salvato sotto questo namespace."
        )
    parts = [
        f"Project '{project}': {n_live} fact attivi",
    ]
    if n_superseded > 0:
        parts.append(f"+ {n_superseded} obsoleti")
    parts.append(f"distribuiti su {n_topics} sub-topic")
    if n_episodes > 0:
        parts.append(f"con {n_episodes} episode collegati nella lineage")
    if n_chains > 0:
        parts.append(f"e {n_chains} catena/e di supersession visibili")
    return ", ".join(parts) + "."


def briefing_by_project(
    agent: Any, project: str, *,
    max_facts: int = 20,
    n_episodes: int = 5,
) -> dict[str, Any]:
    """Cycle #80 — project-scoped briefing.

    Args:
        agent: object with ``.semantic`` (SemanticMemory) and
            ``.memory`` (EpisodicMemory-like). Duck-typed.
        project: short project name; the topic glob becomes
            ``project/<project>/*``.
        max_facts: cap on returned facts payload (counts always
            accurate via SemanticMemory.summary_topic).
        n_episodes: cap on returned related_episodes payload.

    Returns:
        dict with project / topic_glob / counts / topics_seen / facts
        / related_episodes / supersession_chains / summary.
    """
    project = (project or "").strip()
    topic_glob = f"project/{project}/*"
    summary_obj = agent.semantic.summary_topic(
        topic_glob, max_facts=max_facts, include_lineage=True,
    )

    # Build related_episodes: lookup each lineage_episode id and order
    # newest-first by created_at. Episodes not retrievable (orphan ids
    # in source_episodes) are silently dropped.
    eps: list[dict[str, Any]] = []
    for ep_id in summary_obj.get("lineage_episodes", []):
        ep = _safe_get_episode(getattr(agent, "memory", None), ep_id)
        if ep is not None:
            eps.append(ep)
    eps.sort(key=lambda e: -e["created_at"])
    related = eps[:max(0, int(n_episodes))]

    summary_str = _render_summary(
        project=project,
        n_total=summary_obj["n_total"],
        n_live=summary_obj["n_live"],
        n_superseded=summary_obj["n_superseded"],
        n_episodes=len(related),
        n_topics=len(summary_obj["topics_seen"]),
        n_chains=len(summary_obj["supersession_chains"]),
    )

    return {
        "project": project,
        "topic_glob": topic_glob,
        "n_total": summary_obj["n_total"],
        "n_live": summary_obj["n_live"],
        "n_superseded": summary_obj["n_superseded"],
        "topics_seen": summary_obj["topics_seen"],
        "facts": summary_obj["facts"],
        "related_episodes": related,
        "supersession_chains": summary_obj["supersession_chains"],
        "summary": summary_str,
    }


__all__ = ["briefing_by_project"]
