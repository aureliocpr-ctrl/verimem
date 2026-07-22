# Verimem — State of the Project

> **Brand note (2026-07-04):** the product is **Verimem** (verimem.com);
> `engram` stays as the module name and the architecture term. Historical
> entries below keep the names used at the time — they are logs, not brand copy.

> **Single source of truth.** Updated at the end of each macro-cycle.
> Last update: **2026-07-04 EU/Rome** — **HaluMem updating selector v3 shipped**:
> learned out-of-fold discriminator (17 runtime-legal features) lifts the
> severe number 0.254 → 0.3286 and the judge-corrected number 0.2379 → 0.2867
> (61-item judge pass, 0 errors). Metric honesty: the e5@0.94 matcher's v1-era
> calibration does not transfer (precision 0.60 on v3 verdicts) — local severe
> is for relative ranking, absolute numbers come from judge passes. See
> **2026-07-03 (late night) — HaluMem UPDATING slice** below.
> Previous: 2026-07-03 — **knowledge/telemetry tiering shipped**:
> `classify_tier` single source (knowledge|telemetry|test|dialog), reconcile-judge
> guard on both sides of every pair, truth scan reads knowledge only by default,
> +7 telemetry prefixes found by sampling the real corpus (dream/, pin/,
> skill/catalog/, project/recursive-mas/). See **2026-07-03 tiering** below.
> Previous: 2026-07-02 — distilled LOCAL write-gate shipped (opt-in):
> a fine-tuned CE beats the claude judge on heldout ground truth (AUROC 0.983 n=4712,
> clean-admit 0.948 vs 0.80, assistant-injected false-memory admit 0.086 vs claude's
> 0.40 — the new ATTRIBUTION axis), zero API cost, ~15-88 ms. `ENGRAM_GROUNDING_BACKEND=local`,
> default unchanged until real-corpus (IT) validation. See **2026-07-02 local gate** below.
> Previous: 2026-07-01 consolidation (scale wins folded, LoCoMo same-judge TIE, A1 span).
>
> Historical snapshots, audits, and R&D diaries live in
> [`docs/archive/`](./docs/archive/). This file is the only one that stays current.

---

## Current state (2026-06-20) — the honest pitch

**What makes Engram different, in one sentence:** it is the only LLM-memory layer
whose `add()` routes every write through an **anti-confabulation gate** — a candidate
fact is admitted, downgraded, or refused based on whether its source actually entails
it — and whose `search()` returns each fact's **provenance**, so downstream code can
trust-condition instead of trusting blindly.

**The moat (verified):** write-path source⊢fact entailment, **SNLI AUROC 0.971**
(`engram/grounding_gate.py`, `docs/SEMANTIC_GROUNDING_STUDY.md`). A competitor reverse
(mem0 / Zep / Letta / Cognee / MemOS, `docs/COMPETITIVE_LANDSCAPE.md`) confirms **none
ship a write-admission gate** — they store whatever the extractor emits. The cheap
no-LLM L1 screen also downgrades unsupported "it works / verified / completed" claims.

**Downstream proof — re-measured honest (2026-06-23, realistic pairing).** The earlier
"pooled p=3.4e-5" claim was RETRACTED as rigged (confab gated against a RANDOM unrelated
dialogue → trivial rejection). Harness fixed: each confab is now gated against ITS OWN session
dialogue (the realistic threat — a plausible-wrong answer to the user's own question). Re-run
(`benchmark/halumem_writepath_moat.py --noise-mode same-topic`, 7 users, seed 7,
`halumem_moat_fixedpair.json`): gate ON cuts downstream **hallucination 95.9% → 12.2%**
(−83.7 pp absolute = 87.2% relative reduction), **McNemar exact p≈0** (84 fabrications fixed vs 2 caused; magnitude is judge-coupled — same model family answers + judges — whereas the write-level AUROC 0.971 is judge-independent). **Honest
mechanism + cost (not hidden):** the gate does NOT raise correctness (both arms ~1–3%, by
construction — the right answer is often not cleanly retrievable in this stress test); it
converts confabulation into **abstention** (omission 3%→85%) — a memory that says "I don't
know" instead of inventing. At threshold 40 it rejects 100% of injected noise but also
**over-rejects 30-39% of clean facts** (recall traded for trustworthiness). REPLICATED on
2 independent seeds (7: 95.9->12.2; 13: 90.8->13.3), pooled McNemar b=161/c=3 p~=6e-44 — the
prior "non-independent seeds" criticism is closed. The **write-level** moat (source⊢fact entailment
AUROC 0.971) is independent evidence and stands.

**Retrieval (measured, judge-free, same e5 embedder, FULL 500 like-for-like):**
LongMemEval-s **recall@5 0.8745** (hit@5 0.944, MRR 0.856) with the fusion ON vs
**0.8525** OFF — fusion **+0.022** on the full set (`lme_s_fusionON/OFF_n500_clean.json`).
An earlier n=300 sample read 0.909/+0.075, but that subset covered only 4 of 6 question
types and under-sampled temporal-reasoning (the weak type, 0.793) — the full-500 number
is the honest one. The CE rerank doesn't move LongMemEval recall@5 (it reorders within
the top-k; the gold session is already in top-5) — its verified lift is on R@1 for hard
fact paraphrases, a different task.

**Anti-interference (HaluMem):** contradiction-detection TPR **~0.66** / FPR
**~0.0125** after the temporal-supersession fix (`docs/BENCHMARKS.md`).

**Justified-Memory truth-maintenance (live audit, honest scope — `docs/JUSTIFIED_MEMORY.md`):**
The ATMS lifecycle (`engram/justified_memory.py`) is reachable live via read-only
`hippo_justified_audit`. Retraction triggers wired: supersession + stale + dependency-cascade,
and now **contradiction (#4)** — an opt-in NLI pass marks mutually-contradicting live facts
`contested` (`audit_facts(contradicted_ids=…)`, `collect_contradicted_ids`). **Two honest
negatives (2026-06-23):** (1) **R28** — auto-populating the typed `derives_from` edge is
*falsified*: a 9-agent map+falsify workflow found 0/3 write-path sites safe (all dedup/
aggregation or delete-their-parents → would re-create the R26 false-cascade), so the explicit
param + read-only audit stays the correct boundary; (2) on the append-only self-corpus the
contradiction trigger's TRUE yield is **~0** (NLI flags are complementary rules / near-dup
notes), which is exactly why it is opt-in + read-only — its value is on evolving FACTUAL
corpora, not this one. `propagate` is dormant by design (0/4588 facts carry a derivation edge).

**Turnkey SDK:** `from engram import Memory` → `add / search / recall / get / delete`,
gate on by default, provenance on reads (`engram/client.py`, `examples/sdk_quickstart.py`).

| Metric (2026-07-01) | Value | Source |
|---|---|---|
| Full test suite | **5941 passed**, 2 failed — both environmental: `test_real_provider_smoke[anthropic]` (no API key by policy) and `test_8_subprocess_x5_all_saves_persist` (load-flaky on this laptop — fails under concurrent pytest storms and intermittently alone, clean re-run passed 2026-07-02; the SLO test spawns 8 real-model subprocesses under a 90 s timeout) | `pytest` 2026-07-04, ~14 min |
| Test files | **764** | `git ls-files 'tests/test_*.py' \| wc -l` (2026-07-01) |
| `engram/` lines of code | **84,345** | `find engram -name '*.py' \| xargs wc -l` (2026-07-01) |
| Dev corpus | ~1262 episodes · ~5410 facts · ~324 skills | SessionStart `~/.engram` live (2026-07-01) |
| Multi-tenant scale | tenant lookup **1270×** (O(N_tenant)), deserialize **3.7×**, ANN crossover ~100k | `SCALE.md` (2026-06-29), commits d1ef0c0 + acc5ee7 |
| Release | v0.7.0 (code, total-rename branch; PyPI live: 0.5.0) | pyproject |

**What Engram is NOT (the nuda verità):**
- **Answer-path "provenance-conditioning" is NOT proven.** An adversarial review found
  the first demo *inflated* (unfair baseline + answer-leaking tags); `docs/SEMANTIC_GROUNDING_STUDY.md`
  Study 3b. The **write-path** moat stands on its own evidence; the answer-path claim does not.
- **Scale — measured, partly hardened, partly open (`SCALE.md`, 2026-06-29).** Recall is exact
  brute-force: 0.6/5.9/28.4 ms @ 10k/100k/500k, RAM linear (~30 GB @ 10M); ANN (HNSW) crossover
  ~100k, prototype validated (recall-pool ~1.0) but **not wired into the live path yet**.
  Multi-tenant lookup + deserialize are FIXED (1270× / 3.7×) and isolation is leak-free; recall
  precision holds to 11k distractors. Open: ANN wiring for global recall >100k, very-large-tenant
  cache-mask, cold-tiering the ~32% quarantined/superseded ballast.
- **Benchmarks are self-run, not third-party-audited.** Numbers are reproducible from the
  repo; they are not an independent leaderboard placement.
- **Single-node SQLite.** Not a distributed/HA store.

---

## 2026-07-04 — HaluMem 3-slice table, honest, vs MemOS's self-report

The P0 is complete: all three official-protocol slices measured on
HaluMem-Medium, 100% local scoring where possible, Claude-judge (declared
asterisk — the official protocol uses gpt-4o; O4 forbids external APIs).

| Slice | Verimem | MemOS (self-reported) | notes |
|---|---|---|---|
| Extraction F1 | **0.6499** (`halumem_extraction_f1_u10s6.json`, 60 sessions, gate ON; OFF 0.6468 — the admission gate lifts precision 0.622→0.643 at −0.02 recall) | 79.7 | regex-tier extractor by design; behind |
| Updating | **0.2867\*** judge-corrected (61-item Claude-judge; local severe OOF 0.3286, selector v3) | 62.1 | behind; but MemOS authors the benchmark (QA ceiling ~67%) |
| QA (C/H/O) | **correct 0.408 / halluc 0.233 / omission 0.358** (`halumem_qa_cho_n120.json`, n=120, strict, 0 errors) | 67.2 | behind on correct — but see the moat angle |

**The honest read.** On raw accuracy Verimem is **behind MemOS on all three
slices** — no spin. What the table doesn't show is the axis that is ours: on
QA, when Verimem can't ground an answer it **omits** (0.358) rather than
fabricate, and the write-path moat (AUROC 0.971, downstream hallucination
95.9→12.2%) is the capability MemOS and every reversed competitor lack. So the
pitch is not "we beat MemOS's number" (we don't) — it's "we're the memory layer
you can trust-condition on", measured honestly against a self-authored
leaderboard whose own ceiling is ~67%. Next levers: extraction granularity
(the shared bottleneck — MemPal's verbatim-baseline finding says extraction is
where information dies) and the tuned-CE selector on the 152 accumulated judge
verdicts.

---

## 2026-07-03 (late night) — HaluMem UPDATING slice: the missing third of the P0 number

Mandate (Aurelio): overtake the competitors. P0 = an honest official-protocol
HaluMem number (MemOS self-reports 79.7 extraction / 62.1 updating / 67.2 QA on
Medium — and authors the benchmark). Extraction + QA harnesses existed; the
**Updating slice did not. Now it does** (`benchmark/halumem_updating_bench.py`,
commit c27410a, 10 unit tests, 100% local — zero claude -p):

- Protocol-faithful (paper + eval/ repo, fetched & verified): chronological
  ingest → per update retrieve top-10 → select WHICH live memory to update →
  correct / wrong (hallucinated update) / missed (+ `missed_unreachable` split
  for retrieval diagnosis). GT matching is e5-cosine 0.86 — only ~34% of
  `original_memories` are verbatim (measured: 179/529 on 3 users).
- **Selector is probe-calibrated, not guessed:** on GT pairs the update
  ENTAILS the original in 9/12 (refinement), contradiction fires 1/12 — a
  contradiction-only selector scores 0/12 (first smoke, kept in the log).
  Score = max(bidir contradiction, entailment(update⊨candidate)), argmax ≥ 0.7.
- **The honest number, three measurement layers deep (full 20 users, n=3122).**
  (1) Local e5@0.86 matcher: 0.6608 — **INFLATED**, the matcher conflates
  "same topic" with "same fact". (2) **Claude-judge pass** (91-item stratified
  sample, official rubric, `halumem_updating_judge_pass.py`, commit ff17e17):
  P(judge=correct | local-correct) = 9/25 → **judge-corrected accuracy
  0.2379** (propagated Wilson ≈ 0.13–0.37); judge agrees 100% with local
  wrong/missed. (3) Matcher recalibrated on the bought verdicts: at e5@0.94
  precision 7/7, FP 0 → offline full rescore **0.1640** (conservative floor;
  hallucinated-update 0.69 at this severity, omission 0.14, unreachable 0.005).
  **Real starting point: ~0.16–0.24 vs MemOS's self-reported 62.1.** Diagnosis
  is clean: retrieval is fine — fine-grained discrimination is the gap (the
  selector fires on thematically-adjacent memories). The 12-item smoke also
  caught truncated artifacts (160-char previews fed to the judge → everything
  "hallucinated"); artifacts now carry full texts.
- **Selector iteration is now offline** (`--dump-candidates` +
  `halumem_selector_sweep.py`, commits 25bdc48/4e5d520): one dump run saves
  every candidate with retrieval score + NLI probs both directions; policies
  are pure post-processing (seconds/round). Round-2 findings (severe e5@0.94
  matcher, reachability ceiling 0.557): retrieval ranking beats both NLI
  signals at GT-rank (top1 0.427 vs 0.32-0.33); **best policy =
  oldvalue-containment override → retrieval-top1 at 0.2540** (v1 0.1646,
  +54% rel). Counter-evidence locked: NLI rerank WORSENS pure retrieval and
  NLI gating kills accuracy — the current cross-encoder does not do
  fine-grained target discrimination. Next lever: a dedicated discriminator
  (from→to feature-rich matching or a small tuned CE), then ONE judge pass on
  the stabilized v2 (no judge spend on intermediates).
- **v3 dedicated discriminator SHIPPED (2026-07-04, commit 0d35426):**
  logistic regression over 17 runtime-legal features per (update, candidate)
  — IDF-weighted rare-term overlap, containment, bigram jaccard, retrieval
  rank shape, from→to old-value containment, numbers, NLI probs — trained
  **out-of-fold per user** (GroupKFold 5; anti-leak + fold-composition tests).
  Severe end-to-end **0.254 → 0.3286** (+29% rel, 2× v1), GT-top1 among
  reachable 0.427 → **0.590**, MRR 0.729. PRE-registered prediction held on
  both metrics (falsification bar was <0.28). Coefficients: idf_overlap +1.97
  dominates; raw retrieval turns NEGATIVE once margin is present — thematic
  affinity is the trap, rare shared terms are the signal; NLI ~0 (r2
  confirmed). Full-fit JSON model exported for NEW corpora only (applying it
  to these 20 users would be leakage; the OOF number is canonical).
- **Judge pass on the stabilized v3 (61 items, 0 errors):
  judge-corrected 0.2379 → 0.2867** (Wilson on sample 0.25–0.49);
  P(judge-correct | local-correct) 0.36 → 0.60. **Metric-honesty finding from
  recalibrating on the 61 bought verdicts:** the v1-era "precision 7/7" at
  e5@0.94 does NOT transfer to the v3 distribution (precision 0.60 @0.94; no
  e5 threshold separates judge verdicts — 0.96 gives 0.73 prec / 0.50 rec).
  The severe local matcher stays valid for RELATIVE policy ranking (the judge
  confirmed the v1→v3 ordering) but is no longer an absolute floor; absolute
  numbers come from judge passes only. Also measured: the 0.44 severe
  "unreachable" share is a matcher-severity artifact, not retrieval failure
  (reachability at the lax 0.86 matcher is 99.5%). Judged records now carry
  full selected/gt texts — every bought verdict doubles as a calibration row
  (152 accumulated: 91 v1 + 61 v3; seed data for a tuned-CE selector).
- Windows note: `SemanticMemory`/`EntityStore` expose no `close()`;
  TemporaryDirectory cleanup needs `ignore_cleanup_errors=True` (core gap).

Next (queued): extraction/QA paced reruns → the honest 3-slice table vs
MemOS (updating slice enters at judge-corrected 0.2867*); selector lever
after that: tuned CE on the accumulated judge verdicts (152 rows and
growing — needs more bought verdicts or synthetic pairs before it can
train), or raise selection quality upstream (extraction granularity).

---

## 2026-07-03 — knowledge/telemetry tiering (the night-2 "next lever")

Night-2's honest finding — residual NLI conflicts were machine telemetry, not
knowledge — is now structural:

- **`engram/_telemetry_prefixes.classify_tier`** — fact tiers
  `knowledge | telemetry | test | dialog` as the single source of truth.
  `dialog/doc*` verbatim transcripts stay recallable but are not reconcile
  subjects; `dialog/voice` stays telemetry. The duplicated exclude tuples in
  `corroboration.py` / `facts_conflict.py` now import `TEST_TOPIC_PREFIXES`
  from the same leaf module (the 2026-06-13 drift lesson, applied again).
- **Reconcile tier guard** (`truth_reconciliation._is_reconcilable`): the
  knowledge-reconcile judge never supersedes NOR contests a non-knowledge fact,
  on either side, short-circuiting before any entity lookup. 14 new unit tests
  (`test_fact_tier_guard.py`, `test_corpus_truth_scan_tiering.py`).
- **Telemetry prefixes +7, each sampled before listing (B2):** `dream/` (26
  live JSON scenario states — the missing prefix night-2 spotted), then the
  first knowledge-only scan exposed machine state nested under knowledge
  namespaces: `pin/` (24 pin/unpin JSON), `skill/catalog/` (49 auto-generated
  registry rows = 395 of 810 scan conflicts), `project/recursive-mas/` (26
  MAS-worker exhaust). Write-route + generic-recall hide inherit by
  construction (admission/semantic sync suite green); live ro smoke: 291
  machine-state facts now behind the generic-recall denylist (was 166).
  NOTE: the running verimem MCP server picks the new prefixes up at its
  next restart (pip -e import already loaded).
- **Scan is tier-aware** (`--tiers`, default `knowledge`) and every report
  carries `tier_composition` (live corpus: 3014 knowledge / 454 test / 291
  telemetry / 78 dialog).
- **Honest measurement note.** Predicted PRE: composition shift (catalog noise
  gone) — confirmed: `skill/catalog` went from 49% of conflicts to absent;
  top conflict topics are now real knowledge (research/memoria-appresa,
  project/clp, project/nexus). But ABSOLUTE conflict counts under a saturated
  pair cap are NOT a stable metric (6k cap: 810 → 20k cap: 730, still capped;
  widening the cap surfaces previously-unjudged knowledge pairs). The ~730
  same-time knowledge conflicts (+12.6k temporal-evolution candidates) are the
  real consolidation backlog for the RelationJudge — prefix work is done.

---

## 2026-07-02 (night 2) — evolving-facts on the REAL corpus: local NLI + reversible cleanup

The truth-maintenance machinery, applied to the live second brain itself (read-only
scan + reversible supersedes, zero claude -p):

- **`engram/local_relation.py` — LocalRelationJudge** (#3): a 3-way NLI RelationJudge
  on a cached cross-encoder, the subscription-independent alternative to the claude -p
  `LLMRelationJudge`. Label order from `id2label` (two cached models disagree),
  symmetric scoring, precision-biased combine. On HaluMem `is_update` GT: update-recall
  **0.02 (lexical) → 0.33 (local NLI large)**, 17×, zero claude -p (default =
  MoritzLaurer DeBERTa-v3-large: false-supersede on the complementary control
  0.196→0.054 vs the base model at equal recall). Opt-in; 12 unit tests.
- **Corpus cleanup — reversible.** `benchmark/corpus_truth_scan_local.py` (local-NLI
  scan) → `scripts/collapse_autohook_snapshots.py` (daily-collapse the pre-compact
  snapshot ballast, −1463) + `scripts/dedup_exact_facts.py` (byte-identical repeats,
  −202). Live corpus **5501 → 3836 (−1665, −30% ballast)**, 1677 superseded, two undo
  journals in `~/.engram/maintenance`, knowledge recall verified intact. 10 plan-logic
  unit tests.
- **Honest finding.** Post-cleanup the corpus is 74% knowledge / 17% machine telemetry
  (test 405, metric 150, dialog 78, dream 26, bus 20) / 9% other. Most residual NLI
  conflicts are telemetry near-duplicates (`bus/consensus/verdicts`, `dream/*/state`,
  `metric/event_*`), NOT knowledge — the knowledge-reconcile judge must not auto-act on
  them; knowledge/telemetry tiering is the next retrieval lever.

---

## 2026-07-02 (night) — critic ghost_cli backend + write-repair FALSIFIED

**(A) Critic-orchestrator v0.5.0 `ghost_cli`** (repo `~/.claude/critic_orchestrator`,
`da29253`, pushed) — the same TRUE-ghost technique as the interactive judge, applied to
the adversarial reviewers: `CRITIC_BACKEND=ghost_cli` runs the FULL triad (incl. the
execution reviewers falsification/caller_verification) in hidden interactive Claude
sisters, **no `claude --print`**. Fresh sister per worker (adversarial independence),
`clp ai-eye` transport + filesystem handshake, tree-kill in `finally`, live-sister
registry + atexit sweep + `CRITIC_GHOST_MAX_SISTERS` cap. 93/93 tests (+18); live smoke:
real pytest ran inside a hidden sister (MainWindowHandle==0 on every sample, zero
`claude.exe` leaked). HippoAgent `bbe362c`: the interactive judge got the matching
lifecycle hardening (atexit sweep + orphan-kill on failed boot — a spawned-but-never-ready
sister used to leak). Critic O3 fine-cycle 2-1 hold (the falsification "fail" was
methodological: greenfield commit, no stash-able pre-fix baseline). **The anti-claude-p
gate is now complete on all three fronts: local v2 CE + interactive judge + ghost_cli
critic workers.**

**(B) Write-repair (#2 from the 07-01 handoff) — FALSIFIED, not wired** (`4a28aa3`).
Idea: on a gate reject, replace the fact with the most fact-anchored VERBATIM source unit
and re-gate that. Bench (`benchmark/write_repair_ab.py`, seed 11, HaluMem heldout, shipped
local v2 judge) killed both pre-registered predictions: **P1 clean-recovery only +7.6pp**
(the premise is obsolete — the "30-39% over-rejection" was the *claude* judge at θ=40;
local v2 already admits **0.924** of clean facts), and **P2 negatives +94.3pp** — re-gating
a span⊆source against that source is tautological (CE saturates ~99.97 > 99.64), so repair
launders assistant-injected false memories in (interference 0.051→0.994). Structural, not
tunable (τ only changes candidate count). Kept as a self-contained falsification harness;
no production module ships. **Consequence for the roadmap: over-rejection is already
handled by v2 → the live lever for "best 2027 memory" is #3 EVOLVING FACTS
(truth-maintenance on update/contradiction) — the category mem0/Tencent don't hold — now
measurable end-to-end WITHOUT claude -p thanks to the local/ghost judge.**

---

## 2026-07-02 (evening) — gate v2 (real-register distill) + interactive-CLI backend

Two follow-ups after the v1 gate below, both shipped opt-in on main:

**(1) Gate v2 — the real-corpus register.** v1 (HaluMem-only) under-admitted Aurelio's
real notes (phase-3: agreement 0.756, real-fact admit 0.817 — compressed technical
notes RFC/OID/sigles are out of HaluMem's dialogue distribution). Fix: distill the
claude admit DECISION (not its score — soft labels collapsed the slice) on a mix of
HaluMem GT + ~330 real-corpus pairs claude-labeled once (`benchmark/local_gate_distill_v2.py`;
labels under `~/.engram/local_gate/`, never in the repo). Verified on the model on disk
(threshold 99.64): **real-register test (90 held-out items) agreement 0.889, real-fact
admit 0.983** (v1 0.817), AUROC 0.935; **HaluMem heldout AUROC 0.99, interference-admit
0.023** (v1 0.086 — the anti-false-memory skill IMPROVED, not lost), clean 0.921.
`local_gate_ce_v2` is now the shipped `DEFAULT_MODEL_DIR`. **No default flip:** the
backend stays opt-in — real-register agreement 0.889 is below the 0.95 bar I set for an
automatic flip (and swap-negative labels are noisy: claude itself admits ~30%). Honest
race caught + fixed: a first eval read a mid-training checkpoint; numbers above are the
re-run on the final on-disk model.

**(2) Interactive-CLI judge — Claude judge without claude -p.** `ENGRAM_GROUNDING_BACKEND=
interactive` routes the gate to a TRUE-ghost interactive Claude CLI (spawned hidden from
birth: claude.exe under CREATE_NEW_CONSOLE + STARTUPINFO SW_HIDE — window never shown,
ai-eye AttachConsole still reads/injects; folder-trust dialog auto-confirmed). Flat
subscription, no claude -p. Validated live: E2E 4/4 correct in 32.6 s, and a decision-
agreement probe 10/10 vs the claude -p judge. `engram/interactive_judge.py` (transport-
injected, filesystem handshake), fail-over to the injected llm, 6 unit tests. Same ghost
transport is the plan for the critic-orchestrator workers (still on `claude --print`).

## 2026-07-02 local gate — distilled judge ships (opt-in), attribution axis opened

The write-gate no longer NEEDS `claude -p` (the paid-headless constraint): a
deberta-v3-base fine-tuned on HaluMem ground truth (train/heldout users disjoint,
threshold from an unseen val slice) replaces the judge at zero API cost.
**Heldout n=4712** (`benchmark/results/local_gate_finetune_v1_extended.json`): AUROC
**0.983**, clean-admit **0.948** [0.940, 0.955], assistant-injected false-memory admit
**0.086** [0.072, 0.102], foreign 0.024; ~88 ms single / ~15 ms batched. The claude
judge on the same pipeline: clean 0.80, **interference admit 0.40** (n=15,
`attribution_probe_claude.json`) — the **ATTRIBUTION finding**: HaluMem interference
points sit VERBATIM in the dialogue as assistant turns, so every entailment-only judge
admits them; the distilled gate learns the distinction from interference negatives (the
student beats the teacher where the teacher is structurally blind). Zero-shot was
honestly falsified first (doc-level 0.60 → sent-max+speakers 0.75-0.81, not shippable),
and the 07-01 handoff's "free training data in `grounding_score` v12" was FALSIFIED
(column empty, 0/5412). Wiring: `engram/local_grounding.py`,
`ENGRAM_GROUNDING_BACKEND=local`, calibrated `gate_config.json` beside the model,
fail-over to the injected llm, 40 gate tests green. **Honest scope:** in-distribution
(HaluMem EN, same generator); default stays claude until phase-3 validation on the real
IT corpus (one-shot claude labeling + agreement). Commits `fb614d5` → `64fd783`.
**Critic O3 (2-1 fail) found the calibrated cut did NOT reach production L4** (the live
path calls `fact_grounding_score`, not `should_store_fact`; measured cost at θ=40:
interference-admit 0.115 vs 0.086) plus a silent-uncalibrated edge — both FIXED same
night: `fact_grounding_score_ex → (score, judge)` + `resolve_write_threshold_for(judge)`
at every site incl. L4 and fail-over; 63 gate tests green. See BENCHMARKS.md
"Adversarial review of the local gate".
**Phase-3 real-corpus validation (2026-07-02, n=90, both judges on the SAME 1500-char
span): NO default flip.** Agreement 75.6%; real-fact admit local 0.817 vs claude 0.967.
Root cause is REGISTER, not language: conversational Italian transfers fine (97-99
scores; live demo 7/8 incl. attribution-reject), but compressed technical notes
(RFC/OIDs/sigles) score 0.2-8 where claude gives 82-96 — HaluMem is dialogue-only.
Swapped-negative labels are noisy (multi-topic episodes; claude admits 30% too).
The 90 claude labels are banked as free v2 training seed (extend to ~400 + re-distill
mixed HaluMem + technical-note register; result JSON kept LOCAL — personal corpus).
Default stays claude; the opt-in architecture is doing exactly its job.

## 2026-07-01 consolidation (real state, post-drift)

Work since 2026-06-23 was real but **fragmented and un-consolidated** — STATE.md was stale,
comparison runs sat uncommitted in the working tree, and the CI badge was red. This section
reconciles the true picture; numbers are either verified this session or attributed to the
named source (no re-measurement claimed where none was run).

**Retrieval — a TIE, not "behind" (correcting an earlier mis-frame).** Apples-to-apples on
LoCoMo with the SAME claude judge (`SCALE.md` §Quality, n=30 QA): Engram retrieval **0.80** =
full-context ceiling **0.80** = mem0-style extract **0.80** (tie within n=30 noise), at a
fraction of the tokens, and Engram leads on adversarial/abstention (100%). External **Mem0 66.9
/ Zep 66.0** use a *different* judge and are NOT directly comparable (Zep's own 84→58 across
methodologies shows ±25 pp of pure judge/protocol variance). A larger LoCoMo QA run
(`benchmark/results/cmp_engram*.json`, n=120, LLM-judged) recorded baseline **0.75** and a tuned
per-turn-chunk config **0.833** — exploratory, the "spinto" config is not yet fully
characterized, so it is committed as an artifact but NOT headlined.

**Scale — multi-tenant hardened (2026-06-29, `SCALE.md`, commits d1ef0c0 + acc5ee7).** Measured
walls (real corpus + synthetic one-cost tests): tenant lookup O(N_total)→O(N_tenant) **1270×**
(range-query + `INDEXED BY`), batch-deserialize **3.7×** (byte-identical), recall precision flat
to 11k distractors, ANN (HNSW) crossover ~100k with a prototype validated on the real corpus
(recall-pool ~1.0), tenant isolation 0 leak / 50 recalls. Open projects (not one-liners): wire
ANN into global recall >100k, very-large-tenant (>10k facts/tenant) cache-mask, cold-tier the
~32% quarantined/superseded ballast.

**A1 gate over-rejection (2026-06-23, this session) — honest split.** `select_relevant_span` +
`fact_grounding_score(focus_budget=)` + env `ENGRAM_GROUNDING_FOCUS_CHARS` (committed `d077563`,
55 targeted tests): span-selecting the source lifts clean-admission **0.70→0.80** at a FIXED char
budget, noise-rejection **100%** (diagnostic `halumem_gate_source_ab.json`, n=20/10/8). BUT the
"net-positive downstream correct↑" hypothesis was **FALSIFIED** on the moat — `correct` stays
~0 in both arms *by construction* (the moat is a hallucination-vs-abstention stress test, not a
correctness benchmark; span n=5u correct 0.000 vs baseline 7u 0.031, both ≈noise). Net: a
token-efficiency + admission-at-budget win, **not** a correctness win. The abstraction-crediting
judge variant was re-falsified even on the full window (+0.0). Proper next test = a correctness
benchmark where an admitted fact makes its question answerable (not the moat).

**CI red = BILLING, not code.** GitHub Actions jobs don't start ("recent account payments have
failed"), so the badge is red on every recent commit regardless of code. The full suite passes
locally (see the metrics table). This is a payment/ops issue, not a broken build.

---

## What is Engram, in one line

A **persistent memory layer** for LLM agents (Claude Code, Cursor, opencode,
Cline, Continue, any MCP host). Episodes → consolidated skills → deterministic
macros, all inspectable as SQLite + Markdown artifacts. Open-source,
production-hardened, MCP-native. Now with **algorithmic LLM-free skill
discovery** from the fact graph (cycle 213-250).

## Current metrics

> Superseded — see the **Current state (2026-06-20)** table at the top of this file for
> the live numbers (5731 tests, 83,761 LOC, ~4.5k facts). The figures previously listed
> here (2026-05-23: 1921 facts / 60k LOC / "Test count TBD") were stale and contradicted
> the top; removed to keep one honest source.

## Verified capabilities (real benchmarks, repeatable)

### LLM-free emergent skill discovery pipeline (cycles 213→250) — NEW

End-to-end algorithmic skill discovery from the fact graph, zero LLM tokens
spent on the discovery + draft step:

```
detect_emerging_skills (213)           Louvain + topic purity + cohesion
  → normalize_topic (214/215)          family-key collapse, aggressive truncate
    → skill_drafter (217)              deterministic Markdown body + ranked keywords (EN+IT stopwords cycle 220)
      → skill_draft_persist (222)      ~/.engram/skill_drafts/<ts>/<name>.md
      → emerging_skill_register (229)  topic=emerging_skill/auto-discovered/<name> in semantic.db
      → 4th Auto-Dream seed (219)      wired into propose_dream_tasks instructions
      → adaptive_threshold (248/249)   curve (1305→0.40) / (1889→0.20) / (5000→0.10)
      → promote_emerging_to_skill (235) gateway to SkillLibrary candidate
```

**5 MCP tools** expose the pipeline:
- `hippo_emerging_skills_draft` (cycle 218) — detect + draft in one call
- `hippo_emerging_skills_register` (cycle 232) — on-demand register as fact
- `hippo_emerging_skill_promote` (cycle 236) — fact → candidate Skill
- `hippo_skill_drafts_list` (cycle 227) — read persisted batches
- `hippo_emergence_pipeline_status` (cycle 239) — aggregate observability

**6 helper scripts** for empirical observability + tuning:
- `scripts/emergence_dashboard.py` — textual aggregate snapshot
- `scripts/emergence_threshold_sweep.py` — purity × cohesion grid
- `scripts/inspect_emerging_cluster.py <needle>` — deep-dive one cluster
- `scripts/pilot_snapshot.py` — H1 promotion-rate baseline (cycle 175.2 scaffold)
- `scripts/bench_emerging_pipeline.py` — latency probe (p50=279ms, p99=378ms on 1708 facts)
- (`engram/adaptive_threshold.py` — corpus-size-aware curve)

### Auto-Dream worker — 4-hook composition + auto-register

Every firing now writes to **3 locations** (cycle 230):
1. `~/.engram/dreams/auto-<ts>/dream_tasks.json` (cycle 34 base)
2. `~/.engram/skill_drafts/<ts>/<name>.md + .meta.json` (cycle 223)
3. `semantic.db` facts WHERE topic LIKE 'emerging_skill/%' (cycle 230)

Instructions seed concatenates 4 soft hints (cycle 175.1 + 187 + 211 + 219):
- stuck-list retry candidates
- top Louvain community cohesion
- Thompson posterior-sampled warm-up
- emergent skill DRAFT hint (cycle 219, adaptive purity+cohesion cycle 248-249)

### Empirical singolarità #18-#21 (cycle 230, 237, 240/241, 242/246) — NEW

- **#18 SELF-APPLYING LOOP** — Auto-Dream discovery runs without any LLM token. Confirmed empirically (cycle 230 firing with `new_items=2170` on live corpus).
- **#19 LINEAGE BACKWARD NAVIGATION** — `clp chain show <emerging_id>` walks back 23 hops to source cluster ancestry (cycle 237 wires `lineage_to = first source fact_id`).
- **#20 SHADOW ZONE DISCOVERIES** — at purity=0.2 the matrix surfaces 4 candidates (`master-fact`, `antigravity-reverse`, `deep-clp`, `loop29-lineage`) vs 1 at default 0.4 (cycle 240/241).
- **#21 OBSERVER-SHIFTS-EMERGENCE** — re-running the same threshold sweep 4 min after registering shadow candidates moved 3 of them BACK under threshold. The session's own writes shift the Louvain partitioning (Heisenberg-like effect on emergence detection). Cycle 246 second confirmation: 40 min of corpus growth (+181 facts) defragments master-fact into 3 sub-clusters with purity 0.11-0.19 — default 0.4 surfaces zero.

### Critical bug fix (cycle 216) — A1 onesto

`_live_dirs_from` in `auto_dream_worker.py` was silently routing Auto-Dream to the **empty** legacy `~/.engram/semantic.db` (36 KB, 0 facts) instead of the canonical `~/.engram/semantic/semantic.db` (7.4 MB, 1708 facts). Every Auto-Dream firing since the package restructure had been operating on the empty DB — every "triggered=true" was vacuous. Cycle 216 fixes the path resolution; post-fix `new_items=2170` (vs `14` pre-fix).

### Hippo Dreams pipeline (cycles #34-#40, baseline preserved)

Subscription-first skill consolidation. Immutable shadow → review → adopt
with atomic rollback. End-to-end on production corpus (~318 skills baseline):

| Stage | Time | Notes |
|---|---:|---|
| `propose_dream_tasks` | 522 ms | cluster episodes, no LLM |
| `submit_dream_result` × 10 | 18.3 s | 1.83s/task host LLM call |
| `dream_status` + `dream_diff` | 1.15 s | read-only review |
| `adopt_dream` | 784 ms | atomic backup + apply |
| **End-to-end (10 skills)** | **20.8 s** | + double-adopt rejected, prod intact |

### Macro fast-path (Anthropic Opus 4.7, 5 iter × 8 digit-sum tasks)

| Iter | Engram tokens | Engram latency | Raw LLM tokens | Raw LLM latency |
|---|---:|---:|---:|---:|
| 0 (cold) | 4225 | 4.47 s | 59 | 0.67 s |
| 1 | 1711 | 0.92 s | 59 | 0.71 s |
| 2 | 687 | 0.52 s | 59 | 0.85 s |
| **3** | **0** ✅ | **0.22 s** | 59 | 1.08 s |
| **4** | **0** ✅ | **0.24 s** | 59 | 0.69 s |

Break-even at iter 3. Macro hit rate: 70% on recurrent work.

### Compositional generalization (96 calls, 4 providers, baseline preserved)

| Provider | raw | Engram | Δ Lv5 |
|---|---:|---:|---:|
| Anthropic | 42% overall, 0% Lv3-5 | 100% Lv5 | +100% |
| DeepSeek | 25% overall | 100% Lv5 | +100% |
| OpenRouter | 33% overall | 100% Lv5 | +100% |
| Groq | 25% overall | 83% overall | +100% |

LLM raw collapses to 0% at depth 3+. Engram stays at 100% on 3/4 providers.

## What's still prototype / known gaps

| Area | Current state | Gap |
|---|---|---|
| **H1 promotion-rate pilot** | baseline 2.15% captured (cycle 244 scaffold) | 20-cycle multi-day execution NOT run; pipeline ready |
| **Singolarità #21 cure** | tuning scaffold (cycle 246-249) | real fix needs second-pass community detection over master super-cluster |
| **Emerging skills adoption** | promotion gateway (cycle 235) | no production trial loop yet — manual review required |
| **Cycle 228 H8c parallel_drafter** | shipped + FALSIFIED 1.28×<1.5× | not wired in prod (value-as-boundary) |
| **Adaptive threshold 4th anchor** | curve has 3 anchors @ 1305/1889/5000 | needs measurement at 3000-4000 facts when corpus crosses |
| **PyPI distribution** | name **`verimem`** (renamed 2026-07-04) | to reserve on PyPI before announce |
| **Dashboard live push** | polling-based | sub-second EventBus or SQLite WAL hook |
| **Hosted cloud variant** | local SQLite only | Postgres + S3 backend (long-term) |

## What's genuinely original (cycle 213+ additions)

- **LLM-FREE algorithmic emergent skill discovery** — Louvain + topic purity + cohesion fusion produces draft skills + trigger keywords (EN+IT stopword-filtered) WITHOUT spending tokens. The downstream LLM call is OPTIONAL polish (cycle 217).
- **Self-applying memory pipeline** (singolarità #18) — Auto-Dream firing writes back into the same corpus it observes; the OBSERVER is part of the system, causing measurable Louvain partition shifts (singolarità #21).
- **Cross-fact lineage navigation** (singolarità #19) — every emerging_skill fact carries `lineage_to = first source fact_id`; `clp chain show` walks 23 hops back to its origin.
- **Corpus-size-aware adaptive thresholds** (cycle 248-249) — piecewise-linear curve auto-tunes the detector's gates as the corpus grows, with empirical anchors.

Baseline original mechanisms preserved:
- **Subscription-first consolidation pipeline** — zero extra API spend.
- **Compiled-macro deterministic bypass** — skills compile to AST → exec, bypassing the LLM entirely on recurrent tasks.
- **11 neuroscience-inspired memory mechanisms** opt-in: DG pattern separation, TCM, synaptic tagging, lateral inhibition (Földiák 1990), engram crossover, schema priming, spontaneous reactivation (Born & Wilhelm 2012), salience by surprise (Buzsáki 2015), trace alignment, working memory pruning.

## Comparison vs alternatives (updated 2026-05-23)

|  | Engram | Anthropic Dreams | Google ReasoningBank | MemSkill | MemOS / MemMachine 2026 |
|---|:-:|:-:|:-:|:-:|:-:|
| Skill consolidation loop | ✓ | – | ✓ | ✓ | ✓ |
| Immutable shadow + review + adopt | ✓ | ✓ | – | – | partial |
| Subscription-first (host LLM) | ✓ | – | – | – | – |
| Compiled-macro bypass | ✓ | – | – | – | – |
| **LLM-free algorithmic discovery** | ✓ (cycle 213) | – | – | – | partial (MAG paradigm) |
| **Self-applying observer-effect documented** | ✓ (singolarità #21) | – | – | – | – |
| Open source + production-ready | ✓ MIT | proprietary | proprietary | paper only | mixed |
| MCP native | ✓ | N/A | N/A | N/A | N/A |

Engram is the only **open-source production-ready** skill-consolidation
system with native MCP integration AND empirically-documented self-applying
observer-effect mitigation.

## Architecture (high-level, updated 2026-05-23)

```
┌─────────────────────────────────────────────────────────────────┐
│                      Engram                                     │
│                                                                 │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐            │
│  │  WAKE      │ →  │  SLEEP     │ ←  │  HIPPO     │            │
│  │  ReAct +   │    │  consol +  │    │  DREAMS    │            │
│  │  episodic  │    │  skill mng │    │  (v0.2.0+) │            │
│  └─────┬──────┘    └─────┬──────┘    └─────┬──────┘            │
│        │                 │                 │                   │
│        │  ┌──────────────┴─────────────────┴──────────────┐    │
│        │  │ Auto-Dream worker (cycle 69+219+230+249)      │    │
│        │  │ 4-hook seed: stuck + community + thompson +   │    │
│        │  │   emergence (adaptive threshold cycle 248)    │    │
│        │  │ writes: dream_tasks.json + skill_drafts/ +    │    │
│        │  │         semantic.db emerging_skill/*          │    │
│        │  └───────────────────────────────────────────────┘    │
│        ▼                 ▼                 ▼                   │
│  ┌────────────────────────────────────────────────────┐        │
│  │   Persistent layer: SQLite (3 DBs) + .md           │        │
│  │   • episodes.db (444)  • semantic.db (1921 facts)  │        │
│  │   • skills.db (326)    • skills/*.md (inspectable) │        │
│  │   • emerging_skill/auto-discovered/* (cycle 229)   │        │
│  └────────────────────────────────────────────────────┘        │
│                          ▲                                      │
│  ┌────────────────────────────────────────────────────┐        │
│  │   MCP server (stdio JSON-RPC) — ~215 tools         │        │
│  │   5 emergence tools (cycle 218/227/232/236/239)    │        │
│  │   Dashboard (FastAPI) — web UI 127.0.0.1:8765      │        │
│  │   CLI (`hippo` / `engram`) — Typer + Rich          │        │
│  └────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## Roadmap (priority-ordered, honest effort, post-cycle-250)

1. **CYCLE 251+ short term** (next session):
   - Adaptive threshold 4th anchor (3000-4000 facts) when corpus crosses
   - hippo_emerging_skill_promote production trials (real Skill rows in `~/.engram/skills/`)
   - Cycle 175.2 H1 promotion-rate pilot 20 multi-day cycles
   - **Singolarità #21 cure**: second-pass community detection over master super-cluster (depth-2 Louvain)
2. **B — Dashboard live push** (1-2 cycles)
3. **PyPI publish `engram-memory`** (~1h, after v0.4.0 release tag)
4. **Test coverage 59% → 70%+** (2-3 cycles TDD)
5. **Hosted cloud variant** (long-term project)

## Key documents

| Audience | Read this |
|---|---|
| First-time visitor | [`README.md`](./README.md) |
| **Current state + roadmap** | this file (`STATE.md`) |
| Version history | [`CHANGELOG.md`](./CHANGELOG.md) |
| **Emergence pipeline quickstart** | [`docs/emergence/README.md`](./docs/emergence/README.md) (cycle 245) |
| MCP integration in 5 min | [`docs/MCP_QUICKSTART.md`](./docs/MCP_QUICKSTART.md) |
| Architecture deep-dive | [`docs/PLATFORM.md`](./docs/PLATFORM.md) |
| SOTA design docs (5) | [`docs/sota/`](./docs/sota/) |
| Memory Protocol (auto) | [`docs/MEMORY_PROTOCOL.md`](./docs/MEMORY_PROTOCOL.md) |
| Contributing | [`CONTRIBUTING.md`](./CONTRIBUTING.md) |
| **Historical audits + R&D** | [`docs/archive/`](./docs/archive/) |

## Cross-instance handoff (next session)

```bash
# 1. Read MASTER FACT v2 ULTIMATE (cycle 215-250 narrative)
clp chain show 3a7284f360cf

# 2. Live emergence pipeline state
python -m scripts.emergence_dashboard

# 3. H1 pilot baseline delta (re-run for future comparison)
python -m scripts.pilot_snapshot

# 4. Current emergence threshold matrix
python -m scripts.emergence_threshold_sweep

# 5. Emergence pipeline quickstart
cat docs/emergence/README.md
```

## Honest disclaimer (updated 2026-05-23)

Engram is a **production-ready prototype with real assets** (full pipeline,
repeatable benchmarks, TDD+critic discipline, ~215 production-ready MCP
tools, **4 empirical singolarità documented** for the self-applying memory
case). It is **not yet a published PyPI product** — that's the v0.4.0
target post-cycle-250.

A4 onesti caveats from the cycle 213-250 burst session:
- **Emergence pipeline ships but produces 0 candidates at default thresholds on the current 1921-fact corpus** (requires p≤0.1; adaptive curve will auto-drop when corpus crosses 3000-4000). This is FUTURE-PROOFING, not immediate emergence boost.
- **Promotion rate 2.15%** is BELOW the cycle-174 audit baseline 4.3% (retired pool grew from 0 to 156 since cycle 174). H1 pilot multi-day required.
- **Singolarità #21** (observer-shifts-emergence) is documented but NOT cured — only tuned around with adaptive thresholds.
- **Cycle 228 H8c parallel_drafter** FALSIFIED on live corpus (1.28× < 1.5× target). Shipped as value-as-boundary knowledge.

If you're evaluating it for production use:
- ✅ Memory layer for Claude Code: production-ready (444 episodes on the maintainer's daily-driver setup).
- ✅ Emergent skill discovery layer: shipped, observability-complete, awaiting more corpus growth for visible candidates.
- ⚠️ Multi-user / hosted: not yet supported (local SQLite, single-user).
- ⚠️ Distribution: install from source/git for now; PyPI v0.4.0.
- ❌ Drop-in for cloud agent platforms: needs hosted variant first.

---

_This document is the only file in the repo that stays continuously
updated. Everything in `docs/archive/` is frozen-at-date snapshot._

## Dormant capabilities (audited 2026-06-21 — honest "wired vs not")

Zero live callers — but, on closer read, these are **deliberately STAGED capabilities**
(built + tested, awaiting a benchmark-then-wire decision per the repo's own
"measure before you flip it on" discipline), NOT careless dead code to delete:
- `retrieve_pagerank` (`hippo_pagerank.py`) — HippoRAG-2 dual-cue PPR fusing skill-fitness
  and episode-relevance (arXiv:2502.14802). DISTINCT from the live entity-fact PPR
  (`entity_kg.ppr`). Algorithm is sound (runs ~15 s/query on the 527-ep/324-skill corpus,
  bounded + error-caught). **Measured why it's sparse here (2026-06-21, corrected): NOT a
  data bug.** Of the 519 `skills_used` values that don't match a `Skill.id`, **100% are
  external Claude-Code skill SLUGS** (`hippoagent-memory`, `clp-bughunt-discipline`, … =
  `~/.claude/skills`), **0 are stale hashes**; ~80% of all skill-usage is these external
  skills. They are legitimately NOT Engram SkillLibrary skills, so they correctly have no
  graph node — there is nothing to "canonicalize" (an earlier note wrongly said so). PPR
  operates over Engram-consolidated skills; this dev corpus is just dominated by external-
  skill usage, so the graph is naturally sparse. To wire+eval meaningfully needs a workload
  where episodes reuse Engram SkillLibrary skills densely — a workload question, not a fix.
- `assess_claim_trust` (`tier2_judge.py`) — **GRADUATED 2026-06-21** (no longer dormant).
  Was staged with no concrete judge; now: built `LLMJudge`, benchmarked the triage
  (conservative prompt → **1.0 noise-recall / 0.0 false-declass**, n=24), added the
  `triage_corpus` pass + reversible `SemanticMemory.quarantine_fact`, and WIRED it into the
  consolidation cycle (`SleepEngine._stage_tier2_triage`, before pruning, capped 50/cycle,
  fail-safe). Live end-to-end behind `ENGRAM_EVIDENCE_REQUIREMENT` (default off): env →
  cycle → triage_corpus → assess_claim_trust → LLMJudge → quarantine. Complementary to the
  read-time `trust_score`. 388 sleep/tier2 tests green.

(Earlier draft mislabeled these "dead code / redundant-remove" — corrected: both are
staged-pending-benchmark, the same pattern that just graduated apply_topic_penalty and the
reconcile-NLI judge once measured.) Wired live: `apply_topic_penalty`,
`group_by_topic_family`, `find_numeric_conflicts`, `reconcile_new_fact` (+ NLI judge),
the grounding gate (L4), the PPR fusion, grounding-aware trust ranking (opt-in).
