# SOTA — Anti-confabulation gate layers L0 → L3 (HippoAgent)

**Status**: documentation; closes task #66 (Gap-analysis SOTA MAJOR — layer L0-L3 espliciti).
**Date**: 2026-05-22 (cycle 180).
**Scope**: explicit architectural reference for the write-time
confabulation gate that wraps every `hippo_remember` /
`hippo_record_episode` call in the codebase.

This document collects what is already implemented in the source tree
(`engram/anti_confab_gate.py`, `engram/anti_confabulation.py`,
`engram/validate_claim.py`) into one place, so future cycles can
reason about gaps without re-reading 4 modules.

---

## 1. Why the gate exists

Empirical motivation (sessione 2026-05-17 + cycle #128 docstring):

- 7 confabulations admitted honestly, 2/7 of the shape
  `"X SHIPPED PR #N commit_hash"` where the commit hash was invented.
- The pre-#128 path saved such facts as `status='model_claim'` because
  `verified_by` had generic tool refs (no `commit:` / `pr:` /
  `file:` / `git:` markers).
- Cycle #109 hard-gate covers only `status='verified'` writes — leaving
  the `model_claim` path (the **default**) unguarded.
- Cycle #138 closed that gap by wrapping the L1 keyword family + the
  L3 semantic-contradiction probe into `run_validation_gate(...)`,
  called by `hippo_remember` **before** persisting the fact.

The gate's purpose is **not** to refuse writes (the model-claim path
must stay open for "store a guess and revise later" workflows). It is
to **downgrade** suspect claims to `status='provisional'` so they are
hidden from default recall but preserved for audit + later
reconciliation.

---

## 2. Layer taxonomy (canonical)

The codebase uses three tiers — `"off" | "fast" | "full"` — plus two
modes — `"downgrade" | "reject"`. Layers map to tiers as follows:

| Layer   | Tier(s) it runs in | Mean cost | What it detects |
|---------|--------------------|-----------|-----------------|
| **L0**  | every tier         | trivial   | Schema validation (pydantic on the call payload). Pre-gate. |
| **L1**  | `fast`, `full`     | < 1 ms    | "SHIPPED / MERGED / WIRED / DEPLOYED" keyword + no commit-tracking ref in `verified_by` |
| **L1.5**| `fast`, `full`     | < 1 ms    | "diagnosis" verb-form (e.g. `"root cause is X"`) + no `bash:` / `pytest:` / `file:` evidence ref |
| **L1.7**| `fast`, `full`     | < 1 ms    | "task X is in state Y" + no canonical task-tracker ref |
| **L3**  | `full` only        | ~13 ms, p95 40 ms | `validate_claim` semantic-memory contradiction probe (cycle #70) over the agent's fact corpus |

`L2` is **reserved but not implemented** — see §5 "Gap analysis".

### 2.1 L1 — `SHIPPED` keyword family (cycle #128)

Defined in `engram/anti_confabulation.py:detect_unsupported_shipped_claim`.

```python
SHIPPED_KEYWORDS = frozenset({
    "SHIPPED", "MERGED", "WIRED", "DEPLOYED",
})
```

Match condition (all conjunctive):

- `proposition.upper()` contains any keyword (substring match).
- `verified_by` does **not** contain any entry starting with
  `commit:`, `pr:`, `file:`, `git:`.

If both hold, the detector returns a `Warning` value that the gate
escalates depending on the mode (default `downgrade`).

**Why these keywords**: empirical analysis of 7 self-confabulations
(2026-05-17) showed 2/7 were of this shape with invented git refs.

**Why warning, not reject**: keyword heuristics are too coarse to
hard-block writes. A real "SHIPPED" claim from a verified deployment
hook would still hit. The gate downgrades and lets a future L2
reconciler scan the audit log.

### 2.2 L1.5 — diagnosis claim (cycle #130)

Defined in `engram/anti_confabulation.py:detect_unsupported_diagnosis_claim`.

Detects propositions of the shape `"root cause is X"` or
`"the bug was Y"` without a `bash:` / `pytest:` / `file:` line ref in
`verified_by`. Same downgrade semantics as L1.

### 2.3 L1.7 — task-state claim (cycle #131)

Defined in `engram/anti_confabulation.py:detect_unsupported_task_state_claim`.

Detects propositions of the shape `"task #N is COMPLETED / PENDING /
IN_PROGRESS"` without a canonical task-tracker ref in `verified_by`
(e.g. `task:#42` or `linear:ENG-123`). Same downgrade semantics.

### 2.4 L3 — `validate_claim` semantic probe (cycle #70)

Defined in `engram/validate_claim.py:validate_claim`. Runs only in
`tier="full"`.

Algorithm (high level):

1. Embed the candidate proposition.
2. Recall top-k semantically nearest facts from the agent's
   semantic store.
3. Run lexical contradiction probe (year disjunction, negation,
   superseded-by chain).
4. Return one of: `consistent` / `unverified` / `contradicted`.

If the verdict is `contradicted`, mode `"reject"` refuses to persist
(error `action="reject"` with advice + the contradicting fact ids);
mode `"downgrade"` (default) persists with `status='provisional'`.

**Cost**: FASE-1 benchmark 2026-05-18 on 1183-fact live corpus —
mean ~13 ms, p95 ~40 ms. Currently dominated by SQLite blob read
and cosine top-k argpartition (cycle 179 bench confirms BLAS
sub-millisecond once embeddings are in RAM).

**Empirical justification**: caught year-disjoint contradictions
that L1 keyword heuristics missed (Tonegawa 1987 vs 2014, Anthropic
Skills 2025 vs 2026 — the historical 2026-05-14 confabulations).

---

## 3. Orchestration — `run_validation_gate`

Single entry point in `engram/anti_confab_gate.py`. Signature:

```python
def run_validation_gate(
    proposition: str,
    *,
    verified_by: Iterable[str],
    agent: Any,  # Has .semantic for L3
    tier: Literal["off", "fast", "full"] = "fast",
    mode: Literal["downgrade", "reject"] = "downgrade",
    force_persist: bool = False,
) -> GateVerdict:
    ...
```

`GateVerdict` carries:

- `action`: `"allow"` / `"downgrade"` / `"reject"`
- `warnings`: list of layer-specific warning structs (L1, L1.5,
  L1.7, L3)
- `status_override`: `"provisional"` when downgraded, else `None`
- `contradicting_fact_ids`: only set when L3 verdict is
  `contradicted`

### 3.1 Tier semantics

| Tier  | L1 | L1.5 | L1.7 | L3 | Use case |
|-------|----|----|----|----|----------|
| `off`   | – | – | – | – | Migrations, replays, deliberate admin writes (`force_persist=True` equivalent) |
| `fast` (default) | ✓ | ✓ | ✓ | – | Per-call default — sub-millisecond, catches the empirically frequent keyword shapes |
| `full`  | ✓ | ✓ | ✓ | ✓ | High-stakes claims, end-of-session consolidation, pre-publish audit |

Override per-call via the `validate` kwarg in `hippo_remember`.
Global default via `ENGRAM_VALIDATE_DEFAULT` env var
(`"off"|"fast"|"full"`).

### 3.2 Mode semantics

- `downgrade` (default): any positive triggers persist with
  `status='provisional'`. The fact is preserved for audit but
  excluded from default recall (cycle #109 S4-A).
- `reject`: only L3 `contradicted` causes a hard refuse; L1
  family still merely downgrades because keyword heuristics
  are too coarse for a hard block.

### 3.3 `force_persist=True` escape hatch

Gate still runs and emits warnings to the observability bus +
audit log, but the caller's wish to persist wins. Reserved for
operator-initiated writes (CLI, replays, migrations).

---

## 4. Cross-references

- **Anti-confab on read**: `engram/semantic.py` default recall path
  drops `legacy_unverified` + `orphaned` + `quarantined` rows. Cycle
  #109 S4-A.
- **L2 (placeholder)**: future reconciler that scans audit log for L1
  warnings and flips stale claims to `status='orphaned'`. **Not
  implemented**. Scope TBD — see §5.
- **Validate-on-read**: `Fact.fitness_mean` (Bayesian smoothed) +
  `superseded_by` chain. Already covered by `semantic.py`.

---

## 5. Gap analysis (next cycles)

| Gap | Severity | Suggested cycle |
|-----|----------|-----------------|
| **L2 async reconciler** (scan audit log → flip stale L1-warned facts to `orphaned`) | MAJOR | cycle 181 — read-only daemon walking the warnings table; reuse `daemon_runner` (cycle #110.E) |
| **`commit_ref` column in schema** (currently `verified_by` is free-text) | MEDIUM | cycle 182 — `_SEMANTIC_TARGET_VERSION` v6 migration adding nullable `commit_ref TEXT` |
| **L1.X keyword expansion** (currently 3 detectors; corpus shows more shapes — e.g. "test PASS" without `pytest:` ref) | MEDIUM | cycle 183 — empirical audit of last 100 confab incidents, derive 1-2 new patterns |
| **L3 cold-start vs warm**: cycle 177 audit showed first `recall` pays 17s lazy import on subprocess path | MINOR | already mitigated by `HIPPO_EAGER_PRELOAD=1` in MCP server (cycle #24); document explicitly in this file |
| **L3 fitness-aware contradiction probe**: currently lexical only; could use embedding cosine threshold | MINOR | cycle 184 — extend `validate_claim` with a `cosine_threshold` arg; defaults preserve current behaviour |

### 5.1 Acceptance criteria for each gap closure

- **L2 reconciler**: end-to-end test fabricates 3 facts (SHIPPED keyword
  + no commit ref + L1 warning) → reconciler run flips all 3 to
  `orphaned`. TDD-style RED→GREEN.
- **`commit_ref` migration**: schema bump + backfill from
  `verified_by` parse (best-effort, NULL if no `commit:` ref).
  Migration tested with subprocess SQLite open before/after.
- **L1.X expansion**: empirical only — measure precision/recall on
  the audit-log of 100 most-recent confabulations.

---

## 6. References

- `engram/anti_confab_gate.py` — `run_validation_gate` orchestrator
  (cycle #138).
- `engram/anti_confabulation.py` — L1 family detectors (cycles
  #128 / #130 / #131).
- `engram/validate_claim.py` — L3 semantic probe (cycle #70).
- Fact `b0ac1291108f` — cycle 177 cold-start audit (relevant to L3
  cost).
- Fact `179aee63eca9` — cycle 179 corpus-scale bench (relevant to L3
  argpartition path).
- CLAUDE.md global rules — A1 (anti-confab) / A2 (anti-hallucination) /
  A3 (sincerità).
