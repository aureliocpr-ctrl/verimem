# Cycle 159.8 — Scaling Experiment 2 (2026-05-19)

Second test of the cycle-159 scaling hypothesis. Cycle 159.7 (Arm A
vs Arm B on `engram/llm.py`) confirmed for N=1 that 2 sonnet team
beats 1 sonnet on bug-hunt recall + precision. Aurelio then asked:

> ma tu devi provare anche su intelligenza totale e altro, problema
> che opus non risolverebbe, fallo fare a 2 sonnet

i.e. test whether 2 sonnet can match or beat **1 opus** on a problem
where opus would struggle.

## Setup (N=1)

- **Target**: `engram/consolidation.py` (302 LoC, cycle 144 base —
  branch `cycle159-team-real-collab` does not yet carry the
  cycle-151/154/155 fixes that live on other PRs).
- **Arm C**: 1 OPUS single instance, 7 min, 1 call. Anti-confab
  contract requires file:line + verbatim snippet + **triggering
  input**.
- **Arm D**: 2 SONNET team (heidi = primary + ivan = critic) via the
  Real-Collaboration Charter, ~5 min wall clock. Same contract;
  strict-majority `[VOTE-CONVERGED]` required.

## Hypothesis (falsifiable)

> The 2-sonnet team finds at least one real bug that opus-single
> misses, **without** an inflated false-positive rate.

## Result — falsified for THIS task (the picture is mixed)

| Bug                                                            | Arm C (opus) | Arm D (team) | Verified by lead |
|----------------------------------------------------------------|--------------|--------------|------------------|
| **`_source_episodes_for_facts` json.loads on comma-sep column** | ✅ **FOUND HIGH** | ❌ **MISSED** | **REAL HIGH — breaks core feature** |
| LIKE wildcard injection on `prefix`                            | ✅ found LOW  | ✅ found MEDIUM | REAL (severity LOW–MEDIUM) |
| `fact_ids=[]` → SQL `IN ()` crash                              | flagged as defensive smell | ✅ claimed HIGH | **REPRO FAILED** — SQLite 3.51.1 accepts `IN ()` |
| Self-loop `(ep.id, ep.id)` in `causal_edges`                   | not raised   | ✅ found MEDIUM | REAL (latent CTE loop) |
| Idempotency probe checks `proposition` only, not `topic`        | not raised   | ✅ found MEDIUM | REAL (silent bloc) |
| `edges_created` overcount with `INSERT OR IGNORE`               | flagged as smell | not raised | latent smell, not bug today |

**Net score (real bugs with reproducible trigger)**:

- Arm C opus: **1 HIGH** + 1 LOW (LIKE wildcard) + 1 smell.
- Arm D team: **3 REAL bugs** of MEDIUM severity + 1 confabulated
  trigger (their HIGH claim collapses on empirical re-check: SQLite
  doesn't crash on `IN ()`).

The **HIGH** bug (`json.loads` on a comma-separated column —
`consolidation.py:204` vs `semantic.py:466,1345`) silently breaks
the orchestrator's documented core feature (one `narrative_link`
edge per source episode of the cluster's sub-facts). Production runs
were always falling back to a single self-edge. Opus caught it
because the bug requires **cross-file evidence** between
`consolidation.py:204` and `semantic.py:466` — it sits inside a single
opus context window comfortably, while neither sonnet in the team
walked the storage layer to verify the column format.

The team found three real bugs opus missed (self-loop, idempotency-
on-proposition-only, LIKE wildcard injection). It also rejected two
self-confabulations from heidi (TOCTOU on a `_CONSOLIDATE_LOCK` that
doesn't exist on this branch, and a `consolidated_prefixes` cache
that doesn't exist either — both inherited from team-lead's wrong
prompt about cycle-154/155 already being merged).

## Honest synthesis (N=2 across cycles 159.7 + 159.8)

- "2 sonnet team always scale beyond 1 opus" — **REJECTED**.
- "2 sonnet team always scale beyond 1 sonnet" — supported by 159.7,
  not contradicted by 159.8 (we didn't run sonnet-single here).
- Real picture: **task-type matters**.
  - When the bug requires *cross-file* / cross-module reasoning, opus
    single wins on the critical-severity bug; the team disperses.
  - When the bug is *single-file* and falls into many independent
    failure modes, the team's recall + peer-verify wins.

## What got committed

The opus HIGH bug is fixed in this commit:

- `engram/consolidation.py:185-217` — `_source_episodes_for_facts`
  now parses the comma-separated column directly (drops the unused
  `json` import) and short-circuits on empty `fact_ids` so direct
  callers don't trip the `IN ()` shape question.

Tests in `tests/test_consolidation_cycle159_8_bugs.py`:
- `test_source_episodes_for_facts_reads_comma_separated_column`
  (RED pre-fix: returns `[]`; GREEN post-fix: returns all three
  episode ids).
- `test_source_episodes_for_facts_handles_single_episode` (a single
  bare token also fails `json.loads` pre-fix; passes post-fix).
- `test_source_episodes_for_facts_empty_fact_ids_returns_empty`
  (post-fix defensive short-circuit verified).
- `test_propose_master_node_empty_fact_ids_does_not_crash` —
  **falsifies** the team's "HIGH" claim that `IN ()` crashes SQLite.

The other team-found bugs (self-loop, idempotency-proposition-only,
LIKE wildcard injection) are real and queued for follow-up — but
applying them to *this branch* risks colliding with the
cycle-151/154/155 fixes that already address some of these on
sibling branches. Aurelio should decide whether to apply them here
or close this PR after merging the cycle-151+ chain first.

## Caveats

- N=1 per arm, N=2 across the two scaling experiments. Evidence,
  not proof.
- Wall-clock parity is approximate — opus actually used ~7 min, team
  ~5 min. Token cost is roughly comparable (1 opus call ≈ 2 short
  sonnet conversations).
- Heidi confabulated two bugs (TOCTOU lock, cache invalidation)
  because the team-lead's prompt cited cycle-154/155 features that
  don't exist on this branch. Ivan caught both with `grep` —
  Charter v1 self-corrected. But the team-lead's prompt confabulation
  is a real failure mode: same lesson as cycle 159.4.

Fact memoria: `591a8ea5f8ce` (159.7) + follow-up 159.8 fact.
