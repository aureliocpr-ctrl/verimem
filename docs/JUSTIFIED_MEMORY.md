# Justified Memory — the 2027 thesis (Grounded Truth-Maintenance for LLM memory)

**North star: a memory that does not store strings, it maintains JUSTIFIED TRUE BELIEF.**
Every belief carries a justification (the source span that entails it + a grounding score);
a belief is ADMITTED only if source-entailed; and when its justification fails — the source
is superseded, contradicted, or goes stale — the belief is automatically RETRACTED or
downgraded. The memory can explain and audit the epistemic state of its entire belief set.

This is not marketing. It is a concrete, falsifiable engineering direction on an axis the
field has left open.

## The gap (verified against the 2026 literature, not assumed)
The SOTA agent-memory systems compete on RETRIEVAL ACCURACY and TEMPORAL GRAPHS, and that
metric is saturating:
- mem0 — LoCoMo 92.5%, LongMemEval 94.4% (~7k tok/query); Zep/Graphiti — temporal KG,
  LongMemEval 63.8% (GPT-4o); Letta/MemGPT — memory-as-OS; ByteRover 2.0 — LoCoMo 92.2%;
  MemMachine — LoCoMo 0.917, "ground-truth-preserving" by storing RAW episodes (avoids
  extraction-confab by NOT extracting — avoidance, not verification).
- A 2026 survey states the gap plainly: *"most RAG methods address retrieval-time grounding
  rather than ADMISSION-TIME control of what information is stored, and most LLM-native
  memory systems lack explicit safeguards against admitting unsupported content"*
  (arXiv 2603.07670). And: *"truth maintenance systems with justification-based belief
  retraction appear to be an emerging area rather than widely deployed."*
- The closest framework, SSGM (arXiv 2603.11768), blocks only LOGICAL CONTRADICTIONS with
  protected core facts — it does NOT require source-entailment, has no per-fact grounding
  score, no active retraction when a justification fails, and no corpus-level epistemic
  self-audit.

So the open frontier = exactly what Engram's write-path moat already establishes
(admission-time source-entailment, AUROC 0.97–1.0, model-general, R10–R13) PLUS the
truth-maintenance layer that no product ships.

## The concatenation (the novelty)
1. **Classical Truth-Maintenance / belief revision** (Doyle 1979 JTMS; de Kleer 1986 ATMS;
   AGM belief revision): beliefs are held *because of* justifications; retract the belief
   when the justification no longer holds; keep the belief set consistent.
2. **Admission by NLI-grounding** (Engram R10–R13): the JTMS "justification" is made
   concrete and verifiable = does the SOURCE entail the FACT (`fact_grounding_score` /
   `fact_grounding_span`). Only justified beliefs are admitted.
3. **Provenance-on-write**: each belief stores its justification (span + score) — auditable.
4. **Retraction triggers**: justification fails when the source is SUPERSEDED, CONTRADICTED
   (NLI, `semantic_conflict`), or STALE (`valid_until`/freshness). On failure → auto
   downgrade/retract, propagated.
5. **Self-audit** (`epistemic_health`): report the integrity of the whole belief set.

No prior LLM-memory system unifies admission-grounding + justification tracking + automatic
retraction + self-audit. It is "uncompeteable" by construction: you cannot bolt retraction
onto an ungrounded store — you need grounded justifications first, which is our moat.

## The new metric (a fresh axis, where retrieval-SOTA scores poorly)
Retrieval accuracy (LoCoMo/LongMemEval) is saturated and measures the WRONG thing for
trust. We introduce **Justified-Belief Integrity (JBI)**: over a corpus that evolves
(facts get superseded / contradicted / expire), the fraction of SERVED beliefs that are
currently JUSTIFIED — i.e. still source-entailed, not contradicted, not stale. A naive
store (and most SOTA) will serve superseded/contradicted/stale facts as truth → low JBI; a
truth-maintained store retracts them → high JBI. Companion: **stale-served rate** and
**contradiction-served rate** (lower = better). This is orthogonal to "did you retrieve the
right chunk" — it asks "is what you served still TRUE."

## Falsifiable experiment (pre-registered)
- **H-JM1**: a justification-tracked store with grounded admission + retraction achieves
  higher JBI than a naive store on an evolving corpus, WITHOUT lowering answer recall on
  still-valid facts.
- **Setup**: build an evolving fact stream: initial facts (with sources) → updates that
  SUPERSEDE some, contradictions that INVALIDATE some, time that STALES some. Query at the
  end. Compare: (a) naive store (serve latest/most-similar), (b) Engram with truth-
  maintenance (serve only currently-justified). Metric: JBI, stale-served, contradiction-
  served, valid-recall.
- **Falsification**: if truth-maintenance does NOT raise JBI, or raises it only by tanking
  valid-recall (over-retraction), the thesis fails — report it.

## Build plan (on top of the shipped moat)
- `engram/justified_memory.py`: a `Belief{proposition, justification(span, score), status,
  valid_until}`; `admit(belief, source)` (grounded gate); `retract_if_unjustified(beliefs,
  triggers)` (supersede/contradiction/stale → downgrade); `served_beliefs()` (only
  currently-justified). Pure core, LLM-injected, unit-tested.
- `benchmark/justified_belief_bench.py`: the JBI experiment (evolving corpus), deterministic
  where possible.
- Wire into the live store path as an opt-in layer over `grounding_gate` + `truth_recon`.

_Status: design (this doc) — grounded in the verified 2026 SOTA gap. Core build next._

---

## CORRECTION (R19, 2026-06-19) — adversarial verification downgrades two claims

A 5-agent web-grounded workflow stress-tested this design. Honest corrections:

1. **JBI is NOT a brand-new axis** (was overstated above). Prior art ALREADY measures its
   semantic core (penalizing served stale/superseded facts): **PrecisionMemBench**
   (arXiv:2605.11325, "Structured Belief State") with mutation assertions +
   `epistemic_status{active,superseded}`; **"When Facts Expire"** (CIKM 2025) temporal-
   validity classification; Zep/Graphiti edge invalidation. JBI's only unnamed part is the
   single corpus-wide integrity-RATIO framing. Use JBI as a convenient aggregate, NOT as a
   novelty claim.
2. **The novel core is `propagate()` (ATMS dependency-link retraction), not `maintain()`.**
   Supersession/contradiction-driven retraction (`maintain`) is what mem0/Zep/NeuSymMS
   already ship. The genuinely-unclaimed capability is withdrawing a belief because its
   SUPPORT belief failed (transitive `depends_on` cascade) — that is where the moat is.
3. **The combination still appears unclaimed** (admission-time source-entailment + JTMS;
   two 2026 surveys 2604.16548 / 2603.07670 call it an open blind spot) — but it is novel
   as a DESIGN; the empirical moat number is under re-test (R20: realistic, generator≠judge)
   because the 0.97-1.0 was on easy distributions (SNLI/templates) and our real-corpus FP
   ~0.77 is a counter-signal.
4. **Name collision**: ≥3 distinct "Engram" exist (ENGRAM 2511.12960 read-path retrieval;
   DeepSeek Engram; Engrama). Qualify the name externally ("Engram Justified-Memory").

---

## SHIPPED + MEASURED (R23–R24, 2026-06-19) — from design to a live, evidenced system

The thesis is no longer only a design. Two things now hold on the real system:

### 1. The lifecycle is LIVE (R23)
`engram.justified_memory` is reachable in production via the read-only MCP tool
`hippo_justified_audit` (registered in `mcp_server.py`, dispatched at line ~7683 — confirmed
by an O3 caller-verification critic, 2 hold / 0 fail). It maps a real Engram `Fact` to a
`Belief` (the real field `lineage_to` = parent edges → ATMS `depends_on`), runs
`maintain`+`propagate` over the live store (loaded with `include_superseded=True` so a
superseded foundation stays a graph node), and reports served vs would-retract/stale. A
cross-topic leak found by the critic (a topic-scoped load dropped a foundation and silently
served an unjustified fact) was fixed: the graph is built over the FULL corpus, `topic`
scopes only the report. The tool is read-only by design — it SURFACES the epistemic state;
DB-mutating auto-retraction is a separate opt-in needing an explicit mandate.

### 2. The exposure is real and large; the activation is honestly latent (R23–R24)
- **R23**: on the real 4312-fact corpus, `propagate` fires **0 times today** — the 7 actual
  supersessions happen to hit leaf facts. Reported straight: the +0.6 JBI from the design is
  a CONSTRUCTED-chain capability bound, not an observed-on-corpus gain.
- **R24**: but the dependency structure that makes `propagate` matter is already there and
  large. Of 4312 facts, **1821 (42%) are foundations** (others derive from them); superseding
  the most-depended-on foundation would leave **252** served facts un-justified; mean cascade
  over foundations **19.86**; total transitive-dependent exposure **36,158** edges. (Pure
  graph computation, cross-checked to equal `propagate` exactly.) This is the corpus's latent
  **justification-debt** — invisible to retrieval-only SOTA (mem0/Zep/Letta serve by
  similarity/recency, no justification tracking), and exactly what grounded truth-maintenance
  is built to discharge the moment a foundation is superseded or contradicted.

**Honest caveat (carried, not hidden):** supersession ≠ refutation in every case — a derived
fact can survive its foundation's replacement. So the cascade is the "lost stated
justification → must re-examine" set (an upper bound on must-retract), which is precisely why
`propagate` moves beliefs to retract/re-justify rather than to "false". The novel,
real-data metric — **justification-debt = transitive-dependent exposure of the live belief
graph** — is one the retrieval-saturated SOTA does not compute at all. That, not a leaderboard
point, is where "the 2027 memory" is uncompeteable: it tracks whether what it serves is still
JUSTIFIED, and it can name, on a real corpus, exactly how much of what it holds is one
supersession away from being unjustified.

---

## CORRECTION (R26, 2026-06-19) — adversarial workflow #2 + my own verification

A second 5-agent adversarial workflow (prior-art/metric/empirics/moat), with findings I
re-verified against the real corpus, forces three honest retractions of claims made above:

1. **RETRACT "justification-debt is a metric the retrieval-saturated SOTA does not compute at
   all."** It reduces to transitive-closure size (Cohen 1997) / data-lineage "blast radius" /
   change-impact "ripple effect"; belief-over-provenance-graph propagation is prior art (IPAW
   2018; PROV-AGENT 2026). Novel = the application to an LLM grounded-belief graph, not the
   metric.
2. **RETRACT the R24 reading "how much of what it holds is one supersession away from being
   unjustified."** VERIFIED on the corpus: `lineage_to` is a narrative/session-successor
   pointer (95% cross-topic `clp --lineage-to auto` chain links), NOT a logical-derivation
   edge. So the cascade is *narrative-descendant* exposure, not justification-debt;
   superseding a session predecessor does not strip a successor's justification. The graph
   math (BFS==propagate) is correct; the edge SEMANTICS are wrong. Engram records no typed
   logical-derivation edge yet — which is also why propagate fires 0× (R23). Lever: add a
   typed derivation edge to the write-path, then re-measure.
3. **RETRACT "the write-path gate is the moat."** The gate alone is commodity NLI faithfulness
   verification (MiniCheck/Lynx/AlignScore/RAGAS), replaceable by a 7B head more cheaply. The
   defensible moat is the COMBINATION — admission-grounding FEEDING automated transitive
   retraction — a 6–12mo product-lead architecture (closest deployed peer Kumiho, arXiv
   2603.17244, has the graph but a MANUAL cascade), with both ingredients conceded prior art.

The thesis survives as exactly one narrowed, honest claim: *admission-grounded justifications
feeding an automated transitive (cascade-to-fixpoint) belief-retraction*, implemented and live
but currently dormant and computed on the wrong edges — the concrete work to make it real is a
typed derivation edge, not more theory.

---

## FINDING (R28, 2026-06-23) — auto-populating `derives_from` is FALSIFIED (no safe site)

R26 named the lever as "add a typed derivation edge to the write-path, then re-measure". A
9-agent map+falsify workflow (5 write-path subsystems mapped in parallel, every candidate
site adversarially verified against two hard criteria, then synthesised) tested whether ANY
live write-path site can AUTO-populate `derives_from` at high precision. **Verdict: STOP —
0 of 3 candidate sites survived.** Independently spot-checked and confirmed:

- **Merge** (`facts_merge.merge_facts`, `facts_topic_merge`): the originals are forgotten/
  superseded after the merge → the parents do NOT persist, so an edge to them is useless for
  `propagate` (it needs live parents). Also dedup, not truth-derivation.
- **Dream/adopt** (`dream.adopt_dream`): operates on the SKILL library, not the fact corpus →
  no fact-derivation site at all.
- **Consolidation**: aggregation/summary, not a logical truth-dependency strong enough to
  justify transitive retraction (a summary can survive one source being wrong).
- **Symbolic inference** (`symbolic_inference.forward_chain`, `reasoning.reason_about_task`):
  the textbook ATMS case — but it COMPUTES conclusions and does NOT persist them as facts, so
  there is nothing to tag.
- **Recall→answer→store** (`client.add`/`recall`): stores what the caller passes; no
  auto-synthesis of a derived fact from persisting cited sources.

So auto-population would reproduce exactly the R26 false-transitive-retraction failure
(narrative/dedup edge mistaken for logical derivation). **The correct boundary is the one
already shipped**: the explicit `hippo_remember(derives_from=...)` param (authoritative,
true-by-construction because the caller declares the derivation) PLUS the read-only
`hippo_justified_audit`. This is a verified NEGATIVE result — reported, per the falsifiable
contract above, rather than forced.

Baseline measured the same day (read-only, on the live 4588-fact corpus): **0 facts carry a
`derives_from` edge → `propagate` is provably dormant**; the only retractions are the 12
leaf supersessions that `maintain` already handles. `propagate`/ATMS remains a correct,
unit-tested capability with no live data to act on **by design**, not by oversight.

### The safe adjacent lever (R28 → next): CONTRADICTION as a live retraction trigger
The design lists four retraction triggers (supersession, **contradiction**, stale,
dependency-cascade). The live audit wires supersession + stale + cascade, but NOT
contradiction. Contradiction is the one remaining trigger that is **safe** (an NLI
contradiction is a true epistemic signal, not a guessed edge), **live-relevant** (the
real-corpus FP retest finds ~5 genuine contradictions today), and **connected** (reuses
`semantic_conflict`). Making contradicted served-beliefs `contested` (and thus not served as
truth) advances the thesis on real data WITHOUT the `derives_from` precision risk.
