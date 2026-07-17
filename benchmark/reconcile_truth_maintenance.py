"""Measure truth-maintenance on write (reconcile-on-write) on HaluMem ground truth — the
blocker that keeps ENGRAM_RECONCILE_ON_WRITE opt-in is an UNMEASURED false-supersede rate.
This measures it. 100% LOCAL (classify_conflict is lexical + entity-store; no claude -p).

HaluMem memory_points with is_update=True carry `original_memories` (the facts they
supersede) — exact ground truth. We:
  1. UPDATE set: store each original (older), then reconcile the update (newer,
     auto_supersede) → did it correctly supersede the original? (update-recall)
  2. CONTROL set: store a fact, then reconcile an UNRELATED newer fact → did it wrongly
     supersede? (false-supersede rate — must be ~0 to graduate the feature)

    python -m benchmark.reconcile_truth_maintenance --pairs 60 --out benchmark/results/reconcile_truth.json
"""
from __future__ import annotations

import argparse
import json
import random
import tempfile
import time
from pathlib import Path


def _updates(users: list[dict]) -> list[tuple[str, str]]:
    """(original_text, update_text) pairs from is_update memory_points."""
    out = []
    for u in users:
        for s in u.get("sessions", []):
            for mp in s.get("memory_points", []):
                if str(mp.get("is_update", "")).lower() != "true":
                    continue
                upd = (mp.get("memory_content") or "").strip()
                origs = [o.strip() for o in (mp.get("original_memories") or []) if o.strip()]
                if upd and origs:
                    out.append((origs[0], upd))
    return out


def _all_contents(u: dict) -> list[str]:
    return [(mp.get("memory_content") or "").strip()
            for s in u.get("sessions", []) for mp in s.get("memory_points", [])
            if (mp.get("memory_content") or "").strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--pairs", type=int, default=60)
    ap.add_argument("--max-diff-values", type=str, default="1,2,3",
                    help="comma-separated max_diff values to sweep")
    ap.add_argument("--users", type=int, default=6)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--nli", action="store_true",
                    help="confirm conflicts with the semantic NLI judge (LLM) instead of "
                         "the lexical heuristic — measures the reconcile fix's recall")
    ap.add_argument("--local-nli", action="store_true",
                    help="confirm conflicts with the LOCAL NLI cross-encoder judge "
                         "(verimem.local_relation, zero claude -p) — the subscription-"
                         "independent truth-maintenance path")
    ap.add_argument("--nli-model", default=None,
                    help="override the local NLI model (default cross-encoder/"
                         "nli-deberta-v3-base)")
    ap.add_argument("--contra-threshold", type=float, default=0.5)
    ap.add_argument("--contra-thresholds", type=str, default="0.5,0.8,0.9,0.95",
                    help="local-NLI contradiction-threshold sweep (precision/recall knob)")
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--require-evidence", action="store_true",
                    help="anti-sycophancy gate (STRICT): a bare claim (no verified_by, "
                         "status != verified) can only contest, never supersede — measures "
                         "the update-recall COST of the strict gate on real HaluMem updates")
    ap.add_argument("--protect-evidenced", action="store_true",
                    help="anti-sycophancy gate (TIERED): require evidence only to supersede "
                         "an EVIDENCED fact; bare->bare updates still apply — should PRESERVE "
                         "update-recall (HaluMem facts are bare) while protecting verified truth")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    a.max_diff_values = [int(x) for x in str(a.max_diff_values).split(",") if x.strip()]
    import os as _os
    _os.environ.setdefault("ENGRAM_ENTITY_LIVE", "1")  # reconcile needs entity links

    from verimem.semantic import Fact, SemanticMemory

    judge = None
    judge_kind = "lexical"
    shared_classifier = None
    nli_model_name = None
    if a.local_nli:
        # Load the NLI model ONCE and reuse it across the threshold sweep.
        from verimem.local_relation import (
            DEFAULT_NLI_MODEL,
            LocalRelationJudge,
            make_nli_classifier,
        )
        nli_model_name = a.nli_model or DEFAULT_NLI_MODEL
        shared_classifier = make_nli_classifier(nli_model_name)
        judge = LocalRelationJudge(model_name=nli_model_name,
                                   classifier=shared_classifier,
                                   contradiction_threshold=a.contra_threshold)
        judge_kind = f"local_nli:{nli_model_name}"
    elif a.nli:
        from benchmark.qa_runner import LeanClaudeCLILLM
        from verimem.semantic_conflict import LLMRelationJudge
        judge = LLMRelationJudge(LeanClaudeCLILLM(model=a.model, timeout_s=a.timeout))
        judge_kind = f"claude_nli:{a.model}"

    rng = random.Random(a.seed)
    users = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))
    rng.shuffle(users)
    users = users[: a.users]

    update_pairs = _updates(users)
    rng.shuffle(update_pairs)
    update_pairs = update_pairs[: a.pairs]
    # UNRELATED control: cross-user facts (no shared entity) -> must NOT supersede.
    pool = []
    for u in users:
        pool.extend(_all_contents(u))
    rng.shuffle(pool)
    unrelated = [(pool[i], pool[-(i + 1)]) for i in range(min(a.pairs, len(pool) // 2))]
    # COMPLEMENTARY control (the real precision risk): two facts from the SAME user, NOT an
    # update pair -> usually same entity, DIFFERENT attribute. Loosening max_diff must not
    # start superseding these.
    complementary = []
    for u in users:
        cs = _all_contents(u)
        rng.shuffle(cs)
        for i in range(0, min(len(cs) - 1, 2 * (a.pairs // max(1, len(users)))), 2):
            complementary.append((cs[i], cs[i + 1]))
    complementary = complementary[: a.pairs]

    now = time.time()
    old_ts, new_ts = now - 10 * 86400, now  # 10-day gap (> min_age_gap_days)

    def run_pair(old_text, new_text, tag):
        tmp = Path(tempfile.mkdtemp(prefix=f"recon_{tag}_"))
        sm = SemanticMemory(db_path=tmp / "semantic" / "semantic.db")
        old = Fact(proposition=old_text, topic="recon", created_at=old_ts, confidence=0.8)
        new = Fact(proposition=new_text, topic="recon", created_at=new_ts, confidence=0.8)
        try:
            sm.store(old, embed="sync")
            sm.store(new, embed="sync")
            sm.reconcile_new_fact(new, auto_supersede=True, judge=judge,
                                  require_evidence=a.require_evidence,
                                  protect_evidenced=a.protect_evidenced)
            return getattr(sm.get(old.id), "superseded_by", None) == new.id
        except Exception:  # noqa: BLE001
            return None

    def rate(pairs, tag):
        xs = [x for x in (run_pair(o, n, tag) for o, n in pairs) if x is not None]
        return (round(sum(xs) / len(xs), 4) if xs else None, len(xs))

    sweep = {}
    import os as _os
    if a.local_nli:
        # Sweep the CONTRADICTION THRESHOLD (the local-NLI precision/recall knob),
        # reusing the one loaded model. max_diff is irrelevant here — the NLI judge
        # replaces the lexical conflict confirmation.
        from verimem.local_relation import LocalRelationJudge
        thresholds = [float(x) for x in str(a.contra_thresholds).split(",") if x.strip()]
        for thr in thresholds:
            judge = LocalRelationJudge(model_name=nli_model_name,
                                       classifier=shared_classifier,
                                       contradiction_threshold=thr)
            rec, nrec = rate(update_pairs, "u")
            fcomp, ncomp = rate(complementary, "k")
            funr, nunr = rate(unrelated, "x")
            sweep[f"contra_thr={thr}"] = {
                "update_recall": rec, "n_update": nrec,
                "false_supersede_complementary": fcomp, "n_complementary": ncomp,
                "false_supersede_unrelated": funr, "n_unrelated": nunr,
            }
    else:
        for md in (a.max_diff_values or [1, 2, 3]):
            _os.environ["ENGRAM_RECONCILE_MAX_DIFF"] = str(md)
            rec, nrec = rate(update_pairs, f"u{md}")
            fcomp, ncomp = rate(complementary, f"k{md}")
            funr, nunr = rate(unrelated, f"x{md}")
            sweep[f"max_diff={md}"] = {
                "update_recall": rec, "n_update": nrec,
                "false_supersede_complementary": fcomp, "n_complementary": ncomp,
                "false_supersede_unrelated": funr, "n_unrelated": nunr,
            }
        _os.environ.pop("ENGRAM_RECONCILE_MAX_DIFF", None)

    res = {
        "judge": judge_kind,
        "require_evidence": bool(a.require_evidence),
        "protect_evidenced": bool(a.protect_evidenced),
        "sweep": sweep,
        "note": "update_recall = true HaluMem updates correctly superseded (want HIGH); "
                "false_supersede_* = wrongly superseded (want ~0; complementary = same-user "
                "diff-attribute is the real precision risk). Local lexical reconcile; "
                "ground truth = HaluMem is_update / original_memories.",
    }
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
