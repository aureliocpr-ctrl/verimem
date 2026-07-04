"""bench: hallucination-rate@k — the anti-confab moat, made into a number.

The dangerous case for any memory: the fact MOST relevant to the query (highest
cosine) is itself unreliable — a never-verified model_claim, or a retracted fact.
A bare vector store (mem0-class: cosine top-k, no status / supersession /
contradiction) returns it with NO signal, so the caller can't tell it apart from
ground truth. Engram attaches a live trust verdict to every hit and filters the
retracted ones out of the window entirely.

This bench builds a corpus where the strongest matches ARE the unreliable facts,
then reports two numbers over the SAME store, SAME embedder:

  (A) Engram recall      — retracted facts filtered out; each surviving hit
                           carries a trust_signal, so risk is VISIBLE.
  (B) cosine-only / mem0  — include_superseded/orphaned=True (no status filter):
                           the retracted rows re-enter the top-k, the way a bare
                           vector store returns them.

hallucination-rate@k = fraction of the top-k whose verdict is RISKY
(obsolete/contested/unverified). For (B) it is the risk a mem0-class store would
hand back unflagged; for (A) it is what survives Engram's filter — and, unlike
mem0, Engram also TELLS the caller which hits those are.

Run: python scripts/bench_hallucination_rate.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from engram.hallucination_rate import _RISKY_VERDICTS, hallucination_rate_at_k
from engram.semantic import Fact, SemanticMemory

K = 5


def _topk(sm: SemanticMemory, query: str, k: int, **recall_kw) -> dict:
    hits = sm.recall(query, k=k, trust_signals=True, **recall_kw)
    verdicts = [h[2].verdict for h in hits if len(h) >= 3]
    risky = sum(1 for v in verdicts if v in _RISKY_VERDICTS)
    rate = (risky / len(verdicts)) if verdicts else 0.0
    return {"n": len(verdicts), "risky": risky, "rate": rate, "verdicts": verdicts}


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        sm = SemanticMemory(db_path=Path(td) / "bench" / "s.db")
        q = "redis maxmemory eviction policy setting"

        # The 3 STRONGEST matches to the query are unreliable:
        #  - 1 retracted (superseded) fact that was the old answer
        #  - 2 never-verified low-confidence model_claims
        old = Fact(proposition="redis maxmemory eviction policy setting is volatile-lru",
                   topic="ops", status="model_claim", confidence=0.5, source_episodes=["e"])
        sm.store(old, embed="sync")
        superseder = Fact(
            proposition="the cache eviction approach was revised last quarter",
            topic="ops", status="verified", confidence=0.95, source_episodes=["e"])
        sm.store(superseder, embed="sync")
        sm.supersede(old.id, superseder.id, reason="policy revised")

        for i, val in enumerate(("allkeys-lfu", "noeviction")):
            sm.store(Fact(
                proposition=f"redis maxmemory eviction policy setting might be {val}",
                topic="ops", status="model_claim", confidence=0.3,
                source_episodes=["e"]), embed="sync")

        # plus a handful of verified, weaker-matching facts to fill the window
        for i in range(4):
            sm.store(Fact(proposition=f"redis is deployed in cluster mode zone {i}",
                          topic="ops", status="verified", confidence=0.95,
                          source_episodes=["e"]), embed="sync")

        a = _topk(sm, q, K)
        b = _topk(sm, q, K, include_superseded=True, include_orphaned=True,
                  include_conversational=True)
        eng = hallucination_rate_at_k(sm, [q], k=K)

        print("=" * 66)
        print("hallucination-rate@k — Engram (gate ON) vs cosine-only (mem0-class)")
        print("=" * 66)
        print(f"query: {q!r}   k={K}")
        print("corpus: 3 strongest matches are unreliable (1 retracted + 2 low-conf)")
        print()
        print(f"(A) Engram recall     : rate@{K} = {a['rate']:.3f}   "
              f"({a['risky']}/{a['n']} risky in top-k)")
        print(f"    verdicts          : {a['verdicts']}")
        print(f"    full breakdown    : {eng['verdict_breakdown']}")
        print()
        print(f"(B) cosine-only/mem0  : rate@{K} = {b['rate']:.3f}   "
              f"({b['risky']}/{b['n']} risky in top-k)")
        print(f"    verdicts          : {b['verdicts']}")
        print()
        print(f">>> retracted facts Engram filtered from the top-k: "
              f"{b['verdicts'].count('obsolete') - a['verdicts'].count('obsolete')}")
        print(f">>> Engram still FLAGS its {a['risky']} risky hit(s) to the caller; "
              f"a cosine store returns them unlabeled (risk invisible).")
        print("=" * 66)


if __name__ == "__main__":
    main()
