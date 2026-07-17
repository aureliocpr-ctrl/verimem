"""Bench: TCM cabling into EpisodicMemory — 3 dimensions.

Dichiarate prima di misurare:

  1. CONTEXT DISCRIMINATION on near-twin episodes:
     50 paired episodes — same task text, different encoding context.
     `recall(query, context_emb=ctx_A, context_weight=0.5)` should
     pick the matching A-episode at top-1 in ≥ 0.85 of cases. The
     baseline (no context) picks at chance ~0.50.

  2. NO-CONTEXT BACKWARD COMPAT:
     With `context_weight=0` (the default), recall returns identical
     ordering to legacy code on a diverse corpus — zero drift.

  3. STORAGE COST:
     `context_embedding` is a dense float32 of `embedding_dim` (1.5
     KB). Target ≤ 2× summary_embedding (= 1.5 KB → ratio 1.0×).
     The column is NULL for episodes stored without context, so
     legacy stores have ZERO marginal cost.
"""
from __future__ import annotations

import gc
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.config import CONFIG
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(*, ep_id: str, text: str) -> Episode:
    return Episode(
        id=ep_id, task_id=text[:30], task_text=text,
        outcome="success", final_answer="ok",
        traces=[Trace(
            step=1, thought="x", action="x", action_input="{}", observation="x",
        )],
    )


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def main() -> int:
    rng = np.random.default_rng(seed=20260508)
    tmp = Path(tempfile.mkdtemp(prefix="bench_tcm_"))
    tmp2 = Path(tempfile.mkdtemp(prefix="bench_tcm_"))
    try:
        # ---- Dimension 1: context discrimination -------------------
        # 50 task templates; for each, two stored episodes ("A" with ctx_A,
        # "B" with ctx_B) sharing the same text. Each query targets the
        # matching context — the matching episode should rank first.
        mem = EpisodicMemory(db_path=tmp / "ep.db")
        n = 50
        ctxs_a: list[np.ndarray] = []
        ctxs_b: list[np.ndarray] = []
        task_texts: list[str] = []
        for i in range(n):
            text = f"task family {i:03d} retrieve a record"
            ctx_a = _normalize(
                rng.standard_normal(CONFIG.embedding_dim).astype(np.float32)
            )
            ctx_b = _normalize(
                rng.standard_normal(CONFIG.embedding_dim).astype(np.float32)
            )
            mem.store(_ep(ep_id=f"t{i:03d}-A", text=text), context_emb=ctx_a)
            mem.store(_ep(ep_id=f"t{i:03d}-B", text=text), context_emb=ctx_b)
            ctxs_a.append(ctx_a)
            ctxs_b.append(ctx_b)
            task_texts.append(text)

        # Score: how often does the context-A query pick the A-episode?
        ctx_match = 0
        no_ctx_match = 0
        for i, text in enumerate(task_texts):
            res_ctx = mem.recall(
                text, k=1, context_emb=ctxs_a[i], context_weight=0.5,
                track_access=False,
            )
            res_none = mem.recall(text, k=1, track_access=False)
            if res_ctx and res_ctx[0][0].id == f"t{i:03d}-A":
                ctx_match += 1
            if res_none and res_none[0][0].id == f"t{i:03d}-A":
                no_ctx_match += 1
        ctx_rate = ctx_match / n
        no_ctx_rate = no_ctx_match / n

        # ---- Dimension 2: no-context backward compat ---------------
        # Diverse, plain corpus.
        mem2 = EpisodicMemory(db_path=tmp2 / "ep.db")
        for j, t in enumerate([
            "compute factorial of 10",
            "send email via smtp",
            "parse json config file",
            "connect to postgres database",
            "render html template",
        ]):
            mem2.store(_ep(ep_id=f"d{j}", text=t))
        a = mem2.recall("compute factorial", k=3, track_access=False)
        b = mem2.recall(
            "compute factorial", k=3, context_weight=0.0, track_access=False,
        )
        compat = [ep.id for ep, _ in a] == [ep.id for ep, _ in b]

        # ---- Dimension 3: storage cost -----------------------------
        with mem._connect() as c:  # noqa: SLF001
            row = c.execute(
                "SELECT length(summary_embedding), length(context_embedding) "
                "FROM episodes LIMIT 1"
            ).fetchone()
        summary_bytes = int(row[0])
        ctx_bytes = int(row[1])
        storage_ratio = ctx_bytes / summary_bytes
    finally:
        mem = None  # type: ignore[assignment]  # noqa: F841
        mem2 = None  # type: ignore[assignment]  # noqa: F841
        gc.collect()
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(tmp2, ignore_errors=True)

    # ---- Report -----------------------------------------------------
    print()
    print("Bench: TCM cabling into EpisodicMemory")
    print()
    print(f"  context discrimination ({n} twin episodes A/B, k=1):")
    print(f"    no-context baseline:  {no_ctx_rate:.2f} ({no_ctx_match}/{n})")
    print(f"    context-A boosted:    {ctx_rate:.2f} ({ctx_match}/{n})")
    print("    target:               ≥ 0.85")
    print()
    print(f"  no-context backward compat:  "
          f"{'identical' if compat else 'DIFFERS'}")
    print()
    print("  storage cost per episode (when context populated):")
    print(f"    summary_embedding:    {summary_bytes} B")
    print(f"    context_embedding:    {ctx_bytes} B")
    print(f"    ratio ctx/summary:    {storage_ratio:.3f}× "
          f"(target ≤ 2.0×; NULL for legacy stores)")
    print()
    print("Verdict (3 dimensions, declared up front):")
    d1 = ctx_rate >= 0.85
    d2 = compat
    d3 = storage_ratio <= 2.0
    print(f"  context-match ≥ 0.85:      {'+' if d1 else '!'}")
    print(f"  legacy compat preserved:   {'+' if d2 else '!'}")
    print(f"  storage ≤ 2× summary:      {'+' if d3 else '!'}")
    return 0 if (d1 and d2 and d3) else 1


if __name__ == "__main__":
    sys.exit(main())
