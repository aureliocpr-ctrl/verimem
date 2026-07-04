"""Cycle #113.A (2026-05-17) — eval retrieval against ground truth.

Consumes the JSON envelope from ``build_retrieval_groundtruth.py``
and runs each query through one or more SemanticMemory recall paths,
computing precision@k / recall@k / MRR / latency_ms against the
``expected_fact_ids`` set for that query.

Recall paths v1 (minimal, only those that return fact ids directly):

* ``facts_cosine_default``  — SemanticMemory.recall(query, k=k),
  default flags (no legacy, no min_status).
* ``facts_cosine_with_legacy``  — same but include_legacy=True.
  Reveals how much legacy_unverified noise affects ranking.
* ``facts_keyword``  — SemanticMemory.search_facts(query, limit=k).
  SQL LIKE substring; baseline for "does keyword work?"

Recall paths that return episode ids or entity ids (episodic recall,
KG PPR, etc) need a mapping step to translate to fact ids and are
deferred to v2 of this bench so we don't conflate scopes.

Output JSON shape::

    {
      "evaluated_at": <epoch>,
      "k": 10,
      "n_queries": <int>,
      "per_path": {
        "<path_name>": {
          "precision_at_k_mean": <float>,
          "recall_at_k_mean":    <float>,
          "mrr_mean":            <float>,
          "latency_ms_p50":      <float>,
          "latency_ms_p95":      <float>,
          "n_queries":           <int>,
          "per_query": [ ... per-query detail ... ]
        },
        ...
      }
    }

CLI usage::

    python -m benchmark.eval_retrieval_with_gt \
        --groundtruth benchmark/results/cycle113-groundtruth-...json \
        --output      benchmark/results/cycle113-eval-...json \
        --k 10
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from benchmark.retrieval_metrics import mrr, precision_at_k, recall_at_k
from engram.semantic import SemanticMemory


def _run_facts_cosine(
    sm: SemanticMemory, query: str, k: int, *,
    exclude_legacy: bool,
) -> list[str]:
    """Run SemanticMemory.recall and return ordered fact ids.

    Default behaviour of SemanticMemory.recall: legacy_unverified rows
    are INCLUDED (no filter) and superseded rows are EXCLUDED
    (cycle #78). The bench varies ``exclude_legacy`` to measure how
    much noise the legacy_unverified inheritance contributes.
    """
    hits = sm.recall(query, k=k, exclude_legacy=exclude_legacy)
    return [f.id for f, _sim in hits]


def _run_facts_keyword(
    sm: SemanticMemory, query: str, k: int,
) -> list[str]:
    """Run SemanticMemory.search_facts (SQL LIKE) with the FULL query
    as one substring. Cycle #113.A noted this is ~always 0% on long
    task_text queries because no proposition contains a 120-char
    substring verbatim. Kept as a control to show how bad naive LIKE
    is on natural-language queries.
    """
    facts = sm.search_facts(query, limit=k)
    return [f.id for f in facts]


# Minimal stop-word list (IT + EN) — kept small to avoid dropping
# domain terms that happen to look generic.
_STOPWORDS: frozenset[str] = frozenset({
    # English common
    "the", "a", "an", "of", "and", "or", "to", "is", "are", "was",
    "were", "be", "in", "on", "at", "for", "with", "by", "from", "as",
    "this", "that", "it", "its", "if", "then", "but", "not", "no",
    "do", "does", "did", "has", "have", "had", "what", "which", "who",
    "how", "why", "where", "when",
    # Italian common
    "il", "la", "lo", "le", "gli", "un", "una", "uno", "di", "del",
    "della", "dei", "degli", "delle", "che", "con", "per",
    "su", "tra", "fra", "non", "ma", "se", "come", "quando", "cosa",
    "quale", "chi", "dove", "perche", "perché",
})

# Tokenize: split on non-alphanumeric, lower-case, drop short tokens
# and stopwords. We keep length >= 4 to avoid noisy mini-words while
# preserving domain abbreviations like "kg" via the >=2 fallback for
# uppercase originals.
_TOKEN_SPLIT_RE = __import__("re").compile(r"[^A-Za-z0-9_.]+")


def _tokenize_for_keyword(query: str, *, max_tokens: int = 8) -> list[str]:
    """Extract informative tokens from a natural-language query.

    Strategy:
      1. Split on non-alphanumeric.
      2. Lower-case.
      3. Drop stopwords + tokens shorter than 4 chars unless they
         start with an uppercase letter in the original (e.g. "NEXUS",
         "S4-D", "KG") — those are likely domain abbreviations.
      4. Sort by length desc (longer == more informative on average).
      5. Cap at ``max_tokens`` to bound the SQL fan-out.

    Returns the de-duplicated, order-preserving list of tokens.
    """
    raw_tokens = _TOKEN_SPLIT_RE.split(query or "")
    out: list[str] = []
    seen: set[str] = set()
    for t in raw_tokens:
        if not t:
            continue
        lowered = t.lower()
        is_acronym = t.isupper() and len(t) >= 2
        if lowered in _STOPWORDS:
            continue
        if not is_acronym and len(lowered) < 4:
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        out.append(lowered)
    # Longer tokens first — heuristic for "more informative".
    out.sort(key=len, reverse=True)
    return out[:max_tokens]


def _run_facts_keyword_tokens(
    sm: SemanticMemory, query: str, k: int,
) -> list[str]:
    """Tokenized keyword retrieval: split the query into informative
    tokens, run a separate ``search_facts`` per token, aggregate by
    token-hit count.

    Ranking: fact_id sorted by descending number of distinct tokens
    that matched its proposition. Ties broken by first appearance.
    Top-k returned.
    """
    tokens = _tokenize_for_keyword(query)
    if not tokens:
        return []
    hit_count: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    fetch_cap = max(k * 4, 50)
    for token in tokens:
        facts = sm.search_facts(token, limit=fetch_cap)
        for f in facts:
            if f.id not in first_seen:
                first_seen[f.id] = len(first_seen)
            hit_count[f.id] = hit_count.get(f.id, 0) + 1
    if not hit_count:
        return []
    ranked = sorted(
        hit_count.items(),
        key=lambda kv: (-kv[1], first_seen[kv[0]]),
    )
    return [fact_id for fact_id, _count in ranked[:k]]


# Recall path registry. Each callable takes (sm, query, k) and returns
# an ordered list of fact ids (the top-k retrieval result).
# Base paths first (no recursion), then fused paths that depend on them.
_RECALL_PATHS_BASE: dict[str, Any] = {
    "facts_cosine_with_legacy": (
        lambda sm, q, k: _run_facts_cosine(sm, q, k, exclude_legacy=False)
    ),
    "facts_cosine_trusted_only": (
        lambda sm, q, k: _run_facts_cosine(sm, q, k, exclude_legacy=True)
    ),
    "facts_keyword": (
        lambda sm, q, k: _run_facts_keyword(sm, q, k)
    ),
    "facts_keyword_tokens": (
        lambda sm, q, k: _run_facts_keyword_tokens(sm, q, k)
    ),
}


def _run_facts_rrf(
    sm: SemanticMemory,
    query: str,
    k: int,
    *,
    paths_to_fuse: tuple[str, ...],
    rrf_k: int = 60,
    fetch_multiplier: int = 2,
) -> list[str]:
    """Cycle #113.C: Reciprocal Rank Fusion of multiple BASE paths.

    For each path in ``paths_to_fuse``, run the underlying retriever
    asking for ``k * fetch_multiplier`` candidates (so the fusion has
    room to re-rank), then score each fact id by::

        score(fact_id) = sum over paths: 1 / (rrf_k + rank_in_path)

    Items appearing in multiple paths at high ranks dominate. Ties
    broken by the score (no stable secondary key — RRF is robust
    enough on its own).

    Reference: Cormack, Clarke, Buettcher (2009) "Reciprocal Rank
    Fusion outperforms Condorcet and individual Rank Learning Methods".
    Default ``rrf_k=60`` is the value from that paper, robust on TREC
    benchmarks.
    """
    if not paths_to_fuse:
        return []
    scores: dict[str, float] = {}
    fetch_k = max(k, 1) * max(1, fetch_multiplier)
    for path_name in paths_to_fuse:
        if path_name not in _RECALL_PATHS_BASE:
            raise KeyError(
                f"RRF fusion: unknown base path {path_name!r}; "
                f"known: {sorted(_RECALL_PATHS_BASE)}"
            )
        runner = _RECALL_PATHS_BASE[path_name]
        retrieved = runner(sm, query, fetch_k)
        for rank, item_id in enumerate(retrieved, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (rrf_k + rank)
    if not scores:
        return []
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    return [item_id for item_id, _score in ranked[:k]]


# Full registry: base paths + fusion paths (RRF reuses base lookup).
_RECALL_PATHS: dict[str, Any] = {
    **_RECALL_PATHS_BASE,
    "facts_rrf_cosine_tokens": (
        # Cycle #113.C: RRF of cosine_with_legacy + keyword_tokens.
        # Hypothesis: combines cosine's strong MRR with tokens'
        # strong P@10/R@10.
        lambda sm, q, k: _run_facts_rrf(
            sm, q, k,
            paths_to_fuse=("facts_cosine_with_legacy", "facts_keyword_tokens"),
        )
    ),
}


def _percentile(values: list[float], p: float) -> float:
    """Numpy-free percentile: nearest-rank, monotonic in p."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    rank = (p / 100.0) * (len(s) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(s) - 1)
    frac = rank - lo
    return float(s[lo] + frac * (s[hi] - s[lo]))


def evaluate_path(
    sm: SemanticMemory,
    queries: list[dict[str, Any]],
    *,
    path_name: str,
    k: int,
) -> dict[str, Any]:
    """Run one recall path across all queries and compute aggregate metrics."""
    if path_name not in _RECALL_PATHS:
        raise KeyError(
            f"unknown recall path {path_name!r}; "
            f"known: {sorted(_RECALL_PATHS)}"
        )
    runner = _RECALL_PATHS[path_name]
    precisions: list[float] = []
    recalls: list[float] = []
    mrrs: list[float] = []
    latencies_ms: list[float] = []
    per_query: list[dict[str, Any]] = []

    for q in queries:
        query_text = q["query"]
        relevant = set(q["expected_fact_ids"])
        t0 = time.perf_counter()
        retrieved = runner(sm, query_text, k)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        p = precision_at_k(retrieved, relevant, k=k)
        r = recall_at_k(retrieved, relevant, k=k)
        m = mrr(retrieved, relevant)
        precisions.append(p)
        recalls.append(r)
        mrrs.append(m)
        latencies_ms.append(elapsed_ms)
        per_query.append({
            "episode_id": q["episode_id"],
            "n_expected": q["n_expected"],
            "n_retrieved": len(retrieved),
            "precision_at_k": round(p, 4),
            "recall_at_k": round(r, 4),
            "mrr": round(m, 4),
            "latency_ms": round(elapsed_ms, 2),
        })

    return {
        "precision_at_k_mean": round(statistics.fmean(precisions), 4) if precisions else 0.0,
        "recall_at_k_mean":    round(statistics.fmean(recalls), 4) if recalls else 0.0,
        "mrr_mean":            round(statistics.fmean(mrrs), 4) if mrrs else 0.0,
        "latency_ms_p50":      round(_percentile(latencies_ms, 50), 2),
        "latency_ms_p95":      round(_percentile(latencies_ms, 95), 2),
        "n_queries":           len(queries),
        "per_query":           per_query,
    }


def evaluate_all(
    sm: SemanticMemory,
    groundtruth: dict[str, Any],
    *,
    k: int,
    paths: list[str] | None = None,
) -> dict[str, Any]:
    """Run every requested path against the ground truth envelope."""
    queries = groundtruth.get("queries", [])
    selected = paths if paths is not None else sorted(_RECALL_PATHS)
    per_path: dict[str, Any] = {}
    for name in selected:
        per_path[name] = evaluate_path(
            sm, queries, path_name=name, k=k,
        )
    return {
        "evaluated_at": time.time(),
        "k": k,
        "n_queries": len(queries),
        "groundtruth_built_at": groundtruth.get("built_at"),
        "per_path": per_path,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate retrieval paths against ground truth.",
    )
    parser.add_argument(
        "--groundtruth", type=Path, required=True,
        help="Path to the ground-truth JSON produced by build_retrieval_groundtruth.",
    )
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Path to write the eval JSON envelope.",
    )
    parser.add_argument(
        "--k", type=int, default=10,
        help="Top-k for retrieval and metric computation.",
    )
    parser.add_argument(
        "--paths", nargs="*", default=None,
        help="Restrict to a subset of recall paths.",
    )
    args = parser.parse_args(argv)

    gt = json.loads(args.groundtruth.read_text(encoding="utf-8"))
    sm = SemanticMemory()
    envelope = evaluate_all(
        sm, gt, k=args.k, paths=args.paths,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(envelope, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote eval envelope to {args.output}")
    print(f"k={args.k}, n_queries={envelope['n_queries']}")
    for name, data in envelope["per_path"].items():
        print(
            f"  {name:30s}  P@{args.k}={data['precision_at_k_mean']:.3f}  "
            f"R@{args.k}={data['recall_at_k_mean']:.3f}  "
            f"MRR={data['mrr_mean']:.3f}  "
            f"lat_p50={data['latency_ms_p50']:.1f}ms  "
            f"lat_p95={data['latency_ms_p95']:.1f}ms"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
