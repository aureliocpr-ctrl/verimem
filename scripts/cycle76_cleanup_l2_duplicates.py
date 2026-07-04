"""Cycle #76 - L2 semantic-duplicate cleanup script.

Empirical baseline (audit cycle #75 2026-05-15 post-L1):
  - hippo_find_duplicate_facts(threshold=0.7) returns 5 clusters
    containing 30 facts in dup pairs / chains:
      cluster 1: "Stub rationale for bench" x18 (max_sim=1.0)
      cluster 2: "consistent endpoint pattern" x6 (max_sim=1.0)
      cluster 3: AUTOCRITICA verificata 2026-05-14 x2 (max_sim=0.748)
      cluster 4: NEXUS bug fix Phase 4.6 x2 (max_sim=0.754)
      cluster 5: Aurelio account piancopallo@x.it x2 (max_sim=0.833)

Two cluster categories — handle differently:

  - PURE POLLUTION (proposition is short boilerplate/test-fixture,
    e.g. "Stub rationale for bench", "consistent endpoint pattern"):
    delete ALL members. They carry no information and were inserted
    by automated test runs or pattern-injection.

  - KNOWLEDGE DUPLICATES (proposition is real content, paraphrased
    twice): keep the BEST representative, union its source_episodes
    with the others', delete the rest. Best = highest confidence,
    tiebreak by longest proposition, then earliest created_at.

Heuristic for "pure pollution":
  - proposition length < 50 chars AND
  - all members of the cluster have identical proposition

Usage:
  python scripts/cycle76_cleanup_l2_duplicates.py            # dry-run
  python scripts/cycle76_cleanup_l2_duplicates.py --apply    # write

Backup the DB before --apply.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from engram.find_duplicate_facts import find_duplicate_facts
from engram.semantic import Fact, SemanticMemory  # noqa: F401  (kept for callers)

# ---------------------------------------------------------------------------
# Pure helpers (testable)
# ---------------------------------------------------------------------------


def is_pure_pollution_cluster(propositions: list[str]) -> bool:
    """A cluster is pure pollution if all propositions are identical
    AND under 50 chars (boilerplate/test fixture)."""
    if not propositions:
        return False
    first = (propositions[0] or "").strip()
    if len(first) >= 50:
        return False
    return all((p or "").strip() == first for p in propositions)


def pick_representative(facts: list[Any]) -> Any:
    """Return the fact to KEEP. Ranking:
      1. highest confidence
      2. longest proposition (more detail)
      3. earliest created_at (oldest survives)
    """
    if not facts:
        raise ValueError("empty cluster")
    def _key(f: Any) -> tuple[float, int, float]:
        # Negate where larger-is-better so we can sort ascending.
        return (
            -float(getattr(f, "confidence", 0.0)),
            -len(getattr(f, "proposition", "") or ""),
            float(getattr(f, "created_at", 0.0)),
        )
    return sorted(facts, key=_key)[0]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.7,
                    help="Jaccard threshold for cluster detection.")
    ap.add_argument("--db", default=None)
    args = ap.parse_args()

    db_path = Path(args.db) if args.db else Path(
        os.path.expanduser("~/.engram/semantic/semantic.db")
    )
    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}", file=sys.stderr)
        return 1

    print(f"DB: {db_path}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print()

    mem = SemanticMemory(db_path=db_path)
    all_facts = mem.list_facts(limit=20000, offset=0)
    print(f"Loaded {len(all_facts)} facts")

    # find_duplicate_facts returns pairs, not clusters. Build clusters
    # via union-find on the pairs.
    result = find_duplicate_facts(
        all_facts, threshold=args.threshold, top_k=10000,
    )
    print(f"Found {len(result['pairs'])} dup pairs at threshold {args.threshold}")

    # Union-find
    parent: dict[str, str] = {}
    def find(x: str) -> str:
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x
    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for p in result["pairs"]:
        a, b = p["fact_a"], p["fact_b"]
        parent.setdefault(a, a)
        parent.setdefault(b, b)
        union(a, b)

    by_id = {f.id: f for f in all_facts}
    clusters: dict[str, list[str]] = {}
    for fid in parent:
        root = find(fid)
        clusters.setdefault(root, []).append(fid)

    print(f"Clusters built: {len(clusters)}")
    print()

    to_delete: list[str] = []
    to_merge_keeper: list[tuple[str, list[str]]] = []  # (keeper_id, others_to_delete)

    for root, ids in clusters.items():
        ids = sorted(set(ids))
        if len(ids) < 2:
            continue
        facts = [by_id[i] for i in ids if i in by_id]
        if not facts:
            continue
        propositions = [f.proposition for f in facts]
        first_prop = (propositions[0] or "")[:60]

        if is_pure_pollution_cluster(propositions):
            # delete ALL
            to_delete.extend(f.id for f in facts)
            print(f"  POLLUTION cluster ({len(facts)} facts): delete ALL — "
                  f"sample={first_prop!r}")
        else:
            keeper = pick_representative(facts)
            others = [f.id for f in facts if f.id != keeper.id]
            to_merge_keeper.append((keeper.id, others))
            print(f"  KNOWLEDGE cluster ({len(facts)} facts): keep "
                  f"{keeper.id[:12]} delete {len(others)} — "
                  f"sample={first_prop!r}")

    print()
    print(f"Total pure-pollution to DELETE: {len(to_delete)}")
    print(f"Total knowledge-dup to MERGE+DELETE: "
          f"{sum(len(o) for _, o in to_merge_keeper)} "
          f"across {len(to_merge_keeper)} clusters")
    print()

    if not args.apply:
        print("DRY-RUN — no DB writes. Re-run with --apply to commit.")
        return 0

    # APPLY
    n_deleted = 0
    for fid in to_delete:
        try:
            mem.delete(fid)
            n_deleted += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  delete failed id={fid}: {exc}")

    # Merge knowledge clusters: union source_episodes into keeper,
    # then delete the others.
    for keeper_id, others in to_merge_keeper:
        keeper = by_id.get(keeper_id)
        if keeper is None:
            continue
        combined_eps = list(keeper.source_episodes)
        for oid in others:
            other = by_id.get(oid)
            if other is None:
                continue
            for ep in other.source_episodes:
                if ep not in combined_eps:
                    combined_eps.append(ep)
        # rewrite keeper with union source_episodes (INSERT OR REPLACE)
        # rescan2 fix 2026-06-02: replace() preserva la provenance (stesso bug
        # di cycle75) — ricostruire Fact() campo-per-campo azzerava
        # status / verified_by / superseded_by / writer_role / ... al re-store.
        new_keeper = replace(keeper, source_episodes=combined_eps)
        mem.store(new_keeper)
        for oid in others:
            try:
                mem.delete(oid)
                n_deleted += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  delete failed id={oid}: {exc}")

    print(f"Deleted: {n_deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
