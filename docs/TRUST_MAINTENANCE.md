# Trust maintenance — the write-path moat

Most memory systems (mem0, Zep, MemOS) *extract and store*. Verimem adds a layer they
don't have: a **write-path that refuses to be fooled**. It is a tunable dial from
**recall-first** (apply every plausible update) to **never-delete-truth** (a stored,
verified fact cannot be overwritten by a bare assertion). Everything here is **off by
default and byte-identical** until you opt in; the whole dial is env-driven.

All knobs below are verified present in the code (see the file:line anchors). Numbers
are measured on HaluMem-Medium, local and deterministic (no `claude -p`).

## The knobs

| env | default | effect |
|---|---|---|
| `ENGRAM_RECONCILE_ON_WRITE` | off | master switch. When on, each stored fact is reconciled against shared-entity candidates (`engram/semantic.py` `_reconcile_on_write_enabled`). Off ⇒ nothing runs. |
| `ENGRAM_RECONCILE_AUTO_SUPERSEDE` | off | allow a clean update to actually **supersede** the old fact. Off ⇒ conflicts are only **contested** (fail-safe: never deletes). Needed to move the *Updating* slice. |
| `ENGRAM_RECONCILE_REQUIRE_EVIDENCE` | *(unset)* | anti-sycophancy policy when auto-supersede is on (`_reconcile_evidence_policy`): unset ⇒ **tiered** (require evidence only to overwrite an *evidenced* fact; bare→bare updates still apply); `=1` ⇒ **strict** (require evidence for any supersede); `=0` ⇒ **none** (raw recency+authority). |
| `ENGRAM_RECONCILE_MIN_OVERLAP` | `0` | precision floor on the NLI conflict verdict (`engram/truth_reconciliation.py` `_min_conflict_overlap`): reject a CONTRADICTION whose content-token Jaccard is below the floor — filters same-entity different-attribute pairs the NLI over-calls. |
| `ENGRAM_RECONCILE_NLI` | *(unset)* | conflict judge (wired by `HippoAgent.build` via `wire_reconcile_judge`): `=local` ⇒ **local NLI** cross-encoder (no `claude -p`, O4-clean, ~4× conflict-recall vs lexical); `=1/on/true/yes/llm` ⇒ subscription LLM judge; unset ⇒ lexical. |
| `ENGRAM_ENTITY_LIVE` | **on** | entity extraction on write (`_entity_live_enabled`). Reconcile finds candidates via shared entities, so this must stay on for the moat to see anything. |

## The dial, with measured numbers

**Anti-sycophancy** (a bare, confident, merely-newer assertion must not overwrite a
stored fact just because it was asserted). Two-sided bench under escalating pressure:
cave-rate **1.0 → 0.0** with the evidence gate, false-rigidity 0.0
(`benchmark/sycophancy_mem.py`).

**Tiered vs strict** (HaluMem is_update GT, n=60, local NLI thr 0.9):

| policy | update-recall | verified fact protected |
|---|---|---|
| none | 0.2833 | ✗ |
| **tiered** (default) | **0.2833** | ✓ |
| strict | 0.0 | ✓ (over-rigid) |

Tiered *dominates*: same recall as ungated, and a verified fact is sycophancy-proof.
Strict is safe but collapses recall on bare corpora (HaluMem updates carry no evidence).

**Precision dial** (`ENGRAM_RECONCILE_MIN_OVERLAP`, same setup):

| floor | update-recall | complementary false-supersede |
|---|---|---|
| 0.0 (default) | 0.2833 | 0.0667 |
| 0.2 | 0.20 | **0.0** |

A precision/recall dial (**not** a free win): floor 0.2 drops complementary
truth-deletion to zero at a −29% recall cost. Composed with tiered ⇒ *verified facts
protected AND zero complementary truth-deletion* — the "never lose truth" end of the dial.

**Conflict detection is the throughput gate.** Lexical matching supersedes only
1.67% of real HaluMem updates; the local NLI judge lifts that ~17× to 0.2833. So for
the moat to *do* anything at recall, set `ENGRAM_RECONCILE_NLI=local`.

## Honest caveats

- **The candidate finder gates everything.** Reconcile only sees facts that share an
  extracted entity AND pass the conflict judge. With the lexical default it rarely
  fires; `=local` is what makes it useful. Provenance/evidence gate is applied *after*
  a candidate is found.
- **`verified_by` is I/O-verified.** A `status=verified` write is demoted to
  `model_claim` unless its `verified_by` refs pass verification (filesystem / git),
  so "evidenced" means genuinely-backed, not merely-claimed.
- **Local scoring is a relative proxy.** The local e5 matcher for the Updating slice
  reads ~0.66 where the LLM judge reads ~0.29; use local numbers for A/B *direction*,
  not leaderboard absolutes. Judge-graded runs need `claude -p` (out of an
  offline/subscription loop).
- **`ENGRAM_RECONCILE_NLI` is wired by `HippoAgent.build`.** A bare `SemanticMemory`
  needs a programmatic `set_reconcile_judge(...)`.
- **The local NLI judge is usable but noisier than the paid one.** On HaluMem
  interference (seed7, n=160): local NLI AUROC ~0.81, best point TPR 0.71 / FPR 0.25
  vs the LLM judge's TPR 0.675 / FPR 0.10 — comparable recall, ~2.5× the false
  positives. Fail-safe bounds the cost (a false positive is a recoverable CONTESTED
  doubt, not a deletion); a precision-first deployment should raise the threshold or
  use `=llm`. Measured by `benchmark/interference_local_nli.py`.

## Self-correcting memory — the temporal recipe (measured 2026-07-05)

Auto-supersede only *works* when three conditions hold together. Each was
root-caused on HaluMem-Medium (65 sessions, 807 gold facts, one user):

1. **One cumulative store per user.** A cross-session conflict's two facts must
   coexist: with per-session isolated stores, Memory-Conflict evidence never meets
   its contradiction (measured QA 0/10, while cumulative evidence-recall@5 = 40/40).
2. **The semantic timestamp, not `now`.** `classify_conflict` computes the age gap
   from `created_at` (`engram/truth_reconciliation.py:123`); facts ingested in one
   batch share `created_at=now` ⇒ age gap 0 ⇒ every update is a *dispute*, never a
   supersede. `ingest_conversation(asserted_at=...)` stamps the conversation's own
   time onto the facts — this is what unlocks the axis.
3. **The precision floor is MANDATORY with auto-supersede.** At floor 0 the NLI
   over-calls same-entity/different-attribute pairs and the result is destructive:
   **700/807 facts retired (87%)** — a birth date superseded because a fact about
   snakes arrived; sampled legitimacy ~6%. At `ENGRAM_RECONCILE_MIN_OVERLAP=0.35`
   the same run retires **146, with 0 cross-attribute pairs** (12-session inspection:
   99→7 supersessions, all real same-attribute updates — income, savings, health,
   job; birth date / age / degree untouched). Real updates separate cleanly
   (overlap 0.45–0.60) from the junk (<0.25).

**Performance.** The overlap pre-gate (`find_related_candidates`) screens
candidates *before* the expensive NLI call — behaviour-preserving (the floor would
reject them after) and it kills the O(facts-per-entity) blow-up on a popular
entity: full-history ingest **1752s → 573s (3×)** at equal-or-better precision.
Remaining honest cost: ~0.7s/store with the default DeBERTa-large judge — fine for
background ingest, not yet for interactive hot paths (next lever: base model /
batched pairs).

Product surface: `ingest_conversation(..., asserted_at=<epoch>)`
(`engram/conversation_ingest.py`) and `benchmark/halumem_qa.py --reconcile`
(defaults the floor to 0.35). Evidence: `tests/test_conversation_ingest.py`
(asserted_at propagation), `tests/test_truth_reconciliation_matching.py`
(pre-gate skips the NLI below the floor), `benchmark/results/reconcile_scale_fixed.json`.

## Bi-temporal memory (v13): two clocks, like a real memory

``created_at`` is TRANSACTION time (when the system learned it — never
backdated, so the staleness half-life and the anti-spoof fail-closed guard stay
sound). ``asserted_at`` (schema v13) is EVENT time (when it was said / true —
drives the reconcile age-gap and the history story; a FUTURE value is a
legitimate calendar fact, not spoofing). Root-cause that forced it: stuffing
event time into ``created_at`` made **83% of a timestamped store invisible to
recall** (673/807 facts on HaluMem u1 — staleness hid the backdated, anti-spoof
hid the future-dated). Product surface: ``ingest_conversation(asserted_at=…)``
and ``hippo_ingest_conversation(asserted_at=…)``.

Four contracts hardened by the adversarial 5-lens review (2026-07-06, each
with a pre-fix-failing test; findings + minimal repros committed in
``benchmark/results/workflow_5lenti_findings.json``):

* **A future assertion is data, not truth-yet** — ``classify_conflict`` now
  uses ``now``: an ``asserted_at`` beyond now+300s cannot supersede the
  present fact (dispute, recoverable); the same pair re-evaluated once the
  date has arrived is a clean update. Before: a calendar fact deleted present
  truth 60 days early.
* **``recall_as_of`` death is EVENT time** — a fact stops being current at its
  *successor's* ``asserted_at``, not at ``superseded_at`` (wall-clock): a
  batch-ingested 2024 history is superseded *today*, which made every retired
  version look still-current at any past ``when``.
* **Deep / as-of reads are archaeology** — they no longer bump
  ``last_verified_at``: a READ of the past must not refresh dormant facts
  into the live default view.
* **The plain delete keeps chains walkable** — incoming supersession pointers
  are re-linked through the removed row, so a later GDPR
  ``purge_history=True`` closes over the whole chain even across holes dug by
  earlier plain deletes (holes dug BEFORE this fix are not reconstructible —
  stated limit).

## Answer-with-history: "what changed, when — and what I'm not sure about"

Competitors serve the latest value; Verimem KEEPS the supersession chain
(``superseded_by`` + ``superseded_at`` + reason) and the unresolved-conflict
ledger, and ``engram/temporal_context.py`` turns both into recall context:

```
Johnson's monthly income is 5000 USD [current, since 2024-01-13]
  | PREVIOUSLY: 'Johnson's monthly income is 3500 USD' (asserted 2023-11-14, until 2024-01-13)
  | DISPUTED: conflicting record 'Johnson works at Hotel Riva' (unresolved)
```

* ``fact_history`` — backward walk over ``SemanticMemory.direct_predecessors``
  (bounded, cycle-safe, main line only);
* ``recall_with_history`` — live top-k, each hit enriched, fail-safe (an
  enrichment error degrades to the plain proposition);
* declared disputes — an honest memory SAYS it holds two conflicting records
  instead of silently picking one.

MCP surface: ``hippo_recall_history``. Bench arm: ``halumem_qa --history``.

**Measured** (HaluMem u1 transition questions — Memory Conflict + Dynamic
Update, n=44, same reconciled bi-temporal store, same verify answerer, the ONLY
variable is the history-enriched context): plain 0.6364 → **history 0.7955**
(+16pp); Memory Conflict 0.70 → **0.825**, Dynamic Update 0.0 → 0.5. Strictly
additive: **7 questions unlocked, 0 lost**, and the unlocked golds are exactly
the transitions ("increased from 3500 to 4500", "Retired", "health improved").
Compound arc on Memory-Conflict QA: 0.15 (plain store, strict answerer) → 0.675
(reconciled + verify) → **0.825** (+ history) = **5.5× from baseline**.

## The read-path dial: QA on HaluMem (n=120, like-for-like, self-proving arms)

The same trust philosophy on the ANSWER side. `ENGRAM_GROUNDING_GATE=1` verifies
each answer externally against the retrieved evidence (the model's own confidence
is at chance for flagging its fabrications) and abstains when unsupported;
`ENGRAM_RECALL_CENTERING=1` is a zero-cost retrieval de-anisotropy lever.

| arm | correct | hallucination | omission |
|---|---|---|---|
| baseline | 0.4083 | 0.2333 | 0.3583 |
| centering | **0.4333** | 0.2250 | 0.3417 |
| gate | 0.3583 | 0.1250 | 0.5167 |
| centering+gate | 0.3504 | **0.1111** | 0.5385 |

Max-correct point: centering. Min-hallucination point: centering+gate (**−52%**
vs baseline). Honest: the effects do not compose additively on correct (the
gate's abstentions dominate). Competitors ship one unmeasured operating point;
this is a measured 4-point dial. On the extraction axis the same gate is
**F1-flat insurance** (+0.95pp precision / −2.7pp recall) with the local judge.

## Evidence (tests + benches)

- `tests/test_reconcile_tiered_gate.py`, `tests/test_reconcile_evidence_gate_writepath.py`
  — the tiered/strict/none policy and write-path forwarding.
- `tests/test_reconcile_overlap_guard.py` — the NLI precision floor.
- `tests/test_updating_selector_overlap.py` — the update-selector floor (Pareto).
- `tests/test_reconcile_judge_env_wiring.py` — `=local` wires the local NLI judge.
- `benchmark/reconcile_truth_maintenance.py` (+ `results/reconcile_evidence_gate_tradeoff.json`)
  — the update-recall / false-supersede frontiers.
- `benchmark/sycophancy_mem.py`, `benchmark/sycophancy_bench.py` — the cave-rate.

## The abstention price of rich context — measured, with the cure queued

Dated-history context lifts transition QA by +16pp, but it has a measured
price on unanswerable questions: Boundary abstention **1.000 (plain context) →
0.949 (history context)** on u0 (39 questions, same store, same verify
answerer — the model, seduced by dated specifics, asserted 2 answers it should
have refused; 0 recovered). The queued cure is **routing**: serve history only
on temporally-qualified questions (the +33pp Basic-Fact lift came exactly from
those) and plain context elsewhere — hypothesis: keep both 1.000 and +16pp
(`exp3`, pre-written, falsifiable).

## GDPR-grade forget: the chain dies, nothing resurrects

Probe-confirmed defect (2026-07-06): a plain `delete()` removes ONE row while
superseded predecessors carrying the SAME sensitive datum survive — and
resurface via deep recall and `as_of` time travel. Fixed:
``Memory.delete(fact_id, purge_history=True)`` removes the full supersession
closure (forward successors + every predecessor generation, all branches) and
scrubs the dispute-ledger entries referencing them. Default stays single-row.
For the lawyer/medical personas this is the difference between "hidden" and
"forgotten" — and the memory now knows both, explicitly.
