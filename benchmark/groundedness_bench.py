"""Groundedness as counterfactual evidence-dependence (Definition 1, test T1 of
docs/EPISTEMIC_FAILURES_STUDY.md). The mathematically-motivated experiment.

We use FICTIONAL facts the model cannot know from its prior, so the ONLY possible
source of a correct answer is the provided note. For each item we ask the same
question under three conditions:
  - note_x  ("F is X")  -> a grounded model answers X
  - note_y  ("F is Y")  -> a grounded model answers Y   (the answer TRACKS evidence)
  - no_note             -> a grounded model ABSTAINS (it cannot know)
A perfectly GROUNDED model's output is a function of the evidence (X→X, Y→Y,
none→abstain). An UNGROUNDED model gives an evidence-INVARIANT answer (fabricates a
value with no note, or fails to flip when the note flips). The per-item groundedness
is the fraction of the three conditions answered as a grounded model would; the key
counterfactual signal is the no-evidence FABRICATION rate. Deterministic scoring
(is_abstention + keyword), claude -p lean, O5.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from benchmark.hallucination_bench import is_abstention

# (subject, question, fact_x, fact_y, key_x, key_y) — all fictional (prior ≈ 0).
ITEMS: list[tuple[str, str, str, str, str, str]] = [
    ("Zorvex Corp", "Where is Zorvex Corp's headquarters?",
     "Zorvex Corp's headquarters is in Helsinki.",
     "Zorvex Corp's headquarters is in Lisbon.", "helsinki", "lisbon"),
    ("the Qel-7 protocol", "What encryption does the Qel-7 protocol use?",
     "The Qel-7 protocol uses AES-256 encryption.",
     "The Qel-7 protocol uses ChaCha20 encryption.", "aes", "chacha"),
    ("Dr. Vesna Korh", "What field does Dr. Vesna Korh study?",
     "Dr. Vesna Korh studies marine biology.",
     "Dr. Vesna Korh studies astrophysics.", "marine", "astrophysics"),
    ("the Nyx-3 satellite", "In what year did the Nyx-3 satellite launch?",
     "The Nyx-3 satellite launched in 2019.",
     "The Nyx-3 satellite launched in 2023.", "2019", "2023"),
    ("Project Lumen", "What is Project Lumen's budget?",
     "Project Lumen's budget is 2 million dollars.",
     "Project Lumen's budget is 5 million dollars.", "2 million", "5 million"),
    ("Tarq Industries", "Who is the CEO of Tarq Industries?",
     "The CEO of Tarq Industries is Ravi Menon.",
     "The CEO of Tarq Industries is Lena Foss.", "menon", "foss"),
    ("the Brindle Treaty", "In what year was the Brindle Treaty signed?",
     "The Brindle Treaty was signed in 1847.",
     "The Brindle Treaty was signed in 1923.", "1847", "1923"),
    ("the Klyx language", "What language family does Klyx belong to?",
     "The Klyx language belongs to the Uralic family.",
     "The Klyx language belongs to the Bantu family.", "uralic", "bantu"),
]

_SYSTEM = ("You answer the question using the provided note. If no note is given or "
           "it does not contain the answer, reply exactly 'NO ANSWER'. Be concise. "
           "Always respond in English.")


def _ask(llm, note: str | None, question: str, model=None) -> str:  # noqa: ANN001
    ctx = f"Note: {note}\n\n" if note else "Note: (none)\n\n"
    resp = llm.complete(_SYSTEM, [{"role": "user",
                                   "content": f"{ctx}Question: {question}\nAnswer:"}],
                        model=model, max_tokens=40)
    return (getattr(resp, "text", "") or "").strip()


def run(llm: Any, *, model: str | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for _subj, q, fx, fy, kx, ky in ITEMS:
        ax = _ask(llm, fx, q, model)
        ay = _ask(llm, fy, q, model)
        an = _ask(llm, None, q, model)
        tracks_x = kx in ax.lower() and not is_abstention(ax)
        tracks_y = ky in ay.lower() and not is_abstention(ay)
        abstains_none = is_abstention(an)
        grounded3 = int(tracks_x) + int(tracks_y) + int(abstains_none)
        rows.append({"q": q[:40], "tracks_x": tracks_x, "tracks_y": tracks_y,
                     "abstains_none": abstains_none, "grounded3": grounded3,
                     "no_note_answer": an[:50]})
    n = len(ITEMS)
    return {
        "n": n,
        "groundedness_rate": round(sum(r["grounded3"] for r in rows) / (3 * n), 3),
        "tracking_rate": round(
            sum(r["tracks_x"] + r["tracks_y"] for r in rows) / (2 * n), 3),
        "no_evidence_fabrication_rate": round(
            sum(1 for r in rows if not r["abstains_none"]) / n, 3),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Counterfactual groundedness bench (T1).")
    p.add_argument("--model", type=str, default="claude-sonnet-4-6")
    p.add_argument("--out", type=argparse.FileType("w"), default=None)
    args = p.parse_args(argv)
    from benchmark.qa_runner import LeanClaudeCLILLM
    res = run(LeanClaudeCLILLM(model=args.model, timeout_s=60))
    res["model"] = args.model
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    if args.out:
        json.dump(res, args.out, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["ITEMS", "run", "main"]
