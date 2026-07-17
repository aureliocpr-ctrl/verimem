"""Real LongMemEval retrieval benchmark for Engram (judge-free, subscription-safe).

LongMemEval (arXiv 2410.10813) ships, per question, the gold evidence sessions
(``answer_session_ids``) embedded inside a haystack of sessions
(``haystack_sessions`` / ``haystack_session_ids``). That lets us measure
Engram's RETRIEVAL quality OBJECTIVELY — recall@k / hit@k / MRR of the evidence
sessions — with NO LLM judge and NO external API (CLAUDE.md O4 subscription-only,
MAI API key). The end-to-end QA-correctness score (which DOES require an LLM
judge) is deliberately NOT computed here: this is the retrieval sub-metric the
paper reports separately, and it is the honest number we CAN prove today.

Mapping: each haystack session -> one Engram ``Fact`` (proposition = the session
turns joined, provenance ``source_episodes=[session_id]``). Per question we use a
FRESH hermetic ``SemanticMemory`` (haystacks are independent; no cross-question
leakage; NEVER touches ~/.engram).

Honest caveat (reported, not hidden): retrieval is at SESSION granularity and the
embedding model has a token limit, so very long sessions are truncated by the
tokenizer (Engram is tuned for short facts). This is a property of this mapping,
not a hidden assumption.
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from verimem.config import CONFIG
from verimem.semantic import Fact, SemanticMemory


def session_to_text(turns: Any) -> str:
    """Join a LongMemEval session (list of {role, content} turns) into one text."""
    parts: list[str] = []
    for t in turns or []:
        if isinstance(t, dict):
            role = (t.get("role") or "").strip()
            content = (t.get("content") or "").strip()
        else:
            role, content = "", str(t).strip()
        if content:
            parts.append(f"{role}: {content}" if role else content)
    return "\n".join(parts)


def _unique_preserve(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def recall_at_k(retrieved_ids: list[str], gold: Any, k: int) -> float | None:
    """Fraction of gold session ids present in the top-k unique retrieved ids."""
    gold = set(gold or [])
    if not gold:
        return None
    topk = _unique_preserve(retrieved_ids)[: max(0, k)]
    return len(set(topk) & gold) / len(gold)


def hit_at_k(retrieved_ids: list[str], gold: Any, k: int) -> float | None:
    """1.0 if ANY gold session id is in the top-k unique retrieved, else 0.0."""
    gold = set(gold or [])
    if not gold:
        return None
    return 1.0 if (set(_unique_preserve(retrieved_ids)[: max(0, k)]) & gold) else 0.0


def mrr(retrieved_ids: list[str], gold: Any) -> float | None:
    """Reciprocal rank of the FIRST gold session id in the unique retrieved order."""
    gold = set(gold or [])
    if not gold:
        return None
    for i, x in enumerate(_unique_preserve(retrieved_ids), start=1):
        if x in gold:
            return 1.0 / i
    return 0.0


def eval_question(q: dict[str, Any], k: int, *, workdir: Path | str) -> dict[str, Any]:
    """Ingest one question's haystack into a FRESH hermetic memory, recall, score.

    Returns a per-question dict with recall@k / hit@k / mrr / latency. Never
    touches the real corpus (explicit db_path under ``workdir``).
    """
    haystack_sessions = q.get("haystack_sessions") or []
    haystack_ids = q.get("haystack_session_ids") or []
    gold = q.get("answer_session_ids") or []
    qid = q.get("question_id", "q")

    db = Path(workdir) / f"{qid}.db"
    sm = SemanticMemory(db_path=db)
    n_stored = 0
    for sid, sess in zip(haystack_ids, haystack_sessions, strict=False):
        text = session_to_text(sess)
        if not text:
            continue
        sm.store(Fact(proposition=text, topic=f"lme/{sid}", source_episodes=[str(sid)]))
        n_stored += 1

    t0 = time.perf_counter()
    hits = sm.recall(q.get("question", ""), k=k)
    latency_ms = (time.perf_counter() - t0) * 1000.0
    retrieved = [(f.source_episodes[0] if f.source_episodes else "") for f, *_ in hits]

    # free the per-question DB to bound disk on the full 500-question run
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db) + suffix)
        try:
            if p.exists():
                p.unlink()
        except OSError:
            pass

    return {
        "question_id": qid,
        "question_type": q.get("question_type"),
        "n_haystack": len(haystack_ids),
        "n_stored": n_stored,
        "n_gold": len(gold),
        "n_retrieved": len(_unique_preserve(retrieved)),
        "recall_at_k": recall_at_k(retrieved, gold, k),
        "hit_at_k": hit_at_k(retrieved, gold, k),
        "mrr": mrr(retrieved, gold),
        "latency_ms": round(latency_ms, 2),
    }


def _mean(xs: list[float]) -> float:
    xs = [x for x in xs if x is not None]
    return round(statistics.fmean(xs), 4) if xs else 0.0


def run_dataset(
    dataset_path: Path | str,
    *,
    k: int = 5,
    sample: int | None = None,
    workdir: Path | str | None = None,
) -> dict[str, Any]:
    """Run the retrieval benchmark over a LongMemEval JSON file."""
    data = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    if sample is not None:
        data = data[: max(0, int(sample))]

    owns_workdir = workdir is None
    workdir = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="lme_bench_"))
    per_q: list[dict[str, Any]] = []
    try:
        for q in data:
            per_q.append(eval_question(q, k, workdir=workdir))
    finally:
        if owns_workdir:
            shutil.rmtree(workdir, ignore_errors=True)

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in per_q:
        by_type[r.get("question_type") or "?"].append(r)

    per_type = {
        t: {
            "n": len(rows),
            "recall_at_k": _mean([r["recall_at_k"] for r in rows]),
            "hit_at_k": _mean([r["hit_at_k"] for r in rows]),
            "mrr": _mean([r["mrr"] for r in rows]),
        }
        for t, rows in sorted(by_type.items())
    }

    return {
        "dataset": str(dataset_path),
        "k": k,
        "n_questions": len(per_q),
        "embedding_model": CONFIG.embedding_model,
        "embedding_dim": CONFIG.embedding_dim,
        "overall": {
            "recall_at_k": _mean([r["recall_at_k"] for r in per_q]),
            "hit_at_k": _mean([r["hit_at_k"] for r in per_q]),
            "mrr": _mean([r["mrr"] for r in per_q]),
            "latency_ms_mean": _mean([r["latency_ms"] for r in per_q]),
        },
        "per_type": per_type,
        "metric_note": (
            "session-level retrieval recall@k of gold answer_session_ids; "
            "judge-free, no external API; embedding via Engram's own model"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="LongMemEval retrieval benchmark for Engram.")
    p.add_argument("--dataset", type=Path, required=True, help="Path to a LongMemEval JSON file (oracle / s / m).")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--sample", type=int, default=None, help="Run only the first N questions.")
    p.add_argument("--out", type=Path, default=None, help="Write the result JSON here.")
    args = p.parse_args(argv)

    res = run_dataset(args.dataset, k=args.k, sample=args.sample)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    o = res["overall"]
    print(f"LongMemEval retrieval | n={res['n_questions']} k={res['k']} "
          f"| model={res['embedding_model']} dim={res['embedding_dim']}")
    print(f"  OVERALL  recall@{args.k}={o['recall_at_k']:.3f}  hit@{args.k}={o['hit_at_k']:.3f}  "
          f"MRR={o['mrr']:.3f}  lat_mean={o['latency_ms_mean']:.1f}ms")
    for t, d in res["per_type"].items():
        print(f"  {t:28s} n={d['n']:4d}  recall@{args.k}={d['recall_at_k']:.3f}  "
              f"hit@{args.k}={d['hit_at_k']:.3f}  MRR={d['mrr']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
