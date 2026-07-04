"""Distilled local write-gate — fine-tune a CE on HaluMem ground truth (task #1 ph. 2).

Zero-shot CE-NLI plateaued at heldout AUROC 0.75-0.81 (local_gate_eval v2): the pure
NLI axis is nearly solved (clean-vs-foreign 0.91-0.96) but clean-admit stalls at
0.57-0.74 and the ATTRIBUTION axis (assistant-injected false memories, HaluMem
'interference') sits at 0.66-0.77. The claude production judge itself ADMITS ~40% of
those interference points (benchmark/results/attribution_probe_claude.json) — an
entailment-only judge, human or local, is blind to WHO asserted the evidence.

So: fine-tune the CE on the dataset's own ground truth — no claude labels needed
(distilling claude would inherit that blindness):

  label 1  clean          memory_source in {system, secondary, primary}, own session
  label 0  interference   HaluMem's native assistant-injected false memories
  label 0  foreign        another TRAIN user's fact vs this user's dialogue

Split hygiene: train/heldout users are THE SAME split as local_gate_eval (same seed
pipeline); every training pair — including foreign donors — comes from TRAIN users
only. The decision threshold is calibrated on a stratified 10% VAL slice that the
optimizer never sees. All reported numbers are heldout-users only.

    python -m benchmark.local_gate_finetune \
        --base-model cross-encoder/nli-deberta-v3-base --epochs 2 \
        --out-dir ~/.engram/models/local_gate_ce \
        --results benchmark/results/local_gate_finetune_v1.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

from benchmark.halumem_writepath_moat import _TRUE_SRC
from benchmark.local_gate_eval import (
    _session_dialogue,
    _user_name,
    build_pairs,
    evaluate,
    score_pairs,
    split_by_user,
)
from benchmark.stats import auroc
from engram.grounding_gate import optimal_threshold, select_relevant_span
from engram.local_grounding import make_finetuned_scorer


def build_training_pairs(jsonl: str | Path, train_users: set[int], *, seed: int,
                         budget: int, speakers: bool, foreign_per_user: int = 60,
                         ) -> list[dict]:
    """ALL usable clean/interference points of the TRAIN users (own-session span),
    plus foreign negatives drawn ONLY from other TRAIN users. Positives are capped at
    2x negatives (class balance). Deterministic under ``seed``."""
    users = []
    with open(jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))

    rng = random.Random(seed)
    clean: list[dict] = []
    interf: list[dict] = []
    dialogues: dict[int, list[str]] = {}
    seen: set[str] = set()

    for ui, u in enumerate(users):
        if ui not in train_users:
            continue
        smap = None
        if speakers:
            name = _user_name(u)
            smap = {"user": name or "user", "assistant": "Assistant"}
        for s in u.get("sessions", []):
            dlg = _session_dialogue(s, smap)
            if not dlg:
                continue
            dialogues.setdefault(ui, []).append(dlg)
            for mp in s.get("memory_points", []):
                fact = (mp.get("memory_content") or "").strip()
                srct = str(mp.get("memory_source", "")).lower()
                if not fact or fact in seen:
                    continue
                item = {"fact": fact, "dialogue": dlg, "fact_user": ui,
                        "span_user": ui}
                if srct in _TRUE_SRC:
                    seen.add(fact)
                    clean.append(dict(item, kind="clean", label=1))
                elif srct == "interference":
                    seen.add(fact)
                    interf.append(dict(item, kind="interference", label=0))

    foreign: list[dict] = []
    uids = sorted(dialogues)
    if len(uids) >= 2:
        for ui in uids:
            donors = [c for c in clean if c["fact_user"] != ui]
            rng.shuffle(donors)
            for d in donors[:foreign_per_user]:
                foreign.append({
                    "fact": d["fact"], "dialogue": rng.choice(dialogues[ui]),
                    "fact_user": d["fact_user"], "span_user": ui,
                    "kind": "foreign", "label": 0,
                })

    rng.shuffle(clean)
    n_neg = len(interf) + len(foreign)
    clean = clean[: max(1, 2 * n_neg)]

    items = clean + interf + foreign
    for it in items:
        it["span"] = select_relevant_span(it.pop("dialogue"), it["fact"],
                                          budget=budget)
    rng.shuffle(items)
    return items


def split_train_val(items: list[dict], *, seed: int, val_frac: float = 0.1,
                    ) -> tuple[list[dict], list[dict]]:
    """Stratified-by-label val slice, excluded from the optimizer — used for best-epoch
    selection and threshold calibration."""
    rng = random.Random(seed + 2)
    tr: list[dict] = []
    va: list[dict] = []
    for lab in (0, 1):
        grp = [x for x in items if x["label"] == lab]
        rng.shuffle(grp)
        k = max(1, int(len(grp) * val_frac))
        va.extend(grp[:k])
        tr.extend(grp[k:])
    rng.shuffle(tr)
    rng.shuffle(va)
    return tr, va


def train_ce(base_model: str, train_items: list[dict], val_items: list[dict], *,
             epochs: int, batch_size: int, lr: float, max_length: int,
             out_dir: Path, seed: int) -> dict:
    """Plain torch loop: binary head (num_labels=1) on the CE body, BCE loss, AMP,
    best epoch by VAL AUROC, saved to ``out_dir``. Returns training info."""
    import numpy as np
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        base_model, num_labels=1, ignore_mismatched_sizes=True).to(device)

    def encode(batch: list[dict]):
        enc = tok([b["span"] for b in batch], [b["fact"] for b in batch],
                  truncation="longest_first", max_length=max_length,
                  padding=True, return_tensors="pt")
        return {k: v.to(device) for k, v in enc.items()}

    @torch.no_grad()
    def val_scores() -> list[float]:
        model.eval()
        out: list[float] = []
        for i in range(0, len(val_items), batch_size):
            chunk = val_items[i:i + batch_size]
            logits = model(**encode(chunk)).logits.squeeze(-1)
            out.extend(torch.sigmoid(logits).float().cpu().tolist())
        return [x * 100.0 for x in out]

    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    n_steps = max(1, (len(train_items) + batch_size - 1) // batch_size) * epochs
    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt, max_lr=lr, total_steps=n_steps, pct_start=0.1)
    scaler = torch.amp.GradScaler(enabled=device == "cuda")
    loss_fn = torch.nn.BCEWithLogitsLoss()
    val_labels = [x["label"] for x in val_items]

    best = {"val_auroc": -1.0, "epoch": -1}
    order = list(range(len(train_items)))
    rng = random.Random(seed + 3)
    for ep in range(epochs):
        model.train()
        rng.shuffle(order)
        tot, nb = 0.0, 0
        t0 = time.time()
        for i in range(0, len(order), batch_size):
            chunk = [train_items[j] for j in order[i:i + batch_size]]
            labels = torch.tensor([float(c["label"]) for c in chunk], device=device)
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device, enabled=device == "cuda"):
                logits = model(**encode(chunk)).logits.squeeze(-1)
                loss = loss_fn(logits, labels)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            tot += float(loss.item())
            nb += 1
        va = round(auroc(val_scores(), val_labels), 4)
        print(f"epoch {ep}: loss {tot / max(1, nb):.4f} val-AUROC {va} "
              f"({time.time() - t0:.0f}s)", file=sys.stderr, flush=True)
        if va > best["val_auroc"]:
            best = {"val_auroc": va, "epoch": ep}
            out_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(out_dir)
            tok.save_pretrained(out_dir)
    return {"base_model": base_model, "device": device, "epochs": epochs,
            "batch_size": batch_size, "lr": lr, "best": best,
            "n_train": len(train_items), "n_val": len(val_items)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--base-model", default="cross-encoder/nli-deberta-v3-base")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--budget", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--foreign-per-user", type=int, default=60)
    ap.add_argument("--eval-clean", type=int, default=300)
    ap.add_argument("--eval-interference", type=int, default=300)
    ap.add_argument("--eval-foreign", type=int, default=100)
    ap.add_argument("--out-dir", default=str(Path.home() / ".engram/models/local_gate_ce"))
    ap.add_argument("--results", default=None)
    a = ap.parse_args(argv)

    if not Path(a.jsonl).exists():
        print(f"dataset not found: {a.jsonl}", file=sys.stderr)
        raise SystemExit(2)

    # Same eval pairs + user split as local_gate_eval (seed pipeline identical) —
    # numbers directly comparable with the zero-shot runs.
    eval_pairs = build_pairs(a.jsonl, seed=a.seed, n_clean=a.eval_clean,
                             n_interference=a.eval_interference,
                             n_foreign=a.eval_foreign, budget=a.budget,
                             speakers=True)
    calib, held = split_by_user(eval_pairs, seed=a.seed)
    train_users = {p["span_user"] for p in calib}
    held_users = {p["span_user"] for p in held}
    assert train_users.isdisjoint(held_users)

    items = build_training_pairs(a.jsonl, train_users, seed=a.seed, budget=a.budget,
                                 speakers=True, foreign_per_user=a.foreign_per_user)
    train_items, val_items = split_train_val(items, seed=a.seed)
    print(f"train {len(train_items)} (pos {sum(x['label'] for x in train_items)}) "
          f"val {len(val_items)} | heldout users {sorted(held_users)}",
          file=sys.stderr)

    out_dir = Path(a.out_dir).expanduser()
    info = train_ce(a.base_model, train_items, val_items, epochs=a.epochs,
                    batch_size=a.batch, lr=a.lr, max_length=512,
                    out_dir=out_dir, seed=a.seed)

    scorer = make_finetuned_scorer(out_dir)
    # threshold from VAL (never optimized on), applied to heldout
    val_scores = score_pairs(val_items, scorer)
    thr = optimal_threshold(val_scores, [x["label"] for x in val_items])
    held_scores = score_pairs(held, scorer)
    ev = evaluate([], [], held, held_scores, threshold=thr)

    t0 = time.perf_counter()
    scorer([(held[0]["span"], held[0]["fact"])])
    single_ms = (time.perf_counter() - t0) * 1000.0

    # ship the calibrated cut with the model — the production local backend
    # (engram/local_grounding.py) reads gate_config.json for its default threshold
    (out_dir / "gate_config.json").write_text(json.dumps({
        "threshold": float(thr), "focus_budget": a.budget,
        "base_model": a.base_model, "seed": a.seed,
        "trained_on": "HaluMem-Medium ground truth (train users only)",
        "heldout_auroc": ev["auroc_heldout"],
    }, indent=2), encoding="utf-8")

    res = {"config": vars(a), "training": info,
           "threshold_from_val": float(thr),
           "heldout": ev["heldout"],
           "auroc_heldout": ev["auroc_heldout"],
           "auroc_clean_vs_interference": ev.get("auroc_clean_vs_interference"),
           "auroc_clean_vs_foreign": ev.get("auroc_clean_vs_foreign"),
           "latency_single_ms": round(single_ms, 1),
           "reference": {
               "zero_shot_v2": "local_gate_eval_v2_sentmax.json (base 0.75 / large 0.81)",
               "claude_probe": "attribution_probe_claude.json (clean 0.80, interference ADMIT 0.40, n=15)",
           }}
    print(json.dumps(res, indent=2))
    if a.results:
        Path(a.results).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
