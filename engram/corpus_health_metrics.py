"""Cycle #84 — corpus_health_metrics unified dashboard aggregator.

One pure-local read pass over the semantic store producing all the
health-signal numbers a user needs to assess the corpus state:
totals, supersession chains, topic taxonomy, freshness buckets.

No embeddings, no LLM. Designed to be cheap enough to call as the
landing page of a dashboard.
"""
from __future__ import annotations

import time
from typing import Any

from . import embedding
from .semantic import SemanticMemory


def corpus_health_metrics(
    semantic: SemanticMemory, *,
    top_topics_k: int = 10,
) -> dict[str, Any]:
    """Compute health metrics for the corpus.

    Args:
        semantic: SemanticMemory instance (or duck-typed equivalent).
        top_topics_k: cap on the top_topics list (default 10).

    Returns:
        dict with totals, chains, taxonomy, freshness fields.
    """
    now = time.time()
    day = 86400.0

    with semantic._connect() as conn:
        n_total = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        n_superseded = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL"
        ).fetchone()[0]
        n_live = n_total - n_superseded

        # Top topics by count (live only)
        rows = conn.execute(
            "SELECT topic, COUNT(*) c FROM facts WHERE superseded_by IS NULL "
            "AND topic != '' GROUP BY topic ORDER BY c DESC LIMIT ?",
            (int(top_topics_k),),
        ).fetchall()
        top_topics = [{"topic": r[0], "count": int(r[1])} for r in rows]

        n_facts_no_topic = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE topic = '' OR topic IS NULL"
        ).fetchone()[0]

        # Freshness buckets (live facts only)
        cutoff_24h = now - 1 * day
        cutoff_7d = now - 7 * day
        cutoff_30d = now - 30 * day
        n_recent_24h = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL "
            "AND created_at >= ?", (cutoff_24h,),
        ).fetchone()[0]
        n_recent_7d = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL "
            "AND created_at >= ?", (cutoff_7d,),
        ).fetchone()[0]
        n_stale_30d = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL "
            "AND created_at < ?", (cutoff_30d,),
        ).fetchone()[0]

        # Embedding consistency: ogni fatto recall-eligible deve essere
        # all'embedding model+dim ATTIVI; altrimenti e' SILENZIOSAMENTE escluso
        # dal recall (model-gate + byte-filter). n_embedding_dark > 0 = corpus
        # inconsistente (es. migrazione/flip modello incompleta). Lo scope
        # "eligible" combacia con quello del re-embed (superseded esclusi).
        active_model = embedding.model_signature()
        exp_bytes = embedding.expected_embedding_bytes()
        _eligible = (
            "superseded_by IS NULL "
            "AND status NOT IN ('quarantined','orphaned') "
            "AND length(proposition) > 0"
        )
        n_recall_eligible = conn.execute(
            f"SELECT COUNT(*) FROM facts WHERE {_eligible}"
        ).fetchone()[0]
        n_embedding_dark = conn.execute(
            f"SELECT COUNT(*) FROM facts WHERE {_eligible} "
            "AND (embedding_model IS NULL OR embedding_model != ? "
            "OR length(embedding) != ?)",
            (active_model, exp_bytes),
        ).fetchone()[0]

        # Quarantined = unverified claims the anti-confab gate held OUT of
        # recall. Reporting it next to n_recallable makes the headline honest:
        # n_live (= total - superseded) counts quarantined too, so a corpus that
        # is 44% quarantined would look "mostly live/ready" without this split.
        n_quarantined = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE status = 'quarantined'"
        ).fetchone()[0]
        # What recall can ACTUALLY return: eligible AND embedded at the active
        # model (eligible minus the silently-excluded dark vectors).
        n_recallable = n_recall_eligible - n_embedding_dark

        # Chains: every fact with superseded_by != NULL is potentially the
        # head of a chain. Reduce to distinct CHAIN HEADS (facts pointing
        # to something but NOTHING points to them) for accurate count.
        super_rows = conn.execute(
            "SELECT id, superseded_by FROM facts "
            "WHERE superseded_by IS NOT NULL"
        ).fetchall()

    # Find chain heads: anchors that ARE NOT the new_id of any other
    # superseded mapping. This filters chain-middle elements out.
    all_old = {r[0] for r in super_rows}
    all_new = {r[1] for r in super_rows}
    head_anchors = sorted(all_old - all_new)

    chain_lengths: list[int] = []
    for anchor in head_anchors:
        walked = semantic.get_supersession_chain(anchor)
        chain_lengths.append(len(walked))

    n_chains = len(chain_lengths)
    max_chain_length = max(chain_lengths) if chain_lengths else 0
    avg_chain_length = (
        round(sum(chain_lengths) / n_chains, 3) if n_chains > 0 else 0
    )

    return {
        "n_total": int(n_total),
        "n_live": int(n_live),
        "n_superseded": int(n_superseded),
        "n_chains": n_chains,
        "avg_chain_length": avg_chain_length,
        "max_chain_length": max_chain_length,
        "top_topics": top_topics,
        "n_facts_no_topic": int(n_facts_no_topic),
        "n_recent_24h": int(n_recent_24h),
        "n_recent_7d": int(n_recent_7d),
        "n_stale_30d": int(n_stale_30d),
        "n_recall_eligible": int(n_recall_eligible),
        "n_embedding_dark": int(n_embedding_dark),
        "n_quarantined": int(n_quarantined),
        "n_recallable": int(n_recallable),
        "active_embedding_model": active_model,
    }


__all__ = ["corpus_health_metrics"]
