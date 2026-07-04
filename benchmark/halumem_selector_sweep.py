"""Offline selector sweep over a --dump-candidates artifact — iterate update-
target policies in seconds instead of 40-minute reruns.

Input: the full-20 dump (per item: update, gt_originals, candidates each with
retrieval score + NLI probs both directions). Every policy is a pure function
(item → selected candidate text or None); outcomes are scored with the
judge-calibrated e5@0.94 matcher (precision 7/7 on bought verdicts,
2026-07-03). Also reports per-signal GT-rank diagnostics — WHERE the ground
truth sits under each signal ordering — so new policies come from measured
separability, not guesses.

    python -m benchmark.halumem_selector_sweep \
        --dump benchmark/results/halumem_updating_full20_dump.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# --- old-value extraction (the 28% of updates with explicit from→to) ---

_FROM_TO = re.compile(
    r"""from\s+['"]?(?P<old>[^'"]+?)['"]?\s+to\s+['"]?(?P<new>[^'".]+)""",
    re.IGNORECASE)


def extract_old_value(update: str) -> str | None:
    """OLD value cited by an explicit from→to update, else None. Measured on
    the real dataset: ~28% of updates carry this structure (200/726, 5 users);
    for those the true target must assert the OLD value — a high-precision
    signal, deliberately not forced onto the other 72%."""
    m = _FROM_TO.search(update or "")
    if not m:
        return None
    old = m.group("old").strip().strip("'\"")
    return old or None


def _norm_tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(t) > 2}


def old_value_hit(old: str | None, candidate_text: str) -> bool:
    """Does the candidate assert the OLD value? Token-subset containment
    (case/punct-insensitive) — verbatim substring is too brittle."""
    if not old:
        return False
    ot = _norm_tokens(old)
    return bool(ot) and ot <= _norm_tokens(candidate_text)


# --- signals & policies (each policy: item -> selected text | None) ---

def _sig_v1(c):
    return max(max(c["ab"].get("contradiction", 0), c["ba"].get("contradiction", 0)),
               c["ba"].get("entailment", 0))


def _sig_refine(c):
    return c["ba"].get("entailment", 0.0)


def _sig_retrieval(c):
    return c.get("retrieval", 0.0)


def policy_v1(item, thr=0.7):
    best, bs = None, 0.0
    for c in item.get("candidates", []):
        s = _sig_v1(c)
        if s >= thr and s > bs:
            best, bs = c["text"], s
    return best


def policy_oldvalue_then_v1(item, thr=0.7):
    """OLD-value containment wins when the update is explicit from→to and
    exactly one candidate asserts the old value; otherwise fall back to v1."""
    old = extract_old_value(item["update"])
    if old:
        hits = [c for c in item.get("candidates", []) if old_value_hit(old, c["text"])]
        if len(hits) == 1:
            return hits[0]["text"]
        if len(hits) > 1:
            return max(hits, key=_sig_v1)["text"]
    return policy_v1(item, thr)


def make_policy_top_signal(sig, thr):
    def _p(item):
        best, bs = None, 0.0
        for c in item.get("candidates", []):
            s = sig(c)
            if s >= thr and s > bs:
                best, bs = c["text"], s
        return best
    return _p


def policy_ret_top1_nli_gate(item, nli_thr):
    """Retrieval's top-1, but only when it also carries SOME NLI relation to
    the update (v1 signal ≥ nli_thr) — keep retrieval's ranking power, use NLI
    as a veto instead of a ranker."""
    cands = item.get("candidates", [])
    if not cands:
        return None
    top = max(cands, key=_sig_retrieval)
    return top["text"] if _sig_v1(top) >= nli_thr else None


def policy_topk_rerank(item, k):
    """Among retrieval's top-k, pick the one the NLI refine signal prefers —
    retrieval narrows, NLI discriminates locally."""
    cands = item.get("candidates", [])
    if not cands:
        return None
    topk = sorted(cands, key=_sig_retrieval, reverse=True)[:k]
    return max(topk, key=_sig_refine)["text"]


def policy_oldvalue_then_retrieval(item):
    old = extract_old_value(item["update"])
    if old:
        hits = [c for c in item.get("candidates", []) if old_value_hit(old, c["text"])]
        if hits:
            return max(hits, key=_sig_retrieval)["text"]
    cands = item.get("candidates", [])
    return max(cands, key=_sig_retrieval)["text"] if cands else None


# --- scoring with the calibrated matcher ---

def score_policy(items, policy, matcher):
    out = {"correct": 0, "wrong": 0, "missed": 0, "missed_unreachable": 0}
    for it in items:
        sel = policy(it)
        gts = it["gt_originals"]
        cand_texts = [c["text"] for c in it.get("candidates", [])]
        reachable = any(matcher(t, g) for t in cand_texts for g in gts)
        if sel is None:
            out["missed" if reachable else "missed_unreachable"] += 1
        elif any(matcher(sel, g) for g in gts):
            out["correct"] += 1
        else:
            out["wrong"] += 1
    n = sum(out.values())
    return {"n": n, "outcomes": out,
            "accuracy": round(out["correct"] / n, 4) if n else None,
            "hallucination": round(out["wrong"] / n, 4) if n else None,
            "omission": round((out["missed"] + out["missed_unreachable"]) / n, 4)
            if n else None}


def gt_rank_diagnostics(items, matcher):
    """For each signal: where does the GT sit among the candidates? top-1 rate
    and MRR — measured separability that tells us which signal to build on."""
    sigs = {"v1": _sig_v1, "refine_ba_entail": _sig_refine,
            "retrieval": _sig_retrieval}
    diag = {}
    for name, sig in sigs.items():
        top1 = 0
        rr_sum = 0.0
        n = 0
        for it in items:
            cands = it.get("candidates", [])
            gt_idx = [i for i, c in enumerate(cands)
                      if any(matcher(c["text"], g) for g in it["gt_originals"])]
            if not gt_idx:
                continue  # unreachable: not the selector's fault
            n += 1
            order = sorted(range(len(cands)), key=lambda i: -sig(cands[i]))
            rank = min(order.index(i) for i in gt_idx) + 1
            top1 += rank == 1
            rr_sum += 1.0 / rank
        diag[name] = {"n_reachable": n,
                      "gt_top1": round(top1 / n, 4) if n else None,
                      "gt_mrr": round(rr_sum / n, 4) if n else None}
    return diag


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--match-thr", type=float, default=0.94,
                    help="judge-calibrated matcher threshold")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    from benchmark.halumem_updating_bench import make_e5_matcher
    items = json.loads(Path(a.dump).read_text(encoding="utf-8"))["items"]
    matcher = make_e5_matcher(a.match_thr)

    policies = {
        "v1_thr0.7 (baseline)": lambda it: policy_v1(it, 0.7),
        "oldvalue_then_v1": lambda it: policy_oldvalue_then_v1(it, 0.7),
        "retrieval_top1_always": make_policy_top_signal(_sig_retrieval, 0.0),
        # round 2 — composites (retrieval won the GT-rank diagnostics 0.427
        # top1 vs 0.32-0.33 for the NLI signals; these try to keep its
        # accuracy while cutting its 0.76 hallucination rate)
        "ret_top1_nli_gate0.3": lambda it: policy_ret_top1_nli_gate(it, 0.3),
        "ret_top1_nli_gate0.5": lambda it: policy_ret_top1_nli_gate(it, 0.5),
        "ret_top3_rerank_refine": lambda it: policy_topk_rerank(it, 3),
        "ret_top2_rerank_refine": lambda it: policy_topk_rerank(it, 2),
        "oldvalue_then_ret_top1": policy_oldvalue_then_retrieval,
    }
    res = {"dump": a.dump, "match_thr": a.match_thr, "n_items": len(items),
           "gt_rank_diagnostics": gt_rank_diagnostics(items, matcher),
           "policies": {name: score_policy(items, p, matcher)
                        for name, p in policies.items()}}
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
