"""FORGIA pezzo #44 — Recall pipeline ablation study (no LLM calls).

Measures how each forged primitive (DG / Hopfield / salience /
recency / context) affects recall RANKING on a synthetic corpus
of (target, distractor, noise) triples. Cheap (~300 ms, no API spend).

Setup:
  - 8 (target, distractor, paraphrase_query) triples.
  - Targets get a unique context_emb; distractors share head words
    with the target but mean something else (factorial design vs
    factorial computation, etc.).
  - 30 noise episodes (generic Lorem-ipsum tasks).
  - For each query, find the 1-based rank of its target episode in
    `recall(query, k=10)`.

The expected reading is **stability**: every flag combination should
keep top-1 high (no flag should regress baseline). When the corpus
is small enough that pure cosine already separates targets from
distractors, every cell saturates at top-1=1.00 — that's the
floor-effect, not a sign the primitives are useless. The harness
covers the regression-guard role; for the discrimination role you
need a harder corpus (see `scripts/bench_dg_cabling.py` for one).
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.config import CONFIG  # noqa: E402
from verimem.episode import Episode, Trace  # noqa: E402
from verimem.memory import EpisodicMemory  # noqa: E402


@dataclass
class _AblationCell:
    name: str
    flags: dict
    mean_rank: float = -1.0
    top1: float = -1.0
    top3: float = -1.0


def _ep(eid: str, text: str, *, outcome: str = "success") -> Episode:
    return Episode(
        id=eid, task_id=text[:30], task_text=text,
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=time.time(),
    )


def _build_corpus(mem: EpisodicMemory, n_noise: int = 50,
                  rng: np.random.Generator | None = None) -> list[tuple[str, str]]:
    """Store n_noise noise episodes + 8 targets, with distractors per target.

    To make the ablation discriminative, we plant a deliberate
    DISTRACTOR for each target — an episode whose text shares the head
    word but means something different (e.g. "factorial of permutation"
    vs the target "compute factorial of integer n"). Pure cosine
    recall has trouble; DG / context / salience should help.
    """
    rng = rng or np.random.default_rng(seed=0xDA1A)
    # (target_id, target_task_text, paraphrase_query, distractor_text)
    triples = [
        ("t-fact",
         "compute factorial of integer n iteratively",
         "what's the factorial value for a given non-negative integer",
         "factorial design in experiments combinatorial"),
        ("t-email",
         "send email via smtp protocol with authentication",
         "deliver a message through the mail relay using credentials",
         "email regex parsing extract domain part"),
        ("t-json",
         "parse a json configuration from a file path",
         "read structured configuration from a json document on disk",
         "json schema validation of nested objects"),
        ("t-pg",
         "connect to a postgres database with psycopg2 client",
         "open a session against postgresql via dbapi driver",
         "postgres replication slave configuration tutorial"),
        ("t-html",
         "render an html template via jinja2 with context dict",
         "produce an html page from a template engine using variables",
         "html sanitisation strip dangerous tags"),
        ("t-csv",
         "read a csv file with pandas and inspect the columns",
         "load tabular csv data with pandas dataframe inspection",
         "csv injection attack on excel formulas"),
        ("t-img",
         "resize an image with pillow keeping aspect ratio",
         "scale a picture down preserving the proportions via pil",
         "image classification cnn benchmarks"),
        ("t-zip",
         "extract a zip archive into a directory",
         "uncompress a zip file into a target folder",
         "zipf law power distribution natural language"),
    ]
    ctx = [
        rng.standard_normal(CONFIG.embedding_dim).astype(np.float32)
        for _ in triples
    ]
    ctx = [c / np.linalg.norm(c) for c in ctx]
    # Store targets WITH context.
    for (eid, text, _query, _dist), c in zip(triples, ctx, strict=True):
        mem.store(_ep(eid, text), context_emb=c)
    # Store distractors WITHOUT context (so context_emb tie-break helps targets).
    for eid, _text, _q, dist_text in triples:
        mem.store(_ep(f"{eid}-DISTR", dist_text))
    # Noise episodes.
    noise_texts = [
        "process some data",
        "handle a generic request",
        "compute some number quickly",
        "format the output as text",
        "validate the user input",
        "log an event to file",
        "save the result to disk",
        "increment a counter atomically",
        "load some yaml configuration",
        "open a generic file",
    ]
    for i in range(n_noise):
        nid = f"n{i:03d}"
        nt = noise_texts[i % len(noise_texts)] + f" #{i}"
        mem.store(_ep(nid, nt))
    return [(eid, q) for eid, _, q, _ in triples]


def _rank_target(mem: EpisodicMemory, query: str, target_id: str,
                 *, k: int = 10, **flags) -> int:
    """Return 1-based rank of target_id in recall result, or k+1 if absent."""
    result = mem.recall(query, k=k, track_access=False, **flags)
    for i, (ep, _score) in enumerate(result, start=1):
        if ep.id == target_id:
            return i
    return k + 1


def _run_cell(cell: _AblationCell, mem: EpisodicMemory,
              queries: list[tuple[str, str]], k: int = 10) -> _AblationCell:
    ranks = []
    for target_id, q in queries:
        ranks.append(_rank_target(mem, q, target_id, k=k, **cell.flags))
    cell.mean_rank = float(np.mean(ranks))
    cell.top1 = float(np.mean([r == 1 for r in ranks]))
    cell.top3 = float(np.mean([r <= 3 for r in ranks]))
    return cell


def main() -> int:
    # FORGIA #67: honour HIPPO_DATA_DIR so the test can isolate output.
    out_dir = CONFIG.data_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "ablation_corpus.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError as exc:
            # FORGIA #97: if another process holds the DB open (e.g. a
            # dashboard running against the same data dir) we can't
            # unlink. Surface a clear error instead of crashing later
            # at sqlite-level.
            print(
                f"[ablation] cannot unlink {db_path}: {exc}\n"
                "  pass HIPPO_DATA_DIR=/tmp/hippo_ablation to a fresh dir.",
                file=sys.stderr,
            )
            return 2
    mem = EpisodicMemory(db_path=db_path)
    queries = _build_corpus(mem, n_noise=30)

    cells = [
        _AblationCell("baseline_cosine", flags=dict()),
        _AblationCell("dg_only", flags=dict(use_dg=True)),
        _AblationCell("hopfield_only", flags=dict(
            use_hopfield=True, hopfield_beta=8.0,
        )),
        _AblationCell("salience_only", flags=dict(salience_weight=0.30)),
        _AblationCell("recency_only", flags=dict(
            recency_weight=0.30, recency_tau_s=7 * 86400.0,
        )),
        _AblationCell("dg+salience", flags=dict(
            use_dg=True, salience_weight=0.20,
        )),
        _AblationCell("all_on", flags=dict(
            use_dg=True, salience_weight=0.20,
            recency_weight=0.10, recency_tau_s=7 * 86400.0,
        )),
    ]

    t0 = time.perf_counter()
    for c in cells:
        _run_cell(c, mem, queries, k=10)
    elapsed = time.perf_counter() - t0

    print("[ablation] corpus: 8 targets + 30 noise; queries: 8 paraphrases")
    print(f"[ablation] elapsed: {elapsed*1000:.0f} ms")
    print()
    print(f"{'cell':22s} {'mean_rank':>10s} {'top1':>6s} {'top3':>6s}")
    print("-" * 50)
    for c in cells:
        print(f"{c.name:22s} {c.mean_rank:>10.2f} {c.top1:>6.2f} {c.top3:>6.2f}")

    # Persist
    import json
    payload = [{"cell": c.name, **c.flags,
                 "mean_rank": c.mean_rank, "top1": c.top1, "top3": c.top3}
                for c in cells]
    out = out_dir / "bench_recall_ablation.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\n[ablation] wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
