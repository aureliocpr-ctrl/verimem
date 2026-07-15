# Memory Theses — chaining what we verified into what we should test next

**DRAFT 2026-07-15.** Method: B4 concatenation — take only *verified* results
(each with its receipt: a lab law, a shipped module, a benchmark file) and
chain them into **new, falsifiable theses** about what memory for AI agents
should be. Nothing below is claimed as established: each thesis states where
it follows from, the prediction that would falsify it, and the smallest
experiment that could kill it. The receipts live in this repo
(`engram/`, `benchmark/`), the vivarium lab (laws P39–P88), cortex
(laws verified on the future of ≥2 environments), composure (Library/Engine),
and the LLM-conjecture loop (AST-gated language + exact judge).

Honesty note: theses T1–T7 are *conjectures*. Partial evidence is labeled
`[evidence]`; everything else is `[open]`.

---

## T1 — Memory is an epistemic organ, not an archive

**Thesis.** A mature agent memory is defined by four active behaviours, not by
recall quality: (a) it refuses at the *write* boundary; (b) it probes its own
facts before the world contradicts them; (c) it can name what it is missing;
(d) it derives new knowledge only through the same admission gate as any
writer. Remove any one and the system regresses to an archive whose apparent
quality is an artifact of a benign environment.

**Follows from.** Write-gate (AUROC 0.971, `grounding_gate.py`) + active
probes (P87: probes kill spurious postulates in ~4 observations; passive =
limbo) + ignorance map (`ignorance_map.py`) + composition ring through the
gate (P76: composing *safe* 1.0 vs 0.333).

**Prediction.** On a store seeded with N facts of which k are stale-but-
plausible, an organ (gate+probe) retires ≥ half of the k *before any user
query touches them*; an archive with identical retrieval retires ~0.

**Minimal experiment.** 100 facts, 20 falsifiable against a public corpus;
run `active_probe.probe_fact` nightly; count pre-query retirements.
`[evidence: P87 in-lab; open: on real corpora]`

## T2 — The single-witness law (consensus is worthless until deconfounded)

**Thesis.** *Any* agreement signal — multiple sources, multiple model votes,
an LLM's own self-consistency sampling — is manufacturable and therefore
worthless as evidence until it is conditioned on an independent error channel
(an audit, a do-operator). This is one theorem wearing three coats: source
cartels, judge panels, and self-consistency decoding are the same object.

**Follows from.** P88 (agreement confounded by shared truth; conditioning on
audit-revealed-false isolates collusion — cartel 0.90→0.20, honest→0.95,
3/3 seeds on HaluEval) + P66 (correlated noise) + the observation that an
LLM's k samples share one bias (an internal cartel).

**Prediction.** Majority-vote self-consistency (k=5) does NOT reduce
hallucinations on items where the model's bias is systematic (the votes
collude); the same budget spent on one external entailment check does.

**Minimal experiment.** HaluEval unanswerables: k-vote vs single+gate at
equal token budget; compare wrong-answer rates on the systematic-bias slice.
`[evidence: P88 for sources; open: for self-consistency]`

## T3 — The write boundary is the asymmetric leverage point

**Thesis.** A verification bit spent at write-time is worth strictly more
than the same bit at read-time, and the gap *grows with reuse*: a written
error is amplified by every downstream retrieval, derivation, and
consolidation that touches it. Verification cost to hold error-rate ε is
~O(1) per fact at the write boundary but ~O(reuse) at the read boundary.

**Follows from.** HaluMem's operation-level finding (errors accumulate at
extraction/updating and propagate to QA) + our composition ring (derived
facts cite parents; one poisoned parent taints the closure) + NET(λ)
head-to-heads (the floor-off store fabricates exactly on the unanswerable
half).

**Prediction.** Equal verification budget allocated pre-write beats pre-read
on final NET(λ), with the margin increasing in the store's reuse factor
(recalls-per-fact).

**Minimal experiment.** Same store, same budget B of entailment checks:
(a) gate B writes, (b) check B reads; sweep reuse 1×→10×; plot NET(2).
`[open]`

## T4 — Epistemic labels are a type system for knowledge

**Thesis.** `proven / unbeaten(bound) / refuted` behave like types, and
derivation behaves like typed composition: a derived fact's label must be the
*minimum* of its parents' labels (with `refuted` absorbing). A memory that
propagates labels this way is *type-safe for knowledge*: it can grow
overnight without ever minting a false "proven". A memory that composes
without label propagation mints false confidence at a rate that grows with
derivation depth.

**Follows from.** `epistemic.py` (monotone transitions, refuted absorbing) +
composure's Engine (compose with explanations) + the LLM-conjecture loop
(a richer language is safe only because an exact judge gates admission —
25 proposals → 22 exact-TRUE / 3 killed).

**Prediction.** On derivation chains over verified sequence relations
(cortex/OEIS), min-propagation yields 0 false-proven at any depth;
no-propagation yields false-proven growing ~linearly with depth.

**Minimal experiment.** 3-deep derivation chains on the 214-family base,
with and without label propagation; count false-proven per depth.
`[evidence: label mechanics shipped+tested; open: the depth law]`

## T5 — Abstention is a contract, and contracts compose

**Thesis.** Declaring λ and *operating* at it (TCE ≈ 0) turns a memory into a
predictable economic agent. The new part: the contract **composes** — a
router over k stores keeps the declared λ if and only if every store keeps it
AND the router abstains on inter-store disagreement. Federated memory is
therefore possible without re-calibration, as long as disagreement maps to
silence, not to averaging.

**Follows from.** §5.4 (raw scores rank near-oracle but promise ≠ delivered;
isotonic calibration → TCE ≤ 0.011 at declared λ) + P79 (federation) + P82
(SLA risk-coverage) + the two-store trust experiments.

**Prediction.** Two stores each TCE-calibrated at λ, routed with
disagreement→abstain, hold the joint observed risk at the declared level;
replacing abstain with score-averaging breaks it.

**Minimal experiment.** Split HaluEval into two stores; calibrate each;
compare router policies. `[open]`

## T6 — The fact language bounds what memory can learn

**Thesis.** If a store can only hold flat atomic facts, its *composable*
knowledge saturates regardless of scale; enriching the fact language
(relations with products, indices, conditions — an AST-gated grammar, not
free text) opens knowledge classes that no amount of flat accumulation
reaches. The safety cost of the richer language is bounded by an exact or
near-exact judge at admission.

**Follows from.** LLM-conjecture (composition over the linear language
saturated; the DSL found 19 genuinely non-linear relations on real b-files;
judge killed 3/25, halluc 0.12 = the judge is load-bearing) + P54/P80
(composition, linear depth) + T4's typed admission.

**Prediction.** On a relational corpus, an enriched-language store admits
verified relations that are *inexpressible* in the flat store, at a false-
admission rate held near the judge's error, not the proposer's.

**Minimal experiment.** Port the conjecture DSL to one non-OEIS domain
(unit conversions or API-behaviour facts); measure inexpressible-but-
verified yield vs flat baseline. `[evidence: OEIS; open: second domain]`

## T7 — The echo threshold (self-writing has a phase transition)

**Thesis.** An agent that writes into its own memory becomes deaf to the
world not gradually but at a *phase transition* in the self-write ratio
(~0.5): beyond it, self-echo sustains itself and external drift stops being
detected. Below it, signed self-writes (`actor:*`, never testifying) are
harmless. This is a hard population-level constraint for self-improving
agents, not a tunable.

**Follows from.** P85 (self-provenance: exact transition at 0.5 in-lab;
`self_provenance.py` ships the monitor+alarm) + P58 (organism) + T2 (the
self is the ultimate colluding cartel).

**Prediction.** Agents with enforced self-write quotas q<0.5 keep
drift-detection latency ~flat in q; crossing 0.5 produces a discontinuous
jump, robust to the drift's magnitude.

**Minimal experiment.** Memory-equipped agent on a drifting environment,
q ∈ {0.2,0.4,0.45,0.55,0.6}; measure drift-detection latency.
`[evidence: transition in-lab; open: with a real LLM agent]`

---

## What this buys us

Chained, T1–T7 sketch a research programme: **memory as a typed, economically
calibrated, self-probing epistemic organ whose language — not its size — sets
its ceiling, and whose worst enemy is its own echo.** Each thesis is small
enough to kill in a week and valuable enough to publish either way. The next
lever (per the organism plan) is T6's second domain and T2's self-consistency
slice — both reuse infrastructure that already exists in this repo.

*Receipts: `engram/{grounding_gate,source_trust,epistemic,composer,
self_provenance,active_probe,ignorance_map,selective_metrics}.py` ·
`benchmark/{veribench/,source_trust_realcorpus.py,selective_deployment.py}` ·
vivarium laws P39–P88 · cortex `Code/cortex` · composure `Code/composure` ·
conjecture loop `Code/cortex/llm_conjecture.py`.*
