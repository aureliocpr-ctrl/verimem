"""Study 2: production false-positive of the NLI conflict detector on the REAL
Engram corpus (the critic's concern — "0 FP on 4 toy pairs" is not evidence at
scale).

Method: take the live corpus, find high-cosine SIBLING pairs (cos >= min_cosine —
the candidates the write-time gate would actually run the NLI on), classify each
with the NLI judge, and report the relation distribution. In a curated corpus most
high-cosine pairs are near-duplicates or complementary facts → the NLI should
mostly answer ENTAILMENT/NEUTRAL; every CONTRADICTION is either a genuine conflict
(good — that is the point) or a false positive. The flagged contradictions are
written out for MANUAL audit — only a human read gives the true FP rate.

CPU part (encode + pairing) is judge-free and smoke-testable; the NLI part uses
claude -p (subscription, O5). Run: `python -m benchmark.corpus_fp_bench --sample 200`.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from engram import embedding
from engram.semantic import SemanticMemory

# Upstream filter (frozen after seed-0 audit): the seed-0 FPs were NOT NLI errors
# on facts — they were pairs that belong to OTHER mechanisms. test/telemetry noise
# should be excluded by the admission gate; timestamped snapshots are a SUPERSESSION
# (later wins), not a contradiction; different bracket-tags are different subjects.
# Validated on a FRESH seed to check it is not overfit to the pairs it was tuned on.
import re as _re

_NOISE_RE = _re.compile(
    r"pytest|cap20|roundtrip|metric_id|wire import event|^\{"
    r"|^[A-Za-z]+ \d+ [0-9a-f]{8}", _re.I)
_DATE_RE = _re.compile(r"20\d\d[-/.]\d{1,2}[-/.]\d{1,2}|@\s*\d{1,2}:\d{2}|\b\d{1,2}:\d{2}\b")
_TAG_RE = _re.compile(r"^\[([A-Z0-9 ]+)\]")


def noise_or_temporal(a: str, b: str) -> str | None:
    """Return a reason string if the pair belongs to another mechanism (so the
    contradiction-NLI should NOT run on it), else None."""
    if _NOISE_RE.search(a) or _NOISE_RE.search(b):
        return "test-noise"
    if _DATE_RE.search(a) and _DATE_RE.search(b):
        return "temporal"
    ta, tb = _TAG_RE.match(a), _TAG_RE.match(b)
    if ta and tb and ta.group(1).strip() != tb.group(1).strip():
        return "diff-tag"
    return None


def find_high_cosine_pairs(
    propositions: list[str], *, sample: int, min_cosine: float, seed: int,
) -> list[tuple[int, int, float]]:
    """For a random sample of facts, find each one's nearest OTHER fact; keep the
    pair when cosine >= min_cosine. Dedupes unordered pairs. CPU-only."""
    if len(propositions) < 2:
        return []
    mat = embedding.encode([embedding.as_passage(p) for p in propositions])
    idx = list(range(len(propositions)))
    random.Random(seed).shuffle(idx)
    seen: set[tuple[int, int]] = set()
    out: list[tuple[int, int, float]] = []
    for i in idx[:sample]:
        sims = embedding.cosine_matrix(mat[i], mat)
        sims[i] = -1.0
        j = int(sims.argmax())
        c = float(sims[j])
        if c < min_cosine:
            continue
        key = (min(i, j), max(i, j))
        if key in seen:
            continue
        seen.add(key)
        out.append((i, j, round(c, 3)))
    return out


def run(
    sm: SemanticMemory, judge: Any, *, sample: int = 200,
    min_cosine: float = 0.7, seed: int = 0, filter_noise: bool = False,
) -> dict[str, Any]:
    from engram.semantic_conflict import Relation

    facts = sm.all()
    props = [f.proposition or "" for f in facts]
    pairs = find_high_cosine_pairs(props, sample=sample, min_cosine=min_cosine, seed=seed)
    rel_counts: Counter = Counter()
    contradictions: list[dict[str, Any]] = []
    filtered = Counter()
    for i, j, c in pairs:
        if filter_noise:
            reason = noise_or_temporal(props[i], props[j])
            if reason:
                filtered[reason] += 1
                continue  # belongs to another mechanism; don't run the NLI
        rel = judge.classify(props[i], props[j])
        rel_counts[rel.value] += 1
        if rel is Relation.CONTRADICTION:
            contradictions.append({
                "cosine": c,
                "a": props[i][:160], "b": props[j][:160],
                "a_id": facts[i].id, "b_id": facts[j].id,
                "topic_a": facts[i].topic, "topic_b": facts[j].topic,
            })
    n_judged = sum(rel_counts.values())
    return {
        "corpus_facts": len(facts),
        "sample": sample, "min_cosine": min_cosine, "seed": seed,
        "filter_noise": filter_noise,
        "n_high_cosine_pairs": len(pairs),
        "n_filtered_upstream": dict(filtered),
        "n_judged_by_nli": n_judged,
        "relation_distribution": dict(rel_counts),
        "contradiction_rate_of_judged": round(rel_counts.get("contradiction", 0) / n_judged, 3) if n_judged else 0.0,
        "flagged_contradictions_for_audit": contradictions,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Real-corpus NLI false-positive study.")
    p.add_argument("--sample", type=int, default=200)
    p.add_argument("--min-cosine", type=float, default=0.7)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--filter-noise", action="store_true",
                   help="skip test-noise / temporal-snapshot / diff-tag pairs before the NLI")
    p.add_argument("--model", type=str, default="claude-sonnet-4-6")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    from benchmark.qa_runner import LeanClaudeCLILLM
    from engram.semantic_conflict import LLMRelationJudge

    judge = LLMRelationJudge(LeanClaudeCLILLM(model=args.model, timeout_s=60))
    res = run(SemanticMemory(), judge, sample=args.sample,
              min_cosine=args.min_cosine, seed=args.seed,
              filter_noise=args.filter_noise)
    res["judge"] = f"claude-cli ({args.model})"
    print(json.dumps({k: v for k, v in res.items()
                      if k != "flagged_contradictions_for_audit"}, indent=2))
    print(f"\n{len(res['flagged_contradictions_for_audit'])} flagged contradictions "
          f"-> manual audit (see --out json)")
    if args.out:
        args.out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["find_high_cosine_pairs", "run", "main"]
