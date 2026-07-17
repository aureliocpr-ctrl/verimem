"""HaluMem official-protocol UPDATING slice — the missing third of the P0 number.

Protocol (arXiv 2511.03506, eval/ repo): ingest the user's memory points in
chronological order; for each point labeled ``is_update=True``, retrieve the
top-10 most relevant live memories, let the system decide WHICH one to update
(here: LocalRelationJudge NLI contradiction over the ranked candidates — the
same judge wired into reconcile), then score the operation:

  * correct            — the selected memory IS one of the GT ``original_memories``
  * wrong              — the system updated a memory that is NOT a GT original
                         (update hallucination)
  * missed             — nothing selected although a GT original was retrievable
  * missed_unreachable — retrieval never surfaced the GT original (counted as
                         an omission by the official protocol; split out here
                         because the fix lives in retrieval, not the judge)

Leaderboard mapping (MemOS self-reported 79.7/62.1/67.2 on Medium): Updating
"correct rate" = correct / n_targets. The official judge is gpt-4o (their
eval config, temp 0); by O4 policy we never call external APIs, so a
leaderboard-comparable run carries a DECLARED Claude-judge asterisk. This
harness is 100% LOCAL (e5 retrieval + cached NLI) — the LLM judge layer is a
separate, explicit pass over the saved per-item artifacts.

    python -m benchmark.halumem_updating_bench --users 5 \
        --out benchmark/results/halumem_updating_local.json
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from verimem.truth_reconciliation import _content_overlap

_DATASET = Path.home() / ".cache" / "halumem" / "HaluMem-Medium.jsonl"


def _norm(s: str | None) -> str:
    return " ".join((s or "").split()).strip().lower()


def select_update_target(candidates, new_content: str, scorer, *,
                         select_thr: float = 0.7, min_overlap: float = 0.0):
    """Pick the live memory the update targets.

    Probability probe on 12 GT (original → update) pairs (2026-07-03, user 0):
    HaluMem updates are mostly REFINEMENTS — P(update ⊨ original) ≥ 0.72 in
    9/12, while contradiction fires on only 1/12 (the true value-conflict). A
    contradiction-only selector therefore scores ~0 (first smoke: 12/12
    missed). Score per candidate = max(bidirectional contradiction,
    entailment(update ⊨ candidate)); pick the argmax if ≥ ``select_thr``
    (rank order breaks ties).

    ``scorer`` maps [(premise, hypothesis), ...] → [{label: prob}, ...]
    (verimem.local_relation.make_nli_classifier). ``candidates`` =
    [(fact_id, text), ...] ranked by retrieval score."""
    try:
        scored = score_candidate_pairs(candidates, new_content, scorer)
    except Exception:  # noqa: BLE001 — a scorer failure must not kill the run
        return None
    return select_from_scored(scored, new_content, select_thr=select_thr,
                              min_overlap=min_overlap)


def score_candidate_pairs(candidates, new_content: str, scorer):
    """One NLI batch over all candidates, BOTH directions. Returns
    [(fid, text, ab_probs, ba_probs)] where ab = (candidate ⊨ update?) and
    ba = (update ⊨ candidate?). Shared by selection and --dump-candidates so
    a dump run pays inference exactly once."""
    if not candidates:
        return []
    pairs = []
    for _, text in candidates:
        pairs.append((text, new_content))
        pairs.append((new_content, text))
    probs = scorer(pairs)
    return [(fid, text, probs[2 * i], probs[2 * i + 1])
            for i, (fid, text) in enumerate(candidates)]


def select_from_scored(scored, new_content: str | None = None, *,
                       select_thr: float = 0.7, min_overlap: float = 0.0):
    """v1 policy over pre-scored candidates (see select_update_target).

    Optional ``min_overlap`` (needs ``new_content``): reject a candidate whose
    content-token Jaccard with the update is below the floor — a precision guard
    that cuts WRONG selections (updating an unrelated memory = corrupting truth).
    Measured frontier (HaluMem 5u/726, local e5): floor 0.10 acc 0.664->0.674 AND
    wrong 0.194->0.167 (Pareto); 0.15 wrong ->0.138 at flat acc. Default 0.0 =
    unchanged (byte-identical)."""
    best_fid, best_score = None, 0.0
    for fid, text, ab, ba in scored:
        p_contra = max(ab.get("contradiction", 0.0), ba.get("contradiction", 0.0))
        p_refine = ba.get("entailment", 0.0)
        score = max(p_contra, p_refine)
        if score >= select_thr and score > best_score:
            if (min_overlap > 0.0 and new_content is not None
                    and _content_overlap(text, new_content) < min_overlap):
                continue
            best_fid, best_score = fid, score
    return best_fid


def classify_update_outcome(selected_text, gt_originals, candidates_texts,
                            matcher=None):
    """Local (judge-free) outcome classification.

    ``matcher(a, b) -> bool`` decides whether a live text IS a GT original.
    Default: whitespace/case-insensitive exact — sufficient for tests, but on
    the real dataset only ~34% of ``original_memories`` are verbatim copies of
    an earlier memory point (measured 2026-07-03, 3 users: 179/529); the rest
    are paraphrases. The runner therefore injects an e5-cosine matcher (same
    approach and default threshold as halumem_extraction_f1)."""
    if matcher is None:
        matcher = lambda a, b: _norm(a) == _norm(b)  # noqa: E731
    gts = [g for g in gt_originals if _norm(g)]
    reachable = any(matcher(c, g) for c in candidates_texts for g in gts)
    if selected_text is None:
        return "missed" if reachable else "missed_unreachable"
    return "correct" if any(matcher(selected_text, g) for g in gts) else "wrong"


def make_e5_matcher(threshold: float):
    """norm-exact OR e5 cosine >= threshold, with an encode cache."""
    import numpy as np

    from verimem import embedding
    cache: dict[str, object] = {}

    def _vec(t: str):
        v = cache.get(t)
        if v is None:
            v = embedding.encode(t)
            n = np.linalg.norm(v)
            v = v / n if n else v
            cache[t] = v
        return v

    def match(a: str, b: str) -> bool:
        if _norm(a) == _norm(b):
            return True
        return float(np.dot(_vec(a), _vec(b))) >= threshold

    return match


def _iter_updates(user: dict):
    """Chronological (session order, point order) stream of memory points."""
    for si, s in enumerate(user.get("sessions", [])):
        for mp in s.get("memory_points", []):
            content = (mp.get("memory_content") or "").strip()
            if not content:
                continue
            yield si, content, str(mp.get("is_update", "")).lower() == "true", \
                [o for o in (mp.get("original_memories") or []) if (o or "").strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(_DATASET))
    ap.add_argument("--users", type=int, default=5)
    ap.add_argument("--k", type=int, default=10,
                    help="retrieval depth (official protocol: 10)")
    ap.add_argument("--max-updates-per-user", type=int, default=0,
                    help="0 = all")
    ap.add_argument("--select-thr", type=float, default=0.7,
                    help="min max(p_contra, p_entail(update=>cand)) to select "
                         "a target (probe-calibrated, see select_update_target)")
    ap.add_argument("--select-min-overlap", type=float, default=0.0,
                    help="precision floor: reject a selection whose content-overlap "
                         "with the update is below this (cuts WRONG updates; frontier "
                         "0.10 Pareto, 0.15 trust-lean). Default 0 = off (unchanged).")
    ap.add_argument("--nli-model", default=None,
                    help="override the default cached NLI cross-encoder")
    ap.add_argument("--match-thr", type=float, default=0.86,
                    help="e5 cosine GT-match threshold (same default as "
                         "halumem_extraction_f1)")
    ap.add_argument("--dump-candidates", action="store_true",
                    help="save per-item candidates WITH their NLI probs (both "
                         "directions) and retrieval scores — makes every future "
                         "selector a pure offline post-process over one run")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    import tempfile

    from verimem.local_relation import DEFAULT_NLI_MODEL, make_nli_classifier
    from verimem.semantic import Fact, SemanticMemory

    users = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            users.append(json.loads(line))
            if len(users) >= a.users:
                break

    scorer = make_nli_classifier(a.nli_model or DEFAULT_NLI_MODEL)
    matcher = make_e5_matcher(a.match_thr)
    t0 = time.time()
    outcomes: dict[str, int] = {}
    items = []
    for ui, user in enumerate(users):
        # ignore_cleanup_errors: SemanticMemory/EntityStore expose no close()
        # (core gap, noted 2026-07-03) and Windows refuses to unlink an open
        # sqlite file — a leftover tmpdir beats a crashed run; gc below gives
        # the unlink its best chance.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            sm = SemanticMemory(db_path=Path(tmp) / "semantic" / "semantic.db")
            n_upd = 0
            for si, content, is_upd, gt_originals in _iter_updates(user):
                if is_upd and gt_originals and (
                        not a.max_updates_per_user or n_upd < a.max_updates_per_user):
                    n_upd += 1
                    hits = sm.recall(content, k=a.k)
                    cands = [(f.id, f.proposition) for f, _ in hits]
                    try:
                        scored = score_candidate_pairs(cands, content, scorer)
                    except Exception:  # noqa: BLE001
                        scored = []
                    sel = select_from_scored(scored, content,
                                             select_thr=a.select_thr,
                                             min_overlap=a.select_min_overlap)
                    sel_text = dict(cands).get(sel) if sel else None
                    out = classify_update_outcome(
                        sel_text, gt_originals, [t for _, t in cands],
                        matcher=matcher)
                    outcomes[out] = outcomes.get(out, 0) + 1
                    # FULL texts, not previews: the Claude-judge pass reads
                    # these artifacts — truncated inputs made it classify every
                    # correct selection as hallucinated (smoke, 2026-07-03).
                    item = {
                        "user": ui, "session": si, "outcome": out,
                        "update": content,
                        "gt_originals": list(gt_originals),
                        "selected": sel_text or "",
                    }
                    if a.dump_candidates:
                        ret_score = {f.id: float(s) for f, s in hits}
                        item["candidates"] = [
                            {"text": text, "retrieval": round(ret_score.get(fid, 0.0), 4),
                             "ab": {k: round(v, 4) for k, v in ab.items()},
                             "ba": {k: round(v, 4) for k, v in ba.items()}}
                            for fid, text, ab, ba in scored]
                    items.append(item)
                # every point (update or not) becomes live memory afterwards,
                # so later updates can target it — chronological world state.
                sm.store(Fact(proposition=content, topic=f"halu/{ui}",
                              status="model_claim", confidence=0.8))
            del sm
            import gc
            gc.collect()

    n = sum(outcomes.values())
    correct = outcomes.get("correct", 0)
    wrong = outcomes.get("wrong", 0)
    missed = outcomes.get("missed", 0) + outcomes.get("missed_unreachable", 0)
    res = {
        "protocol": "HaluMem updating slice (local judge-free scoring; "
                    "official LLM-judge layer is a separate pass)",
        "dataset": a.jsonl, "users": len(users), "k": a.k,
        "select_thr": a.select_thr,
        "n_target_updates": n,
        "outcomes": outcomes,
        "update_accuracy": round(correct / n, 4) if n else None,
        "update_hallucination_rate": round(wrong / n, 4) if n else None,
        "update_omission_rate": round(missed / n, 4) if n else None,
        "retrieval_unreachable_share": round(
            outcomes.get("missed_unreachable", 0) / n, 4) if n else None,
        "wall_s": round(time.time() - t0, 1),
        "items": items,
    }
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    print(json.dumps({k: res[k] for k in res if k != "items"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
