# Engram Epistemic Research Program

**A structured program to make Engram the most epistemically-reliable LLM memory: it
does not hallucinate, does not store narratives as truth, does not cave to confident
assertions, and knows the epistemic state of everything it holds.**

Owner: Aurelio (CEO) · Lead: CTO. Constraint: Claude subscription only (`claude -p`), no
external API (O5). Method: pre-registration → falsifiable experiment → independent critic
→ commit. Every claim carries n, seed(s), model(s), and a 95% CI. No half-work: a phase is
DONE only when its deliverable is tested, critic-gated, pushed, and its falsification
criterion was actually run.

This program is the forward plan. The completed prologue (R1–R11, the unified
proxy-substitution thesis, the write-path moat) lives in `docs/EPISTEMIC_FAILURES_STUDY.md`.

---

## 0. The thesis we are testing (one sentence)

Hallucination, confabulation, sycophancy, and memory-rot are **four faces of one failure**:
the system substitutes a CHEAP PROXY (plausibility / coherence / self-confidence / recency)
for the EXPENSIVE signal it should require (explicit, entailing evidence). The cure is one
discipline — **evidence-grounding** — applied at the right boundary for each face. The
program's job is to prove or break this on every axis, with numbers that survive a skeptic.

Current evidence (prologue, sonnet-4-6, single-seed unless noted):
- Confabulation (WRITE path): source⊢fact gate, **AUROC 0.971 SNLI [CI 0.943–0.991], 0.992
  realistic [CI 0.972–1.000]**. Shipped + live via `hippo_remember(source=)`. ← the moat.
- Hallucination (ANSWER path): strict prompt halves SQuAD fabrication 0.26→0.14; external
  gate is DOMINATED by it (not the moat here).
- Calibration: verbalized confidence is over-confident (ECE 0.17), a moderate signal
  (AUROC 0.66–0.81), NOT at chance (an earlier "at chance" claim was a measurement bug).
- Sycophancy: evidence-gate flips cave-rate 0.50→0.00 on a SMALL synthetic bench (weakest
  evidence so far — Phase 3 rebuilds it properly).

---

## Phase 0 — Rigor harness (enabling; do FIRST, cheap)

Single biggest gap today: single-seed, single-model, no CIs. Fix it once, structurally, so
no future result can regress to that.

- **Build** `benchmark/epistemic_harness.py`: every experiment runs N seeds (default 3),
  optional model sweep, bootstrap 95% CI, saved per-row scores, a standard result schema
  `{metric, value, ci_low, ci_high, n, seeds, model}`. Existing benches refactored to call it.
- **Build** `benchmark/stats.py`: tie-corrected AUROC (done, move here), AURC (risk-coverage),
  bootstrap CI, DeLong test for AUROC differences, ECE/MCE, reliability bins.
- **Metric**: every headline number becomes `value [CI]`, multi-seed mean±std.
- **Falsification of the program itself**: if any prologue result's 3-seed CI drops below
  its single-seed point by >0.05, that result is downgraded and re-investigated.
- **Deliverable**: harness + all R-numbers re-run 3×3 (3 seeds, {haiku,sonnet,opus}). Cost:
  ~moderate (a few thousand `claude -p`). **Novel? No — table-stakes. But non-negotiable.**

---

## Phase 1 — Confabulation: harden the moat to SOTA (lead with our strength)

The write-path gate is the lead asset. Make it unbreakable and general.

- **H1.1**: source⊢fact separation generalizes across confabulation TYPES and models.
- **Datasets**: SNLI (have) · FEVER (real claim-verification) · VitaminC (contrastive
  contradiction) · a NEW graded synthetic suite `benchmark/confab_suite.py` = 5 types ×
  3 severities, each with a faithful control: **entity-swap, numeric-perturbation,
  temporal-drift, over-generalization, plausible-inference** · real LLM-extracted facts
  from passages (the actual Engram use case).
- **Metric**: AUROC + AURC per type + threshold sensitivity + calls/fact. Per-type table.
- **Falsification**: if AUROC < 0.80 on any realistic type → a blind spot; characterize and
  fix before claiming "the moat." (We EXPECT temporal-drift and over-generalization to be
  the hard ones — that's the interesting science.)
- **Develop** (reuse `engram/grounding_gate.py`): (a) **span-attribution** — return the exact
  supporting span or NONE, so every stored fact gets provenance, not just a score; (b)
  per-type calibrated thresholds via `optimal_threshold`; (c) wire L4 into the OTHER write
  paths — `documents`/`transcript` ingestion + episode `key_facts` — not just hippo_remember.
- **Innovation (real)**: **provenance-on-write** — Engram stores, with every "verified"
  fact, the span that grounds it + a grounding score. An auditable memory. Nobody ships this.
- **Deliverable**: hardened gate + per-type report + provenance wiring + critic. Cost: high.

---

## Phase 2 — Hallucination: selective prediction toward zero (build the lever we found)

R8 found MEAN(confidence, external-entailment) = AUROC 0.847 > either alone (0.812), but we
never BUILT the combined gate. Build it and chase the risk-coverage frontier.

- **H2.1**: a calibrated combine of the answer's own confidence + an external entailment
  score yields a better risk-coverage frontier than the strict prompt alone.
- **Datasets**: SQuAD v2 (have) · TruthfulQA · HaluEval-QA · a long-form FActScore-style set.
- **Metric**: risk-coverage curve, **AURC**, fabrication@{90,95,99}%-coverage, over-abstention.
- **Develop**: `selective_answer.py` — answerer emits answer+confidence; external verifier
  scores entailment; calibrated combine → abstain below the operating point chosen for a
  target fabrication rate. Compare to strict-prompt and confidence-only baselines.
- **Falsification**: if the combined gate's AURC is not below strict-prompt's by a
  CI-separated margin (DeLong), the extra call isn't worth it — report and drop it.
- **Innovation (modest)**: a calibrated selective-answering layer with a tunable
  fabrication/coverage knob. (Table-stakes-adjacent; the honesty is the value.)
- **Deliverable**: selective layer + frontier plots + multi-dataset numbers. Cost: medium.

---

## Phase 3 — Sycophancy: real adversarial, multi-turn, memory-grounded (rebuild weakest axis)

Current sycophancy evidence is the thinnest. Make it serious.

- **H3.1**: an evidence-requirement gate makes the agent robust to (a) confident-but-wrong
  user assertions and (b) recency pressure, WITHOUT over-rigidifying (legitimate corrections
  still land).
- **Datasets**: Anthropic SycophancyEval (if reachable) · a NEW `benchmark/sycophancy_mem.py`
  = stored verified fact vs user's confident contradiction, vary evidence strength + repeat
  the pressure over N turns; plus a CONTROL set of legitimate corrections that SHOULD update.
- **Metric**: **cave-rate** (caves to unsupported assertion) AND **false-rigidity** (rejects a
  legitimate, evidenced correction) — the two-sided measure that prevents a fake win.
- **Develop** (reuse `truth_reconciliation.py`): wire "evidence supersedes, bare assertion
  does not" into supersede logic; validate the asymmetry holds both ways.
- **Falsification**: a gate that drives cave-rate to 0 by also spiking false-rigidity is
  REJECTED — robustness must not cost legitimate updates.
- **Innovation (real)**: the measured asymmetry (evidence beats assertion; assertion never
  supersedes on recency/confidence) as a memory invariant.
- **Deliverable**: real multi-turn bench + wired gate + two-sided numbers + critic. Cost: med.

---

## Phase 4 — Memory epistemics: the system axis (the most novel work)

The three above are answer/write-time. MEMORY adds failure modes nothing else has, and this
is where Engram is unique. Five sub-problems, each a real experiment:

1. **Retrieval-grounding (read-time gate)**: when answering FROM memory, verify the RETRIEVED
   facts entail the answer (apply the R10 gate over retrieved evidence, not the generator's
   confidence). Metric: grounded-answer-rate on LoCoMo/LongMemEval. **H**: read-time grounding
   raises QA-accuracy AND cuts answer-fabrication vs the current pipeline.
2. **Epistemic health score**: of facts stored `verified`, what fraction actually pass the
   grounding gate? Audit the live corpus; track the score as the corpus grows. Reuse
   `anti_confab_gate` + `grounding_gate`. **Innovation**: a memory that reports its own
   grounded-fraction.
3. **Temporal validity**: facts go stale; measure stale-fact-injection rate at recall; the
   freshness gate (reuse `freshness.py`/`time_decay.py`). **H**: freshness-weighting cuts
   stale-answer rate without hurting fresh-answer recall.
4. **Consolidation-confabulation**: the dream pipeline SYNTHESIZES masters — does a dreamed
   master entail from its source cluster? Gate `adopt_dream` with grounding. (Verified the
   deterministic `propose_master_node` does NOT need it; the LLM-synthesis path might.)
5. **Contradiction-over-time**: NLI contradiction detection across the corpus (reuse
   `semantic_conflict.py`); measure FP on the real noisy corpus (known ~0.77 → needs hygiene).
- **Benchmarks**: LoCoMo (0.81 → push with read-time grounding), LongMemEval.
- **Innovation (the big one)**: **epistemic memory** — every fact carries {grounded?, fresh?,
  contested?}, and recall refuses to serve ungrounded/stale facts as truth. This is the
  product moat, not just a paper result.
- **Deliverable**: read-time gate + health score + freshness + dream-gate + corpus audit.
  Cost: high (the flagship phase).

---

## Phase 5 — Unification + publication (the science payoff)

- **Unified metric**: an **evidence-grounding-rate** computed identically across all 4 axes;
  show one grounding-discipline knob moves them together (the lockstep test, now nuanced —
  expect SHARED-ROOT not lockstep).
- **Calibration-as-root (multi-model)**: does a model's ECE predict its pathology rate on all
  4 axes, across {haiku, sonnet, opus}? If yes, calibration is the upstream lever (strong,
  publishable). If no, the axes are more independent than the thesis claims — report it.
- **Unified Epistemic Benchmark (UEB)**: one memory-agent task that elicits all four failures,
  scored by the one grounding metric. (Started in `benchmark/unified_epistemic_bench.py`;
  make it real and external-data-backed.)
- **Paper**: `docs/EPISTEMIC_FAILURES_STUDY.md` → an arxiv-grade writeup (abstract, formal
  framework, methods, R-results with CIs, related work, limitations). The honest arc
  (including the self-caught AUROC bug) is itself a methods contribution.
- **Deliverable**: unified metric + multi-model calibration result + UEB + paper. Cost: med.

---

## What is genuinely novel (defensible) vs table-stakes (necessary)

- **Novel / moat**: write-path source⊢fact gate (Ph1) · provenance-on-write (Ph1) ·
  read-time retrieval-grounding (Ph4) · epistemic-health score + epistemic memory (Ph4) ·
  the unified proxy-substitution theory + calibration-root result (Ph5).
- **Table-stakes / necessary**: the rigor harness (Ph0) · standard hallucination benchmarks
  + strict prompt (Ph2) · LoCoMo/LongMemEval QA (Ph4). Needed for credibility, not a moat.

## Execution model (how we avoid "cose a metà")

1. Phases are sequential gates; each ends with: deliverable tested + falsification run +
   `critic-orchestrator` claim_holds + commit + push. No phase declared done otherwise.
2. Every experiment uses the Phase-0 harness → multi-seed, multi-model, CI by construction.
3. Reuse the 15 existing epistemic modules (grounding_gate, semantic_conflict,
   truth_reconciliation, coherence_check, freshness/decay, hallucination_rate,
   validate_claim, anti_confab_gate) — extend, don't reinvent.
4. Parallelism: independent experiments can be fanned out across the orchestration stack
   (background `claude -p` benches, or a multi-agent workflow) — the harness makes results
   mergeable. Cost is real `claude -p` time under O5; we scope per phase, not "billions".
5. Honesty gates: no headline without a CI; no "works" without the falsification run; a
   one-sided win (e.g. cave-rate 0 with spiked rigidity) is reported as a NON-win.

## Suggested order & first concrete step

Ph0 (harness) → Ph1 (confabulation hardening, our strength) → Ph4 (memory epistemics, the
moat) → Ph2 (hallucination selective) → Ph3 (sycophancy) → Ph5 (unify + paper). Memory (Ph4)
is pulled early-ish because it is the product differentiator.

**First step now**: finish the in-flight multi-model (haiku) + multi-seed runs, fold into a
Phase-0 harness, and re-baseline the moat 3-seed × 3-model with CIs. That single result
turns "0.971 on one seed/one model" into a defensible, general claim.
