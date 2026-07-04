"""Tests for FORGIA pezzo #25: cabling Hopfield in recall().

Pezzo #10 forged the modern-Hopfield pattern completion primitive
(`hopfield_recall`). It's been usable as a standalone function but
the unified `EpisodicMemory.recall()` couldn't dispatch to it.
This pezzo adds `use_hopfield=True` flag (and `hopfield_beta`)
that delegates internally to `hopfield_recall`.

Three measurable invariants:

  1. KILL-SWITCH OFF: default `use_hopfield=False` is byte-for-byte
     legacy. No regression for existing callers.

  2. KILL-SWITCH ON: with `use_hopfield=True`, recall returns valid
     results — top-1 is in the corpus, results are scored.

  3. HIGH BETA APPROXIMATES COSINE: with β=32 (very concentrated
     attention), the Hopfield top-1 matches the cosine top-1 in
     ≥ 80% of cases (the limit β→∞ is exactly argmax cosine).
"""
from __future__ import annotations

import time
from pathlib import Path

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory


def _ep(*, ep_id: str, text: str) -> Episode:
    return Episode(
        id=ep_id, task_id=text[:30], task_text=text,
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="A",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=time.time(),
    )


# ---------- Test 1: kill-switch off = legacy --------------------------


def test_use_hopfield_false_is_legacy(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i, t in enumerate(["alpha", "beta", "gamma"]):
        mem.store(_ep(ep_id=f"e{i}", text=t))

    a = mem.recall("alpha", k=3, track_access=False)
    b = mem.recall("alpha", k=3, use_hopfield=False, track_access=False)
    assert [ep.id for ep, _ in a] == [ep.id for ep, _ in b]


# ---------- Test 2: kill-switch on returns valid results --------------


def test_use_hopfield_true_returns_valid_results(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i, t in enumerate(["alpha", "beta", "gamma"]):
        mem.store(_ep(ep_id=f"e{i}", text=t))

    out = mem.recall(
        "alpha", k=2, use_hopfield=True, hopfield_beta=8.0,
        track_access=False,
    )
    assert out and len(out) <= 2
    out_ids = {ep.id for ep, _ in out}
    assert out_ids <= {"e0", "e1", "e2"}, f"unknown id in result: {out_ids}"
    # All scores are valid floats.
    for _, score in out:
        assert isinstance(score, float)


# ---------- Test 3: high β approximates cosine -----------------------


def test_high_beta_approximates_cosine(tmp_path: Path):
    """At β=32 the softmax is essentially one-hot at argmax(M @ q),
    so the Hopfield top-1 should equal the cosine top-1."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    diverse = [
        ("compute factorial of 10", "fact"),
        ("send email via smtp", "email"),
        ("parse json file", "json"),
        ("connect postgres database", "pg"),
        ("render html template", "html"),
    ]
    for t, eid in diverse:
        mem.store(_ep(ep_id=eid, text=t))

    queries = [
        "calculate factorial of integer",
        "dispatch email via protocol",
        "read json configuration",
        "postgres connection string",
        "render template html",
    ]
    matches = 0
    for q in queries:
        cos_top = mem.recall(q, k=1, track_access=False)
        hop_top = mem.recall(
            q, k=1, use_hopfield=True, hopfield_beta=32.0,
            track_access=False,
        )
        if cos_top and hop_top and cos_top[0][0].id == hop_top[0][0].id:
            matches += 1
    rate = matches / len(queries)
    assert rate >= 0.80, f"high-β Hopfield diverged from cosine: {matches}/5"


# ---------- Test 4: empty corpus ------------------------------------


def test_use_hopfield_empty_corpus(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    out = mem.recall("anything", k=3, use_hopfield=True, track_access=False)
    assert out == []
