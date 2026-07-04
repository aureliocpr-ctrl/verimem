# Engram — Documentation Archive

This directory contains **frozen-at-date snapshots** of audits, R&D diaries,
recap documents, and roadmaps that have been superseded by the rolling
[`STATE.md`](../../STATE.md) at the repo root.

These documents are preserved for transparency and historical reference.
**They do NOT reflect the current state of the project** — see
[`STATE.md`](../../STATE.md) for that.

## Why archive?

Through cycles #1-#40, the project accumulated 15+ top-level Markdown
files: audits (architecture, code quality, security, QA), R&D diaries
(performance, memory, UX, trace alignment, exploration), one-off recaps
(`STATE_OF_HIPPOAGENT_2026-05-13`, `RECAP_ENGRAM_2026-05-13`,
`FINAL_REVIEW`), and a 220 KB cycle-by-cycle log (`FORGIA.md`).

Each was honest and useful when written, but together they created
visitor disorientation: which one is current? Which is stale? What do I
read first? The answer used to require reading file mtimes.

The consolidation (cycle "D", 2026-05-13) introduces:
- `STATE.md` at repo root — single source of truth, kept current.
- `docs/archive/<date>_<NAME>.md` — historical snapshots.

## Contents (2026-05-13 snapshot)

| Document | Lines | Topic |
|---|---:|---|
| [`2026-05-13_ARCHITECTURE_AUDIT.md`](./2026-05-13_ARCHITECTURE_AUDIT.md) | 589 | high-level architecture review |
| [`2026-05-13_BENCH_VALIDATION.md`](./2026-05-13_BENCH_VALIDATION.md) | 231 | benchmark methodology + results |
| [`2026-05-13_CODE_QUALITY_AUDIT.md`](./2026-05-13_CODE_QUALITY_AUDIT.md) | 156 | LOC, complexity, style |
| [`2026-05-13_FINAL_REVIEW.md`](./2026-05-13_FINAL_REVIEW.md) | 715 | omnibus end-of-phase review |
| [`2026-05-13_FORGIA.md`](./2026-05-13_FORGIA.md) | 4839 | cycle-by-cycle development log (FORGIA = "forge" pieces) |
| [`2026-05-13_PRODUCTION_ROADMAP.md`](./2026-05-13_PRODUCTION_ROADMAP.md) | 228 | pre-v0.2.0 production hardening plan |
| [`2026-05-13_QA_AUDIT.md`](./2026-05-13_QA_AUDIT.md) | 316 | test coverage, flakiness, gaps |
| [`2026-05-13_RECAP_ENGRAM.md`](./2026-05-13_RECAP_ENGRAM.md) | 81 | post-rebrand recap (now folded into STATE.md) |
| [`2026-05-13_RND_EXPLORATION.md`](./2026-05-13_RND_EXPLORATION.md) | 293 | exploratory R&D diary |
| [`2026-05-13_RND_MEMORIE.md`](./2026-05-13_RND_MEMORIE.md) | 74 | working memory pruning research |
| [`2026-05-13_RND_PERFORMANCE.md`](./2026-05-13_RND_PERFORMANCE.md) | 283 | perf hot-path R&D (16x to 4700x speedups) |
| [`2026-05-13_RND_TRACE_ALIGNMENT.md`](./2026-05-13_RND_TRACE_ALIGNMENT.md) | 124 | Needleman-Wunsch trace divergence |
| [`2026-05-13_RND_UX.md`](./2026-05-13_RND_UX.md) | 281 | UX research + design system |
| [`2026-05-13_SECURITY_AUDIT.md`](./2026-05-13_SECURITY_AUDIT.md) | 495 | 13 CVE closed, threat model |
| [`2026-05-13_STATE_OF_HIPPOAGENT.md`](./2026-05-13_STATE_OF_HIPPOAGENT.md) | 398 | pre-rebrand state snapshot |

## Archive policy

- **Add a new entry** at the end of each macro-cycle (5-10 cycles) if a
  fresh audit or R&D doc is worth preserving. Always prefix with `YYYY-MM-DD_`.
- **Do not edit** existing archive files — they are frozen by design. If
  the content is wrong, update [`STATE.md`](../../STATE.md) instead.
- **`STATE.md` is the only living doc** at the repo root that summarizes
  current state. CHANGELOG.md is the version log.
