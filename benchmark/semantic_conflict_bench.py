"""Bench: is Engram's write-time conflict/grounding LEXICAL or SEMANTIC?

Labeled pairs across 5 cases. Measures, per case, whether the LEXICAL stack
(coherence_check numeric/boolean clash + looks_like_conflict + facts_conflict) and
the new SEMANTIC detector (verimem.semantic_conflict, NLI judge) fire — and the
cosine (to prove the hard cases ARE detectable in principle).

Key number: case A (conflict where WORDS differ but MEANING conflicts, no number /
no negation token, cosine 0.80-0.87) — the lexical stack catches ~0; a real
semantic detector should catch most WITHOUT false-positiving on case E
(complementary facts about the same subject, also high cosine).

Judge-free for the lexical baseline; the semantic detector uses an injected judge
(live: claude -p lean — subscription, O5). Run: `python -m benchmark.semantic_conflict_bench`.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from verimem.coherence_check import check_against_siblings
from verimem.contradiction import _cosine
from verimem.facts_conflict import find_conflicting_pairs
from verimem.semantic import Fact
from verimem.semantic_conflict import detect_semantic_conflicts
from verimem.truth_reconciliation import looks_like_conflict

# (a, b, case). A=semantic conflict (hard), B=numeric, C=negation,
# D=paraphrase-duplicate (not a conflict), E=complementary (not a conflict).
PAIRS: list[tuple[str, str, str]] = [
    ("Caroline relocated to Milan last year.",
     "Caroline has been living in Rome the whole time.", "A"),
    ("Mark switched his main language to Rust.",
     "Mark codes primarily in Go these days.", "A"),
    ("The team adopted PostgreSQL for storage.",
     "We keep everything in MongoDB now.", "A"),
    ("Alice became a strict vegetarian.",
     "Alice loves a good steak dinner.", "A"),
    ("The release shipped right on schedule.",
     "We ended up delaying the launch.", "A"),
    ("The feature is fully enabled in production.",
     "The feature is turned off for everyone.", "A"),
    ("Tom's startup was acquired by Google.",
     "Tom still runs his startup independently.", "A"),
    ("The contract was signed in January.",
     "The deal fell through before any contract.", "A"),
    ("The cache holds 30 entries.", "The cache holds 5 entries.", "B"),
    ("The timeout is 60 seconds.", "The timeout is 10 seconds.", "B"),
    ("The build passes all the tests.",
     "The build does not pass the tests.", "C"),
    ("The migration was never applied.",
     "The migration was applied successfully.", "C"),
    ("Alice works as a physician.", "Alice is a doctor.", "D"),
    ("The server crashed.", "The server went down.", "D"),
    ("John lives in Rome.", "John is 30 years old.", "E"),
    ("The cache holds 1024 entries.", "The eviction policy is LRU.", "E"),
    ("Sara plays the violin.", "Sara has two younger brothers.", "E"),
    ("The API is written in Go.", "The API is documented in Swagger.", "E"),
]


def _lexical_conflict(f_new: Fact, f_old: Fact) -> bool:
    """Any LEXICAL detector flags a CONFLICT (not a mere duplicate)."""
    coh = check_against_siblings(f_new, [f_old])
    if any(w.kind in ("numeric_clash", "boolean_clash") for w in coh):
        return True
    if looks_like_conflict(f_new.proposition or "", f_old.proposition or ""):
        return True
    try:
        if find_conflicting_pairs([f_new, f_old]):
            return True
    except Exception:  # noqa: BLE001 — detector shape drift must not crash the bench
        pass
    return False


def _lexical_duplicate(f_new: Fact, f_old: Fact) -> bool:
    """LEXICAL near-duplicate (token-Jaccard) — used to show it misses paraphrase."""
    return any(w.kind == "near_duplicate"
               for w in check_against_siblings(f_new, [f_old]))


def run(judge: Any, *, min_cosine: float = 0.7) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for a, b, case in PAIRS:
        f_new = Fact(id="n", proposition=b, topic="t")
        f_old = Fact(id="o", proposition=a, topic="t")
        warns = detect_semantic_conflicts(
            f_new, [f_old], judge, min_cosine=min_cosine)
        sem_kind = warns[0].kind if warns else "none"
        rows.append({
            "case": case,
            "cosine": round(_cosine(f_new, f_old), 3),
            "lexical_conflict": _lexical_conflict(f_new, f_old),
            "lexical_duplicate": _lexical_duplicate(f_new, f_old),
            "semantic_kind": sem_kind,
        })

    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_case[r["case"]].append(r)

    def _rate(rows_: list[dict[str, Any]], pred) -> float:  # noqa: ANN001
        return round(sum(1 for r in rows_ if pred(r)) / len(rows_), 3) if rows_ else 0.0

    summary = {}
    for case, rs in sorted(by_case.items()):
        summary[case] = {
            "n": len(rs),
            "mean_cosine": round(sum(r["cosine"] for r in rs) / len(rs), 3),
            "lexical_conflict_rate": _rate(rs, lambda r: r["lexical_conflict"]),
            "semantic_conflict_rate": _rate(rs, lambda r: r["semantic_kind"] == "semantic_conflict"),
            "semantic_duplicate_rate": _rate(rs, lambda r: r["semantic_kind"] == "semantic_duplicate"),
            "lexical_duplicate_rate": _rate(rs, lambda r: r["lexical_duplicate"]),
        }
    return {"min_cosine": min_cosine, "per_case": summary, "rows": rows}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Lexical-vs-semantic conflict bench.")
    p.add_argument("--model", type=str, default="claude-sonnet-4-6")
    p.add_argument("--min-cosine", type=float, default=0.7)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    from benchmark.qa_runner import LeanClaudeCLILLM
    from verimem.semantic_conflict import LLMRelationJudge

    judge = LLMRelationJudge(LeanClaudeCLILLM(model=args.model, timeout_s=60))
    res = run(judge, min_cosine=args.min_cosine)
    res["judge"] = f"claude-cli ({args.model}); NLI"
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    a = res["per_case"].get("A", {})
    print(f"\nKEY — case A (semantic conflict): lexical caught "
          f"{a.get('lexical_conflict_rate')}, semantic caught "
          f"{a.get('semantic_conflict_rate')} (n={a.get('n')})")
    if args.out:
        args.out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["PAIRS", "run", "main"]
