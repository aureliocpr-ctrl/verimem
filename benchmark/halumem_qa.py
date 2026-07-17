"""HaluMem QA — faithful reconstruction from OUR gated memory (iter 37).

The extraction-F1 slice is string-overlap and matcher-capped; it cannot show the
thing that actually distances us. HaluMem's per-session `questions` can:

  * 39/164 are **Memory Boundary** — the correct answer is to ABSTAIN ("Unknown;
    not provided"). A system that fabricates (ungated extraction) fails these by
    construction; our anti-confab gate + conservative answerer pass them.
  * 39/164 are **Memory Conflict** — the correct answer is the RECONCILED/current
    fact; our reconcile-on-write is built for this.

So ~48% of the benchmark rewards properties only we have. This runner ingests
each session's dialogue through the PRODUCT pipeline
(``verimem.conversation_ingest.ingest_conversation`` — atomic extraction, optional
gap-fill, consolidation, every fact through the store gate), then answers each
question from the STORED facts alone (recall top-k -> answer -> judge, reusing
``benchmark.qa_eval.score_qa``). The ``--raw-turns`` arm stores turns verbatim
(what mem0/raw ingestion does, no gate) so the delta isolates our contribution.

Answer + judge cost ``claude -p`` (O5, subscription, no API key). Ingest costs
2-3 more per session (extraction/consolidate/gap-fill). SAMPLE with --users /
--sessions. Matching/abstention detection is LOCAL.

    python -m benchmark.halumem_qa --users 5 --k 5 --out results/halumem_qa.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from benchmark.qa_runner import LeanClaudeCLILLM, _cleanup_db, _recall_context
from verimem.semantic import Fact, SemanticMemory

#: Gold answers whose CORRECT behaviour is abstention (HaluMem Memory-Boundary).
#: Scoring these as adversarial rewards NOT fabricating — the moat, on the QA axis.
_ABSTENTION_RE = re.compile(
    r"\bunknown\b|not provided|not mentioned|no information|cannot be|"
    r"can't be|insufficient|not (?:stated|specified|given|available)|"
    r"did not (?:say|mention|provide)|does not (?:say|mention)|"
    r"no (?:record|mention|answer)", re.IGNORECASE)


def _is_abstention_gold(answer: str) -> bool:
    """True if the gold answer signals 'the memory does not contain this' — so the
    correct behaviour is to abstain rather than fabricate."""
    return bool(_ABSTENTION_RE.search(answer or ""))


def _ingest_raw_turns(sm: SemanticMemory, dialogue: list[dict], *,
                      topic: str, asserted_at: float | None = None) -> None:
    """Baseline: store each user/assistant turn verbatim (no extraction, no gate)
    — a stand-in for mem0/raw ingestion, to isolate our pipeline's lift.

    The event-time goes to asserted_at (v13), NEVER created_at: backdating
    created_at trips the anti-spoof + half-life guards and blinds default recall,
    which would sink the baseline arm by harness artefact and inflate the delta."""
    stamp = {"asserted_at": float(asserted_at)} if asserted_at is not None else {}
    for i, t in enumerate(dialogue or []):
        c = (t.get("content") or "").strip()
        if c:
            sm.store(Fact(proposition=c, topic=topic,
                          source_episodes=[f"turn:{i}"], **stamp), embed="sync")


def _parse_halumem_ts(s: str) -> float | None:
    """Parse a HaluMem session/turn stamp ("Sep 04, 2025, 18:42:18") to epoch
    seconds — the SEMANTIC time a fact was asserted, so cross-session updates get
    a real age gap and reconcile-on-write can supersede the stale fact. Best-effort:
    unparseable -> None (fall back to now)."""
    import datetime as _dt
    s = (s or "").strip()
    for fmt in ("%b %d, %Y, %H:%M:%S", "%b %d, %Y, %H:%M", "%b %d, %Y",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return _dt.datetime.strptime(s, fmt).replace(
                tzinfo=_dt.timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def _ingest_session(sm: SemanticMemory, dialogue: list[dict], *, topic: str,
                    conversation_id: str, ingest_llm: Any, raw_turns: bool,
                    completeness: bool, consolidate: bool,
                    max_out_tokens: int, asserted_at: float | None = None) -> None:
    from verimem.conversation_ingest import ingest_conversation
    if raw_turns:
        _ingest_raw_turns(sm, dialogue, topic=topic, asserted_at=asserted_at)
    else:
        msgs = [{"role": t.get("role", "user"), "content": t.get("content", "")}
                for t in dialogue if (t.get("content") or "").strip()]
        ingest_conversation(
            sm, msgs, llm=ingest_llm, conversation_id=conversation_id,
            topic=topic, completeness=completeness, consolidate=consolidate,
            max_out_tokens=max_out_tokens, asserted_at=asserted_at, embed="sync")


def _emit_question_records(records: list, sm: SemanticMemory, questions: list, *,
                           k: int, prefix: str, per_session_qa: int | None,
                           history: bool = False) -> None:
    qs = questions[:per_session_qa] if per_session_qa else questions
    for qj, q in enumerate(qs):
        gold = str(q.get("answer", ""))
        cat = str(q.get("question_type", "?"))
        adversarial = _is_abstention_gold(gold) or cat == "Memory Boundary"
        if history:
            # answer-with-history: the context line carries the supersession
            # TRANSITION story + declared disputes — Memory-Conflict golds
            # narrate transitions ("from X to Y"), which a reconciled store
            # serving only the current value forfeits (measured failure mode).
            from verimem.temporal_context import recall_with_history
            ctx = recall_with_history(sm, q.get("question", ""), k=k)
        else:
            ctx = _recall_context(sm, q.get("question", ""), k)
        records.append({
            "id": f"{prefix}:{qj}",
            "question": q.get("question", ""),
            "gold": "" if adversarial else gold,
            "context": ctx,
            "category": cat,
            "adversarial": adversarial,
        })


def build_records_halumem(
    users: list[dict[str, Any]], *, k: int, workdir: Path | str,
    ingest_llm: Any, completeness: bool = False, consolidate: bool = True,
    raw_turns: bool = False, per_session_qa: int | None = None,
    max_out_tokens: int = 1200, cumulative: bool = True,
    reconcile: bool = False, history: bool = False,
) -> list[dict[str, Any]]:
    """One record per question. ``cumulative`` (default, realistic): ALL a user's
    sessions ingest into ONE store before answering, so cross-session
    Memory-Conflict facts coexist and reconcile-on-write can retire the stale one
    (per-session isolation made those questions unanswerable — measured 0/10).
    ``reconcile`` wires the local NLI conflict judge on the store (auto-supersede
    is env-gated: ENGRAM_RECONCILE_ON_WRITE/AUTO_SUPERSEDE). Memory-Boundary /
    abstention golds are flagged ``adversarial`` so scoring rewards abstention."""
    records: list[dict[str, Any]] = []
    for ui, u in enumerate(users):
        sessions = [s for s in (u.get("sessions", []) or [])
                    if s.get("questions")]
        if not sessions:
            continue
        if cumulative:
            db = Path(workdir) / f"hm_u{ui}.db"
            sm = SemanticMemory(db_path=db)
            if reconcile:
                from verimem.agent import wire_reconcile_judge
                wire_reconcile_judge(sm, ingest_llm)
            for si, s in enumerate(u.get("sessions", []) or []):  # ingest ALL
                _ingest_session(
                    sm, s.get("dialogue") or [], topic=f"halumem/{ui}/{si}",
                    conversation_id=f"{ui}:{si}", ingest_llm=ingest_llm,
                    raw_turns=raw_turns, completeness=completeness,
                    consolidate=consolidate, max_out_tokens=max_out_tokens,
                    asserted_at=_parse_halumem_ts(s.get("start_time", "")))
            for si, s in enumerate(u.get("sessions", []) or []):  # then answer
                _emit_question_records(records, sm, s.get("questions") or [],
                                       k=k, prefix=f"{ui}:{si}",
                                       per_session_qa=per_session_qa,
                                       history=history)
            _cleanup_db(db)
        else:
            for si, s in enumerate(u.get("sessions", []) or []):
                if not s.get("questions"):
                    continue
                db = Path(workdir) / f"hm_{ui}_{si}.db"
                sm = SemanticMemory(db_path=db)
                _ingest_session(
                    sm, s.get("dialogue") or [], topic=f"halumem/{ui}/{si}",
                    conversation_id=f"{ui}:{si}", ingest_llm=ingest_llm,
                    raw_turns=raw_turns, completeness=completeness,
                    consolidate=consolidate, max_out_tokens=max_out_tokens,
                    asserted_at=_parse_halumem_ts(s.get("start_time", "")))
                _emit_question_records(records, sm, s.get("questions") or [],
                                       k=k, prefix=f"{ui}:{si}",
                                       per_session_qa=per_session_qa,
                                       history=history)
                _cleanup_db(db)
    return records


def main(argv: list[str] | None = None) -> int:
    from benchmark.qa_eval import score_qa

    ap = argparse.ArgumentParser(description="HaluMem faithful-QA (claude -p).")
    ap.add_argument("--jsonl",
                    default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--users", type=int, default=5)
    ap.add_argument("--sessions", type=int, default=None,
                    help="cap sessions/user (default all)")
    ap.add_argument("--per-session-qa", type=int, default=None,
                    help="cap questions/session (default all)")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--consolidate", action="store_true", default=True)
    ap.add_argument("--no-consolidate", dest="consolidate", action="store_false")
    ap.add_argument("--completeness", action="store_true",
                    help="gap-fill recall pass at ingest (extract->gapfill->consolidate)")
    ap.add_argument("--raw-turns", action="store_true",
                    help="BASELINE arm: store turns verbatim (no extraction, no gate)")
    ap.add_argument("--reconcile", action="store_true",
                    help="enable reconcile-on-write (auto-supersede stale facts on "
                         "cross-session Memory-Conflict) with the LOCAL NLI judge")
    ap.add_argument("--reconcile-min-overlap", type=float, default=0.35,
                    help="precision floor for auto-supersede (0.35 measured to "
                         "keep only same-attribute updates; 0 = destructive)")
    ap.add_argument("--history", action="store_true",
                    help="answer-with-history context: each hit carries its "
                         "supersession TRANSITION story + declared disputes "
                         "(verimem.temporal_context) — the transition-QA lever")
    ap.add_argument("--cumulative", action="store_true", default=True)
    ap.add_argument("--per-session", dest="cumulative", action="store_false",
                    help="ablation: isolate each session (breaks cross-session QA)")
    ap.add_argument("--max-out-tokens", type=int, default=1200)
    ap.add_argument("--model", default="claude-sonnet-4-6",
                    help="claude CLI model for ingest + answer + judge")
    ap.add_argument("--fair-judge", action="store_true")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)

    users: list[dict[str, Any]] = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))
    users = users[: a.users]
    if a.sessions is not None:
        for u in users:
            u["sessions"] = (u.get("sessions") or [])[: a.sessions]

    if a.reconcile:
        os.environ.setdefault("ENGRAM_RECONCILE_ON_WRITE", "1")
        os.environ.setdefault("ENGRAM_RECONCILE_AUTO_SUPERSEDE", "1")
        os.environ.setdefault("ENGRAM_RECONCILE_NLI", "local")
        # Precision floor is MANDATORY with auto-supersede: at floor 0 the NLI
        # over-called cross-attribute pairs and retired 99/165 facts (birth-date
        # dropped for an unrelated fact). 0.35 kept only same-attribute updates
        # (measured). Also gates the O(N^2) NLI pre-screen (perf).
        os.environ.setdefault("ENGRAM_RECONCILE_MIN_OVERLAP",
                              str(a.reconcile_min_overlap))

    llm = LeanClaudeCLILLM(timeout_s=a.timeout, model=a.model)
    workdir = Path(tempfile.mkdtemp(prefix="halumem_qa_"))
    try:
        records = build_records_halumem(
            users, k=a.k, workdir=workdir, ingest_llm=llm,
            completeness=a.completeness, consolidate=a.consolidate,
            raw_turns=a.raw_turns, per_session_qa=a.per_session_qa,
            max_out_tokens=a.max_out_tokens, cumulative=a.cumulative,
            reconcile=a.reconcile, history=a.history)

        def _progress(done: int, total: int) -> None:
            print(f"  ... {done}/{total}", flush=True)

        res = score_qa(records, answer_llm=llm, judge_llm=llm,
                       on_progress=_progress, fair_judge=a.fair_judge)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    res["bench"] = "halumem_qa"
    res["k"] = a.k
    res["arm"] = ("raw-turns" if a.raw_turns
                  else f"pipeline(consolidate={a.consolidate},"
                       f"completeness={a.completeness})")
    res["cumulative"] = bool(a.cumulative)
    res["reconcile"] = bool(a.reconcile)
    res["history"] = bool(a.history)
    res["model"] = a.model
    res["grounding_gate"] = os.environ.get("ENGRAM_GROUNDING_GATE", "")
    res["judge"] = "claude-cli (subscription; NOT GPT-4 — see BENCHMARKS.md)"
    summary = {kk: vv for kk, vv in res.items() if kk != "details"}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_records_halumem", "_is_abstention_gold", "main"]
