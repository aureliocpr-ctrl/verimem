# Trust maintenance — the write-path moat

Most memory systems (mem0, Zep, MemOS) *extract and store*. Verimem adds a layer they
don't have: a **write-path that refuses to be fooled**. It is a tunable dial from
**recall-first** (apply every plausible update) to **never-delete-truth** (a stored,
verified fact cannot be overwritten by a bare assertion). Everything here is **off by
default and byte-identical** until you opt in; the whole dial is env-driven.

All knobs below are verified present in the code (see the file:line anchors). Numbers
are measured on HaluMem-Medium, local and deterministic (no `claude -p`).

## The knobs

| env | default | effect |
|---|---|---|
| `ENGRAM_RECONCILE_ON_WRITE` | off | master switch. When on, each stored fact is reconciled against shared-entity candidates (`engram/semantic.py` `_reconcile_on_write_enabled`). Off ⇒ nothing runs. |
| `ENGRAM_RECONCILE_AUTO_SUPERSEDE` | off | allow a clean update to actually **supersede** the old fact. Off ⇒ conflicts are only **contested** (fail-safe: never deletes). Needed to move the *Updating* slice. |
| `ENGRAM_RECONCILE_REQUIRE_EVIDENCE` | *(unset)* | anti-sycophancy policy when auto-supersede is on (`_reconcile_evidence_policy`): unset ⇒ **tiered** (require evidence only to overwrite an *evidenced* fact; bare→bare updates still apply); `=1` ⇒ **strict** (require evidence for any supersede); `=0` ⇒ **none** (raw recency+authority). |
| `ENGRAM_RECONCILE_MIN_OVERLAP` | `0` | precision floor on the NLI conflict verdict (`engram/truth_reconciliation.py` `_min_conflict_overlap`): reject a CONTRADICTION whose content-token Jaccard is below the floor — filters same-entity different-attribute pairs the NLI over-calls. |
| `ENGRAM_RECONCILE_NLI` | *(unset)* | conflict judge (wired by `HippoAgent.build` via `wire_reconcile_judge`): `=local` ⇒ **local NLI** cross-encoder (no `claude -p`, O4-clean, ~4× conflict-recall vs lexical); `=1/on/true/yes/llm` ⇒ subscription LLM judge; unset ⇒ lexical. |
| `ENGRAM_ENTITY_LIVE` | **on** | entity extraction on write (`_entity_live_enabled`). Reconcile finds candidates via shared entities, so this must stay on for the moat to see anything. |

## The dial, with measured numbers

**Anti-sycophancy** (a bare, confident, merely-newer assertion must not overwrite a
stored fact just because it was asserted). Two-sided bench under escalating pressure:
cave-rate **1.0 → 0.0** with the evidence gate, false-rigidity 0.0
(`benchmark/sycophancy_mem.py`).

**Tiered vs strict** (HaluMem is_update GT, n=60, local NLI thr 0.9):

| policy | update-recall | verified fact protected |
|---|---|---|
| none | 0.2833 | ✗ |
| **tiered** (default) | **0.2833** | ✓ |
| strict | 0.0 | ✓ (over-rigid) |

Tiered *dominates*: same recall as ungated, and a verified fact is sycophancy-proof.
Strict is safe but collapses recall on bare corpora (HaluMem updates carry no evidence).

**Precision dial** (`ENGRAM_RECONCILE_MIN_OVERLAP`, same setup):

| floor | update-recall | complementary false-supersede |
|---|---|---|
| 0.0 (default) | 0.2833 | 0.0667 |
| 0.2 | 0.20 | **0.0** |

A precision/recall dial (**not** a free win): floor 0.2 drops complementary
truth-deletion to zero at a −29% recall cost. Composed with tiered ⇒ *verified facts
protected AND zero complementary truth-deletion* — the "never lose truth" end of the dial.

**Conflict detection is the throughput gate.** Lexical matching supersedes only
1.67% of real HaluMem updates; the local NLI judge lifts that ~17× to 0.2833. So for
the moat to *do* anything at recall, set `ENGRAM_RECONCILE_NLI=local`.

## Honest caveats

- **The candidate finder gates everything.** Reconcile only sees facts that share an
  extracted entity AND pass the conflict judge. With the lexical default it rarely
  fires; `=local` is what makes it useful. Provenance/evidence gate is applied *after*
  a candidate is found.
- **`verified_by` is I/O-verified.** A `status=verified` write is demoted to
  `model_claim` unless its `verified_by` refs pass verification (filesystem / git),
  so "evidenced" means genuinely-backed, not merely-claimed.
- **Local scoring is a relative proxy.** The local e5 matcher for the Updating slice
  reads ~0.66 where the LLM judge reads ~0.29; use local numbers for A/B *direction*,
  not leaderboard absolutes. Judge-graded runs need `claude -p` (out of an
  offline/subscription loop).
- **`ENGRAM_RECONCILE_NLI` is wired by `HippoAgent.build`.** A bare `SemanticMemory`
  needs a programmatic `set_reconcile_judge(...)`.

## Evidence (tests + benches)

- `tests/test_reconcile_tiered_gate.py`, `tests/test_reconcile_evidence_gate_writepath.py`
  — the tiered/strict/none policy and write-path forwarding.
- `tests/test_reconcile_overlap_guard.py` — the NLI precision floor.
- `tests/test_updating_selector_overlap.py` — the update-selector floor (Pareto).
- `tests/test_reconcile_judge_env_wiring.py` — `=local` wires the local NLI judge.
- `benchmark/reconcile_truth_maintenance.py` (+ `results/reconcile_evidence_gate_tradeoff.json`)
  — the update-recall / false-supersede frontiers.
- `benchmark/sycophancy_mem.py`, `benchmark/sycophancy_bench.py` — the cave-rate.
