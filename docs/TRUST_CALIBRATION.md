# Trust-signal calibration — R&D report (2026-06-16)

Judge-free, 100% local, reproducible from this repo. Every number below comes
from `scripts/bench_trust_calibration.py` and `scripts/bench_trust_scorers_compare.py`
(n=1000, mean of 3 seeds).

## 1. The question

Engram attaches a meta-trust verdict to every recalled fact
(`trusted/stale/contested/obsolete/unverified`). The anti-confabulation moat
rests on that verdict being **calibrated**: when Engram implies a fact is
reliable, it should be — and when it flags risk, the risk should be real.
"It has a trust signal" is a claim; this is the measurement.

## 2. Method (avoiding the tautology)

The hard part: the ground-truth `reliable` flag must be **independent** of the
properties the signal reads (supersession, contradictions, age, status) —
otherwise the test is circular. So the dataset is a simulated world with a fixed,
declared composition (`engram/trust_calibration_eval.py`), and reliability is set
by the *world*, not by Engram:

| stratum | reliable | note |
|---|---|---|
| 40% current, verified | 1 | |
| 20% obsolete in the world | 0 | supersession recorded w.p. `1 - unobserved_p` |
| 15% contested | 0 | a contradiction is recorded |
| 15% old (>180d) but still true | 1 | a stable fact |
| 10% low-conf `model_claim` | half 1 / half 0 | |

The dial is **`unobserved_p`**: the fraction of obsolete facts whose
supersession Engram *never observed* — an external knowledge-update the memory
didn't witness. Verdicts are mapped to an implied P(reliable)
(`trusted→0.9, stale→0.5, unverified→0.4, contested→0.2, obsolete→0.05`) and
scored with Brier, ECE, and a reliability table. Two operational rates:
**over-trust** = fraction of truly-unreliable facts implied ≥0.70 (the dangerous,
confabulation-enabling error); **over-caution** = truly-reliable facts implied ≤0.50.

## 3. Results

### 3.1 Calibration vs observation completeness (categorical signal)

| unobserved_p | Brier | ECE | over-trust | over-caution |
|---|---|---|---|---|
| 0.00 | 0.074 | 0.165 | **0.000** | 0.333 |
| 0.25 | 0.115 | 0.128 | 0.126 | 0.333 |
| 0.50 | 0.151 | 0.166 | 0.238 | 0.333 |
| 0.75 | 0.195 | 0.212 | 0.374 | 0.333 |
| 1.00 | 0.235 | 0.255 | **0.500** | 0.333 |

Reliability @ `unobserved_p=0.5`: the `trusted` bucket (implied 0.9) is empirically
reliable only **0.813** of the time — the over-confidence is the unobserved
updates leaking in.

### 3.2 Three scorers, same ground-truth

| world | scorer | Brier | ECE | over-trust | over-caution |
|---|---|---|---|---|---|
| observed | categorical (shipped signal) | 0.074 | 0.165 | 0.000 | 0.333 |
| observed | continuous **R14** (`compute_trust_score`) | 0.258 | 0.355 | 0.115 | 0.333 |
| observed | **calibrated prototype** | **0.035** | **0.087** | 0.000 | **0.083** |
| half-blind | categorical | 0.151 | 0.166 | 0.238 | 0.333 |
| half-blind | continuous R14 | 0.258 | 0.355 | 0.115 | 0.333 |
| half-blind | **calibrated prototype** | 0.116 | 0.085 | 0.238 | 0.083 |

## 4. Findings

1. **The categorical signal is SAFE but pessimistic.** With full observation its
   dangerous over-trust is **0.000** — it never calls a truly-unreliable fact
   trusted when it saw the change. But it over-cautions a third of reliable facts
   (the 180-day `stale` cliff discounts verified-but-old facts).
2. **The shipped continuous score (R14) is the worst-calibrated** (Brier 0.258,
   ECE 0.355) because it *ignores supersession and contradictions* — it
   over-trusts obsolete facts even in the fully-observed world (0.115) — and
   decays every fact by age. **This is a real product finding:** the score behind
   `hippo_rank_facts_trust` should fold in the signal's evidence.
3. **A calibrated score nearly halves Brier and cuts over-caution 4×** (0.035 /
   0.083 vs 0.074 / 0.333) by using supersession + contradictions like the signal
   but dropping the age cliff for verified facts — without adding any over-trust.

## 5. The wall, and the roadmap

The decisive result: in the half-blind world the **calibrated** scorer's
over-trust (0.238) equals the categorical one's. **No scoring function fixes
over-trust** — it scales 0.000 → 0.500 purely with `unobserved_p`. The only lever
is *observing more change*. That is the empirical argument for:

- **(near)** Fold the signal's evidence into a continuous, calibrated trust score
  and replace the R14 formula — halves Brier, removes most over-caution, ships now.
- **(core)** A **truth-reconciliation loop**: let Engram learn obsolescence from
  tool-call outcomes, user corrections, and cross-source disagreement, driving
  `unobserved_p` toward 0 — the only thing that moves the dangerous metric.

## 6. Reproduce

```
python scripts/bench_trust_calibration.py        # calibration vs observation
python scripts/bench_trust_scorers_compare.py    # 3-scorer comparison
pytest tests/test_trust_calibration_metrics.py tests/test_trust_calibration_eval.py
```
