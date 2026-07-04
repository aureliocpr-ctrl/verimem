"""The Justified-Belief Integrity (JBI) experiment — the new axis the retrieval-SOTA ignores.

Retrieval accuracy (LoCoMo/LongMemEval, ~92–94%) measures "did you fetch the right chunk".
It does NOT measure "is what you serve still TRUE" after the corpus evolves. We build an
evolving corpus (facts get SUPERSEDED, CONTRADICTED, or go STALE) and compare:
  * naive store  — serves everything it stored (a vector store returns all matches)
  * TMS store    — `engram.justified_memory`: maintains justifications, serves only
                   currently-JUSTIFIED beliefs (retracts superseded, contests contradicted,
                   drops stale)
Metric: JBI = of SERVED beliefs, the fraction actually currently true (higher = better);
plus stale/contradiction/superseded-served rates; plus valid-recall (the TMS must NOT win
by over-retracting valid facts). Deterministic (the lifecycle is logic, not an LLM call).

H-JM1: TMS raises JBI vs naive WITHOUT lowering valid-recall. Falsified if JBI doesn't rise,
or rises only by tanking valid-recall.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from typing import Any

from engram.justified_memory import (
    Belief,
    justified_belief_integrity,
    maintain,
    propagate,
    served,
)

_NOW = 1000.0


def build_corpus(n: int = 24) -> dict[str, Any]:
    """An evolving corpus: 1/4 superseded, 1/6 contradicted, 1/6 staled, rest still valid."""
    beliefs: list[Belief] = []
    truth: set[str] = set()
    superseded: list[str] = []
    contradicted: list[str] = []
    for i in range(n):
        bid = f"f{i}"
        b = Belief(bid, f"fact {i} value", f"source for {i}", 95.0, "believed")
        if i % 4 == 0:                       # superseded by a newer fact -> false now
            superseded.append(bid)
        elif i % 4 == 1:                     # contradicted -> not servable as truth
            contradicted.append(bid)
        elif i % 4 == 2:                     # expired before now -> stale
            b = replace(b, valid_until=500.0)
        else:                                # still valid
            truth.add(bid)
        beliefs.append(b)
    return {"beliefs": beliefs, "truth": truth, "superseded": superseded,
            "contradicted": contradicted}


def _rates(served_list: list[Belief], superseded: set[str], contradicted: set[str],
           expired_ids: set[str], truth: set[str]) -> dict[str, Any]:
    n = len(served_list)
    if n == 0:
        return {"served": 0, "jbi": 1.0, "stale_served": 0.0, "contradiction_served": 0.0,
                "superseded_served": 0.0}
    sid = [b.id for b in served_list]
    return {
        "served": n,
        "jbi": round(justified_belief_integrity(served_list, truth), 3),
        "superseded_served": round(sum(i in superseded for i in sid) / n, 3),
        "contradiction_served": round(sum(i in contradicted for i in sid) / n, 3),
        "stale_served": round(sum(i in expired_ids for i in sid) / n, 3),
    }


def run(n: int = 24) -> dict[str, Any]:
    c = build_corpus(n)
    beliefs, truth = c["beliefs"], c["truth"]
    sup, con = set(c["superseded"]), set(c["contradicted"])
    expired = {b.id for b in beliefs if b.valid_until is not None and _NOW >= b.valid_until}

    # naive store: serves everything it stored (no maintenance, no grounding lifecycle)
    naive_served = list(beliefs)
    # TMS store: maintain (leaf statuses) then propagate (ATMS dependency cascade), serve
    maintained = propagate(maintain(beliefs, now=_NOW, superseded_ids=sup,
                                    contradicted_ids=con), now=_NOW)
    tms_served = served(maintained, now=_NOW)

    def valid_recall(served_list: list[Belief]) -> float:
        got = {b.id for b in served_list} & truth
        return round(len(got) / len(truth), 3) if truth else 1.0

    naive = _rates(naive_served, sup, con, expired, truth)
    naive["valid_recall"] = valid_recall(naive_served)
    tms = _rates(tms_served, sup, con, expired, truth)
    tms["valid_recall"] = valid_recall(tms_served)
    return {
        "n_facts": n, "n_truth": len(truth),
        "naive_store": naive, "tms_store": tms,
        "jbi_gain": round(tms["jbi"] - naive["jbi"], 3),
        "valid_recall_preserved": bool(tms["valid_recall"] >= naive["valid_recall"]),
        "H_JM1_holds": bool(tms["jbi"] > naive["jbi"] and tms["valid_recall"] >= naive["valid_recall"]),
    }


def run_transitive() -> dict[str, Any]:
    """Where propagate() EARNS its novelty: a chain F0 -> {D1,D2} -> D3 with F0 superseded.
    maintain/supersede ALONE (what mem0/Zep/NeuSymMS ship) retracts F0 but KEEPS D1/D2/D3 —
    facts derived from a now-false foundation, served as truth. ATMS propagate() cascades
    the retraction. This isolates the capability the SOTA lacks."""
    beliefs = [
        Belief("F0", "foundation value", "src0", 95.0, "believed"),
        Belief("D1", "derived from F0", "infer", 95.0, "believed", depends_on=("F0",)),
        Belief("D2", "also from F0", "infer", 95.0, "believed", depends_on=("F0",)),
        Belief("D3", "from D1 (chain)", "infer", 95.0, "believed", depends_on=("D1",)),
        Belief("V1", "independent valid", "srcV1", 95.0, "believed"),
        Belief("V2", "independent valid", "srcV2", 95.0, "believed"),
    ]
    truth = {"V1", "V2"}  # F0 superseded -> false; D1/D2/D3 derive from it -> false
    maint_only = maintain(beliefs, now=_NOW, superseded_ids={"F0"})
    served_maint = served(maint_only, now=_NOW)
    served_prop = served(propagate(maint_only, now=_NOW), now=_NOW)

    def _jbi(s: list[Belief]) -> float:
        return round(justified_belief_integrity(s, truth), 3)

    return {
        "naive_jbi": _jbi(beliefs),                       # serve everything
        "maintain_only_jbi": _jbi(served_maint),          # supersession alone (SOTA)
        "propagate_jbi": _jbi(served_prop),               # + ATMS cascade (novel core)
        "maintain_only_served": sorted(b.id for b in served_maint),
        "propagate_served": sorted(b.id for b in served_prop),
        "cascade_retracted": sorted({"D1", "D2", "D3"} - {b.id for b in served_prop}),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Justified-Belief Integrity experiment.")
    p.add_argument("--n", type=int, default=24)
    p.add_argument("--out", type=argparse.FileType("w"), default=None)
    args = p.parse_args(argv)
    res = run(args.n)
    res["transitive"] = run_transitive()
    print(json.dumps(res, indent=2))
    if args.out:
        json.dump(res, args.out, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_corpus", "run", "run_transitive", "main"]
