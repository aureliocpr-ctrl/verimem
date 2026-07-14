# VeriBench and Verified Memory: Pricing the Wrong Answer in Agent Memory

**DRAFT — 2026-07-14.** Working preprint. Every empirical number is **self-run
and reproducible** from the open-source repository (paths cited inline as
`file:LINE`); **none is third-party audited**, and we say so wherever a figure
appears. This draft is written to be falsifiable, not promotional: the
unflattering rows are in the tables, and the limitations section is not an
afterthought.

> **Honesty ledger for this draft.** Only three external papers are cited that
> the authors verified against the live arXiv abstract during writing
> (2606.30306, 2603.21172, 2606.12703). Product competitors (Mem0, Zep, Letta,
> MemOS) and standard datasets (HaluEval, SQuAD 2.0, LoCoMo, LongMemEval) are
> cited as software/data that exists. Any claim we have not re-run is marked
> `[UNVERIFIED]` and must not survive to submission.

---

## Abstract

Memory layers for LLM agents are evaluated on how much they recall. A symmetric
retrieval score (recall@k, hit@k) cannot distinguish a confident wrong answer
from an honest "I don't know" — yet in deployment those two outcomes have
opposite costs. We make two contributions. **(1) VeriBench**, an open,
deterministic, pre-registered benchmark that scores a memory the way a
deployment pays for it: `NET(λ) = (correct − λ·wrong) / n`, where λ is the
declared cost of a wrong answer relative to an abstention, swept over
λ ∈ {1,2,5,10}. On HaluEval QA (200 answerable + 100 unanswerable), a
raw vector store without an abstention floor turns **net-negative past λ=2**
(100 fabricated answers on the unanswerable half), while a memory with a
calibrated floor stays positive out to λ≈45; a scrambled control goes to
NET(1)=−0.94, and the floor-off control fabricates exactly as predicted — the
benchmark's sanity checks fail when they should. **(2) VeriMem**, a
memory engine whose write path is an admission gate: a candidate fact is
admitted, downgraded, or refused by whether its cited source **entails** it
(source⊢fact entailment, **AUROC 0.971** on SNLI, judge-independent), and whose
per-source trust combines two channels (inter-source agreement and
use-outcome) so that manufactured consensus cannot self-confirm. We reproduce
the trust axis on a **real held-out corpus** (HaluEval, pre-registered criteria,
3/3 seeds): a 4-identity cartel that self-confirms to 0.90 under naive counting
is demolished to 0.20 by independence + audit-deconfounding, honest sources
restored to 0.95, and its hallucinated answers drop out of recall. Finally, we
show that a strong discrimination score (AUROC) does not imply the abstention
knob **operates** at its declared risk, and close the gap with a calibration
step (TCE ≤ 0.011 at declared λ ∈ {0.5–9}). All code, pre-registrations and raw
result files are in the repository; the results are self-run, not certified.

---

## 1. Introduction

A long-running agent that "remembers" will, sooner or later, write something
false — a hallucinated fact, a stale value, a claim it cannot support. Once
written, that claim re-surfaces at recall as if it were history. The failure is
self-amplifying: one bad write pollutes every downstream retrieval.

The open-source memory landscape optimises for the wrong quantity. Mem0, Zep,
Letta and MemOS are benchmarked on retrieval quality — how much of the gold
evidence comes back. But on the *answerable* half of any corpus, a gated memory
and a raw vector store retrieve almost identically; recall@k sees no difference.
The difference appears on the questions the store **cannot** answer: a memory
without an abstention floor returns its nearest neighbour anyway, with full
confidence. In production that is a fabricated answer; in a symmetric benchmark
it is invisible. A 2026 survey of always-on LLM agents (arXiv:2606.30306) finds
the field concentrates far more on accumulating and retrieving agent state than
on governing it — the write-admission gap, exactly.

We argue the fix is two-sided, and neither side is a retrieval score.

**Measure the right thing.** We introduce **VeriBench** (§4): score a memory at a
declared error cost. `NET(λ) = (correct − λ·wrong)/n` makes a fabricated answer a
*priced event*: it earns +1 when right, −λ when wrong, 0 when the system
abstains. The break-even accuracy is λ/(1+λ), the same threshold a deployment's
SLA knob tunes to — the benchmark measures the store at the exact number the
operator tunes it with. The metric, the λ sweep, and the refutation conditions
are committed *before* any run (pre-registration), and the benchmark ships
controls that must fail (a scrambled store, a floor-off store) — if they pass,
the benchmark is broken.

**Build the right defense.** We describe **VeriMem** (§3), a memory engine whose
write path is an admission gate. Every candidate fact is admitted, downgraded or
refused by whether its cited source *entails* it — a source⊢fact entailment
check (AUROC 0.971 on SNLI, §5.1). On top of the gate, a per-source trust book
combines two complementary channels — inter-source agreement (consistency) and
a-posteriori use-outcome — so that copies or colluders of one feed collapse to a
single witness and cannot manufacture consensus. We reproduce this trust axis on
real held-out data (§5.3), and we show that abstention, to be trustworthy, must
be *calibrated to operate at the declared risk*, not merely to discriminate
(§5.4).

Contributions:

1. **VeriBench** — a pre-registered, deterministic, model-free benchmark that
   prices the wrong answer via NET(λ), with real-corpus, causal, and adversarial
   axes, and controls that must fail (§4).
2. **A verified-memory engine** — write-time source⊢fact entailment gate
   (AUROC 0.971) + two-channel per-source trust with independence and
   audit-deconfounding, reproduced on a real corpus 3/3 seeds (§3, §5.3).
3. **Deployment-faithful abstention** — evidence that AUROC does not imply
   operating at the declared risk, and a calibration that closes the gap
   (TCE ≤ 0.011 at declared λ) (§5.4).

We are explicit about what this is not (§6): every number is self-run and
reproducible, none is third-party audited; the engine has essentially no
external adoption yet; and the trust guards ship default-OFF pending exactly the
kind of external scrutiny this paper invites.

---

## 2. Related work
<!-- BLOCCO 2: mem0/Zep/Letta/MemOS (prodotti, competitor review), HaluMem/
LoCoMo/LongMemEval (benchmark retrieval), SMSR 2606.12703 (provenance gate,
VERIFICATO), Oxford 2603.21172 (selective prediction, VERIFICATO), survey
2606.30306 (VERIFICATO). Verificare OGNI altro arXiv prima di citarlo. -->
*(da scrivere — blocco 2)*

## 3. VeriMem: the engine
<!-- write-gate L1 lexical + L4 grounding (grounding_gate.py, AUROC 0.971);
provenance on read; source_trust.py two channels + independence + deconfound;
epistemic labels; composition ring + P85 self-provenance. Solo feature reali. -->
*(da scrivere — blocco 3)*

## 4. VeriBench: the benchmark
<!-- NET(λ) definizione + decision theory; pre-registration; 3 assi (real/
causal/adversarial); controlli-che-falliscono; mem0 adapter same-footing. -->
*(da scrivere — blocco 4)*

## 5. Experiments

All numbers are self-run and reproducible from the cited scripts/result files;
none is third-party audited. Retrieval uses `intfloat/multilingual-e5-base`
offline; no external paid API is called anywhere in these runs.

### 5.1 Write-gate entailment (AUROC 0.971)

The write path's L4 layer scores whether a candidate fact is *entailed* by its
cited source (`engram/grounding_gate.py`). Measured on SNLI, the source⊢fact
entailment score reaches **AUROC 0.971**, and the number is *judge-independent*
(the same score separates entailed from non-entailed pairs regardless of which
LLM produced the candidate). This is the discriminator behind admit / downgrade
/ refuse: a fact whose source does not entail it is quarantined (hidden from
default recall), not stored as fact.

### 5.2 VeriBench head-to-head (HaluEval QA and SQuAD 2.0)

Setup: 300 probes per corpus (200 answerable + 100 unanswerable, disjoint
splits). Both engines use the *identical* embedder offline; mem0 2.0.11 runs in
raw-store mode (its LLM is never called — that axis is out of scope by
declaration). Correctness is id-decidable retrieval; no LLM judge in the loop.
`NET(λ) = (correct − λ·wrong)/n`. Source:
`benchmark/results/veribench_mem0_{halueval-qa,squad-v2}_2026-07-13.json`,
`benchmark/results/veribench_real_halueval-qa_2026-07-13.json`.

**HaluEval QA.**

| System | ✓ | ✗ | ∅ | cov | NET(1) | NET(2) | NET(5) | NET(10) | neg at λ |
|---|---|---|---|---|---|---|---|---|---|
| Verimem · floor τ=0.8 (default) | 182 | 4 | 114 | 0.62 | +0.593 | +0.580 | +0.540 | +0.473 | 45.5 |
| mem0 · as shipped (no floor) | 200 | 100 | 0 | 1.00 | +0.333 | 0.000 | −1.000 | −2.667 | 2.0 |
| mem0 · bolted floor 0.75 (tuned on eval) | 166 | 0 | 134 | 0.55 | +0.553 | +0.553 | +0.553 | +0.553 | never |
| Same store, floor OFF (τ=0 control) | 192 | 100 | 8 | 0.97 | +0.307 | −0.027 | −1.027 | −2.693 | 1.9 |
| Scrambled control (must fail) | 5 | 287 | 8 | 0.97 | −0.940 | −1.897 | −4.767 | −9.550 | 0.02 |

Read both ways, honestly. As shipped, mem0 goes net-negative past λ=2 (100
fabricated answers on the unanswerable half); Verimem's default stays positive to
λ≈45. But a floor can be **bolted onto any engine**: a threshold tuned *on this
eval* gives mem0 a flat +0.553 that **beats our default at λ≥5** (our default
still wins at λ=1 and λ=2; the crossover is λ=4). The differences that remain:
the engine ships no floor, the bolted threshold was chosen on the test set, and
the flat line answers nothing it isn't sure of — coverage 0.55 vs our 0.62.
The two controls behave as pre-registered: floor-off fabricates, scrambled
collapses.

**SQuAD 2.0** (harder — distractor passages compress the score band).

| System | ✓ | ✗ | ∅ | cov | NET(1) | NET(2) | NET(5) | NET(10) | neg at λ |
|---|---|---|---|---|---|---|---|---|---|
| Verimem · floor τ=0.8 (default) | 163 | 49 | 88 | 0.71 | +0.380 | +0.217 | −0.273 | −1.090 | 3.3 |
| Verimem · best floor 0.85 (tuned) | 98 | 7 | 195 | 0.35 | +0.303 | +0.280 | +0.210 | +0.093 | 14.0 |
| mem0 · as shipped (no floor) | 200 | 100 | 0 | 1.00 | +0.333 | 0.000 | −1.000 | −2.667 | 2.0 |
| mem0 · bolted floor 0.80 (tuned) | 44 | 0 | 256 | 0.15 | +0.147 | +0.147 | +0.147 | +0.147 | never |

On SQuAD the crossover drops to λ≈3.3 at the product default, and holding NET
positive at λ=10 costs coverage 0.35 (best-floor arm). Abstention is a dial, not
magic — the corpus decides how expensive honesty is. Hiding this table would be
the dishonest move.

### 5.3 Source-trust reproduced on a real corpus

The two-channel trust book (`engram/source_trust.py`) declares in-code that it
ships default-OFF pending "the held-out reproduction on real VeriMem data". We
ran that reproduction (`benchmark/source_trust_realcorpus.py`, HaluEval QA;
`..._seed{11,12,13}` result files). Pre-registered criteria (fixed before the
first run): C1 independence denies the cartel, C2 no reputation inversion under
the mature policy, C3 honest corroboration restored, C4 the gate wins the recall.

| Condition | cartel-trust | honest-trust | wrong-liar-rate |
|---|---|---|---|
| OFF | 0.50 | 0.50 | 0.25 |
| ON (naive ≥2-distinct) | **0.90** ⚠ self-confirm | 0.79 | 0.025 |
| ON + independence (raw) | 0.50 | 0.50 (merged) | 0.25 |
| ON + independence + deconfound | **0.20** | **0.95** | **0.0** |

`reproduction_holds` on **3/3 seeds** (11–13). A 4-identity cartel that
self-confirms to 0.90 under naive counting is demolished to 0.20 by independence
plus audit-deconfounding (co-admission of audit-revealed-false values — the
do-operator that separates collusion from shared truth); honest sources are
restored to 0.95; the cartel's hallucinated answers drop out of recall (→0.0).
Raw independence alone leaves wrong-liar at OFF's 0.25 (it merges the honest too,
so nobody is punished) — end-to-end evidence that the deconfound is load-bearing,
not decorative.

**Honest-noise robustness curve** (`benchmark/source_trust_noise_curve.py`, 18
points, noise 0→0.25 × seeds 11–13, declared bi-encoder regime). No reputation
inversion at any noise (H2 pass 18/18). Wrong answers written by **deceivers =
0/18 at every noise level** — the outcome channel pins liars+cartel under the
quarantine floor everywhere. The residue is 100% **honest slips**: a per-claim
disease (reconciliation / abstention territory), not a per-source one. We report
this rather than hide it: under heavy honest noise the separation degrades, and
the honest place to attribute that residue is the claim, not the source.

### 5.4 Abstention that operates at the declared risk (TCE)

A strong AUROC says the confidence scores *discriminate*; it does not say the SLA
knob λ *operates* at its declared risk (Oxford, arXiv:2603.21172). We measured
this on HaluEval held-out with an isotonic calibration fit on the dev split only
(`benchmark/selective_deployment.py`).

| Regime | E-AURC | TCE at λ∈{0.5,1,3,9} | observed risk | coverage |
|---|---|---|---|---|
| Raw e5 scores | 0.0008 (near-oracle ranking) | up to 0.08; coverage collapses to 12.8% at λ=9 | promised ≠ delivered | — |
| Isotonic-calibrated (fit on dev) | 0.044 | **≤ 0.011** across all λ | **1.1%** | **73%** |

Raw scores rank near-oracle (E-AURC 0.0008) but promise a different risk than
they deliver; a pure monotone calibration makes every declared λ target met —
TCE ≤ 0.011, observed selective risk 1.1% at 73% coverage. Declared trade-off:
the step calibration flattens fine ranking (E-AURC 0.0008→0.044). Raw scores for
ranking, calibrated scores for operating a declared λ.

## 6. Limitations
<!-- self-run non-audited; e5 band compressa (over-abstention su store piccoli);
honest-noise degrada la separazione trust; trust⊥causalità; 0 adozione;
benchmark/ non su PyPI; judge Claude non GPT-4 su HaluMem. -->
*(da scrivere — blocco 6)*

## 7. Conclusion
*(da scrivere — blocco 7)*

---

## References
<!-- Solo verificati + codebase. Da completare nel blocco 2. -->
- [VERIFIED] arXiv:2606.30306 — *Always-On Agents: A Survey of Persistent Memory, State, and Governance in LLM Agents* (Ding, Nannapaneni, Liu, Zhang, 2026).
- [VERIFIED] arXiv:2603.21172 — *Entropy Alone is Insufficient for Safe Selective Prediction in LLMs* (Phillips, Gustafsson, Wu, Thakur, Clifton, Oxford).
- [VERIFIED] arXiv:2606.12703 — *SMSR: Certified Defence Against Runtime Memory Poisoning in Persistent LLM Agent Systems* (Sharma, 2026).
- arXiv:2402.17753 — *LoCoMo* (Maharana et al., ACL 2024).
- Repository: `engram/grounding_gate.py`, `engram/source_trust.py`, `benchmark/veribench/`, `benchmark/source_trust_realcorpus.py`, `benchmark/selective_deployment.py`.

---

*Path: `docs/papers/veribench-preprint-DRAFT.md`. Status: DRAFT (skeleton + §1). Supersedes the narrower `write-time-confabulation-gates-DRAFT.md` (2026-05, keyword-gate only, unverified refs).*
