"""A/B the write-gate judge prompt V1 (_FACT_SYSTEM) vs V3 (per-detail audit) on the
residual miss class the external sweep exposed: one-detail-wrong confabs (unsupported
temporal details, entity-role swaps, altered numbers) that V1 scores >= 70.

NOT a retry of the 2026-06-21 A/B (that targeted OVER-rejection with an abstraction-
crediting prompt and was falsified). V3 targets UNDER-detection: it instructs the judge
to check EVERY atomic detail and to floor the score when ANY detail is unsupported.
Output contract unchanged ('SCORE: N', max_tokens=12) so parsing and latency hold.

Design: re-score with V3 the SAME HaluEval 120 pairs (seed 42) already measured with V1
(results/moat_external_judge_sonnet_2026-07-17.json), same model, same threshold 70 —
paired comparison, no fresh V1 calls. Guard: the 12 realistic faithful facts of
grounding_conditioned_qa_real MUST stay admitted (>=70) under V3.

    python -m benchmark.judge_prompt_v3_ab --model claude-sonnet-5 \
        --out benchmark/results/judge_prompt_v3_ab.json
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

RESULTS = Path(__file__).parent / "results"

#: V3 candidate — per-detail audit. Same output contract as _FACT_SYSTEM.
FACT_SYSTEM_V3 = (
    "You verify whether a SOURCE supports a candidate FACT for storage in a memory. "
    "Silently check EVERY atomic detail the fact asserts — each entity, number, date, "
    "place, role, comparison and relation — against the source. Rate 0-100: 100 = every "
    "detail is stated or unambiguously entailed by the source. If even ONE detail is "
    "unsupported, altered or contradicted (wrong number, swapped role or subject, added "
    "time/place, reversed comparison), score 0-30. 50 = the source is topically related "
    "but does not establish the fact. Judge MEANING, not word overlap. Reply with "
    "exactly 'SCORE: N'.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--v1-json",
                    default="benchmark/results/moat_external_judge_sonnet_2026-07-17.json")
    ap.add_argument("--threshold", type=float, default=70.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    os.environ["ENGRAM_GROUNDING_BACKEND"] = "claude"
    from benchmark.grounding_conditioned_qa_real import CASES
    from benchmark.moat_external_judge import _LOADERS, _auroc
    from benchmark.qa_runner import LeanClaudeCLILLM
    from engram.grounding_gate import fact_grounding_score_ex
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)

    v1 = json.loads(Path(a.v1_json).read_text(encoding="utf-8"))
    r1 = v1["per_corpus"]["halueval"]
    pairs = _LOADERS["halueval"](len(r1["rows"]), v1.get("seed", 42))
    assert len(pairs) == len(r1["rows"])

    # --- V3 on the same 120 halueval pairs -------------------------------------
    pos3, neg3, rows3 = [], [], []
    for i, (p, row1) in enumerate(zip(pairs, r1["rows"])):
        s3, _ = fact_grounding_score_ex(llm, p["source"], p["claim"],
                                        system=FACT_SYSTEM_V3)
        (pos3 if p["label"] == 1 else neg3).append(s3)
        rows3.append({"label": p["label"], "v1": row1["score"],
                      "v3": round(s3, 1), "claim": p["claim"][:140]})
        print(f"  [{i+1}/{len(pairs)}] label={p['label']} "
              f"v1={row1['score']:<6} v3={s3:.0f}")

    t = a.threshold
    v1_pos = [r["score"] for r in r1["rows"] if r["label"] == 1]
    v1_neg = [r["score"] for r in r1["rows"] if r["label"] == 0]

    def _rates(pos, neg):
        return {"auroc": _auroc(pos, neg),
                "admit": round(sum(s >= t for s in pos) / len(pos), 4),
                "block": round(sum(s < t for s in neg) / len(neg), 4)}

    # --- guard: the 12 realistic faithful facts must stay admitted under V3 ----
    guard = []
    for src, _q, _gold, true_f, dist in CASES:
        sf, _ = fact_grounding_score_ex(llm, src, true_f, system=FACT_SYSTEM_V3)
        sd, _ = fact_grounding_score_ex(llm, src, dist, system=FACT_SYSTEM_V3)
        guard.append({"true_score": round(sf, 1), "dist_score": round(sd, 1)})
        print(f"  guard: true={sf:.0f} dist={sd:.0f}")
    guard_admit = sum(g["true_score"] >= t for g in guard)
    guard_block = sum(g["dist_score"] < t for g in guard)

    res = {"model": a.model, "threshold": t,
           "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "halueval_v1": _rates(v1_pos, v1_neg),
           "halueval_v3": _rates(pos3, neg3),
           "guard_faithful_admitted": f"{guard_admit}/12",
           "guard_confab_blocked": f"{guard_block}/12",
           "rows": rows3, "guard": guard,
           "v3_system": FACT_SYSTEM_V3}
    print(f"\n=== JUDGE PROMPT A/B (t={t}, {a.model}) ===")
    print(f"halueval V1: {res['halueval_v1']}")
    print(f"halueval V3: {res['halueval_v3']}")
    print(f"guard V3: faithful {guard_admit}/12 admitted, confab {guard_block}/12 blocked")
    if a.out:
        RESULTS.mkdir(exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
