"""One-shot (idempotent) entity-graph backfill from the live corpus.

Entity-live step 3: runs the zero-API populate pipeline over
~/.engram/semantic/semantic.db into the live entity KG, prints stats,
then proves the point with a real PPR query. Re-runnable: store/link/
edge are all idempotent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engram.entity_kg import EntityStore  # noqa: E402
from engram.entity_populate import populate_entity_graph  # noqa: E402

SEM = Path.home() / ".engram" / "semantic" / "semantic.db"


def main() -> int:
    kg = EntityStore()  # default: <data_dir>/entity_kg/entity_kg.db
    before = kg.count()
    stats = populate_entity_graph(SEM, kg)
    print("BACKFILL:", json.dumps(stats, indent=1))
    print(f"entities: {before} -> {kg.count()}")

    # Live proof: PPR from a real entity should surface real facts.
    for probe in ("Engram", "reranker", "community_detector", "LongMemEval"):
        e = kg.get_by_name(probe)
        if e is None:
            print(f"probe {probe!r}: not in KG")
            continue
        out = kg.ppr([e.id], k=8)
        print(f"probe {probe!r}: graph={out['graph_size']} "
              f"facts_hit={len(out['facts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
