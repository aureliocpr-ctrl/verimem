"""QuALITY long-document retrieval — F1 virgin corpus #3 (task #22, scenario S2).

The "whole documents" case Aurelio asked about. Corpus: QuALITY
(emozilla/quality, validation) — 115 long articles (median ~27k chars, ALL
> the e5 512-token window) with 2086 reading-comprehension questions. Never
used in Verimem development.

This harness PROVES the S2 fix on real data by comparing two ingest modes over
the SAME haystack of all 115 articles in one shared store (a realistic
multi-document memory, not a hermetic per-question store):

  - ``whole``   : one Fact per article — e5 truncates at ~512 tok, so the
                  embedding only sees the article's head (~7%). This is the
                  silent-truncation fall S2 names.
  - ``chunked`` : each article -> ``chunk_text`` (1000ch / 150 overlap,
                  provenance-anchored) -> one Fact per chunk. The whole
                  article becomes retrievable.

Judge-free, subscription-safe: gold = the SOURCE ARTICLE the question was
written for (objective — QuALITY ships the mapping). Metric = hit@k / MRR of
the gold article's id among the top-k retrieved sources. Declared limit: this
is ARTICLE-level retrieval (which document), not passage-level (which
paragraph) — QuALITY has no gold evidence span, and passage correctness needs
an LLM judge we deliberately do not call. Even so, whole-vs-chunked isolates
whether truncation loses the deep-content questions.

Provenance: articles are ingested source content -> writer_role=external_content
(task #25 gate_router). Never touches ~/.verimem.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

from benchmark.longmemeval_runner import _unique_preserve, hit_at_k, mrr
from verimem.chunking import chunk_text
from verimem.config import CONFIG
from verimem.semantic import Fact, SemanticMemory

_DEFAULT_DATA = Path(
    "benchmark/data/external/.cache/quality/"
    "data/validation-00000-of-00001-77baeb9538209706.parquet")


def load_quality(path: Path | str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Return ({article_id: text}, [{article_id, question}]). article_id is a
    stable hash of the article text (same article across its questions)."""
    import pandas as pd
    df = pd.read_parquet(path)
    articles: dict[str, str] = {}
    questions: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        art = str(r["article"])
        aid = f"a{abs(hash(art)) % (10**12)}"
        articles.setdefault(aid, art)
        questions.append({"article_id": aid, "question": str(r["question"])})
    return articles, questions


def build_store(articles: dict[str, str], mode: str, *, db_path: Path,
                chunk_size: int = 1000, overlap: int = 150) -> tuple[SemanticMemory, int]:
    """One shared store over ALL articles. ``whole`` = 1 fact/article (truncated
    by the embedder); ``chunked`` = 1 fact/chunk (whole article retrievable)."""
    sm = SemanticMemory(db_path=db_path)
    n_facts = 0
    for aid, text in articles.items():
        if mode == "whole":
            pieces = [text]
        elif mode == "chunked":
            pieces = [c.text for c in chunk_text(
                text, chunk_size=chunk_size, overlap=overlap)]
        else:
            raise ValueError(f"mode must be whole|chunked, got {mode!r}")
        for i, piece in enumerate(pieces):
            if not piece.strip():
                continue
            sm.store(Fact(proposition=piece, topic=f"quality/{aid}",
                          source_episodes=[aid],  # gold = source article id
                          writer_role="external_content"), embed="sync")
            n_facts += 1
    return sm, n_facts


def run(dataset_path: Path | str = _DEFAULT_DATA, *, mode: str = "chunked",
        ks: list[int] | None = None, sample: int | None = None,
        seed: int = 42, workdir: Path | str | None = None,
        chunk_size: int = 1000) -> dict[str, Any]:
    ks = sorted(set(ks or [1, 3, 5, 10]))
    articles, questions = load_quality(dataset_path)
    if sample is not None and sample < len(questions):
        import random
        questions = random.Random(seed).sample(questions, sample)

    import shutil
    import tempfile
    owns = workdir is None
    workdir = Path(workdir) if workdir else Path(
        tempfile.mkdtemp(prefix="quality_f1_"))
    db = Path(workdir) / f"quality_{mode}.db"
    per_q: list[dict[str, Any]] = []
    try:
        sm, n_facts = build_store(articles, mode, db_path=db,
                                  chunk_size=chunk_size)
        k_max = max(ks)
        for q in questions:
            gold = [q["article_id"]]
            t0 = time.perf_counter()
            hits = sm.recall(q["question"], k=k_max)
            lat = (time.perf_counter() - t0) * 1000.0
            retrieved = _unique_preserve(
                [f.source_episodes[0] if f.source_episodes else ""
                 for f, *_ in hits])
            per_q.append({
                "per_k": {k: {"hit": hit_at_k(retrieved, gold, k),
                              "mrr": mrr(retrieved, gold)} for k in ks},
                "latency_ms": round(lat, 2),
            })
    finally:
        if owns:
            shutil.rmtree(workdir, ignore_errors=True)

    def _mean(xs):
        xs = [x for x in xs if x is not None]
        return round(statistics.fmean(xs), 4) if xs else 0.0

    overall = {"n": len(per_q)}
    for k in ks:
        overall[f"hit@{k}"] = _mean([r["per_k"][k]["hit"] for r in per_q])
    overall["mrr"] = _mean([r["per_k"][ks[0]]["mrr"] for r in per_q])

    return {
        "dataset": str(dataset_path),
        "corpus": "QuALITY validation (virgin — never used in dev)",
        "mode": mode,
        "ks": ks,
        "n_articles": len(articles),
        "n_facts_stored": n_facts,
        "n_questions": len(per_q),
        "embedding_model": CONFIG.embedding_model,
        "overall": overall,
        "latency_ms_mean": _mean([r["latency_ms"] for r in per_q]),
        "metric_note": (
            "ARTICLE-level retrieval: gold = the source article the question "
            "was written for; hit@k of that article id among top-k sources. "
            "Declared limit: article-level not passage-level (no gold span; "
            "passage correctness needs an LLM judge, not called). whole vs "
            "chunked isolates the S2 silent-truncation fall."),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="QuALITY long-document retrieval (F1 corpus #3, S2 proof).")
    ap.add_argument("--dataset", type=Path, default=_DEFAULT_DATA)
    ap.add_argument("--mode", choices=["whole", "chunked"], default="chunked")
    ap.add_argument("--ks", type=int, nargs="+", default=[1, 3, 5, 10])
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--chunk-size", type=int, default=1000)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    res = run(args.dataset, mode=args.mode, ks=args.ks, sample=args.sample,
              seed=args.seed, chunk_size=args.chunk_size)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(res, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    o = res["overall"]
    print(f"QuALITY F1 [{res['mode']}] | {res['n_articles']} articles -> "
          f"{res['n_facts_stored']} facts | n_q={res['n_questions']} | "
          f"lat={res['latency_ms_mean']:.0f}ms")
    line = "  ".join(f"hit@{k}={o[f'hit@{k}']:.3f}" for k in res["ks"])
    print(f"  {line}  MRR={o['mrr']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
