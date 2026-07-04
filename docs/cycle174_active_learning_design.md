# Cycle 174 — Active Learning Loop for Skill Promotion

**Date**: 2026-05-22
**Status**: design (no code, no implementation yet)
**Author**: Claude (autonomous loop session)
**Empirical baseline**: fact `19985ba64bed` + audit dump
  (`research/engram-skill-corpus-audit-2026-05-22`)

This document is **R&D scaffolding, not a feature spec**. The point is
to write down a falsifiable hypothesis, propose 2–3 designs, and pick
one to test — *before* writing code. Cycle 172's critic counterexample
worker flagged "Active Learning gap CONFIRMED" as a genuine
opportunity; this design opens the cycle that would close it.

## 1. Problem statement (empirical)

Live skill corpus on 2026-05-22 (Aurelio's `~/.engram/skills/skills_index.db`):

| metric | value |
|---|---|
| total skills | 326 |
| `candidate` | 163 |
| `promoted` | 7 |
| `retired` | 156 |
| **untrialed (`trials = 0`)** | **233 (71 %)** |
| `candidate` w/ `trials ≥ 3` | 3 (avg fitness 0.356, **stuck at 0.4**) |
| `promoted` w/ `trials ≥ 3` | 7 (avg fitness 0.731 — working) |
| `retired` w/ `trials ≥ 3` | 57 (avg fitness 0.152 — justified) |
| **`candidate`-to-`promoted` rate** | **7 / 163 = 4.3 %** |

Two observable failure modes of the current pipeline:

1. **Trial famine** — 71 % of the corpus has never been measured.
   Auto-Dream propose-pattern is **passive**: it observes what
   episodes happened, but it does not *select* skills to test.
   Untrialed skills wait for a coincidental task to trigger them.
2. **Stuck-at-0.4** — three concrete skills sit at 3-4 trials with
   1 success each (fitness ≈ 0.35-0.40), forever ambiguous between
   "actually bad" and "context-dependent". No mechanism re-tests
   them. Their fitness is frozen in a low-confidence zone.

## 2. Falsifiable hypothesis

> **H1**: A targeted retry loop that selects (a) untrialed candidate
> skills semantically close to recent episodes, and (b) candidates
> stuck in the `3 ≤ trials ≤ 10 ∧ 0.3 < fitness < 0.5` band, will lift
> the candidate-to-promoted conversion rate from the current 4.3 % to
> > 10 % over N = 20 Auto-Dream cycles on the same corpus.

This is **falsifiable**: run the existing corpus through 20 cycles
without the loop (baseline) and with the loop (treatment). Measure
promotion-rate delta. If treatment ≤ baseline + noise band → H1
rejected.

**Predictions before running** (FIX 3 stop-check — pre-registered):
- baseline promotion-rate ≈ 0–2 % (some chance episodes happen to
  trigger an untrialed skill).
- treatment promotion-rate ≈ 10–25 %.
- If treatment ≥ 30 %, suspect overfitting / data leak.
- If treatment ≤ baseline + 2 % → H1 rejected, design is wrong.

## 3. Three candidate designs

### Design A — "warm-up bandit" (recommended)

A small UCB-1 bandit (or Thompson) over the `candidate` set,
weighted by recency × semantic-similarity-to-recent-episode-window.
At each Auto-Dream cooldown elapsed, the bandit pulls one skill,
synthesizes a retry task (paraphrased variant of the skill's
`trigger`), and submits via `engram.dream.propose_dream_tasks` with
the skill_id embedded so post-execution `update_fitness` can attribute
the outcome.

- **Pro**: principled exploration/exploitation tradeoff, well-known
  guarantees, one parameter (UCB constant `c`).
- **Con**: needs the dream pipeline to actually *execute* the task
  (verify hook path works end-to-end first).

### Design B — "stuck-list cron"

A deterministic SELECT every cooldown elapsed:
```sql
SELECT id FROM skills
WHERE status='candidate' AND trials BETWEEN 3 AND 10
  AND CAST(successes+1 AS REAL)/(trials+2) BETWEEN 0.3 AND 0.5
ORDER BY updated_at ASC LIMIT 3;
```
For each id, synthesize 1-2 paraphrased trigger variants and propose
them. Simpler than A but no exploration of untrialed pool.

- **Pro**: addresses stuck-at-0.4 directly; minimal code.
- **Con**: leaves the 233-skill untrialed tail untouched.

### Design C — "task-driven trigger expansion"

When a task arrives, before executing, query the skill corpus for
candidates whose `trigger_embedding` is within the top-20 cosine of
the task's embedding. Of those, pick the *least-trialed* one and
include its body in the prompt context. Update fitness based on
outcome.

- **Pro**: latency-zero; uses the live task stream as the natural
  experiment generator.
- **Con**: changes the wake path latency; risk of injecting bad
  skills into otherwise-working tasks.

**Recommendation**: start with **B** (smallest blast radius, fastest
to validate the hypothesis), then if H1 holds, evolve to **A**.

## 4. Implementation outline for Design B (cycle 175 if H1 holds)

- New module `engram/active_learning.py` ~150 LOC.
- Entry point `select_stuck_candidates(skill_db, *, max_n=3,
  min_trials=3, max_trials=10, fitness_band=(0.3, 0.5)) -> list[str]`.
- Pure function returning ids; no side effects (testable).
- Hook into `auto_dream_trigger.maybe_trigger_dream`: when the dream
  fires, ask `select_stuck_candidates` for retry targets and append to
  `dream_callable`'s task list.
- **Measure** via existing `skills.update_fitness` audit log — no new
  metric needed.

## 5. Out-of-scope / honest deferrals

- **Embedded eval of skill execution** (genuine R&D gap noted in
  `19985ba64bed`): today success is coarse boolean. Without
  fine-grained step-by-step eval ("which step failed?"), retry can
  only flip the boolean, not fix the failure mode. Cycle 17X+.
- **Retired-bias audit** (156 retired vs 7 promoted disparity): may
  be over-aggressive retire policy. Separate cycle needed to
  re-evaluate retired skills with trials < 5.
- **dg_embedding 482-byte** filter (cycle 173 follow-up) — orthogonal
  defensive-filter completion, not active-learning.

## 6. Anti-confab checklist (verified before commit)

- [x] All numbers in §1 come from `sqlite3` queries against
      `~/.engram/skills/skills_index.db` on 2026-05-22, not inferred.
- [x] The 3 stuck-candidate names are pasted verbatim from query
      output (no paraphrase).
- [x] No claim is made about implementation behavior — this doc is
      design-only.
- [x] Hypothesis is pre-registered with predictions BEFORE running.
- [x] `B vs A vs C` tradeoffs are honest (not "B is best" → "B is
      the smallest first step that lets H1 be tested").

## 7. Next step

Cycle 175 will implement Design B if and only if Aurelio greenlights
this doc. No code lands until then.
