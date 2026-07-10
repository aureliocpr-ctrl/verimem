"""S3 (F1 adversarial map) — recall latency + RAM as the corpus grows.

The silent "far ridere" case: a user with lots of data. Grows one hermetic
store to N facts, and at each checkpoint measures mean recall latency (real
recall path) and process RSS. Judge-free, objective, no network. Synthetic but
LEXICALLY VARIED facts (distinct embeddings), so recall is real work.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import tempfile
import time
from pathlib import Path

from engram.semantic import Fact, SemanticMemory

_SUBJ = ["falcon", "engineer", "river", "senator", "comet", "violinist",
         "glacier", "merchant", "reactor", "orchid", "nomad", "lighthouse"]
_VERB = ["charted", "abandoned", "financed", "eclipsed", "restored",
         "smuggled", "patented", "flooded", "narrated", "dismantled"]
_OBJ = ["the northern archive", "a copper treaty", "the tidal registry",
        "two obsidian ledgers", "the vanished colony", "a brass automaton",
        "the equinox accord", "the seventh manuscript", "a salt cathedral"]


def _fact(i: int) -> str:
    s = _SUBJ[i % len(_SUBJ)]
    v = _VERB[(i // 7) % len(_VERB)]
    o = _OBJ[(i // 13) % len(_OBJ)]
    return f"Record {i}: in year {1500 + (i % 500)} the {s} {v} {o} near sector {i % 97}."


def _rss_mb() -> float:
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except Exception:  # noqa: BLE001
        return -1.0


def _queries():
    return [f"who {v} {o}" for v, o in zip(_VERB[:6], _OBJ[:6], strict=False)]


def run(checkpoints=(1000, 3000, 6000, 10000), k: int = 10) -> dict:
    d = Path(tempfile.mkdtemp(prefix="s3_scale_"))
    sm = SemanticMemory(db_path=d / "scale.db")
    qs = _queries()
    rows = []
    stored = 0
    target_max = max(checkpoints)
    for cp in checkpoints:
        while stored < cp:
            sm.store(Fact(proposition=_fact(stored), topic="scale",
                          source_episodes=[str(stored)]), embed="sync")
            stored += 1
        lats = []
        for q in qs:
            t0 = time.perf_counter()
            sm.recall(q, k=k)
            lats.append((time.perf_counter() - t0) * 1000)
        rows.append({
            "n_facts": stored,
            "recall_ms_mean": round(statistics.fmean(lats), 1),
            "recall_ms_p95": round(sorted(lats)[max(0, int(len(lats) * 0.95) - 1)], 1),
            "rss_mb": round(_rss_mb(), 1),
        })
        print(f"  n={stored:6d}  recall_mean={rows[-1]['recall_ms_mean']:7.1f}ms  "
              f"p95={rows[-1]['recall_ms_p95']:7.1f}ms  RSS={rows[-1]['rss_mb']:.0f}MB",
              flush=True)
    import shutil
    shutil.rmtree(d, ignore_errors=True)
    return {"k": k, "checkpoints": rows, "target_max": target_max}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoints", type=int, nargs="+",
                    default=[1000, 3000, 6000, 10000])
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    res = run(tuple(a.checkpoints), k=a.k)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
