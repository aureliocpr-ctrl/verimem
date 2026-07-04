# Competitive landscape & path to "best real memory" (2026-06-20)

Reverse-engineering of the memory-layer field + Engram's honest position. Sourced from a
multi-agent recon pass (web + GitHub + arXiv). No hype; self-reported numbers flagged.

## The competitors (real architecture, not marketing)

| system | architecture | published numbers | the catch |
|--------|--------------|-------------------|-----------|
| **mem0** (mem0ai/mem0, ~59k★) | 2-phase LLM: extract facts → ADD/UPDATE/DELETE/NOOP consolidation over a vector store (+ optional Neo4j graph). No raw turns, no decay, no PPR. | LoCoMo J=66.9 (paper, ECAI'25, author-run); README claims LoCoMo 91.6 / LongMemEval 94.8 (unverified). | **No write-path grounding/entailment gate** — only an LLM heuristic. On LoCoMo, plain **full-context BEAT mem0 on accuracy (72.9 vs 68)**; mem0's win is latency/tokens, not correctness. Zep alleges mem0 misconfigured competitors. |
| **Zep / Graphiti** (getzep) | Bi-temporal knowledge graph: episode + entity + community subgraphs; every edge has validity interval (t_valid, t_invalid). LLM entity/relation extraction. | Self-reported LoCoMo 75.14 (disputes mem0). | Heavy graph ops; LLM on the write path; numbers contested. |
| **Letta / MemGPT** (letta-ai) | Self-editing memory blocks, sleep-time agents, OS-style paging. | DMR-style; varies. | Agent-framework-coupled; memory is a component, not a standalone moat. |
| **Cognee** (topoteretes) | ECL (extract-cognify-load) graph+vector pipeline. | sparse. | early; pipeline-heavy. |
| **MemOS** (MemTensor) | the system that **wins the HaluMem leaderboard** — but HaluMem is authored by MemTensor (conflict of interest). | HaluMem-Medium: Extraction F1 79.7 / Updating 62.1 / QA 67.2. | self-benchmarked; even "best" tops ~67% QA → large headroom. |

## Where Engram genuinely LEADS (the moat is real)
- **Write-path anti-confabulation gate** — L1 lexical + L3 lexical + **L3-semantic NLI** (now wired) + **L4 NLI grounding** (source⊧fact, AUROC 0.971 on SNLI). **No competitor has a grounding/entailment admission test** — mem0/Zep/Letta admit whatever the extractor LLM emits. This is the differentiator, and it's on the axis HaluMem measures ("interference" = corrupted memory a naive store admits).
- **Honest, reproducible benchmarking** — competitors' headline 90%+ numbers are self-reported on the near-saturated LoCoMo; Engram reports with Wilson CIs + load-bearing caveats + a Claude-judge asterisk.
- **Timestamp-aware contradiction** (supersession ≠ contradiction) shipped end-to-end (HaluMem FPR 0.10→0.0125).

## Where Engram LAGS (the work to lead)
1. **Absolute QA on hard types** ~0.4–0.5 (mid-pack). Retrieval is strong (LongMemEval recall@5 0.909); the gap is answering/reasoning on temporal + preference.
2. **No like-for-like LoCoMo/LongMemEval-500 number** vs the cited SOTA (TiMem 76.9, EverMemOS 83.0 peer-reviewed; vendor 90%+ unverified). → **run qa_comparative over all 500 LongMemEval-S**, accept the Claude-judge asterisk.
3. **No official HaluMem protocol number** (Extraction-F1 / Updating / QA). Our interference work is a proxy. → **build the official HaluMem harness** — the leaderboard is conflict-of-interest + low-ceiling, the single best "honest best-on-X" opportunity.
4. **DX / distribution** — mem0 ships a 5-line SDK (pip+npm), an MCP server (OpenMemory), a managed cloud, ~59k stars. Engram is MCP-first but lacks a marketable `add()/search()` SDK + docs/onboarding.
5. **Perf at scale** — facts recall is O(N) brute-force numpy, no ANN (≈3GB matrix at 1M, full rebuild on write). FAISS is episode-only. → extend ANN to facts; incremental corpus cache.
6. **Durability hot-path** — the non-deferred write path runs `synchronous=NORMAL` and never checkpoints → a committed-but-uncheckpointed write can be lost on hard crash (the journal only covers DEFERRED writes); no cross-DB atomicity; no crash-injection test.

## The plan to "best real, proven" (ranked)
- **P0 — own the differentiator axis:** build the official **HaluMem** harness (extraction/updating/QA) and post an honest number vs the (conflicted) MemOS leaderboard. This is where the moat shows.
- **P0 — like-for-like:** LongMemEval-S full-500 end-to-end (strict-answer + dates ON), Claude-judge asterisk, vs TiMem 76.9 / EverMemOS 83.0.
- **P1 — close the QA gap:** temporal + preference reasoning (date-carry shipped; preference needs answer-mode work).
- **P1 — perf:** ANN (FAISS/HNSW) for facts recall; incremental corpus cache; commit a 768-d 100k–1M scale bench.
- **P1 — durability:** `ENGRAM_SQLITE_SYNCHRONOUS` knob + post-write checkpoint + a real crash-injection test; document the window.
- **P2 — DX:** a thin `add()/search()` SDK over the MCP tools + a quickstart, to answer mem0's adoption ergonomics.

## Adoption roadmap (GitHub source-level study — what to build, with engram/ wire-points)
Code-level reverse of mem0/Graphiti/Letta/HippoRAG/Cognee. Ranked; each verified against engram/.
- **P0 — typed-predicate KG edges** (mem0/Graphiti): `entity_populate.populate_entities_for_fact` emits only untyped `co_occurs` clique edges, discarding semantics — but `openie.py` already produces typed snake_case triples. Wire openie into the write-path (env-gated like ENGRAM_GROUNDING_WRITE).
- **P1 — synchronous reconcile loop** (mem0 ADD/UPDATE/DELETE/NONE): every piece exists but OFF — `reconcile_new_fact` (semantic.py:2924, behind ENGRAM_RECONCILE_ON_WRITE) uses `looks_like_conflict` (token-correlation) and never supersedes. Replace with the **semantic_conflict NLI judge** (already made ts-aware) + flip to auto_supersede ONLY when (status-rank↑ AND NLI=contradiction AND evidence). Keep Engram's SOFT-delete (lineage) — strictly better than mem0's hard DELETE.
- **P1 — bi-temporal edges** (Graphiti): `entity_kg.entity_edges` has NO temporal columns; edges are CASCADE-deleted, not invalidated. Add `valid_at/invalid_at/expired_at` via a migration ladder; invalidate-don't-delete on contradiction.
- **P1 — agent self-edit block tools** (Letta): mostly DONE — `hippo_self_model_update/get/render/refresh` already exist; only append/rethink conveniences missing (low value).
- **P2 — PPR seed weighting** (HippoRAG): `ppr_seed.ppr_seeded_fact_ids` seeds uniformly via `ppr()`; `ppr_weighted()` exists unused — weight seeds by entity degree (IDF-like, down-weight broad seeds). Core-retrieval win; needs an A/B.
- **P2 — recognition seed filter** (HippoRAG-2): CE/LLM-gate which entities seed PPR (not every extracted entity).
- **NOTE:** Engram's PPR core (entity_kg.ppr, ppr_seed, ENGRAM_PPR_FUSION default-on) already equals/beats the HippoRAG reference; the gaps are seed-weighting + recognition-gating, not the core.

**Honest verdict:** Engram is NOT "the best known" today. It has a *real, rare moat* (write-path anti-confabulation no competitor matches) and honest measurement; it lags on absolute hard-type QA, like-for-like headline numbers, scale, and distribution. The path to "best on a defensible axis" is HaluMem (the moat's home turf) + the LongMemEval-500 like-for-like — both runnable with the existing harness.

---

## 2026-07-04 refresh — web recon (new entrants, benchmark shifts, platform-native memory)

Fresh web pass (search + targeted fetches; vendor numbers flagged as self-reported).

### New/changed players since 2026-06-20
| system | what it is | claimed numbers | the catch |
|--------|-----------|-----------------|-----------|
| **EverMind / EverMemOS** (evermind.ai, arXiv 2601.02163) | "memory OS", 4 layers; raw turns → structured **MemCells** organized in **MemScenes** graphs; markets the architecture as **"engram-inspired lifecycle"** (our term, their brand now). Open-source self-host + enterprise cloud. | LoCoMo **93.05**, LongMemEval-S **83.0** (self-published); measures mem0 at 49.0 on LME | Blog describes salience scoring/compression/filter ("preventing garbage memories") — a heuristic screen, **no evidence of an entailment/grounding admission gate** (their code not yet audited by us — verify before claiming publicly). Brand collision: they own "engram-inspired" messaging at scale. |
| **OMEGA** (omegamax.co, Sosa Research) | local-first SQLite memory, 6-stage retrieval (vector + FTS), no cloud | LongMemEval **95.4%** (466/500, GPT-4.1 judge, self-run leaderboard; Mastra 94.87, Emergence 86, Zep 71.2 on the same board) | vendor-run leaderboard; local-first + SQLite = our positioning, no longer unique |
| **Hindsight** (Vectorize.io, MIT) | 4 parallel retrieval strategies per query (semantic, BM25, graph traversal, temporal) | n/a | new entrant, no admission control claimed |
| **MemPalace / MemPal** | spatial-metaphor memory (arXiv 2604.21284 critiques it) | baseline finding: **verbatim text + good embeddings = 96.6% LongMemEval** | the load-bearing datum: extraction-based systems LOSE information; a verbatim store with good retrieval nearly saturates LME-S |
| **mem0** (update) | — | **$24M Series A**, ~47.8k stars; graph features paywalled at $249/mo | distribution lead growing |

### Benchmark landscape shifted
- **LongMemEval-S is near-saturated and vendor-inflated** (95.4 / 94.87 / 96.6-verbatim-baseline). A headline win there is no longer differentiating; a mid-80s+ honest number is table stakes ("not ridiculous"), not a moat.
- **LongMemEval-V2** (arXiv 2605.12493): the field's direction — **web-agent trajectories** (25M–115M tokens), abilities = static/dynamic state, workflow knowledge, environment gotchas, premise awareness. SOTA only **70-75%** (AgentRunbook-C 74.9 small / 70.1 medium; RAG baseline 42.8). Wide open, and it plays to Engram's native episodes/skills/procedural memory.
- **HaluMem** stays the differentiator's home turf (updating/interference; MemOS's 62.1 self-benchmarked, conflict of interest documented).

### Platform-native memory is now real (structural risk)
Anthropic shipped **Memory for Claude Managed Agents** (public beta, April 2026: filesystem-mounted memory + compaction in the managed harness); OpenAI followed within days in the Agents SDK (model-native harness, filesystem tools). Platform "good-enough" memory will eat undifferentiated recall layers. What it does NOT do: cross-provider/multi-tenant memory, provenance/trust-conditioning, admission control, temporal KG, truth-maintenance. The moat axis is unchanged — but "we store and recall" is now free with the platform.

### Strategic read (2026-07-04)
1. The MemPal verbatim-baseline finding **independently confirms our HaluMem updating diagnosis**: extraction is where information dies. Our pitch sharpens: the memory layer's value is not extraction — it is **admission control + provenance + truth maintenance** (the database-with-constraints vs data-lake argument).
2. LME-S end-to-end 500 (paced, Claude-judge asterisk) is still worth ONE honest run for the comparison table — as table stakes, not as the flag.
3. **LongMemEval-V2 is the first-mover opening**: no memory-layer competitor has posted; our episodes/skills/procedural side maps to its abilities.
4. **Brand**: "engram-inspired" is being marketed by EverMind. If we want the term, we need public technical writing soon (repo/README/blog), or pick the fight elsewhere.
