# VeriBench — the public standard for trusted memory

Retrieval benchmarks ask *did you find it?* VeriBench asks the question a memory a
model actually depends on must answer: **do you know when you _don't_ know?**

A `recall@k` score is symmetric — a confident wrong answer and an honest "I don't
know" are scored the same when the item is unanswerable, so trust is **invisible**
to it. VeriBench makes trust a number by scoring the two things recall cannot see:

1. **Abstention** — converting *can't-know* into silence instead of a confident
   fabrication.
2. **Independent provenance** — corroboration that survives copies, echoes, and
   collusion (N mirrors of one feed are **one** witness, not N).

It is deterministic, model-free, and network-free: every axis scores observable
system behavior, so a run is reproducible and cannot be gamed by a lucky sample.

---

## Scoring: `NET(λ)`

Each item yields one `Outcome` — `CORRECT`, `WRONG`, or `ABSTAIN` (abstention is a
first-class outcome, neither right nor wrong). For a penalty `λ` on wrong answers:

```
NET(λ) = (correct − λ · wrong) / n
```

- `λ = 1` is symmetric. `λ > 1` means a wrong answer costs more than silence — a
  legal/medical setting. Sweeping `λ ∈ {1, 2, 5, 10}` is the whole point: it is
  exactly where a fabricator and an honest abstainer separate.
- `coverage = (correct + wrong) / n` — how often the system commits to an answer.
- `crossover_lambda = correct / wrong` — the `λ` at which the system turns
  net-negative. Higher is more trustworthy.

`scoring.py` is the load-bearing core (`net_score`, `coverage`, `crossover_lambda`,
`scorecard`); it depends on nothing else.

---

## The λ through-line — one number, end to end

The same `λ` the benchmark scores at is the number the **product** is tuned at.
Decision theory: answer a candidate with probability-of-correct `p` iff
`p·1 − (1−p)·λ > 0`, i.e. `p > λ/(1+λ)`. That threshold **is** the `NET(λ)`
break-even accuracy. So `λ` means the same thing in the benchmark and in the store
(`engram/sla.py`, `ENGRAM_ERROR_COST`): measure at `λ`, deploy at `λ`.

---

## Axes

| axis | module | what it exposes | headline (deterministic) |
|---|---|---|---|
| **Abstention** | `__main__.py` | fabricator vs honest on answerable+unanswerable | recall@k **0.5 = 0.5** (invisible); NET λ=5 fabricator **−2.0** vs honest **+0.5** |
| **Competitors** | `competitors.py` | a floor-less store (e.g. mem0) fabricates on the unanswerable | loses to abstention under NET(λ>1), *on the answerable it is parity* |
| **Causal / do-query** | `causal_axis.py` | provenance ≠ causality: honest sources corroborate a spurious `X~Y` | trust-only NET λ=5 **−3.5** vs scope-aware **+0.6**; defended `λ*` **0.333** (<1 → λ=1 is a *defended* floor) |
| **Adversarial trust** | `adversarial_axis.py` | collusion + trusted-sleeper, driving the **real** `SourceTrustBook` | only `min_both` (two channels) net-positive: naive **−1.33**, consistency-only **−1.33**, **min_both +0.33** |

The adversarial axis is the capstone: robustness needs **two orthogonal channels** —
independent corroboration (defeats collusion) **and** outcome (defeats the sleeper
who earns reputation then lies where unwitnessed). Each single channel fails one
attack; only their conjunction survives both.

---

## Plugging in a system

Every system under test — Verimem, mem0, any competitor — implements one contract:

```python
answer_fn: Callable[[str], str | None]   # return the answer, or None to abstain
```

```python
from benchmark.veribench.axes import ProbeItem, run_axis
from benchmark.veribench.scoring import scorecard

items = [ProbeItem("capital of France?", "Paris"),
         ProbeItem("next week's lottery numbers?", None)]   # gold=None = unanswerable

outcomes = run_axis(items, my_answer_fn)
print(scorecard(outcomes))          # counts + coverage + NET λ-sweep + crossover
```

Adapters live in `runner.py` (`make_verimem_answer_fn`) and `competitors.py`
(`make_mem0_answer_fn`). A competitor with no abstention floor returns its nearest
neighbor for *any* query, so it scores `WRONG` exactly where a trusted memory
abstains — the gap NET(λ) makes visible. This is **not** a recall contest; on
answerable items everyone retrieves alike (parity, honestly stated). It is a trust
contest, on axes a recall-only system does not have.

---

## Real run (HaluEval) — pre-registered result

Not the toy demo: `run_real.py` scores three systems on a **real external corpus**
(HaluEval QA — 200 answerable + 100 unanswerable, disjoint deterministic splits),
with the hypothesis, metric, and refutation conditions fixed **before** the run
([PREREGISTRATION.md](PREREGISTRATION.md)).

```bash
python -m benchmark.veribench.run_real --n 200 --tau 0.80
```

Result (`benchmark/results/veribench_real_halueval-qa_2026-07-13.json`):

| system | coverage | recall@k | NET λ=1 | NET λ=2 | NET λ=5 | NET λ=10 | crossover λ |
|---|--:|--:|--:|--:|--:|--:|--:|
| **verimem** (abstain, τ=0.80) | 0.62 | 0.607 | +0.593 | +0.580 | **+0.540** | +0.473 | 45.5 |
| no-abstention baseline (τ=0) | 0.97 | 0.640 | +0.307 | −0.027 | **−1.027** | −2.693 | 1.92 |
| scrambled control (validity) | 0.97 | 0.017 | −0.940 | −1.897 | −4.767 | −9.550 | 0.02 |

In one line: on **recall@k the baseline wins** (0.640 > 0.607) — the naive metric
literally prefers the system that fabricates. On **NET(λ=5) verimem is +0.54 and
the baseline is −1.03** (a 1.57 gap): the baseline returns a nearest neighbour on
the unanswerable questions and goes net-negative at λ≈2, while verimem — the *same
retrieval* with the floor on — makes 4 wrong answers and stays net-positive out to
λ≈45. The cost is stated honestly: verimem's coverage is lower (0.62 vs 0.97)
because the floor also over-abstains on some answerable items.

The **scrambled control** is the validity check: destroying the query↔fact
alignment collapses verimem's correct count from 182 to 5 (chance), so the headline
is real retrieval, not a harness artifact. All three pre-registered refutation
conditions are FALSE → **H1 confirmed**.

### Head-to-head vs the real mem0 (offline, TWO corpora)

`run_mem0.py` drives **mem0 v2.0.11's actual stack** (Chroma vector store, its
`search`) with the **same `intfloat/multilingual-e5-base` model and `query:` /
`passage:` prefixes** as verimem — retrieval parity, so the only free variable is
the abstention floor. mem0's LLM extraction needs an external key we don't use, so
memories are stored raw (that does not touch the abstention question). Run on two
independent corpora, each system scored at its OWN oracle floor (swept on the eval —
an upper bound for BOTH, so the comparison is symmetric):

| corpus | system | coverage | recall@k | NET λ=1 | NET λ=5 |
|---|---|--:|--:|--:|--:|
| HaluEval | **verimem** (τ=0.80 = its oracle) | 0.62 | 0.607 | +0.593 | **+0.540** |
| HaluEval | mem0 as shipped (no floor) | 1.00 | **0.667** | +0.333 | **−1.000** |
| HaluEval | mem0 at its oracle floor (0.75) | 0.55 | 0.553 | +0.553 | +0.553 |
| SQuAD v2 | verimem (τ=0.80 *from HaluEval*) | 0.71 | 0.543 | +0.380 | **−0.273** |
| SQuAD v2 | **verimem** at its oracle floor (0.85) | 0.35 | 0.327 | +0.303 | **+0.210** |
| SQuAD v2 | mem0 as shipped (no floor) | 1.00 | **0.667** | +0.333 | **−1.000** |
| SQuAD v2 | mem0 at its oracle floor (0.80) | 0.15 | 0.147 | +0.147 | +0.147 |

What holds and what doesn't — stated plainly, because a benchmark that hides its
limits isn't one:

- **Robust across both corpora: a memory with no floor fabricates.** mem0 as shipped
  posts the **highest recall@k on both (0.667)** yet NET(λ=5) **−1.0 on both** — it
  commits a neighbour on every unanswerable probe. The standard metric rewards it;
  VeriBench is the metric that doesn't. This is the finding that generalizes.
- **The floor is corpus-dependent — a dial, not magic.** verimem's τ=0.80 was its
  oracle on HaluEval, but transfers to SQuAD at NET(λ=5) **−0.273** (net-negative):
  the same floor over-commits on Wikipedia passages. Re-tuned on SQuAD (0.85) verimem
  is positive again (+0.210) and beats mem0's oracle floor (+0.147) — but coverage
  falls to 0.35, because score-threshold abstention is intrinsically harder when the
  embedder separates answerable from unanswerable less cleanly.
- **At each system's oracle floor the two are close** (HaluEval: mem0 +0.553 vs
  verimem +0.540; SQuAD: verimem +0.210 vs mem0 +0.147). So verimem's edge is NOT a
  secret algorithm — it is **shipping the floor calibrated and ON by default** (plus
  the write-gate and independence axes). A bare vector memory ships without it.

The honest bottom line on two corpora: **abstention is what separates a *trusted*
memory from a *confident* one; the standard benchmark can't see it; and it must be
calibrated per corpus.** mem0 as shipped has no floor and fabricates; verimem ships
one, and VeriBench is what makes the difference a number.

---

## Running

```bash
python -m benchmark.veribench                    # abstention demo
python -m benchmark.veribench.run_real --n 200   # the REAL run (HaluEval)
python -m benchmark.veribench.causal_axis        # provenance ≠ causality
python -m benchmark.veribench.adversarial_axis   # collusion + sleeper
pytest tests/test_veribench_*.py                 # the full suite
```

## Guard-rails

Parity is stated as parity — never "surpass". "Best" is not claimed until a
competitor is beaten on a metric that is not our own. New store mechanisms
(source-trust independence, deconfounding) ship behind flags, default OFF, pending
held-out reproduction on real corpora. See `benchmark/TRUST_CORE.md`.
