# Held-out bench — practical tasks (NOT digit-sum)

**Provider:** Anthropic Claude Opus 4.7
**Date:** 2026-05-10

## Setup

5 TRAIN tasks (text/string manipulation primitives) → sleep consolidate →
5 HELD-OUT tasks (different inputs, same task family).

## Results

| Phase | Success | Rate |
|-------|--------:|-----:|
| TRAIN | 5/5 | **100%** |
| **HELD-OUT** | **5/5** | **100%** |

## Per-task breakdown

| Phase | Task ID | Description | Answer | Match | Tokens | Skills |
|-------|---------|-------------|--------|:-----:|--------|-------:|
| TRAIN | t1_dom | Extract domain from URL | `www.example.com` | OK | 4427 | 3 |
| TRAIN | t2_date | ISO date → English long | `January 15, 2026` | OK | 4579 | 3 |
| TRAIN | t3_cap | Capitalize each word | `The Quick Brown Fox` | OK | 4453 | 3 |
| TRAIN | t4_rev | Reverse string | `fedcba` | OK | 4514 | 3 |
| TRAIN | t5_count | Word count | `9` | OK | 3687 | 3 |
| HELD-OUT | h1_dom | Different URL | `api.github.com` | OK | 4248 | 3 |
| HELD-OUT | h2_date | Different date | `December 25, 2027` | OK | 4393 | 3 |
| HELD-OUT | h3_cap | Different sentence | `Hippoagent Is A Memory Layer` | OK | 4448 | 3 |
| HELD-OUT | h4_rev | Different string | `dlrow olleh` | OK | 4401 | 3 |
| HELD-OUT | h5_count | Different text | `5` | OK | 3982 | 3 |

## Consolidate report

- 6 clusters → 6 NREM skills + 2 REM skills
- 0 promoted (trial count gate not yet reached at n=5)

## Conclusion

Held-out generalization on practical text/string tasks: **100%**. The
agent retrieves 3 relevant skills per task (built during the train
phase) and applies them to fresh inputs without per-task re-discovery.

Token cost remains in the 3.5-4.5k range per held-out task — comparable
to TRAIN, since none of these skills compiled into a deterministic macro
(would need n_iter ≥ 3 for fitness threshold; here we run each task
once). For lower-cost replay see `bench_learning_curve_anthropic_n5`.
