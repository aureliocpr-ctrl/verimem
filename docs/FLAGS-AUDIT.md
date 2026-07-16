# FLAGS-AUDIT — claim-vs-default audit (Giro 0)

**Date**: 2026-07-15 · **Auditor**: Claude (CTO session, adversarial-review follow-up)
**Method**: no claim without provenance read *in this session*; every verdict cites `file:line`
on current `main` (`6d1d910`). Coverage is declared at the bottom — what was read in full,
what was read partially, what was NOT read. This audit generalizes the 2026-07-13 lesson
(abstention was OFF by default → fixed for the gateway in `6791bca`, env switch `fd44dc8`):
**when a pattern is found once, sweep ALL its instances.**

---

## 1. Verdict on the 5 external-review claims

| # | Review claim | Verdict | Evidence |
|---|---|---|---|
| 1 | `_is_local_base_url` is a substring match → air-gap verdict spoofable (`evil-localhost.attacker.com` counts as local) | **CONFIRMED** | `engram/airgap.py:42-44` |
| 2 | Admission gate (L0, `admission_gate.py`) is OFF by default | **CONFIRMED** | `engram/admission_gate.py:55-80` ("default OFF = neither") |
| 3 | Preset `balanced` has `ground: False` (L4 moat opt-in) | **CONFIRMED** | `engram/client.py:36-40` |
| 4 | Gateway key resolve = `fetchall()` + Python loop, O(n keys) per request | **CONFIRMED** | `engram/gateway.py:252-265`; note `key_hash` is already `UNIQUE` (line 186) → fix is a one-line indexed lookup |
| 5 | What does `ground=True` do without a `source`? | **RESOLVED: silent skip** | `engram/client.py:86-87` ("Without a source or a judge, L4 is skipped"); flipping `ground=True` by default is non-breaking but only protects callers who pass `source` |

Severity correction on #1: it is a **config self-check** (no network calls, inspects env
the operator controls) — the bug produces a *spoofable compliance verdict*, not remote
exploitation. "CVE-class" was overstated; still a mandatory fix because the verifiability
of air-gap is a sold claim (README line 88-89).

## 2. Where the external reviews were WRONG or STALE

Verified against current main — these review claims do NOT hold:

| Review said | Reality | Evidence |
|---|---|---|
| "L1 default `fast` = only 3 detectors" | `fast` runs the ENTIRE L1 family — L1, L1.5, L1.7, L1.8–L1.19, L1.20, L1.21 (~21 detectors). `fast` vs `full` differ ONLY in L3 contradiction checks | `engram/anti_confab_gate.py:269-532` (`_l1_warnings` unconditional at :676) |
| "L1 is regex EN/IT-only, multilingual claims pass clean" | **L1.20 multilingual SEMANTIC self-claim detector** shipped 2026-07-09 (embedding dual-check, calibrated recall 1.0 / 0 FP across 10 languages), ON by default (opt-out `ENGRAM_L1_SEMANTIC=0`) | `anti_confab_gate.py:493-518`, `semantic_selfclaim.py:310-312` |
| "no sycophancy-related detector exists" | **L1.21 quality-superlative / sycophancy detector** shipped 2026-07-10 (red-team), ON by default. (The *systemic* sycophancy gap — user-belief class, retrieval caveat — remains real, see §4) | `anti_confab_gate.py:498-513` |
| "gateway is 367 lines, no security headers, no TLS story, rate limit only on 2 MCP tools" | gateway.py is 1204 lines: `_SecurityHeadersMiddleware` (CSP per content-type), `_BodyLimitMiddleware` (real-bytes anti-DoS), access-audit JSONL default ON (multi-tenant), per-key rate limit with plan tiers (free 60/min, pro 600), 402 quota teeth, anti DNS-rebinding | `gateway.py:453-573, 629-643, 645-689, 748-758` |
| "the enterprise API does not abstain" | Gateway read-path abstention is **ON by default** (`ENGRAM_GATEWAY_MIN_RELEVANCE=auto`) | `gateway.py:388-403, 806-814` |
| "no injection screen in the default path" (implied by review 1's L0-OFF story) | Injection screen + secret redaction are **ALWAYS-ON** store-side (opt-out escape hatches), independent of the L0 admission gate | `semantic.py:1960-1970, 2009-2022`; `memory.py:461-491`; `skill.py:199-219` |
| "threshold 40 could be 25 or 65 and you wouldn't know (±25pp)" | The measured distribution is bimodal with a clean gap 0→42 (noise scores 0, grounded 42-100): any threshold in the gap decides identically. The real n=15 weakness is corpus representativity, not cut sensitivity | `grounding_gate.py:40-48` |

## 3. Flagship flags — default vs README claim

Defaults verified by reading the resolution site (not inferred):

| Flag / knob | Default | README claim it backs | Aligned? |
|---|---|---|---|
| L1 anti-confab family (`validate` preset) | **ON** (`fast`, all 21 detectors, `gate_mode=downgrade`) | "every fact enters as a low-trust claim…flagged instead of absorbed" (unsupported half) | ✅ |
| `ENGRAM_INJECTION_SCREEN` | **ON** (always-on, opt-out) | memory-poisoning defense | ✅ |
| `ENGRAM_REDACT_SECRETS` | **ON** (always-on, opt-out) | (not even claimed) | ✅ bonus |
| `ENGRAM_L1_SEMANTIC` (L1.20 multilingual) | **ON** (opt-out) | gated writes, all languages | ✅ |
| `ENGRAM_GATEWAY_MIN_RELEVANCE` | **auto = ON** | "abstention by design" (gateway surface) | ✅ (since `6791bca`) |
| `ENGRAM_ADMISSION_GATE` (L0 telemetry/dup/injection routing) | **OFF** | "Every write passes an admission gate" (headline, line 3) | ⚠️ headline is carried by L1+screens, not by the module literally named "admission gate" |
| L3 contradiction (`validate=full`) | **OFF** (default is `fast`) | "or **contradictory** assertions are flagged" (line 20-22) | ❌ the "contradictory" half of the sentence is NOT honored by default |
| `ENGRAM_GROUNDING_WRITE` / preset `ground` | **OFF** (opt-in per call) | "must be backed by evidence to gain status"; site's AUROC 0.971 moat | ❌ the moat is off out-of-the-box (SDK docstring is honest about it; README/site headline is not) |
| `ENGRAM_GROUNDING_BACKEND` | `claude` | zero-API-cost local judge exists (CE distilled) | ⚠️ `local` has automatic failover + per-judge threshold already wired (`grounding_gate.py:288-345`) — flip is safe by construction |
| `ENGRAM_MIN_RELEVANCE` (SDK `explain()`) | **unset → 0.0 permissive** | "Abstention by design…holds at 1.0 across our end-to-end runs" (line 29-30) | ❌ true on the gateway & in e2e runs (which set the floor); NOT true for bare `pip install` SDK |
| `ENGRAM_SOURCE_TRUST` (+`_MIN` 0.25) | **OFF** | README says "*(flag-gated)*" | ✅ honestly labeled |
| Provenance signing (`ENGRAM_PROVENANCE_KEY`) | **OFF** | README says "*(opt-in)*" | ✅ honestly labeled |
| `ENGRAM_SEMANTIC_CONFLICT` (L3-semantic NLI) | **OFF** | (not claimed as default) | ✅ |
| `ENGRAM_SQLITE_SYNCHRONOUS` | `NORMAL` | — | ⚠️ documented data-loss window on OS crash (`_sqlite_pragma.py:9-10`); consider `FULL` for the gateway profile |
| `ENGRAM_VALIDATE_DEFAULT` | exists (`off/fast/full`) | — | ✅ the global flip lever for Giro 1b is already shipped (`anti_confab_gate.py:202-215`) |
| Evidence-existence check (`repo_root`) | opt-in per call | fabricated-but-well-formed `commit:deadbeef` refs | ⚠️ format-only by default |
| WF3 personal-context suppression | ON (L1 advisory-only on personal facts w/o dev signal) | precision guard, ~40% FP fix | ✅ relevant prior art for `user_belief` split |

**The honest one-line summary**: the default write path is NOT naked — L1×21 + injection
screen + redaction + downgrade are all on — but the three things the marketing leads with
(**admission gate as named**, **contradiction detection**, **the L4 entailment moat with its
AUROC**, plus **SDK-side abstention**) are all opt-in or partial. The README's fine print
is mostly honest; the headline sentence and the site are ahead of the defaults.

## 4. Real gaps confirmed (survive the stale-review filter)

1. **Air-gap substring bug** — fix with `urlsplit().hostname` exact match (Giro 1a).
2. **Key lookup O(n)** — indexed `WHERE key_hash = ?` (Giro 1a).
3. **"Contradictory…flagged" claim vs L3-off default** — either flip `balanced` to include
   a cheap L3, or fix the README sentence (Giro 1b decides which side moves).
4. **L4 moat opt-in + `claude` backend + n=15 calibration** — recalibrate (n≥300-500),
   then flip `balanced` to `ground=True` + backend `local` (failover already safe).
5. **SDK abstention floor off** — decide: flip `ENGRAM_MIN_RELEVANCE` default or align README.
6. **Systemic anti-sycophancy** (beyond L1.21 keyword/embedding): PARTIALLY CLOSED (Giro 2).
   The `user_belief` epistemic class now exists (`af22b04`) AND the ingest produces it —
   `ingest_conversation(..., tag_beliefs=True)` tags an unverified factual assertion
   `BELIEF:` → `status="user_belief"` → out of default recall (`0e670e1`, opt-in, default off).
   `include_beliefs` recall opt-in SHIPPED (every recall branch: warm cache bypassed,
   cold fallback + as_of forward the flag, narrow — orphaned/quarantined stay hidden;
   `tests/test_include_beliefs.py`, 7 tests). STILL OPEN: guardian correction and the
   MemSyco-Bench number (no "anti-sycophancy" claim until the delta is measured). Existing hooks that made
   it cheap: `writer_role` already in `classify_admission` (`admission_gate.py:100`) and in
   `run_validation_gate` (`anti_confab_gate.py:633`), `FLAG_LOW_PROVENANCE` verdict, WF3
   personal/dev context split, `_is_honest_reported` (reported-speech guard, `anti_confab_gate.py:244-266`).
7. **`synchronous=NORMAL`** on the gateway profile (durability window).
8. **Sycophancy phase-1 work exists only in the research fork** — `vivarium-verimem`
   commit `a751540` "sycophancy phase-1 paired-test — retrieval layer is pressure-immune"
   never landed on main. Evaluate porting the paired-test into `benchmark/` (Giro 2).

## 5. Full flag inventory (159 names, from `(ENGRAM|HIPPO)_[A-Z0-9_]+` sweep over `engram/`)

Verified individually in §3: the 18 flagship rows. Everything below is **inventory only**
(default NOT individually verified in this audit) — grouped by function:

- **Gate/trust**: `ENGRAM_VALIDATE_DEFAULT`, `ENGRAM_ADMISSION_GATE`, `ENGRAM_GROUNDING_{WRITE,WRITE_THRESHOLD,THRESHOLD,BACKEND,JUDGE,GATE,FOCUS_CHARS}`, `ENGRAM_LOCAL_GATE_MODEL`, `ENGRAM_LOCAL_NLI_MODEL`, `ENGRAM_L1_SEMANTIC{,_T_HYPE,_T_DELTA}`, `ENGRAM_SEMANTIC_CONFLICT`, `ENGRAM_SOURCE_{TRUST,TRUST_MIN,TRUST_HALF_LIFE_DAYS,INDEPENDENCE,INDEPENDENCE_DECONFOUND,AUTO_CONFIRM}`, `ENGRAM_ANCHOR_SUSPECT`, `ENGRAM_EVIDENCE_REQUIREMENT`, `ENGRAM_SELF_RATIO_MAX`, `ENGRAM_ERROR_COST`, `ENGRAM_CONTRADICTION_ENABLED` (daemon gate), `ENGRAM_INJECTION_SCREEN`, `ENGRAM_REDACT_SECRETS`, `ENGRAM_UNICODE_SANITIZE`, `ENGRAM_PROVENANCE_KEY`, `ENGRAM_HOOK_TOKEN`, `ENGRAM_CAPABILITY_GATE`, `ENGRAM_SANDBOX_{MODE,CWD,AUDIT_DIR}`
- **Read path**: `ENGRAM_MIN_RELEVANCE`, `ENGRAM_GATEWAY_MIN_RELEVANCE`, `ENGRAM_RECALL_{RERANK,CENTERING}`, `ENGRAM_RERANK_*` (6), `ENGRAM_PPR_FUSION{,_FLOOR,_BUDGET_S}`, `ENGRAM_ANN_{RECALL,MIN_N}`, `ENGRAM_TOPIC_PENALTY`, `ENGRAM_BUMP_ON_RECALL`, `ENGRAM_COMPOSER_MIN_SCORE`, `ENGRAM_DERIVATION_AUTODETECT`
- **Reconcile/consolidate**: `ENGRAM_RECONCILE_*` (7), `ENGRAM_AUTO_{DREAM_ENABLED,DREAM_MIN_ITEMS,DREAM_COOLDOWN_S,CONSOLIDATE}`, `ENGRAM_CONSOLIDATE_COOLDOWN_S`, `ENGRAM_DREAM_KEEP`, `ENGRAM_USE_{STABLE_PARTITION,HYBRID}`, `ENGRAM_DECAY_ENABLED`, `ENGRAM_EPISODE_UNDO_CAP`
- **Ops/observability**: `ENGRAM_{DATA_DIR,MODE,ACTOR,OFFLINE,AUDIT_LOG,GATEWAY_AUDIT_LOG,EVENT_LOG,EVENT_LOG_MAX_BYTES,FLOW_SURFACE,OPS_MANIFEST,SLOW_TXN_WARN_S,LONG_FACT_WARN_CHARS,SQLITE_SYNCHRONOUS,MODEL_LOCK_TIMEOUT_S,ENCODE_SERVICE,ENCODE_IDLE_S,ENTITY_LIVE,MCP_TOOLS_PREFIX,TOOL_NAMESPACE,BRIEFING_*}`
- **HIPPO_ namespace** (~60 flags: MCP server, providers, models, budgets, capability toggles `HIPPO_ENABLE_*`, FS sandbox `HIPPO_FS_*`, IDE allowlists, rate-limit knobs) — server-side surface, separate sweep recommended when the MCP server is the audit subject.
- Spurious/test tokens seen by the regex: `ENGRAM_X`, `HIPPO_X`, `HIPPO_FOO`, prefix fragments (`HIPPO_MODEL_`, `HIPPO_ENABLE_`, `HIPPO_DISABLE_`, `ENGRAM_BRIEFING_`, `HIPPO_MCP_RATELIMIT_`).

## 6. Coverage declaration (anti-laziness protocol)

- **Read in full this session**: `airgap.py` (116 ll), `admission_gate.py` (189),
  `client.py` (833), `gateway.py` (1204), `grounding_gate.py` (405), `anti_confab_gate.py` (849).
- **Read partially (targeted grep with context)**: `source_trust.py` (enabled/threshold),
  `relevance_floor.py` (env_floor), `semantic.py` (store screens), `memory.py` (episode screens),
  `skill.py` (store chokepoint), `semantic_selfclaim.py` (L1.20 gate), `daemon_runner.py`
  (contradiction daemon), `_sqlite_pragma.py` (header), `README.md` (first 150 lines).
- **NOT read**: `mcp_server.py` (8716 ll), `scope.py`, `ann_index.py`, the 20 `l1_*.py`
  detector bodies, `prompt_injection.py`, conversation_ingest/extraction prompts, the
  verimem.com site source, TS SDK. Claims about those remain UNVERIFIED here.
- **Repo provenance**: canonical main = `C:\Users\aurel\Code\HippoAgent` (`6d1d910`, remote
  `engram-mcp-stable`). Clones NOT audited: `HippoAgent-prefix-check` (detached),
  `vivarium-verimem` (research fork — has sycophancy/rerank work not on main),
  `murphy_intelligence/verimem`.

## 7. Recommended flips (input to Giro 1a/1b — no code changed in this audit)

- **1a (pure fixes, no behavior change for honest users)**: airgap `urlsplit` hostname match;
  indexed key lookup; `synchronous=FULL` in the gateway profile.
- **Site/README (free, immediate)**: align the headline sentence and the "contradictory"
  half-claim with today's defaults (the moat is opt-in for a MEASURED reason — see §8).

## 8. Giro 1b — MEASURED conclusion: do NOT flip the defaults (2026-07-15)

The Giro 0 plan called the `balanced → ground=True` flip a P0 "honest alignment".
Calibration on real HaluMem (``benchmark/local_gate_calibrate.py``, zero-API CPU CE)
**reverses that** — the flip is not free, it is a bad default trade:

| axis (n) | cut 50 | cut 99.64 (shipped) |
|---|---|---|
| foreign noise (400) — clean_admit | 0.96 | 0.87 (−13pp) |
| same-topic confab (144) — clean_admit / noise_reject | 0.965 / 0.889 | 0.896 / **0.931** |

- The shipped local cut **99.64 is Youden's J on the fine-tune's hard val mix**
  (``local_gate_distill_v2.py:216-219``), not arbitrary. On the REAL threat
  (same-topic confab: a plausible-wrong answer to the user's own question) it
  rejects 93% of confabs; dropping to ~50 would pass 11% instead of 7%.
- So the ~10-13% clean over-rejection is the **conscious price of purity**, right
  for `strict`, too aggressive for a general-purpose `balanced` default.
- Two of my own earlier reads were **falsified by measurement** and corrected in
  git: foreign-only ("lower to ~50") and the n=6 smoke ("hard case is easy").
  Kept as the method record: measure at scale, don't trust the toy.

**Decisions (measured, not guessed):**
1. **Do NOT flip `balanced` to `ground=True`.** L4 stays opt-in / `strict`-only —
   a ~10% clean over-rejection default is wrong for general use. The historic
   `ground=False` default was a reasonable undocumented trade, not laziness.
2. **Do NOT lower the local cut.** 99.64 is correctly calibrated for the hard axis.
3. **Close the claim-vs-default gap by DOCUMENTING, not flipping**: state that the
   entailment moat is opt-in *because* it trades recall for purity, and that
   `preset="strict"` is the trust-max mode. (Site/README — product messaging,
   owner decision.)
4. **FP-rate of the default L1 gate on legitimate personal facts: 2.0%** (6/300
   HaluMem, measured) — third-person biographies with ambiguous verbs
   (`works`→L1.10, `secured`→L1.12, `diagnosed`→L1.5) that WF3's personal-context
   suppression doesn't cover. Low, but a candidate mini-fix and direct input to
   the `user_belief` work (Giro 2).

## 9. CI status (honest, updated 2026-07-16)

The windows/py3.12 red is RESOLVED — and it was a CODE DEFECT, not infra
flakiness (this section's earlier "out of scope / infra" call was WRONG):
- **Root cause** (`ae48633`): `encode_service._pid_alive` used the POSIX idiom
  `os.kill(pid, 0)` for liveness. On Windows `signal.CTRL_C_EVENT == 0`, so
  CPython routes it to `GenerateConsoleCtrlEvent(CTRL_C_EVENT, pid)` — a Ctrl-C
  to the console process group pytest shares. `test_acquire_lock_refused_...`
  calls `_pid_alive(os.getppid())`, sending Ctrl-C to the runner's group; it
  bounced back as KeyboardInterrupt and killed the suite at ~66% (ubuntu ran
  6877 tests, windows was interrupted at 4545). Intermittent = console-event
  delivery race — which is exactly why two earlier GUESSED fixes (a reap-orphan
  fixture, a faulthandler dump) missed and were reverted; both rested on a
  disproven "suite passes then hangs at teardown" hypothesis (the 66% interrupt
  never reached teardown).
- **Fix**: Windows liveness via `OpenProcess`/`GetExitCodeProcess` (ctypes), no
  console control event; POSIX keeps the signal-0 idiom. Deterministic
  regression (monkeypatch `os.kill` to raise on win32).
- **py3.10** collection break (`tomllib`) fixed earlier (`69dbee5`).
- Honest caveat: the flake was intermittent, so one green windows run is not the
  proof — confidence comes from the removed mechanism + the deterministic test,
  not from CI passing once.
