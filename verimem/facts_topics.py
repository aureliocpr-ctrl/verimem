"""Facts grouped by topic.

FORGIA pezzo #222 — Wave 21. Lets the user see "quali argomenti ho
memorizzato?" without paginating hundreds of facts.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .fact_contract import fact_payload

_FALLBACK_TOPIC = "(no topic)"


def facts_topics(
    facts: list[Any],
    *,
    n_samples: int = 3,
    top_k_topics: int = 30,
) -> dict[str, Any]:
    """Group facts by their `topic` field.

    Args:
      - `facts`: iterable of fact-likes (`.id`, `.proposition`,
        `.topic`).
      - `n_samples`: number of sample propositions per topic.
      - `top_k_topics`: cap on returned topics, sorted by count DESC.

    Returns: `{n_total, topics: [{topic, count, sample_facts}, ...]}`.
    """
    by_topic: dict[str, list[Any]] = defaultdict(list)
    for f in facts:
        topic = getattr(f, "topic", "") or _FALLBACK_TOPIC
        by_topic[topic].append(f)

    rows: list[dict[str, Any]] = []
    for topic, items in by_topic.items():
        # 2026-07-30: i campioni sono fatti veri, non una statistica, quindi
        # passano dal contratto unico (fact_contract.fact_payload) con
        # l'anteprima corta che questa vista aveva gia'. Chi sfoglia i topic
        # per capire cosa c'e' dentro decide anche cosa fidarsi di leggere.
        sample = [
            {**fact_payload(it),
             "proposition": (getattr(it, "proposition", "") or "")[:200]}
            for it in items[:n_samples]
        ]
        rows.append({
            "topic": topic,
            "count": len(items),
            "sample_facts": sample,
        })

    rows.sort(key=lambda r: -r["count"])
    return {
        "n_total": len(facts),
        "topics": rows[:top_k_topics],
    }


__all__ = ["facts_topics"]
