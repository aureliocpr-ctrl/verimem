# Verimem at datacenter scale — Memory-as-a-Service design

Status: **design document** (2026-07-08). Nothing in here is shipped beyond
what the "Today" section says. No timeline promises; effort estimates are
engineering judgement, stated per phase.

## Why this document

Verimem's product scenarios are (A) sovereign/local air-gapped, (B) team
self-host, (C) hosted Memory-as-a-Service at datacenter scale. A and B are
served today. This document is the honest map from B to C: what the current
design already buys us, what is genuinely missing, and in which order to
build it.

## What exists today (verified, in-repo)

- **Single-node multi-tenant REST gateway** (`engram/gateway.py`, 9 tests):
  API keys (`vm_*`) hashed at rest, revocation with audit, one isolated
  SQLite store per tenant under `tenants/<id>/`, tenant derived from the key
  alone (no traversal / confused deputy), add/search/explain/delete/health.
  Conversation ingest requires an operator-wired LLM (no implicit egress).
- **Storage engine ready for many small tenants**: one SQLite file per
  tenant in WAL mode — a stress battery has run 500 concurrent processes
  with zero errors; ANN keeps recall ~flat at 1M facts (1.3 ms vs 81 ms
  brute force, reproducible via `SCALE.md`).
- **Trust core is storage-agnostic**: the anti-confabulation gate,
  reconciliation, bi-temporal history, TrustReport and abstention live above
  the storage layer and do not change shape in any phase below.
- **Air-gap self-check** (`verimem airgap`) — relevant to C because it is the
  differentiator to keep: hosted OR sovereign, same engine.

**What today is NOT**: there is no service discovery, no shard map, no
replication, no federated auth, no rate limiting, no per-tenant quotas, no
multi-node observability. Claiming "cloud-ready" today would be false.

## Architecture target (3 layers)

```
            ┌──────────────────────────────────────────┐
   L1       │  Gateway fleet (stateless, N replicas)   │
            │  authn (key→tenant) · rate limit · quota │
            │  tenant→shard lookup (shard map)         │
            └────────────────┬─────────────────────────┘
                             │
            ┌────────────────┴─────────────────────────┐
   L2       │  Control plane                           │
            │  shard map (tenant→node) · node health   │
            │  placement/rebalancing · backup schedule │
            └────────────────┬─────────────────────────┘
                             │
            ┌────────────────┴─────────────────────────┐
   L3       │  Memory nodes (stateful)                 │
            │  SQLite-per-tenant (small/medium tenants)│
            │  Postgres+pgvector (enterprise tenants)  │
            │  embedding daemon per node · WAL backups │
            └──────────────────────────────────────────┘
```

The design bet that makes this tractable: **a tenant is a file**. One SQLite
DB per tenant means placement, migration, backup and deletion are file
operations — natural horizontal sharding (the Turso/Cloudflare-D1 model),
perfect tenant isolation for privacy/compliance, and GDPR deletion = delete
the file (plus the purge semantics the engine already has).

## Phases (each independently shippable)

### Phase 1 — harden the single node (gateway v1.x)
What: per-key rate limiting and quotas, structured access logs, Prometheus
`/metrics`, backup/restore CLI for the tenants directory (SQLite online
backup API), Docker image + compose example, TLS docs.
Effort: days-to-weeks. No new distributed-systems risk.
Exit test: a small team runs it for real work behind a reverse proxy.

### Phase 2 — static multi-node (shard map as config)
What: shard map as a signed config file (tenant→node), gateway routes to N
memory nodes over HTTP (same REST contract), per-node health checks, manual
placement of new tenants, nightly per-tenant backups to object storage.
No auto-rebalancing yet — placement changes are operator actions.
Effort: weeks. First real distributed step, kept boring on purpose.
Exit test: two nodes, tenants split between them, one node restart does not
affect the other node's tenants.

### Phase 3 — control plane (dynamic placement)
What: the shard map becomes a small service (SQLite/Postgres backed, itself
replicated), automatic placement of new tenants by load, tenant migration
(file copy + WAL catch-up + cutover), node drain for maintenance,
alerting on replication/backup lag.
Effort: months. This is where distributed-systems care concentrates.
Exit test: kill a node in a 3-node cluster; its tenants come back from
backup/replica on the survivors with a measured, documented RPO/RTO.

### Phase 4 — enterprise tier + federation
What: Postgres+pgvector backend for tenants that outgrow one file (the
storage interface already isolates this), SSO/OIDC federated auth on the
gateway, per-tenant encryption keys at rest, audit export, optional
customer-held keys ("sovereign cell" inside the hosted service).
Effort: months, largely parallel to Phase 3.

## What we deliberately do NOT build

- A custom distributed database: we compose SQLite files + object-storage
  backups + (later) Postgres. Boring beats novel here.
- Cross-tenant anything (search, analytics, "insights"): isolation IS the
  product. Any aggregate feature would need explicit opt-in design work and
  is out of scope for this document.
- Kubernetes-first packaging before Phase 2 exists: a systemd unit and a
  Docker image serve phases 1-2 honestly.

## Open questions (tracked, not hidden)

1. Embedding compute at scale: per-node daemon (today's model) vs a shared
   embedding service — cost/latency measurement needed at Phase 2.
2. Hot-tenant problem: one very large tenant on SQLite → when to promote to
   the Postgres tier, and is the migration transparent?
3. Multi-region: file-per-tenant makes geo-pinning easy (compliance win) but
   cross-region failover needs the Phase 3 control plane first.
4. Pricing/metering hooks: usage counters per key exist implicitly (logs);
   real metering needs first-class counters — Phase 1 candidate.

## Honest bottom line

Today Verimem is **single-node self-host ready** (scenario B) with a design
whose unit of state — the tenant file — is the right shape for datacenter
scale. The distance from B to C is well-understood engineering (phases
above), not research. The trust core (the actual moat) is untouched by every
phase: it is the reason to build C at all.
