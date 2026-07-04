"""v3 learned update-target discriminator over a --dump-candidates artifact.

Round 2 locked (halumem_selector_sweep.py, 4e5d520): retrieval ranks best
(GT-top1 0.427 among reachable) but cannot discriminate the true target among
thematically-adjacent memories, and the generic NLI cross-encoder adds nothing
(rerank and gate both worsen it). This module is the "dedicated discriminator"
lever: a logistic regression over feature-rich (update, candidate) pairs —
lexical from→to structure, IDF-weighted overlap, shared/changed numbers,
retrieval rank shape, NLI probs — trained and applied **out-of-fold per user**
(GroupKFold), so every selection is made on users the model never saw.
End-to-end numbers are scored with the same judge-calibrated e5@0.94 matcher
as round 2, on the same dump: apples-to-apples.

Features are runtime-legal only: update text + candidate text + retrieval
score + cached NLI probs, all available at selection time. Ground truth is
used exclusively for labels and scoring, never inside features
(tests assert this).

    python -m benchmark.halumem_selector_v3 \
        --dump benchmark/results/halumem_updating_full20_dump.json \
        --out benchmark/results/halumem_selector_v3.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from benchmark.halumem_selector_sweep import (
    extract_old_value,
    old_value_hit,
    score_policy,
)

FEATURE_NAMES = [
    "retrieval", "ret_rank", "ret_margin",
    "jaccard", "contain_upd", "contain_cand", "bigram_jaccard", "idf_overlap",
    "num_shared", "num_upd_only",
    "oldvalue_hit", "has_oldvalue",
    "ab_contra", "ba_contra", "ab_entail", "ba_entail",
    "len_ratio",
]

_TOKEN = re.compile(r"[a-z0-9]+")
_NUM = re.compile(r"\d+(?:\.\d+)?")


def _tokens(s: str) -> list[str]:
    return [t for t in _TOKEN.findall((s or "").lower()) if len(t) > 2]


def _bigrams(toks: list[str]) -> set[tuple[str, str]]:
    return set(zip(toks, toks[1:]))


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def build_idf(items: list[dict]) -> dict[str, float]:
    """IDF over the unique candidate texts of the dump — the memory-store
    side, known at selection time (runtime-legal)."""
    texts = {c["text"] for it in items for c in it.get("candidates", [])}
    n = max(len(texts), 1)
    df: dict[str, int] = {}
    for t in texts:
        for tok in set(_tokens(t)):
            df[tok] = df.get(tok, 0) + 1
    return {tok: math.log(n / (1 + d)) + 1.0 for tok, d in df.items()}


def featurize_item(item: dict, idf: dict[str, float]) -> list[list[float]]:
    """One runtime-legal feature row per candidate (aligned with
    FEATURE_NAMES). GT never enters here."""
    upd = item.get("update", "")
    cands = item.get("candidates", [])
    upd_toks = _tokens(upd)
    upd_set = set(upd_toks)
    upd_bi = _bigrams(upd_toks)
    upd_nums = set(_NUM.findall(upd or ""))
    old = extract_old_value(upd)
    upd_idf = sum(idf.get(t, 1.0) for t in upd_set)
    scores = [c.get("retrieval", 0.0) for c in cands]
    order = sorted(range(len(cands)), key=lambda i: -scores[i])
    rank_of = {i: r for r, i in enumerate(order)}

    rows = []
    for i, c in enumerate(cands):
        text = c.get("text", "")
        toks = _tokens(text)
        tset = set(toks)
        inter = upd_set & tset
        ret = scores[i]
        best_other = max((s for j, s in enumerate(scores) if j != i),
                         default=0.0)
        nums = set(_NUM.findall(text))
        n_upd_nums = len(upd_nums)
        ab = c.get("ab", {})
        ba = c.get("ba", {})
        rows.append([
            ret,
            rank_of[i] / max(len(cands) - 1, 1),
            ret - best_other,
            _jaccard(upd_set, tset),
            len(inter) / max(len(upd_set), 1),
            len(inter) / max(len(tset), 1),
            _jaccard(upd_bi, _bigrams(toks)),
            (sum(idf.get(t, 1.0) for t in inter) / upd_idf) if upd_idf else 0.0,
            len(upd_nums & nums) / (1 + n_upd_nums),
            (n_upd_nums - len(upd_nums & nums)) / (1 + n_upd_nums),
            1.0 if old_value_hit(old, text) else 0.0,
            1.0 if old else 0.0,
            ab.get("contradiction", 0.0),
            ba.get("contradiction", 0.0),
            ab.get("entailment", 0.0),
            ba.get("entailment", 0.0),
            min(len(toks), len(upd_toks)) / max(len(toks), len(upd_toks), 1),
        ])
    return rows


def build_dataset(items: list[dict], matcher) -> dict:
    """Training rows from reachable items only (an item with no GT among its
    candidates has no positive to learn from); labels via the calibrated
    matcher. Returns parallel lists: X rows, y, groups (user), item_of_row,
    plus reachable item indices."""
    idf = build_idf(items)
    X: list[list[float]] = []
    y: list[int] = []
    groups: list[int] = []
    item_of_row: list[int] = []
    reachable_items: list[int] = []
    feats_by_item: dict[int, list[list[float]]] = {}
    for idx, it in enumerate(items):
        rows = featurize_item(it, idf)
        feats_by_item[idx] = rows
        labels = [1 if any(matcher(c["text"], g) for g in it["gt_originals"])
                  else 0 for c in it.get("candidates", [])]
        if not any(labels):
            continue
        reachable_items.append(idx)
        for r, lab in zip(rows, labels):
            X.append(r)
            y.append(lab)
            groups.append(it["user"])
            item_of_row.append(idx)
    return {"X": X, "y": y, "groups": groups, "item_of_row": item_of_row,
            "reachable_items": reachable_items, "feats_by_item": feats_by_item,
            "idf": idf}


def _make_model(seed: int):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(class_weight="balanced", max_iter=2000,
                           random_state=seed))


def crossval_select(items: list[dict], matcher, n_splits: int = 5,
                    seed: int = 7) -> dict:
    """Out-of-fold selection: GroupKFold over users; each fold trains on the
    reachable items of the train users and scores EVERY item of the test
    users. Returns per-item selected text, per-candidate probabilities, and
    the fold composition (for leakage tests)."""
    import numpy as np
    from sklearn.model_selection import GroupKFold

    ds = build_dataset(items, matcher)
    users = np.array([it["user"] for it in items])
    X = np.array(ds["X"], dtype=float)
    y = np.array(ds["y"], dtype=int)
    row_users = np.array(ds["groups"])

    selected: dict[int, str | None] = {}
    probs: dict[int, list[float]] = {}
    folds = []
    gkf = GroupKFold(n_splits=n_splits)
    unique_users = np.unique(users)
    for tr_u_idx, te_u_idx in gkf.split(unique_users, groups=unique_users):
        train_users = set(unique_users[tr_u_idx].tolist())
        test_users = set(unique_users[te_u_idx].tolist())
        folds.append({"train_users": sorted(train_users),
                      "test_users": sorted(test_users)})
        mask = np.array([u in train_users for u in row_users])
        model = _make_model(seed)
        model.fit(X[mask], y[mask])
        for idx, it in enumerate(items):
            if it["user"] not in test_users:
                continue
            rows = ds["feats_by_item"][idx]
            if not rows:
                selected[idx] = None
                probs[idx] = []
                continue
            p = model.predict_proba(np.array(rows, dtype=float))[:, 1]
            probs[idx] = [round(float(v), 6) for v in p]
            selected[idx] = it["candidates"][int(np.argmax(p))]["text"]
    return {"selected": selected, "probs": probs, "folds": folds,
            "dataset": {"n_rows": len(ds["X"]),
                        "n_reachable_items": len(ds["reachable_items"])}}


def classify_items(items: list[dict], policy, matcher) -> tuple[list[dict], dict]:
    """Per-item outcome records in the exact shape halumem_updating_judge_pass
    consumes (outcome, update, gt_originals, selected — full texts), plus the
    aggregate counts. Same outcome semantics as score_policy."""
    records = []
    counts = {"correct": 0, "wrong": 0, "missed": 0, "missed_unreachable": 0}
    for it in items:
        sel = policy(it)
        gts = it["gt_originals"]
        cand_texts = [c["text"] for c in it.get("candidates", [])]
        reachable = any(matcher(t, g) for t in cand_texts for g in gts)
        if sel is None:
            outcome = "missed" if reachable else "missed_unreachable"
        elif any(matcher(sel, g) for g in gts):
            outcome = "correct"
        else:
            outcome = "wrong"
        counts[outcome] += 1
        records.append({"user": it.get("user"), "outcome": outcome,
                        "update": it["update"], "gt_originals": gts,
                        "selected": sel or ""})
    return records, counts


def full_fit_coefficients(items: list[dict], matcher, seed: int = 7) -> dict:
    """Fit on ALL reachable items (the deployable model) and export weights as
    plain JSON — used for runtime integration, never for the CV numbers."""
    import numpy as np
    ds = build_dataset(items, matcher)
    model = _make_model(seed)
    X = np.array(ds["X"], dtype=float)
    model.fit(X, np.array(ds["y"], dtype=int))
    scaler = model.named_steps["standardscaler"]
    lr = model.named_steps["logisticregression"]
    return {
        "feature_names": FEATURE_NAMES,
        "scaler_mean": [round(float(v), 8) for v in scaler.mean_],
        "scaler_scale": [round(float(v), 8) for v in scaler.scale_],
        "coef": [round(float(v), 8) for v in lr.coef_[0]],
        "intercept": round(float(lr.intercept_[0]), 8),
        "train_rows": len(ds["X"]),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--match-thr", type=float, default=0.94)
    ap.add_argument("--splits", type=int, default=5)
    ap.add_argument("--abstain", default="0,0.3,0.5",
                    help="comma-separated max-proba thresholds below which "
                         "the selector abstains (0 = always select)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--save-model", default=None)
    ap.add_argument("--dump-selections", default=None,
                    help="write the abstain-0 out-of-fold selections as a "
                         "judge-pass-compatible results file")
    a = ap.parse_args(argv)

    from benchmark.halumem_updating_bench import make_e5_matcher
    items = json.loads(Path(a.dump).read_text(encoding="utf-8"))["items"]
    matcher = make_e5_matcher(a.match_thr)

    cv = crossval_select(items, matcher, n_splits=a.splits)

    # abstain thresholds are post-processing over the same out-of-fold probs
    policies = {}
    for thr_s in a.abstain.split(","):
        thr = float(thr_s)

        def _policy(it, _thr=thr, _idx={id(x): i for i, x in enumerate(items)}):
            i = _idx[id(it)]
            p = cv["probs"].get(i) or []
            if not p:
                return None
            m = max(p)
            if m < _thr:
                return None
            return it["candidates"][p.index(m)]["text"]

        policies[f"v3_oof_abstain{thr}"] = _policy

    # GT-rank diagnostics of the learned score (reachable items only),
    # comparable with round-2 signal diagnostics
    for i, it in enumerate(items):
        for c, p in zip(it.get("candidates", []), cv["probs"].get(i, [])):
            c["_v3"] = p
    diag_items = [it for it in items if it.get("candidates")]
    top1 = rr = n = 0
    for it in diag_items:
        cands = it["candidates"]
        gt_idx = [j for j, c in enumerate(cands)
                  if any(matcher(c["text"], g) for g in it["gt_originals"])]
        if not gt_idx:
            continue
        n += 1
        order = sorted(range(len(cands)), key=lambda j: -cands[j].get("_v3", 0.0))
        rank = min(order.index(j) for j in gt_idx) + 1
        top1 += rank == 1
        rr += 1.0 / rank
    v3_diag = {"n_reachable": n, "gt_top1": round(top1 / n, 4) if n else None,
               "gt_mrr": round(rr / n, 4) if n else None}

    res = {
        "dump": a.dump, "match_thr": a.match_thr, "n_items": len(items),
        "cv": {"folds": cv["folds"], **cv["dataset"]},
        "gt_rank_v3_oof": v3_diag,
        "policies": {name: score_policy(items, p, matcher)
                     for name, p in policies.items()},
    }
    if a.dump_selections:
        sel_policy = policies["v3_oof_abstain0.0"]
        records, counts = classify_items(items, sel_policy, matcher)
        n = sum(counts.values())
        Path(a.dump_selections).write_text(json.dumps({
            "source": "halumem_selector_v3 out-of-fold selections (abstain 0)",
            "dump": a.dump, "match_thr": a.match_thr,
            "outcomes": counts,
            "update_accuracy": round(counts["correct"] / n, 4) if n else None,
            "items": records,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        res["dumped_selections"] = a.dump_selections
    if a.save_model:
        model = full_fit_coefficients(items, matcher)
        model["source_dump"] = a.dump
        model["match_thr"] = a.match_thr
        Path(a.save_model).write_text(json.dumps(model, indent=2),
                                      encoding="utf-8")
        res["saved_model"] = a.save_model
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
