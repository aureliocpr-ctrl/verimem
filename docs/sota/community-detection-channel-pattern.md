# SOTA — Community detection for channel/pattern discovery (HippoAgent)

**Status**: documentation; closes task #67 (Gap-analysis SOTA MAJOR — community detection canali pattern).
**Date**: 2026-05-23 (cycle 185).
**Scope**: gap analysis between HippoAgent's current clustering primitives
(consolidation, facts_cluster_by_topic, hippo_pagerank) and SOTA
community-detection algorithms used in graph-based memory systems.
This is a **descriptive + design** doc, not implementation.

---

## 1. Motivation

HippoAgent persists episodes ⇒ facts ⇒ skills as a directed graph
(lineage chain, source_episodes, causal_edges via skill ids). After
1675+ facts the graph naturally develops dense subgraphs ("channels")
that the current primitives can only approximate via:

- `engram.consolidation` — pairwise cosine clustering (cycle #144).
- `engram.facts_cluster_by_topic` — string-equality on `topic` field.
- `engram.hippo_pagerank` — global centrality only.

None of these explicitly recover **communities** (densely-connected
clusters with sparser inter-cluster edges) which would let the agent:

1. Detect **emerging channels** (e.g. all "ghost-typing" facts cluster
   under one synthetic topic node).
2. Compress whole communities into a single "summary skill" during
   Auto-Dream (cycle #69).
3. Visualise the corpus topology (lineage DAG + community overlay) for
   the operator.

---

## 2. Existing primitives in HippoAgent

| Primitive | File | Algorithm | Output |
|-----------|------|-----------|--------|
| `consolidate` | `engram/consolidation.py` | Greedy pairwise cosine ≥ threshold, single-pass | Flat clusters of episodes/facts |
| `facts_cluster_by_topic` | `engram/facts_cluster_by_topic.py` | String equality on `topic` field | Topic → list[fact_id] |
| `hippo_pagerank` | `engram/hippo_pagerank.py` | NetworkX PageRank over causal_edges | Global centrality score per node |
| `chain_graph` (clp-bridge) | external | DOT/Mermaid export of `lineage_to` DAG | Visual, no clustering |

**Gap**: no algorithm groups facts by **graph topology** (edge density)
— only by `topic` string OR by pairwise cosine. A fact with the right
`topic` but no causal_edges to its siblings is still grouped, and vice
versa. This misses the real **community** structure.

---

## 3. SOTA candidates (community detection on memory graphs)

Three families are mature open-source today and runnable on the
~1.7k-node graphs HippoAgent has:

### 3.1 Louvain modularity maximisation (Blondel et al. 2008)

- `pip install python-louvain` or `networkx.algorithms.community.louvain_communities`.
- Greedy modularity Q-maximisation: ~O(N log N).
- **Pros**: very fast, no `k` to tune, weights from `causal_edges.weight`.
- **Cons**: resolution-limit problem (small communities merged at scale).
- **Fit for HippoAgent**: ✓ good first-cut, ~1ms on 1.7k nodes.

### 3.2 Leiden refinement (Traag et al. 2019)

- `pip install leidenalg igraph` (heavier deps).
- Fixes Louvain's resolution + connectivity guarantees.
- **Pros**: provably-better than Louvain on standard benchmarks.
- **Cons**: extra dependency (igraph C library), ~3× slower than Louvain.
- **Fit**: ✓ but only as cycle-185.3 follow-up if Louvain proves insufficient.

### 3.3 HDBSCAN over embedding space (McInnes et al. 2017)

- `pip install hdbscan`.
- Density-based clustering on the 384-dim sentence-transformers vectors.
- **Pros**: NO graph required — operates on the embedding cloud directly.
- **Cons**: ignores edge information (loses lineage/causal signal).
- **Fit**: ✓ complementary, NOT replacement. Use as a sanity-check
  baseline.

---

## 4. Design — `engram/community_detector.py` (proposed cycle 186)

API contract (sketch):

```python
def detect_communities(
    *,
    semantic_db: Path,
    edges_source: Literal["lineage", "causal", "both"] = "both",
    algorithm: Literal["louvain", "leiden", "hdbscan"] = "louvain",
    min_community_size: int = 3,
    seed: int = 42,
) -> dict[str, Any]:
    """Run community detection over the HippoAgent fact graph.

    Returns:
        {
            "algorithm": ...,
            "n_communities": ...,
            "modularity": ...,        # only for Louvain/Leiden
            "communities": [
                {"id": "c-001", "size": int, "fact_ids": [...],
                 "centroid_topic": str | None, "centrality_top": [...]},
                ...
            ],
            "noise_fact_ids": [...],  # HDBSCAN-only
        }
    """
```

Build the edges once via:

- `lineage`: `SELECT id, lineage_to FROM facts WHERE lineage_to IS NOT NULL`.
- `causal`: `SELECT src, dst, weight FROM causal_edges`.
- `both`: union, dedupe.

Run the chosen algorithm. Return JSON ready for either:

1. `hippo_briefing_by_project` consumption (group facts into virtual
   sub-projects).
2. `engram.consolidation` seed (replace greedy pairwise with
   community-aware grouping).
3. CLI `engram corpus-topology` for operator inspection.

---

## 5. Gap analysis (TDD-ready next cycles)

| Gap | Severity | Suggested cycle |
|-----|----------|-----------------|
| **No community primitive at all** | MAJOR | cycle 186 — Louvain wrapper over networkx, no new dep (already in requirements). 50-80 LOC + TDD strict |
| **Auto-Dream cluster step ignores graph** | MAJOR | cycle 187 — pass community labels into `propose_dream_tasks(cluster_assignments=...)` |
| **Operator visibility** | MEDIUM | cycle 188 — `engram corpus-topology` CLI dumps DOT with community color per node |
| **Comparative bench** (Louvain vs HDBSCAN on real corpus) | MEDIUM | cycle 189 — `engram/bench_community_methods.py` reuses cycle-179 harness pattern |
| **Leiden upgrade path** | MINOR | cycle 190 — only if Louvain modularity Q < 0.4 on real corpus |

### 5.1 Acceptance criteria for cycle 186 (Louvain wrapper)

- Pure function `detect_communities` over real `~/.engram/semantic.db`
  returns at least 3 communities with size ≥ 3 each.
- Empirical Q-modularity ≥ 0.3 (lower bound for "non-trivial" community
  structure per Newman 2004).
- < 100ms on the current 1.7k-fact corpus (single-threaded).
- TDD strict: synthetic 3-clique-bridge fixture → exactly 3 communities.

### 5.2 Falsifiable hypothesis H2

The cycle-186 community detector, when fed to a future
`compress_communities_to_skills` worker, will produce skills with
**higher** `fitness_mean` (Bayesian smoothed) than the current
`engram.consolidation` greedy-pairwise output after 20 Auto-Dream
cycles. Falsification: if mean fitness delta ≤ 0 (or ≤ noise band of
±0.05) the community-detection hypothesis is rejected and we revert
to consolidate-only.

---

## 5.1 Implementation status — cycle 213→221 closure (2026-05-23)

The hypothesis in §5 has been **partially implemented and validated
empirically** through the following chain of cycles. This section
documents the closure pattern; the §5 falsification design (20-cycle
fitness-delta measurement) remains future work.

### Closure chain

| Cycle | Module | What it ships |
|-------|--------|---------------|
| 186 | `engram/community_detector.py` | Louvain (networkx) + min_size filter, `detect_communities()` returns `[{id, size, fact_ids}, ...]` |
| 213 | `engram/skill_emergence_detector.py` | Composes community + topic purity + embedding cohesion into `detect_emerging_skills()` — communities ready to crystallise into skills |
| 214/215 | `engram/topic_normalization.py` | `normalize_topic()` collapses corpus topic variants (`project/X/cycle175` vs `cycle/175.1`) to a single family key, then truncates noise via first-2-tokens / first-2-segments |
| 217 | `engram/skill_drafter.py` | Deterministic LLM-free DRAFT generator: title + evidence + keywords (stopword-filtered EN+IT) + member facts |
| 218 | `engram/mcp_server.py` | `hippo_emerging_skills_draft` MCP tool — one-call pipeline (detect → draft) |
| 219 | `engram/dream_emergence_hook.py` | 4th Auto-Dream seed; wires drafts as soft instructions hint alongside cycle 175.1/187/211 hooks |
| 220 | `engram/skill_drafter.py` | Italian + extended English stopwords for keyword extractor |

### Empirical evidence (live ~/.engram, 1708 facts, 2026-05-23)

- `detect_emerging_skills(min_size=4, purity≥0.4, cohesion≥0.1)` →
  **2 candidates** on real corpus.
- Top candidate: `emerging_skill_master-fact` (community `c-010`,
  size=15, purity=0.53, cohesion=0.72).
- Trigger keywords after IT/EN stopword filter:
  `clp, loop, commands, master, commit, test, config, recovery, wci,
  explain, switch, tip` — all domain signal, zero function words.
- Forced Auto-Dream firing (state reset → fresh worker) produced
  `dream_tasks.json` with a 1446-character `instructions` field
  containing all 4 seed suffixes (stuck + community + thompson +
  emergence). Confirms the 4-hook composition fires end-to-end.

### Reverse-falsification finding (cycle 216)

While probing the emergence pipeline I discovered that
`auto_dream_worker._live_dirs_from` had been silently routing
Auto-Dream to the **empty** legacy `~/.engram/semantic.db` (36 KB, 0
facts) instead of the canonical `~/.engram/semantic/semantic.db`
(7.4 MB, 1708 facts). Every Auto-Dream firing since the package
restructure had operated on an empty DB — every "triggered=true"
status was vacuous. Cycle 216 fixes the path resolution; cycle 219
validation shows `new_items=2163` (vs `14` previously) confirming the
worker now sees the real corpus.

### Remaining work (deferred)

- **§5 falsification**: 20-cycle Auto-Dream pilot, measure
  `fitness_mean` of skills derived from emergence-seeded vs
  consolidate-only dreams. Threshold: ≥+0.05 absolute delta.
- **Cycle 222+** (proposed): disk persistence of drafts (audit trail
  in `~/.engram/skill_drafts/<date>/<name>.md`).
- **Cycle 223+** (proposed): `hippo_emerging_skills_promote` MCP tool
  to convert a DRAFT into a candidate skill in the SkillIndex without
  any LLM call (the agent picks one, accepts, ship).

---

## 6. Caveat A1 onesti

- The §1-§5 design is preserved verbatim from cycle 185. The §5.1
  closure section was added in cycle 221 after the implementation
  was empirically validated.
- The `1675+ facts` count from §1 is from cycle 185 snapshot; cycle
  221 corpus has 1708 facts.
- Cycle 186-190 are no longer "PROPOSALS" — see §5.1 for the actual
  cycle-by-cycle implementation chain (186/213/214-215/217/218/219/220).
- Performance estimates ("< 100ms on 1.7k nodes" for Louvain) come
  from the cycle-179 BLAS-only bench (0.14ms cosine top-k); graph
  algorithms have **different** asymptotic profile. Real bench
  required before claiming numbers.
- HDBSCAN (§3.3) requires `pip install hdbscan` which is a NON-trivial
  binary dep — defer to cycle 190+ only if Louvain insufficient.
- Leiden requires `igraph` C library — STRONGLY defer.

---

## 7. References

- `engram/consolidation.py` — current pairwise greedy clustering.
- `engram/hippo_pagerank.py` — global centrality, no community split.
- `engram/facts_cluster_by_topic.py` — string-equality grouping.
- `docs/sota/L0-L3-anti-confab-layers.md` (cycle 180) — sister SOTA doc
  that established the doc pattern.
- Blondel et al. 2008 — Louvain original paper.
- Traag et al. 2019 — Leiden paper (arxiv 1810.08473).
- McInnes et al. 2017 — HDBSCAN paper.
- Newman 2004 — modularity Q threshold for non-trivial communities.
- `engram/skill_emergence_detector.py` (cycle 213) — community + topic + cohesion fusion.
- `engram/topic_normalization.py` (cycle 214/215) — family-key collapse.
- `engram/skill_drafter.py` (cycle 217/220) — LLM-free DRAFT generator.
- `engram/dream_emergence_hook.py` (cycle 219) — 4th Auto-Dream seed.
- `engram/mcp_server.py::hippo_emerging_skills_draft` (cycle 218) — exposed MCP tool.
- `engram/auto_dream_worker.py` (cycle 216) — semantic_db path fix (canonical nested).
