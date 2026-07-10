# VeriBench — design inputs (pre-F3 seed, 2026-07-10 night)

Synthesis of BOTH instances' work as the raw material for VeriBench (#11).
Sources: this repo's F1 falsification run (`TEST_SURFACE_MAP.md`) + the
research instance's Vivarium corpus (`Code/vivarium/docs/`: TRANSFER-TO-
VERIMEM.md §3-quater, WORKFLOW-CROSSINGS-RESULTS.md, WORKFLOW-CAUSAL-
FRONTIER-RESULTS.md — read 2026-07-10 ~23:30 before any VeriBench design,
per Aurelio's direction). Nothing here is a benchmark yet; these are the
load-bearing design decisions with their evidence.

## 1. The scoring function IS the benchmark (from causal-abstention)

Vivarium measured: **blanket abstention only TIES confident-wrong under
symmetric scoring**; it strictly wins only when wrong costs more than silence
(crossover λ*(f=0)=0.965; and abstention LOSES where the relation is genuinely
causal). Translation: **recall@k-style symmetric scoring makes a trust
memory's core property (knowing when it doesn't know) INVISIBLE.** Every
existing memory bench scores symmetrically — that is exactly why the market
"can't see" trust.

**Decision: VeriBench scores NET = (correct − λ·wrong)/n with λ>1, declared,
plus coverage.** Abstention is a first-class outcome, not a miss. This is
simultaneously our differentiator and an honest scientific position (the lab
measured the crossover).

## 2. Axes nobody measures (F1 falsification + Vivarium adversarial)

Verified on mem0 2.0.4 (same embedder, zero-API): no count API (5/12 via
top-k), 0/5 contradiction detection. Vivarium adds the adversarial axes with
measured mechanisms:

| axis | evidence | existing benches |
|---|---|---|
| silent data loss at ingest | F1 C4/S2 (4.0% gold quarantined; 93% truncated) | none measure |
| set-operation correctness (count/exclude/all) | F1 sweep; mem0 5/12 | none |
| contradiction detection & surfacing | F1 S4 4/5 vs mem0 0/5 | none |
| provenance/attribution of every answer | gate_router + explain | none |
| **manufactured-consensus resistance** | performative echo: corroboration-trust stays confidently wrong (0.40 flat) while typed/interv immune (0.663, 28-30/30) | none |
| **closed-loop trust-gaming resistance** | adaptive adversary 6.41× worse but two-signal still dominates (0.301 vs 0.799); mechanism: truth-tax | none |
| **causal-scope honesty** | trust ⊥ causality: trusted memory 21% on do(X), confidently wrong at trust 0.89 | none |
| graceful degradation under stress | eclipse/extreme: abstain 0.95 instead of wrong | none |

## 3. Hard scope declarations (from the ruptures — put them IN the bench)

- **Provenance ≠ causality (v10.0, category limit).** The ledger certifies
  "who said it and it is corroborated", NOT "it is causally true". A
  well-verified spurious correlation stays spurious. VeriBench must include
  causal-trap items where the HONEST behavior is abstain-or-type-split, and
  confident observational answers to do(X) questions are scored as the
  failure they are. This also keeps US honest on the site.
- **Verification pays only under source unreliability (drift-curve).** In
  pure-drift the value is offload/dedup (+0.483), verification adds ~0.001.
  VeriBench must SEPARATE the dedup axis from the trust axis or it credits
  the wrong mechanism.
- **Consistency-trust can become a liability at extreme performativity**
  (KILL-2: eps≥0.5). Declared boundary, not hidden.

## 4. The 4th classification layer (their result + our thesis, converging)

Our surface-map thesis: quality = CLASSIFY BEFORE ACTING (write=provenance,
read=intent, threshold=self-noise). Vivarium's causal-provenance adds the 4th:
**claim TYPE (observational vs interventional vs derived)** — typed facts +
per-source trust cross the obs→interv barrier (+0.159, = interventional
oracle), and — crucial — **type WITHOUT trust is WORSE than blind (0.346)**:
the tag alone is forgeable/dominated by colluders. Complementarity again.

Implementation implication for VeriMem (F2+): a `fact_type` provenance
dimension routed by the SAME gate_router discipline, but — per their "next
frontier" (tag-forger) — the tag must be EARNED (retro-demotion/consistency),
never trusted bare. This is the same spoofability logic already noted in
gate_router.py for writer_role (safe there because it routes warning-only
heuristics; NOT safe if a bare tag routes answers).

## 5. Methodology to adopt wholesale (their honesty record)

Pre-registered predictions + kill-criteria + held-out virgin seeds +
falsified-and-kept-on-record (their tonight's record: 2 run=falsified, 2
verify=REFUTED, reported as such). VeriBench items must ship with their
kill-criteria and a published falsification log. That IS the brand.

## 6. What VeriBench is NOT built on yet (blockers before F3 build)

- F2 repo cleanup + total verification first (Aurelio's order F1→F2→F3).
- Only ONE competitor probed (mem0, small n, zero-API regime). Need
  engram-memory + MemOS runs on the same probes, larger n.
- The scoring λ needs a defended choice (cost model), not an arbitrary pick.
- Aurelio's product decisions pending: reconcile default, NLI judge, contested
  visibility — the bench should measure the SHIPPED defaults, not a lab config.
