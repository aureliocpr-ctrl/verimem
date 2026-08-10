"""R31: Oracle query — one-call cross-tier memory retrieval.

Combines:
  - episodes (Jaccard similarity on task_text)
  - facts (Jaccard on proposition)
  - skills (Jaccard on trigger)

Plus aggregated confidence verdict using R3 metacognition logic.
"""
from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")


def _tokens(text: str) -> set[str]:
    """I token che portano ARGOMENTO, senza le parole vuote.

    Misurato il 2026-08-01 sul corpus vero: alla domanda «quale versione di
    Kubernetes usa il cluster OnlyPaws» l'oracolo citava «il colore preferito di
    un cliente e' il blu», perche'::

        comuni : ['di', 'il']
        jaccard: 0.1538   >=  min_sim 0.1

    Le uniche parole in comune erano DUE PREPOSIZIONI, e bastavano a superare la
    soglia. La similarita' misurava i connettivi della lingua, non l'argomento.

    La soglia NON si tocca: alzarla sarebbe un numero scelto a occhio, l'errore
    gia' pagato tre volte questa settimana. Si toglie dal conto cio' che non
    porta informazione — e la lista non si riscrive, e' quella che
    `document_index` usa gia' per lo stesso identico motivo su un altro tool.
    Due copie divergono, e questo repo l'ha gia' pagata.
    """
    from .document_index import _PAROLE_VUOTE
    return {t.lower() for t in _TOKEN_RE.findall(text or "")
            if t.lower() not in _PAROLE_VUOTE}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def oracle_query(
    *,
    query: str,
    episodes: list[Any],
    facts: list[Any],
    skills: list[Any],
    top_k_each: int = 5,
    min_sim: float = 0.1,
) -> dict[str, Any]:
    """Cross-tier memory retrieval for a single query."""
    q_tokens = _tokens(query)
    if not q_tokens:
        return {
            "query": query,
            "episodes": [], "facts": [], "skills": [],
            "confidence": "none",
            "n_results": 0,
        }

    # Episodes
    ep_scored: list[tuple[float, Any]] = []
    for e in episodes:
        sim = _jaccard(q_tokens, _tokens(getattr(e, "task_text", "")))
        if sim >= min_sim:
            ep_scored.append((sim, e))
    ep_scored.sort(key=lambda x: -x[0])
    episodes_out = [
        {
            "id": getattr(e, "id", ""),
            "task_text": getattr(e, "task_text", "")[:80],
            "outcome": getattr(e, "outcome", ""),
            "similarity": round(sim, 3),
        }
        for sim, e in ep_scored[:top_k_each]
    ]

    # Facts
    fact_scored: list[tuple[float, Any]] = []
    for f in facts:
        sim = _jaccard(q_tokens, _tokens(getattr(f, "proposition", "")))
        if sim >= min_sim:
            fact_scored.append((sim, f))
    fact_scored.sort(key=lambda x: -x[0])
    facts_out = [
        {
            "id": getattr(f, "id", ""),
            "proposition": getattr(f, "proposition", "")[:120],
            "topic": getattr(f, "topic", ""),
            "similarity": round(sim, 3),
        }
        for sim, f in fact_scored[:top_k_each]
    ]

    # Skills
    sk_scored: list[tuple[float, Any]] = []
    for s in skills:
        if getattr(s, "status", "") == "retired":
            continue
        sim = _jaccard(q_tokens, _tokens(getattr(s, "trigger", "")))
        if sim >= min_sim:
            sk_scored.append((sim, s))
    sk_scored.sort(key=lambda x: -x[0])
    skills_out = [
        {
            "id": getattr(s, "id", ""),
            "name": getattr(s, "name", ""),
            "trigger": getattr(s, "trigger", "")[:80],
            "similarity": round(sim, 3),
        }
        for sim, s in sk_scored[:top_k_each]
    ]

    # Aggregate confidence: max similarity across all results
    max_sims = []
    if ep_scored: max_sims.append(ep_scored[0][0])
    if fact_scored: max_sims.append(fact_scored[0][0])
    if sk_scored: max_sims.append(sk_scored[0][0])
    overall = max(max_sims) if max_sims else 0.0
    if overall < 0.3:
        conf = "none"
    elif overall < 0.5:
        conf = "low"
    elif overall < 0.7:
        conf = "medium"
    else:
        conf = "high"

    n_total = len(episodes_out) + len(facts_out) + len(skills_out)

    return {
        "query": query,
        "episodes": episodes_out,
        "facts": facts_out,
        "skills": skills_out,
        "confidence": conf,
        "n_results": n_total,
    }


__all__ = ["oracle_query"]
