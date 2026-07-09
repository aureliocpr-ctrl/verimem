# Verimem Design Partner Program

*One pilot team. Full engineering attention. Honest numbers.*

## What Verimem is

A trust-first memory engine for AI agents and assistants: every write passes
an anti-confabulation gate, every read carries provenance, and when the
evidence isn't there the system **abstains instead of guessing** — measured
at **1.000 across seven consecutive end-to-end benchmark runs**, not claimed.
Self-hosted: your data never leaves your infrastructure.

## Why we're looking for a design partner

The engine is real and measured (see [Why the numbers matter](../README.md#why-the-numbers-matter)
— every claim links to a raw result file, negative results included). What
we don't have yet is *your* workload. Instead of guessing which enterprise
features matter, we build them in the order a real team needs them.

## What you get

- **Free commercial license** for the pilot period, on your infrastructure
  (self-host gateway: API keys, per-tenant isolation, hot backups — shipped).
- **Direct line to the engineering team.** Your gaps become our sprint:
  SSO/OIDC, RBAC, audit export, deployment hardening — built when *you* need
  them, not from a speculative checklist.
- **A memory layer your compliance team can actually approve**: abstention
  by design, provenance on every answer, bi-temporal audit trail
  ("what did we know on date X"), GDPR-grade deletion that survives
  time-travel queries, optional fully air-gapped operation
  (`verimem airgap` verifies zero egress).

## What we ask

- A real use case with real (or realistic) data, used weekly.
- A 30-minute feedback call every two weeks.
- At the end: an honest case study we can publish (anonymized if you prefer),
  including what did NOT work — that's our brand.

## Who fits (pick your vertical)

| Vertical | What Verimem does there |
|---|---|
| **Dev teams / AI agents** | shared memory with provenance on commits, self-hosted, agent-framework friendly (MCP today; LangGraph/CrewAI integration on the pilot roadmap) |
| **Legal** | exact page-level citations from documents, state-as-of-a-date (`as_of`), full audit trail |
| **Research** | document ingestion with verifiable quotes, abstention on unsupported claims |
| **Healthcare-adjacent** | never-invent behavior (measured), air-gapped deployment |
| **Finance / compliance** | bi-temporal record ("known when"), GDPR deletion, declared conflicts |

## The numbers we'll show you (and their caveats)

End-to-end QA accuracy is at **statistical parity with the best
self-reported competitor** (0.66–0.68 cluster over 7 runs vs MemOS 0.672;
different judges — declared). On a never-before-used test user: **0.716**.
Where no competitor has published numbers at all: abstention 1.000,
TrustMem-Bench 60/60 (vs mem0 40/60, forget-leak reproduced live),
write-gate AUROC 0.971. Full methodology: [BENCHMARKS.md](./BENCHMARKS.md).
We will run the same benchmarks on *your* domain during the pilot and
publish what we find — including regressions.

## Pilot shape (4–6 weeks)

1. **Week 1** — setup on your infra (Docker or bare CLI), import your data
   (consent-first), pick the vertical preset.
2. **Weeks 2–4** — your team uses it; we ship your top-3 gaps.
3. **Weeks 5–6** — measure on your workload, write the case study together,
   decide on a commercial license (no obligation).

## Contact

Aurelio Capriello — [verimem.com](https://verimem.com) ·
[open an issue or discussion on GitHub](https://github.com/aureliocpr-ctrl/verimem)
