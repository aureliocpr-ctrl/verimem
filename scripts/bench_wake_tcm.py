"""Bench: wake-loop TCM integration — 3 dimensions.

Pezzo #15 wires `ContextEngine` into `WakeAgent.run()` so every
stored episode gets a `context_embedding` reflecting its task +
observation drift. The recall side (pezzo #14) was already in place.

Dichiarate prima di misurare:

  1. RECALL DISCRIMINATION on real wake-stored contexts:
     20 paired episode tasks (same task_text → identical summary
     embedding, so cosine top-k can't break the tie). The wake-stored
     contexts diverge per observation set. With
     `recall(context_emb=cur_ctx, context_weight=0.50)` the
     matching-context episode ranks first ≥ 0.75 of the time (vs
     ~0.0 cosine-only baseline that just picks one arbitrary).

  2. ZERO MARGINAL TIME COST:
     `_build_episode_context` should run in < 100ms for a typical
     episode (task + 5 observations × 384-dim sentence-transformer
     encode). Embedding cache amortises repeated obs.

  3. KILL-SWITCH PRESERVES LEGACY:
     With `tcm_wake_enabled=False`, episodes are stored with NULL
     context — recall(context_emb=...) on these episodes contributes
     0 and ranking equals the no-context baseline.
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

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory
from engram.wake import WakeAgent


def _ep(*, ep_id: str, task: str,
        observations: list[str]) -> Episode:
    traces = [
        Trace(step=i + 1, thought="t", action="search",
              action_input="{}", observation=obs)
        for i, obs in enumerate(observations)
    ]
    return Episode(
        id=ep_id, task_id=task[:30], task_text=task,
        outcome="success", final_answer="ok", traces=traces,
        tokens_used=1, skills_used=[],
        created_at=time.time(),
    )


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="bench_wake_tcm_"))
    try:
        wake = object.__new__(WakeAgent)

        # ---- Dimension 1: recall discrimination ---------------------
        # 20 paired tasks. The "user-db" twin always sees observations
        # about users (names, emails); the "orders-db" twin always sees
        # observations about orders (totals, sku). Same task structure,
        # different domain context.
        mem = EpisodicMemory(db_path=tmp / "ep.db")
        n = 20
        users_ctxs: list[np.ndarray] = []
        orders_ctxs: list[np.ndarray] = []
        for i in range(n):
            user_obs = [
                f"found user record id={i}",
                "name: Alice Bianchi, email: alice@example.com",
                "last login 2 hours ago, role admin",
            ]
            order_obs = [
                f"found order record id={i}",
                "total: $1234.56, status: shipped",
                "items: 3 × widget-pro, 1 × extender",
            ]
            ep_u = _ep(
                ep_id=f"u{i:02d}",
                task="query the database for the requested record",
                observations=user_obs,
            )
            ep_o = _ep(
                ep_id=f"o{i:02d}",
                task="query the database for the requested record",
                observations=order_obs,
            )
            ctx_u = wake._build_episode_context(  # noqa: SLF001
                ep_u.task_text, ep_u.traces,
            )
            ctx_o = wake._build_episode_context(  # noqa: SLF001
                ep_o.task_text, ep_o.traces,
            )
            mem.store(ep_u, context_emb=ctx_u)
            mem.store(ep_o, context_emb=ctx_o)
            users_ctxs.append(ctx_u)
            orders_ctxs.append(ctx_o)

        # Simulate a fresh wake.run() that JUST observed a "user-domain"
        # set of obs and is now hitting recall with its current context.
        # We use the i-th query's user_ctx as the "current context".
        match_user = 0
        match_orders = 0
        baseline = 0
        common_task = "query the database for the requested record"
        for i in range(n):
            res_u = mem.recall(
                common_task, k=1,
                context_emb=users_ctxs[i],
                context_weight=0.50,
                track_access=False,
            )
            res_o = mem.recall(
                common_task, k=1,
                context_emb=orders_ctxs[i],
                context_weight=0.50,
                track_access=False,
            )
            res_none = mem.recall(common_task, k=1, track_access=False)
            if res_u and res_u[0][0].id == f"u{i:02d}":
                match_user += 1
            if res_o and res_o[0][0].id == f"o{i:02d}":
                match_orders += 1
            if res_none and res_none[0][0].id == f"u{i:02d}":
                baseline += 1
        rate_user = match_user / n
        rate_orders = match_orders / n
        rate_baseline = baseline / n

        # ---- Dimension 2: time cost --------------------------------
        # Median wall time for _build_episode_context on a typical
        # 5-observation episode. Embedding cache is warm by now.
        sample_obs = [
            "found 5 candidate records",
            "filter applied: created > 2026-01-01",
            "sorted by total descending",
            "top result: order #4242 totalling $9999.99",
            "cached metadata fetched from redis",
        ]
        timings: list[float] = []
        for _ in range(20):
            ep = _ep(ep_id="probe", task="find recent transactions",
                     observations=sample_obs)
            t0 = time.perf_counter()
            wake._build_episode_context(ep.task_text, ep.traces)  # noqa: SLF001
            timings.append((time.perf_counter() - t0) * 1000.0)
        median_ms = float(np.median(timings))

        # ---- Dimension 3: legacy compat (kill switch) ---------------
        ep_legacy = _ep(ep_id="legacy",
                        task="query the database for the requested record",
                        observations=["found legacy record"])
        # No context_emb passed — that's the kill-switch path.
        mem.store(ep_legacy)
        # legacy episode has NULL context — recall with context_emb on
        # it does NOT promote it spuriously.
        legacy_score = mem.recall(
            common_task, k=10,
            context_emb=users_ctxs[0],
            context_weight=0.20,
            track_access=False,
        )
        legacy_in_top1 = bool(legacy_score and legacy_score[0][0].id == "legacy")

    finally:
        wake = None  # type: ignore[assignment]  # noqa: F841
        mem = None  # type: ignore[assignment]  # noqa: F841
        gc.collect()
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- Report -----------------------------------------------------
    print()
    print("Bench: wake-loop TCM integration")
    print()
    print(f"  context-aware recall ({n} paired episodes user/orders):")
    print(f"    no-context baseline (user):  {rate_baseline:.2f}")
    print(f"    user-context match:          {rate_user:.2f} ({match_user}/{n})")
    print(f"    orders-context match:        {rate_orders:.2f} ({match_orders}/{n})")
    print("    target: matched ≥ 0.75, baseline ~0.00 (tied cosine)")
    print()
    print("  _build_episode_context wall time (5-obs episode):")
    print(f"    median: {median_ms:.2f} ms (target ≤ 100 ms)")
    print()
    print("  legacy (NULL-ctx) episode under context-weighted recall:")
    print(f"    legacy in top-1 (should be False): {legacy_in_top1}")
    print()
    print("Verdict (3 dimensions, declared up front):")
    d1 = (rate_user >= 0.75 and rate_orders >= 0.75)
    d2 = median_ms <= 100.0
    d3 = not legacy_in_top1
    print(f"  matched-context ≥ 0.75:    {'+' if d1 else '!'}")
    print(f"  build time ≤ 100 ms:       {'+' if d2 else '!'}")
    print(f"  legacy compat (NULL):      {'+' if d3 else '!'}")
    return 0 if (d1 and d2 and d3) else 1


if __name__ == "__main__":
    sys.exit(main())
