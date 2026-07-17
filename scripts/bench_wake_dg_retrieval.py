"""Bench: wake DG retrieval — 3 dimensions.

Pezzo #16 wires `wake_recall_use_dg` flag into `_retrieve_episodes`.

Dichiarate prima di misurare:

  1. WIRING DELIVERS DIFFERENT ORDERING: with a near-twin corpus
     (5 clusters × 5 variants) and a query identical to one theme,
     the DG path returns a DIFFERENT top-5 ordering than the cosine
     path. This proves the flag is propagated and the DG ranking is
     active (otherwise the flag is a no-op).

  2. TOP-1 RELEVANCE PRESERVED: the top-1 result is still on-cluster
     for both flag positions. (DG must not break basic relevance.)

  3. ZERO LATENCY REGRESSION: median wake retrieval time with DG on
     ≤ 2× legacy path (DG triggers a one-shot back-fill on cold DB
     plus a cosine + DG matrix mul; the index is cached after).
"""
from __future__ import annotations

import gc
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.config import CONFIG
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.wake import WakeAgent, WakeConfig


def _ep(*, ep_id: str, text: str) -> Episode:
    return Episode(
        id=ep_id, task_id=text[:30], task_text=text,
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="A",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=time.time(),
    )


def _build_wake(memory):
    wake = object.__new__(WakeAgent)
    wake.memory = memory  # type: ignore[misc]
    wake.cfg = WakeConfig(
        max_steps=4, self_critique=False, episodes_recall_k=5,
    )
    return wake


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="bench_wake_dg_"))
    try:
        mem = EpisodicMemory(db_path=tmp / "ep.db")
        themes = [
            ("deploy service to production", "dep"),
            ("compute monthly sales report", "rep"),
            ("scrape news headlines", "scr"),
            ("validate signup form", "val"),
            ("refactor auth middleware", "ref"),
        ]
        cluster_of: dict[str, str] = {}
        for theme, prefix in themes:
            for v in range(5):
                ep_id = f"{prefix}-{v}"
                mem.store(_ep(ep_id=ep_id, text=f"{theme} variant {v}"))
                cluster_of[ep_id] = prefix

        wake = _build_wake(mem)
        query = "deploy service to production"

        # ---- Dimension 1+2: cluster coverage + top-1 relevance ----
        saved = CONFIG.wake_recall_use_dg
        try:
            object.__setattr__(CONFIG, "wake_recall_use_dg", False)
            base = wake._retrieve_episodes(query)  # noqa: SLF001
            base_ids = [ep.id for ep, _ in base if ep.outcome == "success"]
            base_clusters = {cluster_of[i] for i in base_ids}

            object.__setattr__(CONFIG, "wake_recall_use_dg", True)
            dg = wake._retrieve_episodes(query)  # noqa: SLF001
            dg_ids = [ep.id for ep, _ in dg if ep.outcome == "success"]
            dg_clusters = {cluster_of[i] for i in dg_ids}
        finally:
            object.__setattr__(CONFIG, "wake_recall_use_dg", saved)

        top1_base_in_cluster = bool(base_ids) and base_ids[0].startswith("dep")
        top1_dg_in_cluster = bool(dg_ids) and dg_ids[0].startswith("dep")

        # ---- Dimension 3: latency ---------------------------------
        # Median over 10 runs. The first DG call back-fills + builds
        # the matrix; subsequent calls hit the cache.
        timings_base: list[float] = []
        timings_dg: list[float] = []
        for _ in range(10):
            object.__setattr__(CONFIG, "wake_recall_use_dg", False)
            t0 = time.perf_counter()
            wake._retrieve_episodes(query)  # noqa: SLF001
            timings_base.append((time.perf_counter() - t0) * 1000.0)
            object.__setattr__(CONFIG, "wake_recall_use_dg", True)
            t0 = time.perf_counter()
            wake._retrieve_episodes(query)  # noqa: SLF001
            timings_dg.append((time.perf_counter() - t0) * 1000.0)
        object.__setattr__(CONFIG, "wake_recall_use_dg", saved)
        med_base = float(np.median(timings_base))
        med_dg = float(np.median(timings_dg))
        latency_ratio = med_dg / max(1e-9, med_base)
    finally:
        wake = None  # type: ignore[assignment]  # noqa: F841
        mem = None  # type: ignore[assignment]  # noqa: F841
        gc.collect()
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- Report -----------------------------------------------------
    different_ordering = base_ids != dg_ids
    print()
    print("Bench: wake DG retrieval (5×5 near-twin corpus)")
    print()
    print("  ordering (top-5 success ids):")
    print(f"    baseline: {base_ids}")
    print(f"    DG:       {dg_ids}")
    print(f"    different: {different_ordering}")
    print()
    print("  cluster coverage (intra-deploy ordering matters more here):")
    print(f"    baseline: {sorted(base_clusters)}")
    print(f"    DG:       {sorted(dg_clusters)}")
    print()
    print("  top-1 in 'deploy' cluster:")
    print(f"    baseline: {top1_base_in_cluster}")
    print(f"    DG:       {top1_dg_in_cluster}")
    print()
    print("  latency (median over 10 runs, k=5):")
    print(f"    baseline: {med_base:.2f} ms")
    print(f"    DG:       {med_dg:.2f} ms")
    print(f"    ratio:    {latency_ratio:.2f}× (target ≤ 2.0×)")
    print()
    print("Verdict (3 dimensions, declared up front):")
    d1 = different_ordering
    d2 = top1_base_in_cluster and top1_dg_in_cluster
    d3 = latency_ratio <= 2.0
    print(f"  DG ordering ≠ baseline:    {'+' if d1 else '!'}")
    print(f"  top-1 relevance preserved: {'+' if d2 else '!'}")
    print(f"  latency ≤ 2× baseline:     {'+' if d3 else '!'}")
    return 0 if (d1 and d2 and d3) else 1


if __name__ == "__main__":
    sys.exit(main())
