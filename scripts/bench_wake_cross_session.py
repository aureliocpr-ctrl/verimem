"""Bench: wake cross-session ContextEngine — 3 dimensions.

Pezzo #17 wires a long-lived ContextEngine on WakeAgent so that
`_retrieve_episodes` uses the agent's drifting cognitive state as a
TCM cue (Howard & Kahana 2002 list-context dynamics).

Dichiarate prima di misurare:

  1. CROSS-SESSION DISCRIMINATION:
     20 paired episodes (same task_text, distinct stored contexts).
     Pre-drift the wake engine to context A, then call retrieve.
     Top-1 should be the A-stored episode in ≥ 0.85 of cases (vs
     baseline 0.0 in tied-cosine regime). Corpus size kept ≤ k_pool
     (50) so the rerank actually has both A and B in scope.

  2. NO-DRIFT (zero state) PRESERVES LEGACY:
     With engine state at zero (boot), retrieve returns the same
     ordering as the legacy path — no spurious context boost from
     a meaningless zero vector.

  3. ZERO LATENCY REGRESSION:
     The `engine.state` lookup + cosine boost adds < 5ms to the
     median retrieve time. The whole point of TCM is that it's
     CHEAPER than full-corpus rerank — just one extra dot product
     per pool entry.
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
from verimem.context_engine import ContextEngine
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
    wake._context_engine = ContextEngine(  # type: ignore[attr-defined]
        dim=CONFIG.embedding_dim, rho=CONFIG.tcm_rho,
    )
    return wake


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def main() -> int:
    rng = np.random.default_rng(seed=20260508)
    tmp = Path(tempfile.mkdtemp(prefix="bench_wake_xs_"))
    try:
        mem = EpisodicMemory(db_path=tmp / "ep.db")
        n = 20
        ctx_a_list: list[np.ndarray] = []
        common_task = "look up the requested record"
        for i in range(n):
            ctx_a = _normalize(
                rng.standard_normal(CONFIG.embedding_dim).astype(np.float32)
            )
            ctx_b = _normalize(
                rng.standard_normal(CONFIG.embedding_dim).astype(np.float32)
            )
            mem.store(_ep(ep_id=f"a{i:02d}", text=common_task), context_emb=ctx_a)
            mem.store(_ep(ep_id=f"b{i:02d}", text=common_task), context_emb=ctx_b)
            ctx_a_list.append(ctx_a)

        wake = _build_wake(mem)

        # ---- Dimension 1: cross-session discrimination -----------
        saved_xs = CONFIG.tcm_cross_session_enabled
        saved_w = CONFIG.tcm_recall_context_weight
        saved_replay = CONFIG.forward_replay_include_failures
        try:
            object.__setattr__(CONFIG, "tcm_cross_session_enabled", True)
            object.__setattr__(CONFIG, "tcm_recall_context_weight", 0.50)
            object.__setattr__(CONFIG, "forward_replay_include_failures", False)

            match = 0
            for i in range(n):
                # Set the wake engine state directly to ctx_a[i]
                # (simulating that prior runs drifted it that way).
                wake._context_engine._state = ctx_a_list[i].copy()  # noqa: SLF001
                out = wake._retrieve_episodes(common_task)  # noqa: SLF001
                top = out[0][0].id if out else ""
                if top == f"a{i:02d}":
                    match += 1
            rate_drifted = match / n

            # ---- Dimension 2: no-drift = legacy ----------------
            wake._context_engine._state = np.zeros(  # noqa: SLF001
                CONFIG.embedding_dim, dtype=np.float32,
            )
            out_zero = wake._retrieve_episodes(common_task)  # noqa: SLF001
            zero_ids = [ep.id for ep, _ in out_zero if ep.outcome == "success"]
            legacy = mem.recall(
                common_task, k=wake.cfg.episodes_recall_k,
                outcome_filter="success",
            )
            legacy_ids = [ep.id for ep, _ in legacy]
            zero_matches_legacy = (
                zero_ids[:len(legacy_ids)] == legacy_ids
            )

            # ---- Dimension 3: latency overhead -----------------
            timings_ctx: list[float] = []
            timings_no: list[float] = []
            for j in range(20):
                wake._context_engine._state = ctx_a_list[j % n].copy()  # noqa: SLF001
                t0 = time.perf_counter()
                wake._retrieve_episodes(common_task)  # noqa: SLF001
                timings_ctx.append((time.perf_counter() - t0) * 1000.0)
                wake._context_engine._state = np.zeros(  # noqa: SLF001
                    CONFIG.embedding_dim, dtype=np.float32,
                )
                t0 = time.perf_counter()
                wake._retrieve_episodes(common_task)  # noqa: SLF001
                timings_no.append((time.perf_counter() - t0) * 1000.0)
            med_ctx = float(np.median(timings_ctx))
            med_no = float(np.median(timings_no))
            overhead = med_ctx - med_no
        finally:
            object.__setattr__(CONFIG, "tcm_cross_session_enabled", saved_xs)
            object.__setattr__(CONFIG, "tcm_recall_context_weight", saved_w)
            object.__setattr__(CONFIG, "forward_replay_include_failures", saved_replay)
    finally:
        wake = None  # type: ignore[assignment]  # noqa: F841
        mem = None  # type: ignore[assignment]  # noqa: F841
        gc.collect()
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("Bench: wake cross-session context (20 paired episodes A/B)")
    print()
    print(f"  matched A-context retrieve top-1: {rate_drifted:.2f} "
          f"({match}/{n})  (target ≥ 0.85)")
    print()
    print(f"  zero-state preserves legacy ordering: {zero_matches_legacy}")
    print()
    print("  latency (median over 20 runs):")
    print(f"    no-context retrieve: {med_no:.2f} ms")
    print(f"    context retrieve:    {med_ctx:.2f} ms")
    print(f"    overhead:            {overhead:+.2f} ms (target ≤ 5 ms)")
    print()
    print("Verdict (3 dimensions):")
    d1 = rate_drifted >= 0.85
    d2 = bool(zero_matches_legacy)
    d3 = overhead <= 5.0
    print(f"  matched-context ≥ 0.85:    {'+' if d1 else '!'}")
    print(f"  zero-state legacy compat:  {'+' if d2 else '!'}")
    print(f"  latency overhead ≤ 5 ms:   {'+' if d3 else '!'}")
    return 0 if (d1 and d2 and d3) else 1


if __name__ == "__main__":
    sys.exit(main())
