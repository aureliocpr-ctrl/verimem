"""Truth-maintenance scan of the REAL live corpus with the LOCAL NLI judge —
read-only. The "evolving facts" differentiator applied to the second brain itself,
zero claude -p.

For every live-fact pair above a cosine pre-filter, the LocalRelationJudge
classifies contradiction / entailment / neutral (both directions). Timestamps then
split the NLI-contradictions the way the claude judge's timestamp prompt did
(BENCHMARKS: contradiction-FPR 0.10→0.0125 with stamps):

  * EVOLUTION — contradiction with a clear temporal order (Δt > --same-time-s):
    the world moved on; candidate for superseding the OLDER fact with the newer.
  * CONFLICT — contradiction asserted at ~the same time: no winner by time alone;
    surface for review.
  * DUPLICATE — bidirectional entailment: same assertion twice; merge candidate.

Output: JSON report (counts + every pair with ids/topics/Δt/cosine) + a readable
top-N per category. NO mutation of any kind — the resolve step is a separate,
explicit decision informed by this report.

    python -m benchmark.corpus_truth_scan_local --out benchmark/results/corpus_truth_scan.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path

import numpy as np

from engram._telemetry_prefixes import classify_tier

#: The judge reads knowledge only unless told otherwise: the night-2 scan showed
#: the residual NLI conflicts were telemetry near-duplicates, not knowledge.
_DEFAULT_TIERS = frozenset({"knowledge"})

_DB = Path.home() / ".engram" / "semantic" / "semantic.db"


def _tier_selection(topics, tiers):
    """Pure selection: indices whose topic classifies into ``tiers`` + the full
    tier composition (every row counted, selected or not)."""
    comp: dict[str, int] = {}
    sel: list[int] = []
    for i, t in enumerate(topics):
        tier = classify_tier(t)
        comp[tier] = comp.get(tier, 0) + 1
        if tier in tiers:
            sel.append(i)
    return sel, comp


def _load_live(db: Path, tiers: frozenset[str] = _DEFAULT_TIERS):
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, proposition, topic, created_at, length(embedding) AS elen, "
        "embedding FROM facts WHERE (superseded_by IS NULL OR superseded_by='') "
        "AND proposition != ''").fetchall()
    con.close()
    sel, composition = _tier_selection([r["topic"] for r in rows], tiers)
    in_tier = [rows[i] for i in sel]
    # uniform-length guard (the frombuffer reshape needs it); report what we drop
    lens: dict[int, int] = {}
    for r in in_tier:
        lens[r["elen"]] = lens.get(r["elen"], 0) + 1
    main_len = max(lens, key=lambda k: lens[k]) if lens else 0
    kept = [r for r in in_tier if r["elen"] == main_len]
    dropped_len = sum(v for k, v in lens.items() if k != main_len)
    emb = np.frombuffer(b"".join(r["embedding"] for r in kept),
                        dtype=np.float32).reshape(len(kept), -1).copy()
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    emb /= norms
    return kept, emb, {"total_rows": len(rows), "kept": len(kept),
                       "tiers_scanned": sorted(tiers),
                       "tier_composition": composition,
                       "dropped_nonuniform_emb": dropped_len,
                       "emb_dim": emb.shape[1] if len(kept) else 0}


def _candidate_pairs(emb: np.ndarray, min_cosine: float, block: int = 512):
    """Yield (i, j, cos) for i<j with cosine >= min_cosine, blockwise."""
    n = emb.shape[0]
    for a in range(0, n, block):
        sims = emb[a:a + block] @ emb.T  # (b, n)
        for bi in range(sims.shape[0]):
            i = a + bi
            row = sims[bi]
            js = np.nonzero(row >= min_cosine)[0]
            for j in js:
                if j > i:
                    yield i, int(j), float(row[j])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(_DB))
    ap.add_argument("--min-cosine", type=float, default=0.86,
                    help="pre-filter (same default as collect_contradicted_ids)")
    ap.add_argument("--same-time-s", type=float, default=600.0,
                    help="Δt at/below which a contradiction is a CONFLICT, above = EVOLUTION")
    ap.add_argument("--max-pairs", type=int, default=6000,
                    help="cap on judged pairs (top-cosine kept; the cap is REPORTED)")
    ap.add_argument("--contra-threshold", type=float, default=0.9)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--tiers", default="knowledge",
                    help="comma-separated fact tiers to scan "
                         "(knowledge|telemetry|test|dialog); default knowledge")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    t0 = time.time()
    tiers = frozenset(t.strip() for t in a.tiers.split(",") if t.strip())
    facts, emb, load_info = _load_live(Path(a.db), tiers)
    pairs = list(_candidate_pairs(emb, a.min_cosine))
    pairs.sort(key=lambda t: -t[2])
    capped = len(pairs) > a.max_pairs
    if capped:
        pairs = pairs[: a.max_pairs]

    from engram.local_relation import LocalRelationJudge
    judge = LocalRelationJudge(contradiction_threshold=a.contra_threshold)
    rels = judge.classify_batch(
        [(facts[i]["proposition"], facts[j]["proposition"]) for i, j, _ in pairs])

    from engram.semantic_conflict import Relation
    ev, cf, dup = [], [], []
    for (i, j, cos), rel in zip(pairs, rels, strict=True):
        if rel is Relation.NEUTRAL:
            continue
        fi, fj = facts[i], facts[j]
        older, newer = (fi, fj) if (fi["created_at"] or 0) <= (fj["created_at"] or 0) else (fj, fi)
        dt = abs((fi["created_at"] or 0) - (fj["created_at"] or 0))
        item = {
            "cosine": round(cos, 4), "dt_s": round(dt, 0),
            "older": {"id": older["id"], "topic": older["topic"],
                      "ts": older["created_at"],
                      "prop": (older["proposition"] or "")[:160]},
            "newer": {"id": newer["id"], "topic": newer["topic"],
                      "ts": newer["created_at"],
                      "prop": (newer["proposition"] or "")[:160]},
        }
        if rel is Relation.CONTRADICTION:
            (ev if dt > a.same_time_s else cf).append(item)
        else:
            dup.append(item)

    wall = round(time.time() - t0, 1)
    res = {
        "load": load_info, "min_cosine": a.min_cosine,
        "same_time_s": a.same_time_s,
        "contra_threshold": a.contra_threshold,
        "n_candidate_pairs": len(pairs), "pairs_capped": capped,
        "counts": {"evolution": len(ev), "conflict": len(cf),
                   "duplicate": len(dup)},
        "evolution": ev, "conflict": cf, "duplicate": dup,
        "wall_s": wall,
        "note": "READ-ONLY scan. evolution = NLI contradiction with temporal order "
                "(supersede candidate: older loses); conflict = same-time "
                "contradiction (review); duplicate = bidirectional entailment "
                "(merge candidate).",
    }
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")

    # readable digest
    print(json.dumps({k: res[k] for k in
                      ("load", "n_candidate_pairs", "pairs_capped", "counts",
                       "wall_s")}, indent=2))
    for name, bucket in (("EVOLUTION", ev), ("CONFLICT", cf), ("DUPLICATE", dup)):
        print(f"\n== top {name} (of {len(bucket)}) ==")
        for it in bucket[: a.top]:
            print(f"[cos {it['cosine']} | dt {int(it['dt_s'])}s]")
            print(f"  OLD {it['older']['id']} ({it['older']['topic']}): "
                  f"{it['older']['prop']}")
            print(f"  NEW {it['newer']['id']} ({it['newer']['topic']}): "
                  f"{it['newer']['prop']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
