"""Mem0 OSS arm for the LongMemEval comparative benchmark (standalone).

Runs INSIDE the isolated .venv-mem0bench (mem0ai + chroma + HF embedder),
NOT the HippoAgent venv — mem0's dependency tree must never touch the
production environment. No engram imports here; the three metric helpers
are pure functions duplicated verbatim from benchmark/longmemeval_runner.py
(declared, kept in sync by the comparative test suite on the engram side).

Configuration honesty:
  * embedder: huggingface intfloat/multilingual-e5-base — the SAME model
    Engram uses, so the comparison isolates the LAYER, not the encoder.
  * llm: provider 'ollama' with a placeholder model. It is NEVER invoked:
    every add() uses infer=False (raw storage, no LLM extraction). This is
    the zero-API mode a local-first user would run.
  * two variants:
      --variant asis       texts/queries exactly as the dataset provides
                           (mem0 as shipped: NO e5 query:/passage: scheme)
      --variant e5parity   "passage: "/"query: " prefixes injected, the
                           scheme e5 was trained with and Engram applies —
                           closes the "you handicapped mem0" objection.
  * search(threshold=0.0, top_k=k): no score cutoff, parity with arms that
    always return k results. Results are re-sorted by the returned score
    DESC defensively (observed in the probe: insertion-ish order otherwise).

Usage (from repo root):
  .venv-mem0bench/Scripts/python benchmark/mem0_arm_runner.py
      --dataset ~/.cache/longmemeval/longmemeval_s
      --k 5 --sample 100 --variant e5parity --out results.json
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

# --- metric helpers: duplicated PURE functions (no engram in this venv) ----


def session_to_text(turns: Any) -> str:
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
    gold = set(gold or [])
    if not gold:
        return None
    topk = _unique_preserve(retrieved_ids)[: max(0, k)]
    return len(set(topk) & gold) / len(gold)


def hit_at_k(retrieved_ids: list[str], gold: Any, k: int) -> float | None:
    gold = set(gold or [])
    if not gold:
        return None
    return 1.0 if (set(_unique_preserve(retrieved_ids)[: max(0, k)]) & gold) else 0.0


def mrr(retrieved_ids: list[str], gold: Any) -> float | None:
    gold = set(gold or [])
    if not gold:
        return None
    for i, x in enumerate(_unique_preserve(retrieved_ids), start=1):
        if x in gold:
            return 1.0 / i
    return 0.0


# --- mem0 arm ---------------------------------------------------------------


def build_memory(workdir: str, collection: str):
    from mem0 import Memory
    config = {
        # Never invoked: every add() is infer=False. Placeholder keeps
        # Memory.from_config from instantiating the default OpenAI client.
        "llm": {"provider": "ollama", "config": {"model": "never-called"}},
        "embedder": {
            "provider": "huggingface",
            "config": {"model": "intfloat/multilingual-e5-base"},
        },
        "vector_store": {
            "provider": "chroma",
            "config": {"path": workdir, "collection_name": collection},
        },
    }
    return Memory.from_config(config)


def eval_question(q: dict[str, Any], k: int, *, workdir: str,
                  e5_prefix: bool) -> dict[str, Any]:
    haystack_sessions = q.get("haystack_sessions") or []
    haystack_ids = q.get("haystack_session_ids") or []
    gold = q.get("answer_session_ids") or []
    qid = str(q.get("question_id", "q"))
    query = q.get("question", "")

    coll = f"q{abs(hash(qid)) % 10**12}"
    m = build_memory(workdir, coll)
    uid = "bench"
    n_stored = 0
    for sid, sess in zip(haystack_ids, haystack_sessions, strict=False):
        text = session_to_text(sess)
        if not text:
            continue
        payload = f"passage: {text}" if e5_prefix else text
        m.add(payload, user_id=uid, infer=False, metadata={"sid": str(sid)})
        n_stored += 1

    qtext = f"query: {query}" if e5_prefix else query
    # UPSTREAM BUG, fully debugged 2026-06-10 (A/B proof): with the chroma
    # backend, mem0 2.0.4's Memory.search feeds chroma's L2 DISTANCE
    # (gold doc: score 0.4026 == 2-2*cos(0.7987) exactly) into
    # score_and_rank() as if it were a SIMILARITY, then cuts top_k —
    # the semantic ranking comes back INVERTED and the cut keeps the
    # WORST candidates (same query vector: gold rank 1 via
    # vector_store.search, rank 50/50 via Memory.search). No post-sort
    # can recover the dropped gold. The arm therefore queries mem0's own
    # vector_store.search directly (its embedder, its store, its add
    # pipeline — the pre-bug point), declared in BENCHMARKS.md.
    t0 = time.perf_counter()
    qv = m.embedding_model.embed(qtext, "search")
    hits_raw = m.vector_store.search(query=qtext, vectors=qv, top_k=k,
                                     filters={"user_id": uid})
    latency_ms = (time.perf_counter() - t0) * 1000.0
    # chroma returns distance-ascending = best-first already.
    retrieved = [str((getattr(h, "payload", None) or {}).get("sid") or "")
                 for h in hits_raw]

    return {
        "question_id": qid,
        "question_type": q.get("question_type"),
        "n_haystack": len(haystack_ids),
        "n_stored": n_stored,
        "n_gold": len(gold),
        "recall_at_k": recall_at_k(retrieved, gold, k),
        "hit_at_k": hit_at_k(retrieved, gold, k),
        "mrr": mrr(retrieved, gold),
        "latency_ms": round(latency_ms, 2),
    }


def _mean(xs: list[float | None]) -> float:
    vals = [x for x in xs if x is not None]
    return round(statistics.fmean(vals), 4) if vals else 0.0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Mem0 OSS arm on LongMemEval.")
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--sample", type=int, default=None)
    p.add_argument("--variant", choices=("asis", "e5parity"), default="e5parity")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    data = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    if args.sample is not None:
        data = data[: max(0, int(args.sample))]

    per_q: list[dict[str, Any]] = []
    for i, q in enumerate(data, 1):
        workdir = tempfile.mkdtemp(prefix="mem0arm_")
        try:
            per_q.append(eval_question(
                q, args.k, workdir=workdir,
                e5_prefix=(args.variant == "e5parity"),
            ))
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        if i % 10 == 0 or i == len(data):
            print(f"... {i}/{len(data)}", flush=True)

    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in per_q:
        by_type[r.get("question_type") or "?"].append(r)
    res = {
        "arm": f"mem0-{args.variant}",
        "mem0_mode": "infer=False (raw add, llm never invoked), chroma local",
        "embedder": "huggingface intfloat/multilingual-e5-base",
        "dataset": str(args.dataset),
        "k": args.k,
        "n_questions": len(per_q),
        "overall": {
            "recall_at_k": _mean([r["recall_at_k"] for r in per_q]),
            "hit_at_k": _mean([r["hit_at_k"] for r in per_q]),
            "mrr": _mean([r["mrr"] for r in per_q]),
            "latency_ms_mean": _mean([r["latency_ms"] for r in per_q]),
        },
        "per_type": {
            t: {
                "n": len(rows),
                "recall_at_k": _mean([r["recall_at_k"] for r in rows]),
                "mrr": _mean([r["mrr"] for r in rows]),
            }
            for t, rows in sorted(by_type.items())
        },
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(res, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    o = res["overall"]
    print(f"\nMEM0 [{args.variant}] | n={res['n_questions']} k={args.k}")
    print(f"  recall@{args.k}={o['recall_at_k']:.3f}  hit@{args.k}={o['hit_at_k']:.3f}  "
          f"MRR={o['mrr']:.3f}  lat={o['latency_ms_mean']:.0f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
