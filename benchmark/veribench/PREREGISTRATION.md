# VeriBench — pre-registration (real run)

A benchmark is only serious if its hypothesis, metric, and refutation conditions
are fixed **before** the numbers are seen, so a favourable result cannot be
manufactured by choosing the metric after the fact. This file is that commitment.
The scoring (`scoring.py`) and the outcome mapping (`real_axis.py`) — the only
places a result could be biased — were written and unit-tested (5 cases,
`tests/test_veribench_real_axis.py`) before the run in `run_real.py`.

## Hypothesis

**H1.** On a real external corpus containing both *answerable* and *unanswerable*
questions, a memory with an abstention floor (verimem) achieves a `NET(λ)` that
stays **positive** and decays slowly as the wrong-answer penalty `λ` rises, while
the **identical retrieval with the floor off** goes **NET-negative** at high `λ`
— because with no floor it returns a nearest neighbour on unanswerable questions
(fabrication). A symmetric `recall@k` (correct/n) **cannot** separate the two: on
the answerable half they retrieve identically.

## Metric (declared before the run)

- `NET(λ) = (correct − λ·wrong) / n`, swept over **λ ∈ {1, 2, 5, 10}** (fixed).
- `coverage = (correct + wrong) / n`; `crossover_lambda = correct / wrong`
  (the λ at which a system turns net-negative; `∞`/None ⇒ never, i.e. no wrong
  answers).
- Outcome mapping (fixed in `real_axis.py`): answerable → CORRECT if committed &
  retrieved, WRONG if committed & missed, ABSTAIN if declined; unanswerable →
  ABSTAIN if declined, WRONG if committed.

## Data

- **HaluEval QA**, cut into **disjoint deterministic splits** (`--make-samples`):
  `heldout` (answerable) and `unanswerable-probe`. The store ingests each
  answerable item's `knowledge` (one crowded store); the unanswerable probes are
  questions whose supporting knowledge was **never ingested**, so abstention is
  the only honest output.
- **τ = 0.80** is fixed a priori from the answerable-vs-absent score-band
  separation measured earlier on the read-path (answerable ≥0.76 vs unanswerable
  ≤0.83; separability AUROC 0.9916), and applied unchanged to the heldout split.

## Systems

1. `verimem_abstain` — the product, abstention floor **τ = 0.80**.
2. `no_abstention_baseline` — the **same store and retrieval** with **τ = 0**
   (never abstains). A confound-free stand-in for a coverage-blind / no-floor
   memory: identical embedder and index, so any NET gap is the abstention effect
   alone, not a different stack.
3. `scrambled_control` — **validity negative control**: the query↔fact alignment
   is destroyed by a fixed-seed shuffle while the system keeps committing.

*mem0 (installed, v2.0.11) is not run here: as shipped it requires an external LLM
API key, which this project does not use. The adapter is in `competitors.py`; the
controlled baseline above is the cleaner, confound-free comparison and is what we
report.*

## Refutation conditions (what would sink H1)

H1 is **refuted** if any of these hold on the run:

- `no_abstention_baseline` NET(λ=5) **≥** `verimem_abstain` NET(λ=5), or
- `verimem_abstain` NET(λ=5) **< 0** (the floor does not keep it net-positive at
  high stakes), or
- the `scrambled_control` does **not** collapse (its `correct` is not far below
  `verimem_abstain`'s) — which would mean the headline CORRECT is a harness
  artifact, not real retrieval.

## Scope (honest boundary)

VeriBench measures **one property**: converting *can't-know* into silence instead
of a confident wrong answer, and doing so on a real corpus. It is **not** a
general-quality or head-to-head-superiority claim. A high VeriBench score says the
memory knows when it does not know — nothing more, and nothing less.
