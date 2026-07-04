# Cycle 159.7 — Scaling Experiment (2026-05-19)

Empirical test of the core hypothesis behind the cycle-159 work:
**do two communicating Claude instances scale to a higher level of
output quality than a single instance on the same task?**

## Setup (N=1)

- **Target**: find real bugs in `engram/llm.py` (1432 LoC, multi-provider
  wrapper: anthropic / openai / ollama / claude-cli / MCP sampling /
  mock + fallback chain).
- **Arm A**: 1 sonnet single-instance, 6 min wall-clock.
  Same anti-confab prompt: cite file:line + verbatim snippet + expected
  vs actual.
- **Arm B**: 2 sonnet team (eve = primary, frank = critic-verifier) via
  the cycle-159 Real-Collaboration Charter, ~5 min wall-clock.
  Same task, same anti-confab contract, plus the `[VERIFIED]` /
  `[CLAIM]` / `[REJECT]` tag protocol and a strict-majority convergence
  gate.

## Hypothesis (falsifiable)

> Team-B finds ≥1 real bug that Arm-A misses, **without** inflating
> the false-positive rate.

## Result — confirmed for N=1

| Bug                                                  | Arm A   | Arm B (after peer-verify) | Verified (lead) |
|------------------------------------------------------|---------|---------------------------|-----------------|
| `ClaudeCLILLM` system msg ordering (line 159-168)    | ✅ found | ✅ found                   | **REAL HIGH**   |
| Retry backoff `**attempt` (line 452)                  | ✅ found | ❌ rejected ("exp standard") | smell debatable |
| `_is_recoverable` string-scan (line 1299-1306)       | ✅ found | not raised                 | smell debatable |
| **`MCPSamplingLLM` `in_tokens` omits `system`** (357-358) | ❌ **MISSED** | ✅ **found**             | **REAL MEDIUM** |
| `FallbackLLM` tool error "all failed" misleading      | missed | raised → self-reject       | LOW quality     |
| `MockLLM` operator precedence (line 862)              | missed | raised → self-reject       | trivial         |

**Net score (strict — bugs surviving independent peer-verification)**:

- Arm A: **1** real bug + 2 smells included as bugs.
- Arm B: **2** real bugs + **3 self-rejections** of false positives
  (one of which Arm A had included as a bug).

The scaling shows up in three dimensions:

1. **Recall**: Arm-B catches `MCPSamplingLLM in_tokens` undercount that
   Arm-A read straight past.
2. **Precision**: Arm-B's peer-verify loop rejects three candidates
   (retry backoff, FallbackLLM diagnostic message, MockLLM precedence)
   that the lone reader had no mechanism to refute.
3. **Self-correction**: frank's own initial reading flagged BUG-F2 and
   BUG-F4 — he then reclassified both as NOT bugs during his second
   pass, before eve's list even arrived. The Charter's "verify before
   claiming" framing nudged self-skeptic behavior we don't see in the
   single-instance arm.

## What got committed back to the repo

The two real bugs the team converged on were fixed in this commit:

- `engram/llm.py:159-178` — `ClaudeCLILLM.complete` now uses
  `system_parts` + `turn_parts` lists instead of `parts.insert(0, ...)`,
  preserving the primary `system` arg at index 0 and the role-`system`
  message order from the input list.
- `engram/llm.py:357-365` — `MCPSamplingLLM._async_complete` now
  computes `in_chars = len(system or "") + sum(...)` so the
  `llm_call` emit and METRICS gauge reflect the full input the model
  was billed for.

Two RED-first tests in `tests/test_llm_cycle159_bugs.py` pin both
behaviours:
- `test_claude_cli_prompt_keeps_system_param_in_front_with_extra_system_msgs`
  (subprocess.run monkeypatched, asserts index ordering in the
  assembled prompt).
- `test_mcp_sampling_in_tokens_includes_system_chars` (verifies the
  formula by source inspection — async path is not exercised because
  it needs a real MCP session).

## Caveats — honest

- **N=1**. One file, one pairing, one task type (bug hunting). The
  result is **evidence**, not proof. Repeat needed with N≥5 pairings
  across different task families (refactor, design review, test
  authoring) before declaring scaling generally.
- **Single pairing**. eve and frank were both fresh-context sonnet
  with the same Charter. Different model mixes (sonnet+haiku,
  sonnet+opus) might shift the trade-off.
- **Wall-clock parity**: Arm A had 6 min, Arm B used ~5 min between
  both members. Tokens-per-bug remains favourable to A — collaboration
  isn't free.
- **The Charter still needs `verify-before-claim` enforcement**. eve's
  Bug 1 (retry backoff) would have been auto-rejected if a `[VERIFIED]
  linecount=N` fingerprint were *mandatory* before a `[CLAIM]`. frank
  did the empirical re-check by character, not by protocol. Cycle 160
  candidate.

## Follow-ups

- Repeat the experiment on `engram/consolidation.py` (post-cycle-154
  refactor + cycle-155 lock) — a more concurrent file where the
  scaling signal might be larger.
- Try Arm-C = 1 opus single instance to bracket the upper bound: is
  2-sonnet-team ≥ 1-opus on the same task? (Cost-sensitive — 1 call
  budget.)
- Charter v2 with mandatory `[VERIFIED]` fingerprints (cycle 159.6
  task already tracked).

Fact memoria: `591a8ea5f8ce` (full experimental log with file:line
verifications and per-agent timings).
