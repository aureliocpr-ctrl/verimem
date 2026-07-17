"""backfill_pending_embeddings must self-heal model-mismatched rows, not just
empty (length-0) blobs (structural-safety hardening, 2026-06-13).

Root cause measured live: 405/5073 live facts were invisible to e5 recall.
Only 108 had an empty blob (the case backfill_pending_embeddings covered);
287 had a 768-d e5 blob with NULL embedding_model, and 10 had a 384-d MiniLM
blob — both excluded by the per-row recall filter
``COALESCE(embedding_model, legacy) = active``, and NEITHER ever auto-healed,
because the daemon only re-embedded ``length(embedding) = 0`` rows. So a fact
saved by ANY path that wrote the wrong model (or no label) stayed silently
unrecallable forever. The robust fix: the backfill heals any STALE row —
wrong dim OR wrong/absent model — by re-encoding from the proposition with
the active model. Idempotent; never re-touches an already-active row.

RED marker: pre-fix backfill_pending_embeddings() returns 0 (leaves stale)
for a row with a non-empty blob whose embedding_model != active.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from verimem.semantic import Fact, SemanticMemory


def _ids(results) -> list[str]:
    out: list[str] = []
    for r in results or []:
        f = r[0] if isinstance(r, (tuple, list)) else r
        fid = getattr(f, "id", None)
        if fid is not None:
            out.append(fid)
    return out


def _corrupt(db: Path, fid: str, *, model: str, blob: bytes | None = None) -> None:
    """Simulate a fact persisted by a path that wrote the wrong model/dim."""
    with sqlite3.connect(str(db)) as c:
        if blob is None:
            c.execute("UPDATE facts SET embedding_model=? WHERE id=?", (model, fid))
        else:
            c.execute(
                "UPDATE facts SET embedding_model=?, embedding=? WHERE id=?",
                (model, blob, fid),
            )
        c.commit()


def test_backfill_heals_wrong_model_label(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    m = SemanticMemory(db_path=db)
    f = Fact(proposition="Healable fact about 321 turbines.", topic="eng/h")
    m.store(f)  # sync -> active embedding, recallable
    _corrupt(db, f.id, model="stale/old-model")  # right blob, WRONG label
    m2 = SemanticMemory(db_path=db)  # fresh read, no stale corpus cache
    assert f.id not in _ids(m2.recall("turbines", k=10)), (
        "a wrong-model row must be excluded from recall (precondition)"
    )
    assert m2.backfill_pending_embeddings() == 1, (
        "backfill must HEAL a wrong-model row, not only empty blobs"
    )
    assert f.id in _ids(m2.recall("turbines", k=10)), "healed row is recallable"
    assert m2.backfill_pending_embeddings() == 0, "idempotent once healed"


def test_backfill_heals_null_embedding_model(tmp_path: Path) -> None:
    """The live root case: clp save omitted the embedding_model column, so it
    was SQL NULL (not '' / a wrong string). COALESCE(NULL, legacy) != active,
    so recall excludes it and backfill must heal it. Guards the three-valued-
    logic edge the adversarial review flagged."""
    db = tmp_path / "s.db"
    m = SemanticMemory(db_path=db)
    f = Fact(proposition="Null-model fact about 246 valves.", topic="eng/n")
    m.store(f)  # active
    with sqlite3.connect(str(db)) as c:
        c.execute("UPDATE facts SET embedding_model = NULL WHERE id = ?", (f.id,))
        c.commit()
    m2 = SemanticMemory(db_path=db)
    assert f.id not in _ids(m2.recall("valves", k=10)), (
        "a NULL-model row must be excluded from recall (precondition)"
    )
    assert m2.backfill_pending_embeddings() == 1, "NULL model must heal"
    assert f.id in _ids(m2.recall("valves", k=10))


def test_backfill_heals_wrong_dim_blob(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    m = SemanticMemory(db_path=db)
    f = Fact(proposition="Wrong-dim fact with 88 gears.", topic="eng/d")
    m.store(f)
    _corrupt(db, f.id, model="legacy/minilm", blob=b"\x00" * 16)  # 16B != active
    m2 = SemanticMemory(db_path=db)
    assert f.id not in _ids(m2.recall("gears", k=10))
    assert m2.backfill_pending_embeddings() == 1
    assert f.id in _ids(m2.recall("gears", k=10))


def test_backfill_leaves_active_rows_untouched(tmp_path: Path) -> None:
    """No churn: an already-active row is never re-encoded (returns 0)."""
    db = tmp_path / "s.db"
    m = SemanticMemory(db_path=db)
    m.store(Fact(proposition="Already active, 5 rotors.", topic="eng/ok"))
    assert m.backfill_pending_embeddings() == 0


def test_backfill_still_heals_empty_blob(tmp_path: Path) -> None:
    """Regression: the original deferred (empty-blob) case still works."""
    db = tmp_path / "s.db"
    m = SemanticMemory(db_path=db)
    f = Fact(proposition="Deferred fact, 777 tokens.", topic="eng/y")
    m.store(f, embed="defer")  # empty blob
    assert m.backfill_pending_embeddings() == 1
    assert f.id in _ids(m.recall("tokens deferred", k=10))
