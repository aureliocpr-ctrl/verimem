"""MuSiQue multi-hop retrieval — F1 virgin-corpus validation (task #22).

Mandate (Aurelio 2026-07-10): validate the COMPLETE engine on an ESTRANEO
corpus never touched in development — "se e' sviluppato sul mio cadra' su uno
nuovo". LongMemEval / LoCoMo / HaluEval / TruthfulQA are all burnt (tuned or
measured on). HotpotQA is a cousin (HaluEval's `knowledge` is built on it).
MuSiQue is DISTINCT: 2-4 hop compositional questions with hard-negative
distractors, engineered anti-shortcut (Trivedi et al., TACL 2022).

Judge-free, subscription-safe (CLAUDE.md O5, MAI API key): MuSiQue ships per
question the gold `is_supporting` paragraphs, so retrieval quality is OBJECTIVE
— recall@k / hit@k / all-hops@k / MRR of the supporting paragraphs — with NO
LLM judge. The end-to-end answer-correctness score (which needs a judge) is
deliberately NOT computed here; this is the honest number we CAN prove today.

Mapping (same discipline as longmemeval_runner): each of the 20 paragraphs ->
one Engram `Fact` (proposition = "title. text", source_episodes=[str(idx)]),
stored through the REAL write path (redaction + injection screen ON by default,
exactly as production). Per question a FRESH hermetic `SemanticMemory` (items
are independent; no cross-question leakage; NEVER touches ~/.engram).

all-hops@k is the multi-hop-honest metric: 1.0 only when EVERY supporting
paragraph is in the top-k. A 2-hop answer needs both hops; hit@k (any one hop)
overstates a memory that finds the easy hop and misses the bridge.
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

from engram.config import CONFIG
from engram.semantic import Fact, SemanticMemory

# Reuse the metrics already unit-tested in test_longmemeval_runner.py.
from benchmark.longmemeval_runner import (
    _unique_preserve,
    hit_at_k,
    mrr,
    recall_at_k,
)


def gold_idxs(item: dict[str, Any]) -> list[str]:
    """Ids (as str) of the supporting paragraphs — the multi-hop gold set."""
    return [str(p["idx"]) for p in item.get("paragraphs", [])
            if p.get("is_supporting")]


def n_hops(item: dict[str, Any]) -> int:
    """Hop count. Primary source: the id prefix ('2hop__...'); fallback: the
    length of question_decomposition."""
    ident = item.get("id", "") or ""
    if "hop" in ident:
        try:
            return int(ident.split("hop", 1)[0])
        except (ValueError, IndexError):
            pass
    return len(item.get("question_decomposition") or [])


def all_hops_at_k(retrieved: list[str], gold: Any, k: int) -> float | None:
    """1.0 only when ALL gold ids are in the top-k unique retrieved, else 0.0.
    The multi-hop-honest metric: partial recall of a 2-hop chain is a miss."""
    gold = set(gold or [])
    if not gold:
        return None
    topk = set(_unique_preserve(retrieved)[: max(0, k)])
    return 1.0 if gold <= topk else 0.0


def paragraph_to_text(p: dict[str, Any]) -> str:
    """One paragraph -> Fact proposition. Title carries the entity the bridge
    hop pivots on, so keep it."""
    title = (p.get("title") or "").strip()
    body = (p.get("paragraph_text") or "").strip()
    return f"{title}. {body}" if title else body


def eval_item(item: dict[str, Any], ks: list[int], *, workdir: Path | str) -> dict[str, Any]:
    """Ingest one MuSiQue item's 20 paragraphs through the real write path,
    recall at max(ks), score every k. Returns per-k retrieval metrics."""
    paras = item.get("paragraphs", [])
    gold = gold_idxs(item)
    qid = item.get("id", "q")

    db = Path(workdir) / f"{abs(hash(qid))}.db"
    sm = SemanticMemory(db_path=db)
    n_stored = 0
    for p in paras:
        text = paragraph_to_text(p)
        if not text:
            continue
        sm.store(Fact(proposition=text, topic=f"musique/{qid}",
                      source_episodes=[str(p["idx"])]))
        n_stored += 1

    k_max = max(ks)
    t0 = time.perf_counter()
    hits = sm.recall(item.get("question", ""), k=k_max)
    latency_ms = (time.perf_counter() - t0) * 1000.0
    retrieved = [(f.source_episodes[0] if f.source_episodes else "") for f, *_ in hits]
    top1_score = float(hits[0][1]) if hits and len(hits[0]) > 1 else None

    for suffix in ("", "-wal", "-shm"):
        pth = Path(str(db) + suffix)
        try:
            if pth.exists():
                pth.unlink()
        except OSError:
            pass

    per_k = {}
    for k in ks:
        per_k[k] = {
            "recall": recall_at_k(retrieved, gold, k),
            "hit": hit_at_k(retrieved, gold, k),
            "all_hops": all_hops_at_k(retrieved, gold, k),
            "mrr": mrr(retrieved, gold),
        }
    return {
        "id": qid,
        "n_hops": n_hops(item),
        "n_paragraphs": len(paras),
        "n_stored": n_stored,
        "n_gold": len(gold),
        "n_retrieved": len(_unique_preserve(retrieved)),
        "top1_score": top1_score,
        "latency_ms": round(latency_ms, 2),
        "per_k": per_k,
    }


def _mean(xs: list[Any]) -> float:
    xs = [x for x in xs if x is not None]
    return round(statistics.fmean(xs), 4) if xs else 0.0


def _agg(rows: list[dict[str, Any]], ks: list[int]) -> dict[str, Any]:
    out: dict[str, Any] = {"n": len(rows)}
    for k in ks:
        out[f"recall@{k}"] = _mean([r["per_k"][k]["recall"] for r in rows])
        out[f"hit@{k}"] = _mean([r["per_k"][k]["hit"] for r in rows])
        out[f"all_hops@{k}"] = _mean([r["per_k"][k]["all_hops"] for r in rows])
    out["mrr"] = _mean([r["per_k"][ks[0]]["mrr"] for r in rows])
    return out


def load_musique(path: Path | str, *, sample: int | None = None,
                 seed: int = 42) -> list[dict[str, Any]]:
    """Load the jsonl. When sampling, stratify by hop count so 3/4-hop
    questions (the hard tail) are not washed out by the 2-hop majority."""
    items = [json.loads(line) for line in
             Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if sample is None or sample >= len(items):
        return items
    import random
    by_hop: dict[int, list] = defaultdict(list)
    for it in items:
        by_hop[n_hops(it)].append(it)
    rng = random.Random(seed)
    picked: list = []
    hops = sorted(by_hop)
    per = max(1, sample // len(hops))
    for h in hops:
        pool = by_hop[h]
        rng.shuffle(pool)
        picked.extend(pool[:per])
    rng.shuffle(picked)
    return picked[:sample]


def run(dataset_path: Path | str, *, ks: list[int] | None = None,
        sample: int | None = None, workdir: Path | str | None = None,
        seed: int = 42) -> dict[str, Any]:
    ks = ks or [2, 5, 10, 20]
    ks = sorted(set(ks))
    data = load_musique(dataset_path, sample=sample, seed=seed)

    owns = workdir is None
    workdir = Path(workdir) if workdir else Path(
        tempfile.mkdtemp(prefix="musique_f1_"))
    per_q: list[dict[str, Any]] = []
    try:
        for it in data:
            per_q.append(eval_item(it, ks, workdir=workdir))
    finally:
        if owns:
            shutil.rmtree(workdir, ignore_errors=True)

    by_hop: dict[int, list] = defaultdict(list)
    for r in per_q:
        by_hop[r["n_hops"]].append(r)

    return {
        "dataset": str(dataset_path),
        "corpus": "MuSiQue-Answerable dev (virgin — never used in dev)",
        "ks": ks,
        "n_questions": len(per_q),
        "embedding_model": CONFIG.embedding_model,
        "embedding_dim": CONFIG.embedding_dim,
        "overall": _agg(per_q, ks),
        "per_hop": {str(h): _agg(rows, ks) for h, rows in sorted(by_hop.items())},
        "latency_ms_mean": _mean([r["latency_ms"] for r in per_q]),
        "top1_score_mean": _mean([r["top1_score"] for r in per_q]),
        "metric_note": (
            "objective paragraph-level retrieval of gold is_supporting ids; "
            "all_hops@k = ALL supporting paragraphs in top-k (multi-hop honest); "
            "judge-free, no external API; Engram's own embedding model"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="MuSiQue multi-hop retrieval (F1 virgin corpus).")
    ap.add_argument("--dataset", type=Path,
                    default=Path("benchmark/data/external/.cache/musique_ans_v1.0_dev.jsonl"))
    ap.add_argument("--ks", type=int, nargs="+", default=[2, 5, 10, 20])
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    res = run(args.dataset, ks=args.ks, sample=args.sample, seed=args.seed)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

    o = res["overall"]
    print(f"MuSiQue F1 | n={res['n_questions']} | model={res['embedding_model']} "
          f"dim={res['embedding_dim']} | lat={res['latency_ms_mean']:.0f}ms top1={res['top1_score_mean']:.3f}")
    ks = res["ks"]
    hdr = "  ".join(f"r@{k} hit@{k} all@{k}" for k in ks)
    print(f"  OVERALL  {hdr}")
    line = "  ".join(f"{o[f'recall@{k}']:.2f} {o[f'hit@{k}']:.2f} {o[f'all_hops@{k}']:.2f}" for k in ks)
    print(f"           {line}   MRR={o['mrr']:.3f}")
    for h, d in res["per_hop"].items():
        line = "  ".join(f"{d[f'recall@{k}']:.2f} {d[f'hit@{k}']:.2f} {d[f'all_hops@{k}']:.2f}" for k in ks)
        print(f"  {h}-hop n={d['n']:4d}  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
