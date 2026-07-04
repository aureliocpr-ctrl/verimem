"""Benchmark the Tier-2 consolidation triage (assess_claim_trust + LLMJudge) — the
documented gate before wiring it into consolidation. Labeled set of SPECIFIC unsourced
claims: DURABLE (worth keeping) vs NOISE (coincidental/ephemeral). Metric: does the judge
DECLASS the noise (recall) WITHOUT declassing the durable (false-declass, must be ~0)?
Serial claude -p.

    python -m benchmark.tier2_triage_eval --out benchmark/results/tier2_triage.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# Specific (quantity/year) + unsourced so the judge is consulted (not pass-through).
DURABLE = [
    "The production cache holds 1024 entries.",
    "The API rate limit is 100 requests per minute.",
    "The deployment uses PostgreSQL 16.",
    "Maria's blood type is AB negative.",
    "The warranty period is 3 years.",
    "The service listens on port 8080.",
    "The company was founded in 2015.",
    "The device operates at 12 volts.",
    "The user's monthly budget is 500 euros.",
    "The building has 14 floors.",
    "The contract renews every 24 months.",
    "The satellite's orbital period is 90 minutes.",
]
NOISE = [
    "The loop ran 3 steps before exiting this time.",
    "The hook took 50 ms on that run.",
    "There were 7 retries in that particular log.",
    "The function returned after 12 iterations in this trace.",
    "The test printed 42 lines of output just now.",
    "The request took 230 ms on this attempt.",
    "The batch processed 5 items in that pass.",
    "The gemini call failed once at 05:05 today.",
    "The script slept 2 seconds between those polls.",
    "The buffer had 8 bytes left in that moment.",
    "The pipeline restarted 4 times during the demo.",
    "The cursor was at column 17 when it crashed.",
]


# HARD, DISJOINT set (adversarial-review holes #3/#4): noise WITHOUT temporal tell-words,
# durable WITH numbers that could look transient — forces meaning-based discrimination, not
# surface-cue matching. None of these appear in the (now generic) judge prompt.
HARD_DURABLE = [
    "The database connection pool maxes at 20 connections.",
    "The user is 34 years old.",
    "The engineering team has 8 people.",
    "The license permits 5 seats.",
    "The request timeout is set to 30 seconds.",
    "The user's PIN is 6 digits.",
    "The plan includes 100 GB of storage.",
    "The SLA target is 99.9 percent uptime.",
    "The default page size is 50 results.",
    "The thermostat is set to 21 degrees.",
    "The car's tank holds 55 litres.",
    "The mortgage term is 25 years.",
]
HARD_NOISE = [
    "The batch processed 5 items.",
    "The buffer had 8 bytes free.",
    "The queue held 3 jobs.",
    "The response came back in 230 ms.",
    "CPU sat at 47 percent.",
    "The function returned 12.",
    "The log had 42 lines.",
    "The cursor was at column 17.",
    "There were 4 idle workers.",
    "The retry count reached 7.",
    "The cache miss ratio was 0.3.",
    "The thread pool used 6 threads.",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hard", action="store_true",
                    help="use the harder DISJOINT set (no surface tell-words)")
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    from benchmark.qa_runner import LeanClaudeCLILLM
    from engram.semantic import Fact
    from engram.tier2_judge import LLMJudge, assess_claim_trust

    judge = LLMJudge(LeanClaudeCLILLM(model=a.model, timeout_s=a.timeout))
    durable_set, noise_set = (HARD_DURABLE, HARD_NOISE) if a.hard else (DURABLE, NOISE)

    def declassed(prop: str, topic: str) -> bool | None:
        f = Fact(proposition=prop, topic=topic, confidence=0.8)
        try:
            d = assess_claim_trust(f, corpus=[], judge=judge, enabled=True)
        except Exception:  # noqa: BLE001
            return None
        return d.action == "declass"

    noise_res = [declassed(p, "diary/run") for p in noise_set]
    dur_res = [declassed(p, "infra") for p in durable_set]
    noise_ok = [x for x in noise_res if x is not None]
    dur_ok = [x for x in dur_res if x is not None]

    res = {
        "noise_n": len(noise_ok), "durable_n": len(dur_ok),
        "declass_recall_on_noise": round(sum(noise_ok) / len(noise_ok), 4) if noise_ok else None,
        "false_declass_on_durable": round(sum(dur_ok) / len(dur_ok), 4) if dur_ok else None,
        "note": "declass_recall = noise correctly DECLASSed (want HIGH); false_declass = "
                "durable wrongly DECLASSed (want ~0). assess_claim_trust + LLMJudge on "
                "specific-unsourced-uncorroborated claims. The gate to wiring tier2 into "
                "consolidation.",
    }
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
