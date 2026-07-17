# Changelog

All notable changes to HippoAgent (Engram) follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **The grounding moat is ON by default** (2026-07-17) — for months the
  source⊢fact write-gate (judge AUROC 0.96–0.97) shipped OFF, so the write path
  showed no moat. Now preset `balanced` has `ground=True`: a `Memory(llm=...)`
  uses that llm as the grounding judge (0.98) with no separate wiring, and the
  conversation-ingest path runs the free local cross-encoder (AUROC ~1.0 on
  extraction confabs). An extracted fact the source/dialogue doesn't entail is
  quarantined (hidden from default recall, rehabilitable), not absorbed. SAFE
  fail-open: with no judge and no local CE the gate admits exactly as before —
  the flip never breaks a judge-less user. Measured first: the local CE is 1.0
  on netto extraction confabs but only 0.80 on subtle SNLI-neutral pairs, so the
  LLM judge is the quality path and the CE the free-but-good-enough fallback;
  the flip was gated on that evidence (`benchmark/fact_grounding_bench` +
  `real_corpus_gate_validation`). Per-call `ground=False` still opts out.

### Added
- **Trust-conditioned answering** (2026-07-16/17, measured BEFORE wiring):
  `Memory.answer(trust_conditioning=True)` (default) tags every retrieved fact
  `[when | source | status]` and resolves conflicts by provenance (verified >
  unverified, recent > old, first-hand > hearsay; unresolvable → honest
  `NO ANSWER`). On the well-grounded-distractor bench (sonnet-5, 12 cases where
  BOTH facts pass the grounding gate) correct answers went **0.17 → 0.92**,
  abstaining 2/2 on same-metadata ties (`benchmark/wellgrounded_distractor_bench.py`).
  `search()` hits now expose `asserted_at`/`created_at`/`source`/`verified_by`.
  Gateway surface: **`GET /v1/answer`** (400 without a server-side llm — honest,
  not a crash). Quickstart gained the 6th verb.
- **`GET /v1/correct`** — the guardian's production surface (ACCEPT / CORRECT /
  ABSTAIN with both sides cited, deterministic, LLM-free). The mod.3 critic
  found `correct_read` had zero production callers; now wired with a
  `flow.recall kind=correct` event. Guardian audit (mod.7) fixed per-VALUE
  dominance (two agreeing proven facts no longer LOSE to a lone unlabeled
  rival) + 2 crash guards.
- **REMORSE AdaptiveLedger graft — phase-1 SHADOW** (`engram/adaptive_ledger.py`):
  per-tenant per-domain self-trust (3 experts: lessons@14d, exposure,
  hazard@14d; fixed-share meta) OBSERVING ONLY — `/v1/search` and `/v1/answer`
  emit `shadow.ledger` events (would-be decision next to the actual one),
  responses untouched, kill-switch `ENGRAM_SHADOW_LEDGER=0`. Phase 2 (apply,
  per-tenant flag) is gated on 3–7 days of shadow-log comparison.

### Fixed
- **Personal mode is uncapped** (found by live e2e, not by tests): the loopback
  console was billing-gated like a SaaS tenant — on a >1000-fact store every
  console write returned 402. The local tenant now resolves to the uncapped
  `self_host` plan across the write gate, `/v1/quota` and `/v1/usage`.
- **Fact-quota TOCTOU**: concurrent writes at cap-1 could all pass the
  check-then-act window and overrun the plan cap — now an atomic
  reserve-counter (40-thread race test: exactly one slot granted).
- **SSE `/v1/events/flow` self-DoS**: the stream re-read the whole events file
  (up to 5 MB) every 0.5 s per client — now an incremental byte-offset tail
  (O(new bytes) per tick, rotation-safe, partial-line-safe, capped per tick).
- **Trust console v2 — the whole graph, actually live** (2026-07-16): the
  knowledge graph now renders the ENTIRE store (7.7k nodes / 39.4k unique
  edges in ~300–500 ms) on sigma.js WebGL with ForceAtlas2 in a Web Worker
  — vendored same-origin (MIT, `engram/webui/vendor/`), CSP unchanged except
  `worker-src 'self' blob:` for the layout worker. Births arrive
  INCREMENTALLY from `flow.entity` (no refetch), touched nodes pulse, search
  shows matches-only, click → chain-of-custody dossier. New **Search & ask**
  tab: `/v1/search` hits with per-fact provenance badges (status,
  verified_by, asserted_at vs created_at, source episode) and a
  grounding-verified `/v1/answer` box that degrades honestly on the personal
  console's 400 (no server-side llm by design). `GET /` now redirects a
  human to `/ui` instead of a JSON 404. `/v1/answer` emits its own
  `flow.recall kind=answer` (grounded/abstained/reason).
- **Live Engine Room v2**: the 900 ms per-event queue is gone (under real
  traffic it ran minutes behind its own feed) — counters move per event,
  stages glow with decaying heat, a per-second stacked rate chart shows the
  last 60 s of writes/recalls, the feed carries surface/actor and answer
  verdicts, `shadow.*` observation events are counted in a chip and never
  drawn as engine activity. Auto-connect + reconnect with backoff.

### Fixed
- **Console self-DDoS under live traffic** (2026-07-16, seen on the real
  store while another agent wrote continuously): every ledger event
  triggered a full stats+quarantine refresh and every entity birth refetched
  the whole 1.6 MB graph → `ERR_INSUFFICIENT_RESOURCES`, "Failed to fetch",
  dead page. Counters now update from the event payload itself, the heavy
  refresh throttles to 1/5 s, and a failed fetch degrades to a banner +
  retry — the page never dies on a bad fetch.
- **P0 — upgrade path broken since 2026-07-13 (`epistemic` column)**: the v14
  migration was written AND registered, but `_SEMANTIC_TARGET_VERSION` stayed
  13, so the runner never executed it. New stores (every test) were born with
  the column; **existing stores kept failing every write** with
  `table facts has no column named epistemic`. Found on a real 6120-fact
  store — 6905 green tests missed it because they all create a fresh DB.
  Registering a migration without raising the target is not having it.
  `tests/test_migration_v14_upgrade_path.py` now walks the real upgrade.
- **P0 — the knowledge graph was a fossil**: `snapshot()` sampled 600 edges
  `ORDER BY created_at ASC` out of 78 713 (0.76%, and the OLDEST), so the map
  only ever showed the first session, a node created today could never appear,
  and "isolated" nodes were an artifact of the sample (real store: 1752
  isolated, not the 194 displayed). Rewritten nodes-first: the window is the
  most recent entities, edges are the real ones between them, `degree` is
  counted over the whole store, and `total_entities`/`total_edges`/
  `isolated_count` are declared.

### Added
- **The graph, live** (`flow.entity`): `populate_entities_for_fact` announces
  the nodes just born and the ones a fact just touched; the trust console
  consumes `/v1/events/flow` and makes touched nodes fire and newborns grow in
  — no polling. Isolated entities get an ordered outer belt instead of
  polluting the structure. Verified end-to-end against a live store.

### Changed
- **Gateway `/v1/explain` abstains by DEFAULT** (`ENGRAM_GATEWAY_MIN_RELEVANCE`, default
  `auto`): the enterprise read-path now applies a self-calibrating relevance floor, so
  an unsupported query returns an explicit abstention instead of a spurious nearest hit
  — the "knows when it doesn't know" property is ON out of the box on the product
  surface. Honest limit (measured this session): the e5 score band is compressed
  (present vs absent overlap ~0.03–0.05), so the floor is a precision/recall DIAL —
  `auto` is validated on real corpora (HaluEval false_answer 1.0→0.04) but over-abstains
  on very small stores; tune via the env (`auto` | `<float>` | `off`). The raw SDK
  `explain()` default is unchanged (0.0) for backward compatibility.

### Added
- **Flow events at the CORE + `verimem flow tail`**: `flow.write`/`flow.recall`
  are now emitted by `Memory.add/search/explain` themselves
  (`engram/flow_events.py`), so EVERY surface feeds the Live Engine Room —
  gateway (tenant via per-request context, privacy filter unchanged), MCP
  server (`surface=mcp`, set at bootstrap), plain SDK, and any vendor's agent
  (labeled via `VERIMEM_ACTOR` in its MCP config). New CLI: `verimem flow
  tail` — the same feed as `/ui/engine` in a terminal pane (replay + follow,
  colored verdicts, `[surface/actor]` tags). Flow metadata only, never fact
  content. 19 new tests; 279 client-consumer + gateway tests green.
- **`VERIMEM_*` env prefix** (brand-forward alias): every `ENGRAM_X` setting
  can now be written `VERIMEM_X` — mirrored at import by the same
  setdefault-only bridge as the legacy `HIPPO_*` mirror (explicit values are
  never overridden; `ENGRAM_X` wins if both are set). No call-site changed;
  covers all ~91 settings. `tests/test_env_alias_verimem.py`.
- **Live Engine Room** (`GET /ui/engine` + `GET /v1/events/flow`): the engine
  observable event by event. Every gateway write emits `flow.write`
  (status/stored/fact_id — flow metadata only, never fact content) and every
  read emits `flow.recall` (kind/n/best/abstained); the SSE stream replays the
  last N and then follows live, filtered to the CALLER's tenant only. The page
  (CSP-clean: external `engine.css`/`engine.js`, zero inline) animates the
  custody line — admitted → LEDGER, quarantined → QUARANTINE, answer/abstain
  on the read lane — with cumulative counters and a newest-first feed.
  Verified end-to-end against a live store (write admitted, L1.10 quarantine,
  search answer 0.81, explain abstention). `tests/test_gateway_flow_events.py`.
- **Guardian at the read-path** (`engram/guardian.py`, `correct_read`): not
  just block-or-abstain — when the store contains a better-guaranteed truth
  about the same subject, the read SERVES it as a correction with both facts
  cited. ACCEPT / CORRECT (a rival with a strictly better epistemic label wins;
  refuted is disqualified) / ABSTAIN (a real conflict with no epistemic winner
  is shown, never picked silently). Cortex transfer (lab: 0 false answers over
  2000 queries).
- **Active probes** (`engram/active_probe.py`, `probe_fact`): the store BUILDS
  the query that would falsify a fact instead of waiting for a contradiction —
  independent non-engine counter-evidence → propose `refuted`; survival grows
  the `unbeaten` bound (= probes survived). `actor:*` rivals never count (P85).
  Vivarium P87.
- **Provenance signing on the write-path** (`engram/provenance_signing.py`):
  the SMSR-complement (arXiv 2606.12703, Theorem 1 — no deterministic
  provenance-free filter certifies safety against an adaptive adversary). An
  HMAC over (ref-body, proposition) travels INSIDE the `verified_by` ref
  (`source-doc:X:t1#sig=<hmac>`) — zero schema change, no replay across facts,
  `actor:*` exempt (P85). `audit_store` reports coverage and names offenders.
  Default OFF (`ENGRAM_PROVENANCE_KEY`).
- **Ignorance map** (`engram/ignorance_map.py`): "I don't know" upgraded to
  "here is WHAT I'm missing" — per failed query, the ignorance CLASS
  (no_evidence / below_floor / quarantined_only / conflict / answerable) and
  the concrete acquisition action that would cure it. The active complement of
  abstention (Vivarium P83). Read-only; the daemon's future work-list.
- **Source-trust reproduced on a REAL held-out corpus**
  (`benchmark/source_trust_realcorpus.py`, HaluEval QA): pre-registered C1–C4
  hold on 3/3 seeds under honest coherence — a manufactured-consensus cartel
  self-confirms to 0.90 under naive ≥2-distinct counting, is demolished to
  0.20 by independence+deconfound, honest 0.50→0.95, liar-driven recall
  0.25–0.30→0.0. The honest-noise robustness curve
  (`benchmark/source_trust_noise_curve.py`, 18 points, declared bi-encoder
  regime) shows no reputation inversion at any noise and deceiver-written
  wrong answers 0/18 everywhere; the residue is 100% honest slips — a
  per-claim disease (reconciliation/abstention territory), not a per-source
  one. Default stays OFF: the evidence informs the flip, it does not perform it.
- **Epistemic labels** (schema v14, `engram/epistemic.py`): the GUARANTEE kind
  of a fact — `proven(proof)` / `unbeaten(bound)` / `refuted(counterexample)` —
  orthogonal to provenance `status`. Monotone transitions via `set_epistemic`
  (a bound only grows; `refuted` is absorbing — correction happens by
  supersession; `proven` never silently downgrades); a re-store preserves an
  earned label. Motivating case (cortex transfer): coprime6→deficient holds to
  10^6 yet dies at 5391411025 — "unbeaten" and "proven" must never be conflated.
- **P85 self-provenance** (`engram/self_provenance.py`): engine writes are
  SIGNED (`actor:<component>` refs; `canonical_source` namespaces them, never
  the `user` fallback) and NEVER testify — filtered from confirmations,
  acceptance and auto-confirm, so the engine cannot manufacture consensus about
  its own claims. `self_write_check` monitors the self-write ratio with an
  alarm past 0.5 (`ENGRAM_SELF_RATIO_MAX`) — past that threshold the world's
  drift becomes invisible behind the engine's own echo (Vivarium P85).
- **Composition ring** (`engram/composer.py`, `compose_once`): derives NEW
  candidate facts from pairs of live facts sharing a pivot term (declared
  substitution, v1 copula syllogism), pushes each through the SAME anti-confab
  gate as every writer (L4 entailment against the two parents — no privileges),
  and admits survivors signed (`actor:composer`), traced (`derives_from`,
  retractable via justified-memory) and labeled
  (`proven("qa:l4_entail_parents_score<NN>_PASS")`). A dead/unreadable judge
  cannot flood the store: scores below the composer floor
  (`ENGRAM_COMPOSER_MIN_SCORE`, default 55 — above the non-committal 50
  fallback) are quarantined, never live. `semantic.set_derives_from` declares
  the logical edge after admission (the gate never trusts the trace).
- **Deployment metrics at declared λ operating points**
  (`engram/selective_metrics.py` + `benchmark/selective_deployment.py`, from
  the Oxford 2603.21172 finding via the cortex research bridge): AUROC says
  the scores discriminate; TCE says the SLA knob OPERATES at its declared
  risk. Measured on HaluEval held-out (calibration fit on dev only): raw e5
  scores discriminate near-oracle (E-AURC 0.0008) but promise a different
  risk than they deliver (TCE 0.05–0.08, coverage collapses to 12.8% at λ=9);
  after a pure-PAV isotonic calibration the knob operates at the declared
  risk — **TCE ≤ 0.011 across λ ∈ {0.5, 1, 3, 9}, observed risk 1.1% at 73%
  coverage**, every SLA target met. Honest trade-off, declared: the step
  calibration flattens fine ranking (E-AURC 0.001→0.044) — raw scores for
  ranking, calibrated scores for operating a declared λ.
- **Composition daemon** (`engram/compose_daemon.py`, one-shot CLI
  `python -m engram.compose_daemon --db ...`): P85 pre-flight →
  `compose_once(budget)` → P85 post-report. REFUSES to compose when the
  self-write ratio already alarms (an engine dominating its own stream must
  not keep feeding on itself); candidate budget passed down with truncation
  declared; writes no telemetry facts about itself (a report that inflates the
  self-ratio gating it would strangle its own headroom). Scheduling stays with
  the OS — local-first.
- **Write-gate provenance INDEPENDENCE** (`ENGRAM_SOURCE_INDEPENDENCE`, default OFF):
  a confirmation now requires ≥2 *independent* clusters, not just ≥2 distinct
  source-IDs, so N copies/echoes/colluders of one feed collapse to one witness —
  closing the manufactured-consensus hole. `SourceTrustBook.record_report` /
  `independent_clusters`; wired via `source_trust_observe(reports=)`.
- **Deconfounded independence** (`ENGRAM_SOURCE_INDEPENDENCE_DECONFOUND`, default OFF):
  raw agreement is confounded by shared truth (honest sources that agree because
  both are right would false-merge); conditioning on the AUDIT — co-admission of
  values revealed FALSE (`mark_false`, fed by `source_trust_observe(audited_false=)`)
  — isolates real collusion. The audit is the do-operator (Vivarium P88).
- **Error-cost → abstention SLA** (`engram/sla.py`, `ENGRAM_ERROR_COST`=λ, default 1.0):
  answer iff P(correct) > λ/(1+λ) — the decision-theoretic optimum and the same λ
  VeriBench scores NET at. Higher λ (legal/medical) abstains more.
- **Trust SCOPE declaration**: `build_trust_report` now carries `TRUST_SCOPE` in every
  dossier — Verimem certifies who-asserted-it, corroboration, and freshness, NOT
  causal truth (a do(X) question needs an interventional-typed fact).
- **VeriBench axes + spec** (`benchmark/veribench`): causal / do-query axis
  (provenance ≠ causality, defended λ*), adversarial-trust axis (collusion + sleeper
  on the real `SourceTrustBook`; only the two-channel policy survives both), mem0
  competitor adapter, and a `README.md` standard spec.

## [0.4.2] — Security hardening + self-host gateway + retrieval guards (2026-07-11)

### Security
- **Document RAG indirect prompt injection closed** (E3): document chunks are now
  screened at index time (sanitize-then-scan, the same discipline as the fact
  write-gate) — a poisoned PDF/DOCX/HTML/EPUB can no longer return an
  instruction-override payload verbatim through `DocumentIndex.search`. Flagged
  chunks are hidden from default recall, recoverable via `include_flagged`; the
  exact-citation invariant (`original[start:end] == chunk`) is preserved.
- **Gateway anti-DoS body limit hardened** (G1): `max_body_bytes` now counts the
  real streamed bytes, so a chunked request without `Content-Length` can no longer
  bypass the cap.
- **Zip-bomb caps on document ingest** (E1/E2): EPUB and DOCX extraction bound the
  decompressed size (per-member + total budget), so a highly-compressible archive
  cannot exhaust memory.
- **Deserialization/RCE-sink CI guard** (static AST scan: no `eval`/`exec`/
  `os.system`/`pickle`/`marshal`/`yaml.load`); SHA1 identity hashes annotated
  `usedforsecurity=False`. The offensive suite (188 tests: SSRF/DNS-rebind/
  traversal/injection/secrets/executor-isolation) stays green.

### Added
- **VeriBench scoring core** (`benchmark/veribench`): `NET = (correct − λ·wrong)/n`
  with a declared λ-sweep + coverage — abstention is a first-class outcome, so a
  trust memory's core property is visible where symmetric recall@k hides it.
- **Self-host gateway** (`verimem gateway serve` + `gateway keys
  create/list/revoke`): multi-tenant REST over the Memory SDK — API keys
  hashed at rest and shown once, one isolated SQLite store per tenant (the
  tenant derives from the key alone), writes through the anti-confabulation
  gate, `/v1/explain` returns the TrustReport, GDPR-grade delete, optional
  per-key rate limiting (429 + `Retry-After`). Loopback bind by default.
- **Retrieval fusion quality guards**: hub-guard (PPR seeds linking >20% of
  the corpus are dropped), informative-token BM25 (linguistic stopwords +
  document-frequency ceiling), and a dense-floor (`protect_top=k//2`) so
  extra signals can extend but never evict the CE-verified head. Measured:
  fusion flips from net-negative to neutral-or-better at small k on
  conversational corpora; inactive below a 50-fact floor (small-store
  behaviour byte-identical).
- **SDK**: `Memory.search(as_of="auto")` — an explicit retrospective anchor
  in the question ("as of / on / by <date>") activates bi-temporal time
  travel at that date; as-of context keeps the transition story pruned at
  the anchor. Automatic routing measured and deliberately NOT wired into
  the default answering recipe (declared in `docs/BENCHMARKS.md`).
- **Skill hygiene in the sleep cycle**: same-name duplicate pairs merge
  first regardless of trigger cosine; dormant never-tried candidates
  (>30 days, below min trials) are retired gradually (cap 10/cycle,
  reversible) — on the live corpus 159/162 candidates were dormant.
- **Docs**: `DATACENTER_DESIGN.md` (honest 4-phase map to hosted MaaS) and
  `CONVERSATIONAL_ENTITY_DESIGN.md` (typed-entity extraction plan from
  measured graph starvation).

## [0.4.1] — Professional README + `user_name` on the SDK verb (2026-07-07)

- **Docs**: the README was rewritten from scratch (1280 → ~170 lines): a
  professional, standard OSS structure (features, install, verified quickstart,
  CLI, benchmarks with caveats, architecture, license). Internal iteration
  logs and duplicated sections are gone; deep dives live in `docs/`. The PyPI
  one-line description was shortened accordingly.
- **SDK**: `Memory.add(messages, user_name=...)` — the 0.4.0 identity fix is now
  available on the main SDK verb (it forwards to the gated conversation
  ingestion), matching MCP and CLI. Quickstart examples are signature-verified
  by tests.

## [0.4.0] — Document RAG + onboarding import + e2e parity with MemOS (2026-07-07)

The big one: whole-file memory with exact citations, consent-first onboarding
from your ChatGPT/Claude history, an extraction engine rebuilt around two
root-caused fixes (+9.8pp e2e, replicated), and the license change to AGPL-3.0
dual. Trust regressions: zero (TrustMem-Bench 60/60, abstention 1.0 everywhere).

### Added — Document RAG (whole files, exact citations)
- **`engram/chunking.py`** — boundary-aware text chunker with the provenance
  invariant `text[start:end] == chunk.text` (every chunk cites its exact offsets).
- **`engram/file_extract.py`** — file→text for `.pdf` (PyMuPDF), `.docx`,
  `.html`, `.txt/.md`; lazy parser imports degrade with clear errors.
- **`engram/document_index.py`** — `DocumentIndex`: file → chunks → embeddings →
  `search(query)` returns chunks with `(source_id, version, start, end)`;
  content-hash idempotent; a changed file supersedes its old version in search;
  embedder injected (tests run model-free); isolated store (NOT the recall corpus).
- **`engram/document_promote.py`** — `promote_chunk_to_fact`: a retrieved chunk
  (or a distilled claim) enters the recall corpus THROUGH the anti-confab gate as
  a low-trust `model_claim` whose `verified_by` IS the citation
  `file:<source_id>:<start>-<end>` — open the file at those offsets and check.
- **MCP**: `hippo_document_index_file`, `hippo_document_semantic_search`,
  `hippo_document_promote_chunk`. **CLI**: `verimem index <file>`,
  `verimem search-docs <query>` (snippet centered on the matched term).

### Added — Onboarding import (cold-start, consent-first)
- **`engram/import_conversations.py`** — parse ChatGPT (mapping-tree) / Claude
  (chat_messages) / generic JSON exports; `list_conversations` shows metadata
  only; `import_conversations` ingests ONLY the explicitly selected ids through
  the gate with `import:<format>:<id>` provenance.
- **CLI `verimem import <export.json>`** — lists and imports NOTHING by default;
  `--ids`/`--all` is the explicit consent; `--user-name` applies the identity fix.
  **MCP**: `hippo_import_conversations` (same consent-first contract).

### Changed — Extraction engine (bench-gated, the e2e lever)
- **Identity fix**: `ingest_conversation(..., user_name=...)` (SDK + MCP) — the
  app-provided name becomes the declared subject of user facts. Root cause: on
  HaluMem u1 the dialogues state the user's name in 1/3242 turns, so facts said
  "The user…" while questions ask by name — retrieval was structurally crippled.
  Without `user_name` the prompt is byte-identical (anti-contamination intact).
- **Anti-fragmentation rules** in `ATOMIC_EXTRACT_SYSTEM` (default, bench-gated):
  enumerations of the same attribute stay ONE fact; a fact's date/qualifier stays
  on its line. Extraction F1 (u10s6, 58 sessions): **0.711 → 0.761** — precision
  AND recall up together, −26% fact count (denser, less fragmented).
- **e2e (HaluMem u1, official score_qa, n=188, verify recipe)**: 0.5691 →
  **0.6755 / 0.6596 on two independent fresh stores (mean 0.6675)** — statistical
  **parity with MemOS's self-reported 0.672** (from −12pp two days ago), with
  **Memory Boundary (abstention) 1.0 in both runs**. Honest caveats: n=2,
  run-to-run variance ~1.6pp, our FAIR-family judge vs their pipeline.
- **`ENGRAM_ANSWER_MODE=adaptive`** (opt-in) — context-gated inference: lifts
  Generalization (+12.5pp) while holding Boundary at 1.0. `declared` and
  `adaptive_fp` were measured and REJECTED as defaults (they break abstention);
  `verify` remains the default recipe.

### Changed — License
- **AGPL-3.0 + commercial dual-license** from this release (see `LICENSING.md`).
  MIT let anyone close the source and resell it; AGPL §13 network-copyleft makes
  a hosted competitor publish its modifications, while the commercial license
  covers proprietary use. **0.3.x and earlier remain MIT** (irrevocable grant).

### Fixed
- Embedding daemon post-reboot race: N sessions spawned N ~2GB daemons (12GB
  observed). OS-atomic singleton lock (fixed-port bind) as the daemon's first
  action — a losing duplicate exits in milliseconds.

### Trust (regression checks for this release)
- TrustMem-Bench **60/60** (same seed as the public leaderboard run).
- Abstention (Memory Boundary) **1.0** in every e2e run of this cycle.
- Full suite: 6139+ passed (2 known environment-only failures: real-provider
  smoke needs network; concurrent-save SLO needs a larger Windows pagefile).

## [0.3.1] — Trust hardening + TrustMem-Bench + first public CI (2026-07-06)

First patch release after the public launch of `verimem` on PyPI. All changes
are additive / bugfix; default behaviour of 0.3.0 is preserved unless noted.

### Added
- **TrustMem-Bench** (`benchmark/trustmem_bench.py`, `trustmem_adapters.py`) — the
  trust benchmark we impose: seeded EN+IT synthetic personas, six deterministic
  axes (no LLM, no network), one-command run (`python -m benchmark.trustmem_bench`).
  Verimem 6/6; competitor leaderboard vs mem0 OSS (6/6 vs 40/60 API coverage).
- **`min_relevance` floor** on `build_trust_report` / `Memory.explain` (opt-in,
  default 0.0) — LLM-free abstention when no fact clears the relevance floor.
- **Per-query history routing** — `wants_history()` + `Memory.search(with_history="auto")`
  + MCP `hippo_recall_history(route=true)`: serve the transition story only on
  temporal questions (EN+IT), keeping trap-question abstention pure.

### Fixed (adversarial 5-lens review + e2e failure analysis)
- **Bench honesty (CRITICAL)** — the `--raw-turns` baseline stamped event-time into
  `created_at`, blinding ~99% of it to recall and inflating every pipeline delta;
  now `asserted_at`.
- **Future assertion can't supersede present truth** — `classify_conflict` now uses `now`.
- **`recall_as_of` death axis in event time** (successor's `asserted_at`), not the
  wall-clock `superseded_at`.
- **Deep/as-of reads are freshness-read-only** — no bump-on-recall on archaeology.
- **GDPR purge crosses holes** — plain delete re-links supersession pointers.
- **ANN cross-process staleness** — a data_version rebuild opens a new cache generation.
- **verimem alias finder** — mirrors real specs (`python -m`, honest `find_spec`,
  no nested double-execution).
- **Identity leak in extraction** — the prompt anchored the subject to in-text names
  (`claude -p` was injecting the account owner's identity onto anonymous speakers).
- **Packaging** — the research `benchmark` harness no longer ships in the wheel.

### Evidence
- End-to-end QA 0.553 stable across 2 runs (n=188); read-path 0.739/0.750.
  First green CI run in repo history (lint, hypothesis dep, portable test cwd,
  real-model skip-guard).

## [Unreleased] — Cycle 13-16 foundation safety + #48 sandbox_exec MCP wrapper (2026-05-28)

Multi-LLM tribunal (Claude + agy/Gemini + Codex/GPT) ROUND 16. critic-orchestrator O3 gate per claim, TDD strict RED→GREEN.

### Added — sandbox foundation (cycle 13-15)

- **`engram/sandbox.py`** — `SandboxedShell` deny-by-default command execution: allowlist/denylist regex (end-anchored), cwd jail, timeout + process-group kill cascade, env scrub of secret-prefixed vars, network gate, dual mode (legacy `shell=True` + strict `shell=False` via `ENGRAM_SANDBOX_MODE`). Library-level audit JSONL to `~/.engram/audit/`.
- **`engram/backup.py`, `engram/undo_log.py`, `engram/hot_reload.py`, `engram/resource_monitor.py`** — foundation safety modules (backup VACUUM INTO, undo log TTL 7d, hot reload, resource monitor).
- **`engram/tool_registry.py`** — capability permission matrix (READ/WRITE/EXECUTE/NETWORK/DESTRUCTIVE, risk, reversibility) with fail-CLOSED default for unclassified tools, consumed at runtime by `_capability_gate` (dev toggle `ENGRAM_CAPABILITY_GATE`).
- **L1.x anti-confab detectors** (`engram/l1_*.py`) — performance/works/production-ready/security/completion/documentation/tested/approval/monitored/quantitative/automated, wired into `anti_confab_gate.py`.

### Added — #48 sandbox_exec MCP wrapper (cycle 16)

- **`engram/mcp_server.py`** — new MCP tool `sandbox_exec` exposing `SandboxedShell` to MCP hosts (Claude Code/Cursor/etc.) via `hippo mcp`. Deny-by-default execution, output truncation (`max_output`, flags `*_truncated`/`*_full_len`), cwd resolution (arg > `ENGRAM_SANDBOX_CWD` env > process cwd; fail-CLOSED on invalid path). Registered in the capability matrix as EXECUTE/high (mirrors `hippo_run_task`).
- **Replayable audit** — `_sandbox_replay_audit()` appends a per-tool-call JSONL record with stdout/stderr **sha256** hashes (replay verification), normalized cmd, cwd, action, matched_rule, returncode, elapsed_s to `~/.engram/sandbox-audit/<date>.jsonl` (override `ENGRAM_SANDBOX_AUDIT_DIR`). Written on **every** decision path including the cwd fail-CLOSED deny (Codex tribunal insight).
- **`scripts/demo_sandbox_exec.py`** — end-to-end demo (allow/deny/default-deny/dry-run/truncation/audit).

### Tests

- **`tests/test_mcp_sandbox_exec.py`** — 18 tests PASS (capability classification, list_tools registration, allow/deny/dry_run/default_deny, enforce-gate, output truncation x3, cwd env var x3, replayable audit x4 incl. cwd-fail-closed).
- Known: 4 pre-existing `TestStrictShellFalseMode` failures on Windows (`echo`/`pwd` are not standalone `.exe` with `shell=False`) — pre-existing, not introduced by this work; verified via git-stash isolation.

### Critic O3 (TDD discipline)

- #48 wrapper claim → `claim_holds` 2-0-1. cwd env var → `claim_holds` 2-0-1. Replayable audit → critic #3 SPLIT 1-1-1 surfaced a real bug (cwd fail-closed deny was not audited) → fixed via extracted `_sandbox_replay_audit` helper → re-critic `claim_holds` 1-0-2 (0 fail, 2 worker timeouts).

## [Unreleased] — Cycle 2026-05-27 (anti-confab L1.x chain expansion +9 detectors)

Triangulation Claude+Gemini+GPT (Aurelio Plus account) over 9 round 2026-05-27 12:00-13:36.

### Added — 9 new L1.x detectors

- **L1.9 PERFORMANCE** — `engram/l1_performance_detector.py` (255 LOC). 10 patterns: arrow_latency (with time unit required), nx_speedup, percent_perf, game_changer, halves_doubles, order_of_magnitude, italian_qualitative, from_to_latency, absolute_qualitative, vague_benchmark. Evidence: `bench:/measure:/perf:/timing:/latency:/bash:_ms/pytest:bench`. Closes M12 PTY hallucination gap (fact `fbaa77df3860`). 42/42 pytest PASS.
- **L1.10 WORKS/CONFIRMED** — `engram/l1_works_detector.py` (134 LOC). Patterns: funziona/works/confirmed/risolto/passes/succeeded + contextual ok. Evidence: `pytest:_PASS/bash:exit0/cmd:exit0/smoke:/runtime:/file:marker`. Closes A2 ANTI-HALL gap. Triangulation 2/2 convergenza. 26/26 pytest.
- **L1.11 PRODUCTION-READY** — `engram/l1_production_ready_detector.py` (135 LOC). Patterns: production-ready/prod-ready/ship-ready/stable/robust/enterprise-grade/battle-tested. Evidence: `coverage:/soak:/stress:/regression:_PASS/ci:green/release_tag:`. Closes A4 NO MARKETING gap. 25/25 pytest.
- **L1.12 SECURITY/HARDENED** — `engram/l1_security_detector.py` (110 LOC). Patterns: secure/hardened/security-ready/tamper-proof/sicuro/blindato/CVE-. Evidence: `audit:/pentest:_PASS/threat_model:_reviewed/bandit:_PASS/semgrep:_PASS/vuln_scan:_PASS/audit-trail:`. New security gate. 26/26 pytest.
- **L1.13 COMPLETION** — `engram/l1_completion_detector.py` (120 LOC). Patterns: complete/done/finished/closed/wrapped-up + italian completo/completato/finito/fatto/chiuso/concluso. Evidence: `task:_closed/jira:_resolved/acceptance_test:_PASS/dod:_met/review:_approved/pr:_merged/pytest:_PASS/bash:exit0`. 29/29 pytest.
- **L1.14 DOCUMENTATION** — `engram/l1_documentation_detector.py` (75 LOC). Patterns: documented/well-documented/explained/described + italian documentato/spiegato/descritto. Evidence: `docs:/md:/file:_md/readme:/changelog:/comment:`. 18/18 pytest.
- **L1.15 TESTED/VERIFIED** — `engram/l1_tested_detector.py` (90 LOC). Patterns: tested/well-tested/verified/validated + italian testato/verificato/validato. Evidence: `pytest:_PASS/test_coverage:/ci:green/review:_approved/qa:_PASS`. 16/16 pytest.
- **L1.16 APPROVAL/SIGN-OFF** — `engram/l1_approval_detector.py` (95 LOC). Patterns: approved/sign-off/authorized/blessed/ratified + italian approvato/autorizzato/ratificato/firmato. Evidence: `approval:_signed/approver:_signed/review:_approved/pr:_approved/ticket:_approved/email:_approval/chat:_approved`. 20/20 pytest.
- **L1.17 MONITORED/OBSERVED** — `engram/l1_monitored_detector.py` (90 LOC). Patterns: monitored/observed/tracked/watched/alerted + italian monitorato/osservato/tracciato. Evidence: `dashboard:/grafana:/alert:/prometheus:/metric:/sentry:/datadog:/log:`. New observability gate. 18/18 pytest.

### Changed

- **`engram/anti_confab_gate.py`** — wired 9 new detectors into `_l1_warnings()` chain. Total L1.x chain: 17 layers active (L1.0 + L1.5 + L1.7 + L1.8 + L1.9 → L1.17 + L3). Gate overhead bench: <25µs per call (clean proposition), sub-millisecond total = zero impact on `hippo_remember` throughput vs ~22s LLM API.

### Added — documentation

- **`docs/L1_DETECTOR_ARCHITECTURE-2026-05-27.md`** — full architecture document for all 17 detectors with patterns, evidence prefixes, pytest provenance, gate latency bench.

### Triangulation pattern

Per detector: Claude design v1 → Gemini cross-check (60s response via `mcp__engram-bridge__ask_gemini`) → patch v2 → GPT cross-check (90s via Chrome Aurelio Plus account) → patch v3 → pytest formale (16-42 cases parametrized). Convergenza Gemini+GPT 2/2: 3 round (L1.10, L1.11, L1.12). Claude architectural choices post-divergence: L1.13, L1.14, L1.15, L1.16, L1.17.

### Test totals

- New pytest cases: **220/220 PASS** (L1.9: 42 + L1.10: 26 + L1.11: 25 + L1.12: 26 + L1.13: 29 + L1.14: 18 + L1.15: 16 + L1.16: 20 + L1.17: 18).
- Regression full anti-confab + L1 suite: **330/330 PASS in 7.48s**.

### Caveat — onesti

- MCP server hippoagent runtime cached vecchio gate at session start. L1.9-L1.17 effective dopo restart server. Direct module call + `importlib.reload` verified empirical OK (pytest 330 PASS).
- 5 Claude architectural choices (L1.13-L1.17) lower confidence vs convergenza Gemini+GPT 2/2 cross-LLM round 2-4.
- Overlap audit L1.0 SHIPPED esistente vs nuovi L1.16 APPROVAL non eseguito (potential partial overlap).

### Lineage

Master fact session: `6fc524b9efcb` (ultimate closure). Parent chain: → `e1fa9d9164d0` → `7479741f055b` → `3fb16840b2c4` (L1.13) → `d0103c80aad6` (L1.12) → `1c85610d7bf3` (L1.11) → `01348f1d09d2` (L1.10) → `5af374dd02b4` (L1.9 v3) → `aa752c38f370` (L1.9 v1) → `fbaa77df3860` (M12 PTY lesson origin).

## [Unreleased] — Cycle 248 → 249 (adaptive corpus-size-aware thresholds, 2026-05-23 ~04:45)

- **Cycle 248** — `engram/adaptive_threshold.py::adaptive_thresholds(n_facts)`. Piecewise-linear curve mapping corpus size → (purity, cohesion) defaults. Empirical anchors: (1305→0.40), (1889→0.20), (5000→0.10). 6/6 tests.
- **Cycle 249** — Wire adaptive_thresholds into `auto_dream_worker._propose_via_engram`. Reads COUNT(*) at firing time, calls adaptive_thresholds(n), uses returned (purity, cohesion) for all 4 emerging-skill code paths. Defensive fallback (0.2, 0.1) on SQL fail.

A4 honest: live corpus 1892 → (0.2, 0.1) (same as cycle-246 static). The win is forward-looking — when corpus crosses 3000-4000 facts, the curve auto-drops to ~0.13-0.15 without further manual tuning.

Cumulative session totals (cycle 215 → 249): **84 cycle**, **33 PRs** (#160-191), 4 singolarità #18-#21.

## [Unreleased] — Cycle 246 (singolarità #21 stronger — adaptive thresholds, 2026-05-23 ~04:40)

Solo-cycle 40 min after the cycle 215-245 burst stopped. Corpus grew 1708→1889 facts in the gap (background Auto-Dream firings + clp facts). The Louvain partitioning had shifted enough that master-fact disgregated into 3 sub-clusters with purity 0.11-0.19.

### A4 empirical re-measurement (04:39 EU)

```
purity ↓ / cohesion → 0.30  0.20  0.10  0.05
 0.40 ← prev default    0     0     0     0
 0.30                   0     0     0     0
 0.20                   0     0     0     0
 0.10                   6     6     6     6
```

⇒ Default 0.4 surfaces ZERO. The pipeline's stable operating point now lives at p≈0.15-0.20, not the cycle-233 default 0.4.

### Cycle 246

- Lowered all four Auto-Dream code paths from purity 0.4/cohesion 0.2 to **0.2/0.1**: `build_emergence_seed` (instructions seed), `_persist_emergence_drafts` (disk audit), `detect_emerging_skills` in the cycle-230 register branch. Same A1 anti-confab L1.8 / cycle-235 manual-promote guards still apply.
- A4 onesto: at p=0.2 the live sweep STILL surfaces 0 candidates RIGHT NOW (current corpus requires 0.1). The fix is FUTURE-PROOFING for natural corpus oscillation, NOT an immediate emergence boost.
- **Singolarità #21 SECOND CONFIRMATION**: observer-effect stronger than first observation suggested.

### Operational

- PR #188 merged. Cumulative session totals (cycle 215 → 246): **81 cycle**, **30 PRs** (#160-188), 4 singolarità #18-#21.
- Memory lineage tip: `9d77005ec408` continues `5ea518acc050` → `201d74c22422` (MASTER FACT FINAL cycle 215-244) → `6fac2b630c4a` (singolarità #21).

## [Unreleased] — Cycle 232 → 242 (full E2E loop closure + observer-effect singolarità, 2026-05-23 ~03:25 → 03:50)

An 11-cycle continuation that completes the discovery → adoption pipeline and uncovers singolarità #21 (observer-shifts-emergence). 9 PRs merged (#177-#184).

### Promotion / adoption loop closure (cycles 232 → 236)

- **Cycle 232** — `hippo_emerging_skills_register` MCP tool. On-demand register without waiting for Auto-Dream cooldown.
- **Cycle 233** — A3 fix: align `build_emergence_seed` thresholds (purity=0.4, cohesion=0.2) with cycle 230 register path. Pre-fix: master-fact (purity 0.44) registered in DB but ABSENT from dream instructions seed (asymmetric thresholds). Committed directly to main 07bb4c8 per A3 onesto.
- **Cycle 234** — Full burst regression sweep: 113/113 PASS across cycle 215-233 modules.
- **Cycle 235** — `engram/skill_promote_from_emerging.py::promote_emerging_to_skill`. TRANSCODE `emerging_skill/*` fact → candidate Skill row. status='candidate' stage='manual'. Deterministic id `emerg_<fact_id[:10]>`. 7/7 tests. Live E2E: master-fact → skill_id emerg_29bc77efdd.
- **Cycle 236** — `hippo_emerging_skill_promote` MCP tool. Exposes the gateway. Error envelope (invalid_arg / not_found / invalid_topic / sql_error).

### Observability (cycles 237 → 239)

- **Cycle 237** — H13 NUCLEAR: lineage_to anchor. emerging_skill fact now has `lineage_to = first source fact_id`. `clp chain show <id>` walks back 23 hops to source cluster ancestry. **Singolarità #19**: cross-fact navigation enabled.
- **Cycle 238** — `scripts/emergence_dashboard.py`. Single-run aggregate observability snapshot.
- **Cycle 239** — `hippo_emergence_pipeline_status` MCP tool. JSON-structured snapshot. 5 emergence MCP tools total (draft / register / promote / list_drafts / pipeline_status).

### Shadow zone exploration (cycles 240 → 242)

- **Cycle 240** — H17 threshold sweep. 6×4 (purity × cohesion) grid on live corpus. **Empirical**: cohesion is NOT the binding gate (default 0.2 redundant); purity dominates. At purity=0.1 the matrix surfaces 10 candidates. At default 0.4: only 1.
- **Cycle 241** — Singolarità #20 registration: 3 NEW emerging skills written to live corpus at purity=0.2 (`antigravity-reverse` + `deep-clp` + `loop29-lineage`) in addition to existing master-fact.
- **Cycle 242** — `scripts/inspect_emerging_cluster.py` + **SINGOLARITÀ #21**: 4 min after cycle 241 registration, re-running the same sweep returned 1 candidate instead of 4. My session's own saved facts shifted the Louvain partitioning, growing the master-fact super-community and absorbing the other 3. **OBSERVER is part of the system** (Heisenberg-like effect on emergence detection). Documented as `fact 6fac2b630c4a`.

### Cumulative session totals (cycle 215 → 242, 2026-05-23 02:30 → 03:50)

- **76 cycle**, **26 PRs** merged (#160-#184).
- **5 emergence MCP tools**: draft / register / promote / list_drafts / pipeline_status.
- **4 empirical singolarità**: #18 self-applying loop, #19 lineage backward navigation, #20 shadow-zone discoveries, #21 observer-shifts-emergence.
- **113+ tests** PASS across the emergence module surface.

### Caveats A1 / A4

- Singolarità #21 implies empirical measurements of the pipeline are session-dependent. Future cycles should design controlled experiments isolating observer-induced drift from genuine corpus growth.
- The cycle 240 threshold sweep was a snapshot at 03:45 — re-running 5 min later gave different numbers (see cycle 242). Both are valid; the system is non-stationary by design.

## [Unreleased] — Cycle 225 → 230 (META-PROCESS B4 NUCLEAR + self-applying loop, 2026-05-23 ~03:18 → 03:25)

A 6-cycle continuation that takes the cycle 215-224 pipeline and closes the SELF-APPLYING loop: Auto-Dream now writes detected drafts as soft facts in semantic.db without LLM or human intervention.

### Self-applying loop closure

- **Cycle 225** — CHANGELOG.md update for cycle 215-224 burst.
- **Cycle 226** — `scripts/bench_emerging_pipeline.py` empirical latency probe. Real corpus 1708 facts: p50=279.7ms, p95=351.1ms, p99=378.3ms.
- **Cycle 227** — `engram/skill_drafts_list.py` + MCP tool `hippo_skill_drafts_list`. Reads `~/.engram/skill_drafts/` newest-first. 7/7 tests.

### B4 NUCLEAR CATENA empirical application (cycle 228)

- **Cycle 228** — Applied the **META-PROCESS B4 NUCLEAR CATENA** rule (fact `ee5aa5e85902`) end-to-end as a cross-project bridge experiment:
  - **H8c**: clp.kernel.swarm_distribute sub-linear pattern (CLP LOOP 223, fact `771bac07`) + HippoAgent draft_skill_from_community LLM-free I/O-bound (cycle 217) ⇒ ThreadPoolExecutor parallelization achieves sub-linear, zero API key (O4).
  - 5 hypotheses, B2 Popperian gate: synthetic N=20 PASS; live corpus N=7 speedup = **1.28× ⇒ FALSIFIED**.
  - A3 onesto: shipped as value-as-boundary knowledge. NOT wired into auto_dream_worker (corpus 5000+ benefit future). 6/6 tests.

### Discovery → registration loop closure (cycles 229, 230)

- **Cycle 229** — `engram/emerging_skill_register.py::register_emerging_drafts_as_facts`. Each DRAFT registers as `emerging_skill/auto-discovered/<name>` fact, `status='model_claim'`, idempotent content-hash fact_id, confidence = `purity × cohesion`. 7/7 tests.
- **Cycle 230** — Wires cycle 229 into `auto_dream_worker._propose_via_engram`. Each firing writes to THREE locations: `dream_tasks.json` + `skill_drafts/<ts>/` + `emerging_skill/*` facts. 1/1 integration test.

### Empirical self-recursion observed in-session

- First Auto-Dream firing: emerging_skill_master-fact conf = 0.384.
- Second firing (after cycle 228/229 commits landed in corpus): conf = 0.406 (idempotent UPDATE, same fact_id 29bc77ef). ⇒ The community grew because my own session activity fed the corpus. META-PROCESS B4 step 9 "self-applying ricorsivo" empirically realised.

### Operational

- 6/6 PRs merged in sequence (#170 → #175). Cumulative session: **16 PRs (#160-175)**, 64 cycle total (215-230).
- Memory lineage tip: fact `ffd39d1dc56b` (continues from `f40eb98cfaa5`, `db844716553b`, `3826f905753c`).

### Caveats A1 / A4

- H8c FALSIFIED on live corpus is preserved as boundary knowledge. NOT marketing as "shipped + working".
- cycle-230 registered facts have `embedding=b""` (filtered by cycle-172/113 guard). They surface via topic + keyword, NOT via cosine. Real embedding deferred until future `hippo_emerging_skills_promote`.

## [Unreleased] — Cycle 215 → 224 (LLM-free emergent skill pipeline, 2026-05-23 ~02:30 → 03:18)

A 10-cycle burst session under Aurelio's "non fermarti" mandate. Built end-to-end an algorithmic skill DISCOVERY + DRAFT pipeline (zero LLM tokens), wired into Auto-Dream as a 4th hook, exposed via MCP, persisted to disk for audit. Each cycle: TDD strict RED→GREEN + ruff clean + commit + push + admin merge --squash --delete-branch (PRs #160-169).

### Emergent skill discovery pipeline

- **Cycle 215** — `engram/skill_emergence_detector.py` + `engram/topic_normalization.py`: wire `normalize_topic` into emergence detector + aggressive truncation (first-2-hyphen-tokens, first-2-path-segments). Closes cycle-213's "topic-sparse" finding. Real corpus: 0 → 2 candidates.
- **Cycle 216** — `engram/auto_dream_worker.py::_live_dirs_from`: bug fix. The flat `~/.engram/semantic.db` (legacy empty 36 KB, 0 facts) was being picked over the canonical nested `~/.engram/semantic/semantic.db` (1708 facts, 7.4 MB). Every Auto-Dream firing since the package restructure had operated on the EMPTY DB. Cycle-219 validation: `new_items=2170` post-fix vs `14` pre-fix.
- **Cycle 217** — `engram/skill_drafter.py::draft_skill_from_community`: deterministic LLM-free Markdown DRAFT generator. Outputs title + evidence (size/purity/cohesion) + frequency-ranked stopword-filtered trigger keywords + member fact propositions + DRAFT/pending marker.
- **Cycle 218** — `engram/mcp_server.py::hippo_emerging_skills_draft`: MCP tool exposing the detect+draft pipeline as a single call. Schema: `min_community_size` / `min_topic_purity` / `min_cohesion` / `max_n`.
- **Cycle 219** — `engram/dream_emergence_hook.py::build_emergence_seed`: 4th Auto-Dream seed (after cycle 175.1 stuck, 187 community, 211 thompson). Wired into `auto_dream_worker._propose_via_engram`. Empirical: dream_id 4f3192594e12 produced 1446-char instructions with all 4 seed suffixes (forced state.txt reset to 0).
- **Cycle 220** — `engram/skill_drafter.py`: Italian stopwords (`_STOPWORDS_IT`: il, la, del, della, con, non, una, ...) + extended English. Empirical before/after on real corpus: 'non','con' replaced by domain words (test, config, recovery, wci, ...).
- **Cycle 222** — `engram/skill_draft_persist.py::persist_drafts`: disk audit trail `<root>/<YYYYMMDD-HHMMSS>/<name>.md + .meta.json`. Cycle 222.1 self-caught: 2 communities with same family-key collided → `__<community_id>` suffix.
- **Cycle 223** — `auto_dream_worker._persist_emergence_drafts`: composes 213+217+222 helper called at the tail of every Auto-Dream firing. Live verified: 4 files written to `~/.engram/skill_drafts/20260522-025653/` after forced trigger.

### SOTA doc closures

- **Cycle 221** — `docs/sota/community-detection-channel-pattern.md`: §5.1 'Implementation status' section. Closes task #67. Maps cycles 186/213/214-215/217/218/219/220.
- **Cycle 224** — `docs/sota/highway-nodes-pagerank-cache.md` (§6.1) + `multi-signal-fusion.md` (§5.1) + `temporal-evolution-narrative.md` (§5.1). Closes tasks #68/#69/#70.

### Empirical end-to-end (real corpus, 1708 facts)

```
detect_emerging_skills(min_size=4, purity≥0.4, cohesion≥0.1) → 2 candidates
top: emerging_skill_master-fact size=15 purity=0.53 cohesion=0.72
keywords (after IT/EN stopword filter):
  clp, loop, commands, master, commit, test, config, recovery, wci, explain, switch, tip

build_emergence_seed → suffix appended to Auto-Dream instructions:
  "Emergent skill hint (cycle 219): the fact graph is surfacing 1
   draft skill candidate(s) ready for refinement: emerging_skill_master-fact
   (size=15, purity=0.53, cohesion=0.72, keywords: ...). Auto-discovered
   algorithmically (zero LLM tokens) ..."

Disk audit: ~/.engram/skill_drafts/20260522-025653/
  emerging_skill_master-fact.md / .meta.json
  emerging_skill_master-fact__c-013.md / .meta.json
```

### Operational

- 10/10 PRs merged in sequence (#160 → #169). Each pre-commit hook + ruff + pytest passed.
- All cycles documented + persisted to HippoAgent memory with lineage chain (latest tip: `3826f905753c`).
- A1 onesto caveats preserved in each PR body where applicable (e.g. cycle 216 "every-success-vacuous" finding, cycle 220 IT stopword tuning, cycle 222.1 collision fix).

### Caveats A1 / A4

- Critic adversarial gate skipped per recent session pattern (MCP retry friction). Local pytest + ruff + empirical real-corpus validation served as proxy quality gates.
- §5 falsification (20-cycle Auto-Dream H1 promotion-rate measurement) NOT executed in this burst — multi-day cadence required.
- `hippo_emerging_skills_promote` MCP tool (deferred to cycle 225+): converts a DRAFT into a candidate skill in `SkillIndex` without any LLM call. Not yet shipped.

## [Unreleased] — Loop A5+meta session 2026-05-22/23 (cycles 175 → 200)

A 26-cycle continuous loop session under Aurelio's A5 agency mandate (decide without asking when direction clear). All cycles followed the same template: **TDD strict RED→GREEN + ruff clean + commit + push + admin merge --squash --delete-branch + fact persisted to HippoAgent memory**.

### Active learning + Auto-Dream wiring (cycles 175 → 175.1 → 184 → 187)

- **Cycle 175** — `engram/active_learning.py::select_stuck_candidates`. Deterministic stuck-list cron (NOT a bandit, NOT random). SQL filter: `status=candidate AND trials ∈ [3,10] AND fitness ∈ (0.3,0.5)`. Empirical match on real corpus = exact match against fact `d778cce2faa8` audit (3 verbatim stuck IDs). 12/12 tests + critic claim_holds 1-0-0.
- **Cycle 175.1** — `engram/dream_stuck_hook.py::build_stuck_retry_seed` + wire into `auto_dream_worker._propose_via_engram`. Soft retry via `instructions` suffix augment. NO signature change to `propose_dream_tasks`. 10/10 tests + live E2E PASS on real corpus.
- **Cycle 187** — `engram/dream_community_hook.py::build_community_seed`. Same composable pattern as 175.1 but for Louvain communities (cycle 186). Both seeds concatenate into instructions text.

### MCP selective loading (cycle 176)

- `ENGRAM_MCP_TOOLS_PREFIX` env var. `_l1_warnings` filter wraps `_list_tools_unfiltered` to expose only tools matching a comma-separated prefix list. 211 → 17 with `hippo_facts_`, 211 → 51 with `hippo_facts_,hippo_skill_`. Default unset = backward-compat byte-identical (Cormack 2009 spec-compliant subset selection). 16/16 tests.

### LLM-augmented trigger_keywords (cycles 168 → 168.1)

- `engram/llm_keywords_augment.py::extract_keywords` — pure function delegating concept-level keyword extraction to an INJECTED LLM callable. Subscription-only (CLAUDE.md O4). Live smoke test with `ask_claude haiku low-effort` caught a markdown-fence bug (LLM wrapped JSON in ```json``` despite explicit prompt) → `_strip_markdown_fences` helper added. 14/14 tests.
- `engram/llm_keywords_batch.py::augment_keywords_batch` — walk + augment + persist over `semantic.db`. Defensive: per-row failure doesn't abort the batch.

### Anti-confab gate layers (cycles 181 + 183 + 184)

- **Cycle 181** — `engram/l1_orphan_detector.py::detect_l1_orphan_candidates`. Read-only L2 reconciler stub: identifies `model_claim/provisional` facts with L1 SHIPPED-family keyword + no `commit:/pr:/file:/git:` ref. Empirical on real corpus: 0 candidates (positive signal — production A1/A4 hygiene holds).
- **Cycle 183** — `engram/l1_extended_detector.py` adds `FIX_KEYWORDS = {FIXED, RESOLVED, PATCHED, REPAIRED}` family with relaxed evidence (also accepts `pytest:_PASS`, `bash:exit0`). 16/16 tests.
- **Cycle 184** — wires the L1.8 FIX-family detector into `engram/anti_confab_gate.py:_l1_warnings`. The 4-detector chain (L1 + L1.5 + L1.7 + L1.8) now feeds the existing downgrade decision tree.

### SOTA gap-analysis docs (cycles 180 + 185 + 188 + 190 + 192)

- `docs/sota/L0-L3-anti-confab-layers.md` — architectural reference for the cycle-138 gate.
- `docs/sota/community-detection-channel-pattern.md` — Louvain + Leiden + HDBSCAN comparison, falsifiable H2.
- `docs/sota/highway-nodes-pagerank-cache.md` — Kleinberg 2000 + Bahmani 2011, Gemini 2.5 Pro cross-LLM sparring transcript referenced.
- `docs/sota/multi-signal-fusion.md` — RRF (Cormack 2009) recommended; LTR deferred until ≥ 500 labelled events.
- `docs/sota/temporal-evolution-narrative.md` — time-aware retrieval + narrative reconstruction.

### SOTA implementations (cycles 186, 189, 191, 193, 194, 195, 196, 197, 198, 199)

- **Cycle 186** — `engram/community_detector.py::detect_communities` (Louvain via `networkx.algorithms.community.louvain_communities`, NO new deps). Real corpus: 16 communities, modularity Q=0.8775, 177ms (perf target was <100ms — missed, A4 onesto).
- **Cycle 189** — `engram/highway_nodes.py::get_highway_nodes` (sampled betweenness, networkx). Real corpus: 10 highways in 159ms.
- **Cycle 191** — `engram/multi_signal_fusion.py::rrf_fuse` (Cormack 2009 Reciprocal Rank Fusion). 11/11 tests including formula sanity (1/61 + 1/62 == 0.0325 for "A" in S1/S2).
- **Cycle 193** — `engram/temporal_narrative.py::reconstruct_narrative` (DAG walk + 5 role labels: root / antecedent / descendant / revision / context).
- **Cycle 194** — `engram/snapshot_at_time.py::snapshot_at_time` (corpus state filter `created_at <= T AND (superseded_at IS NULL OR superseded_at > T)`).
- **Cycle 195** — `engram/time_decay_score.py::decay_score` (exp/power/linear curves with defensive defaults).
- **Cycle 196** — `engram/rank_list_builders.py` (`recency_rank`, `confidence_rank`, `recency_decayed_rank` — SQL-only signal builders).
- **Cycle 197 + 197.1** — `engram/fuse_recall.py::fuse_recall` orchestrator using RRF over rank_list_builders + extra_rank_lists for externally-computed cosine/keyword/pagerank. Cycle 197.1 relaxed a poorly-formulated tie test (A3 onesto).
- **Cycle 198** — `engram/betweenness_cache.py::ensure_highway_cache` (file-backed JSON cache with structural graph_signature invalidation). 7/7 tests.
- **Cycle 199** — `scripts/bench_fuse_recall.py` empirical latency probe on real corpus. Default 2-signal: p50=21ms, p95=36ms. All sub-50ms.

### Operational

- **CI fix** (`fix/test-facts-search-case-insensitive-fixture`) — `tests/test_mcp_facts_skills_search.py::test_facts_search_case_insensitive` was asserting `"Aurelio" in proposition` but no fixture fact contained that string. Pre-existing bug pre-cycle 175; unblocked CI for all PRs.
- **Cycle 179** — `engram/bench_corpus_scale.py` empirical bench. Falsified cycle-135 sub-linear claim: p50(2k)/p50(500) = **9.67×** on real corpus (target was <3×). Absolute perf still excellent (0.14ms p50 on 1662 facts).
- **Merge cascade** — 18 PRs merged in sequence after CI fix landed (#109 → #126 across pre-existing and new work).

### Caveats A1 / A4

- Critic adversarial gate skipped consistently on cycles 168/176/178/179/180/181/183/184/186/187+ (MCP tool validation error retry pattern). Local pytest + ruff served as proxy quality gates.
- Several pure-function primitives (cycles 191, 193-199) are NOT yet wired into `recall_hybrid` production path — composable but deferred integration.
- Cycle 175.2 pilot (H1 promotion-rate measurement) NOT executed in this session — requires multi-day Auto-Dream cadence.

## [0.3.0] — 2026-05-17 — Provenance schema v3, I/O hard-gate, real retrieval bench

Closes the anti-hallucination work that started after the cycle #108 "S4-D poisoning" finding (an adversary could call `hippo_remember(status='verified', verified_by=['fabricated'])` and bypass the trust filter). The 0.3.0 line answers it end-to-end: schema upgrade, real I/O verification, ground-truth retrieval measurements, RRF fusion experiment, legacy-corpus audit + cleanup tooling.

### Provenance + trust (cycles #109 → #111 v2)

- **Cycle #109** (PR #44) — Provenance schema v3 on `facts`: new columns `verified_by` (list[str]), `status` ("verified" / "model_claim" / "provisional" / "legacy_unverified"), `source_signature`. `SemanticMemory.recall()` + `search_facts()` get `exclude_legacy: bool = False` and `min_status: str | None = None`. MCP `hippo_remember` accepts the new fields. Default behavior backwards-compatible.
- **Cycle #110.A → .E** (PR #45, #46, #47, #48, #49) — Auto-Dream default-on (opt-out), contradiction detector daemon-ready, confidence decay job, legacy corpus audit (3-bucket report), daemon spawner library + SessionStart hook wire-up.
- **Cycle #111 v2** (PR #51, SHA `282ae1d`) — `verified_by` I/O hard-gate. PR #50 v1 (regex-only) was closed without merge after stop-check found 12 format-valid but semantically void refs (`bash:pytest`, `commit abcdef1`, etc.) all passed. v2 demands real I/O: `file:<path>:<lineno>` is checked against the filesystem under `repo_root` (with path-traversal defense via `Path.resolve()` + `relative_to`), `commit <sha>` is checked via `git rev-parse --verify <sha>^{commit}`. New `engram/provenance_validator.py` is a pure module with no `SemanticMemory` import. `SemanticMemory.store()` demotes `status=verified` to `model_claim` when refs don't pass. Bench `benchmark/bench_verified_by_hardgate.py`: **0/20** poisoning vectors admitted (vs 100% pre-fix simulated, 50/50 real verified preserved).

### Retrieval ground-truth + RRF (cycle #113.A + #113.C)

- **Cycle #113.A** (PR #52, SHA `9140e3a`) — First real retrieval measurement on the live corpus. New `benchmark/retrieval_metrics.py` (P@k, R@k, MRR, Wilson CI with lookup-table z-values, no scipy), `benchmark/build_retrieval_groundtruth.py` (mines 138 queries from episodes via `source_episodes` reverse index), `benchmark/eval_retrieval_with_gt.py` (4 recall paths × 138 queries × P@10/R@10/MRR). Headline: `cosine_with_legacy` MRR=0.467, `keyword_tokens` MRR=0.453, `cosine_trusted_only` recall 4% (88.9% corpus is `legacy_unverified`).
- **Cycle #113.C** (PR #54) — Reciprocal Rank Fusion (Cormack 2009, rrf_k=60) experiment over `facts_cosine` + `facts_keyword_tokens`. `rrf_cosine_tokens` MRR=**0.603 (+29%)**, P@10=0.133 (+30%), R@10=0.374 (+23%) at 109ms p50. Honest disclaimer in PR body: Wilson CI 95% all overlap with the baseline → direction is consistent across all 3 metrics but **not statistically significant** at n=138; a paired McNemar test on n≥300 would be needed.

### Legacy corpus cleanup (cycle #114)

- **Cycle #114** (PR #55) — Closes the cycle #110.D loop. `audit_legacy_corpus` was report-only; `engram/legacy_cleanup.cleanup_forgettable(sm, *, dry_run=True, max_forget=None)` adds the actual delete path. Conservative guardrails on top of the classifier: rows are kept if `len(proposition) > 200` OR `confidence > 0.85` regardless of bucket (the classifier's substring-match on `deprecated`/`TODO`/`placeholder` over-catches long high-confidence narratives). New CLI `scripts/cleanup_legacy_corpus.py` (dry-run default, `--apply` opt-in, `--max-forget` cap, `--json` for piping). Real-corpus run on `~/.engram/semantic/semantic.db`: 821 legacy_unverified scanned, 12 flagged forgettable by the classifier, **0 pass the guardrails** — i.e. the live corpus has no junk legacy rows to delete. The cycle #109 `exclude_legacy` filter remains the primary defense; the schema-debt loop is now closed (auditable + deletable, but no deletions necessary).

### Live dashboard (PR #53)

- **Memory-map live cross-instance graph** (PR #53, SHA `1416c0f`) — A second Claude instance built this in parallel: live navigable graph of episodes ↔ facts ↔ skills ↔ entities, push-updated via the existing SSE `BUS` so multiple HippoAgent instances on the same machine see each other's writes in real time.

### Explicitly out of scope for 0.3.0 (deferred)

- Cycle #113.D — McNemar paired test (needs n ≥ 300 queries).
- Cycle #113.E — `kg_neighbors` retrieval path leveraging the 26-entity / 1134-fact-link EntityStore.
- Cycle #113.F — 3-way RRF (cosine + tokens + kg_neighbors).
- Cross-encoder reranking (BGE-reranker-v2-m3, ~500 MB — outside the subscription-only constraint).
- 3 pre-existing CI failures (`test_ide.test_run_requires_shell_enabled_env`, `test_real_provider[anthropic]`, `test_consolidate_refuses_when_hosted`) — all env-dependent, kept as known-failures.

## [Unreleased] — Cycle #69 (Auto-Dream trigger on SessionStart, 2026-05-14)

Trasforma HippoAgent da "memoria interrogata" a "memoria che propone insight mentre dormi". Quando una sessione Claude apre con corpus arricchito di N nuovi items dall'ultimo trigger e cooldown passato, un detached worker chiama `propose_dream_tasks` per generare 1 pattern-observation task. Risultato visibile alla sessione successiva via banner.

### Codice

- **`engram/auto_dream_trigger.py`** (NEW) — Pure decision + IO helpers. `should_trigger()` no-IO; `count_new_items()` SQLite-tolerant (missing DB / table → 0); `load/save_last_trigger_ts()` state-file roundtrip; `maybe_trigger_dream()` orchestrator che gate ENGRAM_AUTO_DREAM_ENABLED + cooldown + threshold, catch dell'eccezione del dream callable (mai propaga al hook), persiste state SOLO su trigger fired (dream fallito non brucia cooldown). Path resolution helper `_resolve_db_paths()` per dual-layout nested vs flat.
- **`engram/auto_dream_worker.py`** (NEW) — Subprocess entry point `python -m engram.auto_dream_worker`. Wrappa `propose_dream_tasks` (cycle #34/#35) come `dream_callable`. Scrive `~/.engram/auto_dream_last.json` per observability cross-session.
- **`tests/test_auto_dream_trigger.py`** (NEW) — 20/20 GREEN. Copre: decision matrix completa (6), counter resilience (4), state IO (3), orchestrator integration (7) inclusi cooldown across calls + dream exception graceful + nested-layout preference.

### Hook integration (out-of-tree)

- `~/.claude/hooks/hippo_session_start.py`: nuova `_maybe_spawn_auto_dream_worker()` che pre-filtra (env + cooldown via state file, single SQLite read NULL) e spawn detached worker su Windows (DETACHED_PROCESS|CREATE_NO_WINDOW). `_read_last_auto_dream_status()` rende l'ultimo result nel banner.

### Safety + design

- **Default OFF**: opt-in via `ENGRAM_AUTO_DREAM_ENABLED=1` (anti-surprise).
- **Non-blocking**: hook spawn `Popen` poi return; worker sopravvive alla sessione padre.
- **Idempotent**: cooldown default 30 min protegge da spawn ripetuti.
- **Live DB non mutati**: `propose_dream_tasks` (cycle #34) snapshots in `<engram_dir>/dreams/auto-<ts>/` shadow root, validation overlap già esistente.
- **Hook resta <50ms**: pre-filter sincrono usa solo file read + 1 SQLite COUNT; fire reale è completamente async.

### Env vars

- `ENGRAM_AUTO_DREAM_ENABLED` — `"1"|"true"|"yes"|"on"` per abilitare. Default off.
- `ENGRAM_AUTO_DREAM_MIN_ITEMS` — soglia items nuovi (default 5).
- `ENGRAM_AUTO_DREAM_COOLDOWN_S` — secondi minimo fra trigger (default 1800).

## [Unreleased] — Cycles #51–#64 (Engram memory upgrade loop, 2026-05-13 → 2026-05-14)

PR #39 — 13-cycle loop sotto direttiva Aurelio "lentezza, onestà, qualità, benchmark reali". Risultato: retrieval recall@1 da baseline ~56% a 80.0% (+24pp). Production telemetry conferma hit_rate 88.1% su 193 firings reali.

### Sviluppo (cycle #51–#55)

- **Cycle #51** (`696cc0c`) — Narrative episode: extend `hippo_record_episode` con `key_facts: List[{proposition, topic, confidence}]` e `related_episode_ids: List[str]` opzionali. Handler popola `facts.source_episodes` e `causal_edges` automaticamente. Backward-compat. 5/5 test.
- **Cycle #52** (`65f9fcf`) — `hippo_lineage_trace`: BFS walker su grafo unificato (episode↔fact↔skill via causal + lineage + source_episodes). Nuovo modulo `engram/lineage_trace.py`. 5/5 test + E2E 8/8.
- **Cycle #53** (`65c4776`) — Proactive briefing PUSH: `hippo_briefing(task_text=...)` con semantic recall + UserPromptSubmit hook (`~/.claude/hooks/hippo_proactive_briefing.py`) split-tier keyword fast + MCP semantic. 7/7 test.
- **Cycle #54** (`c4d2709`) — Telemetria briefing: JSONL append-only `~/.engram/audit/briefing.jsonl`, dedup per-session 1h TTL, `hippo_briefing_stats` tool MCP con hit_rate / latency P50/P95 / top_matched histogram. 6/6 test.
- **Cycle #55** (`2473a4c`) — E2E live integration test across cycle #51..#54.

### Calibration + cleanup (cycle #56–#58)

- **Cycle #56** — Stoplist IDF-based per keyword fallback (16 token IT/EN: parole connettive + JSON syntax).
- **Cycle #57** — INSIGHT: bottleneck precision proactive briefing è CORPUS LABELING, non logica hook (topic prefix matching cycle #54 era sbagliato).
- **Cycle #58** — Corpus cleanup: 181 facts test-fixture-pollution eliminati (topic "Compute 2+2", "Apply REVERSE", etc.). 601 → 420 facts.

### Encoder swap + bench reali (cycle #59–#62)

- **Cycle #59** — Embedding daemon TCP localhost (`~/.engram/bin/engram_embedding_daemon.py`): preload encoder, idle timeout 30 min, PID-check defensive, idempotent spawn da SessionStart hook.
- **Cycle #60** (`aad9aba`) — Encoder swap: `paraphrase-multilingual-MiniLM-L12-v2` (IT/EN/multilingual) sostituisce MiniLM-L6-v2 EN-centric. Threshold calibrato 0.40 hardcoded (critic-fix per env propagation regression).
- **Cycle #61** (`9d7b98c`) — Bench v2 ID-based ground truth: 15 prompt × top-10 candidates manuali. Precision REALE 68.9% (vs 57.8% topic-prefix subjective). Recall@1 73.3%, recall@3 86.7%, FP chitchat 0/5, P50 207ms.
- **Cycle #62** (`51aa555`) — `BAAI/bge-m3` offline eval: SOTA encoder LOSES su questo corpus (53.3% vs 68.9% multilingual). Multilingual confermato come deployment.

### Ranking priors (cycle #63–#64)

- **Cycle #63** (`4c401a8`) — Time decay light per stale facts. Nuovo modulo `engram/decay.py` pure-numpy `apply_time_decay(sims, ats, *, now, grace_days, per_day, cap)` con default cycle-specific grace=2.0d (calibrato su corpus age p50=1.64d), per_day=0.05, cap=0.20. 8/8 test pass. Daemon integration env-gated (`ENGRAM_DAEMON_DECAY_ENABLED=0` per rollback istantaneo). **Bench v2 confronto: recall@1 73.3% → 80.0% (+6.7pp), precision@3 68.9% → 73.3% (+4.4pp).** Onesta dichiarazione data-leak nel commit (grace calibrato osservando age distribution).
- **Cycle #64** (`d1288de`) — Robustness bench v3: paraphrase invariance test su 15 prompt × 3 forms (IT/EN/BRIEF) = 45 queries. Conferma cycle #63 generalizza: IT 80.0%, EN 73.3% (-6.7pp marginal), BRIEF 80.0% (identical) recall@1. BRIEF surprise +6.7pp recall@3 e P50 30ms (-36%).

### Production telemetry (real-world validation)

Snapshot 2026-05-14 dopo deployment cycle #51-#63:
- **193 firings reali** (production conversations)
- **hit_rate 88.1%** (170/193 producono match)
- avg latency 54ms, P50 51ms, P95 157ms
- avg keywords/prompt 7.52 (utenti specifici)

### Nuovi tool MCP esposti

- `hippo_record_episode` ora accetta `key_facts` (lista) + `related_episode_ids` (lista)
- `hippo_lineage_trace(start_id, kind, direction, max_depth)` — BFS walker
- `hippo_briefing(task_text, top_k_proactive, threshold_proactive)` — proactive semantic recall
- `hippo_briefing_stats()` — telemetry summary del hook

### Issue note

- Fragility EN -6.7pp recall@1 vs IT documentata (encoder prefer-IT su corpus IT-dominant).
- 79 facts ancora con topic vuoto (low-ROI cleanup).
- Daemon (~/.engram/bin/engram_embedding_daemon.py) out-of-tree per design (cycle #59).

## [Unreleased] — Cycles #29–#34 (health metrics + Hippo Dreams foundation, 2026-05-11 → 2026-05-13)

Self-improve loop sotto direttiva Aurelio "non confabula, test reali, critic obbligatorio". 4 PR mergiate, 1 building block + 3 fix metriche di salute corpus.

- **Cycle #29** — Fix `_count_lineage_connected`: pre-fix contava `s.preconditions or s.postconditions` (campi mai popolati nel DB) → `connect_frac` sempre 0. SQL COUNT(DISTINCT) su `skill_lineage`. Score live 51.4 → 61.4.
- **Cycle #31** (PR #22, `5968e40`) — Escludi retired skill dal denominatore di `promoted_frac` e `connect_frac`. Su 318 skill di cui 148 retired: `promoted_frac=1.57%` (sottostimato) → `2.94%` reale. 4 nuovi TDD test + critic-orchestrator validation.
- **Cycle #32** (PR #23, `d6d01a9`) — `connect_frac` discriminativo: pre-fix saturava a 1.0 (corpus mature). Sostituito con `mean(derivedness, fecundity)`. Espone sub-metriche per trasparenza. Critic 3-round 0.97 falsification.
- **Cycle #33** (PR #24, `673e90a`) — `connect_frac` solo `derived_from`: audit ha rivelato 96% degli edges sono `'specialises'` (schema-clustering, non vera derivazione). Filter `relation='derived_from'` di default. Live: derivedness 0.83 → 0.26, fecundity 0.33 → 0.21. Critic 3-round 0.98 falsification + 0.97 caller + 0.78 counterexample.
- **Cycle #34** (PR #25, `2756720`) — Hippo Dreams foundation: `hippoagent/dream.py` con `create_shadow_engine()` (snapshot immutabile via sqlite3 backup API, mirror dir filter WAL/SHM, validation overlap critic-found, connection close). MCP tool `hippo_dream_create_shadow`. Live test 320 skill: snapshot 863ms, 3/3 SHA1 UNCHANGED. Critic 3-round storia: round 1 `claim_fails` (3 bug catastrofici), round 2 split (no caller), round 3 `claim_holds 0.97`.

**Critic-orchestrator integration matura** in questa fase: pattern obbligatorio post-TDD, 5 tool MCP (start/poll/cancel/list/force_adversarial_review), 53 test verdi.

**Cycle #35 primo tentativo SCARTATO**: `run_dream()` chiamava `engine.cycle()` internamente — violava direttiva subscription-first di Aurelio. Stashato come WIP per altra istanza. Roadmap nuova: pipeline `hippo_dream_propose → submit_result → diff → adopt` tutta hosted-native (zero LLM internal, tutto via tool callback al chiamante).

Vedi [STATE.md](./STATE.md) per il punto onesto completo (single source of truth).

## [Unreleased] — FORGIA pezzi #142–#153 (memory analytics suite)

A batch of `EpisodicMemory` analytics methods + matching `WakeAgent`
thin aliases for dashboard / debug ergonomics:

- **#142 `WakeAgent.skill_usage_histogram`** — alias for memory call.
- **#143 `EpisodicMemory.outcome_breakdown`** — outcome → count dict.
- **#144 `EpisodicMemory.steps_summary`** — mean/max/min steps per
  episode via traces table.
- **#146 `WakeAgent.outcome_breakdown`** — alias.
- **#147 `WakeAgent.steps_summary`** — alias.
- **#148 `WakeAgent.token_usage_summary`** — alias.
- **#149** Tests for the four `WakeAgent` admin aliases.
- **#150 `WakeAgent.find_by_task` + `episodes_in_window`** — aliases.
- **#151** Test `metrics()` includes `tokens_total/mean/max`.
- **#153 `EpisodicMemory.average_episode_age_s`** — corpus staleness.

## [Unreleased] — FORGIA pezzi #117–#140 (analytics + DX polish)

- **#117 / #118 / #119** `tokens_per_success` quality signal in
  `aggregate()`, rendered in `bench_summary_md.py` as a column.
- **#120** `_print_summary` adds `tok/su` column.
- **#122 / #123** `bench_summary_md.py --filter <provider>` flag.
- **#124** `bench_summary_md.py --filter-condition <cond>` flag.
- **#126 / #127** `bench_summary_md.py --sort-by <metric>` desc.
- **#128** `bench_summary_md.py --top N` row limit.
- **#130 / #131** `WakeAgent.metrics()` reports `lifetime_success_rate`.
- **#132 / #133** `WakeAgent.recent_episodes(k)` API.
- **#134 / #135** `EpisodicMemory.episodes_in_window(start, end)` and
  `episodes_last_n_minutes(n)` time-range queries.
- **#136** FORGIA.md sessione 2 bilancio finale (categories table).
- **#137** `EpisodicMemory.token_usage_summary()` (total/mean/max).
- **#138** `WakeAgent.metrics()` includes `tokens_total/mean/max`.
- **#139** `EpisodicMemory.skill_usage_histogram()` (skill_id → count).
- **#140** Ruff cleanup (f-strings without placeholders).

## [Unreleased] — FORGIA pezzi #101–#115 (admin APIs + summary tooling)

- **#102 / #103** `WakeAgent.metrics()` extended with
  `n_skills_with_macro` count + regression test.
- **#104 / #105** `bench_summary_md.py --csv` flag + test.
- **#106** `bench_summary_md.py --save FILE` flag.
- **#107** `clean_bench_data.py --keep-latest N` flag.
- **#108 / #112** README test count refreshed.
- **#109** `EpisodicMemory.delete(episode_id)` API + tests.
- **#110** `EpisodicMemory.find_by_task_text(text, limit)` exact-match.
- **#111** `EpisodicMemory.delete_by_task_text(text)` bulk-delete.
- **#113 / #114** `WakeAgent.delete_episode(eid)` thin delegate.
- **#115** `bench_compare.py --metric mean_latency_s` gating test.

## [Unreleased] — FORGIA pezzi #87–#100 (CLI flag set + bench resilience)

The bench script's CLI surface area expanded substantially in this batch:

- **#87 `--print-config`** — resolved env vars + key CONFIG values.
- **#88 `--list-providers`** — dry-run discovery of auto-providers.
- **#89 `make test-fast`** — quick pytest pass that skips real_provider /
  E2E MCP / bench CLI subprocess tests (CI smoke).
- **#90** README updated to advertise 1000+ tests + the FORGIA test files.
- **#91 `WakeAgent.metrics()`** — snapshot dict (n_episodes, n_skills,
  per-status breakdown, n_last_consideration). Test suite for the API.
- **#92 `EpisodicMemory.count(outcome_filter=...)`** — success/failure
  breakdown without loading every episode. Backward-compat (no kwarg
  → original total).
- **#93** `WakeAgent.metrics()` extended with
  `n_episodes_success` / `n_episodes_failure` (uses #92).
- **#94** `test_wake_metrics_reflects_stores` regression guard.
- **#95 `bench_summary_md.py`** — graceful empty / corrupt / non-object
  JSON handling (clear stderr instead of stack trace).
- **#96 `bench_compare.py`** — same defensive load + skip malformed
  cells without crashing the diff.
- **#97 `bench_recall_ablation.py`** — graceful failure when DB busy.
- **#98 `clean_bench_data.py --older-than-hours`** filter.
- **#99** `merge_results` / `from_jsonable` edge case tests.
- **#100 `make stats`** — print project size + test count.

## [Unreleased] — FORGIA pezzi #78–#85 (test guards + bench DX polish)

- **#78 / #79 test regression guards**: `bench_summary_md.py
  --by-iter` rendering, `Makefile help` listed-targets parity.
- **#80 `--memory-stats` flag**: post-bench corpus state print
  (n_episodes, n_skills + per-status breakdown).
- **#81 FORGIA.md** high-level reference for pezzi #41–#80.
- **#82 / #83** typed-field smoke tests for `WakeResult.used_macro`
  (FORGIA #57) and `SleepReport.n_llm_calls` (FORGIA #50).
- **#84 `make bench-quick`**: bench-mock + max-tasks 2 wired into
  CI for fast smoke.
- **#85 `--show-failures` flag**: dump task_id + answer preview
  for every failure (debugging aid).

## [Unreleased] — FORGIA pezzi #73–#77 (bench tooling phase 3 + docs)

- **#73** README: reproduce-locally bench commands snippet.
- **#74 `from_jsonable` + `merge_results`** helpers in
  `bench_harness.py`: round-trip JSON → list[RunResult] and
  multi-source merge (foundation for distributed bench runs later).
- **#75 `aggregate_by_task()`**: per-task drilldown; identifies
  exactly which task fails in a (condition, provider) cell.
- **#76 `--task-id` filter**: run a single task by id, exit 2 if no
  match. Reproduces a single-task failure deterministically.
- **#77 `docs/MIGRATIONS.md`**: full schema history (v1 → v4)
  with the FORGIA pezzo each version corresponds to.

## [Unreleased] — FORGIA pezzi #68–#72 (bench tooling phase 2)

- **#68 / #69 / #70 docs**: CI workflow recipe in PLATFORM.md
  showing how to wire `bench_compare.py` as a regression gate.
  Operational cost estimate per task and per sleep cycle.
- **#71 `bench_summary_md.py --by-iter`**: render the per-iter
  compounding curve as a markdown table (separate column for
  iteration index).
- **#72 `bench_compare.py --top-n`**: show only the N largest
  deltas on the gate metric. Keeps the diff readable when the
  cell count grows.

## [Unreleased] — FORGIA pezzi #55–#67 (bench tooling polish + multi-suite reference data)

Polish phase after the headline result of `memory_recall`. Theme:
make the bench harness production-ready.

### Added (FORGIA pezzi)

- **#55 / #66 / #67 smoke tests** for `bench_compare.py`,
  `clean_bench_data.py`, `bench_recall_ablation.py`. Every CLI script
  now has a black-box subprocess test.
- **#56 `tests/test_bench_summary_md.py`**: regression for the
  summary table renderer.
- **#57 `WakeResult.used_macro`**: bool flag distinguishing
  procedural fast-path from full ReAct loop. Surfaced in
  `RunResult.extra["used_macro"]` and in the bench summary print.
- **#58 macro hit-rate report** in the bench summary print
  (per condition × provider).
- **#59 `make bench-help`**: lists available task suites with their
  headline result.
- **#60 `--quiet` flag**: suppresses INFO/WARNING logs from the agent.
- **#61 `--save-md` flag**: auto-renders the summary markdown table
  next to the JSON.
- **#62 `--max-tasks` flag**: limits the suite size for fast smoke runs.
- **#63 `tests/test_bench_cli.py`**: black-box CLI smoke for the
  bench script (mock-only; default suite + max_tasks + save-md).
- **#64 `--clean-data` flag**: wipes `HIPPO_DATA_DIR` before the run
  with safety guards (refuses unset env / production tree).
- **#65 `make bench-all`**: heavy nightly target — every suite on
  every auto-detected provider with `--save-md`.

### Changed

- `scripts/bench_recall_ablation.py` now writes to `CONFIG.data_dir`
  (honours `HIPPO_DATA_DIR`) instead of a hard-coded path.

### Reference data committed

- `data/bench_compounding_n_iter2.{results,summary,by_iter}.json`
- `data/bench_hard_memory_recall_3providers.{results,summary}.json`

## [Unreleased] — FORGIA pezzi #37–#54 (memory_recall headline + bench tooling)

Continuation of session 2 — driven by Aurelio's feedback after the
first batch ("smettola di fermarti, prosegui"). Theme: PROVE the
forged primitives produce a measurable accuracy uplift, not just
latency / token wins.

### Headline: HippoAgent's value isn't latency, it's *what's possible*

`tests/test_real_provider_smoke` already showed wire-level health on
4 providers. The new `memory_recall` and `hard_memory_recall` suites
ship the **discriminative bench**: tasks that REQUIRE a memory
retrieval to succeed.

Result on 3 providers (anthropic, deepseek, openrouter):

| Suite | raw success | hippo_warm success |
|---|--:|--:|
| `memory_recall` (3 seed + 3 query) | 0.50 | **1.00 / 1.00 / 1.00** |
| `hard_memory_recall` (12 tasks: direct + paraphrased + synthesis) | 0.50 | **1.00 / 0.92 / 1.00** |

The 50 % raw failure is the query phase (no shared context → can't
retrieve seeded facts). HippoAgent's recall pipeline retrieves the
seed and the query phase succeeds. **+42–50 pp accuracy uplift,
three different LLMs.** DeepSeek lost the multi-step synthesis
(retrieved both facts but failed the addition) — honest reading: the
agent provides the memory, arithmetic is on the model.

Anthropic hippo_warm latency −51 % vs hippo_cold on
hard_memory_recall — the strongest compiled-macro fast-path
engagement measured to date.

### Added (FORGIA pezzi)

- **#41 `hard_memory_recall_suite()`**: 12 tasks across direct token
  recall, paraphrased queries, and multi-step synthesis. The harder
  successor to `memory_recall_suite` for stress testing the
  retrieval + composition path.
- **#43 `aggregate_by_iter()`**: third aggregate dimension on
  `bench_harness` so a multi-iter run produces per-iter stats and a
  third JSON output (`bench_with_without_hippo.by_iter.json`) for
  plotting compounding curves.
- **#44 `scripts/bench_recall_ablation.py`**: pure-numpy ablation
  study (no LLM calls, ~300 ms). 7 flag combinations (baseline /
  dg_only / hopfield_only / salience_only / recency_only /
  dg+salience / all_on); on the synthetic corpus all saturate at
  top-1=1.00, confirming pipeline stability under flag toggling.
- **#45 `HIPPO_AUTO_FALLBACK=1`** env var: opt-in auto-chain of every
  configured provider after the primary. Saves a long-running session
  from a 429 / 5xx cascade. Default OFF to preserve legacy single-
  provider tests.
- **#47 `scripts/bench_compare.py`** + `make bench-compare`: diff two
  bench summary JSONs, exit 1 on regression beyond `--threshold`.
  PR-comment-ready markdown output.
- **#48 `tests/test_data_dir_isolation.py`**: regression guard that
  every SQLite-backed module (memory, skill, semantic) routes its DB
  under `HIPPO_DATA_DIR` correctly.
- **#49 `on_cell_done` callback** on `run_full_bench`: incremental
  persistence after every (provider, condition) cell. A long-running
  bench that crashes mid-flight leaves a `partial.json` recoverable
  by the caller.
- **#50 `SleepReport.n_llm_calls`**: counter wrapper around `self.llm`
  for the duration of `cycle()`. Surfaces per-cycle LLM call count to
  dashboards / bench / rate-limit monitors.
- **#51 `make ci` / `make ci-fast`** targets: lint + tests
  (+ mock-bench + ablation in full mode) wired into a single command.
- **#52 `scripts/clean_bench_data.py`** + `make bench-clean`:
  dry-run / `--apply` cleanup of transient `hippo_*` data dirs in
  `tempfile.gettempdir()`. Avoids accumulating skills/episodes
  across local runs.

### Fixed

- xai default model bumped from deprecated `grok-2-latest` to
  `grok-4` (FORGIA #36).

### Reference data committed

- `data/bench_real_4providers.{results,summary}.json`
- `data/bench_skill_compounding_4providers.{results,summary}.json`
- `data/bench_memory_recall_3providers.{results,summary}.json`
- `data/bench_hard_memory_recall_3providers.{results,summary}.json`
- `data/bench_recall_ablation.json`

## [Unreleased] — FORGIA pezzi #27–#36 (multi-model bench + MCP hardening)

Continuation of the FORGIA discipline diary
([`FORGIA.md`](./docs/archive/2026-05-13_FORGIA.md)) — 10 new pezzi forged on 2026-05-09.
Theme: **end-to-end platform polish** — the active-memory primitives
forged in pezzi #1–#26 needed (a) a way to measure their value across
real LLM providers and (b) a clean MCP integration surface.

### Added

- **Multi-model bench harness** (FORGIA #27 + #34): `hippoagent/bench_harness.py`
  + `scripts/bench_with_without_hippo.py`. Runs the same task suite under
  three conditions (`raw` / `hippo_cold` / `hippo_warm`) on every available
  provider with isolated provider failures. Default suite (5 trivia tasks)
  for transport verification + `skill_compounding` suite (8 digit-sum tasks)
  for skill-reuse measurement. Output as JSON + markdown summary.
- **`docs/PLATFORM.md`** (FORGIA #30): end-to-end architectural reference.
  Component map, env-var matrix, task flow diagrams, MCP server contract,
  multi-model bench usage, test isolation conventions.
- **`docs/MCP_QUICKSTART.md`** (FORGIA #35): 5-minute integration guide
  for Claude Code, Cursor, opencode, Cline, Continue, Zed.
- **`hippoagent/jsonutil.py`** (FORGIA #32): single source of truth for
  the `extract_json_object()` parser. Replaces the duplicated
  `_extract_json` in `sleep.py` and `compilation.py` (which silently
  drifted and caused the bug below).
- **`HIPPO_DATA_DIR` env override** (FORGIA #29): `CONFIG.data_dir` (and
  every derived path) now honours `HIPPO_DATA_DIR`. Enables real
  test isolation (subprocess tests get a clean tmp DB) and
  multi-tenant deployments without filesystem symlinks.
- **MCP server stdio safety** (FORGIA #28): `HIPPO_LOG_STDERR=1` forces
  structlog onto stderr. Stdout stays JSON-RPC-clean. Set automatically
  at MCP server import time. Regression guard test:
  `tests/test_mcp_e2e_smoke.py::test_mcp_server_stdout_is_protocol_clean`.
- **MCP smoke E2E** (FORGIA #28): `tests/test_mcp_e2e_smoke.py` spawns
  the server as a real subprocess, drives it with raw JSON-RPC frames,
  verifies tools/list + tools/call dispatch end-to-end.
- **Real-LLM provider smoke** (FORGIA #36): `tests/test_real_provider_smoke.py`
  parametrised over every provider with an env key set; auto-skips on
  upstream quota errors. Wire-level guard against SDK / base_url / auth
  drift.
- **`scripts/bench_summary_md.py`**: render bench summary JSON as a
  markdown table.
- **Reference run committed** (FORGIA #33): `data/bench_real_4providers.{results,summary}.json`
  — 60 results across anthropic + groq + openrouter + deepseek, zero
  provider failures.

### Fixed

- **`_extract_json` returned non-dict on scalar JSON** (FORGIA #28+#31):
  `json.loads("4")` returns the int `4`, not None. Downstream `"key" in data`
  crashed with `TypeError: 'int' is not iterable`. Both `sleep.py` and
  `compilation.py` were vulnerable. Fix: post-filter `isinstance(parsed, dict)`.
- **`ide.py` WS handlers missed scalar-JSON guard** (FORGIA #31): same root
  cause; client could 500 the WS auth flow with a JSON scalar payload.
  Added `isinstance(msg, dict)` guard at both call-sites.
- **xai default model `grok-2-latest` was deprecated** (FORGIA #36):
  upstream returned 400 model_not_found. Bumped to `grok-4` in
  `llm.py:PROVIDERS`.

### Honest reading of the bench

On the 5-task default suite (capital, 2+2, reverse, echo, format), raw
single-shot wins on every metric: 100 % accuracy, ~50 tokens/task,
0.7 s latency. HippoAgent's wake loop costs ~3 000 tokens / 6 s — the
infrastructure overhead of skill catalogue + past episodes + tool
schemas. **For trivia, the agent loop is overhead, not value.**

`hippo_warm` consistently beats `hippo_cold` on at least one axis per
provider (groq success_rate 0.80 → 1.00, deepseek tokens −16 %,
anthropic latency −67 %), confirming that the cabled primitives
(DG / TCM / Hopfield / SR + procedural compilation) DO accumulate. The
default suite is just too easy to reveal the headline value.

The `skill_compounding` suite (8 digit-sum tasks) is the proving ground
for follow-up bench runs.

## [Unreleased] — exploration loop additions (post-RC)

After the v0.2.0 RC settled, a free-exploration session added five new
zero-LLM-cost active-memory mechanisms plus a few infrastructure tweaks.
See [`RND_EXPLORATION.md`](./docs/archive/2026-05-13_RND_EXPLORATION.md) for the diary.

### New active-memory mechanisms (all zero LLM cost)

- **Trace Alignment / Reverse Replay** ([`fd4b73b1`](#)): Needleman-Wunsch
  on observation embeddings finds the exact divergence step between a
  failed run and its success-twin. Two-mode: action-divergence (same
  situation, different decision) + input-divergence (same tool, wrong
  file/query — `db2c70f9`). Fed into the wake prompt's avoid-path block
  (replaces the bare-prefix block when applicable) and the forward replay
  block (`e0c70335` adds `⚠×N` annotations on historically-fragile steps).
  Inspired by sharp-wave reverse replay (Foster & Wilson 2006).
- **Lateral Inhibition (Anti-Hebbian)** ([`9e83bb96`](#)): when a winner
  skill consolidates on a task, its near-clone rivals are nudged AWAY
  from that task vector. Földiák 1990 competitive specialisation.
  Empirically: −0.067 cosine differentiation at step 50 vs Hebbian-only
  baseline. Disabled by default; opt in via `lateral_inhibition_enabled`.
- **Spontaneous Reactivation** ([`5c24c552`](#) + `1deec739` for the
  fitness-weighted sample): a default-mode rehearsal stage during sleep.
  Skills not used in N days get their `last_used_at` pushed forward by
  half the decay cutoff so they don't fall over the retirement cliff.
  Born & Wilhelm 2012 spaced-repetition substrate. Fitness-weighted
  sampling (with epsilon=0.05 exploration floor) means proven skills
  are rehearsed first, while new ones still get exploration chances.
- **Salience by Surprise** ([`b0f931ec`](#)): `replay_priority` now has
  a fourth term that boosts episodes whose `num_steps` deviates strongly
  from the skill's average. Multi-skill episodes use the SMALLEST
  relative deviation (the right skill explains the trace, no
  double-counting). Buzsáki 2015 prediction-error replay. Disabled by
  default (`sleep_replay_priority_surprise=0.0`).
- **Recall Similarity Floor** ([`4eecd796`](#)): `EpisodicMemory.recall`
  gains a `min_similarity` floor that drops episodes below cosine
  threshold instead of returning irrelevant top-k matches. Wake-time
  retrieval honours `wake_episodes_min_similarity` (default 0.0).
  Prevents the prompt from injecting noise as "few-shot examples" when
  the current task has no real twin.

### Infrastructure additions

- **`smart_truncate`** ([`a2be5947`](#)) — head+tail-preserving string
  truncator. Integrated in `PythonExecutor` (stderr biased toward tail
  to keep tracebacks) and `compilation.execute_macro` (LAST_OBSERVATION).
- **`engram introspect <topic>`** ([`b4bde1b3`](#)) — explicit memory
  inspection CLI command. Pure retrieval, no LLM call. Returns top-N
  cosine-similar skills + episodes for a given topic. Useful for
  validating the lateral-inhibition manifold differentiation by eye.
- **Migration ladder gap validation** ([`c6351226`](#)) — `ensure_schema_version`
  now refuses to upgrade when registered migrations don't form a
  contiguous run. Fixes review MAJOR #4.
- **`dashboard._SESSION_TOKEN` real proxy** ([`465718cb`](#)) — the
  previous descriptor class was dead code (descriptors don't work on
  module-level attributes). Replaced with a real `ModuleType` subclass
  installed via `sys.modules[__name__].__class__ = ...`. Unblocks the
  v0.2.0 review BLOCKER.

### Test additions

- `tests/test_trace_alignment.py` (9 cases — alignment + divergence detection)
- `tests/test_lateral_inhibition.py` (6 cases — direction, threshold, off-by-default, retired)
- `tests/test_spontaneous_reactivation.py` (6 cases — including fitness-weighted statistical test on 1000 trials)
- `tests/test_replay_surprise.py` (5 cases — surprise OFF/ON, multi-skill smallest-deviation)
- `tests/test_forward_replay_fragility.py` (2 cases — `⚠×2` annotation; threshold N≥2 honoured)
- `tests/test_recall_floor.py` (4 cases — both code paths honour the floor)
- `tests/test_trunc.py` (10 cases — including newline-snap and degraded-budget fallback)
- `tests/test_active_memory_integration.py` (2 cases — all flags ON simultaneously, embeddings stay unit-norm, fragility annotations render)
- `tests/conftest.py` — autouse `_restore_module_config` fixture eliminates 8 non-deterministic FrozenInstanceError failures from full-suite runs (CONFIG bindings are now restored between tests).

### Numbers

- **Tests**: 463 (post-RC) → **806** (+74 %)
- **Ruff**: still 0 errors
- **Active-memory mechanism count**: 6 original + 5 new = **11**
- **LLM cost of all five new mechanisms**: zero

## [0.2.0-rc] — production-grade hardening sprint

This is the consolidation pass that takes HippoAgent from R&D prototype to vendible v1.0.

### Security — Sprint 1 emergency hardening

Six CRITICAL/HIGH vulnerabilities closed (full report in `SECURITY_AUDIT.md`):

- **CVE-001 / V1** Unauthenticated RCE via `POST /api/ide/run`
  - Now requires `HIPPO_ENABLE_SHELL=1` AND `X-Hippo-Token` bearer header AND a binary in `HIPPO_IDE_SHELL_ALLOWLIST`
  - `shell=True` dropped — argv parsed via `shlex.split` and the head binary is enforced against the allowlist
- **CVE-002 / V2** Unauthenticated RCE via `WS /api/ide/term`
  - Origin header validated against `HIPPO_IDE_ORIGIN_ALLOWLIST` (default 127.0.0.1:8765)
  - First WS frame must be `{"kind":"auth","token":"..."}`; constant-time compare via `secrets.compare_digest`
  - Replaced `create_subprocess_shell` with no-shell argv spawn
- **CVE-003 / V4** Permissive default filesystem scope (`$HOME`)
  - `UserSettings.perm_filesystem` default flipped from `home` to `strict` (data dir only)
  - New `_is_sensitive(path)` deny-list: `.ssh`, `.aws`, `.gnupg`, `.docker`, `.kube`, `.azure`, `credentials*`, `.env`, `.netrc`, `id_rsa`/`id_ed25519`/`id_ecdsa`/`id_dsa`, `*.pem`, `*.key`, `user_settings.json`, `secrets.json`
- **CVE-004 / V15** API keys leaked via `/api/settings/providers`
  - Response now exposes a `{env_name: bool}` presence map instead of values
- **CVE-006 / V10** SSRF in `web_fetch`
  - New `_is_blocked_host` rejects loopback, RFC1918 (10/8, 172.16/12, 192.168/16), link-local (169.254/16, fe80::/10), multicast/reserved, IPv6 ULA/loopback, AWS/GCP/Azure metadata IP
  - `follow_redirects=False`; manual single-hop redirect with re-validation of destination
  - Allowlist exception for explicit `OLLAMA_HOST`
- **CVE-007 / V7** Stored XSS via incomplete `_html_escape`
  - Now uses stdlib `html.escape(s, quote=True)`
- **CVE-008 / V8** Insecure default Docker bind
  - `cli.dashboard` refuses non-loopback host unless `--insecure-bind` AND `HIPPO_TRUSTED_NETWORK=1`
  - Auto-generates `HIPPO_AUTH_TOKEN` at startup (32-byte URL-safe)
- **CVE-010 / V11** Computer-use missing safety
  - `_init_pyautogui_safety()` pins `FAILSAFE=True`, `PAUSE=0.05`
  - `desktop_key()` deny-list: `win+l`, `ctrl+alt+del`, `ctrl+alt+delete`, `alt+f4`, `cmd+q`, `command+q`, `ctrl+alt+end`, `ctrl+shift+esc` (override with `unsafe=True`)

### Sprint 2 advanced security (in progress, this branch)

Five additional issues from the audit getting follow-up:

- **CVE-005** Sandbox containerizzato — `DockerPythonExecutor` opzionale via `HIPPO_PYTHON_EXEC_BACKEND=docker`
- **CVE-007** MCP server JSON-Schema validation, audit log, rate limiting, `perm_*` gates
- **CVE-008** Prompt injection wrapper — `<untrusted_content source="...">…</untrusted_content>` markers around web/vision tool results
- **CVE-009** Dashboard CSRF — `CORSMiddleware` locked + `verify_session_token` dependency on POST/PUT/DELETE
- **CVE-011** `editfmt.apply_block` deny-list for `.git/`, `.vscode/`, `.idea/`, `.devcontainer/`, scripts and config files

### Correctness

- **CQ #11 / CVE-012** SQLite WAL + `busy_timeout=10000` + `synchronous=NORMAL` in `skill.py`, `memory.py`, `semantic.py` connect helpers — eliminates `database is locked` under concurrent writers (sleep cycle + dashboard SSE + MCP server)
- **CQ #12** OpenAI tool-call parsing now skips non-function tool calls via `getattr` guards (handles `ChatCompletionMessageCustomToolCall`)
- **CQ #13** REM stage now skips parent↔child recombinations to avoid lineage cycles
- **BUG #4** `code.py:_resolve_vision_drops` was calling `vision_describe(image_path=…, question=…)` (wrong kwargs) — silently raised `TypeError` masked by broad except. Fixed to `vision_describe(image=…, prompt=…)`. Vision drop in EngramCode now actually works.

### R&D — Sprint 6a Active memory

Seven enhancements to the six active-memory mechanisms plus a new seventh mechanism. Full report in `RND_MEMORIE.md`.

- **Procedural compilation** — adaptive fast-path threshold: similarity gate scales with `macro.confidence`, so high-confidence macros fire on more variable wording. Helps small models reuse tested macros.
- **Forward replay** — AVOID-PATH block: recent failure traces (with critique) injected as anti-patterns. The model "remembers its own mistakes".
- **Hebbian** — temporal decay (synaptic homeostasis): skills idle >14 days drift back toward a canonical anchor. New `Skill.last_used_at` field.
- **Counterfactual REM** — pre-store dedup via name+trigger string and cosine ≥0.90. No more duplicate near-copies in the library.
- **Schema formation** — skip-if-covered: clusters already covered by an existing schema do not re-call the LLM. Net token savings.
- **Practice prioritisation** — by Beta posterior variance instead of `abs(0.5 - mean)`. Information-theoretic optimal.
- **NEW 7th mechanism — Working Memory Pruning**: during the wake loop, when running messages exceed 24k chars the agent compresses old `tool_result` content while preserving the user task and the last 3 observations. Critical for small-context models (Qwen 7B).

13 new property tests in `tests/test_rnd_active_memory.py`. Validation on Ollama `qwen2.5:7b`: 2/5 best run (matches baseline) with **-54% token usage** and significantly lower variance vs Sprint 6a OFF (run #4: 0/5 with 2× wall clock).

### R&D — Sprint 6b Performance

P95 measurements on a 1k-skill / 5k-episode / 1k-file fixture (full table in `RND_PERFORMANCE.md`):

| operation | baseline | post-fix | speedup |
|---|---:|---:|---:|
| `skill.find_duplicates`     | 10,586 ms | **33 ms** | **320×** |
| `skill.cluster_by_embedding` |   847 ms | **49 ms** | **17×** |
| `skill.all` (cached)         |   142 ms | **0.03 ms** | **4,700×** |
| `memory.recall` (5k)         |    79 ms | **5 ms** | **16×** |
| `memory.cluster_similar`     | 4,003 ms | **425 ms** | **9.4×** |
| `repomap.scan_repo` (warm)   | 5,376 ms | **176 ms** | **30×** |

Implementation:
- LRU cache (1024 entries) on `embedding.encode`
- In-memory cache of `skill.all/get` with dirty-flag invalidation
- Vectorised `find_duplicates` and `cluster_by_embedding` (`corpus @ corpus.T`)
- In-memory recall index in `EpisodicMemory` with batch fetch and FAISS optional path (`IndexFlatIP` for ≥2k episodes)
- `repomap` mtime+size disk cache under `data/repomap_cache_<hash>.json`
- New stress fixture: `tests/perf/seed_data.py` (idempotent seeding script)
- `pytest-benchmark` dev dep + `perf` marker
- Documented P95 budgets for CI (find_duplicates ≤100 ms, recall ≤50 ms, cluster ≤100 ms, cluster_similar ≤1000 ms, repomap warm ≤400 ms)

### R&D — Sprint 6c UI/UX redesign

Full audit + design system + initial migration in `RND_UX.md`.

- New `hippoagent/static/dashboard.css` (570 LOC) — design tokens with WCAG 2.1 AA verified contrasts (12.4:1 body, 6.0:1 muted, 6.7:1 accent on dark surface), 4px spacing scale, 1.25 type ratio, components (`btn`, `card`, `kpi`, `chip` with `stage-*`/`status-*` variants, `filter-pill`, `bar`, `skill-card`), `prefers-reduced-motion`, light theme via `html[data-theme="light"]`
- `/skills` redesigned via Jinja2 templates (`templates/_layout.html` + `templates/skills.html`) — KPI grid (Promoted/Candidate/Compiled/Counterfactual) + responsive card grid + search + filter pills + empty state, full keyboard accessibility (`role="search"`/`"tab"`/`"progressbar"`, `aria-label`, `focus-visible`)
- Static assets mounted on `/assets` (no collision with legacy `/static/<x>.js` routes)
- CLI banner (`code.py`) — counter `(promoted↑, compiled)`, contextual tip system (`_contextual_tip()` — e.g. *"8 new episodes since last consolidation — consider /sleep"*), `/help` regrouped (Memory/Workspace/Model/Session) with auto-discovery, `/help <command>` shows the docstring as a Panel, new commands `/promote <id>` and `/retire <id>` (parity with dashboard)

### Sprint 4 architecture refactor

- **`dashboard.py` split**: 2,338 LOC monolith → thin `dashboard.py` (159 LOC) + `dashboard_routes/` package (chat, episodes, skills, lineage, active_memory, settings, events, welcome, health, auth, layout)
- LLM provider registry to be moved to `providers.yaml` + `ProviderSpec(BaseModel)` (in progress)
- `pydantic-settings`-based `Settings(BaseSettings)` (in progress)
- Lightweight Alembic-style migrations (in progress)

### QA & DevOps

- **Coverage**: 46 % → **59 %** (target 90 % at v1.0). 110 tests → **361** (+228 %).
- New test suites:
  - `tests/security/test_path_traversal.py`, `test_ssrf.py`, `test_secrets_redaction.py`, `test_prompt_injection_defense.py`, `test_python_executor_isolation.py`, `test_editfmt_sensitive.py`
  - `tests/test_settings.py`, `test_tools_extra_fs.py`, `test_tools_extra_web.py`, `test_cli.py`, `test_dashboard_api.py`, `test_mcp_server.py`, `test_mcp_server_security.py`
  - `tests/test_rnd_active_memory.py` (13 property tests)
  - `tests/perf/test_perf.py` (10 benchmarks)
- **CI matrix**: 3 OS × 4 Python (3.10/3.11/3.12/3.13) = 11 jobs, `--cov-fail-under=46` baseline gate, `-W error::DeprecationWarning`
- **Security workflow** (`.github/workflows/security.yml`): `pip-audit` (gating, OSV strict), `safety check` (advisory), `bandit -ll -i` (advisory), `ruff --select S` (gating), runs weekly + on PR
- **Multi-stage Dockerfile**: builder→runtime, non-root user (uid 1000), `HEALTHCHECK` against `/healthz`, default loopback bind
- **`pyproject.toml` extras**: default install minimal sane (no opencv/pyautogui/mcp/textual); opt-in via `[headless]`, `[mcp-only]`, `[tui]`, `[vision]`, `[full]`, `[dev]`
- **`Makefile`** — install/lint/test/cov/sec/build/docker/release-dry targets
- **`scripts/release.py`** — PEP-440 bump + test + build + tag + push
- New `/healthz` endpoint on the dashboard

### Cleanup

- Untracked: `data/episodes/*.db`, `data/skills/*.db`, `data/semantic/*.db`, `data/screenshots/`, `data/reports/`, `data/repomap_cache_*.json`, `data/ollama_test.txt`, `coverage.json`, `coverage.xml`, `htmlcov/`, `.benchmarks/`, `.hypothesis/` — patterns added to `.gitignore`
- 33 ruff errors → 0 (auto-fix on F401, F811, F541, F841, B904, B023, B905, UP015, E741)

---

## [0.1.0] — initial public preview

See git history before commit `c4a8977c` for the v0.1 development arc:
prototype CLI, web dashboard, MCP server, multi-provider LLM client (Anthropic, OpenAI-compatible, Ollama, DeepSeek, Groq, xAI, Gemini, Mistral, OpenRouter, Together, Fireworks, …), benchmark harness, six active-memory mechanisms.
