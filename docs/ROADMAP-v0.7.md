# Verimem v0.7.0 — "Nothing silent, nothing mislabeled"

Plan of record, 2026-07-18. Born from a 3-round external adversarial review
(kimi-k3 + glm-5.2 via VeriAgent, effort=high) **cross-checked against the source
code**. Both models independently scored the product **6/10**; both converged on
the same #1 risk and the same roadmap; the cross-examination round then corrected
both roadmaps. Every model claim below was verified against code — refuted ones
are marked so we don't build fixes for non-problems.

## The one-line truth
The engine is real and the thesis is differentiated, but the word **"verified"**
currently over-promises: it is applied to the CE default tier (a ~92-93% probabilistic
filter with a measured 7% Spanish entity-substitution escape) and to receipts that
only prove a path **resolves** (not that its content **supports** the fact). The
default tier's failures are **silent**. v0.7.0 makes the label honest and nothing
the gate decides silent. This is a "secure-defaults + honest-labels" pass, NOT a
re-architecture.

## STATUS — 2026-07-19 (in progress)
- **Phase 0.1/0.2 SHIPPED** (branch `rename/verimem-total`, CI green all platforms):
  every write returns an `adjudication` receipt {disposition, evidence_class, judge,
  score, threshold, margin, reason, confidence_tier}; GateResult carries the
  judge-of-record + threshold (previously discarded); quarantine is a visible,
  reasoned verdict (incl. the store-time injection screen). Commits 57a392c ·
  6fb2565 · ba772f1. Reviewed by kimi-k3 + glm-5.2 (7/10 both); every finding
  verified against code — 3 refuted (interactive=Claude-LLM; judge⇔score invariant
  holds; modal case already has advice), 3 fixed, 3 → roadmap (below).
- **Phase 0.3 (CE band) — code done, default OFF** (3da25b2 · 6434e86, pre-push):
  `confidence_tier` {grounded/review/ungrounded/unverified}; two-threshold CE band
  (tau_lo=40, tau_hi=80) behind `VERIMEM_CE_BAND_ENFORCE`. CALIBRATED on the real
  CE: true entailments (incl. abstractive/paraphrase) score ≥90 (n=14, min 90.3);
  the entity-substitution escape is bimodal (65/68 catchable, one at 96 not).
  MOAT-BENCHMARK proof: enforce OFF escape 6.2% → ON 1.8%, with 112/112 entailed
  still admitted (0 false-block). Honest bound: the ~96 escape + plausible-inference
  confabs (97-99) still need the llm judge — the band is a REAL but PARTIAL fix.
- **Realness ladder (honest).** External review = 6/10 today. Phase 0+1 (code) → a
  defensible 8–8.5. A REAL 9 is NOT a code sprint: it needs third-party-reproduced
  benchmarks, external anchoring in production, and months of measured judge drift.
  Build the harnesses that make 9 reachable; do not claim 9 until earned.

## VERIFIED-REAL gaps (build these)
1. Gate is bypassable — a direct `sqlite3` INSERT skips the moat (library, no enforcement).
2. Receipts verify RESOLVABILITY, not content — no content hash; file edit silently invalidates.
3. Judge not recorded per decision — only `grounding_score`; no model/version/temp → silent provider drift.
4. No tamper-evident chain — only SQLite crash-consistency. **A hash chain INSIDE the writable DB is theater** (owner has the key → rewrite+re-sign). Needs a key OUTSIDE the DB + an EXTERNAL anchor, or don't ship it.
5. No encryption at rest.
6. Scale unproven >3k facts; single-node SQLite; ~113 ms/write (CE) = swarm serialization point.
7. `source_trust` EXISTS but OFF by default (poisoning exposure out-of-box).
8. Moat evidence coverage-limited (only NUMERIC contradictions) + self-reported (no public harness).
9. Quarantine is SILENT (caller never told what was blocked) → memory-DoS "griefing" is possible.
10. Judge prompt-injection — cited SOURCE text is attacker-influenceable.
11. GDPR forget incomplete — physical bytes + EMBEDDINGS + WAL + backups; no crypto-shred; no export (Art.15/20).
12. Cross-fact contradiction NOT on the write path (gate is source⊢fact only). `ContradictionStore`+scan exist but unwired.
13. **NEW (cross-exam, verified): no access-control WITHIN a tenant** — `key = tenant`, no per-agent roles. Any "show the conflicting fact" visibility fix becomes an **extraction oracle** unless scoped.

## REFUTED by code (do NOT build)
- "Consolidation/dream/rollup mint facts that bypass the gate / poison-laundering" — FALSE. They operate on **skills/episodes/topic-clustering**, not fact-minting. (Both models repeated this; code refutes it.)
- "source_trust default-ON silently mass-quarantines new users" — FALSE. Unknown source gets neutral prior **0.5** > floor **0.25** → admitted. (The "measure cold-start first" caution is still sound.)
- Already-exists (round-1 false "missing"): consolidation, metrics/dashboard, decay + quarantine rehabilitation, source_trust/corroboration, per-tenant DB isolation, ContradictionStore.

## PHASE 0 — days ("nothing silent, nothing mislabeled"). START HERE.
0.1 **Adjudication receipt on every write** → return `{disposition, evidence_class, judge_id, score, margin}` to the caller. Quarantine becomes a visible verdict, not silent exclusion. (`verimem quarantine list/review/resolve`.)
0.2 **Judge-of-record**: persist `judge_backend, model, version, temperature, threshold, margin` on every gate decision (new `gate_decisions` row + FK from facts).
0.3 **Honest tier names + the DECISION MATH, not just the label.** Reserve `verified` for judge-attested + content-bound receipt. CE tier → `plausibility_gated`. Ship a **two-threshold band** on the CE: `≥τ_hi admit / ≤τ_lo reject / middle → review-quarantine (or escalate to llm if configured)`. **Renaming without the band still leaves the 7% poison — fix the math.** Expose `confidence_tier` on every recalled fact; `verimem stats` shows tier distribution.
0.4 **Content-bound receipts (start)**: hash the MINIMAL cited span (line range), store it; on audit/sweep (NOT per-recall — read-path I/O) compare → `stale` is a SEPARATE orthogonal signal, tier stays a static historical claim. (Full auto-repair/provisional-upgrade → Phase 1; honest effort = 2-3 weeks total, split it.)
0.5 **`source_trust` ON in observe/log-only first**, measure false-block on fresh tenants, THEN promote to gating.
0.6 README/brand: kill "100% certain / verified" for the default; publish the CE error band (7% ES + overlapping distributions). (Partly done this session; finish it.)

## PHASE 1 — weeks ("wire the moat")
1.1 Contradiction check ON the write path via **bi-temporal supersession**: same-source contradiction → **supersede** (tombstone old, keep valid-time) NOT quarantine-both; cross-source → quarantine the LOWER-tier one for review. Candidate recall needs an entity+predicate **pre-filter** and a **bounded k** against the 113 ms budget. Griefing detector (per-source contradiction-rate alert); quarantine-under-dispute EXEMPT from decay.
1.2 **Tamper-evidence done right**: coverage-audit (facts lacking a valid gate_decision → auto-quarantine + alert) with the decision signed by an **HMAC/Ed25519 key held OUTSIDE the DB**; daily external anchor (RFC-3161 TSA / transparency log / signed git remote). Chain-without-external-key/anchor = do not ship.
1.3 **Intra-tenant authz**: per-agent identity + RBAC on write/read/forget; scope the adjudication-receipt visibility so `conflict_reason` is NOT an extraction oracle.
1.4 Public reproduction harness + HARD contradiction classes (temporal / hedged / coreferential / conditional) + messy-query abstention benchmark + measured agent-level cost of over-abstention.

## PHASE 2 — weeks ("adversarial + compliance")
2.1 Judge prompt-injection hardening: pass judge only the **minimal evidence window**, structured/constrained output, delimiters as defense-in-depth, **multilingual** injection pre-scan (NOT English-only), dual-judge on flagged sources, injection red-team corpus. (CE-as-classifier is more injection-resistant than the LLM tier — honest selling point, but ONLY for source-verification, not contradiction-detection where an input is attacker-controlled.)
2.2 GDPR (unconditional, not "if EU"): crypto-shredding envelope (per-subject KEK → forget = destroy key). Honest open problems to state, not hide: ANN search over encrypted vectors (rebuild-on-forget), key custody NOT on the same FS as the DB, WAL entries written pre-shred, receipt `source_excerpt` + audit log are NEW PII copies that MUST be in the forget path. Art.15/20 export.
2.3 Encryption at rest (SQLCipher / per-tenant key). Honest scale bound published (~9 w/s per tenant; swarms parallelize across tenants; hot-tenant is the real limit); write-queue batching. Postgres → v0.8.

## Score trajectory
NOW 6/10 (external, verified). After Phase 0+1 → credible 8–8.5. 9+ needs
third-party-reproduced benchmarks, external anchoring in production, and a year of
measured judge drift.

## Discipline (unchanged)
TDD RED→GREEN; atomic commits (env-watcher reverts .py between tool calls);
ruff clean + full CI green before declaring; merge/tag/PyPI = Aurelio's call after
he tests. Branch `rename/verimem-total` (also carries the unfinished source-brand
rename debt — 225 "Engram/HippoAgent" in docstrings + the `HippoAgent` class →
`VerimemAgent` w/ alias; see spawn_task chip).
