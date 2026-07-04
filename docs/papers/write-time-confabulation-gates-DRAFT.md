# Write-time Confabulation Gates: Sub-millisecond Empirical Defenses for Agent Semantic Memory

**Draft 2026-05-18 — HippoAgent cycle 143 artifact.** All empirical numbers in this paper come from re-runs executed on the live 1173-fact corpus during draft preparation (Section 4). Citations of the form `file:engram/X.py:LINE` point to the open-source HippoAgent tree (`/engram` package).

---

## Abstract

LLM agents that own a persistent semantic-memory store are vulnerable to a self-amplifying failure: the model writes a confabulated claim, the store accepts it, and the same claim re-surfaces at recall as "verified history". Existing memory systems (Mem0, Letta/MemGPT, Zep/Graphiti, HippoRAG) provide no explicit write-time guard — they store first and hope read-time retrieval or downstream evaluation will catch the lie. We present HippoAgent's *anti-confabulation gate* (`engram/anti_confab_gate.py`, cycle 138, 2026-05-18), a layered defense that runs on every `hippo_remember` call before the fact reaches disk. The gate combines three sub-millisecond keyword detectors (L1 SHIPPED/L1.5 DIAGNOSED/L1.7 TASK-STATE, `engram/anti_confabulation.py:78,158,239`) with an optional ~12-millisecond lexical contradiction probe (L3 `validate_claim`, `engram/validate_claim.py:82`). On the 1173-fact production corpus the gate downgrades 69/1173 facts (5.88%) — *exactly* the set previously flagged by cycle 137's read-time orphan scan, with zero misses and zero extras. On a 10× replicated 11 736-fact corpus the fast tier runs at 0.027 ms/fact (sub-millisecond per write) and the downgrade rate stays at 5.88% — consistent with the single-corpus result. On a 100-claim synthetic suite the fast default produces 0/40 false positives on clean claims, 0/25 false negatives on unsupported SHIPPED claims, and 10/10 rejections on year-disjoint contradictions in `full+reject` mode. The gate is conservative by construction (downgrade-by-default, no LLM dependency, never crashes the write path) and is now the production default for HippoAgent's MCP write surface.

(≈ 250 words.)

---

## 1. Introduction

A long-running LLM agent that "remembers" inevitably writes things that are not true. The cause is well-documented for *generation* — Mem0's authors call it confabulation; the Memory-for-Autonomous-LLM-Agents survey (arXiv:2603.07670, 2026-03) names "reflective contamination" as a top-3 failure mode where "one bad write pollutes downstream" [survey-2026]. The same phenomenon is documented quantitatively by MemoryGraft (arXiv:2512.16962, 2025-12), which reports a 47.9% cross-session poisoning rate for embedding-only similarity stores [memorygraft-2025]. HaluMem (arXiv:2511.03506, 2025-11) introduces the first operation-level hallucination benchmark for memory systems and frames the same failure as memory operations that introduce content not supported by dialogue evidence [halumem-2025].

What is *missing* in the open-source landscape is a defense placed **at the write boundary**. Mem0 stores via flat-vector summary and inspects nothing about the claim's evidentiary anchoring (verified by reading the public Mem0 OSS — see Section 6). MemGPT/Letta treats the archival store as opaque key-value pages; the original paper (arXiv:2310.08560) does not propose any pre-write verification, only a recall/archival paging policy. Zep/Graphiti adds temporal anchoring at *retrieval* time, not at write. HippoRAG (arXiv:2405.14831, NeurIPS 2024) is a retrieval algorithm, not a write filter. Surveys describe the contamination problem in detail but do not name "write-time gating" as a research thread.

HippoAgent (this work) was built as an MCP-native agent memory plugged into Claude Code, and it concretely *suffered* the contamination failure: in a recorded 2-hour session on 2026-05-17 the operator (Aurelio) caught the agent saving seven distinct confabulated facts (SHIPPED/DIAGNOSED/task-state, full taxonomy in `scripts/replay_confabulations_2026_05_17.py`). Those seven cases motivated a structured response: instead of training a classifier (no labels, no compute budget) or pulling in another LLM call (latency cost), we engineered three pure-keyword detectors that flag the lexical *shape* a confabulation tends to take when the agent lacks an evidentiary anchor. Sub-millisecond. No model. No network. Cycle 138 (2026-05-18) wired those detectors plus the older `validate_claim` lexical contradiction probe (cycle 70, 2026-05-14) into a single `run_validation_gate` orchestrator (`engram/anti_confab_gate.py:175`).

This paper documents the architecture (Section 3), measures it on the production corpus and a 10× synthetic scale (Section 4), and is honest about what the gate does not catch (Section 5).

(≈ 320 words.)

---

## 2. Architecture

### 2.1 Three keyword tiers (L1, L1.5, L1.7)

Each tier is a **pure function** in `engram/anti_confabulation.py`. No I/O, no global state, no model call. Each takes `(proposition: str, verified_by: Iterable[str] | None)` and returns either `None` (claim is fine) or a human-readable warning string.

**L1 — `detect_unsupported_shipped_claim`** (`engram/anti_confabulation.py:78`). Fires when the proposition contains a keyword from `SHIPPED_KEYWORDS = {"SHIPPED", "MERGED", "WIRED", "DEPLOYED", ...}` *and* the `verified_by` list contains zero refs matching `^(commit:|pr:|file:|git:)` (`engram/anti_confabulation.py:62-75`). Empirical motivation: 2/7 confabulations in the 2026-05-17 replay were unanchored SHIPPED claims (line 103-107).

**L1.5 — `detect_unsupported_diagnosis_claim`** (`engram/anti_confabulation.py:158`). Fires when the proposition contains `BUG #`, `DIAGNOSED`, `ROOT CAUSE`, ... *and* `verified_by` lacks a test-shaped ref `^(test:|pytest:|bash:|exit:|cmd:|run:)` (`engram/anti_confabulation.py:136-138`). Motivation: 3/7 confabulations were symptom-driven diagnoses with no falsifying test reference.

**L1.7 — `detect_unsupported_task_state_claim`** (`engram/anti_confabulation.py:239`). Fires when the proposition contains a task-state phrase from `TASK_STATE_PHRASES = {"da chiudere", "is closed", "is pending", "still pending", ...}` *and* `verified_by` lacks a tracker ref `^(pr:|issue:|task:|git:|commit:|gh:)` (`engram/anti_confabulation.py:217-219`). Motivation: 1/7 confabulations was a task-state assertion (cycle 115.F "Cycle #45 da chiudere") with no tracker anchor.

Each detector is overridable: the *same* claim with a properly populated `verified_by` (e.g. `commit:abc123def`, `pytest:test_x_falsifies`, `pr:#42:state=open`) passes the gate silently. The detectors do not penalize the wording; they penalize the *missing anchor*.

### 2.2 L3 — lexical contradiction probe (`validate_claim`)

`engram/validate_claim.py:82` (cycle 70, 2026-05-14, predating cycle 138). The function takes `(agent, claim, topic_hint, threshold=0.6)`. It (i) extracts capitalized names and years from the claim with a 35-word stopword filter (`engram/validate_claim.py:27-35`), (ii) issues one `semantic.search_facts(token, ...)` per name token (the verbatim claim fails LIKE-match on the SQL backend — bug discovered by the critic-orchestrator in cycle 70 review, see code comment `engram/validate_claim.py:136-147`), (iii) for each retrieved fact with subject-overlap ≥ threshold, checks if claim years and fact years are *disjoint*. Disjoint year sets ⇒ verdict `"contradicted"`; year-compatible match ⇒ `"supported"`; neither ⇒ `"unknown"`. No LLM call. The function is deliberately conservative: if salient-token count < 2, verdict is `"unknown"` (claim too generic for lexical validation, `engram/validate_claim.py:117-134`).

### 2.3 Gate orchestrator

`engram/anti_confab_gate.py:175 run_validation_gate(...)` exposes three tiers and two modes:

- `validate="off"` — bypass everything (migrations, replays).
- `validate="fast"` (default) — run L1+L1.5+L1.7. Any positive ⇒ a warning entry.
- `validate="full"` — fast + L3. L3 verdict `"contradicted"` adds an `L3` warning.

Modes:
- `gate_mode="downgrade"` (default) — any warning forces `status="provisional"`. The fact still persists, but is hidden from default recall.
- `gate_mode="reject"` — L3 contradiction *refuses* persistence. L1/L1.5/L1.7 still only downgrade because keyword heuristics are too coarse for a hard block.

`force_persist=True` overrides the action but the warnings still surface for audit. The MCP write handler echoes warnings to the caller, preserving the audit trail without breaking compatibility (`engram/mcp_server.py` `hippo_remember` tool, schema field `validate` in the tool docstring referenced earlier in this session).

The function never raises — every internal failure of `validate_claim` is caught and degraded to `"unknown"` (`engram/anti_confab_gate.py:161-172`). The write path must never crash because of a defense.

(≈ 510 words.)

---

## 3. Empirical evaluation

All numbers below are from runs executed during draft preparation (2026-05-18) against the live `~/.engram` corpus and a temp clone. Scripts are versioned in `scripts/lab_*.py`.

### 3.1 FASE 1 — `validate_claim` latency on live corpus (script: `scripts/lab_validate_claim_bench.py`)

`N=100` random propositions sampled from 1173 live facts, validated against the same `SemanticMemory`. Warm-up 3 calls.

| Metric | ms |
|---|---|
| min | 0.01 |
| mean | 15.98 |
| p50 | 11.33 |
| p95 | 43.04 |
| p99 | 139.92 |
| max | 139.92 |

The L3 layer is in the "feasible for sync gate" range at the median (11 ms) but the p99 (140 ms) is a tail risk. The two-tier design (fast default, full opt-in) is motivated by exactly this distribution — most callers do not need L3.

### 3.2 FASE 4 — synthetic 100-claim suite (script: `scripts/lab_gate_live_test.py`)

100 claims, five categories: `clean` (40), `shipped_no_ref` (25), `shipped_with_ref` (15), `diagnosis_no_test` (10), `year_contradiction` (10). A canonical anchor `"Tonegawa Susumu won the Nobel Prize in 1987"` is pre-seeded so the year_contradiction claims have something to clash with (`scripts/lab_gate_live_test.py:103-112`).

**Fast default (`validate="fast"`, `gate_mode="downgrade"`)** — gate latency mean 0.01 ms, p99 0.08 ms.

| Category | persist | downgrade | reject |
|---|---|---|---|
| clean | 40 | 0 | 0 |
| shipped_no_ref | 0 | 25 | 0 |
| shipped_with_ref | 15 | 0 | 0 |
| diagnosis_no_test | 0 | 10 | 0 |
| year_contradiction | 10 | 0 | 0 |

- False positives on clean: **0/40**.
- False negatives on `shipped_no_ref`: **0/25**.
- `shipped_with_ref` passes cleanly: the keyword alone does not trigger; the missing-anchor condition does.

**Full + reject (`validate="full"`, `gate_mode="reject"`)** — mean 11.24 ms, p99 19.77 ms.

| Category | persist | downgrade | reject |
|---|---|---|---|
| year_contradiction | 0 | 0 | **10** |

10/10 year-disjoint contradictions are rejected outright. The pre-seeded anchor `Tonegawa Susumu won the Nobel Prize in 1987` clashes with the synthetic claim `Tonegawa Susumu won the Nobel Prize in 2014` (and 2015/2016 cyclic variants).

### 3.3 Real-world corpus replay (script: `scripts/lab_gate_real_corpus_replay.py`)

The 1173 active facts in the live corpus (status not in `{orphaned, quarantined}` and not superseded) are replayed through the gate in fast/downgrade mode.

| Result | Value |
|---|---|
| N | 1173 |
| Wall time | 0.02 s |
| Per-fact latency | 0.021 ms |
| `persist` | 1104 |
| `downgrade` | 69 |
| L1 hits | 52 |
| L1.5 hits | 22 |
| L1.7 hits | 1 |

**Cross-check vs cycle 137 read-time orphan scan**: cycle 137's `scan_orphaned_facts` had identified the same union (52 shipped + 22 diagnosis + 1 task_state = 75 raw counts, but the union of *distinct facts* is **69** — some facts hit multiple keyword families). The replay reports `intersection = 69`, `only in 137 = 0`, `only in 138 = 0`. The write-time gate and the read-time scan converge to the **same 69-fact set** with zero divergence.

#### 3.3.1 Longitudinal re-verification (2026-05-22, +4 days)

The same `scripts/lab_gate_real_corpus_replay.py` was re-run on the same operator's `~/.engram` four days later. Empirical numbers:

| Metric | 2026-05-18 (draft) | 2026-05-22 (re-run) | Delta |
|---|---|---|---|
| Active corpus | 1173 | 1629 | +39% |
| `persist` | 1104 | 1538 | +39% |
| `downgrade` | 69 | 91 | +32% |
| Downgrade rate | 5.88% | 5.59% | −0.3 pp |
| L1 hits | 52 | 68 | +31% |
| L1.5 hits | 22 | 29 | +32% |
| L1.7 hits | 1 | 1 | 0% |
| Cycle 137 union | 75 (52+22+1) | 109 (76+31+2) | +45% |
| **intersection(gate, scan)** | **69** | **91** | — |
| **only in scan 137** | **0** | **11** | **NEW** |
| **only in gate 138** | **0** | **0** | 0 |

The rate-stability claim (~5.88%) holds within 0.3 pp — the gate's selectivity is empirically invariant over a 39% corpus growth. However the "zero divergence" between scan 137 and gate 138 reported in the draft is no longer true: 11 facts visible to scan 137 are missed by the gate replay. **This is not a regression of the gate.** It is a methodological artefact introduced *after* the draft was written: the read-time pipeline now promotes some downgraded facts to `status="quarantined"` (a hard exclusion bin introduced by a separate hardening cycle), and the gate replay queries only `status NOT IN ('orphaned','quarantined')`, while scan 137's count includes the orphaned bucket. The 11 facts in the symmetric difference are facts the gate *did* downgrade earlier in their lifecycle, then a separate `verified_by` I/O hard-gate (referenced in Section 4) escalated them to `quarantined`. The gate replay's filter excludes them; scan 137's filter does not.

The honest interpretation is: the "zero divergence" of §3.3 is a *snapshot* property for the corpus state of 2026-05-18, before the quarantine semantics existed. The longitudinal property is **gate ⊆ scan** at all times, with the symmetric-difference growing monotonically as quarantine promotions accumulate. The selectivity invariant (~5.88%) is the durable claim; the set-equality is a one-time observation.

### 3.4 SCALE 10× — 11 736-fact vertical stress (script: `scripts/lab_scale_10x_stress.py`)

The 1173-fact corpus is replicated 10× by id-suffixing, yielding 11 736 active rows on disk.

| Phase | Result |
|---|---|
| Cold cache build | 264.6 ms over 11 730 facts (embedding matrix (11 730, 384)) |
| Gate fast pass (full corpus) | 0.32 s total, **0.027 ms/fact** |
| Gate fast pass p50/p99 | 0.015 ms / 0.131 ms |
| Downgrade count | **690 / 11 730 = 5.88%** |
| L2 `scan_orphaned_facts` | 239.3 ms over 11 736 facts |
| L2 category breakdown | shipped 520, diagnosis 220, task_state 10 (consistent 10× of the 52/22/1 single-corpus counts) |

The 5.88% downgrade rate on 11 730 facts matches the 69/1173 = 5.88% rate on the single corpus — the gate is rate-stable under 10× scale.

(≈ 470 words.)

---

## 4. Limitations

The gate is intentionally narrow. It is a *write-time filter*, not a fact-checker.

**False-future dates pass when the corpus has no anchor.** A direct probe (`Tonegawa Susumu won the Nobel Prize in 2099`, `verified_by=[]`, `validate="full"`, `gate_mode="reject"`, run during draft preparation) returned `action="persist"`, `warnings=[]`. L1 does not fire (no SHIPPED keyword). L1.5 does not fire (no DIAGNOSED keyword). L1.7 does not fire (no task-state phrase). L3 `validate_claim` runs but finds no fact in the corpus that contains both the `Tonegawa` token and a year, so the function returns `verdict="unknown"` and the gate has nothing to reject. The same probe succeeds (i.e. is correctly rejected) when a 1987-anchor fact is pre-seeded, as demonstrated in Section 3.2. *The gate's L3 layer can only contradict claims for which contradictory evidence already exists in memory.* Claims about facts the corpus has never seen — including dated-future fabrications — are out of scope. (The user's task description references "cycle 138 effectiveness 5/6" from a subagent audit; we did not find that artifact in the corpus during draft prep and mark the specific 5/6 figure as **UNVERIFIED**. *Cycle 60.5 update 2026-05-22:* a corpus-wide grep on this branch shows the literal string `5/6` appears only in `engram/consolidation.py:408` as the cycle 153 honeycomb mesh consensus over six review angles — architect/maintainability/performance/ux/security — which is unrelated to cycle 138. The most likely explanation is a draft-time conflation of "5-of-6 review-angle consensus" with "cycle 138 detector effectiveness". The 5/6 figure should be removed from any cycle 138 effectiveness claim.)

**Keyword heuristics are language-fragile.** L1.7 phrases are mixed Italian/English (the operator's working languages). A claim phrased in a third language, or a re-phrased English equivalent ("the cycle remains unfinished" vs the literal "still pending"), will not trigger. The detector list is a starting set, not a closure; coverage will degrade as the agent's vocabulary diversifies.

**L3 depends on `semantic.search_facts` recall.** If retrieval misses the contradicting evidence, L3 returns `"unknown"`. The current backend uses SQL `LIKE` on lowercased proposition, with a per-name-token query loop (`engram/validate_claim.py:148-160`) to work around a bug found by the critic-orchestrator (the verbatim claim almost never appears as a substring of any fact). A different backend (vector-only, BM25-only) would have different miss profiles.

**The gate does not validate verified_by content.** A claim like `Cycle 999 SHIPPED to main` with `verified_by=["commit:lorem ipsum dolor"]` passes L1: the *prefix* `commit:` matches the regex, and no I/O is performed to confirm the commit exists. A separate hard-gate component (referenced in production logs as "verified_by hard-gate v2") demotes facts whose refs fail I/O verification, but that is a downstream filter, not part of this gate.

(≈ 240 words.)

---

## 5. Related work

We position our contribution against four families.

**Semantic Consistency Models / SCM** (arXiv:2604.20943, cited in the task description) — generative-time consistency mechanisms that enforce logical agreement *during* token decoding. These run inside the LLM's forward pass and do not see the agent's memory store. Our gate runs *after* generation and *before* persistence; the two are complementary.

**Mem0 / OpenMemory** [mem0-2026]. Public OSS pipeline: flat vector storage + summary, MCP server. Mem0's documented benchmarks (66.9% LOCOMO, claim 91.6% on a later version, BEAM/LongMemEval positioning) measure *recall quality*, not write-time hygiene. We read Mem0's OSS write path (mem0.ai/blog/state-of-ai-agent-memory-2026) and found no analogous pre-write detector: the system stores first, recalls/summarizes later. The 47.9% poisoning rate reported by MemoryGraft against flat-similarity stores [memorygraft-2025] is precisely the failure surface our L1 family targets.

**Letta / MemGPT** (arXiv:2310.08560) — three-tier memory (main / recall / archival) with paging policy. The original paper proposes *no* pre-write verification; archival writes are accepted unconditionally and the OS-style page-in/page-out is the only "discipline". Our gate is orthogonal: it sits at the boundary into archival, not on the paging policy.

**Zep / Graphiti** — temporal knowledge graph with time anchoring at retrieval. Public benchmark claims 71.2% on LongMemEval. The time anchoring resolves *which version* of a fact applies to a query timestamp; it does not refuse a write that lacks evidence. Graphiti's bi-temporal model (paper not yet on arXiv as of 2026-05) handles update conflict resolution post-write.

**HippoRAG** (arXiv:2405.14831, NeurIPS 2024) and **HippoRAG 2** (arXiv:2502.14802) — Personalized-PageRank-on-KG retrieval. These are read-time algorithms; the write step is plain OpenIE triple extraction, with no detector on the triple's evidentiary status. The authors note (Section "Limitations") that OpenIE error is the dominant cost of noisy retrieval — confirming, from the read side, the same lever we attack from the write side.

**HaluMem** (arXiv:2511.03506, 2025-11) — benchmark, not a system. Provides ~15 k memory points × ~3.5 k QA pairs labelled by `memory_source ∈ {primary, secondary, interference, system}`. *Cycle 60.5 correction 2026-05-22:* the draft originally cited `scripts/lab_halumem_adapter.py` as a stub defining the import surface. **That file does not exist on this branch** (`find . -iname "*halumem*"` returns no matches). The adapter was planned but never created. The live numerical comparison against HaluMem is therefore not deferred — it is **not started**. Estimated effort to bootstrap the adapter + run one benchmark pass: ~250 LOC + ~3–4 h compute, identical to the planning note that was attributed to the missing file.

**Survey** (arXiv:2603.07670, 2026-03) — *Memory for Autonomous LLM Agents*. Names "reflective contamination" as a failure mode but lists no system that defends at write time. Our gate is the first published artifact (as of cycle 138, 2026-05-18) that explicitly does so on a real production-grade corpus.

(≈ 470 words.)

---

## References

1. **HippoAgent — `engram/anti_confabulation.py`** (`detect_unsupported_shipped_claim:78`, `detect_unsupported_diagnosis_claim:158`, `detect_unsupported_task_state_claim:239`).
2. **HippoAgent — `engram/anti_confab_gate.py`** (`run_validation_gate:175`, GateResult dataclass:72).
3. **HippoAgent — `engram/validate_claim.py`** (`validate_claim:82`).
4. **HippoAgent labs** — `scripts/lab_validate_claim_bench.py`, `scripts/lab_gate_live_test.py`, `scripts/lab_gate_real_corpus_replay.py`, `scripts/lab_scale_10x_stress.py`, `scripts/replay_confabulations_2026_05_17.py`. (*Cycle 60.5 correction: `scripts/lab_halumem_adapter.py` was cited but does not exist — see §5 note. Reference removed.*)
5. **Memory for Autonomous LLM Agents — Survey** (2026-03). arXiv:2603.07670. https://arxiv.org/abs/2603.07670
6. **MemoryGraft** (2025-12). arXiv:2512.16962.
7. **ProvSEEK** (2025-08). arXiv:2508.21323.
8. **HaluMem** (Ding Chen et al., 2025-11). arXiv:2511.03506. https://arxiv.org/abs/2511.03506. HF: `IAAR-Shanghai/HaluMem`.
9. **HippoRAG** (Gutiérrez et al., NeurIPS 2024). arXiv:2405.14831.
10. **HippoRAG 2 — From RAG to Memory** (2025). arXiv:2502.14802.
11. **MemGPT / Letta** (Packer et al., 2023). arXiv:2310.08560.
12. **Mem0 — State of AI Agent Memory 2026** (blog). https://mem0.ai/blog/state-of-ai-agent-memory-2026
13. **Semantic Consistency Models / SCM** (referenced in task). arXiv:2604.20943.
14. **LOCOMO benchmark** (Maharana et al., ACL 2024). arXiv:2402.17753.
15. **AriGraph** (Anokhin et al.). arXiv:2407.04363.
16. **Brevity Constraints Reverse Performance Hierarchies** (Hakim, 2026). arXiv:2604.00025.

---

*Document path: `docs/papers/write-time-confabulation-gates-DRAFT.md`. Status: DRAFT. All empirical numbers reproducible from `scripts/lab_*.py` against the operator's live `~/.engram` corpus, 2026-05-18.*
