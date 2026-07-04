# Cycle 134 — HippoAgent Live Dashboard

**Date**: 2026-05-17
**Status**: design approved by Aurelio (CEO)
**Branch**: `cycle134-live-dashboard`
**Goal**: scale HippoAgent with a wow-effect feature that is *really*
integrated in the package, not a side-script.

## Constraints (Aurelio direttiva)

- Wow visual effect
- Real integration (NOT side-script)
- Live sub-second push when MCP tools write to memory
- Total coverage: episodes + traces + skills + lineage + facts + causal +
  bundles + audit
- Real E2E tests

## Decisions (trade-offs argued)

### 1. Server: stdlib `http.server` (NOT FastAPI)

- HippoAgent constraint: no extra API deps
- FastAPI = 30+ deps, breaks `pip install hippoagent` clean path
- `http.server` + `socketserver.ThreadingMixIn` is enough for SSE on
  localhost
- Trade: −1 DX, +100 zero-deps + adoption

### 2. Protocol: SSE (Server-Sent Events)

- NOT WebSocket: bi-directional overkill
- NOT polling: 1-5s latency, defeats "sub-second" requirement
- SSE = `text/event-stream` server→browser, sub-second push, automatic
  browser reconnect, 0 deps
- Proven pattern (Grafana, ChatGPT streaming)

### 3. EventBus: in-process auto-start (NOT mtime polling)

- `engram/bus.py` already exists (cycle 119 wire: `BUS.emit("coherence_warning",...)`)
- MCP server spawns a thread HTTP+SSE that subscribes to `BUS` and pushes
  events to browser
- Trade: out-of-process mtime polling SQLite = 1-2s lag + extra I/O
- In-process = 0ms lag, event captured BEFORE DB write

## Coverage — 8 event categories

1. `episode.created` (hippo_record_episode/batch)
2. `fact.stored` (hippo_remember + L1/L1.5/L1.7 warnings)
3. `skill.adopted` (dream_adopt + promote)
4. `lineage.edge` (episode↔fact bidirectional)
5. `causal.chain` (causal_extract + skill_mine)
6. `bundle.compose` (compose_macro)
7. `audit.tool_call` (every MCP call with `latency_ms` cycle 115.A)
8. `anti_confab.warning` (L1/L1.5/L1.7 detector hits + L2 orphan delta)

## UI minimal wow

- single HTML page, 8 columns live scroll (event feed)
- mini Sigma.js graph for realtime lineage
- animated counters `facts/skills/episodes`
- latency histogram p50/p95/p99 (cycle 115.A telemetry)
- single file `engram/dashboard/static/index.html`, embedded in package

## E2E tests (REAL — not mocked)

- `tests/test_dashboard_sse_e2e.py`: `requests` streaming + assert
  `event: fact.stored\ndata: {...}` received < 200 ms after `hippo_remember`
- `tests/test_dashboard_bus_coverage.py`: emit all 8 categories + verify
  payload schema
- `tests/test_dashboard_static_serve.py`: GET `/` returns HTML + assets,
  no path traversal

## Scope (1 atomic PR)

- `engram/dashboard/__init__.py` (~200 LOC server SSE + static)
- `engram/dashboard/static/index.html` (~300 LOC vanilla JS + Sigma.js CDN)
- Wire in `engram/mcp_server.py`: opt-in env `HIPPO_DASHBOARD_PORT=8765`
  for autostart
- 3 E2E test files (real, not mocked)
- README badge `:: HippoAgent Dashboard live @ localhost:8765`

## Quality gate

- TDD strict RED→GREEN
- `critic-orchestrator start_adversarial_review` before merge
- All CI green (linux + macos + windows × py3.10-3.13)
- Anti-confabulation self-check every N steps

## Anti-pattern guard (cycle 134 specific)

- NO marketing labels in UI ("ROCKS!", "AWESOME!")
- NO emoji noise
- NO fake metrics
- Real numbers, real timestamps, real lineage paths
