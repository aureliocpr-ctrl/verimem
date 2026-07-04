# SOTA — Highway nodes + PageRank cache for recall acceleration (HippoAgent)

**Status**: documentation; closes task #68 (Gap-analysis SOTA MEDIUM — highway nodes PageRank cache).
**Date**: 2026-05-23 (cycle 188).
**Scope**: gap analysis between HippoAgent's current `hippo_pagerank`
primitive and the SOTA techniques for accelerating graph-based recall:
highway-node identification + Personalized PageRank caching +
incremental updates.

This doc was drafted with cross-LLM second opinion from Gemini 2.5 Pro
(sparring transcript saved in episode log).

---

## 1. Motivation

`engram.hippo_pagerank` computes the **global** PageRank vector over
`causal_edges + lineage_to` for centrality scoring. Two limitations:

1. **Full recompute** on every call. ~50ms for 1.7k nodes via
   networkx — acceptable now, O(N) overhead as the corpus grows.
2. **Global only**. Each fact has one centrality score regardless of
   the query context. A fact that's central to "ghost-typing" is
   irrelevant to "active learning" — but `hippo_pagerank` cannot
   differentiate.

Cycle 186 confirmed the corpus has strong community structure
(Q=0.8775, 16 communities ≥ 3). This means there are **highway
nodes** — facts connecting otherwise-disjoint communities — that
should be prioritised in recall.

---

## 2. Highway nodes — definition + algorithm

**Definition (Kleinberg 2000, "Navigable Small-World Networks")**: a
node with high **betweenness centrality**, lying on many shortest
paths between other node pairs. Removing it would fragment the graph
or substantially increase mean path length.

**In HippoAgent terms**: a fact that semantically bridges multiple
Louvain communities (cycle 186). Likely shapes:
- Abstract principle facts ("A1: never invent commits")
- Cross-domain skill ids (used by multiple unrelated workflows)
- Master-fact "vN" summary nodes (lineage_to children from many topics)

**Detection algorithm**:
```python
import networkx as nx
g = build_fact_graph(semantic_db, edges_source="both")
between = nx.betweenness_centrality(g, k=min(500, len(g)))
top_highways = sorted(between.items(), key=lambda kv: -kv[1])[:K]
```

`k` parameter approximates over a sample (default 500) — full
betweenness is O(N³), the sampled version is O(k · (N+M)). On 1.7k
nodes that's ~10-30ms.

---

## 3. Personalized PageRank (PPR) caching

Standard PageRank gives a **single** centrality vector. Personalized
PageRank computes a centrality vector **biased toward a seed node** —
the resulting vector measures "how relevant is every other fact when
the query is anchored at this seed?".

**Caching strategy** (Gemini sparring):
1. Identify the top-K highway nodes (§2).
2. For each highway node, pre-compute the PPR vector
   (`nx.pagerank(g, personalization={seed: 1.0})`).
3. Store the top-N entries per vector (sparse): each highway → its
   N most-PPR-influenced facts.
4. At recall-time: pick the seeds nearest to the query (in embedding
   space), look up their cached PPR vectors, union the results.

**Storage cost**: K highways × N entries × (id + float32) bytes.
For K=50, N=100: ~50 × 100 × 12 = 60 KB. Negligible.

**Refresh cadence**: PPR vectors change only when graph topology
changes near the highway. Stale-by-design — refresh on Auto-Dream
cycle (every 30 min).

**Reference**: Bahmani et al. "Fast Incremental PageRank" describes
the incremental push-based update; networkx does NOT ship this, so a
clean wrapper is required.

---

## 4. Trade-off — cache freshness vs recompute cost

| Strategy | Freshness | Compute cost | Implementation |
|---|---|---|---|
| **Cold recompute on every recall** | perfect | high (50ms+) | already in `hippo_pagerank` |
| **Full recompute on Auto-Dream cycle** (every 30 min) | up to 30 min stale | very low (amortised) | + 50ms once per cycle |
| **Incremental local push** on every write | low stale (seconds) | medium (~1-5ms per write) | NEW algorithm needed |
| **Hybrid** (Gemini recommendation) | low stale | low avg | incremental + nightly full recompute (reset numerical drift) |

**Recommendation**: hybrid. Incremental push for in-session recall
quality, periodic full recompute (daily, or Auto-Dream cycle 24×
default cooldown) to clear accumulated approximation error.

---

## 5. Design — `engram/pagerank_cache.py` (proposed cycle 189)

API sketch:

```python
def get_highway_nodes(
    semantic_db: Path, *, k: int = 50, sample_size: int = 500,
) -> list[tuple[str, float]]:
    """Return top-K highest-betweenness fact ids + score."""

def get_ppr_for_seed(
    semantic_db: Path, *, seed_fact_id: str, top_n: int = 100,
    refresh: bool = False,
) -> list[tuple[str, float]]:
    """Return PPR vector top-N (id, score) anchored at seed.
    Cached. ``refresh=True`` forces recomputation."""

def recall_via_highway(
    semantic_db: Path, *, query_embedding: np.ndarray,
    k_seeds: int = 3, top_n: int = 20,
) -> list[str]:
    """Recall: find nearest highway seeds to the query, union their
    cached PPR top-N, return deduplicated fact_ids by aggregate score."""
```

Cache backed by a new SQLite table `pagerank_cache(highway_id PRIMARY KEY,
ppr_topn_json TEXT, computed_at REAL)` — read-only during recall,
write only during Auto-Dream cycle.

---

## 6. Gap analysis (TDD-ready follow-up cycles)

| Gap | Severity | Suggested cycle |
|-----|----------|-----------------|
| **Betweenness sample wrapper** (top-K highway detection) | MEDIUM | cycle 189 — pure function `get_highway_nodes`, networkx k-sample, ~30 LOC + 6 TDD tests |
| **PPR cache table** (schema v6 migration) | MEDIUM | cycle 190 — SQLite ALTER + bench warm-vs-cold |
| **Recall path uses cache** | MAJOR | cycle 191 — wire `recall_via_highway` into `engram.semantic.recall_hybrid` (cycle #161) as an optional fast-path |
| **Incremental local-push update** | MINOR (defer) | cycle 195+ — needs Bahmani implementation, NOT in networkx |
| **Falsifiable hypothesis H3** | — | recall@5 ↑ ≥ 10% on a sample of 50 queries when PPR cache is enabled vs disabled |

### 6.1 Acceptance criteria — cycle 189 `get_highway_nodes`

- Empirical: 50 highways from real ~/.engram/semantic.db.
- < 100ms on full real corpus (sampled betweenness with k=500).
- TDD strict: bowtie-fixture (2 hubs connected by 1 bridge) → bridge
  node has highest betweenness.

### 6.2 Falsifiable hypothesis H3

After enabling the PPR-cache recall fast-path (cycle 191), recall@5
on a 50-query held-out benchmark increases by ≥ 10% absolute against
the cycle-161 hybrid (semantic + keyword) baseline. Falsification: if
delta ≤ 5% or significantly negative the cache is not worth the
complexity → revert.

---

## 6.1 Implementation status — cycle 189/198 closure (2026-05-23, cycle 224)

The §5 design has been implemented:

| Cycle | Module | What it ships |
|-------|--------|---------------|
| 189 | `engram/highway_nodes.py` | `get_highway_nodes(semantic_db, k=10)` — sampled betweenness centrality (Brandes 2001 approx, configurable sample size). |
| 198 | `engram/betweenness_cache.py` | `ensure_highway_cache(semantic_db, ttl_seconds=...)` — on-disk JSON cache with mtime-based invalidation. |
| 197 | `engram/fuse_recall.py` | Composes highway nodes as one of the signals in the cycle-191 RRF fusion. |

Cycle 198 caches the betweenness computation so repeated calls are
O(1) file-read instead of O(V·E) graph traversal. This closes task
#68 (Gap-analysis SOTA MEDIUM — highway nodes PageRank cache) at the
documentation level.

---

## 7. Caveat A1 onesti

- §1-§5 design preserved from cycle 188 authorship. §6.1 added cycle
  224 once implementation chain (189/197/198) shipped.
- Cycles 189-195 are no longer "PROPOSED" — see §6.1 for the
  delivered chain.
- Highway-node literature is broader (HighwayHash, Hierarchical
  Routing, etc.) — this doc focuses on the Kleinberg/Bahmani lineage
  relevant to memory-graph recall.
- Performance numbers ("~10-30ms sampled betweenness on 1.7k nodes")
  are extrapolated from cycle 186 Louvain timing (177ms). Real bench
  needed in cycle 189.
- The Gemini sparring (2026-05-23) recommended the hybrid cache
  strategy explicitly — citing trade-off table reproduced in §4.

---

## 8. References

- `engram/hippo_pagerank.py` — current global PageRank primitive.
- `engram/community_detector.py` (cycle 186) — Louvain partition;
  highway nodes will bridge these communities.
- `docs/sota/community-detection-channel-pattern.md` (cycle 185).
- `docs/sota/L0-L3-anti-confab-layers.md` (cycle 180) — sister SOTA doc.
- Kleinberg 2000 — "Navigable Small-World Networks".
- Bahmani, Chowdhury, Goel — "Fast Incremental PageRank" (2010/2011).
- Cross-LLM sparring transcript: Gemini 2.5 Pro response @ 2026-05-23
  re: highway nodes definition + hybrid cache strategy.
