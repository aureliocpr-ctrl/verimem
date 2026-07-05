"""Updating-slice retrieval REACHABILITY probe — the ceiling the selector cannot
exceed. Iter-14 finding: at the judge-calibrated e5@0.94 matcher only 55% of GT
originals are inside the top-10 retrieved candidates (the lenient 0.86 matcher
had hidden this at "99.6% reachable"), capping judged Updating at ~0.33 * top1.

Replays the exact chronological ingest of halumem_updating_bench and, for each
is_update point, recalls with a LARGE k once and slices: reachable@10/20/30 =
GT matched (e5@0.94) within the first 10/20/30 hits. No NLI, no selection, no
claude -p — pure retrieval + matcher, one config per run (env-driven A/B, e.g.
ENGRAM_RECALL_CENTERING=1).

    python -m benchmark.updating_reachability_probe --users 5 --k 30 \
        --out benchmark/results/updating_reachability_k30.json
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

from benchmark.halumem_updating_bench import (
    _DATASET,
    _iter_updates,
    make_e5_matcher,
)


def score_hits_file(path: str, *, match_thr: float, slices: list[int]) -> dict:
    """Pass-2 of the embedder A/B: score a --dump-hits jsonl with the FIXED
    default-embedder matcher (e5-base @ match_thr), so arms recorded under
    DIFFERENT retrieval embedders stay metric-comparable (the 0.94 threshold is
    judge-calibrated for e5-base similarities — a per-arm matcher would change
    the meaning of 'reachable' across arms)."""
    matcher = make_e5_matcher(match_thr)
    hit_at = dict.fromkeys(slices, 0)
    n = 0
    meta = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if "embedding_model" in row:      # header line
                meta = row
                continue
            n += 1
            first = None
            for r, t in enumerate(row["hits"], start=1):
                if any(matcher(t, g) for g in row["gt"]):
                    first = r
                    break
            for s in slices:
                if first is not None and first <= s:
                    hit_at[s] += 1
    return {"hits_file": path, "embedder_arm": meta.get("embedding_model", "?"),
            "n_updates": n, "match_thr": match_thr,
            "reachable_at": {str(s): round(hit_at[s] / n, 4) if n else None
                             for s in slices}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(_DATASET))
    ap.add_argument("--users", type=int, default=5)
    ap.add_argument("--k", type=int, default=30)
    ap.add_argument("--slices", default="10,20,30")
    ap.add_argument("--match-thr", type=float, default=0.94)
    ap.add_argument("--dump-hits", default=None,
                    help="pass-1 of the embedder A/B: write {update, gt, hits} "
                         "jsonl and SKIP in-process matching (the matcher must "
                         "not run under a non-default HIPPO_EMBEDDING_MODEL)")
    ap.add_argument("--score-hits", default=None,
                    help="pass-2: score a --dump-hits jsonl with the fixed "
                         "default-embedder matcher; no ingest, no recall")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    slices_parsed = sorted(int(x) for x in a.slices.split(",") if x.strip())

    if a.score_hits:
        res = score_hits_file(a.score_hits, match_thr=a.match_thr,
                              slices=slices_parsed)
        print(json.dumps(res, indent=2))
        if a.out:
            Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 0

    from engram.semantic import Fact, SemanticMemory

    users = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            users.append(json.loads(line))
            if len(users) >= a.users:
                break

    dump_f = None
    if a.dump_hits:
        Path(a.dump_hits).parent.mkdir(parents=True, exist_ok=True)
        dump_f = open(a.dump_hits, "w", encoding="utf-8")  # noqa: SIM115
        from engram.config import CONFIG
        dump_f.write(json.dumps({"embedding_model": CONFIG.embedding_model,
                                 "k": a.k, "users": a.users}) + "\n")
    matcher = None if a.dump_hits else make_e5_matcher(a.match_thr)
    slices = slices_parsed
    hit_at = dict.fromkeys(slices, 0)
    n_upd = 0
    t0 = time.time()
    for ui, user in enumerate(users):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            sm = SemanticMemory(db_path=Path(tmp) / "semantic" / "semantic.db")
            for _si, content, is_upd, gt_originals in _iter_updates(user):
                if is_upd and gt_originals:
                    n_upd += 1
                    hits = sm.recall(content, k=a.k)
                    texts = [getattr(fo, "proposition", "") for fo, _ in hits]
                    if dump_f is not None:
                        dump_f.write(json.dumps(
                            {"update": content, "gt": list(gt_originals),
                             "hits": texts}, ensure_ascii=False) + "\n")
                    else:
                        # first rank (1-based) at which ANY GT original matches
                        first = None
                        for r, t in enumerate(texts, start=1):
                            if any(matcher(t, g) for g in gt_originals):
                                first = r
                                break
                        for s in slices:
                            if first is not None and first <= s:
                                hit_at[s] += 1
                # chronological world state, identical to the bench
                sm.store(Fact(proposition=content, topic=f"halu/{ui}",
                              status="model_claim", confidence=0.8))
            del sm
            import gc
            gc.collect()

    if dump_f is not None:
        dump_f.close()
    from engram.config import CONFIG as _CFG
    res = {
        "users": len(users), "k": a.k, "match_thr": a.match_thr,
        "n_updates": n_upd,
        "embedding_model": _CFG.embedding_model,
        "dump_hits": a.dump_hits,
        "env": {k: os.environ.get(k, "") for k in
                ("ENGRAM_RECALL_CENTERING", "ENGRAM_PPR_FUSION",
                 "ENGRAM_RECALL_RERANK", "ENGRAM_RERANK_TOPN",
                 "ENGRAM_ANN_RECALL", "HIPPO_EMBEDDING_MODEL",
                 "ENGRAM_ENCODE_SERVICE")},
        "reachable_at": None if dump_f is not None else {
            str(s): round(hit_at[s] / n_upd, 4) if n_upd else None
            for s in slices},
        "wall_s": round(time.time() - t0, 1),
        "note": "reachable@k = share of is_update points whose GT original "
                "(e5@match_thr OR norm-exact) appears in the first k recalled "
                "hits, chronological ingest identical to halumem_updating_bench. "
                "The selector ceiling: judged accuracy <= reachable@k * top1.",
    }
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
