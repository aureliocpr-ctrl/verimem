"""TRUST-CORE block B — read-path on EXTERNAL data (HaluEval QA, MIT).

Measures hallucination-on-recall sub-mode (a) miss→fabrication from
benchmark/TRUST_CORE.md §2 with NO LLM: the store's contents are the ground
truth, so "supported" is id-decidable, not judged.

Protocol
  * one CROWDED store per run: every sampled item's `knowledge` is ingested
    (never a single-fact store — discrimination is the point);
  * answerable: the item's own `question` → hit iff the item's OWN fact id
    reaches top-k; `explain(min_relevance=τ)` gives the abstention face;
  * unanswerable: questions of items whose knowledge was NEVER ingested →
    the only supported behaviour is abstention; answering = false_answer;
  * a knowledge blocked at ingest counts as a retrieval MISS (the read-path
    lost it) and is reported as write-path FP pressure on external data.

Held-out discipline: `--make-samples` cuts three DISJOINT deterministic
splits (dev / heldout / unanswerable-probe). Development looks at dev only;
heldout is run, not read.

Usage
  python -m benchmark.external_readpath --make-samples
  python -m benchmark.external_readpath --split dev --n 100 --k 5 --tau 0.35
  python -m benchmark.external_readpath --split dev --n 100 --sweep
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any

from engram.client import Memory

DATA_DIR = Path(__file__).parent / "data" / "external"
CACHE_SRC = DATA_DIR / ".cache" / "qa_data.json"
RESULTS_DIR = Path(__file__).parent / "results"

SOURCE_REF = "source-doc:halueval-qa"
TOPIC = "external/halueval-qa"


# ---- sampling ----------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_samples(src: Path, out_dir: Path, *, n_dev: int = 100,
                 n_heldout: int = 200, n_unans: int = 100,
                 seed: int = 42, prefix: str = "halueval_qa") -> dict[str, Any]:
    """Cut three disjoint deterministic splits from the raw JSONL dump. ``prefix``
    names the corpus (files ``{prefix}_{split}.jsonl``) so a second corpus reuses
    the identical held-out discipline."""
    rows = [json.loads(line) for line in
            Path(src).read_text(encoding="utf-8").splitlines() if line.strip()]
    rng = random.Random(seed)
    idx = list(range(len(rows)))
    rng.shuffle(idx)

    cuts = {}
    pos = 0
    for name, want in (("dev", n_dev), ("heldout", n_heldout),
                       ("unanswerable", n_unans)):
        take = idx[pos:pos + want]
        pos += len(take)
        cuts[name] = [rows[i] for i in take]

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, items in cuts.items():
        path = out_dir / f"{prefix}_{name}.jsonl"
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False)
                                  for r in items) + "\n", encoding="utf-8")
    return {"prefix": prefix, "n_dev": len(cuts["dev"]),
            "n_heldout": len(cuts["heldout"]),
            "n_unanswerable": len(cuts["unanswerable"]),
            "seed": seed, "source_sha256": _sha256(Path(src))}


def load_split(name: str, limit: int | None = None, *,
               prefix: str = "halueval_qa") -> list[dict[str, Any]]:
    path = DATA_DIR / f"{prefix}_{name}.jsonl"
    rows = [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows[:limit] if limit else rows


# ---- store build ---------------------------------------------------------------

def build_store(items: list[dict], db_path: Path,
                ) -> tuple[Memory, list[str | None], dict[str, Any]]:
    """Ingest every item's knowledge into ONE crowded store.

    Returns (memory, fact_ids aligned to items — None where the gate blocked
    the write, ingest stats). External knowledge carries its source ref; a
    quarantined ingest is a write-path FP on external data and is COUNTED,
    not silently retried.
    """
    mem = Memory(db_path)
    fact_ids: list[str | None] = []
    by_status: dict[str, int] = {}
    for i, item in enumerate(items):
        res = mem.add(item["knowledge"], topic=TOPIC,
                      verified_by=[f"{SOURCE_REF}:{i}"])
        status = res.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        blocked = (not res.get("stored")) or status == "quarantined"
        fact_ids.append(None if blocked else res.get("id"))
    n_blocked = sum(1 for f in fact_ids if f is None)
    return mem, fact_ids, {"admitted": len(items) - n_blocked,
                           "blocked": n_blocked, "by_status": by_status}


# ---- evaluation ----------------------------------------------------------------

def eval_answerable(mem: Memory, items: list[dict],
                    fact_ids: list[str | None], *, k: int,
                    tau: float) -> list[dict[str, Any]]:
    """One row per item. hit = the item's own fact id in top-k (id-decidable).
    A blocked ingest is an honest miss. `abstained` is the product face at τ —
    abstaining on an answerable question is over-abstention, the cost of τ."""
    rows = []
    for item, fid in zip(items, fact_ids):
        if fid is None:
            rows.append({"retrieval_hit": False, "abstained": True,
                         "blocked": True})
            continue
        hits = mem.search(item["question"], k=k)
        rows.append({"retrieval_hit": any(h.get("id") == fid for h in hits),
                     "abstained": _abstains(hits, tau),
                     "blocked": False})
    return rows


def _abstains(hits: list[dict[str, Any]], tau: float) -> bool:
    """The relevance-floor decision derived from ONE retrieval pass.

    Same semantics as ``explain(min_relevance=τ)`` — abstain iff nothing
    scores at/above the floor — without re-running retrieval (and its CE
    rerank) once per τ. Pinned to the product path by
    ``test_abstains_matches_explain`` so a semantics change there breaks HERE,
    not silently in a benchmark number."""
    return (not hits) or max(h.get("score", 0.0) for h in hits) < tau


def eval_unanswerable(mem: Memory, questions: list[str], *, k: int,
                      tau: float) -> list[dict[str, Any]]:
    """Support is absent by construction — abstention is the only honest
    output; anything else is sub-mode (a) fabrication pressure."""
    return [{"abstained": _abstains(mem.search(q, k=k), tau)}
            for q in questions]


def eval_raw(mem: Memory, items: list[dict], fact_ids: list[str | None],
             unanswerable_questions: list[str], *, k: int):
    """Search ONCE per probe and record (retrieval_hit, top_score, has_hits) — so
    ANY abstention floor τ can be applied post-hoc (a τ sweep without re-running
    retrieval). Mirrors what the mem0 adapter does, so verimem's own floor can be
    calibrated the same way, on the same footing. Returns (answerable, unanswerable)."""
    ans = []
    for item, fid in zip(items, fact_ids):
        if fid is None:
            ans.append({"retrieval_hit": False, "top_score": 0.0,
                        "has_hits": False})
            continue
        hits = mem.search(item["question"], k=k)
        ans.append({
            "retrieval_hit": any(h.get("id") == fid for h in hits),
            "top_score": max((h.get("score", 0.0) for h in hits), default=0.0),
            "has_hits": bool(hits)})
    unans = []
    for q in unanswerable_questions:
        hits = mem.search(q, k=k)
        unans.append({"top_score": max((h.get("score", 0.0) for h in hits),
                                        default=0.0), "has_hits": bool(hits)})
    return ans, unans


def run_readpath(items: list[dict], unanswerable_questions: list[str],
                 db_path: Path, *, k: int = 5,
                 tau: float = 0.35) -> dict[str, Any]:
    mem, fact_ids, ingest = build_store(items, db_path)
    ans = eval_answerable(mem, items, fact_ids, k=k, tau=tau)
    unans = eval_unanswerable(mem, unanswerable_questions, k=k, tau=tau)

    n_a, n_u = len(ans), len(unans)
    abst = (sum(r["abstained"] for r in unans) / n_u) if n_u else 0.0
    return {
        "n_answerable": n_a,
        "n_unanswerable": n_u,
        "retrieval_hit_rate": round(
            sum(r["retrieval_hit"] for r in ans) / n_a, 4) if n_a else 0.0,
        "over_abstention_rate": round(
            sum(r["abstained"] for r in ans) / n_a, 4) if n_a else 0.0,
        "abstention_rate": round(abst, 4),
        "false_answer_rate": round(1.0 - abst, 4) if n_u else 0.0,
        "ingest": ingest, "k": k, "tau": tau,
    }


# ---- CLI -----------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--make-samples", action="store_true")
    ap.add_argument("--split", default="dev", choices=["dev", "heldout"])
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--tau", type=float, default=0.35)
    ap.add_argument("--sweep", action="store_true",
                    help="sweep tau over 0.25..0.55 on ONE store build")
    args = ap.parse_args()

    if args.make_samples:
        info = make_samples(CACHE_SRC, DATA_DIR)
        print(json.dumps(info, indent=2))
        return

    items = load_split(args.split, args.n)
    probes = [r["question"] for r in load_split("unanswerable", args.n // 2)]

    import tempfile
    taus = ([0.25, 0.35, 0.45, 0.55, 0.65, 0.70, 0.75, 0.80, 0.85,
             0.90, 0.95] if args.sweep else [args.tau])
    # ignore_cleanup_errors: on Windows the store keeps entity_kg.db open and
    # the tempdir unlink would otherwise crash AFTER the work, eating the run.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        mem, fact_ids, ingest = build_store(items, Path(td) / "rp.db")
        # ONE retrieval pass per query (search+rerank are τ-independent);
        # every τ point and the separability AUROC derive from these scores.
        ans_rows = []
        for item, fid in zip(items, fact_ids):
            if fid is None:
                ans_rows.append({"hit": False, "max_score": None})
                continue
            hits = mem.search(item["question"], k=args.k)
            ans_rows.append({
                "hit": any(h.get("id") == fid for h in hits),
                "max_score": max((h.get("score", 0.0) for h in hits),
                                 default=0.0)})
        unans_scores = [
            max((h.get("score", 0.0) for h in mem.search(q, k=args.k)),
                default=0.0) for q in probes]

    from benchmark.external_grounding import auroc
    ans_scores = [r["max_score"] for r in ans_rows
                  if r["max_score"] is not None]
    separability = auroc(ans_scores, unans_scores)

    curves = []
    hit_rate = round(sum(r["hit"] for r in ans_rows) / len(ans_rows), 4)
    for tau in taus:
        abstain_a = sum(1 for r in ans_rows
                        if r["max_score"] is None or r["max_score"] < tau)
        abstain_u = sum(1 for s in unans_scores if s < tau)
        point = {
            "tau": tau,
            "retrieval_hit_rate": hit_rate,
            "over_abstention_rate": round(abstain_a / len(ans_rows), 4),
            "abstention_rate": round(abstain_u / len(unans_scores), 4),
            "false_answer_rate": round(1 - abstain_u / len(unans_scores), 4),
        }
        curves.append(point)
        print(json.dumps(point))

    report = {
        "dataset": "HaluEval qa_data (MIT)", "split": args.split,
        "n_answerable": len(items), "n_unanswerable": len(probes),
        "k": args.k, "ingest": ingest, "curve": curves,
        "separability_auroc": separability,
        "score_stats": {
            "answerable": {"min": min(ans_scores), "max": max(ans_scores)},
            "unanswerable": {"min": min(unans_scores),
                             "max": max(unans_scores)},
        },
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    print(json.dumps({"separability_auroc": separability,
                      "score_stats": report["score_stats"]}))
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / (f"external_readpath_halueval_{args.split}"
                         f"_{time.strftime('%Y-%m-%d')}.json")
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
