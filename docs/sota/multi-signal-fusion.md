# SOTA — Multi-signal fusion for retrieval ranking (HippoAgent)

**Status**: documentation; closes task #69 (Gap-analysis SOTA MEDIUM — multi-signal fusion).
**Date**: 2026-05-23 (cycle 190).
**Scope**: gap analysis on combining multiple ranking signals
(semantic cosine + keyword overlap + recency + PageRank + community
membership + confidence + trust verdict) into a single retrieval
score. Companion to cycles 180 (anti-confab), 185 (community
detection), 188 (PageRank cache).

---

## 1. Motivation

HippoAgent already exposes several **ranking signals** but currently
the production recall path uses ONLY two of them:

| Signal | Source | Used in default recall? |
|--------|--------|--------------------------|
| Semantic cosine | `engram/semantic.py:recall` | ✓ primary |
| Keyword overlap | `engram/semantic.py:recall_hybrid` (cycle #161) | ✓ via hybrid |
| Recency (`created_at`) | `facts.created_at` column | ✗ tie-breaker only |
| PageRank centrality | `engram/hippo_pagerank.py` | ✗ separate query |
| Community membership | `engram/community_detector.py` (cycle 186) | ✗ not in recall |
| Confidence | `facts.confidence` | ✗ |
| Trust verdict | `engram/trust_signal.py` | ✗ optional |
| Fitness (skills) | `Skill.fitness_mean` | for skills only |

The cycle-161 hybrid weights cosine + keyword via a hard-coded
α (0.7 / 0.3). Six other signals are computed but ignored at
ranking time. SOTA retrieval systems fuse multiple signals via
**learning-to-rank** (LTR) or **reciprocal rank fusion** (RRF).

---

## 2. SOTA candidates (multi-signal fusion)

### 2.1 Reciprocal Rank Fusion (RRF) — Cormack et al. 2009

Simple, no training, no parameters except a smoothing constant
(default `k=60`):

```
score(d) = Σ_signal  1 / (k + rank_signal(d))
```

Each signal produces its own ranked list; RRF combines them by
summing 1/rank. **Critical advantage**: signal scores don't need to
be on the same scale (cosine ∈ [0,1] vs PageRank ∈ [0,~0.05] vs
recency in epoch seconds).

**Reference**: Cormack, Clarke, Buettcher 2009, "Reciprocal Rank
Fusion outperforms Condorcet and individual Rank Learning Methods".
Used today in Elasticsearch + Vespa + Weaviate hybrid search.

### 2.2 Learning-to-Rank (LTR) — Burges et al. 2005

Train a small gradient-boosted tree (LightGBM-style) on labelled
`(query, fact, relevance)` triples. Features = all 7-8 signals
above + query-side meta (length, recency-of-query).

**Pros**: optimal Bayes-rate combination.
**Cons**: needs labels we don't have. Synthetic labels via
`mcp__engram-bridge__falsify_claim` could bootstrap but introduce
a self-fulfilling loop.

**Verdict for HippoAgent**: defer until we have ≥ 500 labelled
recall events.

### 2.3 Weighted linear combination

```
score(d) = Σ_signal  w_signal · normalised_signal(d)
```

With normalisation (min-max or z-score) on each signal. Weights
hand-tuned or grid-searched on a held-out set.

**Pros**: trivial to implement.
**Cons**: requires per-signal normalisation; weights are brittle.

---

## 3. Recommended approach — RRF first, LTR later

For HippoAgent's current scale (~1.7k facts, ~10-100 recall events
per session), **RRF is the right primitive**:

1. **No training required** — production-ready immediately.
2. **Robust to scale mismatches** — handles cosine vs PageRank vs
   recency in a single formula.
3. **Easy to A/B-test** — toggle signals in/out by adding/removing
   the corresponding rank list.
4. **Composable with cycle-161 hybrid** — the hybrid result IS one
   of the rank lists fed into RRF, not a replacement.

When the corpus passes 10k facts AND we have ≥ 500 labelled events
(from operator clicks / `validate_claim` outcomes / skill fitness
updates), graduate to a LightGBM LTR model trained on those same
features. Cycle 200+ scope.

---

## 4. Design — `engram/multi_signal_fusion.py` (proposed cycle 191)

API sketch:

```python
def rrf_fuse(
    rank_lists: list[list[str]], *, k: float = 60.0,
) -> list[tuple[str, float]]:
    """Combine N ranked id lists into a single fused ranking.

    Args:
        rank_lists: each entry is an ordered list of fact_ids
            (best-first). Order = rank-1.
        k: RRF smoothing constant (Cormack default 60).

    Returns:
        Sorted ``[(fact_id, fused_score), ...]`` desc by score.
        ``fact_id``s present in only one list still appear.
    """

def fuse_recall(
    semantic_db: Path, *, query: str, k: int = 10,
    enabled_signals: set[str] = frozenset({"cosine", "keyword",
                                            "recency", "pagerank"}),
) -> list[str]:
    """High-level recall using RRF over enabled signals."""
```

Each signal is implemented as a thin wrapper that returns a ranked
list of fact_ids:

- `cosine`: reuse `engram.semantic.recall`
- `keyword`: reuse `engram.semantic.recall_hybrid` (cycle #161)
- `recency`: SQL `ORDER BY created_at DESC`
- `pagerank`: cycle 188 cached vectors (when available; falls back
  to `engram.hippo_pagerank` cold compute)
- `community`: facts in the same Louvain community as the top
  cosine hit (cycle 186)
- `confidence`: SQL `ORDER BY confidence DESC`
- `trust`: `engram.trust_signal` verdict in {verified, contested,
  ...}

---

## 5. Gap analysis (follow-up cycles)

| Gap | Severity | Suggested cycle |
|-----|----------|-----------------|
| **RRF primitive** | MAJOR | cycle 191 — pure function ``rrf_fuse``, 30 LOC + 8 TDD tests |
| **Per-signal rank-list builders** | MEDIUM | cycle 192 — 5 thin SQL wrappers |
| **fuse_recall orchestrator** | MAJOR | cycle 193 — splice into `recall_hybrid` as opt-in |
| **A/B bench: cycle-161 hybrid vs RRF-4-signal** | MEDIUM | cycle 194 — recall@5 on a 50-query held-out set |
| **LTR training pipeline** | DEFER | cycle 200+ — needs ≥ 500 labelled events |

### 5.1 Acceptance criteria — cycle 191 `rrf_fuse`

- TDD strict: identical lists → identical rankings;
  disjoint lists → both ids appear; constant `k=60` reproduces
  Cormack 2009 table 1 numbers.
- < 5ms on 10×100 lists.

### 5.2 Falsifiable hypothesis H4

After enabling RRF-4-signal recall (cycle 193), recall@5 on a 50-query
held-out set improves by ≥ 5% absolute against the cycle-161 hybrid
baseline. Falsification: delta ≤ 2% or negative → revert.

---

## 5.1 Implementation status — cycle 191/195/196/197 closure (2026-05-23, cycle 224)

The §4 RRF design has been implemented:

| Cycle | Module | What it ships |
|-------|--------|---------------|
| 191 | `engram/multi_signal_fusion.py` | `rrf_fuse(rank_lists, k=60)` — Cormack 2009 reciprocal rank fusion. Pure-Python, no dependencies. |
| 195 | `engram/time_decay_score.py` | `decay_score(t_delta, mode)` — exponential / power / linear. Provides recency signal. |
| 196 | `engram/rank_list_builders.py` | `recency_rank` / `confidence_rank` / `recency_decayed_rank` helpers — turn raw fact lists into per-signal ranks for RRF. |
| 197 | `engram/fuse_recall.py` | Orchestrator: cosine + keyword + recency (decay) + topic-match + highway → `rrf_fuse` → unified top-k. |

This closes task #69 (Gap-analysis SOTA MEDIUM — multi-signal fusion)
at the documentation level. The bench-vs-cycle-161 hybrid (§5.1
falsification) is deferred to a later cycle when a 50-query held-out
set is available.

---

## 6. Caveat A1 onesti

- §1-§4 design preserved from cycle 190 authorship. §5.1 added cycle
  224 once the RRF chain (191/195/196/197) shipped.
- Cycles 191-194 are no longer "PROPOSED" — see §5.1 above.
- "10-100 recall events per session" is anecdotal — needs metrics
  from a real session.
- The "RRF outperforms LTR with no training" claim is from the 2009
  Cormack paper on TREC datasets; HippoAgent corpora may behave
  differently. Real bench needed in cycle 194.
- The signal table §1 reflects the codebase 2026-05-23. New signals
  (e.g. cycle-189 highway-betweenness) MAY be added as additional
  inputs without changing the RRF formula.

---

## 7. References

- `engram/semantic.py:recall_hybrid` — cycle #161 current 2-signal.
- `engram/hippo_pagerank.py` — centrality (cycle <#161).
- `engram/community_detector.py` — Louvain (cycle 186).
- `engram/highway_nodes.py` — betweenness top-K (cycle 189).
- `docs/sota/community-detection-channel-pattern.md` (cycle 185).
- `docs/sota/highway-nodes-pagerank-cache.md` (cycle 188).
- Cormack, Clarke, Buettcher 2009 — RRF foundational paper.
- Burges et al. 2005 — RankNet / LTR foundational.
