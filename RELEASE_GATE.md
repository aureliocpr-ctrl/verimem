# Release Gate — public single-package readiness

> Owner mandate (2026-07-04): public release requires (a) verified-working
> ("certezza matematica" → translated into the falsifiable criteria below) and
> (b) a single installable package. **No criterion passes without evidence**
> (command + output committed or linked). Declaring "ready" with any row open
> is forbidden (A2/A4).

| # | Criterion | Evidence required | Status |
|---|-----------|-------------------|--------|
| G1 | **Full test suite green** on a clean run | pytest output, count, date | ⏳ 2026-07-04 full run: **5937 passed**, 5 failed → 3 were REAL regressions from the 2026-07-02 interactive-judge work (bare subprocess callsites + tests patching the pre-_ex API), all FIXED same day; 2 remaining are the known environmental pair (provider smoke without API key by policy; SLO test flaky under load — it ran while claude -p benches saturated the box). Final clean re-run at gate close |
| G2 | **Install-from-scratch**: virgin venv → wheel install → `import engram` → SDK smoke (add/search/recall) → `engram` CLI entrypoint → MCP server starts | transcript in `docs/release/G2_install.md` | ✅ 2026-07-04 — PASS, and it caught a real bug: `engram mcp` logged on stdout breaking JSON-RPC purity (fixed, `tests/test_mcp_stdout_purity_g2.py`) |
| G3 | **Crash durability**: crash-injection test over the write paths | `tests/test_crash_injection_g3.py` (3 tests: kill mid-burst = zero committed loss + integrity ok, reopen+write, journal replay after kill; anti-vacuity guard). Residual: OS-crash/power-loss window under default NORMAL is BY DESIGN, closed by `ENGRAM_SQLITE_SYNCHRONOUS=FULL` — declared, not testable in userspace | ✅ 2026-07-04 (knob + replay-checkpoint pre-existed from the data-loss hunt) |
| G4 | **Benchmarks reproducible by one command** (seeded): every README number regenerable | `benchmark/repro_all.py` + doc | ⏳ 2026-07-04 entrypoint shipped: registry claim→command→artifact, `--verify` 6/6 backed, guarded by `tests/test_repro_registry_g4.py` (artifact drift breaks the suite). Remaining: seed audit per command + registry coverage of remaining README numbers |
| G5 | **Property-based invariants** on core paths via hypothesis | `tests/test_property_invariants_g5.py` + `tests/test_property_gate_admission_g5.py` | ✅ 3/3 2026-07-04 — tier totality/prefix-stability; supersession no-delete/no-cycle (hypothesis found the A→B→A cycle bug, fixed); gate-admission monotone in score + decision flips exactly at the PER-JUDGE resolved threshold + env override wins (locks the 2026-07-02 critic finding about scale-mismatched cuts) |
| G6 | **README claim audit**: zero unverified claims, every number sourced to a results file | audit note in PR | ⏳ policy already; final pass at gate close |
| G7 | **Name / PyPI identity** + LICENSE/attribution check of bundled models (e5, NLI, distilled CE weights) | pyproject rename + license notes | ⏳ NAME DECIDED 2026-07-04: **Verimem** (verimem.com purchased by owner; PyPI/npm/.ai/.dev verified free, zero web collisions). pyproject renamed (dist `verimem`, module stays `engram`), wheel builds `verimem-0.3.0`. Remaining: owner reserves PyPI name (placeholder upload), formal EUIPO/USPTO search, model-license audit, GitHub repo rename (owner's call) |
| G8 | **Fresh-environment model download**: first-run UX when HF cache is empty | CI `wheel-install` job (runner cache is empty → e5 first-run download exercised on every push, both OSes) | ⏳ wired 2026-07-04. BLOCKER (owner): GitHub Actions has NOT run since 2026-07-03 — every push is startup_failure (0 steps, no annotations) on ALL matrix legs, pre-dating my commits and the repo rename. Actions is enabled; cause is almost certainly exhausted Actions minutes on the private repo (billing API needs a scope this token lacks). Resolves itself when the repo goes public (free unlimited Actions) — or owner tops up minutes |
| G9 | **Cross-platform CI**: suite matrix existed; G2-from-wheel added (`wheel-install` job: virgin venv, SDK gate smoke, MCP stdout-purity handshake, win+ubuntu) | `.github/workflows/ci.yml` + green run | ⏳ wired 2026-07-04 — closes on first green run |

| G10 | **Multilingual validation** (the product claims memory for AI agents, not for English agents): smoke zh/ru/fi in CI; L1 unsupported-claim patterns beyond EN; NLI/CE multilingual options (mDeBERTa-xnli, mmarco-mMiniLM) benchmarked before swap; re-run en→fi cross-lingual search on an idle machine | smoke script + model A/Bs | ⏳ opened 2026-07-04 — measured: retrieval IS multilingual (zh→zh 0.909, it→zh 0.843, multilingual-e5); span-selection regex fixed (was [a-z0-9]+ = blind prefix on non-Latin, `tests/test_span_multilingual_g10.py`); L1 screen is EN-only (RU unsupported claim passed); NLI=DeBERTa-v3(EN), CE=ms-marco(EN) degrade silently |

## Adversarial review findings (2026-07-04, 3 Opus agents read-only)

**Critic (write-path moat):** S1 the entailment gate was unreachable from
`add()` — FIXED (`ground=True`/`gate_mode` per-call, honest claim). S2
reject-mode unreachable — FIXED. S3 supersede cycle-check hop-cap escape
(70-ring) — FIXED. **Open:** S4 local-uncalibrated score vs claude-scale cut
(warn, not prevent) — needs the shipped CE score distribution to size impact;
S5 interactive-judge trusts the sister's scale with no cross-check.

**Security/privacy sweep:** C1 personal-corpus dumps + H1 real email in
tracked files — FIXED (git rm --cached + scrub; **history purge still owed
before first public push**). **Open, security:** H2 `sandbox_exec` behind
`HIPPO_ENABLE_SHELL` — FIXED (disabled by default, opt-in like run_task,
`tests/test_sandbox_exec_shell_gate_h2.py`);
H3 strict-mode pytest-arg escape — FIXED (`-p`/`--pyargs`/`--import-mode`/`-c`/`-o` blocked, `tests/test_sandbox_strict_pytest_args_h3.py`; the `git config` write vector it named was already closed 2026-06-05); M3 IDE symlink TOCTOU +
uncapped subprocess stdout. CLEAN (verified): no tracked secrets, SSRF guard
solid, dashboard loopback-only + token, workflows least-privilege OIDC, MIT
license + runtime-downloaded models (no redistribution obligation).

**DX review:** README numbers reconciled (tests badge, 231 MCP tools), 2
broken audit links fixed, `hippoagent/static` path fixed, plugin.json +
workflows renamed hippoagent→verimem (was release-blocking). **Open:** README
is ~1156 lines with duplicated install/demo sections — a ~40% cut + move the
cycle-log history to CHANGELOG is the highest-leverage launch task; a few
Italian lines + a HippoAgent code sample remain.

## Non-goals of this gate (declared)
- ANN wiring >100k and cold-tiering: performance roadmap, not release blockers
  (single-node honesty is already documented in STATE/README).
- Third-party leaderboard placement: the 3-slice HaluMem + LME-S table ships
  with the release as *self-run, reproducible, asterisked* numbers.

## Order of execution
1. G2 (in progress) → G8 right after (same harness, empty HF_HOME).
2. G3 (the only real known reliability hole) — TDD.
3. G5 → G4 → G1 full rerun → G6 → G9.
4. G7 whenever the owner picks the name (independent of 1-3).
