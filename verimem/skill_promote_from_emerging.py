"""Cycle 235 (2026-05-23) — promote emerging_skill fact → Skill row.

Closes the discovery → adoption loop end-to-end:

  detect (213)
    → normalize (214/215)
    → draft (217)
    → persist disk (222)
    → register as fact (229)
    → REGISTER AS SKILL (235) ← here
    → promote_or_retire on trials (existing cycle 144)

A4 honest contract:
  - New Skill has ``status='candidate'`` NOT ``'promoted'``.
  - ``stage='manual'`` to distinguish from NREM/REM consolidation.
  - ``provenance_episodes`` records the SOURCE FACT id (not an
    episode — the lineage is fact → skill, not episode → skill).
    Field reused for traceability since SkillLibrary does not yet
    expose a ``provenance_facts`` field.
  - ``trigger_keywords`` from the fact's keywords list (parsed from
    the proposition text).
"""
from __future__ import annotations

import re
from typing import Any

from verimem.skill import Skill

_EMERGING_TOPIC_PREFIX = "emerging_skill/"

#: Match the "Trigger keywords: a, b, c" line in cycle-229
#: registered-fact propositions.
_KW_LINE_RE = re.compile(r"Trigger keywords:\s*(.+)", re.IGNORECASE)

#: Match topic suffix after the prefix (cycle 229 convention is
#: ``emerging_skill/auto-discovered/<name>``).
_TOPIC_LEAF_RE = re.compile(r"emerging_skill/[^/]+/(.+)$", re.IGNORECASE)


def _name_slug(fact: dict[str, Any]) -> str:
    """Derive a Skill.name slug from the fact topic."""
    topic = str(fact.get("topic", "") or "")
    m = _TOPIC_LEAF_RE.search(topic)
    leaf = m.group(1) if m else topic
    # Strip the ``emerging_skill_`` prefix if the leaf carries it.
    leaf = re.sub(r"^emerging_skill_", "", leaf)
    return leaf.strip() or "auto_skill"


def _extract_keywords(proposition: str) -> list[str]:
    """Pull the comma-list out of the 'Trigger keywords: ...' line."""
    m = _KW_LINE_RE.search(proposition or "")
    if not m:
        return []
    raw = m.group(1).strip()
    # Stop at the next newline section header.
    raw = raw.split("\n")[0]
    parts = [k.strip() for k in raw.split(",")]
    return [k for k in parts if k]


def promote_emerging_to_skill(
    fact: dict[str, Any],
    library: Any,
) -> dict[str, Any]:
    """Convert an ``emerging_skill/*`` fact into a candidate Skill row.

    Args:
        fact: dict with at least ``id``, ``proposition``, ``topic``.
            Topic MUST start with ``emerging_skill/`` (raises ValueError
            otherwise — explicit guard against accidentally promoting
            arbitrary facts).
        library: a ``SkillLibrary`` instance (or any object exposing
            ``store(Skill)``, ``get(id)``, ``all()``).

    Returns:
        ``{"skill_id": str, "name": str, "was_replaced": bool}``.

    Raises:
        ValueError: if the fact topic does not match
            ``emerging_skill/*``.
    """
    topic = str(fact.get("topic", "") or "")
    if not topic.lower().startswith(_EMERGING_TOPIC_PREFIX):
        raise ValueError(
            f"fact topic must start with '{_EMERGING_TOPIC_PREFIX}' "
            f"to be eligible for promotion (got: {topic!r})",
        )

    name = _name_slug(fact)
    keywords = _extract_keywords(str(fact.get("proposition", "") or ""))
    trigger_text = ", ".join(keywords) if keywords else name

    # Deterministic skill id derived from the source fact id so
    # repeated promotion is idempotent (Skill.id default is random
    # uuid; we override).
    fact_id = str(fact.get("id", "") or "")
    skill_id = f"emerg_{fact_id[:10]}" if fact_id else None

    # Body carries the proposition verbatim so a reviewer can see the
    # evidence + draft that originated this skill.
    body = (
        f"# {name} (auto-discovered candidate skill)\n\n"
        f"Source fact id: {fact_id}\n"
        f"Source topic: {topic}\n\n"
        f"## Auto-generated rationale\n"
        f"{fact.get('proposition', '')}\n"
    )

    rationale = (
        "Auto-discovered via cycle 213 community detection + cycle 217 "
        "deterministic drafter + cycle 229 fact registration. Promoted "
        "to candidate skill via cycle 235. NOT yet trial-validated."
    )

    skill = Skill(
        id=skill_id or "",  # Skill default will fill in if None-equivalent
        version=1,
        name=name,
        trigger=trigger_text,
        body=body,
        rationale=rationale,
        stage="manual",
        provenance_episodes=[fact_id] if fact_id else [],
        status="candidate",
    )
    # If the caller passed an empty id, restore the Skill default uuid.
    if not skill.id:
        # Recreate; Skill dataclass default factory used.
        skill = Skill(
            version=1, name=name, trigger=trigger_text,
            body=body, rationale=rationale,
            stage="manual",
            provenance_episodes=[fact_id] if fact_id else [],
            status="candidate",
        )

    # Idempotency: if a skill with this id already exists, store()
    # uses INSERT OR REPLACE (cycle 144 default). To make the test
    # contract clear, we surface a ``was_replaced`` flag.
    was_replaced = library.get(skill.id) is not None
    library.store(skill)

    return {
        "skill_id": skill.id,
        "name": skill.name,
        "was_replaced": was_replaced,
    }


__all__ = ["promote_emerging_to_skill"]
