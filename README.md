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

- **Gated writes** — every fact enters as a low-trust claim and must be backed
  by evidence to gain status. Unsupported or contradictory assertions are
  flagged instead of absorbed (anti-sycophancy on the write path).
- **Provenance on every read** — answers cite where each fact came from
  (conversation, document offset, tool call). A `TrustReport` explains *how the
  system knows*: chain of custody, declared conflicts, or an explicit abstention.
- **Bi-temporal history** — facts carry both *when it happened* and *when we
  learned it*. Query the past (`as_of`), see transitions ("changed from X to Y
  on date Z"), and audit every revision.
- **Abstention by design** — on questions the store cannot support, Verimem
  says so. Memory-boundary abstention holds at 1.0 across our end-to-end runs.
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
verimem airgap                          # verify a zero-egress configuration
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
stopped, auditable. Live: gate events stream over SSE (`GET /v1/events`), so
you watch the memory working, not a 30s-old photograph. Personal mode binds
127.0.0.1 only (Host-header checked against DNS rebinding); a presented API
key always wins. For agents there is `GET /v1/snapshot` — the whole visible
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

Scale: recall latency stays ~flat with an ANN index (1.3 ms at 1M facts vs
81 ms brute-force — reproducible, see [SCALE.md](./SCALE.md)).

## Why the numbers matter

Accuracy benchmarks measure how often a memory system answers correctly.
They do not measure what happens **when it cannot know** — and that failure
mode is exactly what makes memory systems risky in serious applications.
This is where Verimem is structurally different, and every row below is a
measured result with the raw file in the repo, not a design intention:

| Capability | Verimem (measured) | mem0 / Zep / MemOS |
|---|---|---|
| Abstains instead of fabricating when the store can't support an answer | **1.000 across seven consecutive full e2e runs** | not measured by their leaderboards |
| Write-path gate (unsupported "it works" claims quarantined, not stored) | grounding judge AUROC **0.971** | no write gate |
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
  admission gate  ── rejects unsupported & contradictory claims
        ▼
  bi-temporal store (SQLite) ── facts + provenance + supersession chains
        │
        ├─ semantic recall (local embeddings + ANN, optional reranker)
        ├─ history / as-of / transition context
        └─ TrustReport: evidence dossier or explicit abstention
```

The Python package is `engram` (the architecture name); `verimem` is the
product and distribution name. Both import paths work.

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
