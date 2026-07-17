"""Local grounding gate — zero-shot CE-NLI vs HaluMem ground truth (2027 task #1).

Why: the write-gate's judge is one ``claude -p`` call per candidate fact
(``grounding_gate.fact_grounding_score``); headless subscription calls are moving to
paid, so the gate needs a LOCAL backend. This bench measures whether an off-the-shelf
cross-encoder NLI model can match the claude judge — scored DIRECTLY against HaluMem
ground truth, not distilled from claude labels (distillation would inherit the
teacher's errors AND cost a labeling run; the semantic.db ``grounding_score`` column
is empty — 0/5412 — so there is no free persisted training set, contrary to the
2026-07-01 handoff hypothesis).

Pairs (all from ``~/.cache/halumem/HaluMem-Medium.jsonl``, seed-deterministic):

* clean (label 1)        — memory points with memory_source in {system, secondary,
                           primary}, paired with THEIR OWN session dialogue.
* interference (label 0) — HaluMem's NATIVE hallucinated memory points (2648 in
                           Medium): same-topic, plausible, NOT supported by the
                           dialogue — the realistic write-poisoning threat, labeled
                           by the dataset itself (zero claude calls to build).
* foreign (label 0)      — another user's facts vs this user's dialogue (easy floor).

The source is span-selected with the SHIPPED production selector
(``verimem.grounding_gate.select_relevant_span``) at ``--budget`` chars — the same
code path as ``fact_grounding_score(focus_budget=...)`` — so the eval measures the
deployment configuration (CE max_length 512 tokens ≈ 1500-2000 chars).

Split is BY USER (calib users ∩ heldout users = ∅): the threshold is calibrated on
calib (Youden, ``grounding_gate.optimal_threshold``) and every reported rate/AUROC is
heldout-only — out-of-user generalization, no session leakage.

Reference points (claude judge): clean-admit 0.80 / noise-admit 0.0 at budget 2000
(halumem_gate_source_ab.json, n=20/10/8); SNLI AUROC 0.971. Honest scope: HaluMem is
EN-only — the live corpus is IT/mixed, so a multilingual CE (mDeBERTa-xnli) is the
follow-up if the EN result holds; zero-shot, no finetuning.

    python -m benchmark.local_gate_eval \
        --models cross-encoder/nli-deberta-v3-base \
        --clean 600 --interference 600 --foreign 200 --budget 1500 \
        --out benchmark/results/local_gate_eval.json
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path

from benchmark.halumem_writepath_moat import _TRUE_SRC, wilson
from benchmark.stats import auroc
from verimem.grounding_gate import optimal_threshold, select_relevant_span

Scorer = Callable[[list[tuple[str, str]]], list[float]]


def _session_dialogue(session: dict, speaker_map: dict[str, str] | None = None) -> str:
    out = []
    for t in session.get("dialogue", []) or []:
        c = (t.get("content") or "").strip()
        role = str(t.get("role", "?"))
        if speaker_map:
            role = speaker_map.get(role.lower(), role)
        if c:
            out.append(f"{role}: {c}")
    return "\n".join(out)


_NAME_RE = re.compile(r"user'?s name is\s+([^.\n]+)", re.I)


def _user_name(user: dict) -> str | None:
    """The user's real name from HaluMem's 'system' memory points, if declared."""
    for s in user.get("sessions", []):
        for mp in s.get("memory_points", []):
            if str(mp.get("memory_source", "")).lower() == "system":
                m = _NAME_RE.search(mp.get("memory_content") or "")
                if m:
                    return m.group(1).strip()
    return None


def build_pairs(jsonl: str | Path, *, seed: int, n_clean: int, n_interference: int,
                n_foreign: int, budget: int, speakers: bool = False) -> list[dict]:
    """Seed-deterministic (span, fact, label) pairs. Every clean/interference point is
    paired with ITS OWN session dialogue (same-topic by construction — the CE cannot
    win on topic mismatch); foreign facts are paired with a DIFFERENT user's dialogue.
    Facts are globally deduped by text before sampling (a duplicate fact landing in
    both splits would leak). ``speakers=True`` replaces the 'user:' turn prefix with
    the user's declared NAME (from the system memory point) — third-person facts
    ('Jennifer's status…') then co-refer with the dialogue ('Jennifer: I…'), which the
    live write-path can replicate since it knows its user."""
    users = []
    with open(jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                users.append(json.loads(line))

    rng = random.Random(seed)
    clean_pool: list[dict] = []
    interf_pool: list[dict] = []
    sessions_by_user: dict[int, list[str]] = {}
    seen_facts: set[str] = set()

    for ui, u in enumerate(users):
        smap = None
        if speakers:
            name = _user_name(u)
            smap = {"user": name or "user", "assistant": "Assistant"}
        for s in u.get("sessions", []):
            dlg = _session_dialogue(s, smap)
            if not dlg:
                continue
            sessions_by_user.setdefault(ui, []).append(dlg)
            for mp in s.get("memory_points", []):
                fact = (mp.get("memory_content") or "").strip()
                srct = str(mp.get("memory_source", "")).lower()
                if not fact or fact in seen_facts:
                    continue
                item = {"fact": fact, "dialogue": dlg, "fact_user": ui, "span_user": ui}
                if srct in _TRUE_SRC:
                    seen_facts.add(fact)
                    clean_pool.append(dict(item, kind="clean", label=1))
                elif srct == "interference":
                    seen_facts.add(fact)
                    interf_pool.append(dict(item, kind="interference", label=0))

    rng.shuffle(clean_pool)
    rng.shuffle(interf_pool)
    picked = clean_pool[:n_clean] + interf_pool[:n_interference]

    # foreign: another user's CLEAN fact vs a random session of this user.
    foreign: list[dict] = []
    user_ids = sorted(sessions_by_user)
    if len(user_ids) >= 2 and n_foreign > 0:
        donors = [p for p in clean_pool[n_clean:]] or clean_pool[:n_clean]
        rng.shuffle(donors)
        for d in donors:
            hosts = [ui for ui in user_ids if ui != d["fact_user"]]
            if not hosts:
                continue
            host = rng.choice(hosts)
            foreign.append({
                "fact": d["fact"], "dialogue": rng.choice(sessions_by_user[host]),
                "fact_user": d["fact_user"], "span_user": host,
                "kind": "foreign", "label": 0,
            })
            if len(foreign) >= n_foreign:
                break

    pairs = picked + foreign
    for p in pairs:
        p["span"] = select_relevant_span(p.pop("dialogue"), p["fact"], budget=budget)
    rng.shuffle(pairs)
    return pairs


def split_by_user(pairs: list[dict], *, seed: int, calib_frac: float = 0.5,
                  ) -> tuple[list[dict], list[dict]]:
    """Partition BY span_user: a user's sessions never straddle calib/heldout."""
    users = sorted({p["span_user"] for p in pairs})
    random.Random(seed + 1).shuffle(users)
    k = max(1, int(len(users) * calib_frac)) if len(users) > 1 else 0
    calib_users = set(users[:k])
    calib = [p for p in pairs if p["span_user"] in calib_users]
    held = [p for p in pairs if p["span_user"] not in calib_users]
    return calib, held


def score_pairs(pairs: list[dict], scorer: Scorer, *, batch_size: int = 32,
                ) -> list[float]:
    """Apply an injected scorer to (span, fact) pairs, preserving order."""
    out: list[float] = []
    for i in range(0, len(pairs), batch_size):
        chunk = [(p["span"], p["fact"]) for p in pairs[i:i + batch_size]]
        out.extend(float(s) for s in scorer(chunk))
    return out


def evaluate(calib: list[dict], calib_scores: list[float],
             held: list[dict], held_scores: list[float], *,
             threshold: float | None = None) -> dict:
    """Threshold from calib (Youden) unless an explicit ``threshold`` is given (e.g.
    calibrated on a training VAL slice); every reported number is heldout-only."""
    thr = (float(threshold) if threshold is not None
           else optimal_threshold(calib_scores, [p["label"] for p in calib]))
    res: dict = {"threshold": float(thr), "n_calib": len(calib), "n_heldout": len(held),
                 "heldout": {}}
    by_kind: dict[str, list[float]] = {}
    for kind in ("clean", "interference", "foreign"):
        sc = [s for s, p in zip(held_scores, held, strict=True) if p["kind"] == kind]
        by_kind[kind] = sc
        if not sc:
            res["heldout"][kind] = {"n": 0, "admit_rate": None, "wilson95": None}
            continue
        k = sum(1 for s in sc if s >= thr)
        res["heldout"][kind] = {
            "n": len(sc), "admit_rate": round(k / len(sc), 4),
            "wilson95": wilson(k, len(sc)),
            "mean_score": round(sum(sc) / len(sc), 2),
        }
    labels = [p["label"] for p in held]
    has_both = 0 < sum(labels) < len(labels)
    res["auroc_heldout"] = round(auroc(held_scores, labels), 4) if has_both else None
    # per-kind AUROCs: clean-vs-foreign is the pure NLI task; clean-vs-interference is
    # the ATTRIBUTION task (HaluMem injects the false memory VERBATIM into the dialogue
    # as an assistant turn — an entailment-only judge, local or claude, admits it).
    cl = by_kind["clean"]
    for neg in ("interference", "foreign"):
        sc = cl + by_kind[neg]
        lab = [1] * len(cl) + [0] * len(by_kind[neg])
        res[f"auroc_clean_vs_{neg}"] = (
            round(auroc(sc, lab), 4) if cl and by_kind[neg] else None)
    return res


def split_units(span: str, *, max_unit_chars: int = 400, bigrams: bool = True,
                max_units: int = 80) -> list[str]:
    """Scoring units for sentence-level NLI: dialogue turns (lines), long lines broken
    into sentences, plus adjacent-turn bigrams (cross-turn evidence) when ``bigrams``.
    CE-NLI models are trained on 1-2 sentence premises — scoring per-unit and
    max-pooling recovers the lost recall of a document-level premise (SummaC-style)."""
    lines = [ln for ln in (span or "").split("\n") if ln.strip()]
    units: list[str] = []
    for ln in lines:
        if len(ln) <= max_unit_chars:
            units.append(ln)
        else:
            sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", ln) if x.strip()]
            buf = ""
            for x in sents:
                if buf and len(buf) + len(x) + 1 > max_unit_chars:
                    units.append(buf)
                    buf = x
                else:
                    buf = f"{buf} {x}".strip()
            if buf:
                units.append(buf)
    if bigrams:
        units = units + [f"{a}\n{b}" for a, b in zip(units, units[1:], strict=False)]
    return units[:max_units] if units else ([span] if span else [])


def make_sent_max_scorer(base: Scorer, *, bigrams: bool = True) -> Scorer:
    """Wrap a (premise, hypothesis) scorer: score the hypothesis against EVERY unit of
    the premise and take the max — 'does at least one place in the source entail the
    fact?', the write-gate semantics. One flattened batch per call (the base scorer
    handles its own internal batching)."""

    def scorer(batch: list[tuple[str, str]]) -> list[float]:
        flat: list[tuple[str, str]] = []
        spans_of: list[tuple[int, int]] = []
        for prem, hyp in batch:
            units = split_units(prem, bigrams=bigrams)
            spans_of.append((len(flat), len(flat) + len(units)))
            flat.extend((u, hyp) for u in units)
        scores = list(base(flat)) if flat else []
        return [max(scores[i:j]) if j > i else 0.0 for i, j in spans_of]

    return scorer


def make_ce_scorer(model_name: str, *, max_length: int = 512) -> tuple[Scorer, dict]:
    """Production scorer: CrossEncoder NLI → P(entailment)*100. The entailment logit
    index is read from the model config (NOT assumed); raises if the model has no
    'entailment' label. Returns (scorer, info)."""
    import numpy as np
    from sentence_transformers import CrossEncoder

    t0 = time.time()
    ce = CrossEncoder(model_name, max_length=max_length)
    load_s = time.time() - t0
    id2label = getattr(getattr(ce.model, "config", None), "id2label", None) or {}
    ent_idx = next((int(i) for i, lab in id2label.items()
                    if str(lab).lower() == "entailment"), None)
    if ent_idx is None:
        raise ValueError(f"{model_name}: no 'entailment' label in id2label={id2label}")

    def scorer(batch: list[tuple[str, str]]) -> list[float]:
        logits = ce.predict(batch, convert_to_numpy=True, show_progress_bar=False)
        logits = np.atleast_2d(logits)
        e = np.exp(logits - logits.max(axis=1, keepdims=True))
        p = e / e.sum(axis=1, keepdims=True)
        return [float(x) * 100.0 for x in p[:, ent_idx]]

    info = {"model": model_name, "load_s": round(load_s, 1),
            "id2label": {str(k): v for k, v in id2label.items()},
            "device": str(getattr(ce.model, "device", "?")), "max_length": max_length}
    return scorer, info


def _latency_single(scorer: Scorer, pairs: list[dict], *, n: int = 20) -> dict:
    """Per-call latency on single pairs (the live write-path shape), after warmup."""
    sample = pairs[:n]
    if not sample:
        return {"n": 0}
    scorer([(sample[0]["span"], sample[0]["fact"])])  # warmup
    times = []
    for p in sample:
        t0 = time.perf_counter()
        scorer([(p["span"], p["fact"])])
        times.append((time.perf_counter() - t0) * 1000.0)
    times.sort()
    return {"n": len(times), "p50_ms": round(times[len(times) // 2], 1),
            "p95_ms": round(times[int(len(times) * 0.95) - 1], 1),
            "mean_ms": round(sum(times) / len(times), 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--models", nargs="+",
                    default=["cross-encoder/nli-deberta-v3-base"])
    ap.add_argument("--clean", type=int, default=600)
    ap.add_argument("--interference", type=int, default=600)
    ap.add_argument("--foreign", type=int, default=200)
    ap.add_argument("--budget", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--mode", choices=("doc", "sent_max"), default="doc",
                    help="doc: whole span as one premise; sent_max: per-unit max-pool")
    ap.add_argument("--speakers", action="store_true",
                    help="name the 'user:' turns with the user's declared name")
    ap.add_argument("--finetuned-dir", default=None,
                    help="evaluate a fine-tuned binary-head model dir (threshold from "
                         "its gate_config.json) instead of --models")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dump-pairs", default=None,
                    help="also persist the labeled pairs JSON (reusable dataset)")
    a = ap.parse_args(argv)

    if not Path(a.jsonl).exists():
        print(f"dataset not found: {a.jsonl}", file=sys.stderr)
        raise SystemExit(2)

    pairs = build_pairs(a.jsonl, seed=a.seed, n_clean=a.clean,
                        n_interference=a.interference, n_foreign=a.foreign,
                        budget=a.budget, speakers=a.speakers)
    calib, held = split_by_user(pairs, seed=a.seed)
    if a.dump_pairs:
        Path(a.dump_pairs).write_text(json.dumps(pairs, indent=1), encoding="utf-8")

    res: dict = {
        "jsonl": a.jsonl, "seed": a.seed, "budget_chars": a.budget,
        "mode": a.mode, "speakers": bool(a.speakers),
        "n_pairs": len(pairs),
        "n_by_kind": {k: sum(1 for p in pairs if p["kind"] == k)
                      for k in ("clean", "interference", "foreign")},
        "split": {"calib_users": len({p['span_user'] for p in calib}),
                  "heldout_users": len({p['span_user'] for p in held}),
                  "n_calib": len(calib), "n_heldout": len(held)},
        "reference_claude": {
            "note": "halumem_gate_source_ab.json budget=2000 n=20/10/8: clean-admit "
                    "0.80, foreign/confab 0.0; SNLI AUROC 0.971 (different set)"},
        "models": {},
    }

    model_specs: list[tuple[str, object, dict, float | None]] = []
    if a.finetuned_dir:
        from verimem.local_grounding import LocalGroundingJudge, make_finetuned_scorer
        judge = LocalGroundingJudge(model_dir=a.finetuned_dir)
        model_specs.append((str(a.finetuned_dir),
                            make_finetuned_scorer(a.finetuned_dir),
                            {"model": str(a.finetuned_dir), "kind": "finetuned",
                             "gate_config": judge.config},
                            judge.threshold))
    else:
        for name in a.models:
            scorer, info = make_ce_scorer(name)
            model_specs.append((name, scorer, info, None))

    for name, scorer, info, fixed_thr in model_specs:
        print(f"== {name} ({a.mode})", file=sys.stderr)
        if a.mode == "sent_max":
            scorer = make_sent_max_scorer(scorer)
        t0 = time.time()
        calib_scores = [] if fixed_thr is not None else score_pairs(calib, scorer)
        held_scores = score_pairs(held, scorer)
        batch_s = time.time() - t0
        ev = evaluate(calib, calib_scores, held, held_scores, threshold=fixed_thr)
        ev["latency_single"] = _latency_single(scorer, held)
        ev["batch_total_s"] = round(batch_s, 1)
        ev["batch_ms_per_pair"] = round(batch_s * 1000.0 / max(1, len(pairs)), 1)
        # honest error inspection: worst heldout mistakes at the calibrated threshold
        thr = ev["threshold"]
        fn = [(s, p) for s, p in zip(held_scores, held, strict=True)
              if p["label"] == 1 and s < thr]
        fp = [(s, p) for s, p in zip(held_scores, held, strict=True)
              if p["label"] == 0 and s >= thr]
        ev["errors_sample"] = {
            "false_reject_clean": [{"score": round(s, 1), "fact": p["fact"][:140]}
                                   for s, p in sorted(fn)[:3]],
            "false_admit_noise": [{"score": round(s, 1), "kind": p["kind"],
                                   "fact": p["fact"][:140]}
                                  for s, p in sorted(fp, reverse=True)[:3]],
        }
        res["models"][name] = {**info, **ev}
        print(json.dumps({name: {k: ev[k] for k in
                                 ("threshold", "auroc_heldout", "heldout",
                                  "latency_single")}}, indent=2), file=sys.stderr)

    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
