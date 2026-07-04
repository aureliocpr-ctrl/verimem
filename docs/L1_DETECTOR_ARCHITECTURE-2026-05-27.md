# L1.x Anti-Confab Detector Chain — Architecture 2026-05-27

**Status**: 18 detectors active in `engram/anti_confab_gate.py` orchestrator. 350/350 pytest PASS regression in 7.73s. <30µs/call overhead.

**Origin cycle 2026-05-27**: M12 PTY hallucination lesson (fact `fbaa77df3860`) → triangulation Claude+Gemini+GPT 10 round → 10 nuovi detector shipped (L1.9 to L1.18).

---

## Chain L1.0 → L1.12

| Layer | Cycle | Module | Triggers on | Evidence accepted |
|---|---|---|---|---|
| **L1.0** | #128 | `anti_confabulation.py:detect_unsupported_shipped_claim` | SHIPPED/MERGED/WIRED/DEPLOYED | commit:/pr:/file:/git: |
| **L1.5** | #128 | `anti_confabulation.py:detect_unsupported_diagnosis_claim` | "the bug is X" / "root cause is Y" | file:/grep:/log: |
| **L1.7** | #128 | `anti_confabulation.py:detect_unsupported_task_state_claim` | task state "DONE"/"COMPLETE" | task_id:/PR_state: |
| **L1.8** | #183-184 | `l1_extended_detector.py:detect_unsupported_fix_claim` | FIXED/RESOLVED/PATCHED/REPAIRED | commit:/pytest:_PASS/bash:exit0 |
| **L1.9** | 2026-05-27 round 1-2 | `l1_performance_detector.py` | 10 patterns: arrow_latency, nx_speedup, percent_perf, game_changer, halves_doubles, order_of_magnitude, italian_qualitative, from_to_latency, absolute_qualitative, vague_benchmark | bench:/measure:/perf:/timing:/latency:, bash:..._ms, pytest:bench |
| **L1.10** | 2026-05-27 round 2 | `l1_works_detector.py` | funziona/works/confirmed/risolto/passes/succeeded + contextual ok | pytest:_PASS, bash:exit0, cmd:exit0, smoke:, runtime:, file:marker |
| **L1.11** | 2026-05-27 round 3 | `l1_production_ready_detector.py` | production-ready, prod-ready, ship-ready, stable, robust, enterprise-grade, battle-tested | coverage:, soak:, stress:, regression:_PASS, ci:green, release_tag: |
| **L1.12** | 2026-05-27 round 4 | `l1_security_detector.py` | secure, hardened, hardening, security-ready, tamper-proof, sicuro, blindato, CVE- | audit:, pentest:_PASS, threat_model:_reviewed, bandit:_PASS, semgrep:_PASS, vuln_scan:_PASS |
| **L1.13** | 2026-05-27 round 5 | `l1_completion_detector.py` | complete/completed/done/finished/closed/wrapped-up + italian completo/completato/finito/fatto/chiuso/concluso | task:_closed, jira:_resolved, acceptance_test:_PASS, dod:_met, review:_approved, pr:_merged, pytest:_PASS, bash:exit0 |
| **L1.14** | 2026-05-27 round 6 | `l1_documentation_detector.py` | documented, well-documented, explained, described + italian documentato/spiegato/descritto | docs:, md:, file:_md, readme:, changelog:, comment:|
| **L1.15** | 2026-05-27 round 7 | `l1_tested_detector.py` | tested, well-tested, verified, validated + italian testato/verificato/validato | pytest:_PASS, test_coverage:, ci:green, review:_approved, qa:_PASS |
| **L1.16** | 2026-05-27 round 8 | `l1_approval_detector.py` | approved, sign-off, authorized, blessed, ratified + italian approvato/autorizzato/ratificato/firmato | approval:_signed, approver:_signed, review:_approved, pr:_approved, ticket:_approved, email:_approval, chat:_approved |
| **L1.17** | 2026-05-27 round 9 | `l1_monitored_detector.py` | monitored, observed, tracked, watched, alerted + italian monitorato/osservato/tracciato | dashboard:, grafana:, alert:, prometheus:, metric:, sentry:, datadog:, log: |
| **L1.18** | 2026-05-27 round 10 | `l1_automated_detector.py` | automated, automatic, scheduled, periodic, recurring + italian automatizzato/programmato/schedulato/periodico | cron:, schedule:, scheduler:, workflow:, systemd:, airflow:, celery:, ci: |
| **L3** | #70 (full tier) | `validate_claim.py` | semantic contradiction vs corpus | corpus search threshold 0.6 |

---

## Triangulation pattern Claude+Gemini+GPT

Effort per detector ~30-60min cross-LLM consultation + implement + pytest:

1. **Claude** propone initial design 4-5 patterns
2. **Gemini 2.5 Pro** (via `mcp__engram-bridge__ask_gemini`, 60s response): identifica FP/FN
3. **GPT** (via Chrome Aurelio Plus account, 90s response): identifica FP/FN aggiuntivi
4. **Claude** sintetizza + implement v2/v3 con patch
5. **Pytest** parametrizzato 20-30 cases (positive + negative + evidence + edge + gate wire)

**Convergenza tipica**: 2/2 cross-LLM su candidate (es. L1.10 entrambi votano (a), L1.11 entrambi votano (b), L1.12 entrambi votano (d)).

**Divergenza notable**: L1.13 (round 5) Gemini favorita (f) scalable vs GPT favorita (h) deployed — no convergenza, detector skipped.

---

## Gate overhead (bench empirical 2026-05-27)

| Configuration | Latency per call |
|---|---|
| `validate="off"` (baseline) | 1.7µs |
| `validate="fast"` clean proposition | 17.7µs |
| `validate="fast"` perf claim (L1.9 fires) | 8.6µs (early return) |
| `validate="fast"` works claim (L1.10 fires) | 15.0µs |
| **Overhead L1.0-L1.12 chain (clean)** | **~16µs** |

Sub-millisecond → ZERO impact su `hippo_remember` throughput (LLM call dominante).

---

## File structure

```
~/Code/HippoAgent/engram/
  ├── anti_confab_gate.py            # Orchestrator (run_validation_gate)
  ├── anti_confabulation.py          # L1.0/L1.5/L1.7 (cycle 128)
  ├── l1_extended_detector.py        # L1.8 FIX-family (cycle 183-184)
  ├── l1_performance_detector.py     # L1.9 perf (2026-05-27 round 1-2)
  ├── l1_works_detector.py           # L1.10 works (2026-05-27 round 2)
  ├── l1_production_ready_detector.py # L1.11 prod-ready (round 3)
  ├── l1_security_detector.py        # L1.12 security (round 4)
  └── validate_claim.py              # L3 (cycle 70)
```

---

## Empirical evidence (cycle 2026-05-27)

| Detector | Pytest cases | Time | Provenance |
|---|---|---|---|
| L1.9 (v3 final) | 42 PASS in ~2.5s | 36 detector + 6 wire | Claude v1 (5/5) → Gemini v2 (14/14) → GPT v3 (18/18) → 36 parametrized |
| L1.10 | 26 PASS in 2.49s | 21 detector + 5 wire | Triangulation Claude+Gemini+GPT votano (a) |
| L1.11 | 25 PASS in 2.38s | 23 detector + 2 wire | Triangulation 2/2 votano (b) |
| L1.12 | 26 PASS in 2.36s | 24 detector + 2 wire | Triangulation 2/2 votano (d) |
| L1.13 | 29 PASS in 2.33s | 27 detector + 2 wire | Round 5 DIVERGENZA → Claude architectural choice (e) ortogonal |
| L1.14 | 18 PASS in 2.38s | 16 detector + 2 wire | Round 6 Claude choice (g) ortogonal a tutti |
| **Total nuovi** | **166/166 PASS** | session 2026-05-27 ~3h | |
| **Regression full** | **276/276 PASS in 7.40s** | post-shipping | |

---

## How to add L1.13+ (replicable pattern)

1. Identify gap from real incident (es. M12 lesson for L1.9)
2. Brainstorm `mcp__engram-bridge__ask_gemini` con 4 candidates + criteri
3. Brainstorm GPT via Chrome con stesso prompt
4. If convergenza 2/2 → implement; else skip
5. Write `engram/l1_<name>_detector.py` con pattern + evidence prefixes
6. Wire in `engram/anti_confab_gate.py:_l1_warnings()`
7. Pytest parametrizzato `tests/test_l1_<name>_detector.py` (positive + negative + evidence + edge + wire)
8. Run regression pytest anti-confab suite
9. Save Engram fact with lineage parent

Effort tipico: 30-60 min per detector.
