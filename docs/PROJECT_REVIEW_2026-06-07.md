# Engram / HippoAgent — Total Project Review (2026-06-07)

> Evidence-based, done by reading code + running commands (no subagents — they
> fabricate). Every verdict carries a receipt. Triggered by Aurelio: "fai un
> review totale" after catching repeated over-claims. Honest, no spin.

## TL;DR (the honest distinction)
- **The ENGINE is production-quality** — verified with receipts (below). We are not
  debugging a broken memory engine anymore.
- **The PRODUCT is NOT yet shippable to the public** — the headline `pip install hippoagent`
  was **broken** (not on PyPI), and the README carried **3 false claims** I had written.
  All caught by this review and fixed. The remaining distance is **market** (publish,
  adoption, demo) + a few quality gaps, not core functionality.

## Inaccuracies this review caught + fixed (the "negligence" Aurelio sensed — real)
1. **`pip install hippoagent` → PyPI 404** (NOT published; `engram` on PyPI is someone else's
   v0.1.0). The #1 onboarding command failed for every new user. → README + PLUGIN_QUICKSTART
   now install from `git+https://github.com/aureliocpr-ctrl/hippoagent.git` (repo is public, HTTP 200).
2. **"no entity-graph / multi-hop walk yet"** — FALSE. `engram/entity_kg.py` (982 LOC, schema
   v1-v6) + `engram/openie.py` implement an entity KG with OpenIE + Personalized-PageRank +
   multi-hop neighbors, MCP-exposed (`hippo_ppr_retrieve` / `hippo_entity_neighbors` /
   `hippo_extract_entities`), wired into agent/self_model/mcp_server, **28 tests pass**. I had
   trusted a stale 2026-05 survey instead of the code. → corrected (commit 2deb51f).
3. **"the only one that runs as a native MCP server"** — FALSE (Mem0 ships OpenMemory MCP; my own
   table said so). → reframed to the *combination* being unique (commit d60d95f).
4. **"Tonegawa Nobel 2014"** in the intro — confabulation (Nobel was 1987, not for engrams). →
   fixed (commit b8531f7).

## Scorecard (receipts)
| Dim | Verdict | Evidence |
|---|---|---|
| Tests / CI | ✅ | 4365 test fns / 597 files; CI **GREEN** cross-platform on `main`@d60d95f (11 test jobs 3 OS × 4 py + build, confirmed by `gh run watch --exit-status`=0); CI skips only 1 slow + 2 e2e files |
| Core save/recall | ✅ | fresh-user empty corpus: init 0.07s, 3 saves 0.35s, recall **0.06s** correct ranking; live IT recall@5 **0.84** / MRR 0.71; LongMemEval-s recall@5 **0.85** |
| MCP server | ✅ | 228 tools (227 `hippo_*` + `sandbox_exec`), every advertised tool dispatchable (orphan-guard test), real-subprocess stdio boot clean + protocol-clean stdout (e2e 2/2) |
| Entity-KG / multi-hop | 🟡 **built-not-live** | engine real + unit-tested (entity_kg.py 982 LOC + openie.py, 28 tests, PPR byte-deterministic, ~27→70 ms @ 10→1000 synthetic nodes) BUT **`entity_get` hit_rate = 0.0 on the live corpus** (`bench_p2_entity_kg.py`: facts_linked=0 every query) — no OpenIE extraction has populated entities. Making it live = LLM-OpenIE backfill (~2585 calls) + save-path wiring. I mis-stated this BOTH ways before (first "missing", then "available"); it's *plumbing-complete, not data-complete*. |
| Security | ✅ | 0 secrets/keys committed (`git grep` clean), 0 corpus dump, CI `security` workflow green (pip-audit/bandit/ruff-S), MIT license (commercial OK) |
| Data reliability | ✅ | corpus 100% on active e5-768 model (flip done + verified), backups present, 44% quarantine = correct curation of test-pollution (sampled: 100% noise, 0 good facts wrongly hidden) |
| Code quality | 🟡 | 75,439 LOC / 319 files; **`mcp_server.py` = 11,828 LOC monolith** (maintainability risk); only 4 TODO/FIXME (low debt); coverage gate **46%** (low for "production") |
| Install / onboarding | 🟡 | git-install works (verified equivalent via fresh probe); **NOT on PyPI** → `pip install hippoagent` was broken (now corrected to git) |
| Docs / positioning | 🟡 | honest comparison section now in README (real LongMemEval + competitor table + caveats); 4 inaccuracies fixed; idiosyncratic internal benchmarks still dominate the body |
| Adoption / market | ❌ | 0 GitHub stars, not on PyPI, no public demo / white-paper. This is the real "vendibile" gap — non-code. |
| Scalability | 🟡 | cosine recall benched to 200k earlier; PPR + entity-KG at scale **un-benchmarked** |

## Prioritized gaps (what "really production-ready / sellable" still needs)
- **P0 — Publish to PyPI** (or keep README install git-only, which is now honest). Onboarding.
- **P1 — Benchmark the entity-KG / PPR retrieval** vs the cosine baseline + (ideally) LOCOMO/
  multi-hop. We have the capability; prove it (turns the "behind" into a real differentiator).
- **P1 — Coverage 46% → higher** on the core recall/save paths; consider splitting the
  `mcp_server.py` 11.8k-LOC monolith.
- **P2 — Docker CPU-only slim** (7-18GB → ~1.5GB) for a server edition; public demo + short paper.

## What is NOT a blocker (verified clean)
MIT license, no secrets, no private-corpus dump, CI green cross-platform, core engine reliable,
recall quality competitive (retrieval recall@k), MCP first-run clean. The engine is sound.
