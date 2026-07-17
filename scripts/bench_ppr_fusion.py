"""A/B bench: PPR-fusion recall lift on a controlled wording-mismatch corpus.

Measures recall@k with ENGRAM_PPR_FUSION OFF vs ON on a corpus designed to ISOLATE
the multi-hop / wording-mismatch case the fusion is FOR: each GOLD fact is lexically
far from its query but linked to an entity the query mentions; DECOYS are lexically
close to the query (share its words) but carry NO entity link. A pure-cosine recall
ranks the decoys first and misses the gold; entity-PPR should rescue the gold.

HONEST scope: this is a CONTROLLED MECHANISM bench, not a public benchmark
(LOCOMO/LongMemEval). It measures the lift on the case the feature targets, with the
CE-rerank disabled to isolate the PPR signal (the fusion×rerank fix already ensures
PPR-only facts survive the rerank). Run: python scripts/bench_ppr_fusion.py
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def main() -> None:
    td = Path(tempfile.mkdtemp())
    os.environ["ENGRAM_DATA_DIR"] = str(td)
    os.environ["ENGRAM_RECALL_RERANK"] = "0"  # isolate the PPR signal from the CE
    from verimem.entity_kg import Entity, EntityStore
    from verimem.entity_populate import entity_kg_path_for
    from verimem.semantic import Fact, SemanticMemory

    sm = SemanticMemory(db_path=td / "semantic" / "semantic.db")
    es = EntityStore(db_path=entity_kg_path_for(sm.db_path))

    fillers = [
        "the quarterly budget spreadsheet was archived in spring",
        "minutes of the offsite planning retrospective",
        "a note about the cafeteria menu rotation",
        "summary of the annual compliance training",
        "observations on the parking lot resurfacing",
    ]
    n = 12
    golds: list[tuple[str, str]] = []
    for i in range(n):
        ent = f"servicecomponent{i}"  # CamelCase-free snake-ish token the lite extractor emits
        gold = Fact(proposition=f"{fillers[i % len(fillers)]} reference {i}",
                    topic=f"t/gold/{i}")
        sm.store(gold, embed="sync")
        eid = es.store(Entity(canonical_name=ent, type="module"))
        es.add_edge(eid, eid, "self", weight=1.0)
        es.link_fact(gold.id, eid)
        golds.append((ent, gold.id))
        for d in range(3):
            # Decoys: share the query's GENERIC words ("deployment runbook") to win
            # on cosine, but DO NOT mention the entity token — otherwise the
            # write-path entity extractor links them too and PPR boosts them as well
            # (the entity must be the gold's distinguishing signal, not shared).
            sm.store(Fact(proposition=f"deployment runbook step {d} operational details",
                          topic=f"t/decoy/{i}/{d}"), embed="sync")

    def recall_at(k: int) -> tuple[float, float]:
        off = on = 0
        for ent, gid in golds:
            q = f"{ent} deployment runbook"
            os.environ.pop("ENGRAM_PPR_FUSION", None)
            sm._recall_es = None
            if gid in {f.id for f, _ in sm.recall(q, k=k)}:
                off += 1
            os.environ["ENGRAM_PPR_FUSION"] = "1"
            sm._recall_es = None
            if gid in {f.id for f, _ in sm.recall(q, k=k)}:
                on += 1
        return off / len(golds), on / len(golds)

    print(f"corpus: {n} gold (wording-mismatch, entity-linked) + {n * 3} decoys")
    for k in (3, 5, 10):
        off, on = recall_at(k)
        print(f"  recall@{k}: OFF {off:5.0%}  ->  ON {on:5.0%}   (+{(on - off) * 100:.0f}pp)")


if __name__ == "__main__":
    main()
