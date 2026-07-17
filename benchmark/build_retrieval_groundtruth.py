"""Cycle #113.A (2026-05-17) — build retrieval ground-truth via corpus mining.

Aurelio handoff cycle 112: il bench `bench_retrieval_baseline.py` misura
solo latency / Jaccard overlap. Per dire QUALCOSA sulla qualita' del
retrieval serve ground truth — ma non possiamo usare host LLM
sampling (Claude Code MCP host non supporta createMessage, lesson
cycle #71 BIS).

Soluzione: il corpus STESSO contiene il ground truth. Quando
`hippo_record_episode` viene chiamato con ``key_facts``, ogni fact
estratto ha ``source_episodes`` che punta a quel episode. Quindi:

    query        := episode.task_text  (naturale, scritto da un user)
    relevant_set := {fact.id : episode.id IN fact.source_episodes}

Questo da' ~N pairs (query, relevant) gratis senza sampling esterno.
Filtriamo via gli episode senza key_facts derivati (non hanno ground
truth utile).

Output JSON shape::

    {
      "built_at": <epoch>,
      "n_queries": <int>,
      "n_facts_total": <int>,
      "n_episodes_total": <int>,
      "queries": [
        {
          "episode_id": "<hex>",
          "query": "<task_text>",
          "expected_fact_ids": ["<fact_id>", ...],
          "n_expected": <int>
        },
        ...
      ]
    }

CLI usage::

    python -m benchmark.build_retrieval_groundtruth \
        --output benchmark/results/cycle113-groundtruth-YYYYMMDD.json

The output is consumed by ``eval_retrieval_with_gt.py`` which runs
each query through the 6 recall paths and computes precision@k /
recall@k / MRR against the relevant set.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory


def build_groundtruth(
    *,
    episodes: EpisodicMemory,
    semantic: SemanticMemory,
    min_query_chars: int = 8,
    max_queries: int | None = None,
) -> dict[str, Any]:
    """Walk the corpus and emit (query, relevant_fact_ids) pairs.

    Args:
        episodes: open EpisodicMemory instance.
        semantic: open SemanticMemory instance.
        min_query_chars: skip episodes whose task_text is shorter
            than this (avoids trivial "x" queries that pollute the
            metric).
        max_queries: cap on the number of pairs emitted. None = no cap.

    Returns:
        Dict with the JSON envelope documented in the module docstring.
        Pairs are sorted by episode_id for determinism.
    """
    # Build reverse index: episode_id -> {fact_id, ...}
    facts = semantic.all()
    rev: dict[str, set[str]] = {}
    for f in facts:
        for ep_id in (f.source_episodes or []):
            ep_id_s = (ep_id or "").strip()
            if not ep_id_s:
                continue
            rev.setdefault(ep_id_s, set()).add(f.id)

    eps = episodes.all(limit=10_000)
    pairs: list[dict[str, Any]] = []
    for ep in eps:
        task = (ep.task_text or "").strip()
        if len(task) < min_query_chars:
            continue
        relevant = sorted(rev.get(ep.id, set()))
        if not relevant:
            continue
        pairs.append({
            "episode_id": ep.id,
            "query": task,
            "expected_fact_ids": relevant,
            "n_expected": len(relevant),
        })
    pairs.sort(key=lambda p: p["episode_id"])
    if max_queries is not None:
        pairs = pairs[: max(0, int(max_queries))]
    return {
        "built_at": time.time(),
        "n_queries": len(pairs),
        "n_facts_total": len(facts),
        "n_episodes_total": len(eps),
        "queries": pairs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mine retrieval ground truth from HippoAgent corpus.",
    )
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Path to write the JSON envelope.",
    )
    parser.add_argument(
        "--min-chars", type=int, default=8,
        help="Skip episodes with task_text shorter than this.",
    )
    parser.add_argument(
        "--max-queries", type=int, default=None,
        help="Cap on emitted pairs (default: no cap).",
    )
    args = parser.parse_args(argv)

    episodes = EpisodicMemory()
    semantic = SemanticMemory()
    envelope = build_groundtruth(
        episodes=episodes, semantic=semantic,
        min_query_chars=args.min_chars,
        max_queries=args.max_queries,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(envelope, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        f"Wrote {envelope['n_queries']} (query,relevant) pairs "
        f"to {args.output} "
        f"(corpus: {envelope['n_episodes_total']} episodes, "
        f"{envelope['n_facts_total']} facts).",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
