# Contributing to HippoAgent

Thanks for considering contributing — this is a research-grade prototype, so
we're especially happy with experiment reports, new providers, sleep-cycle
variants, benchmark tasks, and visualization improvements.

## Quick start

```bash
git clone https://github.com/<you>/hippoagent.git
cd hippoagent
python -m venv .venv && source .venv/Scripts/activate   # or .venv/bin/activate
pip install -e ".[dev]"
HIPPO_OFFLINE=1 pytest        # 23+ tests, no network needed
```

## Project layout

| where | what |
|---|---|
| `hippoagent/` | core library — memory, skills, sleep, wake, tools, cli, dashboard |
| `benchmark/` | task suite + evaluator + statistical helpers |
| `tests/` | pytest, all runnable offline with `HIPPO_OFFLINE=1` |
| `scripts/` | platform launchers (Windows .bat/.ps1) |

## Conventions

- **Python ≥ 3.10**, type hints encouraged but not enforced.
- **Tests must run offline.** Use `MockLLM` for any new code path.
- **Every tool result is a `ToolResult`** — don't bypass.
- **Every state mutation emits an event** via `observability.emit(...)`.
- **No `innerHTML` in dashboard JS** with user content. Use DOM API + `textContent`.
  Static templates may use `innerHTML` if the content is purely server-trusted.
- Run `ruff` before submitting: `ruff check hippoagent benchmark tests`.

## Adding a new LLM provider

If the provider is OpenAI-compatible:

```python
# hippoagent/llm.py
PROVIDERS["my_provider"] = {
    "env": "MY_PROVIDER_API_KEY",
    "base_url": "https://api.my-provider.com/v1",
    "default_model": "their-best-model",
}
```

Add it to `AUTODETECT_ORDER` and (optionally) `ALIASES`. Done. No client class needed.

If it's *not* OpenAI-compatible, write a class that exposes
`complete(system, messages, model=None, temperature=0.0, max_tokens=None,
stop_sequences=None) -> LLMResponse` and add it to `_build()`.

## Adding a new benchmark task

```python
# benchmark/tasks.py
TASKS.append(BenchmarkTask(
    id="my_001_thing",
    family="my_family",
    difficulty=2,
    prompt="Define `do_thing(x)` that ...",
    function_name="do_thing",
    test_code="assert do_thing(...) == ...\nprint('PASS')\n",
))
```

Tests use `subprocess` + `assert` + a `print('PASS')` sentinel. No fixtures needed.

## Pull requests

1. Open an issue first for non-trivial changes (sleep-stage logic, schema, fitness).
2. Branch from `main`, name it `feat/...`, `fix/...`, `docs/...`.
3. Keep tests green (`HIPPO_OFFLINE=1 pytest`).
4. Update README/CHANGELOG when relevant.
5. Squash if the history is noisy; otherwise normal merge is fine.

## Reporting experiments

If you ran HippoAgent on a new domain, model, or scale, we'd love a writeup.
Open an issue with the **Experiment** template — paste your `data/reports/*.json`
and what you observed, even if results are negative. Negative results are
genuinely interesting here: skill consolidation isn't always a win.

## Meta-rules for empirical claims (cycle 253-272)

This repository ships claims about a phenomenon (Structural Observer-Shift, see `docs/proposal/PAPER-21-OUTLINE.md`) that has been studied through 20 autonomous loops with adversarial review. Two A4 (anti-marketing) violations were detected by critic-orchestrator and remediated. The resulting meta-rules apply to anyone (human or AI) extending this codebase with claims about empirical findings.

### The 5 super-rules (cycle 267)

- **S1 EMPIRICAL DISCIPLINE**: untested claim = hypothesis. Run a bench (<5 min) before writing it in the paper. `N=5` single-injection note "replicated injection deferred".
- **S2 PROCESS DISCIPLINE**: every shipped claim about new behaviour must pass a critic-orchestrator gate (`mcp__critic-orchestrator__start_adversarial_review`). Save the narrative decision-making, not only the conclusion.
- **S3 WIRING DISCIPLINE**: code not wired in production = "test-validated only", never "shipped/production-ready". Hyperparameters with "fraction of total" semantics empirically calibrated to corpus, not theoretically.
- **S4 REFRAMING DISCIPLINE**: when a hypothesis is falsified, rewrite it honestly. Distinguish empirically "X creates Y" from "X reveals latent Y".
- **S5 LEVEL-OF-EFFECT DISCIPLINE**: clarify which level the fix acts on (partition shape, candidate count, cliff edge). Boundary parameters at the threshold edge are suspect of mis-calibration.

### Automated checks

The repo ships three scripts that operationalize S1-S5:

- `scripts/check_a4_violations.py --commit-msg "..." --new-files engram/...` — pre-flight gate for marketing patterns in commit messages combined with dead-code modules. Validated on 3 scenarios (cycle 253 BLOCK, cycle 254 OK, cycle 261 WARN). See `docs/proposal/PAPER-21-OUTLINE.md` §9.6 for theory.
- `scripts/track_a4_violations.py` — cumulative tracker over `critic/*` facts saved in HippoAgent memory. Computes pre/post-threshold violation rate. Outputs `tracked_a4_violations.json`.
- `scripts/mine_meta_rules.py` — automated meta-rule mining from git log (recall 1.0 on HippoAgent self-authored commits, 0.5 on engram-orchestrator/clp cross-validation — generalization bounded, see paper §9.6.1).

### Saving critic verdicts as memory

When you run an adversarial review, save the verdict as a HippoAgent fact with namespace `critic/cycle{N}-verdict-{summary}-2026-MM-DD`. Examples: `critic/cycle258-verdict-second-pass-louvain-dead-code-2026-05-23`. This makes past evidence retrievable for future anti-confab cross-reference (paper §9.6.2 CRITIC-AS-MEMORY).

### Additional M-rules from critic-gate feedback (cycle 287, 299)

Two M-rules emerged from critic-orchestrator HOLD verdicts (singolarità #22 BENCH-CRITIC DUALITY: HOLD verdicts ALSO extract M-rules from counterexample worker evidence):

- **M13 SECOND-CALL-SITE COVERAGE** (cycle 287, closed cycle 289): when a parameter is threaded through multiple call sites from a single derivation point, the contract test should pin EACH call site explicitly, not just the first.
- **M14 EMPIRICAL-HEADLINE-PROTECTION** (cycle 299, closed cycle 303): bench numbers quoted in commit/paper claims (e.g. "X candidates vs Y") should have unit-test pinning, not only bench JSON artifacts. Test the comparative inequality even if the exact number depends on corpus.
- **M15 DOCSTRING-VS-ASSERT-PARITY** (cycle 308, closed cycle 311, re-closed cycle 322): when a contract test's docstring promises a falsifiable claim, the actual `assert` statement MUST enforce the same claim. Wording drift (e.g. docstring says "2x dominance" while assert says `>= other_max` parity) is a silent semantic regression that critic-orchestrator counterexample worker will catch. Closure requires updating BOTH the docstring AND the assertion together, and ideally adding a Popperian fixture that exercises the gap between them.
- **M16 POST-FIX-CRITIC-VALIDATION** (cycle 322, closed cycle 325): when a critic gate FAILS and the fix is applied, the fix must be RE-GATE-ED with a fresh adversarial review BEFORE claiming closure. The cycle 308 → 311 → 318 trajectory shows that a "fix" can introduce new silent issues (M15 self-violation in cycle 311) that only surface in a second gate. The cycle 322 → 325 HOLD verdict closes the loop properly. Pattern: FAIL gate → empirical fix with Popperian fixture → fresh gate → HOLD (or new FAIL with new specific counterexample, repeat).
- **M17 LIVE-CORPUS-SNAPSHOT-FREEZE** (cycle 354, born 2026-05-23): when running cross-snapshot replicate benches on production data, the source corpus may evolve between safe-copy snapshots (auto-dream worker writes, contradictions resolution, etc.). For true cross-validation, freeze a snapshot file (`shutil.copy2` once to a stable path, then bench from that frozen file across N runs) rather than re-copying the live source each run. The cycle 354 finding (HYBRID variance 40-44 across n=6 snapshots) showed that "same nominal corpus 2366 alive" can yield different counts when sourced live. Pattern: for empirical replicate benches, freeze artifacts; for cross-snapshot legitimate variation studies, document the snapshot timestamps explicitly.
- **M18 NARROW-CRITIC-CLAIMS** (cycle 384, born 2026-05-23, revised cycle 386 post-falsify-claim CONSENSUS_FAIL 2-1): critic-orchestrator timeouts ARE EMPIRICALLY ASSOCIATED with broad multi-conjunctive claims (cycle 343 / 358 / 371 / 382 all timed out at 180s on n≥3 conjuncts). Pattern: split broad claims into atomic single-predicate clauses and gate each independently. **A3 honest revision per cycle 386 falsify-claim (agy Gemini 3.1 + gemini 2.5 + claude opus 2-1 CONSENSUS_FAIL)**: M18 is a SUFFICIENCY heuristic (n≥3 conjuncts → high timeout probability), NOT a NECESSITY claim. Cycle 385 self-test timeout with conjunct=2 demonstrates timeout can occur for OTHER reasons too (not yet operationalized — vague "semantic complexity" rejected as infalsificable per critics). Useful as a practical heuristic for splitting broad claims, but NOT a complete model of when critic times out. Future work: instrument critic.py per-claim metadata + correlate (conjunct count, claim length, evidence-link count, abstract-reasoning depth) with timeout probability across n≥10 controlled gates.

### Production wire — opt-in environment variables (cycle 284, 297)

The SOS mitigation modes are wired into `engram.auto_dream_worker` via opt-in env vars. Default OFF, so existing behaviour is unchanged.

| Variable | Mode | Cycle | Effect |
|---|---|---:|---|
| `ENGRAM_USE_STABLE_PARTITION` | stable_partition | 284 | Persistent partition (cycle 261, 0.0 Jaccard unchanged nodes) |
| `ENGRAM_USE_HYBRID` | hybrid | 297 | stable + second_pass within (cycle 295, 44 candidates vs 0 at 2200 facts; cycle 346 replicated 40 vs 0 at 2366 facts) |

Accepted values: `1`, `true`, `yes`, `on` (case-insensitive). Anything else is treated as False.

Precedence (cycle 292+295): `enable_hybrid` > `enable_stable_partition` > `enable_second_pass` > vanilla. The if/elif chain in `detect_emerging_skills` picks the most-specific active mode.

Compute cost (cycle 306 measured, corpus 2366 facts, 5 runs):
- vanilla: 286.5 ms (1.00x)
- stable_partition: 399.7 ms (1.40x)
- second_pass: 583.7 ms (2.04x)
- hybrid: 1249.4 ms (4.36x)

### Engram OS-native memory stack (cycle 362-369)

The `engram/` package now exposes a layered OS-native memory primitive
stack, designed to integrate with the parallel `clp.agentos` 10-layer
OS-per-AI stack (loop 337-368). All layers have falsifiable contract
tests in `tests/test_*.py` and route through a single typed boundary.

| Layer | Module | Cycle | Tests | Purpose |
|---|---|---:|---:|---|
| L1 | `engram/mesh_memory.py` | 362-363 | 4/4 | Cross-instance recall via clp vec_bus, embedding-only exchange (no plaintext). Resonant-merge: Hopfield cross-agent interpolation. |
| L3 | `engram/syscall_bridge.py` | 364 | 5/5 | Typed entry point with manifest validation + audit JSONL + rate limit. Single `engram_invoke(op, args, actor)` API. |
| L4 | `engram/op_supervisor.py` | 365 | 6/6 | Erlang-style per-op circuit breaker (closed/open/half_open) with reset_window. Fault-isolation at operation level. |
| L5 | `engram/capability_token.py` | 368 | 7/7 | HMAC-SHA256 capability tokens scoped to (peer_id, op, expiry). Reuses A2A bus secret per A6 lentezza. |
| extra | `engram/dashboard_widget.py` | 367 | 4/4 | Diagnostic snapshot CLI: stack layers, manifest ops, circuit states, rate-limit, audit summary. Run: `python -m engram.dashboard_widget`. |
| extra | `engram/engram_syscall_mcp.py` | 366 | manual | Standalone MCP server: 5 tools (recall, mesh_query, mesh_fetch, audit_tail, dashboard) wrap engram_invoke. NO modification to main `mcp_server.py`. |
| E2E | `tests/test_engram_stack_e2e.py` | 369 | 2/2 | Full 2-agent pipeline test: token-authz + mesh federation + privacy + audit order. |

**Total falsifiable contracts: 28/28 PASS** (`pytest tests/test_{mesh_memory,syscall_bridge,op_supervisor,capability_token,dashboard_widget,engram_stack_e2e}.py`).

A3 honest scope: cycle 362-363 mesh_memory is the only genuine
singolarità claim (embedding-only cross-instance recall federation,
n=4 PASS validated). Cycle 364-369 are engineering integration of
known patterns (Hystrix/Polly circuit breaker, JWT-like capability
tokens, MCP tool exposure) — value is in the composition with the
syscall_bridge typed boundary + audit, not in the patterns themselves.

### Database-less memory experiments (cycle 388-389)

**Aurelio mandate 2026-05-23 post-compact**: "sperimenta cose che non
siano database". Two B4 NUCLEAR attempts, both empirically falsified:

| Cycle | Module | Approach | Result | Lesson |
|---|---|---|---|---|
| 388 | `engram/holographic_memory.py` | HRR (Plate 1995) + Modern Hopfield + Bloom + bounded cleanup pool | **FALSIFIED**: recall@1=10%=pool_cap/N puro cache effect. HRR-pure senza cleanup library = rumore. | Cleanup pool è mini-DB. "Zero DB" naive non raggiungibile via HRR algebra sola. |
| 389 | `engram/resonator_memory.py` | Resonator Networks (Frady/Kent/Olshausen/Sommer 2020 NeurIPS) — fixed alphabet codebook, no per-fact storage, factorize via dynamics | **PARTIAL**: K-1 hint funziona (recover ultimo role 100%). No-hint pure resonator = stuck in fixed-point local minima (xfail honest). | Storage costante 24MB indipendente N ✓. Ma cleanup oracle = codebook = piccolo DB. |
| 390 | (same module) | Soft cleanup (softmax weighted) + multi-restart 16 seeds | **PARTIAL+**: residual hard=1.69 → soft+restart=1.04 (-38%). N=3 no-hint: 1/3 found (vs 0/20 cycle 389). | Soft cleanup migliora ma N=10 no-hint resta 0/20 (xfail still). |
| 391 | (same module) | Matching Pursuit (Mallat 1993) — iterative subtract of found composition | **PARTIAL**: stesso ceiling 1/3 N=3. Matching pursuit naive non rompe il limite. | Vera lateral inhibition richiede modifica dynamics interna, non solo post-hoc. |
| 392 | `scripts/bench_resonator_scaling.py` | D vs M scaling sweep 5 configs × 5 seeds | **SUPPORTED**: Config C (D=4096, M=32) recupera 3/3 facts in 2/5 seeds (max=3/3, mean=2.2/3). | Sweet spot empirical D=4096 M=32. Database-less raggiungibile a cost ~1.5MB codebook shared. |
| 393 | (same script `--mode nscaling`) | N scaling at sweet-spot D=4096 M=32, n=3-5 seeds | **CHERRY-PICKED**: N=320 → 96.8% recovery in 3 seeds. Falsificato in cycle 394 con n=20. | Cherry-pick danger: 3 seeds confermano happy path ma nascondono distribuzione reale. |
| 394 | (cross-LLM falsify + replicate n=20) | Replication N=320 con 20 seeds per significatività statistica | **HONEST UPDATE**: mean=89.0% ± 14.7%, median=95.0%, 20% seeds catastrophic (<80%), 80% nominal (≥90%). Distribuzione bimodale. | claude_opus + agy peer review giustificato. n≥20 seeds necessari per claim affidabile. Cycle 393 96.8% era cherry-pick. |
| 395 | (root cause + fix) | Investigation 4 catastrophic seeds + n_restarts bump 16→32 | **FIXED**: con n_restarts=32, seed 4=99.7% (era 70.9%), seed 6=97.8% (era 45.6%), seed 13=97.5% (era 72.8%), seed 18=97.5% (era 56.9%). Tutti >97%. Default bumped 16→32 in `recall_all_via_matching_pursuit`. | Catastrophic mode was random init collision recoverable with more restarts. n_restarts=32 elimina coda bimodale. |
| 396 | (full n=20 verification post-fix) | Replica empirica n=20 seeds con n_restarts=32 fix permanente | **VERIFIED FINAL**: mean=98.2% ±0.7%, median=98.1%, min=97.2%, max=99.7%. **0/20 catastrophic**, 20/20 nominal. Distribuzione monomodale stretta. | Database-less memory empiricamente CONFIRMED su N=320 facts con storage 1.5MB costante. End of B4 NUCLEAR experiment chain. |

Cross-LLM cycle 388 `mcp__engram-bridge__falsify_claim` 4-source CONSENSUS_FAIL 2-1:
- **agy Gemini 3.1**: rivelazione Resonator Networks 2020 (informazione cruciale)
- **claude opus HOLD**: precisione "DB-equivalent" vaghezza, Hopfield item memory ≠ DB indicizzato
- **gemini 2.5 FAIL**: spurious answer

**Meta-conclusione cycle 388+389**: OGNI memoria AI persistente richiede una struttura dati (vocabolario, codebook, dictionary, alphabet, embedding space, weights). Il "database" è la rappresentazione esplicita di quella struttura. "Database-less" è quantitative non qualitative — si può ridurre per-fact storage a zero (Resonator) ma serve sempre un alphabet/codebook. Vera "in-weights memory" richiede LoRA-delta o decoder generativo (cycle 390+ future work).

Trade-off table:
- HRR + cleanup_pool: storage = 110KB constant, accuracy 100% con cleanup, lossy senza.
- Resonator: storage = 24MB constant, accuracy 100% con K-1 hint, fail no-hint naive.
- SQLite baseline: storage N-linear, accuracy 100%, no algebra.
- Crossover storage: HRR vince oltre N≈1300 facts, Resonator vince sempre (constant) ma serve alphabet shared.

Files: `engram/holographic_memory.py`, `engram/resonator_memory.py`, `tests/test_holographic_memory.py` (10/10), `tests/test_resonator_memory.py` (8/8 + 1 xfail honest), `scripts/bench_holographic_vs_sqlite.py`. Lineage: cycle 388 commit `bd13b1a`, cycle 389 to be committed.

Lesson from clp parallel session loop 359-363: cross-LLM FALSIFY
accepted 3/3 for "singolarità" claims. Engineering rigor (manifest
validator catches 3/3 hallucinated commands) is the real win, not
paradigm-shift marketing.

### Honesty wins

Falsifying your own hypothesis is positive science. Cycles 253 and 261 both shipped framing that later failed adversarial review; honest re-framing in cycles 260 and 263 makes the body of work stronger, not weaker. The pattern "ship isolated code, frame as production" recurs unless detected — automated checks ($check_a4_violations.py$) reify this learning.

## Code of conduct

Be kind, be precise, attack ideas not people. We follow the
[Contributor Covenant 2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
