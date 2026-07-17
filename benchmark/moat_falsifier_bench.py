"""R20 — honest moat falsifier: realistic distribution + generator != judge.

R19 (adversarial workflow) flagged that the moat's AUROC 0.97-1.0 is measured on SNLI /
SQuAD / hand-authored template suites, which may be EASIER than real extraction
confabulations, and that the real-corpus FP ~0.77 is a counter-signal. This bench attacks
both validity holes:
  * DISTRIBUTION: longer, multi-fact source passages; the confabulation is a MODEL-GENERATED
    plausible-but-unstated inference (subtle), not a hand-authored entity/number swap.
  * GENERATOR != JUDGE: a DIFFERENT model (haiku) generates the (faithful, confab) pair; the
    gate (sonnet) judges. Same family (O5: Claude-only) so this is a PARTIAL mitigation of
    the shared-prior circularity, stated honestly — not a different vendor.

Pre-registered falsifier: if AUROC(faithful vs confab) on this realistic, generator!=judge
set is < 0.85 (vs the claimed 0.97-1.0), the "model-general 0.97-1.0" moat is FALSIFIED and
downgraded to "easy-distribution only." Reported with CI (bootstrap). claude -p serial, O5.
"""
from __future__ import annotations

import argparse
import json
import re
from typing import Any

from benchmark.stats import auroc, bootstrap_ci
from verimem.grounding_gate import fact_grounding_score

# Rich, multi-fact fictional passages (prior ~ 0; long, with numbers/dates/relations).
PASSAGES: list[str] = [
    "The Veldran Institute, founded in 1962 in the city of Oost, operates three research "
    "wings. Its flagship instrument, the Calwen spectrometer, was installed in 2014 and "
    "resolves features down to 0.8 nanometres. The institute is directed by Prof. Ima Sarn "
    "and employs 240 staff across optics, materials, and computation.",
    "Project Harrow is a five-year marine survey that began in 2021 and is funded jointly "
    "by the Delmar Trust and the city of Pell. Its research vessel, the Anwen, carries a "
    "sonar array rated to 6,000 metres and a crew of 18. The survey has so far catalogued "
    "412 species along the eastern shelf.",
    "The Qel-9 messaging protocol, ratified by the Brindle Working Group in 2019, uses "
    "AES-256 for payload encryption and a 64-byte header. It supports up to 1,024 "
    "concurrent channels and was designed primarily for low-latency industrial telemetry, "
    "not for public internet traffic.",
    "Dr. Vesna Korh joined Aldous University in 2015 after a decade at the Marlowe Centre. "
    "She studies deep-sea bioluminescence, has published 47 peer-reviewed papers, and leads "
    "a team of nine. Her 2022 monograph on photophore evolution won the Tarn Prize.",
    "The Sennar Dam, completed in 1978 on the Ashen River, generates 340 megawatts and "
    "supplies water to roughly 1.2 million residents of the Calbry basin. It is operated by "
    "the regional authority and underwent a turbine refit in 2016.",
    "The Aster Festival, established in 1998, draws about 120,000 visitors to the town of "
    "Lindholm each September. It is organised by the Lindholm Cultural Society, runs for "
    "nine days, and features 60 stages. Ticket revenue funds the town's library year-round.",
    "The Orrel-2 spacecraft, launched in 2014 by the Mersk Agency, weighs 1,800 kilograms "
    "and carries a hyperspectral imager plus a magnetometer. It reached its operational "
    "polar orbit at 720 kilometres after a four-month commissioning phase.",
    "Calvenir, a cardiovascular drug approved in 2016, is dosed at 50 milligrams daily and "
    "was developed by Pell Therapeutics. In its phase-III trial of 2,300 patients it reduced "
    "the primary endpoint by 19 percent versus placebo, with mild headache the most common "
    "side effect.",
]

_GEN_SYSTEM = (
    "You read a source passage and output TWO claims about it as JSON. 'faithful' = a "
    "specific fact the passage EXPLICITLY states. 'confab' = a plausible, on-topic claim a "
    "careless reader might believe but that the passage does NOT state (a subtle inference, "
    "an unstated number/cause/superlative — NOT a blatant contradiction). Both must sound "
    "equally confident. Output ONLY: {\"faithful\": \"...\", \"confab\": \"...\"}")

_JSON = re.compile(r"\{.*\}", re.S)


def _generate(gen_llm: Any, passage: str) -> tuple[str, str] | None:
    raw = gen_llm.complete(_GEN_SYSTEM, [{"role": "user", "content": f"Passage: {passage}"}],
                           max_tokens=200)
    m = _JSON.search(getattr(raw, "text", "") or "")
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        f, c = str(d.get("faithful", "")).strip(), str(d.get("confab", "")).strip()
        return (f, c) if (f and c and f != c) else None
    except (ValueError, TypeError):
        return None


def run(judge_llm: Any, gen_llm: Any, *, judge_model: str | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for p in PASSAGES:
        pair = _generate(gen_llm, p)
        if pair is None:
            continue
        faithful, confab = pair
        sf = fact_grounding_score(judge_llm, p, faithful, model=judge_model)
        sc = fact_grounding_score(judge_llm, p, confab, model=judge_model)
        rows.append({"faithful_score": sf, "confab_score": sc,
                     "faithful": faithful[:80], "confab": confab[:80]})
    if not rows:
        return {"error": "no generated pairs"}
    scores = [r["faithful_score"] for r in rows] + [r["confab_score"] for r in rows]
    labels = [1] * len(rows) + [0] * len(rows)
    point, lo, hi = bootstrap_ci(scores, labels, b=3000, seed=0)
    mf = sum(r["faithful_score"] for r in rows) / len(rows)
    mc = sum(r["confab_score"] for r in rows) / len(rows)
    return {
        "n_pairs": len(rows),
        "auroc": round(auroc(scores, labels), 3),
        "ci95": [round(lo, 3), round(hi, 3)],
        "mean_faithful": round(mf, 1), "mean_confab": round(mc, 1),
        "falsified_below_0_85": bool(point < 0.85),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Realistic generator!=judge moat falsifier (R20).")
    p.add_argument("--judge-model", type=str, default="claude-sonnet-4-6")
    p.add_argument("--gen-model", type=str, default="claude-haiku-4-5")
    p.add_argument("--out", type=argparse.FileType("w"), default=None)
    args = p.parse_args(argv)
    from benchmark.qa_runner import LeanClaudeCLILLM
    judge = LeanClaudeCLILLM(model=args.judge_model, timeout_s=60)
    gen = LeanClaudeCLILLM(model=args.gen_model, timeout_s=60)
    res = run(judge, gen, judge_model=None)
    res["judge_model"] = args.judge_model
    res["gen_model"] = args.gen_model
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    if args.out:
        json.dump(res, args.out, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["PASSAGES", "run", "main"]
