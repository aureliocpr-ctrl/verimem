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
- **Document memory with exact citations** — index PDF/DOCX/HTML/text files;
  semantic search returns passages with file, version and character offsets;
  passages can be promoted to memory *through the gate*, citation attached.
- **Consent-first import** — bootstrap from your ChatGPT / Claude export:
  conversations are listed first, nothing is ingested without an explicit
  selection.
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
verimem trust "the deploy is green" --verified-by ci:main:green
verimem airgap                          # verify a zero-egress configuration
```

## Self-host (team server)

Run Verimem as a shared memory server your team hosts — the data never
leaves your infrastructure:

```bash
verimem gateway keys create --tenant acme --name laptop   # key shown once
verimem gateway serve                                     # 127.0.0.1:8377
```

Each tenant gets an isolated store; the tenant is derived from the API key
alone. Endpoints: `POST /v1/memories`, `GET /v1/search`, `GET /v1/explain`
(TrustReport), `DELETE /v1/memories/{id}?purge_history=true`. The gateway
binds loopback by default — for remote access put it behind a TLS reverse
proxy (nginx/caddy).

## Benchmarks

Measured on [HaluMem](https://github.com/MemTensor/HaluMem) with the full
pipeline (our extraction → gated store → answer), judged by a Claude-based
grader. Full methodology, caveats and raw result files:
[BENCHMARKS.md](./docs/BENCHMARKS.md).

| Metric | Verimem | MemOS (self-reported) |
|---|---|---|
| End-to-end QA, mean of 2 independent runs (n=188) | **0.6675** (0.6755 / 0.6596) | 0.672 |
| Read-path QA (gold store, 3 users) | 0.739 / 0.750 / 0.787 | — |
| Memory-boundary abstention (end-to-end) | **1.000** (both runs) | — |
| Extraction F1 (58 sessions, replicated ×2) | 0.761–0.768 | 0.797 |

We describe the end-to-end result as **parity, not a win**: one run scored
above MemOS's self-reported number, one just below, and the judges differ
(ours vs theirs). Trust properties hold through the full pipeline. On
[TrustMem-Bench](./benchmark/trustmem_bench.py) — six deterministic trust axes
(fabrication under absence, destructive updates, temporal integrity, forget
integrity, provenance honesty, sycophancy resistance) — Verimem scores 60/60;
the bench is offline and seeded, run it yourself in one command.

Scale: recall latency stays ~flat with an ANN index (1.3 ms at 1M facts vs
81 ms brute-force — reproducible, see [SCALE.md](./SCALE.md)).

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
