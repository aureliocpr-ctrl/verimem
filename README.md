# Verimem

**Verified memory for AI agents.** Every write passes an admission gate, every
read carries provenance, and when the evidence isn't there the system abstains
instead of guessing.

[![PyPI](https://img.shields.io/pypi/v/verimem)](https://pypi.org/project/verimem/)
[![CI](https://github.com/aureliocpr-ctrl/verimem/actions/workflows/ci.yml/badge.svg)](https://github.com/aureliocpr-ctrl/verimem/actions)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue)](./LICENSING.md)
[![Website](https://img.shields.io/badge/web-verimem.com-informational)](https://verimem.com)

Most memory layers optimize for how much they can recall. Verimem optimizes for
whether you can **trust** what comes back: facts are admitted through an
anti-confabulation gate, stored with their sources, revised through explicit
supersession (never silent overwrites), and answered with citations — or with an
honest *"I don't know."*

## Features

- **Gated writes with the grounding moat ON by default** — every fact enters as
  a low-trust claim and must be backed by evidence to gain status. The
  **source⊢fact grounding gate** (the moat, judge AUROC **0.96–0.97**) runs by
  default: an extraction confabulation the source doesn't entail is quarantined,
  not absorbed. A `Memory(llm=...)` uses that llm as the judge (best quality); the
  conversation-ingest path uses the free local cross-encoder (AUROC ~1.0 on
  extraction confabs, no per-fact LLM call). With no judge configured the gate
  fail-opens (admits) — it never blocks a user who has none. Contradiction
  screening runs with the `strict` preset. Opt-in
  origin tagging (`tag_beliefs=True` at ingest) additionally classes an
  unverified user assertion as `user_belief`: stored, but out of default
  recall until you ask for it (`search(..., include_beliefs=True)`).
- **Provenance on every read** — answers cite where each fact came from
  (conversation, document offset, tool call). A `TrustReport` explains *how the
  system knows*: chain of custody, declared conflicts, or an explicit abstention.
- **Bi-temporal history** — facts carry both *when it happened* and *when we
  learned it*. Query the past (`as_of`), see transitions ("changed from X to Y
  on date Z"), and audit every revision.
- **Abstention by design** — on questions the store cannot support, Verimem
  says so instead of stitching an answer from the nearest-but-irrelevant facts.
  Memory-boundary abstention holds at 1.0 across our end-to-end runs. It is **ON
  by default on every served surface** (gateway/console self-calibrate the floor
  per tenant); in the embedded SDK it is one switch away —
  `explain(..., min_relevance="auto")` or `ENGRAM_MIN_RELEVANCE=auto` — left
  permissive by default so a brand-new, near-empty store doesn't over-abstain
  while it fills up (the floor is sharpest on real-size corpora).
- **Document memory with exact citations** — index PDF/DOCX/HTML/EPUB/text
  files; semantic search returns passages with file, version and character
  offsets; passages can be promoted to memory *through the gate*, citation
  attached.
- **Consent-first import** — bootstrap from your ChatGPT / Claude export:
  conversations are listed first, nothing is ingested without an explicit
  selection.
- **Opt-in auto-memory** — `AutoMemory(memory).observe(role, text)` watches a
  live conversation and remembers on its own, but through the SAME gated
  pipeline as explicit writes (extraction → gate → provenance). Opt-in by
  construction: if you don't instantiate it, it doesn't exist.
- **Trust odometer** — `m.trust_stats()` / `verimem stats`: persistent
  counters of what the gate actually *did* on your store — writes admitted,
  quarantined, rejected, and honest read-path abstentions, with per-layer
  attribution. Observable actions, not marketing claims; no fact text is
  copied into the counter.
- **True forget** — `delete(purge_history=True)` removes the fact *and* its
  supersession chain; the deleted data does not resurface through history or
  time-travel queries.
- **Per-source trust, two channels** *(flag-gated)* — every writing source earns
  a reputation from inter-source agreement (consistency) and from how its claims
  fare in use (outcome); the weaker observed channel decides. Independence
  clustering collapses copies/colluders of one feed to a single witness, so
  manufactured consensus cannot self-confirm. Reproduced on a real held-out
  corpus (HaluEval, 3/3 seeds): a 4-id cartel that self-confirms to 0.90 under
  naive counting is demolished to 0.20, honest sources restored to 0.95, and
  the hallucinated answers it pushed drop out of recall entirely.
- **Epistemic labels** — a fact can carry the *kind* of guarantee behind it:
  `proven` (a named machine-checkable proof), `unbeaten` (held up to a declared
  bound — the bound only grows), or `refuted` (a named counterexample,
  absorbing). "Held to 10^6" and "proven" are never conflated.
- **Derived knowledge, through the same gate** — the composition ring derives
  new candidate facts from verified ones (declared substitution patterns),
  pushes them through the *same* admission gate as every other writer, and
  admits survivors signed (`actor:composer` — engine writes never testify for
  themselves), traced (`derives_from` parents, retractable if a parent falls)
  and labeled with the exact check that passed. Few but zero-false by
  construction. Run it one-shot (`python -m engram.compose_daemon --db ...`,
  schedule with cron/Task Scheduler): the daemon refuses to compose when the
  engine's own writes already dominate the recent stream (self-echo
  guard-rail).
- **Read-path guardian** — when the store holds a better-guaranteed truth about
  the same subject, a read doesn't just abstain: it *corrects*, citing both
  facts (`correct_read` → ACCEPT / CORRECT / ABSTAIN; a refuted fact is never
  served). Paired with **active probes** that build the query which would
  falsify a stored fact — finding independent counter-evidence proposes a
  `refuted` label, surviving grows its `unbeaten` bound — the store falsifies
  itself instead of waiting for a contradiction to arrive.
- **Ignorance map** — "I don't know" becomes "here is *what* I'm missing": each
  unanswerable query is classed (no evidence / below the floor / evidence
  quarantined / a live conflict) with the concrete source or audit that would
  answer it — the active complement of abstention.
- **Provenance signing** *(opt-in)* — an unforgeable HMAC of *who is speaking*
  rides inside each write's provenance ref, complementing the entailment gate's
  *what deserves admission*: content authenticity **and** channel authenticity,
  the two halves no deterministic content filter alone can certify against an
  adaptive adversary.
- **Local-first** — SQLite storage, local embeddings, injectable LLM. Runs
  air-gapped (`verimem airgap` verifies zero-egress configuration).

## Install

```bash
pip install verimem
```

## Quickstart (Python)

```python
from datetime import datetime

from verimem import Memory

m = Memory("memory.db", llm=my_llm)   # any client with .complete(system, messages)

# Gate presets: "balanced" (default), "strict" (reject on contradiction or
# failed source-grounding — needs a grounding judge), "permissive" (creative /
# low-stakes contexts, no quarantine). Per-call args always override.
m = Memory("memory.db", preset="strict", grounding_llm=my_llm)

# Store a conversation — facts are extracted atomically and pass the gate.
# user_name makes the app-provided identity the subject of the facts.
m.add([{"role": "user", "content": "I moved to Berlin in March."}],
      user_name="Alice")

# THE MOAT, live — the reason Verimem exists. Same source, two writes:
src = "We migrated the analytics store to Postgres last quarter."
m.add("Analytics runs on Postgres.", source=src)   # entailed  -> admitted
r = m.add("Analytics runs on MongoDB.", source=src)  # confab -> QUARANTINED
assert r["status"] == "quarantined"   # stored but OUT of default recall —
                                      # your agent will never repeat it as truth

# Store a single verified fact (no LLM needed)
m.add("Deploy pipeline is green", verified_by=["ci:main:green"])

# Search — optionally with history context or as of a past moment
m.search("where does Alice live?")
m.search("where did Alice live?", as_of=datetime(2024, 1, 1).timestamp())

# Ask HOW the system knows: evidence dossier or an explicit abstention
report = m.explain("where does Alice live?")
```

## Quickstart (Claude Code / MCP)

Add to `.mcp.json` in your project (or `~/.claude/.mcp.json`):

```json
{
  "mcpServers": {
    "verimem": {
      "command": "engram",
      "args": ["mcp"],
      "env": { "ENGRAM_HOSTED": "1", "ENGRAM_TOOL_NAMESPACE": "verimem" }
    }
  }
}
```

This exposes the memory tools (`verimem_remember`, `verimem_facts_recall`,
`verimem_trust_report`, `verimem_document_semantic_search`, …) to any MCP
client. Drop the `ENGRAM_TOOL_NAMESPACE` entry to keep the legacy `hippo_*`
names — both dispatch to the same tools.

## CLI

```bash
verimem index contract.pdf              # index a document for semantic search
verimem search-docs "termination clause" # passages with file + offset citations
verimem import conversations.json       # list a ChatGPT/Claude export (imports nothing
                                        # until you pass --ids or --all)
verimem import conversations.json --project verimem --since 2026-06-01 --all-matching
                                        # import a filtered subset (title/date/project)
verimem trust "the deploy is green" --verified-by ci:main:green
verimem airgap                          # verify a zero-egress CONFIGURATION
verimem airgap --live                   # PROVE it: audit every socket during a
                                        # real write+search, exit 0 iff no egress
```

## See your memory working — the trust console

The visual layer exists at every deployment size — single user, team
server, SaaS — same page, same guarantees:

```bash
verimem console        # your OWN local store: browser opens, no keys, no config
```

`GET /ui` (also served by the team gateway) shows: the **trust ring** (share
of writes admitted clean) with per-day sparklines, the **knowledge graph**
(drag, zoom; grounded edges solid, ungrounded dashed red — declared, never
hidden) where clicking a conclusion lights its **chain of custody** hop by
hop, and the **blocked-claims log** — every unsupported claim the gate
stopped, auditable. The graph is **alive**: nodes the engine touches fire and
new ones grow in as you work, straight from `/v1/events/flow`. It is an honest
window, not the whole store — it shows the most recent entities with the real
edges between them and declares the totals (`total_entities`, `total_edges`,
`isolated_count`), so a node's `isolated` badge means "no relation anywhere",
never "the sample dropped it". Live: gate events stream over SSE (`GET /v1/events`), so
you watch the memory working, not a 30s-old photograph. For the engine itself
there is the **Live Engine Room** (`GET /ui/engine`, stream
`GET /v1/events/flow`): the custody line animated by YOUR store's real events
— each write admitted or quarantined, each recall answered or abstained, with
per-tenant privacy (flow metadata only, never fact content). The events are
emitted by the core, so every surface shows up in one panel — SDK, gateway,
and the MCP server used by Claude Code **or any other vendor's agent** (label
yours with `VERIMEM_ACTOR` in its MCP config). Same feed in a terminal:
`verimem flow tail`. Personal mode binds
127.0.0.1 by default — the **loopback bind is the real defense**; a Host-header
allowlist is a *second* layer against browser DNS-rebinding, but a direct client
(e.g. `curl`) can spoof the Host header, so never expose personal mode on a
non-loopback bind. A presented API key always wins. For agents there is `GET /v1/snapshot` — the whole visible
state (odometer + daily series + quarantine + graph with provenance) in one
structured call: what the console shows a human, shaped for an AI.

## Self-host (team server)

Run Verimem as a shared memory server your team hosts — the data never
leaves your infrastructure:

```bash
verimem gateway keys create --tenant acme --name laptop   # key shown once
verimem gateway serve                                     # 127.0.0.1:8377
```

Each tenant gets an isolated store; the tenant is derived from the API key
alone. Endpoints: `POST /v1/memories`, `GET /v1/search`, `GET /v1/explain`
(TrustReport), `GET /v1/stats` (the tenant's own trust odometer + usage),
`GET /v1/quarantine`, `GET /v1/graph`, `GET /v1/graph/dossier`,
`GET /v1/snapshot`, `GET /v1/events` (SSE),
`DELETE /v1/memories/{id}?purge_history=true`. Open `/ui` in a browser for
the trust console (or `/dashboard` for the legacy minimal odometer) — static,
dependency-free pages; your API key stays in the tab and travels only as an
Authorization header. The gateway binds loopback by default — for remote
access put it behind a TLS reverse proxy (nginx/caddy).

Docker (embedding models baked in — runs fully offline):

```bash
docker compose -f docker-compose.gateway.yml up -d --build
```

TypeScript client ([sdk/typescript](./sdk/typescript)) — typed, zero-dependency,
contract-tested against the live gateway from the Python suite:

```ts
const memory = new VerimemClient({ baseUrl, apiKey });
await memory.add("deploy is green", { verifiedBy: ["ci:main:green"] });
```

Consistent hot backups (SQLite online backup API — correct while serving):

```bash
verimem gateway backup ./snap-2026-07-08   # keys + every tenant store + manifest
verimem gateway restore ./snap-2026-07-08 ./new-data-dir
```

## Benchmarks

Measured on [HaluMem](https://github.com/MemTensor/HaluMem) with the full
pipeline (our extraction → gated store → answer), judged by a Claude-based
grader. Full methodology, caveats and raw result files:
[BENCHMARKS.md](./docs/BENCHMARKS.md).

| Metric | Verimem | MemOS (self-reported) |
|---|---|---|
| End-to-end QA, same-recipe cluster (7 full runs, n=188) | **0.66–0.68** (mean 0.667, n=3 clean) | 0.672 |
| End-to-end QA, cross-user generalization (never-seen user, n=169) | **0.716** | — |
| Read-path QA (gold store, 3 users) | 0.739 / 0.750 / 0.787 | — |
| Memory-boundary abstention (end-to-end) | **1.000 — seven consecutive full runs** | — |
| Extraction F1 (58 sessions, replicated ×2) | 0.761–0.768 | 0.797 |

We describe the end-to-end result as **parity, not a win**: the same-recipe
runs cluster around MemOS's self-reported number and the judges differ
(ours vs theirs). Trust properties hold through the full pipeline. On
[TrustMem-Bench](./benchmark/trustmem_bench.py) — six deterministic trust axes
(fabrication under absence, destructive updates, temporal integrity, forget
integrity, provenance honesty, sycophancy resistance) — Verimem scores 60/60;
the bench is offline and seeded, run it yourself in one command.

Scale: recall latency stays ~flat with an **opt-in** ANN index (1.3 ms at 1M
facts vs 81 ms brute-force — see [SCALE.md](./SCALE.md) for the table + the honest
caveats: the ANN is *approximate*, ~0.84 recall-in-pool worst-case, and the 1M
build needs a large-RAM box). The default is exact brute-force.

## Why the numbers matter

Accuracy benchmarks measure how often a memory system answers correctly.
They do not measure what happens **when it cannot know** — and that failure
mode is exactly what makes memory systems risky in serious applications.
This is where Verimem is structurally different, and every row below is a
measured result with the raw file in the repo, not a design intention:

| Capability | Verimem (measured) | mem0 / Zep / MemOS |
|---|---|---|
| Abstains instead of fabricating when the store can't support an answer | **1.000 across seven consecutive full e2e runs** | not measured by their leaderboards |
| Write-path gate (unsupported "it works" claims quarantined, not stored) | grounding judge AUROC **0.96–0.97** across models/seeds (0.971 sonnet-4 R10, 0.963 sonnet-5 re-run 2026-07-16, 0.974 pooled multi-model) | no write gate |
| Conflicting well-grounded memories resolved by provenance, or an honest abstention (`answer`, trust-conditioned) | correct **0.17 → 0.92**, abstains 2/2 on unresolvable conflicts ([bench](./benchmark/wellgrounded_distractor_bench.py), sonnet-5) | served as-is |
| Trust axes under adversarial pressure ([TrustMem-Bench](./benchmark/trustmem_bench.py), deterministic, run it yourself) | **60/60** | mem0: 40/60 (forget-leak reproduced live) |
| Bi-temporal history & time travel (`as_of`, "changed from X to Y on date Z") | shipped, tested | latest-value only |
| True forget (GDPR): deleted data cannot resurface via history or time travel | shipped, probe-tested | mem0 leaked in our probe |
| Provenance on every read (who wrote it, source ref, gate status) | every hit | absent or partial |
| Runs fully air-gapped (local embeddings, injectable LLM, zero egress check) | `verimem airgap` | cloud-first |

Our method is the other differentiator: **every claim in this README links
to a raw result file, negative results are published** (see the declared
regressions and falsified hypotheses in
[BENCHMARKS.md](./docs/BENCHMARKS.md)), and the honest framing rule —
"parity, not a win" — is enforced against ourselves. A memory layer asking
for your trust should be able to show its work. This one does.

## Architecture

```
conversations / documents / tool results
        │  atomic extraction (subject-named, date-attached)
        ▼
  admission gate  ── quarantines unsupported claims (contradictions: strict mode)
        ▼
  bi-temporal store (SQLite) ── facts + provenance + supersession chains
        │
        ├─ semantic recall (local embeddings + ANN, optional reranker)
        ├─ history / as-of / transition context
        └─ TrustReport: evidence dossier or explicit abstention
```

The Python package is `engram` (the architecture name); `verimem` is the
product and distribution name. Both import paths work — and so do both env
prefixes: every `ENGRAM_X` setting can be written `VERIMEM_X` (mirrored at
import, explicit values never overridden).

## License

Dual-licensed: **AGPL-3.0** for open source use, with a **commercial license**
available for proprietary or closed-SaaS deployments — see
[LICENSING.md](./LICENSING.md). Versions 0.3.x and earlier remain MIT.

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](./CONTRIBUTING.md). Development
setup:

```bash
git clone https://github.com/aureliocpr-ctrl/verimem && cd verimem
pip install -e ".[dev]"
pytest -q
```
