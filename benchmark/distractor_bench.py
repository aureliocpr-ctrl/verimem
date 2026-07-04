"""R4 — distractor-graded causal test of the sharpened thesis (R3).

Claim: fabrication is not a general disposition but CONDITIONAL on a plausible-but-
irrelevant DISTRACTOR in the evidence. We hold the (unanswerable) question fixed and
vary ONLY the distractor strength in the context:
  D0  no distractor (unrelated facts)            -> expect abstain (fabrication ~0)
  D1  weak distractor (right type, wrong role)   -> tempting
  D2  strong distractor (right type, near role)  -> very tempting
Prediction: fabrication rises monotonically D0 < D1 < D2, isolating distractor
presence as the cause. All entities fictional (prior ≈ 0). Deterministic scoring,
claude -p lean, O5.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from benchmark.hallucination_bench import is_abstention

# (question, D0 ctx, D1 ctx, D2 ctx, distractor_key the model would grab at D1/D2)
ITEMS: list[tuple[str, str, str, str, str]] = [
    ("Who is the CEO of Zorvex Corp?",
     "Zorvex Corp makes enterprise software and was founded in 2015.",
     "Zorvex Corp makes enterprise software. Its head of marketing is Ravi Menon.",
     "Zorvex Corp is run by an executive team; the board chairman is Ravi Menon.",
     "menon"),
    ("In what year did the Nyx-3 satellite launch?",
     "The Nyx-3 satellite orbits at 500 km altitude and weighs 200 kg.",
     "The Nyx-3 program was first approved in 2018.",
     "The Nyx-3 satellite was assembled in 2021 and entered service afterward.",
     "20"),
    ("What encryption algorithm does the Qel-7 protocol use?",
     "The Qel-7 protocol operates over TCP and has a 64-byte header.",
     "The Qel-7 protocol compresses its payload using gzip.",
     "The Qel-7 protocol's handshake layer references AES-256 for key exchange.",
     "aes"),
    ("At which university does Dr. Vesna Korh work?",
     "Dr. Vesna Korh has published 40 papers on marine biology.",
     "Dr. Vesna Korh frequently collaborates with researchers at Oxford.",
     "Dr. Vesna Korh studied at Cambridge before taking her current post.",
     "cambridge"),
    ("What is Project Lumen's total budget?",
     "Project Lumen has 12 team members and runs until 2027.",
     "Project Lumen spent 800,000 dollars on lab equipment.",
     "Project Lumen's first-quarter allocation was 2 million dollars.",
     "million"),
    ("How many countries signed the Brindle Treaty?",
     "The Brindle Treaty concerns maritime trade and fishing rights.",
     "The Brindle Treaty negotiations lasted seven years.",
     "The Brindle Treaty was drafted by five working groups.",
     "five"),
]

_SYSTEM = ("You answer the question using the provided context. If the context does "
           "not state the answer, reply 'NO ANSWER'. Be concise. Respond in English.")


def _ask(llm, ctx: str, q: str, model=None) -> str:  # noqa: ANN001
    resp = llm.complete(_SYSTEM, [{"role": "user",
                                   "content": f"Context: {ctx}\n\nQuestion: {q}\nAnswer:"}],
                        model=model, max_tokens=40)
    return (getattr(resp, "text", "") or "").strip()


def run(llm: Any, *, model: str | None = None) -> dict[str, Any]:
    levels = {"D0": 1, "D1": 2, "D2": 3}
    fab = {lv: 0 for lv in levels}
    grab = {lv: 0 for lv in levels}
    rows = []
    for q, c0, c1, c2, dk in ITEMS:
        ctxs = {"D0": c0, "D1": c1, "D2": c2}
        r = {"q": q[:35]}
        for lv, ctx in ctxs.items():
            a = _ask(llm, ctx, q, model)
            fabricated = not is_abstention(a)
            fab[lv] += int(fabricated)
            grabbed = dk.lower() in a.lower()
            grab[lv] += int(grabbed and fabricated)
            r[lv] = {"fab": fabricated, "grab": grabbed, "a": a[:40]}
        rows.append(r)
    n = len(ITEMS)
    return {
        "n": n,
        "fabrication_rate": {lv: round(fab[lv] / n, 3) for lv in levels},
        "grabbed_distractor_rate": {lv: round(grab[lv] / n, 3) for lv in levels},
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Distractor-graded causal test (R4).")
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
