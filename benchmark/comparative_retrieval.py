"""Comparative retrieval benchmark: Engram vs a vanilla RAG, same embedder.

The competitive question Engram has never answered with a number: how much
does the Engram layer (provenance gating, corpus cache, 2-stage CE rerank)
add OVER a bare cosine top-k with the IDENTICAL embedding model? Until this
exists, "better than plain RAG" is an unverified claim (A2).

Arms (all 100% local, zero external APIs — CLAUDE.md O4):
  engram       SemanticMemory.recall with the PRODUCTION default
               (cross-encoder rerank ON since 2026-06-10, commit 9ca0c75).
  engram-base  Same, ENGRAM_RECALL_RERANK=0 — the bi-encoder-only stack.
  vanilla      Bare numpy cosine top-k over the same e5 embeddings, with the
               same as_passage/as_query e5 prefix scheme (parity: penalising
               the baseline with a worse text scheme would inflate Engram).

Dataset: LongMemEval (judge-free session-retrieval protocol — see
longmemeval_runner.py, whose metric helpers this module reuses).

Fairness notes (declared):
  * vanilla has NO status/provenance gates and NO dedup — it sees every
    stored text. Engram's gates are part of the product being measured.
  * per-question hermetic stores for Engram (fresh tmp db), in-memory
    matrices for vanilla; both ingest the identical (sid, text) pairs.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from benchmark.longmemeval_runner import (
    _unique_preserve,
    hit_at_k,
    mrr,
    recall_at_k,
    session_to_text,
)
from engram import embedding
from engram.semantic import Fact, SemanticMemory

ARMS = ("engram", "engram-base", "vanilla")


class VanillaRAG:
    """Bare cosine top-k over the same embedder. The honest baseline."""

    def __init__(self) -> None:
        self._ids: list[str] = []
        self._texts: list[str] = []
        self._mat: np.ndarray | None = None

    def store(self, sid: str, text: str) -> None:
        self._ids.append(sid)
        self._texts.append(text)
        self._mat = None

    def _matrix(self) -> np.ndarray:
        if self._mat is None:
            if not self._texts:
                self._mat = np.zeros((0, 1), dtype=np.float32)
            else:
                self._mat = np.asarray(embedding.encode(
                    [embedding.as_passage(t) for t in self._texts]
                ), dtype=np.float32)
        return self._mat

    def retrieve(self, query: str, k: int) -> list[str]:
        mat = self._matrix()
        if mat.shape[0] == 0:
            return []
        q = np.asarray(embedding.encode(embedding.as_query(query)),
                       dtype=np.float32)
        sims = mat @ q
        order = np.argsort(-sims)[: max(0, int(k))]
        return [self._ids[i] for i in order]


def _engram_retrieve(
    pairs: list[tuple[str, str]], query: str, k: int,
    *, workdir: Path, qid: str, rerank: bool,
) -> tuple[list[str], float]:
    """Fresh hermetic SemanticMemory -> ranked source ids + recall latency."""
    db = Path(workdir) / f"{qid}-{'rr' if rerank else 'base'}.db"
    os.environ["ENGRAM_RECALL_RERANK"] = "1" if rerank else "0"
    try:
        sm = SemanticMemory(db_path=db)
        for sid, text in pairs:
            sm.store(Fact(proposition=text, topic=f"lme/{sid}",
                          source_episodes=[sid]))
        t0 = time.perf_counter()
        hits = sm.recall(query, k=k)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return (
            [(f.source_episodes[0] if f.source_episodes else "")
             for f, *_ in hits],
            latency_ms,
        )
    finally:
        os.environ["ENGRAM_RECALL_RERANK"] = "0"
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(db) + suffix)
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass


def eval_question_arms(
    q: dict[str, Any], k: int, *, workdir: Path | str,
    arms: tuple[str, ...] = ARMS,
) -> dict[str, Any]:
    """Run one LongMemEval question through every arm on identical inputs."""
    haystack_sessions = q.get("haystack_sessions") or []
    haystack_ids = q.get("haystack_session_ids") or []
    gold = q.get("answer_session_ids") or []
    qid = str(q.get("question_id", "q"))
    query = q.get("question", "")

    pairs: list[tuple[str, str]] = []
    for sid, sess in zip(haystack_ids, haystack_sessions, strict=False):
        text = session_to_text(sess)
        if text:
            pairs.append((str(sid), text))

    out: dict[str, Any] = {
        "question_id": qid,
        "question_type": q.get("question_type"),
        "n_haystack": len(haystack_ids),
        "n_gold": len(gold),
        "arms": {},
    }
    workdir = Path(workdir)
    for arm in arms:
        if arm == "vanilla":
            rag = VanillaRAG()
            for sid, text in pairs:
                rag.store(sid, text)
            rag._matrix()  # ingest cost out of the timer (engram pays it in store)
            t0 = time.perf_counter()
            retrieved = rag.retrieve(query, k)
            latency_ms = (time.perf_counter() - t0) * 1000.0
        elif arm in ("engram", "engram-base"):
            retrieved, latency_ms = _engram_retrieve(
                pairs, query, k, workdir=workdir, qid=qid,
                rerank=(arm == "engram"),
            )
        else:  # pragma: no cover — guarded by ARMS
            raise ValueError(f"unknown arm {arm!r}")
        out["arms"][arm] = {
            "recall_at_k": recall_at_k(retrieved, gold, k),
            "hit_at_k": hit_at_k(retrieved, gold, k),
            "mrr": mrr(retrieved, gold),
            "n_retrieved": len(_unique_preserve(retrieved)),
            "latency_ms": round(latency_ms, 2),
        }
    return out


def _mean(xs: list[float | None]) -> float:
    vals = [x for x in xs if x is not None]
    return round(statistics.fmean(vals), 4) if vals else 0.0


def run_comparative(
    dataset_path: Path | str, *, k: int = 5, sample: int | None = None,
    arms: tuple[str, ...] = ARMS, workdir: Path | str | None = None,
) -> dict[str, Any]:
    data = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    if sample is not None:
        data = data[: max(0, int(sample))]

    owns = workdir is None
    workdir = Path(workdir) if workdir else Path(
        tempfile.mkdtemp(prefix="lme_cmp_"))
    per_q: list[dict[str, Any]] = []
    try:
        for i, q in enumerate(data, 1):
            per_q.append(eval_question_arms(q, k, workdir=workdir, arms=arms))
            if i % 10 == 0 or i == len(data):
                print(f"... {i}/{len(data)}", flush=True)
    finally:
        if owns:
            shutil.rmtree(workdir, ignore_errors=True)

    summary: dict[str, Any] = {}
    for arm in arms:
        rows = [r["arms"][arm] for r in per_q]
        by_type: dict[str, list[dict]] = defaultdict(list)
        for r in per_q:
            by_type[r.get("question_type") or "?"].append(r["arms"][arm])
        summary[arm] = {
            "recall_at_k": _mean([r["recall_at_k"] for r in rows]),
            "hit_at_k": _mean([r["hit_at_k"] for r in rows]),
            "mrr": _mean([r["mrr"] for r in rows]),
            "latency_ms_mean": _mean([r["latency_ms"] for r in rows]),
            "per_type": {
                t: {
                    "n": len(rs),
                    "recall_at_k": _mean([r["recall_at_k"] for r in rs]),
                    "mrr": _mean([r["mrr"] for r in rs]),
                }
                for t, rs in sorted(by_type.items())
            },
        }
    return {
        "dataset": str(dataset_path),
        "k": k,
        "n_questions": len(per_q),
        "embedding_model": embedding.model_signature(),
        "arms": summary,
        "metric_note": (
            "session-level retrieval of gold answer_session_ids; identical "
            "(sid,text) ingest per arm; judge-free; zero external APIs"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Engram vs engram-base vs vanilla RAG on LongMemEval.")
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--sample", type=int, default=None)
    p.add_argument("--arms", type=str, default=",".join(ARMS))
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    res = run_comparative(args.dataset, k=args.k, sample=args.sample, arms=arms)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(res, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    print(f"\nCOMPARATIVE LongMemEval | n={res['n_questions']} k={args.k} "
          f"| embedder={res['embedding_model']}")
    for arm in arms:
        s = res["arms"][arm]
        print(f"  {arm:12s} recall@{args.k}={s['recall_at_k']:.3f}  "
              f"hit@{args.k}={s['hit_at_k']:.3f}  MRR={s['mrr']:.3f}  "
              f"lat={s['latency_ms_mean']:.0f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
