# Truth-Reconciliation Loop — design (2026-06-16)

Status: DESIGN. The empirical motivation is `docs/TRUST_CALIBRATION.md`.

## 1. The problem it exists to solve

The calibration study found the decisive fact: the trust-signal's dangerous
**over-trust scales 0.0 → 0.5 with `unobserved_p`** (the fraction of
knowledge-updates Engram never recorded). *No scoring function fixes it* — the
calibrated prototype's over-trust in the half-blind world equals the categorical
one's. The only lever that moves the dangerous metric is **observing more
change**. The truth-reconciliation loop is that mechanism: it converts real-world
signals into recorded supersessions/contradictions, driving `unobserved_p` toward
0 in proportion to how many updates leave an observable trace.

## 2. Principle (and its honest ceiling)

A memory cannot know about a change that leaves **no** trace anywhere. But most
updates do leave one. The loop has N "intake ports", each turning a trace into a
trust update via the existing primitives (`SemanticMemory.supersede`,
`ContradictionStore.add`):

| port | real-world signal | action | confidence |
|---|---|---|---|
| **P1 update-on-write** | a new fact on the same subject/predicate with a different value | `supersede(old, new)` | high when entity+predicate match |
| **P2 outcome-feedback** | an episode FAILS while relying on fact F | lower `confidence(F)` / flag for review | medium |
| **P3 user-correction** | the user explicitly negates/corrects | `supersede` or mark `contested` | high (user authority) |
| **P4 cross-source** | two *independent* sources disagree | mark `contested` | medium |

Ceiling (stated, not hidden): the loop shifts `unobserved_p` toward 0 *only for
updates that pass through a port*. A world-change never written, never acted on,
never corrected stays invisible. We reduce the blind fraction; we do not zero it.

## 3. First prototype: P1 (update-on-write)

**Status (2026-06-17):** decision logic + **candidate-matching**
(`find_related_candidates` / `reconcile_against_corpus` via the entity-KG) are
implemented and tested (12 tests, end-to-end FIND+reconcile). Default is
**fail-safe**: contest, never auto-supersede on a correlation match
(`auto_supersede` opt-in). Still **NOT wired into `SemanticMemory.store`**.
Remaining before production: (a) the write-path wiring + a performance budget,
(b) a real **semantic conflict detector** — today's matching is correlation by
shared entity, so a *complementary* fact could be a candidate; the fail-safe
default mitigates but does not solve this, (c) measure the false-supersede rate
on a real corpus before enabling `auto_supersede`.

The most concrete and directly measurable port. At write time of `F_new`:

1. Find `F_old` *update candidates*: same entity + same predicate, **different
   value**, not already superseded.
2. Strong, unambiguous match → `supersede(F_old, F_new, reason="reconcile:update-on-write")`.
3. **Fail-safe**: anything short of an unambiguous match → mark `contested`
   (review), never a blind supersede. A wrong supersede deletes truth from the
   live set; a wrong "contested" only adds a (visible, recoverable) doubt. The
   asymmetry is the same one that drove the #6 redesign.

## 4. Metric (falsifiable)

Extend `scripts/bench_trust_calibration.py`: route a fraction of the Type-B
(obsolete-in-world) updates through P1 (an `F_new` arrives and reconciliation
runs). Prediction: for updates that pass through P1, **over-trust → 0** (they
become observed, like the fully-observed world); for the externally-unobserved
remainder it stays. If over-trust does NOT drop for the P1-routed updates, the
port does not work and the design is falsified.

## 5. Risks & guards

- **False supersede** (the dangerous one): demands reliable entity+predicate
  extraction. Guard: supersede only on an unambiguous subject match with a
  genuinely conflicting value; otherwise `contested`.
- **Supersede storms / loops**: `supersede` is idempotent and raises
  `SupersedeConflict` on re-targeting — the loop must catch and chain, not thrash.
- **Authority**: P3 (user) outranks P1 (inferred). Never let an inferred
  supersede silently overwrite a user-asserted fact.

## 7. Reality check on a real corpus (2026-06-17) — honest, unflattering

Dry-run of P1 on the live ~4300-fact corpus (read-only), 400 most-recent
non-superseded facts:

- **Shared-entity-ONLY matching: 5090 candidates on 16 facts.** Popular entities
  ("engram", "claude", linked to thousands of facts) explode into hundreds of
  spurious correlations each; the fail-safe default would have written 5090 FALSE
  contradictions. → fixed: `find_related_candidates` now filters by
  `looks_like_conflict`.
- **With the conflict filter: 0 candidates on 400 facts**, even at a permissive
  `max_diff=4`. So it is NOT the heuristic being too tight — the corpus simply
  has no token-detectable update among recent facts: facts sharing an entity are
  COMPLEMENTARY (100 different facts about "engram"), not successive values of
  the same attribute.

**Conclusion (no spin):** P1 as built (entity + token-conflict, update-on-write)
is correct, safe, and lab-validated (4 critics), but **inert on this corpus** —
zero effect. Its value only shows in domains with same-attribute value updates
phrased similarly (config stores, changing KBs). A *generally useful*
truth-reconciliation needs a **semantic** conflict detector (LLM-level: "the
timeout is 30s" → "we cut the timeout to 5 seconds" is an update that token
overlap misses), not token matching. That — not P2/P3/P4 — is the real next step,
and it is a strategic call (one LLM pass per candidate, cost vs value).

## 7b. O1 lesson (2026-06-17) — coherence_check already existed

While "proceeding", a memory-first check (which should have happened BEFORE P1)
found `engram/coherence_check.py`: it already detects `near_duplicate` +
`numeric_clash` ("30s" vs "5s") + `boolean_clash` (negation) using **cosine on
embeddings** — a *semantic* conflict detector, better than P1's token
`looks_like_conflict`. P1 largely **re-invented** it (worse), and the earlier
"a semantic detector needs a costly LLM pass" claim was wrong — it exists, free.

What P1 added that coherence_check lacks: a write-time, fail-safe action wiring
(reconcile_new_fact behind a gate). The correct synthesis is coherence_check
(semantic detection) + that wiring — NOT a new token detector. But for THIS
corpus the whole axis is moot: it has no value-updates, only redundancy + dev
noise. Engram already has every anti-confab brick (trust-signal, coherence_check,
find_duplicate_facts, facts_merge, L1.x); the real gap is **activation +
measurement on real data + corpus hygiene**, not more code.

## 6. Build order

P1 prototype + the calibration-bench extension that measures it → then P2
(outcome-feedback, reuses episode outcomes) → P3 (correction intake) → P4
(independence-weighted, needs the provenance graph). Each lands with a falsifiable
number, not a claim.
