"""HaluMem interference → contradiction/grounding evaluation, stage 0 (retrieval).

HaluMem (arXiv:2511.03506) labels each memory point ``memory_source`` ∈
{system, secondary, interference}. ``interference`` points are plausible-sounding
distortions injected to test whether a memory system *admits* corrupted memories.

This is the HONEST framing of Engram on its differentiator axis: an interference
point is caught either because it CONTRADICTS an already-stored true memory
(Engram's ``semantic_conflict`` layer) or because it is UNSUPPORTED by any stored
memory (Engram's grounding gate). A single-mechanism score under-reports; the
research value is the *decomposition*.

Stage 0 (this file, fully offline): flatten the dataset, embed each conversation's
TRUE memory set (system+secondary) with the local e5 model, and for a stratified
sample of interference points (positives) and secondary points (controls) retrieve
the top-k nearest true memories. Emits judgment tasks as JSON. The relation
judgment itself (stage 1) is done by an LLM panel (workflow) and scored by
``halumem_interference_score`` (stage 2) — kept separate so stage 0 needs no LLM.

Run:
    python -m benchmark.halumem_interference_stage \
        --jsonl ~/.cache/halumem/HaluMem-Medium.jsonl \
        --n-pos 80 --n-neg 80 --topk 5 --seed 7 \
        --out benchmark/results/halumem_tasks_seed7.json
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np

from verimem import embedding as E

_TRUE_LABELS = ("system", "secondary")


def flatten(jsonl_path: Path) -> list[dict]:
    """Return per-conversation dicts: {uuid, true:[str], interference:[str]}.

    De-duplicates identical memory_content within a conversation (HaluMem repeats
    persona rows across sessions) so retrieval candidates are distinct.
    """
    convs: list[dict] = []
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            true_seen: dict[str, None] = {}
            interf_seen: dict[str, None] = {}
            for s in c.get("sessions", []):
                for mp in s.get("memory_points", []):
                    src = str(mp.get("memory_source", "")).lower()
                    txt = (mp.get("memory_content") or "").strip()
                    if not txt:
                        continue
                    if src in _TRUE_LABELS:
                        true_seen.setdefault(txt, None)
                    elif src == "interference":
                        interf_seen.setdefault(txt, None)
            convs.append({
                "uuid": c.get("uuid"),
                "true": list(true_seen),
                "interference": list(interf_seen),
            })
    return convs


def _topk_candidates(query: str, corpus_txt: list[str], corpus_vec: np.ndarray,
                     k: int, exclude_self: bool) -> list[dict]:
    qv = E.encode(E.as_query(query))
    sims = E.cosine_matrix(qv, corpus_vec)
    order = np.argsort(-sims)
    out: list[dict] = []
    for idx in order:
        cand = corpus_txt[idx]
        sim = float(sims[idx])
        # For a control (the query IS a true memory), drop the self-match and any
        # near-identical paraphrase so the judge sees genuinely *other* memories.
        if exclude_self and (cand == query or sim >= 0.999):
            continue
        out.append({"text": cand, "sim": round(sim, 4)})
        if len(out) >= k:
            break
    return out


def build_tasks(convs: list[dict], *, n_pos: int, n_neg: int, topk: int,
                seed: int) -> list[dict]:
    rng = random.Random(seed)
    # Collect candidate (conv_idx, kind, text) then stratified-sample.
    pos_pool: list[tuple[int, str]] = []
    neg_pool: list[tuple[int, str]] = []
    for ci, c in enumerate(convs):
        if len(c["true"]) < topk + 2:
            continue  # too small to retrieve a meaningful candidate set
        for t in c["interference"]:
            pos_pool.append((ci, t))
        for t in c["true"]:
            neg_pool.append((ci, t))
    rng.shuffle(pos_pool)
    rng.shuffle(neg_pool)
    pos_pool = pos_pool[:n_pos]
    neg_pool = neg_pool[:n_neg]

    # Embed only the true sets of conversations we actually sampled from.
    needed = {ci for ci, _ in pos_pool} | {ci for ci, _ in neg_pool}
    corpus_cache: dict[int, np.ndarray] = {}
    for ci in sorted(needed):
        txts = convs[ci]["true"]
        corpus_cache[ci] = np.vstack([E.encode(E.as_passage(t)) for t in txts])

    tasks: list[dict] = []
    tid = 0
    for ci, txt in pos_pool:
        cands = _topk_candidates(txt, convs[ci]["true"], corpus_cache[ci],
                                 topk, exclude_self=False)
        tasks.append({"id": tid, "conv": ci, "label": "interference",
                      "claim": txt, "candidates": cands})
        tid += 1
    for ci, txt in neg_pool:
        cands = _topk_candidates(txt, convs[ci]["true"], corpus_cache[ci],
                                 topk, exclude_self=True)
        tasks.append({"id": tid, "conv": ci, "label": "true",
                      "claim": txt, "candidates": cands})
        tid += 1
    return tasks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, required=True)
    ap.add_argument("--n-pos", type=int, default=80)
    ap.add_argument("--n-neg", type=int, default=80)
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    convs = flatten(args.jsonl.expanduser())
    n_true = sum(len(c["true"]) for c in convs)
    n_interf = sum(len(c["interference"]) for c in convs)
    print(f"flattened: {len(convs)} convs | true={n_true} interference={n_interf}")

    tasks = build_tasks(convs, n_pos=args.n_pos, n_neg=args.n_neg,
                        topk=args.topk, seed=args.seed)
    n_pos = sum(1 for t in tasks if t["label"] == "interference")
    n_neg = sum(1 for t in tasks if t["label"] == "true")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "meta": {"jsonl": str(args.jsonl), "seed": args.seed, "topk": args.topk,
                 "n_pos": n_pos, "n_neg": n_neg},
        "tasks": tasks,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(tasks)} tasks ({n_pos} interference / {n_neg} control) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
