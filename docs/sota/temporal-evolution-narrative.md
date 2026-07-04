# SOTA — Temporal evolution + narrative reconstruction (HippoAgent)

**Status**: documentation; closes task #70 (Gap-analysis SOTA MEDIUM — temporal evolution narrative).
**Date**: 2026-05-23 (cycle 192).
**Scope**: gap analysis on representing the **time evolution** of the
fact graph and reconstructing a coherent **narrative** from it.
Companion to cycles 180, 185, 188, 190.

---

## 1. Motivation

HippoAgent stores facts with `created_at` timestamps and `lineage_to`
DAG edges, plus an explicit `superseded_by` chain. But the system does
NOT currently exploit the **temporal dimension** for retrieval or
storytelling:

| Temporal signal | Stored? | Used in retrieval? |
|------|------|------|
| `created_at` (epoch) | ✓ | only tie-break |
| `superseded_by` (replacement chain) | ✓ | excluded from default recall |
| `superseded_at` | ✓ | NOT exposed |
| `superseded_reason` | ✓ | NOT exposed |
| `causal_edges.created_at` | ✓ | NOT exposed |
| Episode chronology | ✓ via `episodes.created_at` | only tie-break |
| Narrative arc reconstruction | ✗ | — |
| Topic decay (recency weight) | ✗ | — |

**Gap**: the agent cannot answer "what was the state of X 3 days ago?"
or "show me the evolution of cycle-175 from design to ship", because
nothing in the recall path is temporally aware.

---

## 2. SOTA temporal primitives

### 2.1 Time-aware retrieval (recency decay)

Add a recency multiplier to the recall score:

```
final_score = base_score × decay(now - created_at)
```

Common decay curves:
- **Exponential**: `exp(-λ · age_days)` — λ ≈ 0.05 (~14-day half-life)
- **Power-law**: `1 / (1 + age_days)^p` — fat-tail, never dies
- **Linear cutoff**: `max(0, 1 - age_days/N)` — hard horizon

**Reference**: Bahmani 2016 "Time-Aware PageRank" applies decay
on the random-walk transition matrix; equivalent effect.

### 2.2 Narrative reconstruction (temporal lineage walk)

Given a seed fact F, walk:
1. **Backward** through `lineage_to` to find the chain that led to F.
2. **Forward** through descendants (facts whose `lineage_to == F.id`).
3. **Sideways** through `superseded_by` to find revisions of F itself.
4. **Topic-co-occurrence** (facts on same topic, close in time, no
   direct edge) to gather "background context".

Output: an ordered narrative `[(timestamp, fact_id, role)]` where role
∈ {root, antecedent, current, descendant, revision, context}.

**Reference**: Carstens & Toulmin "argument-graph" + temporal layering;
analogous to Git's `log --graph --topo-order`.

### 2.3 Snapshot-at-time

Query API: "what does the corpus look like AS OF timestamp T?"
Implementation: filter every recall by `created_at <= T` AND
(`superseded_at IS NULL OR superseded_at > T`).

**Use case**: replaying an agent's reasoning trajectory; debugging
"how did we conclude X on day Y when we now know Y was wrong?".

---

## 3. Existing primitives + gaps

| Primitive | File | What it does | Gap |
|------|------|------|------|
| `engram/fact_chain.py` | DAG walk on `lineage_to` | only backward |
| `engram/recall_chain.py` | episode chain replay | no superseded handling |
| `engram/chain_render.py` | DOT export | no temporal axis |
| `engram/episode_replay.py` | step-by-step replay | no time-cursor |
| `engram/decay_simulate.py` | mock decay function | not wired to retrieval |
| `engram/time_decay.py` | actual decay impl | NOT used by default recall |

So the building blocks exist but are **disjoint** — no single
function returns a temporal narrative or time-aware ranking.

---

## 4. Design — `engram/temporal_narrative.py` (proposed cycle 193)

API sketch:

```python
def reconstruct_narrative(
    semantic_db: Path, *, seed_fact_id: str, window_days: float = 30,
) -> list[dict]:
    """Return an ordered narrative of facts related to ``seed_fact_id``
    within ``window_days`` before and after its creation.

    Each entry: {
      "fact_id": str, "ts": float, "age_days": float,
      "role": Literal["root", "antecedent", "current",
                       "descendant", "revision", "context"],
      "edge_to_seed": Literal["lineage_to", "lineage_from",
                                "supersedes", "superseded_by",
                                "same_topic", None],
    }
    """

def snapshot_at_time(
    semantic_db: Path, *, as_of_ts: float, query: str, k: int = 5,
) -> list[str]:
    """Return top-K facts that were ALIVE at ``as_of_ts``."""

def time_decay_recall(
    semantic_db: Path, *, query: str, k: int = 5,
    decay_fn: Literal["exp", "power", "linear"] = "exp",
    half_life_days: float = 14.0,
) -> list[tuple[str, float]]:
    """Cosine recall multiplied by recency decay."""
```

---

## 5. Gap analysis (follow-up cycles)

| Gap | Severity | Suggested cycle |
|-----|----------|-----------------|
| **`reconstruct_narrative`** | MEDIUM | cycle 193 — DAG walk + role labelling, 80-100 LOC + TDD |
| **`snapshot_at_time`** | MEDIUM | cycle 194 — SQL filter ` AND created_at <= ? AND (superseded_at IS NULL OR superseded_at > ?)` |
| **`time_decay_recall`** | LOW | cycle 195 — multiply cosine by exp-decay, A/B vs flat |
| **Wire decay into `recall_hybrid`** | LOW | cycle 196 — add as RRF signal (composes with cycle 191) |
| **Narrative as MCP tool** | MEDIUM | cycle 197 — `hippo_narrative(seed_id, window)` exposing reconstruct_narrative |

### 5.1 Acceptance criteria — cycle 193 `reconstruct_narrative`

- TDD strict on a synthetic 5-fact chain (root → desc1 → desc2 +
  superseded_by + same-topic-context) → all 5 roles labelled.
- Empirical: a real cycle-175 narrative recovered with ≥ 5 entries
  (the cycle has design → impl → 175.1 → 184 wire fix etc.).
- < 50ms for window_days=30 on 1.7k-fact corpus.

### 5.2 Falsifiable hypothesis H5

`time_decay_recall` with half-life=14 days improves recall@5 on the
recent-events subset of the 50-query held-out (cycle 190 §H4) by
≥ 8% absolute, WITHOUT degrading recall on the older subset by more
than 3%. Falsification: degradation on older > 5% OR recent gain
< 4% → revert.

---

## 5.1 Implementation status — cycle 193/194/195 closure (2026-05-23, cycle 224)

The §4 design has been implemented:

| Cycle | Module | What it ships |
|-------|--------|---------------|
| 193 | `engram/temporal_narrative.py` | `reconstruct_narrative(fact_id, semantic_db)` — 5-role walk: root / antecedent / descendant / revision / context. |
| 194 | `engram/snapshot_at_time.py` | `snapshot_at_time(semantic_db, t_iso)` — corpus view as-of timestamp. |
| 195 | `engram/time_decay_score.py` | `decay_score(t_delta, mode)` — exp / power / linear curves. |

Cycle 195's `decay_score` is also referenced in
`docs/sota/multi-signal-fusion.md` §5.1 as the recency signal of the
cycle-197 fuse_recall orchestrator. This closes task #70
(Gap-analysis SOTA MEDIUM — temporal evolution narrative) at the
documentation level.

---

## 6. Caveat A1 onesti

- §1-§4 design preserved from cycle 192 authorship. §5.1 added cycle
  224 once the chain (193/194/195) shipped.
- Cycles 193-197 are no longer "PROPOSALS" — see §5.1.
- The decay curves (§2.1) are off-the-shelf; HippoAgent's optimal
  half-life is empirical and needs measurement (cycle 195).
- The 6 existing primitives (§3) are documented from the file tree —
  whether they actually work standalone is verified per-file in
  their test files. Some may have rotted.
- "Narrative reconstruction" can produce verbose results — cycle 197
  MCP tool should accept a `max_entries` cap.

---

## 7. References

- `engram/fact_chain.py` — current lineage_to walk.
- `engram/recall_chain.py` — episode-level chain.
- `engram/time_decay.py` — existing decay function, not wired.
- `engram/decay_simulate.py` — mock harness.
- `docs/sota/multi-signal-fusion.md` (cycle 190) — recency is one of
  the 8 signals to fuse via RRF.
- Bahmani 2016 — Time-Aware PageRank.
- Carstens & Toulmin — argument graphs (foundational).
