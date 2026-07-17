"""Local gate v2 — distill the claude judge on the REAL corpus register (phase-3 v2).

Phase-3 v1 verdict (STATE.md 2026-07-02): the HaluMem-only fine-tune under-admits the
real corpus (agreement 75.6%, real-fact admit 0.817 vs claude 0.967). Root cause is
REGISTER, not language: compressed technical notes (RFC/OIDs/sigles) never appear in
HaluMem's natural dialogue. v2 closes the gap by mixing:

* HaluMem ground truth (same recipe as local_gate_finetune — keeps the attribution
  skill and the conversational register), binary labels;
* REAL-corpus pairs (fact vs its source episode's span) with SOFT claude labels
  (score/100) — pure distillation of the production judge on the register it must
  serve. Swap-negatives (cross-topic proposition swaps) are labeled by claude too:
  no synthetic ground truth is assumed (v1 showed those labels are noisy).

Split hygiene: the 90 phase-3-v1 items (real_corpus_gate_validation.json) are the
TEST set — their fact_ids are excluded from sampling, so v2 trains on disjoint facts
and is measured on the exact items v1 failed. Privacy: labeled corpus data lives
under ~/.engram/local_gate/ (NEVER in the repo; only this code is versioned).

Stages (resumable):
    python -m benchmark.local_gate_distill_v2 --stage label --n 250 --n-neg 80
    python -m benchmark.local_gate_distill_v2 --stage train --epochs 2
    python -m benchmark.local_gate_distill_v2 --stage eval

Honest caveat: distilling claude on the corpus imports claude's attribution
blindness FOR THAT REGISTER; the HaluMem interference negatives in the mix are what
keeps the attribution skill alive — re-measured at eval (HaluMem heldout must not
regress).
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
import time
from pathlib import Path

from verimem.grounding_gate import select_relevant_span

DATA_DIR = Path.home() / ".engram" / "local_gate"
LABELS_JSONL = DATA_DIR / "corpus_labels_v2.jsonl"
V1_TEST_JSON = Path("benchmark/results/real_corpus_gate_validation.json")
MODEL_DIR_V2 = Path.home() / ".engram" / "models" / "local_gate_ce_v2"
SEM_DB = Path.home() / ".engram" / "semantic" / "semantic.db"
EPI_DB = Path.home() / ".engram" / "episodes" / "episodes.db"


def _episode_text(epi: sqlite3.Connection, src_field: str) -> str | None:
    ids = [s.strip() for s in str(src_field).replace("[", "").replace("]", "")
           .replace('"', "").replace("'", "").split(",") if s.strip()]
    parts = []
    for eid in ids[:3]:
        r = epi.execute("SELECT task_text, final_answer FROM episodes WHERE id=?",
                        (eid,)).fetchone()
        if r:
            parts.append(f"TASK: {r[0] or ''}\nESITO: {r[1] or ''}")
    return "\n---\n".join(parts) if parts else None


def sample_corpus_facts(sem_db: Path, epi_db: Path, *, seed: int, n: int,
                        exclude_ids: set[str], budget: int = 1500,
                        min_prop: int = 30, min_src: int = 200) -> list[dict]:
    """Live facts with a reconstructable episode source, span-selected. Deterministic;
    ``exclude_ids`` keeps the v1 test set (and anything else) held out."""
    sem = sqlite3.connect(str(sem_db))
    epi = sqlite3.connect(str(epi_db))
    rows = sem.execute(
        "SELECT id, proposition, source_episodes, topic FROM facts "
        "WHERE superseded_by IS NULL AND source_episodes IS NOT NULL "
        "AND source_episodes != '' AND source_episodes != '[]' "
        "ORDER BY id").fetchall()
    rng = random.Random(seed)
    rng.shuffle(rows)
    out: list[dict] = []
    for fid, prop, src, topic in rows:
        if len(out) >= n:
            break
        if fid in exclude_ids or not prop or len(prop) < min_prop:
            continue
        txt = _episode_text(epi, src)
        if not txt or len(txt) < min_src:
            continue
        out.append({"fact_id": str(fid), "topic": str(topic or ""),
                    "fact": str(prop),
                    "span": select_relevant_span(txt, prop, budget=budget)})
    sem.close()
    epi.close()
    return out


def make_swap_negatives(items: list[dict], *, seed: int, n: int) -> list[dict]:
    """Cross-topic proposition swaps over the sampled facts: donor fact on host span.
    Labeled by claude downstream — no synthetic ground truth assumed."""
    rng = random.Random(seed + 5)
    donors = items[:]
    rng.shuffle(donors)
    out: list[dict] = []
    for host, donor in zip(items, donors, strict=True):
        if len(out) >= n:
            break
        if host["fact_id"] != donor["fact_id"] and host["topic"] != donor["topic"]:
            out.append({"fact_id": f"swap:{host['fact_id']}<-{donor['fact_id']}",
                        "topic": host["topic"], "fact": donor["fact"],
                        "span": host["span"]})
    return out


def load_labeled_jsonl(path: Path, *, binarize_at: float | None = None,
                       ) -> tuple[set[str], list[dict]]:
    """(done_ids, train_items) from the resumable label file. Duplicate fact_ids
    collapse to the first occurrence. Default label is SOFT (claude score/100);
    ``binarize_at`` makes it the claude admit DECISION (1.0/0.0 at that cut) — v2
    finding: soft targets (~0.85 mean) leave the corpus slice score-collapsed and
    the threshold non-transferable (Youden fell to 0.1); the gate decides binary
    anyway, so distill the decision."""
    done: set[str] = set()
    items: list[dict] = []
    if not Path(path).exists():
        return done, items
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            fid = str(r.get("fact_id"))
            if fid in done:
                continue
            done.add(fid)
            score = float(r["claude_score"])
            label = (1.0 if score >= binarize_at else 0.0) \
                if binarize_at is not None else score / 100.0
            items.append({"fact_id": fid, "fact": r["fact"], "span": r["span"],
                          "label": label, "kind": "corpus_claude"})
    return done, items


def _v1_test_ids() -> set[str]:
    try:
        d = json.loads(V1_TEST_JSON.read_text(encoding="utf-8"))
    except OSError:
        return set()
    ids: set[str] = set()
    for it in d.get("items", []):
        fid = str(it.get("fact_id", ""))
        ids.add(fid)
        if fid.startswith("swap:"):
            host, _, donor = fid[5:].partition("<-")
            ids.update({host, donor})
    return ids


def stage_label(a) -> int:
    from benchmark.qa_runner import LeanClaudeCLILLM
    from verimem.grounding_gate import fact_grounding_score

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    exclude = _v1_test_ids()
    done, _ = load_labeled_jsonl(LABELS_JSONL)
    print(f"v1-test held out: {len(exclude)} ids | already labeled: {len(done)}",
          file=sys.stderr)
    pos = sample_corpus_facts(SEM_DB, EPI_DB, seed=a.seed, n=a.n,
                              exclude_ids=exclude, budget=a.budget)
    neg = make_swap_negatives(pos, seed=a.seed, n=a.n_neg)
    todo = [x for x in pos + neg if x["fact_id"] not in done]
    print(f"to label: {len(todo)} (pos {len(pos)} + neg {len(neg)}, resume-safe)",
          file=sys.stderr)
    llm = LeanClaudeCLILLM(model=a.model, timeout_s=a.timeout)
    with open(LABELS_JSONL, "a", encoding="utf-8") as f:
        for i, it in enumerate(todo):
            t0 = time.time()
            score = fact_grounding_score(llm, it["span"], it["fact"])
            f.write(json.dumps({**it, "claude_score": score}, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{i + 1}/{len(todo)}] {it['fact_id'][:24]:24s} "
                  f"claude={score:5.1f} ({time.time() - t0:.1f}s)", flush=True)
    return 0


def stage_train(a) -> int:
    from benchmark.local_gate_eval import build_pairs, split_by_user
    from benchmark.local_gate_finetune import (
        build_training_pairs,
        split_train_val,
        train_ce,
    )

    _, corpus_items = load_labeled_jsonl(
        LABELS_JSONL, binarize_at=a.binarize_at if a.binarize_at > 0 else None)
    if not corpus_items:
        print("no labeled corpus data — run --stage label first", file=sys.stderr)
        raise SystemExit(2)

    # same HaluMem train users as v1 (identical seed pipeline)
    eval_pairs = build_pairs(a.halumem, seed=a.seed, n_clean=300, n_interference=300,
                             n_foreign=100, budget=a.budget, speakers=True)
    calib, _held = split_by_user(eval_pairs, seed=a.seed)
    train_users = {p["span_user"] for p in calib}
    halumem_items = build_training_pairs(a.halumem, train_users, seed=a.seed,
                                         budget=a.budget, speakers=True,
                                         foreign_per_user=60)
    # upweight the corpus register by duplication (it is ~20x smaller than HaluMem)
    mix = halumem_items + corpus_items * a.corpus_dup
    print(f"mix: halumem {len(halumem_items)} + corpus {len(corpus_items)}"
          f"x{a.corpus_dup}", file=sys.stderr)
    train_items, val_items = split_train_val(mix, seed=a.seed)
    info = train_ce(a.base_model, train_items, val_items, epochs=a.epochs,
                    batch_size=a.batch, lr=a.lr, max_length=512,
                    out_dir=MODEL_DIR_V2, seed=a.seed)

    from benchmark.local_gate_eval import score_pairs
    from verimem.grounding_gate import optimal_threshold
    from verimem.local_grounding import make_finetuned_scorer
    scorer = make_finetuned_scorer(MODEL_DIR_V2)
    val_scores = score_pairs(val_items, scorer)
    # threshold on HARD val labels (>=0.5) — Youden needs binary targets
    thr = optimal_threshold(val_scores, [1 if x["label"] >= 0.5 else 0
                                         for x in val_items])
    (MODEL_DIR_V2 / "gate_config.json").write_text(json.dumps({
        "threshold": float(thr), "focus_budget": a.budget,
        "base_model": a.base_model, "seed": a.seed,
        "trained_on": "HaluMem GT + real-corpus claude soft labels (v2 mix)",
        "training": info}, indent=2), encoding="utf-8")
    print(json.dumps({"training": info, "threshold": thr}, indent=2))
    return 0


def stage_eval(a) -> int:
    from benchmark.stats import auroc
    from verimem.local_grounding import LocalGroundingJudge, make_finetuned_scorer

    judge = LocalGroundingJudge(model_dir=MODEL_DIR_V2)
    thr = judge.threshold
    scorer = make_finetuned_scorer(MODEL_DIR_V2)

    # (i) the untouched v1 test set: agreement vs the banked claude labels
    d = json.loads(V1_TEST_JSON.read_text(encoding="utf-8"))
    items = d["items"]
    sem = sqlite3.connect(str(SEM_DB))
    epi = sqlite3.connect(str(EPI_DB))
    spans: list[tuple[str, str]] = []
    kept: list[dict] = []
    for it in items:
        fid = it["fact_id"]
        host = fid[5:].partition("<-")[0] if fid.startswith("swap:") else fid
        row = sem.execute("SELECT source_episodes FROM facts WHERE id=?",
                          (host,)).fetchone()
        txt = _episode_text(epi, row[0]) if row and row[0] else None
        if txt:
            spans.append((select_relevant_span(txt, it["fact"], budget=a.budget),
                          it["fact"]))
            kept.append(it)
    sem.close()
    epi.close()
    scores = scorer(spans)
    agree = 0
    real_admit = real_n = 0
    for it, s in zip(kept, scores, strict=True):
        loc_admit = s >= thr
        cl_admit = it["claude"] >= 40.0
        agree += loc_admit == cl_admit
        if it["kind"] == "real_admitted":
            real_n += 1
            real_admit += loc_admit
    res = {"v1_test": {
        "n": len(kept), "threshold": thr,
        "agreement_vs_claude": round(agree / len(kept), 4),
        "real_admit_local": round(real_admit / real_n, 4) if real_n else None,
        "auroc_vs_claude_admit": round(auroc(
            scores, [1 if it["claude"] >= 40 else 0 for it in kept]), 4),
    }}
    print(json.dumps(res, indent=2))
    out = Path("benchmark/results/local_gate_v2_eval.json")
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"(HaluMem regression: python -m benchmark.local_gate_eval "
          f"--finetuned-dir {MODEL_DIR_V2} ...)", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("label", "train", "eval"), required=True)
    ap.add_argument("--n", type=int, default=250)
    ap.add_argument("--n-neg", type=int, default=80)
    ap.add_argument("--seed", type=int, default=11)  # NOT 7: disjoint from v1 sampling
    ap.add_argument("--budget", type=int, default=1500)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--halumem",
                    default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--base-model", default="cross-encoder/nli-deberta-v3-base")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--corpus-dup", type=int, default=6,
                    help="duplication factor for the (smaller) corpus slice in the mix")
    ap.add_argument("--binarize-at", type=float, default=40.0,
                    help="distill the claude admit DECISION at this cut (0 = soft "
                         "score/100 labels — v2 finding: soft collapses the slice)")
    a = ap.parse_args(argv)
    return {"label": stage_label, "train": stage_train, "eval": stage_eval}[a.stage](a)


if __name__ == "__main__":
    raise SystemExit(main())
