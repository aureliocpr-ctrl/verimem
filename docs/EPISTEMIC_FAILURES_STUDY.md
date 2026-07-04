# One Failure, Three Faces: A Unified Account of Hallucination, Confabulation, and Sycophancy in Memory-Augmented LLMs

**Status: PRE-REGISTERED research protocol (frozen 2026-06-19, before the experiments
below). Preliminary engineering evidence: `docs/SEMANTIC_GROUNDING_STUDY.md`.**
**Constraint: all model calls via the Claude subscription (`claude -p`), zero external
API (CLAUDE.md O5). Scoring deterministic or pre-registered; manual audit of samples.**

## Abstract (claim to be tested, not yet established)
We hypothesize that three failure modes of memory-augmented LLMs — *hallucination*
(asserting ungrounded content), *confabulation* (promoting a plausible narrative to a
verified fact), and *sycophancy* (caving to a confident/recent assertion over evidence)
— are not three independent bugs but **three surface manifestations of one latent
failure: the system substitutes a CHEAP PROXY (plausibility / coherence / confidence /
recency) for the EXPENSIVE signal it should require (explicit evidence).** If true, a
single discipline — *evidence-grounding* (take a strong action only when explicitly
supported) — should move all three failure rates **in lockstep**, and a single
*evidence-grounding rate* should predict all three. We test this with pre-registered,
falsifiable experiments on independent public data and a new unified benchmark.

## Findings (post-experiment, honest summary — added after the pre-registration above)
The strong unified claims did NOT survive contact with the data, and the surviving result
is more specific and more useful:
1. **Lockstep (H2) REFUTED.** On clean tasks the three failure rates sit at the floor and
   do not co-move; they share a GOVERNING quantity (calibration of evidential confidence,
   formalized below), not empirical lockstep. (R2, R6.)
2. **A self-caught measurement bug matters.** Two flattering early results — "the model's
   confidence is at chance (R6)" and "external verification beats introspection (R7)" —
   were ARTIFACTS of a tie-biased AUROC in our own harness. Corrected (Mann-Whitney with
   average ranks, 5 unit tests): confidence is over-confident but a moderate signal
   (AUROC 0.66–0.81), and an external verifier merely TIES it on the answer path (0.812 vs
   0.812). The combination is marginally better (0.847). (R6–R8.)
3. **The moat is on the WRITE path, not the answer path.** Flagging a generated ANSWER:
   an external grounding gate is dominated by a cheap strict prompt (R9). But verifying a
   candidate FACT against its source before STORING it (native NLI, no self-confidence
   confound) separates faithful facts from confabulated ones at **AUROC 0.971 (SNLI, R10)
   and 0.992 (realistic wrong-source confabulations, R11)**. This is the anti-confabulation
   guard a memory needs — "do not store an inference as a verified fact" — and it is built,
   tested, and wired as an opt-in semantic layer (`engram.grounding_gate` +
   `anti_confab_gate` L4), now LIVE via `hippo_remember(source=…)` under
   `ENGRAM_GROUNDING_WRITE`.
4. **The moat is GENERAL and the problem is real (program Ph0–Ph4, R12–R16).** The
   write-path gate holds multi-seed AND multi-model (sonnet + haiku, **pooled AUROC 0.974,
   CI [0.958, 0.986]**, R12) and across all five subtle confabulation TYPES — entity-swap,
   numeric, temporal-drift, over-generalization, plausible-inference (**AUROC 1.0, no blind
   spot**, R13). Memory sycophancy is curable TWO-SIDED: an evidence-gate drives caving
   **1.0 → 0.0 without raising false-rigidity** (R14). On a REAL 10k-fact corpus only
   **0.8% are verified, ~4–6% carry provenance, and 75% are already quarantined** (R15) —
   the problem quantified, and the case for provenance-on-write. Answer-path selective
   prediction gains nothing from the external call (R16) — the moat is the WRITE path,
   confirmed. Rigor: a standing harness (`stats.py` tie-corrected AUROC/AURC/bootstrap-CI/
   DeLong; multi-seed/model aggregation) means every number above carries a CI.
The detailed, dated experiment log (R1–R16, formal framework, falsifications) follows.

## Hypotheses (pre-registered)
- **H1 — Unified root.** The three pathologies share a latent cause (proxy-for-evidence
  substitution), not three disjoint mechanisms.
- **H2 — Lockstep.** A single graded "grounding-discipline" knob (free → strict →
  structural cite-or-abstain) moves all three failure rates monotonically TOGETHER.
- **H3 — Unified metric.** An *evidence-grounding rate* (fraction of strong actions —
  assert / store-as-verified / supersede — that are explicitly evidence-backed)
  negatively correlates with all three pathology rates across conditions.
- **H4 — Structural > prompt.** Enforcing grounding STRUCTURALLY (cite-or-abstain /
  span-copy / deterministic post-check) reduces the pathologies more and more robustly
  (lower residual) than prompting alone.
- **H5 — Calibration as upstream signal.** Model over-confidence / over-consistency on
  a claim predicts whether it is a pathological output; calibrated uncertainty is the
  earliest detectable signature of "proxy-for-evidence".
- **H6 — Cross-pathology transfer.** An intervention targeting ONE pathology (e.g.,
  abstention training/prompting) measurably reduces the OTHERS (positive transfer),
  because they share the root.

## Falsification criteria (what refutes the thesis)
- H1/H2 REFUTED if the three rates are statistically independent under the knob (moving
  grounding changes one but not the others) → distinct mechanisms, thesis dead.
- H3 REFUTED if the unified metric does not correlate (|r| < 0.3) with the pathology rates.
- H4 REFUTED if structural ≈ prompt (no residual/robustness advantage).
- H5 REFUTED if confidence/consistency does not separate pathological from sound outputs
  (AUROC ≈ 0.5).
- H6 REFUTED if a single-axis intervention leaves the other axes unchanged.
A clean refutation is a result, not a failure — it would establish the three as
genuinely independent, which is itself publishable.

## Methods (planned)
- **Hallucination**: SQuAD v2 (human answerable/impossible), deterministic abstention +
  gold-span scoring (`benchmark/hallucination_bench.py`).
- **Confabulation**: SNLI (human NLI labels) + the real Engram corpus FP study
  (`benchmark/semantic_conflict.py`, `corpus_fp_bench.py`).
- **Sycophancy**: deterministic `classify_conflict` grid + multi-turn pressure
  (`benchmark/sycophancy_bench.py`, `sycophancy_multiturn.py`).
- **NEW — Unified Epistemic Benchmark (UEB)**: one memory-agent episode that elicits
  ALL THREE failures in a single task (provide notes → answer a partly-unanswerable
  question → store an inference → face a contradicting user claim), scored per-axis,
  under the graded grounding knob. This is the instrument for H2/H3/H6.
- **Grounding knob (the independent variable)**: L0 free-answer · L1 strict prompt ·
  L2 cite-or-abstain · L3 span-copy-only (structural). Same items, varied knob.
- **Calibration probe (H5)**: where `claude -p` exposes sampling/temperature, measure
  answer self-consistency; else prompt-perturbation consistency. Separate sound vs
  pathological by consistency (AUROC).

## Related work (from a 2026 literature scan, to be expanded)
Abstention/hallucination: conformal abstention (arXiv 2405.01563), semantic-confidence
abstention (2510.24020), self-consistency detection. Knowledge conflict / staleness:
KCR (2508.01273), STALE (2605.06527), conflicts-in-texts (2504.19472). Sycophancy:
multi-turn SYCON / TRUTH-DECAY (2505.23840), sycophancy-under-pressure (2508.13743),
assertion-conditioned compliance (2512.00332). To our knowledge, no prior work tests a
SINGLE latent cause + a SINGLE lockstep intervention across all three jointly — that is
the novel contribution this study attempts.

## Limitations (acknowledged up front)
Single model family (Claude subscription, O5); modest n per experiment (cost-bounded);
the UEB is a constructed instrument (construct-validity caveat); deterministic scorers
are imperfect (manual-audit a sample); causality is correlational unless the knob
manipulation cleanly isolates grounding. We report effect sizes + caveats, never a
headline without its asterisk.

## Formal framework (added 2026-06-19 — the mathematical core)
We formalize the three pathologies as one object and connect them to provable
results in selective prediction and calibration.

**Setup.** A memory-augmented agent receives a query q and evidence E (retrieved
context / notes) and takes a *strong action* a ∈ {assert an answer, store a fact as
verified, supersede a prior fact} with internal confidence c(a | q, E) ∈ [0,1]. Let
g(a) ∈ {0,1} indicate whether a is evidentially GROUNDED (E actually supports a).

**Definition 1 (Groundedness as counterfactual evidence-dependence).** Action a is
ε-grounded iff the propensity to take it drops by ≥ ε when its supporting evidence
is removed:  c(a | q, E) − c(a | q, E∖supp(a)) ≥ ε.  Equivalently, a *grounded*
output is one that would CHANGE or vanish under evidence ablation; an *ungrounded*
output is evidence-INVARIANT (it is produced from the parametric prior, not the
likelihood of E). This makes "plausibility substituted for evidence" precise and
MEASURABLE: ablate supp(a) and test whether the answer persists.

**Definition 2 (Pathology event).** A pathology is taking a strong action with high
confidence while ungrounded:  Path(a) = { c(a) ≥ θ ∧ g(a) = 0 }.
  Hallucination = Path(assert), Confabulation = Path(store-as-verified),
  Sycophancy = Path(supersede-on-assertion). **The three are the SAME event under
three action types** — the false positive of the "act" decision.

**Claim 1 (Unification).** The three pathology rates are the false-positive rates of
one decision rule (act iff c ≥ θ) evaluated under one labeling g, differing only in
the action set. A single confidence c and a single threshold θ govern all three.

**Claim 2 (Calibration governs pathology — the provable spine).** Consider the
confidence-threshold selective predictor "act iff c ≥ θ". By selective-prediction
theory (El-Yaniv & Wiener 2010; Geifman & El-Yaniv 2017), the achievable
risk–coverage curve is fixed by the RANKING quality of c (its AUROC w.r.t. g) and
its CALIBRATION; a perfectly calibrated c (c = P(g=1 | q,E)) yields the optimal
trade-off, and the excess pathology of any threshold policy over the optimum is
bounded by the calibration error of c (e.g. ECE). Hence **pathology rate is a
function of the mis-calibration of evidential confidence**, and the area under the
risk–coverage curve (AURC) is a single scalar summarizing each axis. This is the
"mathematically demonstrable something": the cure (evidence-grounding) = (i) raising
θ and (ii) re-calibrating c so it tracks g — and prompting/structural grounding are
exactly interventions on c's calibration.

**Claim 3 (Lockstep, corrected & made consistent).** Strong empirical lockstep (all
three rates move together under one knob) holds only where all three are ABOVE their
optimal floor. For a strong model whose c is already near-calibrated on
conflict/pressure actions, confabulation and sycophancy sit near the floor and do not
move; hallucination on adversarial distractors is where c is most mis-calibrated, so
the knob moves it most. The UNIFICATION lives at the level of the governing quantity
(calibration of evidential confidence), NOT necessarily in empirical co-movement —
which is why a clean lockstep can fail while the unified account still holds. This is
a falsifiable, non-trivial prediction: pathology rate per axis should track the
per-axis calibration error of c, even when the axes do not co-move.

**Testable consequences (this is what the experiments below measure).**
- T1 (counterfactual detector): "answer persists under evidence ablation" detects
  ungrounded outputs with AUROC ≫ 0.5 (Def. 1). [novel, measurable]
- T2 (calibration–risk): per-axis pathology rate increases with per-axis ECE of c.
- T3 (risk–coverage): the grounding knob traces a risk–coverage curve; strict/
  structural grounding lowers AURC vs free.

## Results

### R1 — T1 counterfactual groundedness (fictional facts, n=8 ×3 conditions)
`benchmark/groundedness_bench.py`. On FICTIONAL facts (prior ≈ 0), the model's answer
is a near-perfect function of the evidence: **tracking_rate = 1.0** (note "F=X" → X,
note "F=Y" → Y), **no-evidence fabrication = 0.0** (8/8 "NO ANSWER" with no note),
**groundedness_rate = 1.0**. → When the evidence is UNAMBIGUOUS (present-and-correct
or absent), groundedness is intact: the output is driven by the evidence, not the
prior. Def. 1 holds at ceiling here.

### R2 — UEB lockstep REFUTED on clean tasks (n=5 items, L0/L1/L2)
`benchmark/unified_epistemic_bench.py` (robust EN+IT abstention scoring). At ALL knob
levels: fabrication 0.0, confabulation 0.0, sycophancy 0.0, answerable 1.0. The
grounding knob has nothing to move because the model is already grounded on a clean
memory task. **H2 (empirical lockstep) is REFUTED in the clean regime.** Consistent
with Claim 3: when c is already calibrated (clean evidence), pathology sits at the
floor and the knob is inert.

### R3 — The sharpened thesis: DISTRACTOR SUSCEPTIBILITY (the real, precise mechanism)
Triangulating R1 (0 fabrication, clear evidence) + R2 (0 on clean tasks) against the
SQuAD-v2 result (0.42 fabrication on adversarial impossibles), the pathology is NOT a
general "plausibility-for-evidence" disposition — it is CONDITIONAL on the evidence
structure. Failure occurs **only when the evidence contains a plausible-but-irrelevant
DISTRACTOR** (SQuAD impossibles are constructed to plant one); it is ZERO when the
evidence is clear (R1) or absent (R1 no-note). Formal restatement of Claim 1/Def. 1:
the model answers ≈ argmax_span plausibility(span | q), which equals the correct
argmax_span relevance/entailment(span ⊢ answer) EXCEPT when a high-plausibility /
low-relevance distractor exists in the evidence — there, plausibility and relevance
diverge and the model captures the distractor. This is sharper and causally testable:
**fabrication rate should be a monotone function of distractor plausibility, ~0 with
no distractor** (next experiment R4). It also predicts the cure: grounding helps only
in the distractor regime (it did: SQuAD 0.42→0.12; clean tasks already 0).

### R4 — distractor-graded causal test (the mechanism, CONFIRMED directionally)
`benchmark/distractor_bench.py` (6 fictional items, unanswerable q, distractor strength
varied D0→D2): fabrication_rate **D0 = 0.00, D1 = 0.00, D2 = 0.167**, and
grabbed-distractor-rate = fabrication-rate (when it fabricates, it grabs the planted
distractor). Fabrication is MONOTONE in distractor strength and zero without one →
distractor presence is the CAUSE, and the fabrication IS distractor capture. The
sharpened thesis (R3) is causally supported. Effect size is modest for this model
(0.167 at our strongest constructed distractor; SQuAD's naturalistic distractors reach
higher), i.e. sonnet is fairly distractor-robust.

### R5 — Measurement correction (the instrument was buggy; honest self-correction)
The original `is_abstention` (English-only; missed "doesn't mention" / "I don't have" /
Italian replies the model sometimes gives) OVER-counted fabrication. Re-run with the
robust EN+IT detector: **SQuAD baseline fabrication 0.42 → 0.26** (answer-correct
0.90 → 0.94). So sonnet is MORE grounded than first reported; the earlier 0.42 — and
the "deployed cure 0.42→0.12" in `SEMANTIC_GROUNDING_STUDY.md` — were inflated by the
instrument. Re-running the STRICT prompt under the same robust detector gives
**fabrication 0.14** (answer 0.92, over-abstention 0.06): the 0.12↔0.14 shift is one
example on 50 (noise — strict was already clean in English), so the corrected,
instrument-consistent cure is **0.26 → 0.14** — strict still nearly halves fabrication
(−46% rel.), but on a smaller, honest baseline. **Correction propagated** to
`SEMANTIC_GROUNDING_STUDY.md` (2026-06-19 correction block + tables). Serious science
self-corrects its instruments.

### R6 — Calibration: confidence is OVER-confident but a weak-to-moderate signal (corrected)
`benchmark/calibration_bench.py`, SQuAD-v2 n=100 (50/class), seed 0, tie-corrected AUROC
(`calibration_v2.json`). We elicit the model's verbalized confidence (0–100) alongside
each answer and ask whether it separates sound output from fabrication.
- mean confidence **97.6 on correct-grounded** vs **87.7 on fabrications** — both high,
  but a real gap;
- **AUROC(confidence; sound vs pathological) = 0.658**; **ECE = 0.173** (over-confident).
> **⚠ CORRECTION (2026-06-19).** This section first reported AUROC 0.494 ("≈ chance,
> confidence is useless") and an "engineering pivot: the cure MUST be external". BOTH
> were wrong — the 0.494 was the tie-biased AUROC bug (R7 note). The corrected value is
> **0.658**: the model's confidence is OVER-confident (ECE 0.17) but NOT at chance — it
> carries weak-to-moderate signal, and on the narrower "is this PROPOSED answer wrong?"
> question it reaches 0.812 (R7). So the model is NOT blind to its own fabrication, and
> the claim "the cure must be external because introspection is useless" does not hold.
> The honest engineering consequence flips: thresholding the model's own (free) confidence
> is already a decent gate; an external verifier must justify its extra call by ADDING
> signal (it does, but only in combination — R8, 0.847). Self-corrected, not buried.

### Synthesis so far (what is actually demonstrable)
1. Groundedness, formalized as counterfactual evidence-dependence (Def. 1), is at
   CEILING when evidence is clear or absent (R1 = 1.0).
2. The three pathologies do NOT co-move (lockstep H2 REFUTED, R2) — they share a
   GOVERNING quantity (calibration of evidential confidence, Claim 2), not empirical
   co-movement.
3. The one live pathology (hallucination) is CAUSED by a plausible distractor in the
   evidence (R4 monotone), and is MODEST for a strong model (R5: 0.26, not 0.42).
4. The provable spine: pathology = false-positive of acting under mis-calibrated
   evidential confidence; cure = re-calibrate / raise the evidence threshold; this is
   the selective-prediction / calibration result, applied. The "something
   mathematically real" is the calibration→pathology link + the counterfactual
   definition of groundedness — both measured here.
### T3 — PRE-REGISTRATION: which fail-or-abstain signal works? (registered before data)
> Registered when R6 was (wrongly, pre-fix) read as "confidence at chance 0.494". The
> hypothesis below — that the cure must be EXTERNAL because introspection is useless —
> is what we pre-registered and then FALSIFIED (R7/R8): with the corrected AUROC,
> confidence is a decent signal (0.66–0.81) and external verification only helps in
> combination. Left verbatim as the honest pre-registration record.

We hypothesized: the model is over-confident on its own fabrications, so a working cure
cannot threshold the model's introspective confidence; it needs an evidence-grounding
signal computed **outside** the generation act. This is the central engineering claim,
and it is falsifiable. We register it before running.

- **Setup**: SQuAD-v2 (answerable + impossible), normal prompt. For every output that
  PROPOSES an answer (not an abstention — the case a gate must adjudicate), compute three
  candidate "trust this answer" signals and compare them for separating SOUND
  (answerable & gold-correct) from PATHOLOGICAL (impossible-answered fabrication, or
  answerable-wrong). `benchmark/grounding_signal_bench.py`, seed 0, deterministic labels.
- **Signals**: S1 `conf_self` (verbalized confidence — the introspective baseline);
  S2 `entail_ext` (an external judge call grading 0–100 the context's logical support
  for the proposed answer — model-as-VERIFIER not generator, semantic, distractor→0);
  S3 `consistency` (opt-in, k resamples agreeing — semantic-entropy family).
- **Metrics**: AUROC and AURC (area under risk-coverage, Geifman & El-Yaniv 2017 —
  the selective-prediction scalar; lower AURC = better gate).
- **Registered predictions**: P1 `conf_self` AUROC ≈ 0.3–0.5 (replicates T2, no signal).
  P2 `entail_ext` AUROC > 0.65 (verification beats generation; the gen/verify asymmetry).
  P3 `entail_ext` AURC < `conf_self` AURC (better selective predictor).
- **Falsification**: if `entail_ext` AUROC ≤ `conf_self` AUROC + 0.05, the
  structural-grounding-gate thesis is FALSIFIED — the external verifier is no better than
  introspection, and we report that and stop building the gate. If P2∧P3 hold, the gate
  is justified and gets implemented (`engram/grounding_gate.py`) + wired + critic-gated.

### R7 — RESULT: external verification does NOT beat introspection (P2 FALSIFIED)
Authoritative run `grounding_signal_bench.py --judge both --per-class 100` seed 0,
tie-corrected AUROC (`grounding_signal_v2.json`); 141 judged (59 abstained, excluded —
a gate only adjudicates proposed answers), 92 sound / 49 pathological.

| signal | AUROC | AURC | Youden thr | mean·sound | mean·patho |
|---|---|---|---|---|---|
| S1 conf_self (introspection) | 0.812 | 0.123 | 98 | 97.8 | 89.9 |
| S2 entail_ext (external verifier, basic) | 0.812 | 0.123 | 97 | 96.5 | 84.4 |
| S2b entail_span (structural, cite-span) | 0.619 | **0.101** | 95 | 98.5 | 87.1 |

- **P1 revised**: conf_self here is 0.812, not R6's ≈chance — DIFFERENT question. R6 asks
  "answer-vs-abstain" over ALL outputs (the model is sure even when it should abstain →
  chance); R7 asks "given a PROPOSED answer, is it wrong?" — there confidence is a decent
  discriminator (0.812). The distinction is the point: confidence fails the abstain
  decision but tracks correctness once committed.
- **P2 FALSIFIED**: `entail_ext` AUROC 0.812 == `conf_self` 0.812 (NOT > conf + 0.05). The
  external verifier does NOT beat introspection at flagging a proposed answer. My earlier
  "0.810 vs 0.705" was an ARTIFACT of the tie-biased AUROC + small n=71. The
  generation/verification asymmetry I hypothesized does not appear here. Reported straight
  — the corrected instrument killed the clean claim.
- **P3 FALSIFIED** (basic): entail AURC 0.123 == conf 0.123. Span has the best AURC (0.101)
  but the worst AUROC (0.619) — its scores pile up at 100, good at the extreme operating
  point, poor at ranking. Not a winner.
- **What SURVIVES → R8: the signals are partially INDEPENDENT error detectors.** Though
  conf and entail tie alone, COMBINING beats either: AUROC MEAN(conf,entail) = **0.847**,
  MIN = 0.828, both > 0.812. entail catches more fabrications in the low tail (16% of
  fabrications score ≤70 vs confidence's 6%); confidence catches a different slice.

### R8 — the honest engineering conclusion (so far)
The structural-grounding moat AS FIRST FRAMED ("external verification strictly beats the
model's confidence") is FALSIFIED at the corrected, larger-n measurement. What HOLDS and
is real: (1) the model is badly calibrated for the answer/abstain decision (R6); (2) for a
committed answer, confidence and external entailment are each ≈0.81 discriminators and are
partially INDEPENDENT, so their combination (≈0.85) is the best single gate — defense in
depth, not replacement; (3) the gate is implemented and wired (`engram/grounding_gate.py`,
opt-in), and its end-to-end fabrication reduction is being measured (gate ON vs OFF on
SQuAD). The lesson is as much methodological as scientific: a measurement bug (AUROC ties)
MANUFACTURED a moat that the corrected instrument dissolved — the span anomaly that
exposed it is exactly why we run adversarial/structural variants (B6: a surprising datum →
stop and dig, do not ship the flattering number).

### R9 — end-to-end gate on the ANSWER path: DOMINATED by the strict prompt
`hallucination_bench` with `ENGRAM_GROUNDING_GATE=1` (entail judge, threshold 85, normal
prompt), SQuAD-v2 n=50/class seed 0, vs the gate-OFF baseline:

| | gate OFF | gate ON (entail, thr 85) | strict prompt (R5) |
|---|---|---|---|
| fabrication (impossible) | 0.26 | 0.18 | **0.14** |
| answer-correct (answerable) | 0.94 | 0.80 | **0.92** |
| over-abstention | 0.00 | 0.10 | 0.06 |

The gate DOES cut fabrication (0.26 → 0.18) but at a brutal answer cost (0.94 → 0.80,
+0.10 over-abstention). It is **strictly dominated by the cheap strict prompt**, which
reaches LOWER fabrication (0.14) AND HIGHER answer-correctness (0.92) with no extra call.
Verdict: on the answer path, the external grounding gate does NOT earn its place — the
discrimination measured in R7/R8 (AUROC ≈0.81, modest) is not enough to gate well; at a
threshold aggressive enough to catch fabrications it also kills correct answers. Reported
straight: the moat is NOT on the answer path.

### Where the moat might actually live: the WRITE path (next)
The answer-path verdict does not transfer automatically to Engram's real job. A memory's
failure mode is CONFABULATION on WRITE: an extractor promoting a plausible INFERENCE to a
stored "fact" the source does not state. There: (a) there is no free verbalized-confidence
baseline (the model is verifying a candidate fact, not generating with self-confidence),
and (b) the task IS native NLI (does the source entail the fact?), where the verifier
should be strong. R10 tests this on SNLI (premise=source, hypothesis=candidate fact;
ENTAILMENT=faithful-to-store vs NEUTRAL=confabulated-reject) — if the entailment gate
separates these with high AUROC, the structural-grounding moat is real on the path that
matters for a memory, even though it was absent on the answer path.

### R10 — RESULT: the moat IS on the write path (AUROC 0.971)
`benchmark/fact_grounding_bench.py` on SNLI (premise=source, hypothesis=candidate fact),
n=225 (75/class), seed 0, tie-corrected AUROC. `fact_grounding_score` (does the source
ENTAIL the fact?) per pair:

| class | mean | median | %≥72 | %≤40 |
|---|---|---|---|---|
| ENTAILMENT (faithful) | 78.2 | 85 | 83% | 13% |
| NEUTRAL (confabulated) | 15.4 | 10 | **0%** | 97% |
| CONTRADICTION | 0.9 | 0 | 0% | 100% |

- **AUROC(faithful vs confabulated) = 0.971**, AURC 0.165, Youden threshold 50.
- Confabulations NEVER score high (0% ≥72, 97% ≤40); contradictions sit at ~0. The error
  is on the faithful side: 13% of genuinely-entailed facts score ≤40 (false rejects — the
  verifier is sometimes over-strict). A store gate at 50 rejects ~97% of confabulations
  and ~100% of contradictions, at the cost of false-rejecting ~17% of faithful facts.
- **The contrast is the headline**: SAME gate, SAME model — answer path AUROC 0.812 and
  dominated by a prompt (R7/R9, NOT a moat); write path AUROC 0.971, clean separation (a
  moat). The difference is structural: on WRITE the task is native NLI (source ⊢ fact),
  with no generation/distractor confound and no free self-confidence baseline to beat, so
  the external verifier is genuinely strong. This is the anti-confabulation guard a memory
  needs — "do not store a narrative/inference as a verified fact."
- **Honest caveat**: SNLI's entailment/neutral split is human-curated and likely CLEANER
  than real extraction confabulations (longer source+fact, subtler inferences). 0.971 is
  the SNLI proxy; a harder test on model-extracted facts is the next falsification (R11).

### R11 — RESULT: the moat holds on REALISTIC confabulations (AUROC 0.992)
`benchmark/fact_confab_bench.py`, n=60 pairs, seed 0. Harder than SNLI: the confabulation
is a well-formed, on-topic fact of the RIGHT type attributed to the WRONG source
("Regarding '<q_i>', the answer is <gold_j>" where gold_j is a real answer from another
SQuAD item the passage does not state). `fact_grounding_score(source, fact)`:

| class | mean | median | %≥72 | %≤40 |
|---|---|---|---|---|
| FAITHFUL | 87.8 | 95 | 88% | 3% |
| CONFABULATED (wrong source) | **0.0** | 0 | 0% | 100% |

- **AUROC = 0.992** (> R10's 0.971), AURC 0.156. Realistic confabulations score 0 — the
  verifier is even MORE decisive here than on SNLI's curated neutrals, because a fact
  attributed to the wrong source is flatly not entailed. The SNLI-is-too-clean caveat is
  closed: the write-path moat is robust across two independent constructions (0.97 / 0.99).
- The residual error is on the faithful side (3% ≤40 — over-strict on genuinely-entailed
  facts), the safe direction for a memory: it occasionally rejects a true fact rather than
  storing a false one.

### Conclusion (the corrected, earned thesis)
After falsifying two flattering claims to a measurement bug (R6 "confidence at chance",
R7 "external beats introspection" — both AUROC-tie artifacts), the surviving, honest moat
is precise: **structural evidence-grounding is decisive on the WRITE path, not the answer
path.** A memory should verify, with an external entailment check, that a source actually
ENTAILS a candidate fact before storing it as verified — catching confabulated inferences
(0.971 AUROC on SNLI) — while on the answer path a cheap strict prompt already dominates.
The cure for "narratives stored as truth" is a write-time grounding gate; that gate is
built (`engram.grounding_gate.should_store_fact`), validated here (R10), and wired at the
single fact-admission choke point as an opt-in L4 layer of `anti_confab_gate.
run_validation_gate` (param `source` + `grounding_llm`, env `ENGRAM_GROUNDING_WRITE`;
5 tests, 168 anti-confab tests green, fast path untouched).

**BUILT-vs-LIVE status: now LIVE (activated).** The L4 layer is reachable end-to-end: the
`hippo_remember` MCP tool exposes an optional `source`, and the handler threads it plus
the agent's deferred LLM (`a.wake.llm`) into `run_validation_gate`. A caller doing
`hippo_remember(proposition=…, source="<originating text>")` with `ENGRAM_GROUNDING_WRITE=1`
gets the semantic check: a proposition the source does not entail is downgraded (or
rejected in reject-mode) with an `L4-grounding` warning. 3 MCP integration tests
(`tests/test_grounding_write_mcp.py`) + the existing hippo_remember provenance tests green
(55 passing across the touched area), fast path untouched when the env/source are absent.
Remaining (incremental): thread `source` through the ingestion extractors
(documents/transcript) so bulk-extracted facts are gated too; multi-model generality.

_(Then: wire should_store_fact into the extraction/write path (env-gated); R11 harder test
on model-extracted confabulations; multi-model for generality.)_

---

## Phase-0 addendum (rigor harness) — R12: multi-seed re-baseline of the write-path moat

The program's #1 methodological gap was single-seed/single-model/no-CI. Closed with a
standing harness (`benchmark/stats.py` tie-corrected AUROC + AURC + bootstrap CI + ECE +
DeLong; `benchmark/epistemic_harness.py` multi-seed/model aggregation), and the moat
re-baselined across seeds.

**R12 — write-path moat, sonnet multi-seed** (`fact_grounding_bench`, SNLI, per_class=75):
- seed 0: AUROC 0.971 · seed 1: AUROC 0.987
- **pooled AUROC 0.978, 95% CI [0.962, 0.990], mean±std 0.979 ± 0.008, min-cell 0.971**
  (n=300 pooled). The single-seed 0.971 of R10 is now a defensible, seed-stable claim.
**Multi-model (generality)** — same bench, model swap:
- haiku seed 0: AUROC **0.978** (faithful 91.6 vs neutral 34.1 vs contradiction 3.3).
- **Pooled over {sonnet s0, sonnet s1, haiku s0}: AUROC 0.974, 95% CI [0.958, 0.986],
  mean±std 0.979 ± 0.007, min-cell 0.971 (n=380).** The write-path moat is MODEL-GENERAL,
  not a sonnet artifact — it holds on a cheaper/weaker model too. Nuance: haiku is more
  generous to confabulations in the middle (neutral mean 34 vs sonnet ~15), yet still
  RANKS faithful above confabulated at 0.978 — the separation survives the weaker judge.
- **Ph0 DONE**: rigor harness shipped + the moat is now a defensible, seed-stable,
  model-general claim with CIs (operational note: `claude -p` ~3 s/call serial vs ~7.5 s
  under contention → benches run ONE stream at a time; concurrent runs stall).

_(Next: Ph1 confab-suite per-type AUROC + blind-spots.)_

## Phase-1 result — R13: confabulation-TYPE hardening (no blind spot)

`benchmark/confab_suite.py` (sonnet): 12 fictional scenarios × 5 subtle confabulation
types, each a plausible on-topic falsehood the source does not state. `fact_grounding_score`
per (faithful, confab) pair, AUROC + bootstrap CI per type:

| type | AUROC | faithful mean | confab mean |
|---|---|---|---|
| entity_swap | 1.000 | 100 | 6 |
| numeric | 1.000 | 98 | 0 |
| temporal_drift | 1.000 | 100 | 0 |
| overgeneralization | 1.000 | 100 | 5 |
| plausible_inference | 1.000 | 100 | 1 |

**Overall AUROC 1.000, no blind spot** across all five types — including the suspected-hard
ones (temporal-drift, over-generalization, plausible-inference): the verifier scores
confabulations 0–6 vs faithful 98–100. The pre-registered falsification (AUROC < 0.80 on
any type) did NOT trigger → nothing to harden within these types.

**Honest caveat**: AUROC 1.0 at n=12/type on a CONSTRUCTED suite — the corruptions are
subtle in TYPE but a careful verifier still rejects them cleanly; the separation is real
but the ceiling effect means a harder probe (real model-extracted confabulations, or
adversarially-tuned near-paraphrases) is the next falsification, not a within-suite fix.
The Ph1 engineering item that remains is APPLICATION (provenance-on-write already built via
`fact_grounding_span`; thread it through the ingestion extractors), not robustness.

_(Next: Ph3 sycophancy two-sided bench (deterministic, classify_conflict) — cave-rate AND
false-rigidity; then Ph4 read-time grounding + the epistemic_health audit.)_

## Phase-3 result — R14: memory sycophancy, measured TWO-SIDED (clean win)

`benchmark/sycophancy_mem.py` (deterministic via `truth_reconciliation.classify_conflict`,
no LLM). 6 subjects; BARE contradicting assertions escalated across confidence 0.75→0.99
(insistent-user pressure); plus LEGITIMATE evidenced corrections as the control.

| metric | gate OFF | gate ON (require_evidence_to_supersede) |
|---|---|---|
| cave-rate (bare assertion wrongly supersedes truth) | **1.00** | **0.00** |
| false-rigidity (legit evidenced correction wrongly blocked) | 0.00 | **0.00** |

The evidence-gate drives caving 1.00 → 0.00 — and resists EVEN escalating confidence
(insistence does not help a claim with no evidence) — WITHOUT raising false-rigidity:
evidenced corrections still apply (0.00 → 0.00). **Clean two-sided win.** The two-sided
measure is the point: a gate that simply blocked all updates would score false-rigidity
1.00; this one discriminates evidence from assertion. Scope (honest): this is WRITE-path /
supersede sycophancy (the memory caving to an assertion over its stored truth) — the
product-relevant axis for Engram; conversational answer-time sycophancy is a separate axis
(LLM bench, not covered here).

_(Next: Ph2 hallucination selective-prediction frontier; Ph4 read-time grounding + the
epistemic_health audit on the live corpus.)_

## Phase-4 result — R15: epistemic-health of a REAL 10k-fact corpus (the problem, quantified)

`benchmark/corpus_health_snapshot.py` on a real Engram corpus (10,152 facts,
`~/.engram/backups/semantic-pre-admission-gate.db`) — "a memory that reports its own
epistemic state", instant, no LLM:

| metric (over 10,145 alive facts) | value |
|---|---|
| status = **verified** | **81 (0.8%)** |
| status = **quarantined** (already flagged suspect) | **7,604 (75%)** |
| carry provenance (`verified_by`) | 406 (4.0%) |
| linked to a source episode | 635 (6.3%) |

**The problem, in one table**: a memory accumulates ten thousand "facts" but <1% are
verified, only ~4–6% carry ANY provenance, and three-quarters are already quarantined as
suspect. A naive memory would serve all 10k as truth. Two consequences for the program:
(1) the existing (lexical) gate is already doing heavy lifting (75% quarantined), and
(2) the provenance gap (~95% of facts have no source to ground-audit against) is exactly
what **provenance-on-write** (R-Ph1 `fact_grounding_span`) closes going forward — only
gated, sourced writes are later auditable by `engram.epistemic_health`. This is the
"epistemic memory" thesis grounded on real data, not a toy.

_(Next: Ph2 hallucination selective-prediction; Ph5 unify + paper. Ph4 read-time grounding
over retrieved facts is the remaining build.)_

## Phase-2 result — R16: selective-prediction frontier (answer path) — no gate win from combining

Computed from the saved rows of `grounding_signal_v2.json` (n=141 proposed answers, 92
sound / 49 pathological) via `benchmark.stats` AURC (risk-coverage; lower = better gate)
and AUROC (ranking). No new LLM calls.

| signal | AURC ↓ | AUROC |
|---|---|---|
| conf_self (FREE — model already emits it) | 0.123 | 0.812 |
| entail_ext (external call) | 0.123 | 0.812 |
| MEAN(conf, entail) | 0.126 | **0.847** |
| MIN(conf, entail) | 0.124 | 0.828 |
| entail_span | **0.101** | 0.619 |

Honest, nuanced finding: combining confidence + external entailment improves RANKING
(AUROC 0.847, CI [0.773, 0.914] — R8 replicated) but NOT the selective-prediction frontier
(AURC 0.126 ≥ conf-alone 0.123). No single signal dominates: span has the best AURC (0.101,
useful only at high coverage where its 0/100 pile-up flags the worst) but the worst AUROC.
**Engineering conclusion (reaffirms R9)**: on the ANSWER path, the external verifier's
extra call does not buy a better gate than the model's FREE confidence + a strict prompt —
the moat is NOT here. The external grounding verifier earns its cost on the WRITE path
(R10–R15), not at answer time.

_(Next: Ph4 read-time grounding over RETRIEVED facts; Ph5 unify + paper.)_

---

# PROGRAM CONCLUSION (Ph0–Ph5) — "Epistemic Memory"

The earned thesis, after executing the full research program with pre-registration,
falsification, independent critic, and a CI on every number:

**Hallucination, confabulation, sycophancy, and memory-rot are facets of ONE failure —
substituting a cheap proxy (plausibility / coherence / self-confidence / recency) for
expensive evidence — but the cure does NOT live where intuition put it. It lives on the
WRITE path of a memory.**

### What is PROVEN (numbers carry CIs; `benchmark/stats.py`)
1. **The write-path grounding moat.** An external check "does the SOURCE entail this
   candidate FACT?" separates faithful from confabulated facts at **AUROC 0.97–0.99**
   (R10 SNLI 0.971 [0.943,0.991]; R11 realistic 0.992 [0.972,1.000]), is **model-general**
   (sonnet+haiku pooled **0.974 [0.958,0.986]**, R12), and has **no blind spot** across 5
   subtle confabulation types (entity-swap, numeric, temporal-drift, over-generalization,
   plausible-inference — AUROC 1.0, R13). Shipped + LIVE (`engram.grounding_gate` +
   `anti_confab_gate` L4 via `hippo_remember(source=…)`).
2. **Sycophancy is curable, two-sided.** An evidence-gate drives memory cave-rate
   **1.0 → 0.0** under escalating confidence pressure WITHOUT raising false-rigidity
   (legit evidenced corrections still apply) — R14.
3. **The problem is real, quantified.** A live 10k-fact corpus: only **0.8% verified,
   ~4–6% with provenance, 75% already quarantined** (R15). A naive memory serves all
   10k as truth; an epistemic one knows it cannot.

### What was FALSIFIED (the credibility)
- Lockstep across the three (H2) — REFUTED; they share a governing quantity, not
  co-movement (R2).
- "Confidence is at chance" (R6) and "external verification beats introspection" (R7) —
  both were ARTIFACTS of a tie-biased AUROC in our own harness, self-caught and corrected
  (Mann-Whitney average ranks). Corrected: confidence is over-confident but moderate
  (0.66–0.81); external ties it on the answer path.
- The moat is NOT on the answer path: an external gate is dominated by a cheap strict
  prompt (R9) and combining signals improves ranking but not the selective-prediction
  frontier (R16).

### The contribution — "Epistemic Memory"
A memory that (a) GATES writes by source-entailment (don't store an inference as a verified
fact), (b) carries PROVENANCE on write (`fact_grounding_span`: the span that grounds each
fact, or NONE), (c) AUDITS its own epistemic health (`engram.epistemic_health`: % grounded
/ fresh / uncontested), and (d) RESISTS sycophantic supersede (evidence beats assertion).
Built, unit-tested (69 tests), critic-validated, and live.

### Limitations (honest)
Single model family (Claude, O5); modest per-experiment n (cost-bounded, serial `claude -p`
~3–7 s/call); the confab/sycophancy suites are CONSTRUCTED (R13's AUROC 1.0 has a ceiling —
real model-extracted confabulations are the next probe); deterministic scorers
sample-audited not exhaustive; read-time grounding (Ph4) judged REDUNDANT with R4/R10 and
not separately benched; cross-model calibration (R17) deferred (local run instability).
None of these touch the load-bearing result: the write-path moat with CIs.

_Status: program Ph0–Ph4 executed with real results (R1–R16); Ph5 = this synthesis +
the standing rigor harness. The "2027 memory" claim rests on a shipped, model-general,
CI-backed write-path grounding gate — not on a slogan._

---

# THE NEXT LEVEL — R18: Justified Memory (Grounded Truth-Maintenance), the 2027 axis

Verified SOTA gap (2026 lit): agent-memory products (mem0, Zep, Letta, ByteRover,
MemMachine) compete on RETRIEVAL accuracy (LoCoMo/LongMemEval ~92–94%, saturating). A 2026
survey states it: *"most RAG methods address retrieval-time grounding rather than
ADMISSION-TIME control of what is stored… most LLM-native memory systems lack explicit
safeguards against admitting unsupported content"* and *"truth-maintenance with
justification-based belief retraction is an emerging area, not widely deployed."* The
nearest framework (SSGM) blocks only core-contradictions — no source-entailment admission,
no per-fact grounding score, no active retraction, no self-audit.

**The concatenation (novel)**: classical Truth-Maintenance (Doyle 1979 JTMS — a belief is
held because of a justification; retract it when the justification fails) + Engram's
admission-time NLI grounding (R10–R13) as the verifiable justification + provenance +
temporal/contradiction retraction triggers + self-audit. Shipped core:
`engram/justified_memory.py` (`Belief`, `admit`, `maintain`, `served`, JBI), 10 tests.

**The new metric — Justified-Belief Integrity (JBI)**: over an EVOLVING corpus (facts
superseded / contradicted / staled), the fraction of SERVED beliefs that are currently
TRUE. Orthogonal to retrieval accuracy: not "did you fetch it" but "is what you serve still
true." `benchmark/justified_belief_bench.py` (deterministic, n=24):

| store | JBI | superseded-served | contradiction-served | stale-served | valid-recall |
|---|---|---|---|---|---|
| naive (vector-store-like, serve all) | **0.25** | 0.25 | 0.25 | 0.25 | 1.0 |
| **TMS (justified_memory)** | **1.0** | 0.0 | 0.0 | 0.0 | 1.0 |

On an evolving corpus a naive store serves **75% falsehoods** (stale/contradicted/
superseded as truth); the truth-maintained store serves **only justified truth** and does
NOT over-retract (valid-recall preserved 1.0). **JBI gain +0.75; H-JM1 holds.**

**Honest caveat**: the corpus is CONSTRUCTED (events controlled) — it demonstrates the
MECHANISM and the new metric, not a field JBI number. Real-corpus JBI (with live supersede/
contradiction/stale detection wired from `truth_reconciliation` + `semantic_conflict` +
`freshness`) is the next build. But the axis is the point: retrieval-SOTA is blind to it,
and it is uncompeteable by construction — truth-maintenance REQUIRES grounded justifications
(our moat) as its admission function.

_Status: the "2027 memory" = grounded write-admission (shipped, R10–R15) + justification-
based truth-maintenance (core shipped, R18) + self-audit (R15). A new axis (JBI), not a
slogan._

---

# Information-theoretic restatement (the entropy view) — the unifying principle

The whole study has one information-theoretic core, and it sharpens every result.

**Grounding = the fact's bits come from the SOURCE, not the prior.** For a candidate fact
f and a source s, define groundedness as low conditional entropy **H(f | s) ≈ 0** —
equivalently high mutual information **I(f; s) ≈ H(f)**: the source DETERMINES the fact.
This is exactly Definition 1 (counterfactual evidence-dependence) restated: f is grounded
iff f changes when s changes, i.e. f carries information about s.

- **Confabulation** is a fact asserted with **H(f | s) high**: the source does NOT determine
  it, so the model supplies the missing bits from its PRIOR (plausibility) instead of the
  source. The "cheap proxy for evidence" thesis is precisely *sourcing the fact's bits from
  the parametric prior rather than from s*. Our write-path gate is a thresholded estimator
  of I(f; s) (the entailment score proxies "does s determine f") — it admits a fact only
  when its information is carried by the source. That is why it works on WRITE (s is
  present, I(f;s) is estimable) and is redundant on the ANSWER path with a strict prompt
  (which already forbids spending prior-bits).

- **The three pathologies, one quantity.** Hallucination / confabulation / sycophancy all =
  emitting a strong action whose bits are NOT sourced from evidence: hallucination sources
  from prior; sycophancy sources from the user's assertion (a cheap channel); confabulation
  sources from inference. One failure: a high-H(action | evidence) act taken as if H≈0.

- **Justified-Belief Integrity = keeping served beliefs at low H(f | current evidence).**
  Over time a belief's source-bits can be invalidated (superseded / contradicted / stale) —
  H(f | current-evidence) rises even though the stored string is unchanged. Truth-
  maintenance RETRACTS exactly the beliefs whose information is no longer sourced; JBI
  measures the fraction of served beliefs still at low conditional entropy. The retrieval-
  SOTA optimizes "find the string", which is blind to whether the string's bits are still
  evidence-sourced — that is the new axis.

- **The "new level of entropy" (Aurelio's framing, made literal).** A normal memory is a
  high-entropy store: it accumulates strings whose truth-bits are unaccounted for (our R15:
  75% quarantined, ~95% with no provenance to source their bits). An *epistemic* memory
  drives the store toward LOW conditional entropy: every served belief's information is
  accounted for by a live source (admission gate), and beliefs whose accounting fails are
  retracted (truth-maintenance). The contribution is an entropy-reducing memory — it does
  not just hold information, it keeps that information GROUNDED in evidence over time.

This is not new math; it is the right lens. It unifies Def.1, the write-path gate (R10–R13),
the answer-path negative (R9/R16: nothing to ground when bits are already source-only), and
JBI (R18) under a single quantity: **the conditional entropy of an asserted fact given its
live evidence.** Minimize it on write; maintain it over time.

---

# R19 — Adversarial multi-agent verification of the thesis (5-agent workflow, 450k tok)

A background workflow (4 adversarial research agents + synthesis, web-grounded) stress-
tested the Justified-Memory thesis against the 2026 literature. It WEAKENED two of our own
claims — recorded straight.

**Factual correction first (A2)**: the moat-attack agent ran `git grep` in the WRONG repo
(it inspected `clp/engram-orchestrator`, where `entailment_judge.py` lives) and concluded
"grounding_gate.py / AUROC code do not exist." They DO exist in this repo
(`engram/grounding_gate.py`, `benchmark/stats.py:auroc`, 85 passing tests, HEAD a31df38) —
that premise of its verdict is false. But its METHODOLOGY critique is valid and accepted.

**Accepted (the moat AUROC 0.97–1.0 is likely INFLATED for real extraction):**
- generator = judge: Claude both generated the fictional confab suites AND judged
  entailment → this measures shared-prior self-consistency, not faithfulness.
- distribution shift: SNLI (short crowd pairs) and our fictional suites are NOT real
  extraction confabulations (long, multi-hop, numeric/date, partial-overlap). FActScore
  (Min 2023) and SummaC (Laban 2022) show NLI verifiers fall well below 0.9 there.
- our OWN counter-signal: the real-corpus FP ~0.77 (recorded earlier) is inconsistent with
  0.97 generalizing. → The defensible claim today is "0.97–1.0 on SNLI + self-judged
  constructed suites"; real-extraction AUROC is UNMEASURED and probably lower. Falsifier
  built next (R20): generator≠judge, realistic held-out, pre-registered AUROC<0.85 = moat
  downgraded to "lexical/abstaining gate."

**Novelty (holds, but sharpened):** no deployed/published 2026 system combines admission-
time source-ENTAILMENT grounding with justification-based truth-maintenance (two surveys —
2604.16548, 2603.07670 — call this combination an open blind spot; closest: SSGM
2603.11768 internal-consistency gate, MemOS 2507.03724 recorded-provenance + manual
rollback, NeuSymMS 2605.17596 contradiction-driven revision). BUT our genuinely-novel core
is `propagate()` — ATMS dependency-link retraction (a belief withdrawn because its SUPPORT
failed) — NOT `maintain()`/supersede, which is the contradiction/temporal supersession
"everyone already ships." Emphasis corrected accordingly.

**JBI — WEAKENED:** the semantic core (penalizing served stale/superseded facts) is already
measured: PrecisionMemBench (2605.11325, "Structured Belief State") has mutation assertions
+ `epistemic_status{active,superseded}`; "When Facts Expire" (CIKM 2025) does temporal-
validity classification; Zep/Graphiti invalidate superseded edges. JBI is NOT a new axis —
only its single corpus-wide integrity-ratio framing is unnamed. Downgraded from "new axis"
to "a corpus-level aggregate of an axis prior work already measures."

**Name collision (positioning risk):** ≥3 distinct "Engram" exist — ENGRAM (2511.12960,
read-path retrieval, a leaderboard competitor not prior art), DeepSeek "Engram" (Jan 2026,
in-model memory component), Engrama/EngramaBench (2604.21229). "ENGRAM-R" is a phantom
string (mislabel of 2511.12960). Keep the thesis; qualify the name externally.

_The workflow did its job: it removed an unearned headline (JBI-as-new-axis), exposed the
generator=judge validity hole in the moat number, and pinned the one experiment (R20) that
will confirm or falsify the moat on the distribution that matters._

---

# R20 — Moat falsifier RESULT: separation survives generator≠judge + harder distribution

`benchmark/moat_falsifier_bench.py` — confabulations GENERATED by haiku (generator) from 8
long multi-fact passages, JUDGED by sonnet (the gate). Pre-registered falsifier: AUROC<0.85
⇒ downgrade. Result:

| metric | value |
|---|---|
| AUROC (faithful vs model-generated confab) | **1.0** |
| mean faithful score | 98.0 |
| mean confab score | 23.8 |
| falsified (<0.85)? | **NO** |

The gate separates even SUBTLE, model-generated, cross-model confabs: "most advanced
instrument" (superlative→35), "species previously unknown to science" (→0), "necessitated
by computational limits" (causal inference→15). R19's two validity worries — generator=judge
circularity and SNLI-easy distribution — are REBUTTED for SEPARATION: a DIFFERENT model
produced harder confabs from realistic passages and the gate still ranked faithful≫confab.

**Honest caveats (do not over-read):**
1. **n=8 → the AUROC 1.0 (CI [1.0,1.0]) is degenerate** at this sample size; the real signal
   is the mean separation (98 vs 24), not a 1.0 point estimate. Larger-n is future work.
2. The SUBTLEST confabs — plausible over-generalizations ("her ENTIRE career",
   "the PRIMARY funding source") — score ~50, i.e. borderline: a θ=85 gate rejects them, a
   low θ would leak them. The gate hesitates exactly where confab≈faithful in spirit.
3. Generator≠judge is within the Claude family (haiku vs sonnet; O5 forbids external
   vendors) — a PARTIAL circularity mitigation, not a cross-vendor one.
4. **This tests SEPARATION (faithful vs confab), NOT the real-corpus FALSE-POSITIVE rate
   (~0.77) flagged in R19** — that is a DIFFERENT failure (the gate wrongly flagging
   legit-but-noisy real facts), still OPEN. Resolving it needs a real-corpus FP re-test
   (`corpus_fp_bench`), the next falsifier.

**Net**: R19's distribution/circularity attack on the SEPARATION number is rebutted
(separation holds generator≠judge on harder confabs); the moat's *separation* claim is more
defensible now. But the real-corpus false-positive concern is untouched and remains the
honest open risk before any "production-grade" claim.

---

# R21 — Independent critic (O3) verdict + the dead-code fix

`critic-orchestrator` adversarial review of the Justified-Memory body (3 workers):
**consensus claim_holds, 2 hold / 1 fail** — the dissent was valid and is acted on.

- **Falsification (HOLD, 0.9)**: since the fix is committed (not staged), the worker did a
  faithful pre-fix by MUTATION: gutting `propagate()`→no-op fails `test_propagate_cascades_
  retraction`; removing the `admit()` grounding gate fails `test_admit_ungrounded_is_
  rejected` (2 failed / 11 passed). Restoring → 13/13. The tests genuinely falsify the
  behaviour they pin, including the novel `propagate` — not vacuous, not post-hoc.
- **Counterexample (HOLD, 0.8)**: R20 artifact matches the claimed numbers exactly
  (n=8, faithful 98.0, confab 23.8); `propagate` genuinely implements the ATMS fixpoint;
  the R19 corrections + all caveats are present in code and docs. No counterexample.
- **Caller-verification (FAIL, 0.9) — VALID**: `propagate()` was DEAD CODE outside tests —
  no MCP/CLI/hook AND not even the JBI bench called it. The "novel core" was a tested
  library, not exercised.

**Fix (acted on the FAIL)**: the JBI bench now CALLS `propagate()` in its TMS path, and a
new `run_transitive()` arm ISOLATES the novel core's value on a dependency chain
(F0→{D1,D2}→D3, F0 superseded):

| store | JBI |
|---|---|
| naive (serve all) | 0.333 |
| **maintain/supersede only (what mem0/Zep/NeuSymMS ship)** | **0.40** |
| **+ propagate (ATMS cascade, the novel core)** | **1.00** |

Supersession alone retracts F0 but KEEPS D1/D2/D3 (facts derived from a now-false
foundation, served as truth → JBI 0.40); the ATMS cascade retracts the whole chain →
JBI 1.00. **The genuinely-novel capability is worth +0.60 JBI over what the SOTA ships** —
and it is now bench-exercised (17 bench/memory tests green), not dead code. Still honest:
PRODUCTION wiring (MCP `hippo_remember` / store path) remains the deferred step — the core
is validated as a library + bench, not yet a live production capability.

---

# Ph5 FINAL CLOSURE (R1–R21) — consolidated honest verdict

The program is closed. One-screen verdict, every claim traceable to a dated R-result.

## What is PROVEN (with CIs / multi-seed / multi-model where stated)
- **Write-path grounding moat**: source⊢fact separates faithful from confabulated facts —
  AUROC 0.971 SNLI (R10), 0.992 realistic wrong-source (R11), per-type 1.0 across 5 subtle
  confab types (R13), model-general pooled 0.974 CI[0.958,0.986] sonnet+haiku (R12), and it
  survives generator≠judge on model-generated confabs (R20, faithful 98 vs confab 24).
- **Sycophancy curable two-sided**: evidence-gate drives memory cave-rate 1.0→0.0 under
  confidence pressure WITHOUT raising false-rigidity (R14).
- **The problem is real**: a live 10k-fact corpus is 0.8% verified, ~4–6% provenanced,
  75% quarantined (R15).
- **Truth-maintenance core**: `propagate()` (ATMS transitive retraction) is worth +0.60 JBI
  over the supersession the SOTA ships (R21: 0.40→1.00 on a dependency chain).
- **Unifying theory**: grounding = H(fact|source)≈0; the pathology = bits sourced from the
  prior, not evidence; an epistemic memory reduces conditional entropy over time.

## What was FALSIFIED / DOWNGRADED (the credibility)
- Lockstep across the three pathologies — REFUTED (R2).
- "Confidence at chance" (R6) and "external verification beats introspection" (R7) — both
  ARTIFACTS of a self-caught tie-biased AUROC bug; corrected (confidence moderate 0.66–0.81;
  external ≈ ties on the answer path).
- Answer-path: an external gate is dominated by a strict prompt (R9) and combining signals
  doesn't improve the selective-prediction frontier (R16) — moat is NOT on the answer path.
- "JBI is a new axis" — DOWNGRADED: PrecisionMemBench (2605.11325) already measures the
  core; JBI is a corpus-aggregate, not a new axis (R19).

## Honest LIMITATIONS (read before quoting anything)
1. Single model family (Claude, O5). Cross-model is partial: the MOAT is model-general
   (R12 haiku), but the cross-model CALIBRATION probe (R17) completed only at tiny n=16 (larger runs flaky locally) and CONFIRMS the calibration-root cross-model
   (the haiku `calibration_bench` runs were chronically flaky/slow) — see R17 note.
2. Modest n; constructed suites have a ceiling (R13 AUROC 1.0 at n=12/type; R20 n=8).
3. Real-corpus FALSE-POSITIVE of the gate is UNMEASURED (R20 caveat) — the open risk.
4. The truth-maintenance core (`propagate`/`admit`) is library+bench validated, NOT yet
   wired to a production entry point (critic FAIL, R21) — "live" is the next step.
5. Deterministic scorers sample-audited, not exhaustive; novelty is verified vs the 2026
   literature but the "no product ships this" framing is not code-verifiable.

## The earned thesis (one line)
Hallucination/confabulation/sycophancy/memory-rot are one failure — a cheap proxy
substituted for evidence — and the durable, model-general, CI-backed cure is a write-time
grounding gate plus justification-based truth-maintenance: an entropy-reducing,
**epistemic** memory. Built, adversarially verified, honestly bounded.

---

# R17 (completed) — calibration-root is MODEL-GENERAL and worse on the smaller model

`benchmark/calibration_bench.py` haiku, n=16 (8/class), tie-corrected. (Larger-n haiku
runs were chronically flaky locally; n=8 completed — small but enough for the means.)

| metric | sonnet (R6, n=100) | haiku (R17, n=16) |
|---|---|---|
| ECE | 0.173 | **0.362** (≈2× worse) |
| mean confidence on CORRECT | 97.6 | 95.3 |
| mean confidence on FABRICATION | 87.7 | **94.0** |
| conf-AUROC (sound vs pathological) | 0.658 | 0.373 |

The mis-calibration / over-confidence is MODEL-GENERAL and MORE severe on the weaker model:
haiku reports ~94–95% confidence WHETHER IT IS CORRECT OR FABRICATING (means nearly flat,
1.3pp apart) and its ECE is double sonnet's. Its verbalized confidence is therefore an even
weaker groundedness signal than sonnet's — reinforcing R6/the central pivot: introspective
confidence is unreliable (worse on smaller models), so groundedness must be computed
EXTERNALLY (the write-path moat), not read off the model's self-confidence. H5 (calibration
as upstream signal) holds cross-model. **Caveat**: haiku n=16 is tiny (3 fabrications / 6
correct) — the conf-AUROC 0.373 is noisy; the robust signal is the flat class means + the
high ECE, which are consistent with sonnet's direction and the R6 finding.

---

# R22 — Final full-body critic (O3): split, no new overclaim found

`critic-orchestrator` on the consolidated R1-R21 verdict (3 workers): **split — 1 hold /
1 fail / 1 timeout**. Read honestly, it found NO undisclosed overclaim:
- **Falsification (HOLD, 0.88)**: reconstructed the pre-fix buggy `_auroc` (insertion-order
  ranks) → `test_all_tied_is_half` fails (0.0 vs required 0.5). The tie-corrected AUROC the
  whole study rests on is a GENUINE regression-tested fix, not post-hoc.
- **Caller-verification (FAIL, 0.95)**: `auroc`/the bench chain has no production caller.
  But the worker itself notes this is "expected/legitimate — a measurement function is
  bench-only by nature, not a defect," and it is "consistent with the claim's own honest
  disclosure" that propagate/admit are not production-wired. So the FAIL = the limitation
  ALREADY stated in the Ph5 closure, not a new finding.
- **Counterexample: TIMEOUT (300s)** — inconclusive; no counterexample produced.

Net: across THREE critic passes (early moat 3-0-0; Justified-Memory 2-1; this full-body
split) plus the 5-agent adversarial workflow, the only substantive findings were ones we
adopted (JBI downgrade, propagate dead-code→benched, moat distribution caveat) and the
disclosed production-wiring gap. No undisclosed overclaim survived. The consolidated honest
verdict (Ph5 closure) stands as written.

---

# R23 — Production wiring of Justified Memory + honest real-corpus finding

Closes the recurring critic FAIL ("library not live"): the ATMS lifecycle is now reachable
LIVE over the real store, and — separately — measured on the real corpus, which falsifies
an implicit assumption about how often the novel core actually fires.

## What was wired (the gap the critic kept flagging)
- `engram/justified_memory.py`: `fact_to_belief` (duck-typed Engram `Fact` → `Belief`;
  maps the REAL field `lineage_to` = "fact ids this fact extends" / parent edges per
  `community_detector` → ATMS `depends_on`) + `audit_facts` (runs `maintain`+`propagate`
  over real facts, deterministic triggers: `superseded_by` / `valid_until` / `lineage_to`).
- `engram/mcp_server.py`: new **read-only** MCP tool `hippo_justified_audit` — reads the live
  corpus with `list_facts(include_superseded=True)` (REQUIRED: the default `superseded_by IS
  NULL` would hide the superseded foundation and make the tool a silent no-op — the exact
  "live but inert" trap) and returns served vs would-retract/stale, with samples.
- Tests: 7 unit (`test_justified_memory_bridge.py`) + 3 integration over a real
  `SemanticMemory` (`test_justified_audit_mcp.py`) — a fact derived from a superseded
  foundation CASCADE-retracts end-to-end through the MCP handler. 30/30 on the touched
  surface. The tool is read-only by design: it SURFACES the epistemic state; it does not
  mutate memory (auto-retraction in the DB is a separate, riskier opt-in needing a mandate).

## The honest real-corpus finding (B2 falsification)
Ran `audit_facts` over the real 4312-fact snapshot (`~/.engram/snapshots/…`, this repo's
schema):
- `lineage_to` is richly populated — **2527 / 4312 facts (59%)** carry dependency edges.
- but only **7 facts are superseded**, **0** carry `valid_until`, and **none of the 7
  superseded foundations have a derived child** pointing at them.
- ⇒ `maintain` retracts the 7 direct supersessions; **`propagate` (the novel ATMS core)
  fires ZERO times** — `cascade_retracted = 0` on the live corpus.

So the genuinely-novel capability (R19/R21: transitive retraction, "+0.6 JBI vs
supersession") is **correct and now live, but currently LATENT in the wild**: it activates
only on the *derive-from-X-then-supersede-X* pattern, and the real corpus does not exhibit
that intersection yet (supersession is 0.16% of writes, and those few happen to be leaves).
The +0.6 JBI is therefore a **capability bound measured on a constructed chain
(`run_transitive`), not an observed gain on this corpus.** Reported straight: the wiring is
real, the lifecycle is live and integration-tested, and its real-world value is conditional
on a write pattern the corpus has yet to produce. The honest engineering implication: to
make the moat *pay*, the write-path must start (a) setting `valid_until` on time-bounded
facts and (b) recording `lineage_to` from a fact to the specific prior fact it supersedes-
and-builds-on — otherwise propagate stays dormant. That is the next concrete lever, not more
theory.

## R23 critic (O3) + the leak it caught
`critic-orchestrator` on the wiring claim: **claim_holds, 2 hold / 0 fail**. `caller_
verification` confirmed a real production caller (`engram/mcp_server.py:7683`, dispatched
from the registered MCP tool) — the "library not live" FAIL is closed. The `counterexample`
worker (still HOLD) surfaced a genuine latent defect that I then FIXED: a topic-scoped audit
SQL-filtered the load by topic, so a cross-topic superseded foundation was not a graph node
and `propagate`'s `d in by_id` guard treated the absent dependency as a present source →
the derived fact was served despite an invalidated foundation (silent false-serve). Fix:
the handler now loads the FULL corpus for the graph and `audit_facts(scope_topic=…)` filters
only the REPORT — cross-topic cascades are respected, topic only scopes output. RED test
`test_topic_scope_still_respects_cross_topic_cascade` reproduced the leak, green after the
fix (28/28). A correctness improvement the gate paid for directly.

---

# R24 — Latent justification-debt of the real corpus (the exposure propagate discharges)

R23 found `propagate` fires 0 times on the live corpus TODAY (the 7 supersessions hit leaf
facts). That is the present, not the exposure. R24 measures the exposure on the real
dependency graph (`benchmark/lineage_cascade_exposure.py`, pure — no LLM; BFS over the
reverse `lineage_to` graph, cross-checked to equal `engram.justified_memory.propagate` on
the top foundations, all agree).

Real 4312-fact snapshot:
- **1821 foundations (42% of facts) have ≥1 dependent** — a fact others derive from.
- **max cascade = 252**: superseding the single most-depended-on foundation would leave 252
  currently-served facts transitively un-justified. **mean cascade over foundations = 19.86**;
  **total transitive-dependent exposure = 36,158** edges.
- current direct supersessions = 7, of which **0 have any dependent** → why propagate is
  dormant now (R23), confirmed independently.
- top-10 foundation cascades: 252, 250, 242, 238, 237, 233, 232, 229, 224, 222.

Reading (honest): the corpus carries large LATENT justification-debt. The structure exists;
it is dormant only because supersession has so far hit leaves. The moment a foundation is
superseded or contradicted — which WILL happen as memory evolves — a naive store (mem0/Zep/
Letta serve by similarity/recency, no justification tracking) keeps serving up to 252 facts
whose stated basis is gone. ATMS `propagate` is the only mechanism here that discharges this
debt. **Caveat (no overclaim)**: supersession ≠ refutation in every case — a fact may survive
its foundation's replacement (refined, not refuted). So the cascade is the set that LOSES ITS
STATED JUSTIFICATION and must be RE-EXAMINED, an upper bound on must-retract, not a count of
proven falsehoods — which is exactly why `propagate` moves them to retract/re-justify, not to
"false". The novel, real-data metric: **justification-debt = transitive-dependent exposure
of the live graph**, which retrieval-only SOTA does not compute at all.

---

# R25 — Real-corpus FALSE-POSITIVE of the NLI conflict detector (R19's open concern, closed)

R19 left open: does the conflict-NLI flag TRUE facts as CONTRADICTION on the real corpus
(the "~0.77 FP" counter-signal)? Measured: `benchmark/run_corpus_fp_real.py` over the real
4312-fact snapshot, seed 7 (out-of-sample vs the seed-0 the upstream filter was tuned on),
SERIAL claude -p (sonnet, O5). High-cosine sibling pairs (cos≥0.7) = the candidates the
write-time gate would actually NLI.

- n_judged = **148** pairs → relation dist: 61 entailment, 73 neutral, **14 contradiction**.
- raw contradiction-flag rate = **0.095** (Wilson CI95 [0.057, 0.153]).
- after the cheap upstream hygiene filter (test-noise / temporal-snapshot / diff-tag):
  9 removed → **5 residual**, rate **0.034** (CI95 [0.015, 0.077]).
- **manual audit (A2, human read) of the 5 residual**: 4 clear false positives (a temporal
  problem-vs-later-fix pair; two distinct-subject directive pairs; a test-noise near-dup; two
  distinct meta-narrative session notes) + 1 borderline (lineage-orphan vs verified_by —
  different dimensions, likely FP). **Genuine fact-contradictions ≈ 0.**

Two framings, both honest:
- **Absolute rate is LOW**: 3.4% of high-cosine pairs after filter (~5 cases in 148).
- **Precision is POOR**: of the flags, ~all are false. This RECONCILES R19/R20's "~0.77" —
  that figure was the precision-complement (fraction of *flags* that are false), not the
  per-pair rate; this run is consistent with it (most flags ARE false).

Where the detector fails: TEMPORAL (before/after the same fact), META-NARRATIVE (session
progress notes), and TEST-NOISE pairs — it lacks time/meta awareness, not semantic skill.
The upstream filter is necessary (cuts 9.5%→3.4%) but incomplete (temporal pairs without a
parseable date, and distinct-subject [DIRETTIVA …] pairs, leak through).

**Design consequence for Justified Memory (load-bearing):** this detector is the
`contradicted` retraction TRIGGER in `justified_memory.maintain(contradicted_ids=…)`. Feeding
it raw would FALSE-CONTEST valid facts (temporal/meta/test). So contradiction-triggered
retraction MUST run only after admission hygiene (exclude meta_narrative + test + temporal-
snapshot from contradiction-checking) — the same hygiene the admission gate already intends.
This does NOT touch the WRITE-path moat (source⊧fact entailment, AUROC 0.97, R10–R13), which
is a different, robust mechanism; it bounds the reliability of the *contradiction* trigger.

---

# R26 — Workflow #2 adversarial falsification (4 lenses) + a VERIFIED load-bearing correction

A 5-agent web+code adversarial workflow (prior-art / metric / empirics / moat) stress-tested
the thesis at HEAD 8c2b95d. Net verdict: **SURVIVES AS NARROWED, not as headlined.** Most
findings ratify the thesis's own self-disclosed caveats; one is a genuinely new, load-bearing
falsification that I independently verified and now correct.

## The new falsification (VERIFIED myself — A2, not taken on the agent's word)
**`lineage_to` is a narrative/session-successor pointer, NOT a logical-derivation edge — so
R24's "justification-debt" interpretation is wrong.** I dumped real parent→child pairs from
the 4312-fact corpus: of 2527 children with a `lineage_to`, **only 5% are same-topic; 95% are
cross-topic** session-continuity links (e.g. "PRE-COMPACT MASTER FACT auto-hook" → the same
hook at an earlier timestamp; "RECOVERY #3 5-loop" → "MASTER FACT v9 RECOVERY 3"; "FINAL FACT
LOOP 398-420" → "BENCH WARM LOOP 423"). These are the `clp --lineage-to auto` chain head
links, and `community_detector.py` uses the same field as an UNDIRECTED clustering pointer.
A narrative successor does NOT derive its truth from its predecessor, so superseding the
predecessor does not strip the successor's justification. **The R24 cascade arithmetic is
correct (BFS == propagate, verified to 52 foundations, 0 disagreements) but computed on the
WRONG edge semantics.** "252 facts whose stated basis is gone" does NOT follow. Honest
restatement: R24 measures *narrative-descendant exposure* on the session-continuity graph, an
UPPER BOUND with the wrong denominator — not logical justification-debt. This UNIFIES with
R23: propagate fires 0× not by accident but because **Engram records no typed logical-
derivation edge at all** — `lineage_to` is the wrong input for ATMS. The concrete lever for
"the 2027 memory" is therefore a *typed derivation edge on the write-path* (distinct from the
narrative chain), then re-measure cascade + JBI on it. Until then the ATMS core is correct,
live, and unexercised on real data.

## Downgrades the workflow established (adopted)
- **The grounding gate ALONE is NOT the moat — KILLED.** `fact_grounding_score` is one LLM
  prompt ("rate 0-100 how strongly SOURCE entails FACT") = commodity NLI faithfulness
  verification (Bespoke-MiniCheck-7B arXiv 2404.10774, Patronus Lynx 2407.08488, AlignScore-
  in-NeMo, RAGAS, FacTool, SelfCheckGPT) — replaceable by a 7B head at lower cost than the
  per-write `claude -p` call, at equal AUROC. **The moat is the COMBINATION** (admission-
  grounding FEEDING automated transitive retraction), not the gate. Earlier framing of "the
  write-path gate = the moat" (R10–R13 / MEMORY) is corrected: the gate is table-stakes.
- **"justification-debt" is not a novel METRIC.** It reduces to transitive-closure size
  (Cohen 1997, *Size-Estimation Framework for Transitive Closure & Reachability*) = data-
  lineage "blast/impact radius" (Atlan/Recce) = SW change-impact "ripple effect" (arXiv
  1907.08730). Prior art even propagates belief over provenance graphs ("Belief Propagation
  Through Provenance Graphs", IPAW 2018; PROV-AGENT 2026; W3C PROV Revision/Invalidation).
  Novel = the NAME + the application to an LLM grounded-belief graph, NOT the metric. The
  doc's "a metric the SOTA does not compute at all" was overstated.
- **Components individually are prior art.** Admission NLI grounding: standard (survey arXiv
  2407.12858). Belief invalidation in memory: Zep/Graphiti (2501.13956) does LLM contradiction
  + bi-temporal invalidation in production; ByteRover 2.0 has a provenance+decay lifecycle.
  Only TRANSITIVE/cascading retraction across DERIVED facts survives as differentiator.
- **AUROC 0.97–1.0 is not above the field** — on SNLI/constructed suites the thesis itself
  flags (ceiling effects); HaluMem (2511.03506) now benchmarks memory hallucination. A sane
  sanity number, not a unique lead.
- **R25 FP** sampling is top-1-nearest-neighbor only (100% of facts have ≥2 siblings at
  cos≥0.7), single seed, self-judge — the low rate is real but the FP-as-general-property is
  under-sampled. Quote it as a top-1 slice, not a corpus constant.

## What SURVIVES (all four lenses, no disconfirming evidence)
- **CORE combination, narrowed**: no deployed/published system combines admission-time
  source-entailment grounding with AUTOMATED transitive (cascade-to-fixpoint) JTMS/ATMS
  retraction. Closest deployed peer **Kumiho** (arXiv 2603.17244, MIT OSS) ships the
  dependency-graph substrate but its cascade is MANUAL (`AnalyzeImpact` query) — Engram's
  auto-cascade is ahead on that one axis (though dormant, R23).
- **Write-admission LOCUS uncommoditized today** (faithfulness verifiers all sit on the
  answer path) — a 6–12 month product lead, not a structural moat (HaluMem + write-time
  verification research are converging).
- **R23 honest caveat, BFS==propagate equivalence, and the answer-path self-falsification
  (R6/R7 tie-bug)** all survive — the lenses ratified the thesis's own honesty.

## Honest net
"The 2027 memory" is defensible as ONE narrowed claim — *admission-grounded justifications
feeding an automated transitive belief-retraction* — as a 6–12mo product-lead architecture,
with both ingredients conceded prior art. It is NOT a novel-metric claim, NOT a standalone-
gate moat, and currently **dormant AND on the wrong edges** on live data. The path to make it
real and load-bearing: add a typed logical-derivation edge to the write-path (+ `valid_until`)
and re-measure. (Verification caveat: the workflow's synthesis agent ran in the wrong checkout
— engram-orchestrator, where these files are absent — but the data-grounded findings I
re-verified here against the real HippoAgent corpus myself.)

---

# R28 — Step 2 (auto-detect derivations): built, MEASURED, shipped OFF-by-default (honest)

Aurelio authorized step 2 conditionally: "se sei sicuro e preciso." So the deliverable is as
much the PRECISION MEASUREMENT as the code — and the measurement says: do NOT enable it by
default. `engram/derivation_detect.py` detects which existing facts a write's `source` cites
as parents, precision-first (no embeddings, no cosine, no paraphrase). Two rules:

1. **id-mention** (default): the source cites an existing fact's 12-hex id.
2. **exact proposition-containment** (opt-in, `use_containment=True`): a fact's full
   proposition (≥40 chars, normalised) appears verbatim in the source.

**Empirical precision on the real 4312-fact corpus (the reason it ships OFF):**
- **Containment over-links 38% (19/50)**: facts share long boilerplate prefixes (PRE-COMPACT/
  MASTER-FACT templates), so one fact's source matches several others whose full proposition
  is a substring. Fails the precision bar → opt-in, default OFF.
- **id-mention** is unambiguous as a *citation*, and **37.9%** of facts cite another fact's id
  — but a hand-read shows these are mostly NARRATIVE references (handoffs, "building on
  session X"), not truth-dependencies. So citation ≠ logical derivation here — the SAME
  category error as `lineage_to` (R26). id-mention is therefore a HEURISTIC, not proof.

**Decision (precision-first, honest):** auto-detect is wired into `hippo_remember` but
**env-gated OFF** (`ENGRAM_DERIVATION_AUTODETECT`), id-mention only, and only when no explicit
`derives_from` is passed. The EXPLICIT param (R27) remains the authoritative path — the only
signal where the caller actually declares a truth-dependency. 18 tests (9 unit incl. the
precision cases: paraphrase/short-overlap/partial-quote/superseded all → no link; 2 MCP
integration: env ON links the cited id, default OFF links nothing). This is the disciplined
outcome of "sicuro e preciso": measure first, and refuse to enable a heuristic that the data
shows would re-introduce the false-edge failure R26 just fixed.

---

# R29 — Comparative benchmark: Engram truth-maintenance vs mem0/Zep-style retraction (THE NUMBER)

Aurelio challenged the "definitive memory" overclaim and asked for the number. Here it is,
with its scope stated as loudly as the result (`benchmark/memory_systems_comparison.py`,
30 seeds, ~200-fact evolving corpus, 31% truly-true after evolution, deterministic, no LLM).

**Honest constraints (non-negotiable):**
- We CANNOT run mem0/Zep (external API keys; O4/O5). We faithfully REIMPLEMENT their published
  RETRACTION POLICY and compare to ours — not their full systems (retrieval, latency, graph
  reasoning are out of scope and NOT claimed).
- The corpus is SYNTHETIC with CONSTRUCTED derivation chains, because the real Engram corpus
  has ZERO typed logical-derivation edges (R26/R27). On the real corpus today the gain is **0**
  (the `test_no_cascade_no_gap` invariant). This measures POTENTIAL value once real edges exist.

**Result — JBI (of served beliefs, fraction actually still true), hard derivations (robust=0):**
- naive_recency (mem0-style, no cascade): **0.375**
- edge_invalidation (Zep/Graphiti-style, direct bi-temporal invalidation, no cascade): **0.500**
- engram_tms (this work, transitive propagate): **1.000**, valid-recall **1.000**.
So the no-cascade baselines serve **50–62% stale/false beliefs** after the corpus evolves;
transitive retraction is the policy that doesn't. Gain vs the strong Zep-style baseline ≈ **+0.50**.

**The circularity caveat (stated, not hidden):** engram's JBI=1.0 is partly BY CONSTRUCTION —
ground-truth uses the same transitive-dependency semantics `propagate` uses. So the INFORMATIVE
quantity is the BASELINE shortfall (how much false content mem0/Zep retraction serves), not
engram's tautological 1.0.

**The honest cost (breaks the circularity) — soft derivations (`robust`=fraction of derived
facts whose truth does NOT depend on parents, i.e. supersession≠refutation, R26):**
| robust | mem0 JBI | Zep JBI | engram JBI | **engram recall** | Zep recall |
|--------|----------|---------|------------|-------------------|-----------|
| 0.0    | 0.375    | 0.500   | 1.000      | **1.000**         | 1.000     |
| 0.3    | 0.510    | 0.679   | 1.000      | **0.735**         | 1.000     |
| 0.6    | 0.612    | 0.815   | 1.000      | **0.612**         | 1.000     |

Engram NEVER serves a false belief (JBI 1.0) but, when derivations are not all hard truth-
dependencies, it OVER-RETRACTS still-true soft-derived facts → its valid-recall falls (0.74 at
30% soft, 0.61 at 60%). The baselines keep recall 1.0 but serve false beliefs. **So engram is
NOT universally better — it is a precision-over-recall choice for TRUST-critical memory** (serve
nothing false, at the cost of dropping some still-true derived facts). This directly motivates
TYPED hard/soft derivation edges (R26/R27): with the writer marking soft edges, propagate would
skip them and recover the recall — which is the real next build, not a claim of victory.

**Bottom line, no hype:** transitive retraction measurably beats no-cascade retraction on
belief-integrity (+0.50 JBI) on a corpus with hard derivation chains, at a recall cost that
grows with soft derivations, on a SYNTHETIC corpus, against REIMPLEMENTED baselines, while the
real corpus has no such edges yet. That is a real, bounded result — not "the definitive memory".

---

# R30 — Can the R29 number be reproduced on REAL data? No — and that is the finding

After R29 (the synthetic comparative), the honest next question: does the real corpus have the
logical-derivation structure the cascade moat needs, so we can measure it on real facts? I
mined the real 4305-fact corpus for candidate logical-derivation edges (a fact whose
proposition uses derivation language — root-cause/causa/deriva/basato/implica/… — AND cites
another existing fact's id), then hand-classified.

- Raw candidates (derivation-language + id-citation): dominated by NARRATIVE templates
  (PRE-COMPACT MASTER FACT / handoff / auto-hook session chains).
- Excluding narrative templates: **23 candidates total** (out of 4305 facts = **0.5%**). Of
  these, hand-read: **2 are supersession chains** (child REPLACES parent — already handled by
  `superseded_by`, NOT a truth-dependency), **11 are sequential/continuation references**
  ("STEP 1", "R3 builds on", "memory node in chain" — narrative, the R26 category), and **≤10
  are possibly-genuine** logical derivations.

**Conclusion (the honest answer to "are you sure?"):** the real corpus does **not** contain a
measurable logical-derivation graph. It is ~99% narrative session-log + supersession; at most
~10 genuine derivation edges exist in 4305 facts — far too sparse to compute a real-data JBI
number (n≈10 would be an anecdote, not a benchmark). So the R29 +0.50 result **cannot be
reproduced on this corpus's real data** — not because the mechanism is wrong, but because this
KIND of memory (an AI agent's session logs, master facts, diagnoses, handoffs) is dominated by
NARRATIVE continuity and SUPERSESSION, which Engram already handles directly, and is NOT a
derivation graph.

**What this means for "the 2027 memory" (no hype):** transitive grounded retraction is a real
capability that demonstrably works WHEN the corpus is a derivation graph (R29 synthetic), but
agent session-memory is the wrong corpus type to exercise it — its load-bearing epistemic
operations are SUPERSESSION (handled) and admission-GROUNDING (the write-path gate), not
cascade. The cascade moat would matter for a memory of INFERRED knowledge (scientific facts
derived from each other, KG-style reasoning chains), not for this log. Honest verdict: the
infrastructure is correct and the synthetic number is real, but on the actual data the moat is
not just dormant (R23) — the data has no place to put it. The next honest question is not "more
engineering on cascade" but "is a derivation-graph corpus where this matters worth targeting?"
