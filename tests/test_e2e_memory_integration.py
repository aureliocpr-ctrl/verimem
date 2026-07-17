"""End-to-end integration smoke test for FORGIA pezzi #13–#25.

The recall pipeline now exposes (cosine, DG, Hopfield) ranking
modes and (salience, recency, context) re-rank dimensions. These
have been tested in isolation. This file confirms the WHOLE
machinery composes coherently on a representative corpus — a
regression guard against future changes silently breaking some
combination.

What we verify in this single test:

  1. STORE WITH FULL CARGO: episodes are stored with
     summary_embedding, dg_embedding (sparse), context_embedding,
     salience_score (cached), and standard fields. Schema v4 is
     stamped.

  2. ALL RECALL FLAGS COMPOSE: a single `recall()` call with
     `use_dg=True`, `salience_weight>0`, `recency_weight>0`,
     `context_emb=...`, `context_weight>0` returns a sensible
     non-empty result. No crash, no NaN.

  3. SISTER APIs WORK: `recall_by_context` and
     `WakeAgent.predict_next_skill` work on the same corpus.

  4. CONTEXT LIFECYCLE: reset/checkpoint/restore roundtrip works.

  5. SR + DG INDICES BUILD: `_ensure_dg_index`, build_successor_matrix
     all run without error on the corpus.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from verimem.config import CONFIG
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(*, ep_id: str, text: str, skills: list[str] | None = None,
        outcome: str = "success") -> Episode:
    return Episode(
        id=ep_id, task_id=text[:30], task_text=text,
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="search",
                      action_input="", observation="result")],
        tokens_used=1,
        skills_used=skills or [],
        created_at=time.time(),
    )


def test_full_pipeline_smoke(tmp_path: Path):
    """A single test that exercises every cabled primitive together."""
    from verimem.successor_repr import (
        build_successor_matrix,
        cluster_by_sr_similarity,
    )
    from verimem.wake import WakeAgent, WakeConfig

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")

    # --- Store a representative corpus ---------------------------------
    rng = np.random.default_rng(seed=20260508)
    diverse_tasks = [
        ("compute factorial of n", "fact"),
        ("send email via smtp", "email"),
        ("parse json file", "json"),
        ("connect postgres database", "pg"),
        ("render html template", "html"),
    ]
    contexts = [
        rng.standard_normal(CONFIG.embedding_dim).astype(np.float32)
        for _ in range(len(diverse_tasks))
    ]
    contexts = [c / np.linalg.norm(c) for c in contexts]

    for (text, eid), ctx in zip(diverse_tasks, contexts, strict=True):
        mem.store(
            _ep(ep_id=eid, text=text, skills=["A", "B"]),
            context_emb=ctx,
        )
    # Also a no-context legacy episode.
    mem.store(_ep(ep_id="legacy", text="legacy with no context", skills=[]))
    # And a failure for forward_replay.
    mem.store(_ep(
        ep_id="fail",
        text="failed factorial computation",
        outcome="failure", skills=["A"],
    ))

    # --- Schema must be at the current target version ------------------
    from verimem.memory import _EPISODES_SCHEMA_VERSION
    from verimem.migrations import schema_version
    with mem._connect() as c:  # noqa: SLF001
        v = schema_version(c, "episodes")
    assert v == _EPISODES_SCHEMA_VERSION, (
        f"schema not at current version: got {v}, "
        f"expected {_EPISODES_SCHEMA_VERSION}"
    )

    # --- Full recall with every flag composed together -----------------
    out = mem.recall(
        "calculate factorial of integer",
        k=3,
        use_dg=True,
        salience_weight=0.20,
        recency_weight=0.10,
        recency_tau_s=7 * 86400.0,
        context_emb=contexts[0],
        context_weight=0.30,
        track_access=False,
    )
    assert out, "composed recall returned empty"
    out_ids = [ep.id for ep, score in out]
    assert "fact" in out_ids[:3], f"factorial not in top-3: {out_ids}"
    # No NaN scores.
    for _, score in out:
        assert np.isfinite(score)

    # --- recall_by_context works on the same corpus --------------------
    ctx_results = mem.recall_by_context(contexts[0], k=2)
    ctx_ids = [ep.id for ep, _ in ctx_results]
    assert ctx_ids[0] == "fact", (
        f"recall_by_context didn't pick the matching ctx: {ctx_ids}"
    )
    # Legacy (no context) episode must NOT appear.
    assert "legacy" not in ctx_ids

    # --- SR primitives build without error on the corpus --------------
    skill_seqs = [ep.skills_used for ep in mem.all() if ep.skills_used]
    ids, M = build_successor_matrix(skill_seqs, gamma=0.85)
    assert len(ids) >= 2  # ['A', 'B']
    assert M.shape[0] == len(ids)
    sr_clusters = cluster_by_sr_similarity(ids, M, threshold=0.5)
    assert sr_clusters  # at least one cluster

    # --- WakeAgent context lifecycle + predict_next_skill -------------
    wake = object.__new__(WakeAgent)
    wake.memory = mem  # type: ignore[misc]
    wake.cfg = WakeConfig(max_steps=4, self_critique=False)
    # predict_next_skill uses the corpus we just stored.
    nxt = wake.predict_next_skill(["A"], top_k=1)
    assert nxt == ["B"], f"expected next 'B' (5 of 7 episodes go A→B): {nxt}"

    # Context lifecycle:
    wake.restore_context(contexts[2])  # set
    snap = wake.checkpoint_context()
    assert np.array_equal(snap, contexts[2])
    wake.reset_context()
    assert float(np.linalg.norm(wake.checkpoint_context())) == 0.0
    wake.restore_context(snap)
    assert np.array_equal(wake._context_engine.state, snap)  # noqa: SLF001

    # --- DG index can be built (lazy back-fill triggers) -------------
    ids_dg, dg_matrix = mem._ensure_dg_index()  # noqa: SLF001
    assert len(ids_dg) == 7  # 5 diverse + legacy + fail
    assert dg_matrix.shape == (7, CONFIG.dg_d_expand)
