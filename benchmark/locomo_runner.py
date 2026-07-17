"""Real LoCoMo retrieval benchmark for Engram (judge-free, subscription-safe).

LoCoMo (arXiv 2402.17753, snap-research/locomo) ships 10 long multi-session
conversations; each carries ~200 QA, every QA tagged with the gold evidence
turns it needs (``evidence`` = list of ``dia_id`` like "D1:3"). That lets us
measure Engram's RETRIEVAL quality OBJECTIVELY — recall@k / hit@k / MRR of the
gold evidence turns — with NO LLM judge and NO external API (CLAUDE.md O5). The
end-to-end QA-correctness score (which needs an LLM judge) is deliberately NOT
computed here; this is the honest retrieval number we can prove today, on the
same dataset mem0 reports.

Mapping: each conversation is one hermetic ``SemanticMemory``; each turn ->
one ``Fact`` (proposition = "speaker: text", provenance ``source_episodes=[dia_id]``).
Per QA we recall the question and score the retrieved dia_ids vs the gold
evidence. Never touches ~/.engram (explicit db_path under a temp workdir).

Honest caveat: turn-level retrieval; QA with empty/non-turn evidence (e.g. the
adversarial category) are skipped from the recall metric (gold is undefined).
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from benchmark.longmemeval_runner import (
    _mean,
    hit_at_k,
    mrr,
    recall_at_k,
)
from verimem.config import CONFIG
from verimem.semantic import Fact, SemanticMemory


def _session_keys(conversation: dict[str, Any]) -> list[str]:
    return [
        k for k in conversation
        if k.startswith("session_") and not k.endswith("date_time")
    ]


def _gold_evidence(qa: dict[str, Any]) -> list[str]:
    """Keep only turn-id evidence ('D<sess>:<turn>'); drop empty/non-turn refs."""
    ev = qa.get("evidence") or []
    if not isinstance(ev, list):
        return []
    return [e for e in ev if isinstance(e, str) and e.startswith("D") and ":" in e]


def eval_conversation(
    item: dict[str, Any], k: int, *, workdir: Path | str,
) -> list[dict[str, Any]]:
    """Ingest one conversation's turns into a fresh hermetic memory, then score
    every answerable QA against the gold evidence turns."""
    conversation = item.get("conversation") or {}
    sample_id = str(item.get("sample_id", "conv"))
    db = Path(workdir) / f"{sample_id}.db"
    sm = SemanticMemory(db_path=db)

    n_turns = 0
    for skey in _session_keys(conversation):
        for turn in conversation[skey] or []:
            if not isinstance(turn, dict):
                continue
            did = turn.get("dia_id")
            text = (turn.get("text") or "").strip()
            if not did or not text:
                continue
            speaker = (turn.get("speaker") or "").strip()
            prop = f"{speaker}: {text}" if speaker else text
            sm.store(Fact(proposition=prop, topic=f"locomo/{did}",
                          source_episodes=[str(did)]))
            n_turns += 1

    per_q: list[dict[str, Any]] = []
    for qa in item.get("qa") or []:
        gold = _gold_evidence(qa)
        if not gold:
            continue  # unanswerable / no turn-level evidence -> skip from recall
        hits = sm.recall(qa.get("question", ""), k=k)
        retrieved = [
            (f.source_episodes[0] if f.source_episodes else "") for f, *_ in hits
        ]
        per_q.append({
            "category": qa.get("category"),
            "n_gold": len(gold),
            "n_turns": n_turns,
            "recall_at_k": recall_at_k(retrieved, gold, k),
            "hit_at_k": hit_at_k(retrieved, gold, k),
            "mrr": mrr(retrieved, gold),
        })

    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db) + suffix)
        try:
            if p.exists():
                p.unlink()
        except OSError:
            pass
    return per_q


def run_dataset(
    dataset_path: Path | str, *, k: int = 5, sample: int | None = None,
    workdir: Path | str | None = None,
) -> dict[str, Any]:
    data = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    if sample is not None:
        data = data[: max(0, int(sample))]
    owns = workdir is None
    workdir = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="locomo_"))
    per_q: list[dict[str, Any]] = []
    try:
        for item in data:
            per_q.extend(eval_conversation(item, k, workdir=workdir))
    finally:
        if owns:
            shutil.rmtree(workdir, ignore_errors=True)

    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in per_q:
        by_cat[str(r.get("category"))].append(r)
    per_cat = {
        c: {
            "n": len(rows),
            "recall_at_k": _mean([r["recall_at_k"] for r in rows]),
            "hit_at_k": _mean([r["hit_at_k"] for r in rows]),
            "mrr": _mean([r["mrr"] for r in rows]),
        }
        for c, rows in sorted(by_cat.items())
    }
    return {
        "dataset": str(dataset_path),
        "k": k,
        "n_conversations": len(data),
        "n_qa_scored": len(per_q),
        "embedding_model": CONFIG.embedding_model,
        "embedding_dim": CONFIG.embedding_dim,
        "overall": {
            "recall_at_k": _mean([r["recall_at_k"] for r in per_q]),
            "hit_at_k": _mean([r["hit_at_k"] for r in per_q]),
            "mrr": _mean([r["mrr"] for r in per_q]),
        },
        "per_category": per_cat,
        "metric_note": (
            "turn-level retrieval recall@k of gold evidence dia_ids; judge-free, "
            "no external API; embedding via Engram's own model. Unanswerable QA "
            "(no turn evidence) excluded from the recall metric."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="LoCoMo retrieval benchmark for Engram.")
    p.add_argument("--dataset", type=Path, required=True,
                   help="Path to locomo10.json")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--sample", type=int, default=None,
                   help="Run only the first N conversations.")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)
    res = run_dataset(args.dataset, k=args.k, sample=args.sample)
    print(json.dumps(res, indent=2))
    if args.out:
        args.out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["eval_conversation", "run_dataset"]
