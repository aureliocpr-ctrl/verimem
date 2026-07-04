"""Comparative belief-integrity benchmark: Engram truth-maintenance vs mem0/Zep-style baselines.

THE HONEST SCOPE (read before quoting any number):
- We CANNOT run mem0/Zep here (external API keys; O4/O5 subscription-only). So we faithfully
  REIMPLEMENT their PUBLISHED retraction semantics and measure the gap to ours. This is a
  comparison of RETRACTION POLICY, not of full systems (their retrieval quality, latency,
  graph reasoning etc. are out of scope and NOT claimed).
- The corpus is SYNTHETIC with CONSTRUCTED derivation chains, because the real Engram corpus
  has no typed logical-derivation edges yet (R26/R27). So this measures the value of
  transitive cascade IN THE REGIME IT IS DESIGNED FOR: a corpus where a fact's truth genuinely
  depends on its parents and foundations get superseded/contradicted/expire over time. On a
  corpus WITHOUT such derivations (like today's real one) the gap is 0 — stated plainly.

Models (retraction policy only; all see the same stored facts):
- naive_recency  (mem0-style): keep every stored fact except one directly overwritten by a
                  newer version (supersession). No contradiction/expiry/cascade handling.
- edge_invalidation (Zep/Graphiti-style): bi-temporal — invalidate a fact directly on
                  supersession OR contradiction OR expiry. NO propagation to derived facts.
- engram_tms     (this work): admission + maintain + propagate (ATMS transitive cascade):
                  a fact is retracted when ANY fact it transitively derives from is invalid.

Ground truth: a fact is CURRENTLY TRUE iff it is not itself superseded/contradicted/expired
AND all its (transitive) derivation parents are currently true. Metric = JBI (of served
beliefs, the fraction actually currently true) + valid-recall (of currently-true facts, the
fraction still served — guards against winning by over-retraction). Deterministic, no LLM.
"""
from __future__ import annotations

import argparse
import json
import random
from typing import Any

from engram.justified_memory import Belief, maintain, propagate, served

_NOW = 1000.0


def _mean_ci(xs: list[float]) -> tuple[float, float, float]:
    """Mean + 95% percentile bootstrap CI across seeds (no scipy)."""
    xs = sorted(xs)
    n = len(xs)
    mean = sum(xs) / n if n else 0.0
    if n < 2:
        return round(mean, 4), round(mean, 4), round(mean, 4)
    lo = xs[max(0, int(0.025 * n))]
    hi = xs[min(n - 1, int(0.975 * n))]
    return round(mean, 4), round(lo, 4), round(hi, 4)


def build_corpus(n_foundations: int, n_derived: int, *, seed: int,
                 frac_superseded: float = 0.2, frac_contradicted: float = 0.1,
                 frac_stale: float = 0.1, frac_robust: float = 0.0) -> dict[str, Any]:
    """An evolving corpus with real derivation chains: derived facts depend on 1-2 EARLIER
    facts (a DAG, no cycles). A fraction is then superseded / contradicted / staled.

    ``frac_robust``: fraction of DERIVED facts whose truth does NOT actually depend on their
    parents (supersession != refutation, R26) — they stay true even if a parent is falsified.
    ``propagate`` cannot tell these apart from hard derivations (it has only the edge), so it
    OVER-RETRACTS them — this is engram's recall COST, the honest counter to the otherwise
    near-tautological JBI=1.0. With typed edges (R26/R27) the writer would mark these soft."""
    rng = random.Random(seed)
    beliefs: list[Belief] = []
    for i in range(n_foundations):
        beliefs.append(Belief(f"F{i}", f"foundation {i}", f"src{i}", 95.0, "believed"))
    robust: set[str] = set()
    for j in range(n_derived):
        k = rng.randint(1, 2)
        parents = tuple(rng.choice(beliefs).id for _ in range(k))
        bid = f"D{j}"
        if rng.random() < frac_robust:
            robust.add(bid)
        beliefs.append(Belief(bid, f"derived {j}", "inferred", 95.0, "believed",
                              depends_on=parents))
    ids = [b.id for b in beliefs]
    rng.shuffle(ids)
    n_sup = int(frac_superseded * len(ids))
    n_con = int(frac_contradicted * len(ids))
    n_sta = int(frac_stale * len(ids))
    superseded = set(ids[:n_sup])
    contradicted = set(ids[n_sup:n_sup + n_con])
    stale = set(ids[n_sup + n_con:n_sup + n_con + n_sta])
    beliefs = [b if b.id not in stale else Belief(b.id, b.proposition, b.source,
               b.grounding_score, "believed", valid_until=500.0, depends_on=b.depends_on)
               for b in beliefs]
    return {"beliefs": beliefs, "superseded": superseded,
            "contradicted": contradicted, "stale": stale, "robust": robust}


def _currently_true(beliefs: list[Belief], bad: set[str], robust: set[str]) -> set[str]:
    by_id = {b.id: b for b in beliefs}
    memo: dict[str, bool] = {}

    def is_true(bid: str) -> bool:
        if bid in memo:
            return memo[bid]
        if bid in bad:
            memo[bid] = False
            return False
        memo[bid] = True  # guard (DAG, no cycles); set before recursion is safe here
        if bid in robust:                       # truth independent of parents (soft edge)
            return True
        memo[bid] = all(is_true(d) for d in by_id[bid].depends_on if d in by_id)
        return memo[bid]

    return {b.id for b in beliefs if is_true(b.id)}


def _jbi(served_ids: set[str], truth: set[str]) -> float:
    return 1.0 if not served_ids else len(served_ids & truth) / len(served_ids)


def _recall(served_ids: set[str], truth: set[str]) -> float:
    return 1.0 if not truth else len(served_ids & truth) / len(truth)


def run_once(*, n_foundations: int, n_derived: int, seed: int,
             frac_robust: float = 0.0) -> dict[str, Any]:
    c = build_corpus(n_foundations, n_derived, seed=seed, frac_robust=frac_robust)
    beliefs, sup, con, sta = c["beliefs"], c["superseded"], c["contradicted"], c["stale"]
    expired = {b.id for b in beliefs if b.valid_until is not None and _NOW >= b.valid_until}
    bad = sup | con | expired
    truth = _currently_true(beliefs, bad, c["robust"])

    naive = {b.id for b in beliefs if b.id not in sup}                       # mem0-style
    edge = {b.id for b in beliefs if b.id not in bad}                         # Zep-style
    maintained = propagate(maintain(beliefs, now=_NOW, superseded_ids=sup,
                                    contradicted_ids=con), now=_NOW)
    engram = {b.id for b in served(maintained, now=_NOW)}                     # this work

    return {
        "naive_jbi": _jbi(naive, truth), "naive_recall": _recall(naive, truth),
        "edge_jbi": _jbi(edge, truth), "edge_recall": _recall(edge, truth),
        "engram_jbi": _jbi(engram, truth), "engram_recall": _recall(engram, truth),
        "n_facts": len(beliefs), "n_true": len(truth),
    }


def run(*, n_foundations: int = 60, n_derived: int = 140, seeds: int = 20,
        frac_robust: float = 0.0) -> dict[str, Any]:
    rows = [run_once(n_foundations=n_foundations, n_derived=n_derived, seed=s,
                     frac_robust=frac_robust)
            for s in range(seeds)]

    def agg(key: str) -> dict[str, float]:
        m, lo, hi = _mean_ci([r[key] for r in rows])
        return {"mean": m, "ci95": [lo, hi]}

    out = {
        "config": {"n_foundations": n_foundations, "n_derived": n_derived, "seeds": seeds,
                   "frac_robust": frac_robust},
        "avg_facts": round(sum(r["n_facts"] for r in rows) / len(rows), 1),
        "avg_true_fraction": round(sum(r["n_true"] / r["n_facts"] for r in rows) / len(rows), 3),
        "naive_recency_mem0_style": {"jbi": agg("naive_jbi"), "valid_recall": agg("naive_recall")},
        "edge_invalidation_zep_style": {"jbi": agg("edge_jbi"), "valid_recall": agg("edge_recall")},
        "engram_tms_this_work": {"jbi": agg("engram_jbi"), "valid_recall": agg("engram_recall")},
    }
    out["jbi_gain_vs_zep_style"] = round(
        out["engram_tms_this_work"]["jbi"]["mean"]
        - out["edge_invalidation_zep_style"]["jbi"]["mean"], 4)
    out["engram_preserves_valid_recall"] = bool(
        out["engram_tms_this_work"]["valid_recall"]["mean"] >= 0.999)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--foundations", type=int, default=60)
    p.add_argument("--derived", type=int, default=140)
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--robust", type=float, default=0.0,
                   help="fraction of derived facts whose truth does NOT depend on parents "
                        "(soft edges) — shows engram's over-retraction recall cost")
    p.add_argument("--out", type=str, default=None)
    a = p.parse_args(argv)
    res = run(n_foundations=a.foundations, n_derived=a.derived, seeds=a.seeds,
              frac_robust=a.robust)
    print(json.dumps(res, indent=2))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_corpus", "run_once", "run", "main"]
