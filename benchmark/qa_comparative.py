"""END-TO-END QA-accuracy head-to-head: Engram pipeline vs a plain-RAG baseline.

This is the comparison Engram never actually ran (the one Aurelio asked for 3 days ago): not
retrieval recall@k (the easy, judge-free sub-metric) but the leaderboard-comparable number —
retrieve -> ANSWER -> JUDGE -> accuracy — for EACH arm, on the SAME questions, with the SAME
judge. The difference between arms is ONLY the retrieval/memory policy.

Arms (same embedder, same k, same answerer, same judge):
  vanilla      bare cosine top-k over e5 (the honest baseline = mem0-without-extraction)
  engram-base  Engram recall, reranker OFF (bi-encoder stack + status/provenance/dedup gates)
  engram       Engram recall, reranker ON (production default)

Honest asterisks (declared, not hidden):
  * Our judge is Claude (claude -p, subscription, ZERO external API — O5); mem0/LongMemEval
    publish numbers judged by GPT-4. So absolute numbers are comparable in METHOD, not
    judge-identical. We use the FAIR rubric (paraphrase-tolerant) the public judges use.
  * We do NOT run mem0/Zep's hosted systems; `vanilla` is a faithful plain-RAG baseline, and a
    fact-EXTRACTION arm (mem0's actual differentiator) is a separate, heavier follow-up.
  * SERIAL claude -p only (concurrent benches hang — measured); n is modest by necessity.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from benchmark.comparative_retrieval import VanillaRAG, _engram_retrieve
from benchmark.longmemeval_runner import session_to_text
from benchmark.qa_eval import answer_question, judge_correct

ARMS = ("vanilla", "engram-base", "engram")


def _retrieve_texts(arm: str, pairs: list[tuple[str, str]], query: str, k: int,
                    *, workdir: Path, qid: str) -> list[str]:
    """Return the retrieved CONTEXT TEXTS (not ids) for one arm."""
    by_id = {sid: text for sid, text in pairs}
    if arm == "vanilla":
        rag = VanillaRAG()
        for sid, text in pairs:
            rag.store(sid, text)
        sids = rag.retrieve(query, k)
    else:
        sids, _ = _engram_retrieve(pairs, query, k, workdir=workdir, qid=qid,
                                   rerank=(arm == "engram"))
    seen: set[str] = set()
    out: list[str] = []
    for sid in sids:
        if sid in seen:
            continue
        seen.add(sid)
        if sid in by_id:
            out.append(by_id[sid])
    return out


def eval_question(q: dict[str, Any], llm: Any, *, k: int, workdir: Path,
                  arms: tuple[str, ...], judge_fair: bool = True) -> dict[str, Any]:
    # The answer system prompt explicitly resolves relative dates "using the
    # [timestamp] prefixes in the context", but the harness was dropping
    # haystack_dates, so temporal-reasoning questions ("how many days between X and
    # Y") had NO dates to compute from (measured temporal-reasoning 0.0). Prefix each
    # session with its date (also part of the stored text, so retrievable). Applies
    # to every arm equally (fair). Env-gated for the A/B that validates the lever:
    # ENGRAM_QA_DATES=0 reproduces the old date-blind behaviour. (2026-06-20)
    import os as _os
    use_dates = _os.environ.get("ENGRAM_QA_DATES", "1").strip().lower() not in (
        "0", "off", "false", "no")
    pairs: list[tuple[str, str]] = []
    dates = q.get("haystack_dates") or []
    for i, (sid, sess) in enumerate(zip(q.get("haystack_session_ids") or [],
                                        q.get("haystack_sessions") or [], strict=False)):
        text = session_to_text(sess)
        if not text:
            continue
        date = dates[i] if i < len(dates) else None
        pairs.append((str(sid), f"[{date}] {text}" if (use_dates and date) else text))
    question = q.get("question", "")
    qdate = q.get("question_date")
    if use_dates and qdate:
        question = f"[Question asked on: {qdate}]\n{question}"
    gold = str(q.get("answer", "") or "")
    qid = str(q.get("question_id", "q"))

    res: dict[str, Any] = {"question_id": qid, "question_type": q.get("question_type"),
                           "arms": {}}
    for arm in arms:
        # Robust per-arm: a single claude -p timeout/error must NOT crash the whole run
        # (it did under rate-limit contention). Record it as an error sample and continue.
        try:
            ctx = _retrieve_texts(arm, pairs, question, k, workdir=workdir, qid=qid)
            pred = answer_question(llm, question, ctx)
            abstained = (not pred.strip()) or pred.strip().upper().startswith("NO ANSWER")
            correct = False if abstained else judge_correct(
                llm, question, gold, pred, fair=judge_fair)
            res["arms"][arm] = {"correct": bool(correct), "abstained": bool(abstained),
                                "n_ctx": len(ctx)}
        except Exception as exc:  # noqa: BLE001 — bench robustness
            res["arms"][arm] = {"correct": False, "abstained": True, "n_ctx": 0,
                                "error": str(exc)[:120]}
    return res


def _stratified(data: list, sample: int) -> list:
    """Pick ~sample questions spread EVENLY across question_type (the first-N of
    LongMemEval_s is all single-session-user — the easiest type; this gives the hard
    types: multi-session / temporal-reasoning / preference). Deterministic (order-based)."""
    from collections import defaultdict
    by_type: dict[str, list] = defaultdict(list)
    for q in data:
        by_type[q.get("question_type") or "?"].append(q)
    types = sorted(by_type)
    per = max(1, sample // len(types))
    out: list = []
    for t in types:
        out.extend(by_type[t][:per])
    return out[:sample] if len(out) >= sample else out


def run(dataset_path: Path | str, llm: Any, *, k: int = 5, sample: int = 40,
        arms: tuple[str, ...] = ARMS, stratify: bool = False) -> dict[str, Any]:
    raw = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    data = _stratified(raw, sample) if stratify else raw[:sample]
    workdir = Path(tempfile.mkdtemp(prefix="qa_cmp_"))
    per_q = [eval_question(q, llm, k=k, workdir=workdir, arms=arms) for q in data]

    def acc(arm: str) -> dict[str, Any]:
        rows = [r["arms"][arm] for r in per_q]
        n = len(rows)
        ncorr = sum(x["correct"] for x in rows)
        nabs = sum(x["abstained"] for x in rows)
        nerr = sum(1 for x in rows if x.get("error"))
        return {"qa_accuracy": round(ncorr / n, 4) if n else 0.0,
                "n_correct": ncorr, "abstention_rate": round(nabs / n, 4) if n else 0.0,
                "n_errors": nerr}

    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in per_q:
        by_type[r.get("question_type") or "?"].append(r)
    return {
        "dataset": str(dataset_path), "k": k, "n_questions": len(per_q),
        "judge": "claude-cli (FAIR rubric); NOT GPT-4 judge — comparable in method not identical",
        "arms": {arm: acc(arm) for arm in arms},
        "per_type_engram": {
            t: round(sum(r["arms"].get("engram", {}).get("correct", False) for r in rows) / len(rows), 3)
            for t, rows in sorted(by_type.items())} if "engram" in arms else {},
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=str,
                   default=str(Path.home() / ".cache/longmemeval/longmemeval_s"))
    p.add_argument("--sample", type=int, default=40)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--arms", type=str, default=",".join(ARMS))
    p.add_argument("--model", type=str, default="claude-sonnet-4-6")
    p.add_argument("--stratify", action="store_true",
                   help="sample evenly across question_type (hard types), not first-N")
    p.add_argument("--out", type=str, default=None)
    a = p.parse_args(argv)
    from benchmark.qa_runner import LeanClaudeCLILLM
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)
    res = run(a.dataset, llm, k=a.k, sample=a.sample, stratify=a.stratify,
              arms=tuple(x.strip() for x in a.arms.split(",") if x.strip()))
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["eval_question", "run", "main"]
