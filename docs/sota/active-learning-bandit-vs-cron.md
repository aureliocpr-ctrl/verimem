# SOTA — Active learning: stuck-list cron (Design B) vs multi-armed bandit (Design A)

**Status**: documentation; retrospective on cycle 174 design choice + H8 falsifiable proposal.
**Date**: 2026-05-23 (cycle 209).
**Scope**: comparing the **stuck-list cron** that shipped in cycle 175 (Design B) against the **warm-up multi-armed bandit** that was considered but deferred (Design A), and the **task-driven expansion** that was considered but deferred (Design C). Companion to the SOTA series 180/185/188/190/192/203/206.

---

## 1. Background — the cycle 174 decision

The cycle 174 design doc (PR #114, merged 2026-05-21) audited the live corpus and found:

- **233/326 skills (71%) untrialed** — large warm-up problem.
- **3 candidates stuck at fitness 0.33–0.40** — narrower retry problem.
- **candidate → promoted conversion rate: 4.3 %** (7/163 over project lifetime).

Three designs were on the table:

| Design | What it does | Solves |
|--------|--------------|--------|
| A — warm-up bandit | UCB / Thompson sampling over untrialed skills | 71% untrialed |
| B — stuck-list cron | deterministic SQL retry for fitness ∈ (0.3, 0.5) | 3 stuck candidates |
| C — task-driven expansion | propose new skill IDs from task semantics | (orthogonal) |

Aurelio greenlit Design B (cycle 175) because:
1. Simplest first implementation (pure SQL, no exploration math).
2. The stuck band is the smallest, most measurable target.
3. Failure of B is cheap to detect (cycle 175.2 pilot H1).

Design A and C were **explicitly deferred**, not killed.

---

## 2. Empirical update (post-cycle 175 shipping)

- **Cycle 175 + 175.1 shipped** in cycle 175 / 175.1. Live E2E verified the cron picks the exact 3 stuck candidates from fact `d778cce2faa8`.
- **Cycle 175.2 pilot NOT YET run** — requires multi-day Auto-Dream cadence × 20 cycles. H1 (4.3 % → > 10 % promotion rate) untested.
- **The 71 % untrialed problem is STILL OPEN.**

So Design B is necessary but not sufficient. A complementary Design A wave is the natural follow-up once H1 has results.

---

## 3. SOTA — Multi-Armed Bandit options for warm-up (Design A revisited)

The "explore untrialed skills" subproblem maps cleanly to the **best-arm identification** literature:

| Algorithm | Exploration formula | Pros / cons |
|----------|----------------------|-------------|
| **UCB1** | `μ + sqrt(2 ln(t) / n)` | Deterministic, requires `n ≥ 1` per arm |
| **Thompson sampling** | Beta(α=successes+1, β=failures+1) | Natural for the `(s+1)/(t+2)` smoothed fitness already in HippoAgent! |
| **UCB-Tuned** | UCB1 + variance term | Best practical performer on stochastic bandits |
| **ε-greedy** | uniform random with prob ε | Simplest, weakest theory |

**Native fit for HippoAgent**: Thompson sampling. The cycle-129 (cycle #129) Bayesian smoothed fitness `(s+1)/(t+2)` is **literally** the posterior mean of a Beta(s+1, t-s+1). Switching to Thompson sampling means drawing a sample from that posterior per skill and picking the arg-max — natural, low-effort.

---

## 4. Design — `engram/active_learning_thompson.py` (proposed cycle 210)

API sketch:

```python
def thompson_sample_candidates(
    skill_db: Path, *, max_n: int = 3,
    rng_seed: int | None = None,
) -> list[str]:
    """Sample skill IDs proportional to their Beta posterior.

    Filters: status='candidate' AND trials < min_trials_for_promotion.
    Returns the top-max_n by Thompson-sampled value.
    """
```

Composes naturally over the existing `engram.skill` schema. No
side effect, fully testable with `rng_seed`. The Auto-Dream worker
would then concatenate the Thompson seed alongside the existing
stuck-list cron seed (cycle 175.1) and the community seed
(cycle 187) in the `instructions` text passed to
`propose_dream_tasks`.

---

## 5. Gap analysis (follow-up cycles)

| Gap | Severity | Cycle |
|-----|----------|-------|
| **Thompson sampling primitive** | MEDIUM | cycle 210 — pure-numpy stats.beta draw + arg-max top-n + TDD |
| **Wire into dream_stuck_hook style** | MEDIUM | cycle 211 — dream_thompson_hook composable as cycle 175.1 |
| **Bench H1 (cycle 175.2)** | DEFERRED | scheduled multi-day pilot |
| **Bench H8: A∥B vs B-only** | NEW | cycle 212 — does Thompson + stuck combined lift promotion rate further? |
| **Bench H9: cold-start fairness** | LOW | cycle 213 — measure how many untrialed get a turn per N dream cycles |
| **Design C task-driven expansion** | DEFERRED | cycle 215+ — needs skill-name generator (LLM-augment cycle 168 reusable) |

### 5.1 Acceptance — cycle 210 Thompson primitive

- TDD: synthetic skill set with known (s, t) → sampled output favours arms with higher posterior mean over many runs (statistical, ~1000 draws).
- Empirical: 326-skill corpus → returns 3 candidates in < 10 ms.
- Defensive: empty skill set → []; missing DB → [].

### 5.2 Falsifiable hypothesis H8 (NEW)

After enabling cycle 211 (Thompson hook alongside cycle 175.1 stuck hook) in Auto-Dream for 20 cycles, the candidate→promoted conversion rate improves by ≥ 5 percentage points absolute against the cycle-175-only baseline measured in H1. Falsification: gain ≤ 2 pp → bandit not worth the added complexity; revert to stuck-list only.

---

## 6. Caveat A1 onesti

- This doc is **retrospective + design**; cycle 210-213 are PROPOSALS.
- The 4.3 % baseline (cycle 174 audit) is from a single corpus snapshot — H1 / H8 should be measured on the same corpus state for apples-to-apples.
- Design C (task-driven expansion) is orthogonal to A/B — could be a third hook seed.
- Thompson sampling requires `scipy.stats.beta` (already in `pyproject.toml` deps line 43), so NO new dep.

---

## 7. References

- `engram/active_learning.py` — cycle 175 deterministic stuck cron.
- `engram/dream_stuck_hook.py` — cycle 175.1 instructions wire.
- Auer, Cesa-Bianchi, Fischer 2002 — UCB1 foundational.
- Thompson 1933 — original posterior-sampling paper.
- Chapelle & Li 2011 — "An Empirical Evaluation of Thompson Sampling" — modern revival.
- `docs/sota/community-detection-channel-pattern.md` (cycle 185).
- `docs/sota/multi-signal-fusion.md` (cycle 190) — same RRF-style composition idea applies to multi-hook dream seeds.
