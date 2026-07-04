"""Judge-validation of the Updating reachability metric — settles whether the
44% "unreachable@10" at the severe e5@0.94 matcher is a REAL retrieval gap or a
matcher artifact (historic warning: "unreachable 0.44 = artefatto metro").

Samples items from a --dump-candidates artifact where NO top-10 candidate matches
any GT original at the severe threshold, and asks the claude judge whether any
candidate nonetheless EXPRESSES the same fact as a GT original (paraphrase counts).

  judge_found_rate ~ 0   -> unreachable is REAL -> invest in retrieval (k/centering/fusion)
  judge_found_rate high  -> matcher-inflated    -> the ceiling is looser than 0.56;
                            invest in selector/scoring, not retrieval.

    python -m benchmark.updating_reachability_judge_check \
        --dump <dump.json> --sample 25 --out benchmark/results/reachability_judge_check.json
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

_SYSTEM = (
    "You compare ONE ground-truth memory against 10 candidate memories.\n"
    "Answer with the 1-based INDEX (1-10) of a candidate that expresses the SAME "
    "FACT as the ground-truth memory (paraphrase counts; extra detail is fine as "
    "long as the core fact matches), or exactly NONE if no candidate does.\n"
    "Reply with just the index number or NONE."
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--match-thr", type=float, default=0.94)
    ap.add_argument("--sample", type=int, default=25)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--pause-s", type=float, default=1.5)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    from benchmark.halumem_updating_bench import make_e5_matcher
    from benchmark.qa_runner import LeanClaudeCLILLM

    items = json.loads(Path(a.dump).read_text(encoding="utf-8"))["items"]
    matcher = make_e5_matcher(a.match_thr)

    unreachable = []
    for it in items:
        cands = [c["text"] for c in it.get("candidates", [])]
        gts = [g for g in it.get("gt_originals", []) if g.strip()]
        if not cands or not gts:
            continue
        if not any(matcher(c, g) for c in cands for g in gts):
            unreachable.append((it, cands, gts))
    rng = random.Random(a.seed)
    rng.shuffle(unreachable)
    picked = unreachable[: a.sample]

    llm = LeanClaudeCLILLM(model=a.model, timeout_s=90)
    found = none = err = 0
    records = []
    t0 = time.time()
    for it, cands, gts in picked:
        gt = gts[0]
        lines = "\n".join(f"{i+1}. {c}" for i, c in enumerate(cands[:10]))
        user = f"GROUND-TRUTH MEMORY:\n{gt}\n\nCANDIDATES:\n{lines}"
        try:
            resp = llm.complete(_SYSTEM, [{"role": "user", "content": user}],
                                max_tokens=6)
            w = (getattr(resp, "text", "") or "").strip().upper()
        except Exception as exc:  # noqa: BLE001
            err += 1
            records.append({"gt": gt, "verdict": f"ERROR:{str(exc)[:50]}"})
            continue
        if w.startswith("NONE"):
            none += 1
            records.append({"gt": gt, "verdict": "NONE"})
        else:
            try:
                idx = int("".join(ch for ch in w if ch.isdigit())[:2] or "0")
            except ValueError:
                idx = 0
            if 1 <= idx <= len(cands):
                found += 1
                records.append({"gt": gt, "verdict": idx,
                                "candidate": cands[idx - 1]})
            else:
                err += 1
                records.append({"gt": gt, "verdict": f"UNPARSED:{w[:20]}"})
        time.sleep(a.pause_s)

    judged = found + none
    res = {
        "dump": a.dump, "match_thr": a.match_thr,
        "n_unreachable_at_thr": len(unreachable), "n_items": len(items),
        "unreachable_share": round(len(unreachable) / len(items), 4),
        "sampled": len(picked), "judged": judged, "errors": err,
        "judge_found": found, "judge_none": none,
        "judge_found_rate": round(found / judged, 4) if judged else None,
        "corrected_reachable_at10_estimate": round(
            (1 - len(unreachable) / len(items))
            + (len(unreachable) / len(items)) * (found / judged), 4)
            if judged else None,
        "wall_s": round(time.time() - t0, 1),
        "records": records,
        "note": "judge_found_rate = share of matcher-unreachable items where the "
                "judge finds a top-10 candidate expressing the GT fact. High -> the "
                "severe matcher inflates unreachability (metric artifact); ~0 -> the "
                "retrieval gap is real. corrected_reachable_at10 = reachable@0.94 + "
                "unreachable_share * judge_found_rate.",
    }
    print(json.dumps({k: res[k] for k in res if k != "records"}, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
