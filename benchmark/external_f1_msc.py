"""MSC-Self-Instruct memory recall — F1 virgin corpus #2 (task #22).

The PRODUCT case: prior chat sessions ingested as memory, then the user asks
"remember when we talked about X?". Corpus: MemGPT/MSC-Self-Instruct (500
items; MSC multi-session chats, Meta AI). Each item ships 4 previous sessions
(with wall-clock gaps, `time_back`) plus a memory question (`self_instruct.B`)
and its short answer (`self_instruct.A`). Never used in Verimem development.

Judge-free, subscription-safe: gold = the previous-session turns that CONTAIN
the normalized answer string. Declared heuristics (reported, not hidden):
- the questions are GPT-generated (self-instruct), not human-written;
- answer-substring gold can miss paraphrased answers → items whose answer
  appears in NO prior turn are SKIPPED and counted (`n_skipped_no_gold`);
- turns are stored one-per-fact with speaker prefix (dialog granularity).

Provenance: turns are the users' own words → writer_role='user' (task #25
gate_router routes them off the agent-self-claim heuristics, exactly as a
production chat ingest would). Fresh hermetic SemanticMemory per item; never
touches ~/.engram.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from engram.config import CONFIG
from engram.semantic import Fact, SemanticMemory

from benchmark.longmemeval_runner import (
    _unique_preserve,
    hit_at_k,
    mrr,
    recall_at_k,
)

_DEFAULT_DATA = Path("benchmark/data/external/.cache/msc/msc_self_instruct.jsonl")


def _norm(s: str | None) -> str:
    """Lowercase, collapse whitespace, strip punctuation — containment key."""
    return re.sub(r"[^a-z0-9 ]+", "", (s or "").lower().strip())


def flatten_turns(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Previous-session turns as [{tid, session, speaker, text, time_back}]."""
    out: list[dict[str, Any]] = []
    for si, sess in enumerate(item.get("previous_dialogs") or []):
        tb = str(sess.get("time_back") or "").strip()
        for ti, turn in enumerate(sess.get("dialog") or []):
            text = (turn.get("text") or "").strip()
            if not text:
                continue
            out.append({
                "tid": f"{si}:{ti}",
                "session": si,
                "speaker": (turn.get("id") or "").strip(),
                "text": text,
                "time_back": tb,
            })
    return out


def gold_turn_ids(turns: list[dict[str, Any]], answer: str) -> list[str]:
    """Turns whose normalized text contains the normalized answer."""
    key = _norm(answer)
    if not key:
        return []
    return [t["tid"] for t in turns if key in _norm(t["text"])]


def eval_item(item: dict[str, Any], ks: list[int], *,
              workdir: Path | str) -> dict[str, Any] | None:
    """Ingest previous sessions through the real write path, ask the memory
    question, score retrieval of the answer-bearing turns. None = no gold."""
    si = item.get("self_instruct") or {}
    question = (si.get("B") or "").strip()
    answer = (si.get("A") or "").strip()
    turns = flatten_turns(item)
    gold = gold_turn_ids(turns, answer)
    if not question or not gold:
        return None

    db = Path(workdir) / f"{abs(hash(question)) % 10**12}.db"
    sm = SemanticMemory(db_path=db)
    n_stored = 0
    for t in turns:
        sm.store(Fact(
            proposition=f"{t['speaker']}: {t['text']}",
            topic=f"msc/s{t['session']}",
            source_episodes=[t["tid"]],
            writer_role="user",
        ))
        n_stored += 1

    k_max = max(ks)
    t0 = time.perf_counter()
    hits = sm.recall(question, k=k_max)
    latency_ms = (time.perf_counter() - t0) * 1000.0
    retrieved = [(f.source_episodes[0] if f.source_episodes else "")
                 for f, *_ in hits]

    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db) + suffix)
        try:
            if p.exists():
                p.unlink()
        except OSError:
            pass

    per_k = {k: {
        "recall": recall_at_k(retrieved, gold, k),
        "hit": hit_at_k(retrieved, gold, k),
        "mrr": mrr(retrieved, gold),
    } for k in ks}
    return {
        "question": question[:80],
        "n_turns": len(turns),
        "n_stored": n_stored,
        "n_gold": len(gold),
        "latency_ms": round(latency_ms, 2),
        "per_k": per_k,
    }


def _mean(xs: list[Any]) -> float:
    xs = [x for x in xs if x is not None]
    return round(statistics.fmean(xs), 4) if xs else 0.0


def run(dataset_path: Path | str = _DEFAULT_DATA, *,
        ks: list[int] | None = None, sample: int | None = None,
        seed: int = 42, workdir: Path | str | None = None) -> dict[str, Any]:
    ks = sorted(set(ks or [1, 3, 5, 10]))
    items = [json.loads(line) for line in
             Path(dataset_path).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    if sample is not None and sample < len(items):
        import random
        rng = random.Random(seed)
        items = rng.sample(items, sample)

    owns = workdir is None
    workdir = Path(workdir) if workdir else Path(
        tempfile.mkdtemp(prefix="msc_f1_"))
    per_q: list[dict[str, Any]] = []
    skipped = 0
    try:
        for it in items:
            r = eval_item(it, ks, workdir=workdir)
            if r is None:
                skipped += 1
            else:
                per_q.append(r)
    finally:
        if owns:
            shutil.rmtree(workdir, ignore_errors=True)

    overall: dict[str, Any] = {"n": len(per_q)}
    for k in ks:
        overall[f"recall@{k}"] = _mean([r["per_k"][k]["recall"] for r in per_q])
        overall[f"hit@{k}"] = _mean([r["per_k"][k]["hit"] for r in per_q])
    overall["mrr"] = _mean([r["per_k"][ks[0]]["mrr"] for r in per_q])

    return {
        "dataset": str(dataset_path),
        "corpus": "MSC-Self-Instruct (virgin — never used in dev)",
        "ks": ks,
        "n_questions": len(per_q),
        "n_skipped_no_gold": skipped,
        "n_turns_mean": _mean([r["n_turns"] for r in per_q]),
        "embedding_model": CONFIG.embedding_model,
        "embedding_dim": CONFIG.embedding_dim,
        "overall": overall,
        "latency_ms_mean": _mean([r["latency_ms"] for r in per_q]),
        "metric_note": (
            "gold = prior-session turns containing the normalized answer "
            "substring (declared heuristic; paraphrase-only items skipped and "
            "counted); judge-free, no external API; questions are "
            "self-instruct-generated (declared)"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="MSC-Self-Instruct memory recall (F1 virgin corpus #2).")
    ap.add_argument("--dataset", type=Path, default=_DEFAULT_DATA)
    ap.add_argument("--ks", type=int, nargs="+", default=[1, 3, 5, 10])
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    res = run(args.dataset, ks=args.ks, sample=args.sample, seed=args.seed)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(res, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    o = res["overall"]
    print(f"MSC F1 | n={res['n_questions']} (skipped {res['n_skipped_no_gold']} "
          f"no-gold) | turns/item={res['n_turns_mean']:.0f} | "
          f"model={res['embedding_model']} | lat={res['latency_ms_mean']:.0f}ms")
    for k in res["ks"]:
        print(f"  k={k:<3d} recall={o[f'recall@{k}']:.3f}  hit={o[f'hit@{k}']:.3f}")
    print(f"  MRR={o['mrr']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
