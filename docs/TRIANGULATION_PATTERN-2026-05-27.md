# Cross-LLM Triangulation Pattern — Replicable Method

**Origin**: cycle 2026-05-27, 10 L1.x anti-confab detectors shipped via Claude+Gemini+GPT triangulation in ~31 min effective work.

**Empirical**: 240 nuovi pytest PASS + 350 regression PASS at session close.

---

## The Pattern (4 steps)

### Step 1 — Claude initial design (5-10 min)

1. Identify gap from real incident (es. M12 PTY hallucination → L1.9 perf)
2. Brainstorm 3-5 keyword patterns covering claim semantic space
3. Define `verified_by` evidence prefix accepted list
4. Write detector module `engram/l1_<name>_detector.py` with:
   - Compiled regex patterns
   - `_has_*_evidence(verified_by)` helper
   - `detect_unsupported_*_claim(*, proposition, verified_by) → Warning | None`
   - `@dataclass(frozen=True) *ClaimWarning(matched_text, advice)`

### Step 2 — Gemini cross-check (1 min response)

Call `mcp__engram-bridge__ask_gemini` with prompt:

```
Cross-check L1.X anti-confab detector Python. Patterns: [...]
Evidence accepted: [...]
Tu vedi pattern FP/FN critici mancanti? Brevità 4-5 righe.
```

Gemini identifies FP (false positives) + FN (false negatives) in ~60s.

### Step 3 — GPT cross-check (1.5 min response)

Via `mcp__Claude_in_Chrome__*` on Aurelio Plus account:

1. `tabs_context_mcp` per get tab GPT
2. `find` per textbox + send button refs
3. `browser_batch` with `[click textbox, type prompt, key Return, wait 20s, screenshot]`
4. Read screenshot for GPT response

GPT often proposes richer patterns + lookahead/negative-lookahead than Gemini.

### Step 4 — Patch v3 + pytest formale (10-15 min)

1. Implement patterns suggested by Gemini + GPT
2. Add FP guards (Gemini-identified)
3. Add FN coverage (GPT-identified)
4. Write `tests/test_l1_<name>_detector.py`:
   - `TestPositiveCases` parametrized (8-15 cases)
   - `TestNegativeCases` parametrized (FP guards)
   - `TestEvidenceSuppression` parametrized (evidence prefix cases)
   - `TestEdgeCases` (empty proposition, None evidence)
   - `TestGateWire` (run_validation_gate integration)
5. Wire in `engram/anti_confab_gate.py` `_l1_warnings()`
6. Run pytest → expected 100% PASS

---

## Convergence vs Divergence Handling

### Convergence 2/2 (Gemini + GPT vote same)

→ **Ship with high confidence**. Implement merged pattern (Gemini base + GPT richness).

Empirical 2026-05-27: 3/10 round (L1.10 works, L1.11 prod-ready, L1.12 security).

### Divergence (Gemini ≠ GPT)

→ **Claude architectural choice**:
1. Evaluate orthogonality to existing detectors (avoid overlap)
2. Pick option matching most distinct semantic space
3. Document rationale in detector docstring + fact lineage
4. Lower confidence flag in master fact

Empirical 2026-05-27: 7/10 round Claude architectural (L1.13 completion, L1.14 doc, L1.15 tested, L1.16 approval, L1.17 monitored, L1.18 automated, +L1.9 initial design).

---

## Cost per detector

| Phase | Time | Tool calls |
|---|---|---|
| Claude design | 5 min | 1 (Write detector.py) |
| Gemini ask | 1 min | 1 (`ask_gemini`) |
| GPT ask | 1.5 min | 1 (`browser_batch` Chrome) |
| Patch v2/v3 | 5 min | 1-2 (Edit) |
| Pytest write | 5 min | 1 (Write test.py) |
| Pytest run + verify | 1 min | 1 (Bash pytest) |
| Wire in gate | 2 min | 2 (Edit anti_confab_gate.py) |
| Fact save | 1 min | 1 (`hippo_remember`) |
| **Total** | **~20 min** | **~8-10 calls** |

Compounding: in cycle 2026-05-27 averaged ~3 min/detector (highly optimized after first 2 rounds).

---

## Evidence prefix conventions (10 detector standard)

| Domain | Standard prefixes |
|---|---|
| Performance | `bench:` `measure:` `perf:` `timing:` `latency:` |
| Runtime works | `pytest:_PASS` `bash:exit0` `smoke:` `runtime:` |
| Production | `coverage:` `soak:` `regression:_PASS` `ci:green` `release_tag:` |
| Security | `audit:` `pentest:_PASS` `threat_model:` `bandit:_PASS` `semgrep:_PASS` |
| Completion | `task:_closed` `acceptance_test:_PASS` `dod:` `pr:_merged` |
| Documentation | `docs:` `md:` `file:_md` `readme:` `changelog:` |
| Testing | `pytest:_PASS` `test_coverage:` `ci:green` `qa:_PASS` |
| Approval | `approval:_signed` `review:_approved` `pr:_approved` |
| Monitoring | `dashboard:` `grafana:` `alert:` `prometheus:` `metric:` |
| Automation | `cron:` `schedule:` `workflow:` `systemd:` `airflow:` |

---

## Failure modes catched (empirical 2026-05-27)

| Pattern | Catched by | Example |
|---|---|---|
| Performance hyperbole | L1.9 | "12s→1s game changer" without bench |
| Implicit runtime confidence | L1.10 | "funziona" without pytest |
| Marketing maturity | L1.11 | "production-ready" without coverage |
| Security claim | L1.12 | "secure" without audit |
| Done declaration | L1.13 | "task done" without closing criteria |
| Documentation assertion | L1.14 | "well-documented" without md file |
| Testing process | L1.15 | "tested" without pytest_PASS |
| Business approval | L1.16 | "approved" without approver |
| Observability claim | L1.17 | "monitored 24/7" without dashboard |
| Automation claim | L1.18 | "automated nightly" without cron |

---

## Replicable for future cycles

Apply same 4-step pattern for new detector. Estimated cost ~20 min per detector (optimized) including triangulation. Aim for convergence 2/2 cross-LLM; if divergence, use orthogonality criterion for Claude architectural choice.

**Pattern signature**:
1. Real incident → gap diagnosis
2. Claude design v1
3. Gemini cross-check (FP/FN identification)
4. GPT cross-check (additional FP/FN + richer patterns)
5. Patch v2/v3 merged
6. Pytest formale parametrized (15-40 cases)
7. Wire in gate orchestrator
8. Save fact lineage with `lineage_parent:` to incident origin
