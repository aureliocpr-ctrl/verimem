"""Live QA-accuracy runner: retrieve -> answer -> judge, via claude -p (O5).

Wraps :func:`benchmark.qa_eval.score_qa` with REAL retrieval (Engram
``SemanticMemory``) and the subscription LLM (``engram.llm.ClaudeCLILLM``, no
external API key). Produces the leaderboard-comparable QA-accuracy number that
retrieval recall@k cannot — at the honest cost of an LLM judge (Claude here;
mem0 / LongMemEval judge with GPT-4, declared, so the number is comparable in
METHOD not judge-identical).

Two dataset shapes:
  --bench longmemeval   per question, ingest its haystack, recall top-k context.
  --bench locomo        per conversation, ingest turns, recall top-k per QA.

Each record costs 2 ``claude -p`` calls (~seconds each), so SAMPLE: ``--sample N``
(longmemeval = first N questions) / ``--per-conv N`` (locomo = first N QA per
conversation). The retrieval recall@k numbers (longmemeval_runner /
locomo_runner) remain the robust full-set metric; this is the costlier QA axis.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from benchmark.qa_eval import score_qa
from engram.semantic import Fact, SemanticMemory


class LeanClaudeCLILLM:
    """``claude -p`` stripped of the user's global CLAUDE.md / SessionStart hooks.

    The production ``engram.llm.ClaudeCLILLM`` inherits the full Claude Code
    session context (global CLAUDE.md + hooks ~30k tokens) — noise that pollutes
    a benchmark answer/judge (the model reasons about the user's rules file
    instead of the question). This variant passes ``system`` via
    ``--system-prompt`` (replacing the default) plus ``--setting-sources project
    --exclude-dynamic-system-prompt-sections`` to drop the user-global memory and
    hooks. Subscription only, ZERO API key (O5). MEASURED: 30128 -> ~4228 input
    tokens/call; the answer focuses on the question, not the rules file.
    """

    def __init__(self, *, claude_bin: str = "claude", timeout_s: float = 120.0,
                 model: str | None = None) -> None:
        self.claude_bin = claude_bin
        self.timeout_s = float(timeout_s)
        self.model = model

    def complete(self, system: str, messages: list[dict[str, str]], *,
                 model: str | None = None, temperature: float = 0.0,
                 max_tokens: int | None = None,
                 stop_sequences: list[str] | None = None):  # noqa: ANN201
        import json as _j
        import subprocess as _sp
        import time as _t

        from engram.llm import LLMError, LLMResponse

        sys_parts = [system.strip()] if system else []
        user_parts: list[str] = []
        for m in messages:
            if m.get("role") == "system":
                sys_parts.append(str(m.get("content", "")))
            else:
                user_parts.append(str(m.get("content", "")))
        full_system = "\n\n".join(p for p in sys_parts if p) or "You are a helpful assistant."
        stdin = "\n\n".join(user_parts)
        cmd = [self.claude_bin, "-p", "--output-format", "json",
               "--system-prompt", full_system,
               "--setting-sources", "project",
               "--exclude-dynamic-system-prompt-sections"]
        mdl = model or self.model
        if mdl:
            cmd += ["--model", mdl]
        t0 = _t.time()
        try:
            r = _sp.run(cmd, input=stdin, capture_output=True, text=True,
                        timeout=self.timeout_s, encoding="utf-8")
        except _sp.TimeoutExpired as exc:
            raise LLMError(f"lean claude CLI timeout {self.timeout_s}s") from exc
        if r.returncode != 0:
            raise LLMError(f"lean claude CLI rc={r.returncode}: {(r.stderr or '')[:200]}")
        try:
            d = _j.loads((r.stdout or "").strip())
        except (ValueError, _j.JSONDecodeError) as exc:
            raise LLMError(f"lean claude non-JSON: {(r.stdout or '')[:200]}") from exc
        if d.get("is_error"):
            raise LLMError(f"lean claude error: {str(d.get('result', ''))[:200]}")
        usage = d.get("usage", {}) or {}
        return LLMResponse(
            text=str(d.get("result", "")),
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
            model=mdl or "claude-cli-lean", latency_s=_t.time() - t0)

    def supports_tools(self) -> bool:
        return False


def _cleanup_db(db: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db) + suffix)
        try:
            if p.exists():
                p.unlink()
        except OSError:
            pass


def _recall_context(sm: SemanticMemory, question: str, k: int) -> list[str]:
    hits = sm.recall(question or "", k=k)
    return [getattr(f, "proposition", "") for f, *_ in hits]


_HYDE_SYSTEM = (
    "Write ONE short sentence that plausibly answers the question as if recalled "
    "from a personal conversation. Invent plausible specifics; it is used only to "
    "improve memory retrieval, never shown to a user."
)


def hyde_query(llm, question: str, *, model: str | None = None) -> str:
    """HyDE: ask the LLM for a hypothetical answer and append it to the question,
    so the retrieval query embeds like the casual ANSWER turns (which an abstract
    question — "what martial arts?" vs "I do kickboxing" — embeds far from). The
    coverage study showed gold evidence recall@100 was only 0.76; this closes the
    question/answer phrasing gap. Best-effort: any error falls back to the raw
    question."""
    try:
        resp = llm.complete(
            _HYDE_SYSTEM,
            [{"role": "user",
              "content": f"Question: {question}\nHypothetical recalled answer:"}],
            model=model, max_tokens=64)
        hypo = (getattr(resp, "text", "") or "").strip()
    except Exception:  # noqa: BLE001 — HyDE is an optimisation, never fatal
        hypo = ""
    return f"{question}\n{hypo}" if hypo else question


_EXTRACT_SYSTEM = (
    "Extract atomic, self-contained FACTS from the conversation excerpt. One fact "
    "per line, no numbering. Each fact must name WHO it is about and KEEP any "
    "date/time shown in [brackets]. Capture preferences, events, relationships, "
    "plans, possessions and attributes. Output ONLY the facts, nothing else."
)


def extract_memories(llm, text: str, *, model: str | None = None,
                     max_tokens: int = 1024) -> list[str]:
    """mem0-style: distil a chunk of raw turns into atomic, self-contained facts
    via the LLM. Indexing these (instead of raw casual turns) is the architectural
    difference that closes the abstract-question/casual-turn embedding gap (§7).
    Best-effort: returns [] on any error."""
    try:
        resp = llm.complete(
            _EXTRACT_SYSTEM,
            [{"role": "user", "content": f"Conversation excerpt:\n{text}\n\nFacts:"}],
            model=model, max_tokens=max_tokens)
        out = (getattr(resp, "text", "") or "").strip()
    except Exception:  # noqa: BLE001 — extraction is best-effort, never fatal
        return []
    mems: list[str] = []
    for line in out.splitlines():
        clean = line.strip().lstrip("-•*").strip()
        # strip a leading "1. " / "1) " enumerator if the model added one
        if clean[:2].rstrip(".)").isdigit():
            clean = clean.split(".", 1)[-1].split(")", 1)[-1].strip()
        if len(clean) > 3:
            mems.append(clean)
    return mems


def build_records_longmemeval(
    data: list[dict[str, Any]], *, k: int, workdir: Path | str,
) -> list[dict[str, Any]]:
    """One record per question: ingest its haystack into a hermetic memory,
    recall top-k, attach the gold ``answer`` + ``question_type`` category."""
    from benchmark.longmemeval_runner import session_to_text

    records: list[dict[str, Any]] = []
    for qi, q in enumerate(data):
        db = Path(workdir) / f"lme_{qi}.db"
        sm = SemanticMemory(db_path=db)
        import os as _os
        _chunk = _os.environ.get("ENGRAM_LME_CHUNK", "").strip().lower()
        _sids = q.get("haystack_session_ids") or []
        _sessions = q.get("haystack_sessions") or []
        _dates = q.get("haystack_dates") or []
        for _i, (sid, sess) in enumerate(zip(_sids, _sessions, strict=False)):
            if _chunk in ("turn", "turn_ts"):
                # Chunk a long session into per-turn facts. Engram is tuned for
                # SHORT facts: recall@5 of the gold session 0.80->1.00 and the
                # answer context shrinks from whole sessions to a few short turns
                # (lme_chunk_test.py). turn_ts ALSO prefixes the session date so
                # the answer has the temporal dimension (temporal-reasoning is the
                # weakest category). topic=lme/{sid} preserves the gold mapping.
                _date = _dates[_i] if _i < len(_dates) else None
                _pref = f"[{_date}] " if (_chunk == "turn_ts" and _date) else ""
                for _t in (sess or []):
                    _c = (_t.get("content") or "").strip() if isinstance(_t, dict) else ""
                    if _c:
                        sm.store(Fact(proposition=_pref + _c, topic=f"lme/{sid}",
                                      source_episodes=[str(sid)]))
            else:
                text = session_to_text(sess)
                if text:
                    sm.store(Fact(proposition=text, topic=f"lme/{sid}",
                                  source_episodes=[str(sid)]))
        ctx = _recall_context(sm, q.get("question", ""), k)
        records.append({
            "id": q.get("question_id", f"q{qi}"),
            "question": q.get("question", ""),
            "gold": str(q.get("answer", "")),
            "context": ctx,
            "category": q.get("question_type", "?"),
        })
        _cleanup_db(db)
    return records


def build_records_locomo(
    data: list[dict[str, Any]], *, k: int, workdir: Path | str,
    per_conv: int | None = None, window: int = 0,
    categories: set | None = None, full_context: bool = False,
    hyde_llm: Any = None, hyde_model: str | None = None,
    qa_sample: int | None = None, seed: int = 0,
    extract_llm: Any = None, extract_model: str | None = None,
    extract_chunk: int = 25,
) -> list[dict[str, Any]]:
    """Records per conversation: ingest all turns, then recall top-k per QA
    (capped at ``per_conv`` QA each). Gold = the QA ``answer``.

    ``window`` > 0 stores each turn together with its +/-``window`` neighbours
    (the proposition is the joined window; provenance stays the exact dia_id).
    This enriches the retrieved CONTEXT — measured to help the QA-accuracy axis
    (the answer often lives in a turn ADJACENT to the gold one) even though it
    slightly lowers exact-dia_id recall.
    """
    import random as _random

    from benchmark.locomo_runner import _session_keys

    # Global random QA sampling (representative of the TRUE category mix —
    # first-N-per-conv is heavily skewed). Pick the (conv, qa) pairs up front so
    # only the sampled QA pay the expensive retrieve+answer+judge.
    selected: dict[int, set[int]] | None = None
    if qa_sample is not None:
        pool = [
            (ci, qj)
            for ci, item in enumerate(data)
            for qj, qa in enumerate(item.get("qa") or [])
            if categories is None or qa.get("category") in categories
        ]
        pick = _random.Random(seed).sample(pool, min(qa_sample, len(pool)))
        selected = {}
        for ci, qj in pick:
            selected.setdefault(ci, set()).add(qj)

    records: list[dict[str, Any]] = []
    for ci, item in enumerate(data):
        if selected is not None and ci not in selected:
            continue  # no sampled QA here -> skip the (costly) ingest entirely
        conv = item.get("conversation") or {}
        db = Path(workdir) / f"loco_{ci}.db"
        sm = SemanticMemory(db_path=db)
        seq: list[tuple[str, str]] = []
        for skey in _session_keys(conv):
            # LoCoMo timestamps each session; temporal-reasoning QA needs it to
            # resolve relative references ("yesterday" -> 7 May 2023). Dropping it
            # (the naive ingest) made every temporal question unanswerable.
            sdate = str(conv.get(f"{skey}_date_time") or "").strip()
            for turn in conv[skey] or []:
                if not isinstance(turn, dict):
                    continue
                did = turn.get("dia_id")
                text = (turn.get("text") or "").strip()
                if not did or not text:
                    continue
                speaker = (turn.get("speaker") or "").strip()
                base = f"{speaker}: {text}" if speaker else text
                prop = f"[{sdate}] {base}" if sdate else base
                seq.append((str(did), prop))
        full_seq = [p for _, p in seq]  # full-context ceiling (no retrieval)
        if not full_context and extract_llm is not None:
            # mem0-style: distil atomic memories from chunks of turns, index those
            for n in range(0, len(seq), extract_chunk):
                chunk_text = "\n".join(p for _, p in seq[n:n + extract_chunk])
                for mem in extract_memories(extract_llm, chunk_text,
                                            model=extract_model):
                    sm.store(Fact(proposition=mem, topic=f"locomo/{ci}/mem",
                                  source_episodes=[f"{ci}:c{n}"]))
        elif not full_context:
            for i, (did, prop) in enumerate(seq):
                if window > 0:
                    lo, hi = max(0, i - window), min(len(seq), i + window + 1)
                    prop = "\n".join(p for _, p in seq[lo:hi])
                sm.store(Fact(proposition=prop, topic=f"locomo/{did}",
                              source_episodes=[str(did)]))
        picked: list[tuple[int, dict[str, Any]]] = []
        for qj, qa in enumerate(item.get("qa") or []):
            if selected is not None:
                if qj not in selected[ci]:
                    continue
            else:
                if categories is not None and qa.get("category") not in categories:
                    continue
            picked.append((qj, qa))
            if selected is None and per_conv is not None and len(picked) >= per_conv:
                break
        for qj, qa in picked:  # qj is the ORIGINAL dataset index (stable id)
            # LoCoMo adversarial QA (category 5) carry answer=None: the question
            # is UNANSWERABLE and the correct behaviour is to ABSTAIN, not to
            # fabricate. Mark it so scoring rewards abstention (Engram's moat)
            # instead of string-matching "NO ANSWER" against the literal "None".
            raw_ans = qa.get("answer")
            adversarial = raw_ans is None
            ans = "" if adversarial else raw_ans
            question = qa.get("question", "")
            if full_context:
                ctx = full_seq
            else:
                query = (hyde_query(hyde_llm, question, model=hyde_model)
                         if hyde_llm is not None else question)
                ctx = _recall_context(sm, query, k)
            records.append({
                "id": f"{ci}:{qj}",
                "question": qa.get("question", ""),
                "gold": str(ans),
                "context": ctx,
                "category": str(qa.get("category", "?")),
                "adversarial": adversarial,
            })
        _cleanup_db(db)
    return records


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Live QA-accuracy benchmark (claude -p).")
    p.add_argument("--bench", choices=["longmemeval", "locomo"], required=True)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--sample", type=int, default=None,
                   help="longmemeval: first N questions; locomo: first N conversations")
    p.add_argument("--spread", type=int, default=None,
                   help="pick N items EVENLY spaced across the dataset (spans "
                        "grouped question types — use instead of --sample)")
    p.add_argument("--per-conv", type=int, default=5,
                   help="locomo: cap QA per conversation")
    p.add_argument("--window", type=int, default=0,
                   help="locomo: store each turn with +/-N neighbours (richer context)")
    p.add_argument("--categories", type=str, default=None,
                   help="locomo: keep only these comma-separated category ids (e.g. 1,2)")
    p.add_argument("--full-context", action="store_true",
                   help="locomo: feed the WHOLE conversation (no retrieval) = the ceiling")
    p.add_argument("--hyde", action="store_true",
                   help="locomo: HyDE query expansion (hypothetical answer) before recall")
    p.add_argument("--qa-sample", type=int, default=None,
                   help="locomo: randomly sample N QA across ALL convs (representative mix)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--extract", action="store_true",
                   help="locomo: mem0-style LLM memory extraction at ingest "
                        "(index distilled facts instead of raw turns)")
    p.add_argument("--extract-chunk", type=int, default=25,
                   help="locomo: turns per extraction chunk")
    p.add_argument("--model", type=str, default=None,
                   help="claude CLI model for BOTH answer+judge (e.g. claude-sonnet-4-6)")
    p.add_argument("--answer-model", type=str, default=None,
                   help="override the answerer model (default = --model)")
    p.add_argument("--judge-model", type=str, default=None,
                   help="override the judge model (default = --model)")
    p.add_argument("--raw", action="store_true",
                   help="use the production ClaudeCLILLM (inherits global CLAUDE.md "
                        "~30k tokens) instead of the lean benchmark client")
    p.add_argument("--fair-judge", action="store_true",
                   help="grade with the standard semantic rubric (paraphrase / "
                        "minor-omission tolerant) instead of the strict one")
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    data = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    if args.spread is not None and args.spread > 0 and len(data) > args.spread:
        n = len(data)
        idx = [round(i * (n - 1) / (args.spread - 1)) if args.spread > 1 else 0
               for i in range(args.spread)]
        idx = sorted(set(idx))
        data = [data[i] for i in idx]
    elif args.sample is not None:
        data = data[: max(0, int(args.sample))]

    answer_model = args.answer_model or args.model
    judge_model = args.judge_model or args.model
    if args.raw:
        from engram.llm import ClaudeCLILLM
        answer_llm = ClaudeCLILLM(
            timeout_s=args.timeout,
            extra_args=["--model", answer_model] if answer_model else None)
        judge_llm = ClaudeCLILLM(
            timeout_s=args.timeout,
            extra_args=["--model", judge_model] if judge_model else None)
    else:
        answer_llm = LeanClaudeCLILLM(timeout_s=args.timeout, model=answer_model)
        judge_llm = LeanClaudeCLILLM(timeout_s=args.timeout, model=judge_model)

    workdir = Path(tempfile.mkdtemp(prefix="qa_bench_"))
    try:
        if args.bench == "longmemeval":
            records = build_records_longmemeval(data, k=args.k, workdir=workdir)
        else:
            cats = ({int(x) for x in args.categories.split(",") if x.strip()}
                    if args.categories else None)
            records = build_records_locomo(
                data, k=args.k, workdir=workdir, per_conv=args.per_conv,
                window=args.window, categories=cats,
                full_context=args.full_context,
                hyde_llm=answer_llm if args.hyde else None,
                hyde_model=answer_model,
                qa_sample=args.qa_sample, seed=args.seed,
                extract_llm=answer_llm if args.extract else None,
                extract_model=answer_model, extract_chunk=args.extract_chunk)

        def _progress(done: int, total: int) -> None:
            print(f"  ... {done}/{total}", flush=True)

        res = score_qa(records, answer_llm=answer_llm, judge_llm=judge_llm,
                       on_progress=_progress, fair_judge=args.fair_judge)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    res["bench"] = args.bench
    res["dataset"] = str(args.dataset)
    res["k"] = args.k
    res["window"] = args.window
    res["client"] = "raw-claude-cli" if args.raw else "lean-claude-cli"
    res["answer_model"] = answer_model or "cli-default"
    res["judge_model"] = judge_model or "cli-default"
    res["judge_rubric"] = "fair" if args.fair_judge else "strict"
    res["full_context"] = bool(args.full_context)
    res["hyde"] = bool(args.hyde)
    res["extract"] = bool(args.extract)
    res["judge"] = "claude-cli (subscription; NOT GPT-4 — see BENCHMARKS.md)"
    # keep the output compact: drop per-record details unless writing to file
    summary = {kk: vv for kk, vv in res.items() if kk != "details"}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(res, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_records_longmemeval", "build_records_locomo", "main"]
