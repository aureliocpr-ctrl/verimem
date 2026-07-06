# 🧠 Verimem

> **Verified memory for AI agents** · [verimem.com](https://verimem.com)
> *(engine formerly known as Engram / HippoAgent — "engram" remains the
> architecture term: the inspectable memory-trace artifacts this system produces)*

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/verimem)](https://pypi.org/project/verimem/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE) [![Commercial license available](https://img.shields.io/badge/license-commercial_available-green.svg)](LICENSING.md)
[![Python ≥ 3.10](https://img.shields.io/badge/python-≥3.10-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-5900%2B-brightgreen)](../../actions/workflows/ci.yml)

> **Persistent memory layer for Claude Code (and any LLM agent).**
> Most AI agents have amnesia — and the ones with memory will store anything,
> true or not. Verimem screens every write with a lexical anti-confabulation
> filter by default, and — when you pass a `source` and `ground=True` — admits
> the fact only if that source actually **entails** it (the AUROC-0.971 moat no
> competitor ships). Reads carry **provenance**. A hippocampus with a
> notary at the door.

📊 **Live state** — run `engram status` for the current counts (they grow as you use it). This repo's corpus is **~550 episodes · ~325 skills · ~4.6k facts · 231 MCP tools** at the time of writing — see [STATE.md](./STATE.md) for the honest snapshot (what works, what doesn't, and the roadmap).

> **Why the *engram* architecture?** In neuroscience, an *engram* is the physical substrate
> of a memory trace — the actual change in neural tissue that encodes a
> learned experience (the term was coined by Richard Semon in 1904; Tonegawa's
> lab at MIT later gave it physical evidence through optogenetic *engram cell*
> studies). That's exactly what this system produces: not weights, but
> inspectable, fitness-tracked, mergeable memory artifacts that persist across
> sessions.

Verimem is **not a replacement** for Claude Code, Cursor, or your favourite
agent. It's the **memory module** they're missing. Plug it in via MCP and:

- Episodes you and the agent worked on **persist across sessions**.
- Procedures the agent figured out **get compiled into deterministic macros** —
  the next call doesn't even hit the LLM.
- Failure → success patterns are **rescued and replayed** during sleep cycles.
- Skill consolidation runs **subscription-first** (cycles #34-#40 *Hippo Dreams*):
  the host's LLM does the heavy lifting via Pro/Max plan — zero extra API
  spend, atomic shadow → review → adopt with rollback on failure.

8+ neuroscientific mechanisms (DG pattern separation, TCM, synaptic tagging,
lateral inhibition, engram crossover, schema priming, …) all opt-in via flags.

## 🏆 Retrieval moat — measured, not claimed

Verimem's recall fuses **dense-cosine + entity-PPR + BM25-lexical** via RRF,
then a cross-encoder rerank — a combination no competitor ships (HippoRAG-2:
no CE, no lexical; Zep: no CE; Mem0: cosine only). On **LongMemEval-s**
(public benchmark, session-level retrieval, judge-free, the *same* e5-base
embedder for every arm, zero external APIs):

| arm (FULL 500, like-for-like) | recall@5 |
|---|---|
| Verimem, fusion OFF (bare cosine) | 0.8525 |
| **Verimem, fusion ON (3-signal)** | **0.8745** |

**+2.2 pp from the fusion** on the full 500 (A/B toggling *only* `ENGRAM_PPR_FUSION`;
`lme_s_fusionON/OFF_n500_clean.json`). An earlier n=300 sample read 0.909/+7.5pp, but
it covered only 4 of the 6 question types and under-sampled temporal-reasoning (the weak
type at 0.793) — **the full-500 number above is the honest one**; the n=300 headline was
optimistic. mem0 2.0.4 (e5-parity) sat at 0.790 on an n=100 slice (not full-500, so not
strictly comparable). The stage-2 cross-encoder rerank does **not** move LongMemEval
recall@5 (it reorders within the top-k; the gold session is already in top-5) — its
verified lift is R@1 on hard fact paraphrases, a different task. **Fusion is Default-ON**;
opt-out with `ENGRAM_PPR_FUSION=0`. On top of retrieval, Verimem ships two things the others don't:
**bi-temporal valid-time** (`valid_until` hard-expire — the differentiator vs
Mem0/Zep) and a **write-time prompt-injection screen** that is multilingual
(incl. Italian) — mem0 and `engram-memory` ship none.

On the **write path**, a tunable **trust-maintenance** dial no competitor ships:
anti-sycophancy (a bare assertion can't overwrite a *verified* fact), evidence-tiered
supersession, and a precision floor — recall-first ↔ never-delete-truth, all env-driven
and default-off. Numbers, knobs and honest caveats: **[docs/TRUST_MAINTENANCE.md](./docs/TRUST_MAINTENANCE.md)**.

On the **read path**, the same philosophy as a measured 4-point dial
(HaluMem QA, n=120, like-for-like — competitors ship one unmeasured operating point):

| arm | correct | hallucination |
|---|---|---|
| baseline | 0.408 | 0.233 |
| `ENGRAM_RECALL_CENTERING=1` | **0.433** | 0.225 |
| `ENGRAM_GROUNDING_GATE=1` | 0.358 | 0.125 |
| both | 0.350 | **0.111** |

Every answer is externally verified against the retrieved evidence; unsupported
answers become abstentions — **hallucinations −52%** at the trust-first end, your call
where to sit. And it holds at **scale**: brute-force recall is O(N) (81 ms @1M) while
the wired ANN stays ~flat (1.3 ms) — **62× @1M, sublinear** (reproducible):
**[SCALE.md](./SCALE.md)**.

**Honest scorecard vs MemOS (self-reported) on HaluMem**: extraction F1 0.71–0.74
vs 79.7 (gap −6/−9pp, was −14.7); updating 0.25–0.29 judged vs 62.1 — retrieval-capped
(4 embedders across 3 families within ~3pp; the paraphrase-matching ceiling is a
model-class limit we state instead of hiding); QA **end-to-end 0.553 vs 0.672**
(behind; extraction recall is the bottleneck — the same recipe on a gold store
reads 0.739–0.750, split detailed in the comparison section below) with the
hallucination trade above. Our axis is **measured trust + reproducible scale + the
dial** — not raw-recall parity.

Full numbers, fairness notes and honest limits: **[BENCHMARKS.md](./BENCHMARKS.md)**.

## ⚡ Install in 2 minutes (Claude Code)

```bash
pip install verimem
# From source (latest main):  pip install "git+https://github.com/aureliocpr-ctrl/verimem.git"
# For development:  git clone https://github.com/aureliocpr-ctrl/verimem && cd verimem && pip install -e .
```

Drop `.mcp.json` in your project root (or `~/.claude/.mcp.json` global):

```json
{
  "mcpServers": {
    "engram": {
      "command": "engram",
      "args": ["mcp"],
      "env": {
        "ENGRAM_HOSTED": "1",
        "ENGRAM_DATA_DIR": "${HOME}/.engram"
      }
    }
  }
}
```

Restart Claude Code. The 231 `hippo_*` MCP tools become callable; the
`hippoagent-memory` skill auto-activates at every session. **To disable
temporarily**: `export ENGRAM_DISABLED=1` (legacy `HIPPO_DISABLED=1` still works).

> **First run downloads a ~440 MB embedding model** (`multilingual-e5-base`).
> Pre-download it once so your first recall is instant instead of waiting on a
> silent background fetch:
> ```bash
> engram warmup        # downloads + loads the model, reports when ready
> ```
> It's also the natural pre-bake step for CI / Docker images.

### Use it from Python (no MCP, 3 lines)

```python
from engram import Memory

mem = Memory()                                          # local SQLite, offline
mem.add("The deployment uses PostgreSQL 16.")           # write goes THROUGH the gate
for hit in mem.search("which database?"):               # read returns provenance
    print(hit["text"], hit["status"], hit["grounding_score"])
```

Same `add()` / `search()` ergonomics as mem0/Zep — with the difference that is
the whole point: `add()` routes every write through the **anti-confabulation
gate** (lexical screen + optional contradiction + optional source⊢fact
entailment), so an unsupported claim is downgraded or refused instead of stored;
and `search()` returns each fact's **provenance** (`status`, write-time
`grounding_score`) so your code can trust-condition. Pass `source=` and enable
`ENGRAM_GROUNDING_WRITE` for the strongest gate (source-entailment, AUROC 0.971).

Full surface (mem0/Zep parity): `add · search/recall · get · get_all · update · delete`,
plus the one a cosine-only store can't offer — **`history(id)`**, the supersession chain
(`update()` never destroys the old fact, it supersedes it, so the provenance trail is
auditable):

```python
mem.update(fid, "The server now listens on port 9090.")  # supersedes, keeps the old
for v in mem.history(fid):                                # oldest -> newest
    print(v["text"], "->", v["superseded_by"])
```

### Make it fully automatic (recommended)

Add the [Memory Protocol](./docs/MEMORY_PROTOCOL.md) to your `~/.claude/CLAUDE.md`
so Claude writes to memory at end of every significant task and reads at start —
no slash commands, no friction. Two-line setup, [details here](./docs/MEMORY_PROTOCOL.md).

For explicit control instead, install the optional slash commands from
[`slash_commands/`](./slash_commands/) (`/recall`, `/remember`, `/memory`, `/forget`, `/skill-top`).

### Real-world use cases

- **General developer workflow** → [`docs/MEMORY_PROTOCOL.md`](./docs/MEMORY_PROTOCOL.md)
- **Autonomous pentesting agent (NEXUS)** → [`docs/usecases/pentesting_nexus.md`](./docs/usecases/pentesting_nexus.md)

## 📊 How Verimem compares (honest, no spin)

### HaluMem QA — the composed trust recipe, adversarially reviewed (2026-07-06)

With the full recipe ON (bi-temporal `asserted_at` + reconcile floor 0.35 +
verification-aware answerer + **dated history context** + k=12), per-session QA on
**HaluMem-Medium** ([u0 evidence](./benchmark/results/qa_gem_k12_u0.json)):

Two DIFFERENT measurements, never on the same row (adversarial review C8 —
an earlier draft compared our read-path number against MemOS's end-to-end
number without saying so):

| | user 1 (n=188) | user 0 (n=164) | user 2 (n=169) | MemOS **end-to-end** (self-reported) |
|---|---|---|---|---|
| **Read-path QA** — store built from *gold* memory points; measures the memory (recall+history+verify+abstention), not our extractor | **0.739** | **0.750** | **0.787** | — |
| **End-to-end QA** — our extraction → gated store → answer, same questions ([run 1](./benchmark/results/e2e_full_pipeline_u1.json), [run 2](./benchmark/results/e2e_full_pipeline_u1_postfix.json)) | 0.553* (×2 runs) | not run | not run | 0.672 |
| Memory Boundary, never fabricate (read-path / e2e) | 0.976 / **1.000** | 0.897 / — | **1.000** / — | — |
| Memory Conflict (read-path / e2e) | 0.800 / 0.800 | 0.872 / — | 0.889 / — | — |
| Basic Fact Recall (read-path / e2e) | 0.800 / 0.267 | 0.725 / — | 0.750 / — | — |

Read-path across **3 users: 0.739 / 0.750 / 0.787 (mean 0.759)** — every run
above MemOS's end-to-end 0.672 ([u2 evidence](./benchmark/results/qa_gem_k12_u2.json)).

**End-to-end we are BEHIND MemOS (−12pp) — stated, not hidden.** The split shows
where: the trust properties HOLD through the full pipeline (Boundary 1.000 on
both runs, Conflict 0.70–0.80) while extraction recall on basic facts is the
bottleneck (0.27–0.38 e2e vs 0.800 read-path). \*Two independent runs both
scored 0.5532 (stable overall). Between them we found and fixed an
identity-leak artefact by reading run-1's failures (the extractor baptised
anonymous speakers with an out-of-text name — reproduced live, fixed): run 2
has 3/188 leak-tainted answers vs 13/188, and Basic Fact +11pp where the fix
bites; per-category shifts elsewhere are within run-to-run variance.

The read-path claim survived an adversarial counterexample review
(`claim_holds`, conf 0.86: per-category counts consistent by construction;
abstention flagging doesn't inflate — fabrications are penalized; answerable
categories graded by the strict judge).
**Declared caveats, every time:** judge is Claude (MemOS self-reports with GPT-4 —
comparable method, not identical); n=3 users; the rich
context trades a little abstention purity (0.976/0.897 vs 1.0 with the strict answerer).
The single biggest lever is the **answer-with-history** dated context: on transition
questions it lifts +16pp (7 unlocked, 0 lost), and the Memory-Conflict arc is
**0.15 → 0.825 (5.5×)** from plain store to full recipe — see
[TRUST_MAINTENANCE.md](./docs/TRUST_MAINTENANCE.md) for the measured dial and
[QUICKSTART_SDK.md](./docs/QUICKSTART_SDK.md) for the 5-verb SDK that ships it
(`add/search/history/as_of/explain` — archaeology, time-travel and the evidence
dossier included). Write-path robustness, same block: reconcile auto-supersede made
surgical (146/807 retired, **0 cross-attribute**, 3× faster) and a 7/7 stress battery
([evidence](./benchmark/results/stress_battery.json)).

### TrustMem-Bench — the trust benchmark we impose (offline, run it yourself)

Every memory benchmark measures *accuracy*. None measures whether a memory can
be **trusted** — so we built one. Seeded synthetic personas (EN + IT), six axes
whose verdict is deterministic (no LLM, no network), one command:

```bash
python -m benchmark.trustmem_bench --engine verimem   # 6/6, offline
python -m benchmark.trustmem_bench --engine mem0      # competitor (pip install mem0ai)
```

Same dataset, both engines ([verimem](./benchmark/results/trustmem_verimem_scorecard.json)
· [mem0](./benchmark/results/trustmem_mem0_scorecard.json), n=10 seed=42):

| Axis | Verimem | mem0 OSS (raw) |
|---|---|---|
| Fabrication under absence | **10/10** | 0/10 |
| Destructive-update | 10/10 | 10/10 · *trivial (never reconciles)* |
| Temporal integrity (as-of) | **10/10** | n/a — cloud-API-gated |
| Forget integrity (GDPR) | **10/10** | 0/10 · *delete leaves it in `history()`, verified live* |
| Provenance honesty | **10/10** | 0/10 |
| Sycophancy resistance | **10/10** | n/a — cloud-API-gated |
| **API coverage** | 6/6 | 40/60 (0.67) |

Honest by construction (design §2): 100% on axes we *build* only proves no
regression — the value is the competitor column and the two LLM-judged axes
(still to come) where nobody scores 100%. mem0 runs in raw-store mode (their
LLM extraction is out of scope, HaluMem measures that); maintainers are invited
to PR an official run. Design + full reads: [TRUSTMEM_BENCH_DESIGN.md](./docs/TRUSTMEM_BENCH_DESIGN.md).

### Retrieval (LongMemEval-s, judge-free, fully local)

On the standard **LongMemEval-s** benchmark (full 500 questions, judge-free, fully local —
[result file](./benchmark/results/lme_s_fusionON_n500_clean.json)):
**recall@5 0.8745 · hit@5 0.944 · MRR 0.856** (`multilingual-e5-base`, 768-d, fusion ON).
On the **Italian** embedding A/B ([result file](./benchmark/results/lme_model_comparison_2026-06-05.json)),
the e5 flip lifts Italian **MRR 0.466 → 0.710 (+52%)** at **zero** English regression
(English recall@5 ties within noise: **0.80** e5 vs **0.82** legacy-MiniLM, 50-question slice).

**End-to-end Italian smoke** (`benchmark/qa_italiano_smoke.py`, the full recipe
on an all-Italian store with accents): **13/13 factual + 6/6 abstention on trap
questions = 1.000**, dated transition resolved ("prima di trasferirsi → Milano").
Honest: a small hand-built synthetic set (easy, distinct facts) — a proof that
recall AND anti-fabrication work in Italian end-to-end, not an external
benchmark. The abstention 6/6 shows the anti-confab gate is not English-only.

**New (2026-06-10): same-embedder comparative + full method notes in
[BENCHMARKS.md](./BENCHMARKS.md)** — Verimem vs a bare cosine baseline with the *identical*
e5 model (the honest reading both ways: on pure ranking over a clean haystack the layer adds
~nothing — its value is provenance gating, crash-durable writes, per-model isolation and
multi-tenancy, which a bare matrix doesn't have), plus the regime-dependence of the 2-stage
cross-encoder rerank: **default-ON** on short facts (twice McNemar-validated, R@1 0.52→0.81
HARD / 0.53→0.68 fair-paraphrase) and auto-skipped on documents beyond the CE's 512-token
window (`ENGRAM_RECALL_RERANK=0` to opt out, `ENGRAM_RERANK_MAX_DOC_CHARS` to tune the
guard, `ENGRAM_RERANK_TOPN` for the latency/quality knob).

> **Honest caveat:** those are **retrieval recall@k**, *not* end-to-end QA-accuracy, so they
> are **not** directly 1:1 with the LOCOMO / LongMemEval *QA* scores Mem0 / Zep headline. The
> **default** fact-recall is single-hop cosine. The entity-graph + Personalized-PageRank
> engine (`entity_kg.py`, `hippo_ppr_retrieve`) is **populated from the live corpus** as of
> 2026-06-10: a deterministic zero-API extractor (`entity_extract_lite.py`) backfilled 7 570
> entities / 75 959 co-occurrence edges / 22 609 fact-links from 2 181 facts, and PPR from
> real entities returns real facts (e.g. probe "Verimem" → 1 039 facts). Two limits, no spin:
> extraction is regex-tier (paths, modules, identifiers, proper nouns — not semantic OpenIE),
> and it runs as an idempotent backfill script (`scripts/backfill_entity_graph.py`), not yet
> wired into the live save path — new facts need a re-run to enter the graph.

| System | Approach | Maturity |
|---|---|---|
| **Mem0** | flat vector + LLM summary; ships an MCP server (OpenMemory) | established, widely adopted |
| **Zep / Graphiti** | temporal knowledge graph, time-anchoring | commercial, mature |
| **HippoRAG** | OpenIE + Personalized-PageRank (the *same* hippocampal metaphor) | research; LLM-based OpenIE extraction (Verimem's PPR is live on real data too, but with a lighter regex-tier extractor) |
| **Cognee** | multi-step pipeline + pluggable ontology | established |
| **Letta (MemGPT)** | memory-as-OS, tiered paging | established |
| **Verimem** | sleep/Dream consolidation + `self_model` + critic-orchestrator gate + MCP-native + Italian-first + subscription-only | **brand-new public release — 0 adoption yet** |

*(Competitor benchmark scores and adoption numbers vary by source and drift over time — see
our [2026-05 landscape survey](./docs/research/entity-memory-state-of-art-2026-05.md) for the
sourced detail rather than trusting a number in this table.)*

**Where Verimem is behind — no spin:** zero adoption (this is a fresh public repo); entity
extraction is regex-tier (deterministic, zero-API) rather than semantic OpenIE, so common-noun
entities are missed; and extraction is a backfill script, not yet wired into the live save
path (HippoRAG / Zep extract at write time).

**Where Verimem is genuinely different — the *combination*:** (a) **MCP-native** integration
(Mem0 also ships one via OpenMemory; the others are mostly SDKs you wire up yourself), (b)
explicit **sleep / Dream** consolidation with a persistent **`self_model`** of the agent, (c)
an **adversarial critic** gate on every write, and (d) running **entirely on your Claude
subscription — no API key, no per-token billing**. No other system here combines all four.
The entity-KG + PPR engine is live on real data (7 570 entities backfilled from the corpus,
PPR returns real facts) — with the declared limits above (regex-tier extractor, backfill not
yet in the write path).

**Multi-tenancy (Mem0-parity, 2026-06-08):** scope facts to `user_id` / `agent_id` /
`run_id` with **strict per-tenant isolation** — a query for one tenant never sees another's —
plus `include_shared` opt-in for global facts and scoped delete (`delete_all(scope)`, dry-run
default + per-fact undo). Zero schema change (the scope is a canonical `user:…/agent:…/run:…/`
topic prefix), so it works identically on **both** surfaces:

```text
# MCP:  hippo_remember(proposition=…, topic="prefs", user_id="alice")
#       hippo_facts_recall(query=…, user_id="alice")          # bob's facts invisible
#       hippo_forget_scope(user_id="alice", dry_run=true)     # mem0 delete_all(scope)
# CLI:  engram facts add  -p "…" -t prefs --user-id alice
#       engram facts recall "…" --user-id alice [--include-shared]
```

Honest scope: this is the **fact** surface (Mem0's add / search / get_all / delete by scope);
**episode**-level scoping is a declared follow-up, not yet shipped.

## 🔌 Verimem as MCP server — what Claude Code actually gets

When you wire Verimem into Claude Code (or any MCP host: Cursor,
opencode, Cline, Continue, Zed), the host LLM sees **231 tools** at
session start. They cover the full memory-layer surface; below is the
honest tour by category. Full per-tool reference: [`docs/MCP_QUICKSTART.md`](./docs/MCP_QUICKSTART.md).

| Category | Tools | What the host does with them |
|---|---:|---|
| **Recall** | 3 | `hippo_recall` at task start → 5 past episodes (~3k tok). Find similar work, prime the answer. |
| **Remember / Forget** | 3 | `hippo_remember` to persist a fact (proposition + topic + confidence). Pure SQLite write, zero LLM. |
| **Episodes** | 15 | `hippo_record_episode` after every significant task. Plus pin/unpin, replay, classify, diff, clusters, dedup. |
| **Facts / Semantic** | 15 | `hippo_facts_search` (substring), `hippo_facts_recall` (cosine), `hippo_facts_disagreement` (conflict flag), merge/cluster/export. |
| **Skills** | 50 | Lifecycle (promote/retire/archive/recover/edit), discovery (top/similar/for/search), composition (lineage/cooccurrence/bundles), health (failure_audit/bottlenecks), import/export. |
| **Hippo Dreams** ⭐ | 7 | `hippo_dream_create_shadow` → `hippo_dream_propose` → host LLM iterates `submit_result` per task → `hippo_dream_diff` → `hippo_dream_adopt` (atomic, rollback-safe). Zero internal LLM call. |
| **Reasoning chains** | 12 | `hippo_reason`, `hippo_chain_validate`, `hippo_forward_chain`, `hippo_plan_strips`, `hippo_compose_macro`, `hippo_promote_chain`. |
| **Lineage / causal** | 8 | `hippo_causal_extract`, `hippo_skill_lineage_*`, `hippo_find_analogues`, `hippo_export_graph`. |
| **Audit / metrics** | 7 | JSONL audit tail, metrics export, velocity stats. |
| **Health / introspection** | 8 | `hippo_health`, `hippo_status`, `hippo_dashboard_overview`, `hippo_corpus_*`. |
| **Analytics / prediction** | 12 | Outcome patterns, drift detection, RCA on failures, freshness/trust ranking. |
| **Misc** | ~35 | Rollup, prune, cross-agent consensus, briefings, provider switch. |

**Typical Claude Code session** (real workflow, not synthetic):

> User: *"Refactor `auth.py` to use bcrypt."*
>
> Claude Code internally:
> 1. `hippo_recall("refactor auth bcrypt")` → finds 3 episodes from
>    last month's sha256→bcrypt migration. Pulls them in (~3k tok).
> 2. `hippo_skills_for("auth library swap")` → retrieves a consolidated
>    skill ("audit usage sites → introduce shim → flip default → remove old").
> 3. Edits `auth.py` applying the skill.
> 4. After tests pass: `hippo_record_episode(...)` + `hippo_remember(proposition="auth.py now uses bcrypt cost=12", topic="project/X/auth")`.
>
> Next month, "rotate bcrypt cost factor" → recall finds today's
> session, primes the answer instantly. **Token bill drops to ~0
> on the second-time-around work.**

**Context cost (honest)**: the ~231-tool registry is auto-loaded at
session start → **~27k tokens of JSON schemas** (~13% of a 200k
window, ~3% of a 1M window). Skills/facts/episodes themselves do
NOT auto-load — they're SQLite on disk, fetched per-call. A typical
`hippo_recall(k=5)` returns ~3-5k tokens.

**Subscription-first mode** (`ENGRAM_HOSTED=1`): every tool that
would call an LLM internally instead returns a structured payload
the host can act on. Zero extra API spend — the host's Pro/Max plan
does all the work. The Hippo Dreams pipeline runs entirely this way:
`propose` (no LLM) → host iterates `submit_result` (host LLM call) →
`adopt` (no LLM).

## 📈 Learning curve — what changes when memory is on (real LLMs)

5 iterations of the same task family on **Anthropic Claude Opus 4.7**, 8 tasks
per iter (digit-sum suite). After the 3rd iteration Verimem has compiled
the procedure into a deterministic macro that bypasses the LLM entirely:

| Iter | Verimem tokens | Verimem latency | Raw LLM tokens | Raw LLM latency |
|---|---|---|---|---|
| 0 (cold) | 4225 | 4.47s | 59 | 0.67s |
| 1 | 1711 (-60%) | 0.92s (-79%) | 59 | 0.71s |
| 2 | 687 (-84%) | 0.52s (-88%) | 59 | 0.85s |
| 3 | **0** ✅ | **0.22s (-95%)** | 59 | 1.08s |
| 4 | **0** ✅ | **0.24s (-95%)** | 59 | 0.69s |

**Break-even at iter 3.** Macro fast-path hit rate: **70%**. The agent stops
asking the LLM for tasks it has solved before — your token bill drops to zero
on recurrent work and your replies come back in 200 ms instead of 700 ms.

Bench data: [`data/bench_learning_curve_anthropic_n5.{results,by_iter}.json`](./data/).

## 🎯 Held-out generalization — practical text tasks

Beyond digit-sum: 5 TRAIN tasks (URL parsing, date format, capitalize,
reverse, word count) → sleep consolidate → 5 HELD-OUT tasks with fresh
inputs of the same families.

| Phase | Success | Rate |
|-------|--------:|-----:|
| TRAIN | 5/5 | 100% |
| **HELD-OUT** | **5/5** | **100%** |

The agent retrieves 3 relevant skills per held-out task and applies them
without per-task re-discovery. Bench data: [`data/bench_held_out_practical.{results.json,summary.md}`](./data/).

## 📊 Headline — compositional generalization (real LLMs, 96 calls)

12 tasks at increasing skill-chaining depth (apply ROT3 + REVERSE in 1-5
chained transformations to fresh inputs). 4 providers, 1 iter:

| Provider | Lv1 | Lv2 | Lv3 | Lv4 | Lv5 | overall |
|---|---|---|---|---|---|---|
| **Anthropic** raw | 100% | 50% | **0%** | **0%** | **0%** | 42% |
| **Anthropic** Verimem | 100% | 100% | **100%** | **100%** | **100%** | **100%** |
| **DeepSeek** raw | 50% | 0% | 0% | 0% | 0% | 25% |
| **DeepSeek** Verimem | 100% | 100% | 100% | 100% | 100% | **100%** |
| **OpenRouter** raw | 100% | 0% | 0% | 0% | 0% | 33% |
| **OpenRouter** Verimem | 100% | 100% | 100% | 100% | 100% | **100%** |
| **Groq** raw | 50% | 0% | 0% | 0% | 0% | 25% |
| **Groq** Verimem | 100% | 50% | 100% | 50% | 100% | 83% |

**The accuracy gap GROWS with composition depth.** Single-shot LLMs collapse
to 0% at Lv3; persistent-memory agents stay at 100% up to Lv5 on 3/4
providers. Empirical signature of compositional reasoning over consolidated
skills.

Compiled-macro hit rate (skills bypassing the LLM entirely): **OpenRouter
92%, Groq 75%, DeepSeek 58%, Anthropic 0%** (Anthropic uses the full ReAct
loop — the 100% accuracy comes from memory recall, not caching).

Bench data (replicable): [`data/bench_compositional_4providers.*.json`](./data/).

```bash
python scripts/bench_with_without_hippo.py \
    --suite compositional \
    --providers anthropic,deepseek,openrouter,groq \
    --conditions raw,hippo_warm
```

**Verimem** — the product. The engine keeps the neuroscientific term
*engram* — the physical substrate of a memory trace (Semon 1904; Lashley;
Tulving; Tonegawa 2014 Nobel) — because that is what the system produces:
inspectable, fitness-tracked, mergeable memory artifacts. Verified before
they are stored: that is the Verimem part.

## 📚 Platform reference (start here)

If you want the **end-to-end map** of the moving parts — components,
configuration knobs, task flow, MCP integration, multi-model bench
harness, test isolation — read [`docs/PLATFORM.md`](./docs/PLATFORM.md).
That doc is the contract; everything below is narrative.

For a **5-minute MCP integration walkthrough** (Claude Code, Cursor,
opencode, Cline, Continue) see [`docs/MCP_QUICKSTART.md`](./docs/MCP_QUICKSTART.md).

## 🧬 What's new in cycle 213-250 (LLM-free emergent skill discovery, 2026-05-23)

The latest burst shipped a complete **algorithmic skill discovery pipeline** that finds, drafts, persists, and registers candidate skills FROM THE FACT GRAPH ITSELF without spending any LLM tokens on discovery + draft. The downstream LLM call is now an OPTIONAL polish step — not a discovery step.

```
detect_emerging_skills (213)         Louvain + topic purity + cohesion
  → normalize_topic (214/215)        family-key collapse + aggressive truncate
    → skill_drafter (217)            deterministic Markdown body + ranked keywords
      → skill_draft_persist (222)    ~/.engram/skill_drafts/<ts>/<name>.md
      → emerging_skill_register (229) topic=emerging_skill/auto-discovered/<name>
      → 4th Auto-Dream seed (219)    + adaptive_threshold (248/249) curve
      → promote_emerging_to_skill (235) gateway to SkillLibrary candidate
```

**5 new MCP tools**: `hippo_emerging_skills_draft` (218), `hippo_skill_drafts_list` (227), `hippo_emerging_skills_register` (232), `hippo_emerging_skill_promote` (236), `hippo_emergence_pipeline_status` (239).

**6 helper scripts**: dashboard, threshold_sweep, inspect_cluster, pilot_snapshot, bench_emerging_pipeline, plus the corpus-size-aware `adaptive_threshold` module (cycle 248).

**4 empirical singolarità documented** (A1 onesti, not marketing):
- **#18 SELF-APPLYING LOOP** — Auto-Dream discovery runs without any LLM token.
- **#19 LINEAGE BACKWARD NAVIGATION** — `clp chain show <emerging_id>` walks back 23 hops to source cluster ancestry.
- **#20 SHADOW ZONE** — at purity=0.2 the matrix surfaces 4 candidates (vs 1 at default 0.4): master-fact, antigravity-reverse, deep-clp, loop29-lineage.
- **#21 OBSERVER-SHIFTS-EMERGENCE** — re-running the same threshold sweep 4 min after registering shadow candidates moved 3 of them BACK under threshold. The session's own writes shift the Louvain partitioning (Heisenberg-like effect). Adaptive threshold curve (cycle 248-249) is the tuning scaffold; real cure (second-pass community detection) deferred.

A4 caveats:
- On the current 1921-fact corpus the pipeline surfaces 0 candidates at adaptive threshold 0.2 — requires p≤0.1 due to corpus fragmentation. Cycle 248-249 is FUTURE-PROOFING when corpus crosses 3000-4000 facts.
- Promotion rate H1 baseline 2.15% (vs cycle-174 audit 4.3%; retired pool grew). H1 multi-day pilot ready (cycle 244 scaffold).
- Cycle 228 H8c parallel_drafter FALSIFIED 1.28× < 1.5× target. Shipped as value-as-boundary.

See [`docs/emergence/README.md`](./docs/emergence/README.md) for quickstart and [`STATE.md`](./STATE.md) for the full empirical snapshot.

## 🚀 What's new in v0.2.0 (production hardening)

The v0.2 push consolidates the prototype into a vendible system. See
[`CHANGELOG.md`](./CHANGELOG.md) and the four R&D reports
([`FINAL_REVIEW.md`](./docs/archive/2026-05-13_FINAL_REVIEW.md), [`BENCH_VALIDATION.md`](./docs/archive/2026-05-13_BENCH_VALIDATION.md),
[`QA_AUDIT.md`](./docs/archive/2026-05-13_QA_AUDIT.md), [`RND_MEMORIE.md`](./docs/archive/2026-05-13_RND_MEMORIE.md),
[`RND_UX.md`](./docs/archive/2026-05-13_RND_UX.md))
for the full picture.

- **13 CVE closed** — RCE in `/api/ide/run` and the WS terminal (auth token + binary allowlist + `shlex.split`), SSRF blocklist in `web_fetch`, sensitive-path deny-list, plaintext API-key leak in `/api/settings/providers` redacted, computer-use kill-switch hotkey deny-list, dashboard CORS lock + session token, `editfmt` config-file deny-list, MCP server schema validation + audit log + rate limit, prompt-injection wrapper around external content (`<untrusted_content>`), Docker sandboxed Python executor (opt-in via `HIPPO_PYTHON_EXEC_BACKEND=docker`).
- **Active memory v2** — 7 enhancements to the original 6 mechanisms + 5 new ones (11 total). All five new mechanisms are **zero LLM call** (pure numpy / string ops on existing memory). See [RND_EXPLORATION.md](./docs/archive/2026-05-13_RND_EXPLORATION.md) for the diary of how they were found:
  - 7 — **Working Memory Pruning** ([RND_MEMORIE.md](./docs/archive/2026-05-13_RND_MEMORIE.md)): wake-loop char-budget compressor; critical for small-context models. Validated on Ollama `qwen2.5:7b`: **−54 % token usage** with lower variance vs unpatched build.
  - 8 — **Trace Alignment / Reverse Replay** ([RND_TRACE_ALIGNMENT.md](./docs/archive/2026-05-13_RND_TRACE_ALIGNMENT.md)): Needleman-Wunsch on observation embeddings finds the *exact* divergence step between a failed run and its success-twin. Two-mode: action-divergence (same situation, different decision) + input-divergence (same tool, wrong file/query). Inspired by sharp-wave reverse replay in CA1 place cells.
  - 9 — **Lateral Inhibition (Anti-Hebbian)**: when a winner skill consolidates on a task, its near-clone rivals are nudged away from that task vector. Földiák 1990 competitive specialisation. Empirically: −0.067 cosine differentiation at step 50 vs Hebbian-only baseline. Disabled by default; opt in via `lateral_inhibition_enabled`.
  - 10 — **Spontaneous Reactivation**: a default-mode rehearsal stage during sleep. Skills not used in N days get their `last_used_at` pushed forward by half the decay cutoff so they don't fall over the retirement cliff. Born & Wilhelm 2012 spaced-repetition substrate. Disabled by default; opt in via `spontaneous_reactivation_enabled`.
  - 11 — **Salience by Surprise**: replay priority gains a fourth term that boosts episodes whose `num_steps` deviates from the skill's average — Buzsáki 2015 prediction-error replay. Combined with multi-skill smallest-deviation logic so a typical-for-skill-A / anomalous-for-skill-B trace doesn't double-count. Disabled by default (`sleep_replay_priority_surprise=0.0`).
- **Performance** — hot paths are optimised: LRU-cached embeddings, vectorised skill clustering (`corpus @ corpus.T`), in-memory recall index with optional FAISS, mtime+size repomap cache. (Per-path speedups are workload-dependent — see `tests/perf/` for the perf-test suite; the older "16×–4700×" figure had no reproducible benchmark behind it and was removed.)
- **Architecture** — `dashboard.py` 2 338 LOC monolith → 159 LOC entry-point + 11-file `dashboard_routes/` package. LLM provider registry moved to `providers.yaml` + Pydantic `ProviderSpec`. New `pydantic-settings`-based `Settings` v2 singleton. Lightweight Alembic-style migrations.
- **UX** — Production-grade design system at `engram/static/dashboard.css` (WCAG 2.1 AA verified contrasts, 4 px scale, 1.25 type ratio, light theme). `/skills` page redesigned with KPI grid + responsive card grid + filter pills + accessibility. CLI banner with contextual tips and grouped `/help`.
- **CI/CD** — 3 OS × 4 Python = 11 jobs, dedicated security workflow (`pip-audit`, `safety`, `bandit`, ruff S-rules) running weekly. Multi-stage Dockerfile (~500 MB), non-root user, `HEALTHCHECK`. `pip` extras (`[headless]`, `[mcp-only]`, `[tui]`, `[vision]`, `[full]`, `[dev]`) — default install is now minimal sane.
- **Tests** — 113 → **1072+** (+849 %). Coverage 46 % → **59 %**. Ruff: 33 → 0 errors. Recent additions (FORGIA #27–#89): `tests/test_bench_harness.py`, `test_bench_compare.py`, `test_bench_summary_md.py`, `test_bench_cli.py`, `test_bench_recall_ablation.py`, `test_clean_bench_data.py`, `test_jsonutil.py`, `test_corruption_guards.py`, `test_data_dir_isolation.py`, `test_auto_fallback.py`, `test_config_env.py`, `test_makefile_help.py`, `test_wake_used_macro.py`, `test_sleep_report_n_llm_calls.py`, `test_real_provider_smoke.py`, `test_mcp_e2e_smoke.py`. Original suites preserved: `tests/security/` (path traversal, SSRF, secrets redaction, prompt injection, executor isolation, editfmt sensitive, pentest validation), `tests/test_settings.py`, `test_settings_v2.py`, `test_provider_registry.py`, `test_migrations.py`, `test_mcp_server.py`, `test_mcp_server_security.py`, `test_dashboard_api.py`, `test_cli.py`, `tests/perf/test_perf.py` (10 benchmarks), `tests/test_rnd_active_memory.py`, `test_trace_alignment.py`, `test_lateral_inhibition.py`.

## What Verimem does, in one breath

You give the agent a task in plain language. It thinks, uses tools (Python
sandbox, file I/O, shell, web fetch, screenshots, webcam, vision LLM, computer
use), retrieves any relevant past skills it has consolidated, and answers.
Every conversation is an **episode** in memory. Every few episodes, you trigger
a **sleep cycle** that distills new procedural skills (NREM), recombines them
creatively (REM), merges duplicates, and promotes/retires by Bayesian fitness.
Tomorrow the agent is genuinely better at what you asked it yesterday — and
you can read every lesson it learned.

## Verified working today

**Multi-model bench harness** (FORGIA #27, 2026-05-09): same task suite,
3 conditions (raw / hippo_cold / hippo_warm), 3-4 real providers, fail-isolated.

**Headline result — `memory_recall` suite (the discriminative one):**

| Provider | raw | hippo_cold | hippo_warm |
|---|--:|--:|--:|
| anthropic | **0.50** | 1.00 | 1.00 (latency −56 %) |
| deepseek | **0.50** | 1.00 | 1.00 |
| openrouter | **0.50** | 1.00 | 1.00 |

The 50 % raw failure is the **3 query tasks** ("What was the value I told you?")
— with no shared context, the LLM has no place to retrieve from. Verimem's
recall pipeline retrieves the seed episode and the query phase succeeds 100 %
on every provider. **+50 percentage-point accuracy uplift, three different LLMs.**

**Hardened result — `hard_memory_recall` (12 tasks: direct + paraphrased + synthesis):**

| Provider | raw | hippo_cold | hippo_warm |
|---|--:|--:|--:|
| anthropic | **0.50** | 1.00 | 1.00 (latency −51 %) |
| deepseek | **0.50** | 0.92 | 0.92 (lost the synthesis) |
| openrouter | **0.50** | 1.00 | 1.00 |

The headline holds: +42–50 pp uplift across paraphrased queries and
multi-step synthesis. DeepSeek lost the multi-step task (retrieved
both facts but failed the addition) — Verimem provides the memory,
arithmetic composition is on the model.

Skill-compounding suite (8 digit-sum tasks): hippo_warm latency −41 % vs
hippo_cold on anthropic (compiled-macro fast-path engaging). Default
trivia suite: raw wins (~50 tokens vs ~3 000), hippo costs structural
overhead but proves end-to-end transport works.

All raw data committed at `data/bench_*.{results,summary}.json`. Full
analysis in [`docs/PLATFORM.md`](./docs/PLATFORM.md#reference-run-3--memory_recall-suite-3-seed--3-query).

**Reproduce locally:**
```bash
make bench-help          # list available task suites
make bench-mock          # offline smoke (no API key needed)
make bench-real          # run on every provider with an env key set
make bench-memory        # the discriminative recall suite
make bench-summary       # render the latest summary as markdown
make bench-csv           # CSV (Excel-friendly)
make bench-quick         # mock + 2 tasks (CI smoke)
make bench-clean         # dry-run of transient bench dirs
make stats               # project size + test count
make bench-compare BEFORE=... AFTER=...   # diff two bench summaries
```

The bench script supports many flags useful in CI:
`--quiet --max-tasks N --task-id ID --providers auto|csv --suite NAME
--n-iter N --consolidate-every K --save-md --memory-stats
--show-failures --print-config --list-providers --clean-data
--output-dir PATH`. See `python scripts/bench_with_without_hippo.py --help`.

**Tool-use** verified live across 4 providers (same task: write a real file
to Desktop), all via **native tool-use API** (no fragile JSON-in-text parsing):

| Provider | Model | Steps | Tokens | Outcome |
|---|---|---|---|---|
| Ollama (local, free) | qwen2.5:1.5b | 2 | 4,655 | ✓ wrote file to disk |
| Ollama (local, free) | qwen2.5:7b-instruct | 2 | 4,699 | ✓ wrote file to disk |
| Groq (free tier) | llama-3.3-70b-versatile | 4 | 11,794 | ✓ wrote file to disk |
| Anthropic | claude-haiku-4-5 | 2 | 7,200 | ✓ wrote file to disk |

**Computer-use end-to-end** verified live:
- ✓ shell_run: `whoami`, `systeminfo`, `wmic`, `ver` — Claude riassume sistema
- ✓ Task "apri Calc + screenshot + descrivi + chiudi" — 4 step, success
- ✓ vision_describe — Claude descrive logo NEXUS correttamente
- ✓ web_fetch + web_search (DuckDuckGo) — paper Nature/ScienceDirect
- ✓ desktop_screenshot 2560×1600 + describe via Anthropic vision
- ✓ Sleep cycle: 18 episodi → 6 NREM + 2 REM + 2 merge + 6 facts in 103s

**Plan mode** + **auto-fallback** chain verified.

Verimem is a working prototype of an idea: an LLM agent that **becomes
measurably more competent over time without ever updating its weights**. It
does so by mimicking the two-stage memory consolidation model from
neuroscience (NREM slow-wave + REM paradoxical sleep). Every "lesson"
the agent learns is a structured, versioned, fitness-tracked artifact you can
read, edit, share, retire — not an opaque parameter shift.

## Why this exists

Today's LLM agents have two ways to "learn":

1. **Fine-tuning** — costly, centralized, opaque, irreversible.
2. **RAG / context** — they "know" things but don't *remember the session*;
   no consolidation, no transfer, no growth curve.

The space in between — what humans actually do during sleep — is empty in
production systems. Voyager (Wang et al.) introduced a skill library for
Minecraft. MemGPT/Letta layered tiered memory. Reflexion added critique.
But **nobody has closed the loop** with a consolidation cycle that:

- replays episodes (success and failure),
- extracts invariant patterns into procedural skills,
- recombines existing skills creatively,
- tests them under a fitness function,
- prunes the losers, promotes the winners,
- and measures itself with held-out tasks.

That loop is the bet of Verimem.

## Architecture (one screen)

```
┌──────────────────────────────────────────────────────────────────────┐
│                            Verimem                                │
│                                                                      │
│  ╔═══════════════ WAKE ════════════════╗   ╔═════ SLEEP ══════════╗  │
│  ║  Task → Memory retrieval (skills    ║   ║  NREM: cluster        ║  │
│  ║          + similar episodes)        ║   ║   episodes →          ║  │
│  ║  ReAct loop with tool use:          ║   ║   distill skills      ║  │
│  ║   • run_python (sandboxed subproc)  ║   ║   + semantic facts    ║  │
│  ║   • syntax_check, find_function     ║   ║                       ║  │
│  ║   • submit_solution                 ║   ║  REM: pick 2 skills,  ║  │
│  ║  Reflexion-style self-critique on   ║   ║   propose hybrid      ║  │
│  ║   failure → 1-shot retry.           ║   ║                       ║  │
│  ║  Episode persisted to memory.       ║   ║  Curator: merge       ║  │
│  ╚══════════════════ ▼ ════════════════╝   ║   semantic dups       ║  │
│                      │                     ║                       ║  │
│              Episodes (SQLite +            ║  Pruning: Bayesian    ║  │
│              embeddings + causal graph)    ║   fitness → promote / ║  │
│                                            ║   retire skills.      ║  │
│              Skills (JSON files +          ╚══════════ ▲ ══════════╝  │
│              version chain + lineage DAG ──────────────┘              │
│              + Beta-Binomial fitness)                                │
│                                                                      │
│              Semantic facts (decoupled from time)                    │
└──────────────────────────────────────────────────────────────────────┘

Observability layer: every action emits a structured event →
   structlog → metrics registry → dashboard (FastAPI + vis-network).
```

### What's actually inside

| Module | What it does | Key novelty |
|---|---|---|
| `episode.py` | `Episode` + `Trace` — full ReAct trajectory, immutable | timestamped, embedding-indexed |
| `memory.py` | Episodic memory: SQLite + dense recall + causal graph (networkx) | clustering for replay; A→B causal edges via shared skill |
| `semantic.py` | Semantic memory: facts decoupled from time | Tulving-style separation |
| `skill.py` | Skill library — versioned JSON files + index | **Bayesian Beta-Binomial fitness**, **lineage DAG**, status lifecycle |
| `tools.py` | Sandboxed Python executor + AST analyzer | subprocess isolation, timeout, output cap |
| `wake.py` | ReAct loop with skill+episode injection | tolerant parser, Reflexion critique, A/B toggle |
| `sleep.py` | Multi-stage consolidation engine | NREM + REM + Curator + Pruning |
| `prompts.py` | All LLM prompts, in one auditable file | "experience as artifact" thesis |
| `observability.py` | EventBus + structlog + metrics registry | every step emits a typed event |
| `dashboard.py` | FastAPI + HTML dashboard | skill lineage graph (vis-network) |
| `cli.py` | typer + rich CLI | `hippo run/wake/sleep/benchmark/skills/episodes/dashboard` |
| `benchmark/` | 18 HumanEval-style coding tasks + evaluator | wake/heldout split, Wilson CIs, two-prop z-test |

## Scientific anchors

- **Two-stage consolidation**: Walker & Stickgold (2004), Diekelmann & Born (2010). NREM consolidates declarative memory; REM enables creative recombination.
- **Episodic vs semantic vs procedural**: Tulving (1972, 1985).
- **Fast hippocampal replay → slow cortical consolidation**: McClelland, McNaughton & O'Reilly (1995) — the model Verimem's wake/sleep split mirrors.
- **Reflexion**: Shinn et al. (2023) — verbal RL on agents (no gradients) — used here for the self-critique retry.
- **Voyager**: Wang et al. (2023) — skill library for embodied agents — closest prior art for the procedural memory.
- **Bayesian fitness for small N**: Beta-Binomial conjugate prior — robust posterior mean even after 1–2 trials.
- **Declarative → procedural transition**: Anderson (1982) ACT-R, Logan (1988) instance theory — the basis for procedural compilation.
- **Hippocampal forward sweeps**: Pfeiffer & Foster (2013), Diba & Buzsáki (2007) — predictive replay before action — the basis for forward replay.
- **Hebbian plasticity**: Hebb (1949) "cells that fire together wire together" — the basis for the trigger-embedding drift on success.
- **Counterfactual reasoning in episodic memory**: Gershman & Daw (2017) — alternative trajectories during offline replay drive learning beyond mere reinforcement.

## What makes the memory *active* (not just stored)

Most LLM-agent memory systems are passive: they retrieve past prompts and dump
them into context. Verimem's memory is **active** — the act of using a skill
makes it stronger, faster, and more discriminating. **Six** mechanisms compound:

1. **Procedural compilation** — once a skill has succeeded N times with high
   fitness, the DREAMER (during sleep) distills its successful traces into a
   parameterised macro: a list of tool calls with `{{TASK}}` and
   `{{LAST_OBSERVATION}}` placeholders. At wake time, when a strongly-matching
   task arrives, the macro is executed deterministically — **zero LLM tokens,
   no model latency between steps**. The skill is not just remembered, it is
   *compiled* the way deliberate actions become motor reflexes.
   ([compilation.py](hippoagent/compilation.py))

2. **Forward replay** — before the wake loop fires, the agent looks up the top
   skill's past successful trajectories and projects an *expected action
   sequence*. The block is injected as `## PREDICTED PATH` in the user prompt.
   This anchors the LLM's reasoning (less drift on familiar tasks) and lets us
   detect divergence (a learning signal). Pure retrieval — no extra LLM call.
   ([wake.py:_forward_replay_block](hippoagent/wake.py))

3. **Hebbian skill embedding** — every successful application drifts the
   skill's trigger embedding toward the task that just succeeded
   (`new = (1 - α)·current + α·task`, α = 0.05, then re-normalised). Skills
   become *more* retrievable for the kind of task they keep solving — the
   library shapes itself to its workload over time without any retraining.
   ([skill.py:_hebbian_update](hippoagent/skill.py))

4. **Counterfactual REM** — when a skill keeps failing (fitness < 0.5, trials
   ≥ 3), the dreamer doesn't just decrement Bayesian counts. It reads the
   failed trajectory and synthesises an *alternative strategy* — a candidate
   counterfactual skill with the failed skill as parent. The alternative
   competes for retrieval on future similar tasks; if it wins, it supersedes
   the broken approach without manual intervention.
   ([sleep.py:_stage_counterfactual](hippoagent/sleep.py))

5. **Schema formation** — once a domain has accumulated enough skills (≥3
   with cosine similarity ≥ 0.62 on triggers), the dreamer writes a SCHEMA: a
   meta-skill whose body is a one-line rubric for *picking among the
   children*. Lineage edges (`relation='specialises'`) connect each schema to
   its specifics, building a 2-level hierarchy that becomes navigable as the
   library grows. Tulving's episodic→semantic transition.
   ([sleep.py:_stage_schema](hippoagent/sleep.py))

6. **Self-suggested practice** — for skills sitting in the *uncertain middle*
   (fitness 0.45–0.65), the dreamer writes 2 concrete practice prompts that
   would plausibly trigger them. They appear in the dashboard's skill detail
   under "📚 Practice prompts" with one-click "▶ run in chat" buttons.
   Running a prompt feeds real evidence into the Bayesian fitness — so the
   skill is decisively promoted or retired instead of lingering in
   ambiguity. The agent literally suggests its own training set.
   ([sleep.py:_stage_practice](hippoagent/sleep.py))

Together these turn memory from an archive into an organ that grows.

### End-to-end demo (no API keys needed)

```bash
python scripts/demo_active_memory.py
```

Seeds a library with six skills, runs a complete sleep cycle (NREM + REM +
Curator + compilation + counterfactual + schema + practice + pruning) using a
scripted mock LLM, then re-runs a matching task to demonstrate the macro
fast-path. Typical output:

```
Sleep cycle — six mechanisms fire in one pass
  duration    : 1.37s  (12 LLM calls, 3080 tokens)
  🔧 macros   : 1
  🌀 cf       : 1
  🌳 schemas  : 1
  📚 practice : 6 prompts written
  promoted    : 1   retired : 1

Wake — re-running a similar task uses the macro fast-path
  steps       : 2
  tokens used : 0
  llm calls   : 0  (macro fired, no model invoked)
```

### Empirical evidence — macro speed-up

Run `python scripts/bench_macro.py --repeats 3 --latency 0.5` to reproduce:

```
COLD (ReAct)    median  wall=1.296s  llm_calls=2  tokens=560
HOT  (macro)    median  wall=0.202s  llm_calls=0  tokens=0
→ speed-up      :   6.41x
→ time saved    : 1094 ms per task
→ token saved   :   560 per task
```

The simulated LLM models a real-world 0.5 s/call latency (typical for hosted
models). On the **hot path** the macro fires deterministically — not a single
token leaves the box.

### Live dashboard

Visit `/active-memory` (or click "Active memory" in the nav) for a live KPI
panel — compiled-macro coverage, Hebbian-tuned skills, counterfactual lineage,
schema hierarchy. The `/api/active-memory/stats` JSON endpoint exposes the
same metrics for external tooling.

### Closing the loop — explicit user feedback

Every chat turn surfaces 👍 / 👎 buttons. Clicking them feeds the same
Bayesian fitness machinery used by automatic outcomes — no separate
"feedback model" or fine-tune. A 👎 on a successful turn flips the episode
to failure and records a failure trial against each applied skill;
mis-promoted skills decay back into the candidate pool. A 👍 simply boosts
the trial count with a success.

So the library has three sources of evidence, all converging on the same
fitness posterior:
  1. automatic validator outcomes during the wake loop;
  2. counterfactual REM evaluations during sleep;
  3. explicit user up- / down-votes from the chat surface.

## Install

### Option A — Python (local)

```bash
git clone https://github.com/aureliocpr-ctrl/verimem.git
cd hippoagent
python -m venv .venv
source .venv/Scripts/activate           # or .venv/bin/activate on POSIX
pip install -e .
hippo dashboard                         # → http://127.0.0.1:8765
```

The first time you open the dashboard, you'll land on `/welcome` — pick a
provider, paste an API key (or run Ollama locally — no key needed), test the
connection, save. Everything is configurable from the **⚙ Settings** page;
no env-var voodoo required.

### Option B — Docker

```bash
docker compose up
# or:  docker build -t hippoagent . && docker run -p 8765:8765 -v $PWD/data:/app/data hippoagent
```

The container picks up any `*_API_KEY` env vars you pass through. To use a
host-running Ollama, the compose file already maps `host.docker.internal`.

## Using Verimem

There are three ways to interact with the agent. They share the same backend
(memory, skills, sleep cycles) — just pick what suits you.

### 1. Web dashboard

`hippo dashboard` → http://127.0.0.1:8765

| page | what it's for |
|---|---|
| **Chat** ⭐ | the main UI — type a task, get an answer with applied skills |
| **Settings** | pick LLM provider, paste API key, test connection, switch models live |
| **Episodes** | every task ever executed; click any row for the full ReAct trajectory |
| **Skills** | consolidated lessons with Bayesian fitness, status, lineage |
| **Lineage** | interactive graph of how skills derive from one another |
| **Events** | live event stream (every memory write, retrieval, LLM call) |
| **Metrics** | counters/histograms |

### 2. CLI

```bash
hippo chat                       # interactive REPL: type tasks, /sleep, /skills, /quit
hippo run "your task here"       # one-shot
hippo wake --n-tasks 5           # run the bench wake-set
hippo sleep                      # consolidation cycle on demand
hippo benchmark                  # held-out evaluation
hippo skills list / show <id>
hippo episodes list / show <id>
hippo providers list / scan / models <p> / active
```

### 3. As an MCP server inside Claude Code / Cursor / opencode / Cline / Zed

Verimem ships an MCP (Model Context Protocol) server, so any MCP-aware
client can use it as a memory layer. Add this to your client's
`mcp.json` (or equivalent) — **no API key needed**: in hosted mode the host
(Claude Code, Cursor, …) does all the LLM work, so memory tools like
`hippo_recall` / `hippo_remember` cost zero extra API spend.

```json
{
  "mcpServers": {
    "engram": {
      "command": "engram",
      "args": ["mcp"],
      "env": { "ENGRAM_HOSTED": "1" }
    }
  }
}
```

> The `engram` and `hippo` commands are identical (same entry point) — use
> either. A provider API key is only required for the **standalone agent**
> (`hippo_run_task`, `hippo chat`), which runs its own LLM loop; the memory
> layer above never needs one.

Once registered, the host (Claude Code, Cursor, etc.) can call:

| MCP tool | what it does |
|---|---|
| `hippo_run_task` | full wake loop — agent uses its own tools + skills |
| `hippo_consolidate` | trigger a sleep cycle |
| `hippo_recall` | **semantic** search over past episodes (embeddings) |
| `hippo_recall_explain` | semantic recall + per-component score breakdown |
| `hippo_search` | **keyword** search over episode `task_text` (LIKE) |
| `hippo_episode_list` | paginated listing of episodes (`limit`/`offset`/`outcome`) |
| `hippo_episode_get` | one episode in full (trajectory + critique) |
| `hippo_episode_pin` / `hippo_episode_unpin` | protect / release an episode from decay-pruning |
| `hippo_forget` | delete one episode by id (privacy / GDPR) |
| `hippo_metrics_history` | token-usage timeseries bucketed by day |
| `hippo_skills_for` | preview which skills Verimem would inject for a task |
| `hippo_skill_promote` / `hippo_skill_retire` / `hippo_skill_edit` | manual curation |
| `hippo_skill_export` / `hippo_skill_import` | portable JSON bundles (share skills between installations) |
| `hippo_skill_test` | render the prompt-context for a (skill, task) pair without calling the LLM |
| `hippo_skill_top` | top-k skills by `fitness` / `recency` / `activity` |
| `hippo_skill_lineage` | walk the `parent_skills` DAG ancestry of a skill |
| `hippo_skill_compare` | diff two skills (body / fitness / trials) |
| `hippo_skill_similar` | top-k skills by Jaccard overlap on body tokens |
| `hippo_skill_describe` | deterministic 1-line natural-language summary of a skill (no LLM) |
| `hippo_skill_merge` | manually merge skill A into B (sum trials, retire A, lineage tracked) |
| `hippo_episodes_by_skill` | every episode whose `skills_used` includes a given skill |
| `hippo_provider_switch` | switch the active LLM provider at runtime (anthropic / openai / groq / …) |
| `hippo_remember` | **store one fact directly in semantic memory** — no episode, no sleep cycle |
| `hippo_facts_recall` | semantic search over facts (cosine on proposition embedding) |
| `hippo_facts_search` | keyword/substring search over facts (LIKE on proposition) |
| `hippo_facts_list` | paginated listing of all facts (newest-first) |
| `hippo_fact_forget` | delete one fact by id (privacy / GDPR) |
| `hippo_skills_search` | keyword/substring search over skills (LIKE on name+trigger+body) |
| `hippo_skill_bundles` / `hippo_compound_skills` / `hippo_skill_antagonists` | structural introspection |
| `hippo_status` | counts + active provider |
| `hippo_health` | **deep preflight at startup** — 3-tier reachability + counts + flag + tool_count |
| `hippo_stats` | aggregate metrics (episodes by outcome, skills, token usage) |
| `hippo_audit_tail` | last N records of the MCP audit log (forensics) |
| `hippo_prepare_task` | **HOSTED MODE**: assemble prompt context (skills + recall) without calling any LLM |
| `hippo_record_episode` | **HOSTED MODE**: persist an episode the host LLM has just executed |
| `hippo_consolidate_light` | **HOSTED MODE**: dedup + promotion + retirement gates (no LLM) |
| `hippo_plan_forward` | **REASONING / Pezzo B** — hippocampal forward sweep (Pfeiffer & Foster 2013): beam-search top-k skill trajectories from `start_skill`. Pure local, no LLM. |
| `hippo_plan_strips` | **REASONING / Pezzo A** — STRIPS forward planner (Anderson ACT-R / Fikes & Nilsson): chain skills via preconditions/postconditions. BFS shortest-plan. Pure local. |
| `hippo_find_analogues` | **REASONING / Pezzo C** — structural analogy (Gentner 1983): find skills with high structural overlap but LOW semantic similarity. Surfaces transfer candidates the semantic recall misses. |

And read MCP resources:

- `hippo://skills/list` and `hippo://skills/{id}` — consolidated skills
- `hippo://episodes/recent` and `hippo://episodes/{id}` — past trajectories

The result: your Claude Code (or whatever) gets a *second-brain agent* it can
delegate to — and the second brain remembers across sessions, not just within
one conversation.

### 4. Programmatically

```python
from engram.agent import HippoAgent
agent = HippoAgent.build()
result = agent.run_task(
    task_id="my-task",
    task_text="Write a Python function that ...",
    validator=lambda ans: (bool(ans.strip()), "non-empty"),
)
print(result.episode.final_answer)
agent.consolidate()              # nightly sleep cycle
```

### Desktop launchers (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_desktop_shortcut.ps1
```

This creates two shortcuts on your Desktop:
- **Verimem Dashboard** — double-click to launch the web UI (browser opens to http://127.0.0.1:8765).
- **Verimem CLI** — opens a shell with the venv activated, ready for `hippo …` commands.

## Providers — bring any LLM you like

Verimem is provider-agnostic. Set ONE of these env vars (or run Ollama locally) and you're done.
The first matching one wins (or force with `HIPPO_LLM_PROVIDER=<name>`).

| family | provider (alias) | env var | base URL |
|---|---|---|---|
| native | `anthropic` | `ANTHROPIC_API_KEY` | Anthropic SDK |
| native | `ollama` | `OLLAMA_HOST` (defaults to `http://localhost:11434`) | local |
| US/EU | `openai`, `openrouter`, `mistral`, `groq`, `xai` (`grok`), `perplexity`, `fireworks`, `together`, `cerebras`, `gemini` (`google`), `nvidia`, `huggingface` (`hf`), `deepinfra`, `hyperbolic`, `novita`, `lepton`, `anyscale`, `azure` | `<NAME>_API_KEY` | each provider's `/v1` |
| China | `moonshot` (`kimi`), `deepseek`, `qwen` (`dashscope`/`alibaba`), `zhipu` (`glm`), `baichuan`, `yi` (`lingyi`/`01ai`), `doubao` (`ark`), `hunyuan` (`tencent`), `stepfun` (`step`), `minimax`, `spark` (`iflytek`) | `<NAME>_API_KEY` | each provider's `/v1` |
| local OpenAI-compat | `lmstudio`, `vllm`, `localai`, `tabby` | `<NAME>_API_KEY` (any non-empty) | localhost |

Per-stage model overrides (Claude defaults are tuned; for other providers you usually want to set these):

```bash
export HIPPO_MODEL=qwen2.5:7b               # all stages
export HIPPO_MODEL_EXECUTOR=qwen2.5:7b      # ReAct loop only
export HIPPO_MODEL_DREAMER=qwen2.5:14b      # NREM/REM synthesis (smarter recommended)
export HIPPO_MODEL_CRITIC=qwen2.5:1.5b      # cheap critic
```

Discover what's actually reachable from your setup:

```bash
hippo providers list      # all known providers + env-var status
hippo providers scan      # query /v1/models on every configured one (real discovery)
hippo providers models kimi    # list one provider's models
hippo providers active    # which provider is selected right now
```

Examples:

```bash
HIPPO_LLM_PROVIDER=kimi     MOONSHOT_API_KEY=sk-...                              hippo wake
HIPPO_LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-... HIPPO_MODEL=deepseek-reasoner hippo wake
HIPPO_LLM_PROVIDER=ollama   OLLAMA_MODEL=qwen2.5:7b                              hippo wake
HIPPO_LLM_PROVIDER=groq     GROQ_API_KEY=gsk-...   HIPPO_MODEL=llama-3.3-70b-versatile hippo wake
```

For tests / dev:

```bash
pip install -e ".[dev]"
```

## Quick run

```bash
# Tests (fully offline, mock LLM)
HIPPO_OFFLINE=1 pytest

# CLI
hippo --help
hippo run "Define a Python function that returns the n-th prime"
hippo wake --n-tasks 5             # run wake-set (records episodes)
hippo sleep                        # run consolidation cycle
hippo benchmark                    # run held-out tasks with consolidated skills
hippo skills list
hippo skills show <id>
hippo episodes list
hippo dashboard                    # → http://127.0.0.1:8765
```

## End-to-end demo (the actual experiment)

```bash
python run_demo.py --n-wake 10 --n-heldout 8
```

What it does, in order:

1. **Reset**.
2. **Baseline**: held-out tasks, **without skills, without past episodes** — pure model.
3. **Wipe** the episodes the baseline accidentally created (clean slate).
4. **Wake**: run the wake-set; the agent records everything.
5. **Sleep**: NREM clusters episodes → distills skills; REM proposes hybrids;
   Curator merges semantic duplicates; pruning promotes/retires by fitness.
6. **Hippo**: re-run the held-out tasks **with the consolidated skill library**.
7. **Compare**: pass-rate, avg-steps, avg-tokens, skill-reuse-rate.
   95% Wilson interval on rates. Two-proportion z-test for the gap.

The script saves a JSON report under `data/reports/`.

### First-run observations

A small run (10 wake / 8 held-out) on Claude Haiku 4.5 produced these
consolidated skills, **derived autonomously** from the agent's own behavior:

- `Verify test cases before blaming algorithm` (NREM, fitness=0.70)
- `Validate test runner output before debug` (REM hybrid, 0.70)
- `Harden JSON code payloads end-to-end` (REM hybrid, 0.70)
- `Escape newlines in JSON code strings` (the Curator merged 4 near-duplicates of this)

These are not generic "be helpful" stubs — they are concrete lessons the
agent extracted from its own failure modes (mostly: malformed JSON in
`run_python` calls when the code contained newlines).

The pass-rate gap on N=8 held-out is **not statistically significant**
(p≈0.5 by two-prop z-test) — and that is the honest scientific finding at
this scale. Ramping to N≥30 is the next experiment; the architecture is
ready for it.

## What makes this a prototype, not a toy

- ✅ 23 unit + integration tests passing
- ✅ Real LLM client + offline mock for deterministic CI
- ✅ Sandboxed Python execution (subprocess + timeout)
- ✅ Structured logging + event bus + metrics registry
- ✅ Bayesian fitness with conjugate prior (not naive ratios)
- ✅ Skill lineage DAG (networkx) — full provenance from episode → skill → REM hybrid → merge
- ✅ Web dashboard with skill lineage visualization
- ✅ Reproducible benchmark with deterministic seed split
- ✅ Statistical primitives (Wilson interval, two-prop z-test) for honest reporting
- ✅ A/B toggle (`--no-skills`) so baseline-vs-hippo is a single CLI flag

## 👁 Vision — works with any multimodal provider

The `vision_describe` tool dispatches to the right multimodal endpoint per
provider. Defaults shipped (override via `HIPPO_VISION_MODEL`):

| Provider | Default vision model | Status |
|---|---|---|
| Anthropic | `claude-haiku-4-5-20251001` | ✓ verified live |
| OpenAI | `gpt-4o-mini` | ✓ |
| Google Gemini | `gemini-1.5-flash` | ✓ free tier |
| Groq | `meta-llama/llama-4-scout-17b-16e-instruct` | ✓ verified live, free tier |
| OpenRouter | `anthropic/claude-haiku-4.5` | ✓ verified live |
| xAI Grok | `grok-4` | ✓ (paid) |
| Mistral | `pixtral-12b-latest` | ✓ |
| Alibaba Qwen | `qwen-vl-plus` | ✓ |
| Zhipu GLM | `glm-4v` | ✓ |
| Moonshot Kimi | `moonshot-v1-8k-vision-preview` | ✓ |
| 01.AI Yi | `yi-vision` | ✓ |
| ByteDance Doubao | `doubao-vision-pro-32k` | ✓ |
| NVIDIA NIM | `meta/llama-3.2-90b-vision-instruct` | ✓ |
| Together / Fireworks | Llama 3.2 Vision 90B | ✓ |
| HuggingFace router | Llama 3.2 Vision 90B | ✓ |
| Ollama (local) | `llava` (override with OLLAMA_VISION_MODEL) | ✓ — needs `ollama pull llava` (or `qwen2-vl`, `llama3.2-vision`, `bakllava`, `moondream`) |
| **DeepSeek** | n/a | ✗ DeepSeek V4 API doesn't accept image_url blocks |

The dispatcher prefers `HIPPO_VISION_MODEL` env var > `OLLAMA_VISION_MODEL`
(for Ollama) > the default in the table above. So you can mix: text inference
on cheap-fast model, vision on a multimodal-capable one — same single call.

```bash
# Use Ollama for everything but route vision to Anthropic:
HIPPO_LLM_PROVIDER=ollama OLLAMA_MODEL=qwen2.5:7b \
  HIPPO_VISION_MODEL=ignored  # vision uses provider, set ANTHROPIC_API_KEY too
hippo dashboard

# Use DeepSeek for text, fallback to Groq for vision:
# (DeepSeek V4 has no vision; agent calls vision_describe → falls through to
# the configured fallback chain.)
```

## 🔁 Auto-fallback provider chain

When the active provider hits rate-limit / quota / 5xx, Verimem transparently
tries the next configured provider. Configure in `/settings` → "Fallback chain":

```
primary: Anthropic Claude   (fast, paid)
   ↓ on 429/quota
fallback 1: Groq llama 70b  (free tier, very fast)
   ↓ on quota
fallback 2: Ollama qwen 7b  (local, always available)
```

Result: zero-downtime LLM access, scaling free → paid → premium automatically.
Recoverable error patterns: `429`, `rate`, `quota`, `billing`, `credit`,
`limit`, `503`, `504`, `timeout`, `connection`, `overload`.

## 📋 Plan mode

Press **📋 Plan first** in the chat instead of Send. The agent produces a
numbered plan (3-7 steps) WITHOUT executing anything. Review it, then click
**✓ Approve & execute** to run the plan, or **✗ Reject**.

Useful for: cautious computer-use tasks, multi-step shell ops, anything
where you want to know what will happen before it does.

## 🔐 Permissions & Sandbox

Verimem exposes a **single master switch** plus 6 granular toggles in
`/settings`:

| Capability | Default | Description |
|---|---|---|
| Sandbox master | **ON** | When OFF, all permissions are unrestricted |
| Filesystem | `home` | `strict` (data/ only), `home` (user dir), `full` (anywhere) |
| Computer use | OFF | mouse/keyboard control via pyautogui |
| Webcam | OFF | capture frames + describe via vision LLM |
| Shell | OFF | arbitrary `cmd.exe` / `/bin/sh` commands |
| Web | ON | web_fetch + DuckDuckGo search |
| Vision | ON | describe images via multimodal LLM |

Two preset buttons:

- **🔓 Unleash** — sandbox OFF + all permissions ON. Full PC access.
- **🔒 Lockdown** — sandbox ON, filesystem = strict, only web + vision.

When the sandbox is OFF the agent has *full* access to your machine: it can
read/write any file, run any shell command, control your mouse and keyboard,
capture your webcam, fetch the web, and describe images. Use this only with
models you trust.

## 📱 Android / Termux

Verimem runs on Termux (Android 10+) with a few caveats:

```bash
pkg install python git ffmpeg-essentials
git clone https://github.com/aureliocpr-ctrl/verimem.git
cd hippoagent
python -m venv .venv && source .venv/bin/activate
# Skip pyautogui (no display server) and opencv (heavy):
pip install -e . --no-deps
pip install anthropic openai sentence-transformers numpy scipy scikit-learn \
            networkx pydantic structlog typer rich fastapi uvicorn jinja2 \
            python-dotenv httpx mcp textual pillow
hippo dashboard --host 0.0.0.0 --port 8765
```

Open `http://<phone-ip>:8765` from any device on the same network. CLI works
fully (`hippo chat`, `hippo tui`). Webcam/computer-use are no-op on Android,
everything else (incl. Ollama via Termux+proot or remote, Groq, Gemini,
Anthropic) works normally.

## ⚠ Security notes

- **The Python sandbox is `subprocess -I`, not a real isolation layer.** A task
  like *"write a calculator and save it to the desktop"* will actually write to
  your disk, because the LLM-generated code can call `open()`, `os.makedirs`,
  `requests.get`, etc. That's by design for this prototype (it's how you get
  an agent that *does* things), but it means **only run Verimem against models
  and tasks you trust**. For untrusted use, run the whole agent in Docker with
  no host volume mounts, or wrap the executor in seccomp/Firejail.
- API keys saved via the Settings page are written to `data/user_settings.json`
  in plaintext. Don't commit that file (it's in `.gitignore`). Production
  deployments should swap the storage for an OS keychain or Vault.

## What's still toy

- Sandbox is `subprocess -I`, not seccomp/Firejail/Docker — fine for non-adversarial models, not for production.
- Benchmark is small (18 tasks). Real validation would need ≥100 tasks across more domains.
- No active learning: the agent doesn't *choose* which tasks to attempt to maximize learning.
- No explicit forgetting curve over time — only fitness-based pruning.
- Single-agent. The lineage DAG is ready for skill-sharing across instances; the marketplace is not built.

## Repository layout

```
verimem/                       # repo root
├── engram/                    # core library (import engram)
│   ├── __init__.py
│   ├── config.py              # all hyper-params, single source
│   ├── observability.py       # event bus, logger, metrics
│   ├── llm.py                 # Anthropic client + MockLLM
│   ├── embedding.py           # sentence-transformers wrapper
│   ├── tools.py               # PythonExecutor, CodeAnalyzer, tool registry
│   ├── episode.py             # Episode + Trace
│   ├── memory.py              # EpisodicMemory (vector + causal graph)
│   ├── semantic.py            # SemanticMemory (facts)
│   ├── skill.py               # Skill + SkillLibrary (lineage, fitness, lifecycle)
│   ├── prompts.py             # all prompts, auditable
│   ├── wake.py                # ReAct loop with skill injection + critique
│   ├── sleep.py               # NREM + REM + Curator + Pruning
│   ├── agent.py               # high-level orchestrator
│   ├── cli.py                 # typer + rich CLI
│   └── dashboard.py           # FastAPI dashboard
├── benchmark/                 # task suite + evaluator + statistics
├── tests/                     # pytest suite
├── data/                      # episodes/skills/semantic/runs/reports (gitignored)
├── run_demo.py                # full baseline-vs-hippo experiment
├── pyproject.toml
└── README.md
```

## License

MIT, but please cite the underlying neuroscience papers if you build on the consolidation idea.
