"""Does the write-path defend collusion WITHOUT punishing dense honest corroboration?

The sellability question for the shipped auto-confirmation: raw independence catches a
copy-cartel, but raw agreement is CONFOUNDED by shared truth — N honest sources that
independently assert the SAME true facts also look like copies, so raw independence
collapses them and their corroboration is LOST. This probes the trade-off on the REAL
gate (Memory.add + store() auto-confirm), across three acceptance signals:

  raw              independence via report-vector agreement (no audit)
  deconf_noanchor  P88 deconfound but NO audit anchors yet (fail-open)
  deconf_anchor    P88 deconfound WITH the cartel's values audit-marked false

Pre-registered expectation (the two-channel thesis) and what the data REFUTED/kept:
  * raw            -> predicted cartel LOW; MEASURED cartel HIGH (~0.85). REFUTED: on
                     UNCONTESTED topics (no honest opposition, no audit) a copy-cartel
                     rides a COLD-START window of ~_COPY_MIN_SHARED writes and gets
                     confirmed before it is detectable as copies. But raw DOES
                     under-credit the honest (0.81 vs 0.91) — the false-merge caveat is
                     REAL: after cold start, identical honest sources are merged.
  * deconf_noanchor-> honest HIGH (protected) but cartel HIGH (~0.94) — toothless. KEPT.
  * deconf_anchor  -> honest HIGH (0.91) AND cartel the LOWEST (~0.78): the two channels
                     are uniquely best, KEPT — but the cartel is SUPPRESSED, not crushed,
                     by the same ~_COLLUSION_MIN_SHARED cold-start.
Bottom line for sellability: the write-path independence defends CONTESTED facts (world
harness: honest contradict the cartel -> cartel crushed 0.15) and the two-channel
deconfound+audit is uniquely best, but there is a real COLD-START window on uncontested
copy-runs that only accumulated history, honest opposition, or an EARLIER audit closes.

    python -m benchmark.independence_dense_honest
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from statistics import mean

RESULTS_DIR = Path(__file__).parent / "results"
_NEUTRAL = 0.5
_N_HONEST = 3
_N_CARTEL = 5
_N_TOPICS = 6          # per group; >= 3 so report vectors can identify copies


def _run(condition: str) -> dict:
    os.environ["ENGRAM_SOURCE_TRUST"] = "1"
    os.environ["ENGRAM_SOURCE_AUTO_CONFIRM"] = "1"
    os.environ["ENGRAM_SOURCE_INDEPENDENCE"] = "1"
    os.environ["ENGRAM_SOURCE_INDEPENDENCE_DECONFOUND"] = (
        "1" if condition.startswith("deconf") else "0")
    os.environ["ENGRAM_RECONCILE_ON_WRITE"] = "0"
    from engram.client import Memory
    from engram.source_trust import reset_book_cache
    reset_book_cache()
    honest = [f"honest_{i}" for i in range(_N_HONEST)]
    cartel = [f"cartel_{i}" for i in range(_N_CARTEL)]
    htopics = [f"consensus/h{i}" for i in range(_N_TOPICS)]
    ctopics = [f"consensus/c{i}" for i in range(_N_TOPICS)]
    hprop = {t: f"The true value of {t} is stable_{i}." for i, t in enumerate(htopics)}
    cprop = {t: f"The value of {t} is fabricated_{i}." for i, t in enumerate(ctopics)}

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        mem = Memory(Path(td) / "m.db")
        # deconf_anchor: the outcome/audit has ALREADY revealed the cartel's values
        # false (fed before the writes so the deconfound bites during auto-confirm).
        if condition == "deconf_anchor":
            for t in ctopics:
                mem.source_trust_observe(audited_false=(t, cprop[t]))
        # dense honest consensus: every honest source asserts the SAME true facts
        for t in htopics:
            for s in honest:
                mem.add(hprop[t], topic=t, verified_by=[f"source-doc:{s}:1"])
        # copy cartel: every colluder asserts the SAME false facts
        for t in ctopics:
            for s in cartel:
                mem.add(cprop[t], topic=t, verified_by=[f"source-doc:{s}:1"])
        hon = mean(mem.consistency_trust(s) for s in honest)
        car = mean(mem.consistency_trust(s) for s in cartel)
    return {"honest_consistency": round(hon, 4), "cartel_consistency": round(car, 4)}


def main() -> None:
    res = {c: _run(c) for c in ("raw", "deconf_noanchor", "deconf_anchor")}
    raw, noanchor, anchor = res["raw"], res["deconf_noanchor"], res["deconf_anchor"]
    verdict = {
        # the false-merge caveat is REAL: raw under-credits dense honest vs deconfound
        "raw_undercredits_honest":
            raw["honest_consistency"] < anchor["honest_consistency"] - 0.05,
        # deconfound WITHOUT the audit is toothless on the cartel
        "noanchor_toothless": noanchor["cartel_consistency"] >= 0.85,
        # the two channels together are uniquely best: honest protected AND cartel the
        # most suppressed of the three
        "two_channels_best":
            (anchor["honest_consistency"] >= 0.85
             and anchor["cartel_consistency"] < noanchor["cartel_consistency"]
             and anchor["cartel_consistency"] <= raw["cartel_consistency"]),
        # honest limit named, not hidden: the cartel is suppressed, NOT crushed, by the
        # cold-start window on uncontested copy-runs
        "cold_start_residual_cartel": anchor["cartel_consistency"] > 0.6,
    }
    report = {"config": {"n_honest": _N_HONEST, "n_cartel": _N_CARTEL,
                         "n_topics": _N_TOPICS},
              "results": res, "verdict": verdict,
              "note": "REFUTED the naive 'raw crushes the cartel' on UNCONTESTED topics: "
                      "a cold-start window (~_COPY_MIN_SHARED writes) confirms copies "
                      "before detection. Two-channel deconfound+audit is uniquely best "
                      "(honest protected, cartel most suppressed) but suppresses rather "
                      "than crushes; the write-path defends CONTESTED facts strongly "
                      "(world harness: cartel 0.15). Motivates the outcome->audit loop "
                      "and a new-source probation.",
              "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    print(json.dumps(report, indent=2))
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"independence_dense_honest_{time.strftime('%Y-%m-%d')}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
