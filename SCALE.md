# Engram at scale — 20-year / 20-tenant analysis (2026-06-29)

Measured on the real corpus (`~/.engram/semantic/semantic.db`) plus synthetic
scale tests. Every number below is reproducible by the named script under
`arch-lab/sistema/` (in the ProgettiAI workspace, not this repo). Honest scope:
single-machine, the synthetic tests isolate one cost each.

## The walls, measured

| Wall | Finding | Status |
|---|---|---|
| Recall precision vs N | recall@10 flat (65.7%) to 11k real distractors; distractors compete (cos 0.78) but don't displace gold — margin holds; %distractor in top-10 grows ~logarithmically (≈4.7% extrapolated @10M) | **robust** — not the wall |
| Global recall latency | brute-force O(N): 7.68 / 37.42 ms @100k/500k; **ANN (HNSW) WIRED** (`engram/ann_cache.py`, `ENGRAM_ANN_RECALL`): **0.96 / 1.38 ms = 8× / 27×** (gap widens with N — brute is linear, ANN sublinear); build 54s/338s once then incremental add; RAM linear (10M ≈ 30GB) | **wired, behaviour-preserving**; 500k/1M+auto-enable next |
| **Multi-tenant lookup** | `topic LIKE 'prefix%'` → full `superseded_by` scan, **O(N_total)**: 203ms @ 1M rows / 10k tenants | **FIXED** → range + `INDEXED BY`, O(N_tenant) 0.16ms (**1270×**) — `d1ef0c0` |
| **Multi-tenant deserialize** | per-row `np.stack([deserialize])` O(N_tenant): 374ms @ 100k rows/tenant | **FIXED** → batch `frombuffer(join).reshape` (**3.7×**) — `acc5ee7` |
| Tenant isolation | 0 leak / 50 scoped recalls; `scope.py` strict `user:/agent:/run:` | **correct** |
| Model-drift | 0% now (single embedding model); each future model swap orphans ~100% of facts until re-embedded | future |
| DB growth | ~9GB @ 1 tenant / 20y (ok); ~180GB @ 20 tenants → sharding. Ballast: 32% of live rows are quarantined/orphaned | tiering future |

## Quality (LoCoMo, apples-to-apples, same claude judge, 30 QA)
Engram retrieval **0.80** = full-context ceiling **0.80** = mem0-style extract **0.80**
(tie within n=30 noise), at a fraction of the tokens. Engram leads on adversarial
(abstention) 100%. External numbers (Mem0 66.9, Zep 66.0) use a different judge and
are not directly comparable (Zep 84→58 shows ±25pp of pure methodology).

## Shipped on main
- `d1ef0c0` perf(scope): index-driven O(N_tenant) lookup (range-query + `INDEXED BY idx_facts_topic`). +264 tests.
- `acc5ee7` perf(scope): batch-deserialize on the scoped per-query path. +421 tests green, result byte-identical.

> NB: CI is red on these commits because GitHub Actions **billing** is blocked
> (jobs don't start: *"recent account payments have failed"*), not because of the
> code. Same red on every prior commit. Tests pass locally.

## Roadmap (not started — projects, not one-line fixes)
1. **ANN for global recall** — **module SHIPPED** `engram/ann_index.py`
   (2026-07-04): faiss HNSW, oversampled candidate pool (recall-in-pool ≈ 1.0,
   5 tests), gated `>_ANN_MIN_N=100k`, and the hard part solved — **incremental
   `add`** (faiss appends, no 348s rebuild-per-store). **WIRED into recall**
   (2026-07-04, `ENGRAM_ANN_RECALL=1`, default OFF): `ANNCache` (build-once,
   version-keyed, incremental grow) pre-narrows the corpus to the ANN pool
   BEFORE the filters/cosine/rerank — so they run on O(pool) not O(N). Proven
   behaviour-preserving: ANN-on recall returns identical top-k SCORES to the
   exact brute-force path (`tests/test_ann_recall_equivalence.py`); the whole
   5941-test suite is byte-identical with the gate off. **Remaining**: a
   500k/1M in-engine bench + auto-enable heuristic.
2. **Very-large-tenant recall** (> ~10k facts/tenant): the scoped path still
   re-stacks per query. A cache-matrix scope-mask would be ~35× but touches the
   hot-path (deferred — risk/benefit).
3. **Cold-tiering** the 32% quarantined/superseded ballast off the live DB.

## Reproduce
`arch-lab/sistema/`: `multitenant_scan_v2.py` (lookup O(N_total)→O(N_tenant)),
`deser_bench.py` (batch deserialize), `latency_scale.py` (brute vs ANN),
`scale_degradation.py` (precision vs N), `isolation_test.py` (leak test),
`multitenant_e2e.py` (per-query deserialize cost), `cmp_synthesis.py` (LoCoMo quality).
