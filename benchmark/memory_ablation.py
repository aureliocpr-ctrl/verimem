"""Memory ablation — how much does verimem memory actually help an agent?

The question a buyer asks: on a REAL task, is an agent WITH verified memory
faster / cheaper / more correct than the SAME agent WITHOUT it? This measures
it head-to-head on questions whose answers are verified facts already in the
store AND re-derivable (slowly) from the project source.

Two arms, same model (headless `claude -p`), same questions, same judging:

  WITHOUT memory: the agent is dropped in the project and must EXPLORE the
    codebase (Read/Grep) to answer cold. Measures the re-derivation cost.
  WITH memory:    verimem serves the top-k recall for the question; the agent
    answers from what memory gave it. Measures the served-answer cost.

Per arm, from `claude -p --output-format json`: num_turns (agentic rounds ~=
tool-call rounds), total input tokens PROCESSED (input + cache read + cache
creation), output tokens, duration. Correctness = does the answer contain the
verified ground-truth key? (deterministic substring on a canonical key, plus
the raw answer saved for audit.)

Honest scope: this compares "memory serves the fact" vs "re-derive from
source". It is NOT a claim that the agent could never answer without memory —
it is a measure of the COST (tokens, turns, time) and the correctness delta.

Usage
  python -m benchmark.memory_ablation --n 6            # all arms, real claude -p
  python -m benchmark.memory_ablation --n 6 --dry      # print questions only
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent          # HippoAgent repo root
RESULTS_DIR = Path(__file__).parent / "results"

# (question, verified ground-truth key that MUST appear in a correct answer).
# Every key is a fact stored in memory AND present in the repo (docs/code), so
# both arms CAN answer — the ablation measures the cost + correctness gap.
QUESTIONS: list[tuple[str, str]] = [
    ("What AUROC does the free local CE grounding judge score on the "
     "TruthfulQA heldout out-of-distribution set?", "0.829"),
    ("Which Python file implements the anti-confabulation write-gate function "
     "run_validation_gate?", "anti_confab_gate.py"),
    ("In the 0.7.0 moat, what does the RANK FLOOR prevent — what kind of write "
     "can never supersede a verified fact?", "unverified"),
    ("What is the default value of the balanced preset's `validate` setting in "
     "verimem 0.7.0 (fast or full)?", "full"),
    ("What local ollama model did we benchmark as an offline grounding judge, "
     "and did it beat the CE?", "qwen2.5:7b"),
    ("What cryptographic scheme does tamper anchor-B use to sign the audit "
     "head with an external key?", "ed25519"),
]


def _claude_json(prompt: str, *, cwd: Path, explore: bool,
                 timeout: float = 240.0) -> dict:
    """One headless claude -p call; returns the parsed json (usage + result).
    ``explore`` grants read-only codebase tools for the WITHOUT arm."""
    cmd = ["claude", "-p", "--output-format", "json"]
    if explore:
        # read-only exploration of the repo: the agent may Read/Grep/Glob but
        # the prompt forbids edits; headless needs the permission bypass to run
        # tools at all. (No write tools are used by the task.)
        cmd += ["--dangerously-skip-permissions"]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                           cwd=str(cwd), timeout=timeout,
                           encoding="utf-8", errors="replace")
        d = json.loads(r.stdout or "{}")
    except Exception as exc:  # noqa: BLE001 — a dead run is data
        return {"_error": str(exc)[:160], "_wall_s": round(time.time() - t0, 1)}
    u = d.get("usage", {}) or {}
    total_in = (int(u.get("input_tokens", 0))
                + int(u.get("cache_read_input_tokens", 0))
                + int(u.get("cache_creation_input_tokens", 0)))
    return {
        "answer": str(d.get("result", "")),
        "num_turns": int(d.get("num_turns", 0)),
        "input_tokens_total": total_in,
        "output_tokens": int(u.get("output_tokens", 0)),
        "duration_ms": int(d.get("duration_ms", 0)),
        "_wall_s": round(time.time() - t0, 1),
    }


def _recall_context(mem, question: str, k: int = 5) -> tuple[str, int]:
    """Top-k verimem recall rendered as the memory an agent would be served,
    plus a rough token estimate (chars/4)."""
    hits = mem.search(question, k=k)
    lines = []
    for h in hits:
        txt = h.get("text") if isinstance(h, dict) else getattr(h, "proposition", "")
        if txt:
            lines.append(f"- {txt}")
    block = "\n".join(lines)
    return block, max(1, len(block) // 4)


def run_ablation(n: int) -> dict:
    from verimem.client import Memory
    mem = Memory()
    qs = QUESTIONS[:n]
    rows = []
    for i, (q, key) in enumerate(qs):
        print(f"\n[{i+1}/{len(qs)}] {q}", flush=True)
        # WITHOUT: cold exploration of the repo.
        without_prompt = (
            f"You are in the software project at {PROJECT}. Answer this "
            f"question by exploring the codebase (read files, grep) — do NOT "
            f"edit anything. Give a short, direct answer.\n\nQuestion: {q}")
        without = _claude_json(without_prompt, cwd=PROJECT, explore=True)
        print(f"   WITHOUT: turns={without.get('num_turns')} "
              f"in_tok={without.get('input_tokens_total')} "
              f"{without.get('_wall_s')}s", flush=True)
        # WITH: verimem serves the recall; the agent answers from it.
        ctx, ctx_tok = _recall_context(mem, q)
        with_prompt = (
            f"Answer the question using ONLY this retrieved memory. Give a "
            f"short, direct answer.\n\nRetrieved memory:\n{ctx}\n\nQuestion: {q}")
        withm = _claude_json(with_prompt, cwd=PROJECT, explore=False)
        print(f"   WITH:    turns={withm.get('num_turns')} "
              f"in_tok={withm.get('input_tokens_total')} "
              f"recall_tok={ctx_tok} {withm.get('_wall_s')}s", flush=True)

        def _correct(ans: str) -> bool:
            return key.lower() in (ans or "").lower()
        rows.append({
            "question": q, "ground_truth_key": key, "recall_tokens": ctx_tok,
            "without": {**without, "correct": _correct(without.get("answer", ""))},
            "with": {**withm, "correct": _correct(withm.get("answer", ""))},
        })

    def _agg(arm: str, field: str) -> float:
        vals = [r[arm].get(field, 0) for r in rows if not r[arm].get("_error")]
        return round(sum(vals) / max(1, len(vals)), 1)

    summary = {
        "n": len(rows),
        "without": {
            "mean_turns": _agg("without", "num_turns"),
            "mean_input_tokens": _agg("without", "input_tokens_total"),
            "mean_duration_ms": _agg("without", "duration_ms"),
            "correct": sum(1 for r in rows if r["without"].get("correct")),
        },
        "with": {
            "mean_turns": _agg("with", "num_turns"),
            "mean_input_tokens": _agg("with", "input_tokens_total"),
            "mean_duration_ms": _agg("with", "duration_ms"),
            "correct": sum(1 for r in rows if r["with"].get("correct")),
        },
    }
    w0, w1 = summary["without"]["mean_input_tokens"], summary["with"]["mean_input_tokens"]
    summary["token_reduction_x"] = round(w0 / w1, 1) if w1 else None
    return {"summary": summary, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=len(QUESTIONS))
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    if args.dry:
        for q, key in QUESTIONS[:args.n]:
            print(f"- [{key}] {q}")
        return
    out = run_ablation(args.n)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "memory_ablation.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    s = out["summary"]
    print("\n=== MEMORY ABLATION (with vs without verimem) ===")
    print(f"  WITHOUT (cold explore): turns {s['without']['mean_turns']}  "
          f"input_tok {s['without']['mean_input_tokens']}  "
          f"correct {s['without']['correct']}/{s['n']}")
    print(f"  WITH (memory served):   turns {s['with']['mean_turns']}  "
          f"input_tok {s['with']['mean_input_tokens']}  "
          f"correct {s['with']['correct']}/{s['n']}")
    print(f"  input-token reduction:  {s['token_reduction_x']}x")


if __name__ == "__main__":
    main()
