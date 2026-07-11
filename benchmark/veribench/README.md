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

## Running

```bash
python -m benchmark.veribench                    # abstention demo
python -m benchmark.veribench.causal_axis        # provenance ≠ causality
python -m benchmark.veribench.adversarial_axis   # collusion + sleeper
pytest tests/test_veribench_*.py                 # the full suite
```

## Guard-rails

Parity is stated as parity — never "surpass". "Best" is not claimed until a
competitor is beaten on a metric that is not our own. New store mechanisms
(source-trust independence, deconfounding) ship behind flags, default OFF, pending
held-out reproduction on real corpora. See `benchmark/TRUST_CORE.md`.
