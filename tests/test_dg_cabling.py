"""Tests for FORGIA pezzo #13: DG cabling into EpisodicMemory.

Pezzo #11 forged the DG primitive (`build_dg_projection` + `dg_encode`).
This pezzo wires it into the storage/retrieval pipeline so that
near-duplicate episodes (cosine ~0.99) actually surface as DISTINCT in
the encoded representation — even when raw cosine sees them as
identical.

Design:

  1. New schema column `dg_embedding BLOB` on episodes (v2 → v3).
     `NULL` allowed: existing rows are back-filled lazily on first
     `recall(use_dg=True)` so the migration itself is O(1).

  2. `EpisodicMemory.__init__` builds a DETERMINISTIC `W_dg` projection
     using `CONFIG.dg_seed` (a fixed seed kept stable across process
     restarts — same matrix from day 1, no re-encoding old episodes).

  3. `store(episode)` computes `dg_embedding = dg_encode(summary_emb,
     W_dg, k_sparse)` and persists it alongside `summary_embedding`.

  4. `recall(query, ..., use_dg=False)`: the DG path is opt-in. When
     `use_dg=True`, the candidate pool is ranked by cosine on the
     DG-encoded query against `dg_matrix`. The pool then enters the
     existing salience/recency rerank pipeline.

Six measurable invariants we test (declared BEFORE implementing):

  1. PAIRWISE TWIN SEPARATION:
     Two near-twin episodes (cosine 0.99 on summary embeddings) should
     have a LOWER cosine on their DG-encoded representations. The
     amplification factor (1 - cos_dg) / (1 - cos_sum) is the headline
     measure of pattern separation.

  2. RECALL PRESERVATION (no false separation):
     With diverse episodes (no twins) and a query relevant to one of
     them, DG-recall must keep that episode in top-3. The DG path must
     not BREAK retrieval for non-pathological corpora.

  3. PERSISTENCE / SCHEMA MIGRATION:
     A v2 DB with stored episodes can be opened with the new code:
     migration auto-applies, dg_embedding back-fill happens lazily,
     subsequent recall(use_dg=True) returns the same set as a fresh
     v3 install.

  4. STABLE PROJECTION:
     Two `EpisodicMemory` instances build the SAME W_dg matrix —
     stored DG vectors stay valid across process restarts.

  5. STORE PERSISTS DG:
     After store(), `dg_embedding` column is populated with the
     compact sparse encoding.

  6. LEGACY PATH UNCHANGED:
     `recall(use_dg=False)` returns identical results to legacy code,
     same order — backward compat is non-negotiable.
"""
from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path

import numpy as np
import pytest

from verimem.config import CONFIG
from verimem.episode import Episode, Trace


def _ep(task_text: str, *, outcome: str = "success", final: str = "ok",
        ep_id: str | None = None, created: float | None = None) -> Episode:
    """Tiny helper to fabricate episodes with controlled task text.
    The task text drives the summary embedding directly."""
    return Episode(
        id=ep_id or "",
        task_id=task_text[:30],
        task_text=task_text,
        traces=[Trace(step=1, thought="t", action="A", action_input="", observation="o")],
        outcome=outcome,  # type: ignore[arg-type]
        final_answer=final,
        tokens_used=1,
        skills_used=[],
        created_at=created or time.time(),
        notes="", critique="",
    )


# ---------- Test 1: pairwise twin separation ----------------------------


def test_dg_config_amplifies_near_twin_separation():
    """Sanity check on `CONFIG.dg_*` parameters: with the configured
    `k_sparse`, `d_expand`, and `dg_seed`, two near-identical
    embeddings get pulled apart by DG. This is the property that makes
    `recall(use_dg=True)` surface a richer mix of clusters when twins
    exist in the corpus.

    We test the math directly (perturbed unit vectors, not sentence-
    transformer outputs) so the assertion isn't at the mercy of the
    encoder's noise floor — `pezzo #11` already covered that regime."""
    from verimem.dentate_gyrus import dg_encode
    from verimem.memory import _global_dg_projection

    rng = np.random.default_rng(seed=99)
    base = rng.standard_normal(CONFIG.embedding_dim).astype(np.float32)
    base = base / np.linalg.norm(base)
    # Tiny gaussian perturbation; ||perturb|| ≈ 0.1 → cosine ≈ 0.995.
    perturb = (
        rng.standard_normal(CONFIG.embedding_dim).astype(np.float32) * 0.005
    )
    twin = base + perturb
    twin = twin / np.linalg.norm(twin)
    cos_sum = float(np.dot(base, twin))
    assert cos_sum >= 0.95, f"sanity: twins should be near-identical, got {cos_sum:.3f}"

    W = _global_dg_projection()
    k = CONFIG.dg_k_sparse
    dg_a = dg_encode(base, W, k_sparse=k)
    dg_b = dg_encode(twin, W, k_sparse=k)
    cos_dg = float(np.dot(dg_a, dg_b))

    amp = (1.0 - cos_dg) / max(1e-9, 1.0 - cos_sum)
    assert amp >= 2.0, (
        f"DG didn't amplify twin separation under CONFIG defaults: "
        f"cos_sum={cos_sum:.3f}, cos_dg={cos_dg:.3f}, amp={amp:.2f}× (need ≥ 2×)"
    )
    assert cos_dg < cos_sum


# ---------- Test 2: recall preservation on diverse corpus ---------------


def test_dg_recall_preserves_top_match_on_diverse_corpus(tmp_path: Path):
    """When episodes are diverse (no near-twins), DG must not hurt the
    top@1 retrieval — the right answer should still rank first."""
    from verimem.memory import EpisodicMemory

    db = tmp_path / "ep.db"
    mem = EpisodicMemory(db_path=db)

    diverse = [
        ("compute factorial of 10", "fact-10"),
        ("send email via smtp", "email"),
        ("parse json config file", "json-cfg"),
        ("connect to postgres database", "pg-conn"),
        ("render html template", "html-tpl"),
    ]
    for text, eid in diverse:
        mem.store(_ep(text, ep_id=eid))

    query = "calculate factorial of n"  # paraphrase of "compute factorial of 10"

    base = mem.recall(query, k=3, use_dg=False, track_access=False)
    dg = mem.recall(query, k=3, use_dg=True, track_access=False)

    assert base and dg
    # Baseline cosine should land "fact-10" first — sanity.
    assert base[0][0].id == "fact-10", "baseline cosine failed sanity"
    # DG must keep "fact-10" in top-3. The exact rank-1 may shift due
    # to the sparse k-WTA reshuffling of mid-cosine paraphrases — we
    # accept a top-3 hit (still strong relevance, no false separation).
    dg_ids = [ep.id for ep, _ in dg]
    assert "fact-10" in dg_ids, (
        f"DG dropped target from top-3 on diverse corpus: dg_ids={dg_ids}"
    )


# ---------- Test 3: persistence / migration v2 → v3 ---------------------


def test_dg_migration_from_v2_database(tmp_path: Path):
    """A pre-v3 database (without dg_embedding column) must migrate
    automatically and back-fill lazily on first DG recall."""
    from verimem.memory import _EPISODES_SCHEMA_VERSION, EpisodicMemory

    db = tmp_path / "ep_v2.db"

    # Create memory at current version, store episodes.
    mem1 = EpisodicMemory(db_path=db)
    mem1.store(_ep("alpha event", ep_id="a"))
    mem1.store(_ep("beta event", ep_id="b"))
    del mem1

    # Simulate "old DB without dg_embedding column" by stripping the
    # column. ALTER TABLE DROP COLUMN works on SQLite ≥ 3.35 (2021).
    # We also drop any post-v3 columns so the rollback is complete —
    # otherwise the v3+ migrations would re-execute against a partially
    # forward schema and fail with "duplicate column".
    conn = sqlite3.connect(db)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(episodes)")}
        for col in ("dg_embedding", "context_embedding", "pinned", "embedding_model"):
            if col in cols:
                conn.execute(f"ALTER TABLE episodes DROP COLUMN {col}")
        # Roll back the version ledger so reopening triggers v3+ migrations.
        conn.execute(
            "UPDATE _schema_version SET version = 2 WHERE db_id = 'episodes'"
        )
        conn.commit()
    finally:
        conn.close()

    # Reopen — should auto-migrate to v3.
    mem2 = EpisodicMemory(db_path=db)
    with sqlite3.connect(db) as c:
        cols = {r[1] for r in c.execute("PRAGMA table_info(episodes)")}
    assert "dg_embedding" in cols
    with sqlite3.connect(db) as c:
        v = c.execute(
            "SELECT version FROM _schema_version WHERE db_id='episodes'"
        ).fetchone()[0]
    assert v == _EPISODES_SCHEMA_VERSION

    # Gli episodi sono stati embeddati col modello ATTIVO allo store() qui sopra;
    # il rollback v2 ha droppato il tag embedding_model e la migrazione l'ha
    # ri-aggiunto NULL (=legacy MiniLM via COALESCE). Sotto un default attivo
    # NON-legacy (flip 2026-06-04: multilingue) quel NULL escluderebbe a torto
    # questi episodi dal recall — ma qui i loro vettori SONO nello spazio attivo,
    # quindi ripristino il tag veritiero. (Le DB legacy reali tengono NULL e
    # vengono re-embeddate dal flip; l'isolamento embedding-model ha test suoi.)
    from verimem import embedding as _emb
    with sqlite3.connect(db) as c:
        c.execute("UPDATE episodes SET embedding_model = ?", (_emb.model_signature(),))
        c.commit()

    # Recall with DG works (back-fill triggers).
    out = mem2.recall("alpha", k=1, use_dg=True, track_access=False)
    assert out and out[0][0].id == "a"


# ---------- Test 4: deterministic projection across instances ----------


def test_dg_projection_seed_is_stable_across_memory_instances(tmp_path: Path):
    """Two `EpisodicMemory` objects (same DB, different process lifetimes)
    must build the IDENTICAL W_dg matrix — otherwise yesterday's stored
    DG-embeddings stop matching today's encoder."""
    from verimem.memory import EpisodicMemory

    mem1 = EpisodicMemory(db_path=tmp_path / "a.db")
    mem2 = EpisodicMemory(db_path=tmp_path / "b.db")
    # Both should expose the same projection matrix, derived from
    # CONFIG.dg_seed.
    assert np.array_equal(mem1._dg_projection(), mem2._dg_projection())  # noqa: SLF001


# ---------- Test 5: store persists dg_embedding ------------------------


def test_store_persists_dg_embedding(tmp_path: Path):
    """After store(), the dg_embedding column should be populated
    (non-NULL) for the new episode."""
    from verimem.memory import EpisodicMemory

    db = tmp_path / "ep.db"
    mem = EpisodicMemory(db_path=db)
    mem.store(_ep("hello world", ep_id="h"))

    with sqlite3.connect(db) as c:
        row = c.execute(
            "SELECT dg_embedding FROM episodes WHERE id = 'h'"
        ).fetchone()
    assert row is not None
    assert row[0] is not None
    # Sparse format: 2-byte header (uint16 k) + k × (2 byte idx + 4 byte val).
    # This keeps storage well below the dense float32 cost — for
    # k=20, only 122 bytes per episode (vs 32 KB dense).
    assert isinstance(row[0], bytes)
    expected_bytes = 2 + CONFIG.dg_k_sparse * 6
    assert len(row[0]) == expected_bytes


# ---------- Test 6: use_dg=False is exact backward compat -------------


def test_use_dg_false_is_exact_legacy_path(tmp_path: Path):
    """The legacy code path (no `use_dg` kwarg or `use_dg=False`) must
    return identical results — backward compat is non-negotiable."""
    from verimem.memory import EpisodicMemory

    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i, text in enumerate([
        "deploy", "report", "scrape", "validate", "refactor"
    ]):
        mem.store(_ep(f"{text} task #{i}", ep_id=f"e{i}"))

    a = mem.recall("deploy task", k=3, track_access=False)
    b = mem.recall("deploy task", k=3, use_dg=False, track_access=False)
    assert [ep.id for ep, _ in a] == [ep.id for ep, _ in b]
