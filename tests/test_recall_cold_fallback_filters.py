"""recall()'s cold-encode keyword fallback must apply the SAME default-view
filters as the warm paths (correctness-hunt #3, HIGH-1).

When the query-encode budget overruns (cold/contended encode daemon — the
exact degraded path the circuit-breaker exists for), recall() delegates to
search_facts(), which only drops superseded + orphaned/quarantined. The two
warm paths ALSO hide: stale-aged facts (freshness cutoff), unverified
writer_role='conversational_promotion' rows (anti-laundering), and — for a
generic topic=None recall — telemetry-namespace blobs. So the SAME recall()
returned a strictly larger, lower-trust set under load. Fix: the fallback
applies those three filters in Python (oversampling to compensate).

RED marker: pre-fix the cold fallback surfaces a stale / conversational /
telemetry fact that the warm recall hides.
"""
from __future__ import annotations

import time
from pathlib import Path

# Single import style (CodeQL): we need the module handle for
# monkeypatch.setattr(sem, ...), so Fact/SemanticMemory are reached via `sem.`.
import engram.semantic as sem

_QUERY = "does the widget pipeline still deploy via the foo endpoint"


def _force_cold(monkeypatch) -> None:
    """Make the query-encode return None so recall() takes the keyword fallback."""
    monkeypatch.setattr(sem, "_encode_prepared_within_budget",
                        lambda *a, **k: None)


def _ids(hits) -> set[str]:
    return {f.id for f, _ in hits}


def test_cold_fallback_excludes_stale(tmp_path: Path, monkeypatch) -> None:
    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    sm.store(sem.Fact(id="fresh", proposition="widget pipeline deploys via foo",
                  topic="cap/x", created_at=now, last_verified_at=now),
             embed="defer")
    sm.store(sem.Fact(id="stale", proposition="widget pipeline deploys via foo",
                  topic="cap/x", created_at=now - 400 * 86400,
                  last_verified_at=now - 400 * 86400), embed="defer")
    _force_cold(monkeypatch)
    got = _ids(sm.recall(_QUERY, k=10))
    assert "fresh" in got
    assert "stale" not in got, "cold fallback must hide a stale fact like warm recall"


def test_cold_fallback_excludes_unverified_conversational(
    tmp_path: Path, monkeypatch,
) -> None:
    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    sm.store(sem.Fact(id="ok", proposition="widget pipeline deploys via foo",
                  topic="cap/x", created_at=now, last_verified_at=now),
             embed="defer")
    sm.store(sem.Fact(id="conv", proposition="widget pipeline deploys via foo",
                  topic="cap/x", created_at=now, last_verified_at=now,
                  writer_role="conversational_promotion", status="model_claim"),
             embed="defer")
    _force_cold(monkeypatch)
    got = _ids(sm.recall(_QUERY, k=10))
    assert "ok" in got
    assert "conv" not in got, (
        "cold fallback must hide an unverified conversational_promotion fact"
    )


def test_cold_fallback_excludes_telemetry_on_generic_recall(
    tmp_path: Path, monkeypatch,
) -> None:
    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    sm.store(sem.Fact(id="real", proposition="widget pipeline deploys via foo",
                  topic="cap/x", created_at=now, last_verified_at=now),
             embed="defer")
    sm.store(sem.Fact(id="tel", proposition="widget pipeline deploys via foo",
                  topic="bus/events", created_at=now, last_verified_at=now),
             embed="defer")
    _force_cold(monkeypatch)
    got = _ids(sm.recall(_QUERY, k=10))  # topic=None generic recall
    assert "real" in got
    assert "tel" not in got, "generic cold fallback must hide telemetry topics"


def test_cold_fallback_conversational_verified_kept(
    tmp_path: Path, monkeypatch,
) -> None:
    """A VERIFIED conversational fact is NOT laundered — it stays.

    The store's verified_by hard-gate (v2) demotes a conversational_promotion
    stored as 'verified' WITHOUT a verification ref back to 'model_claim'. That
    gate is store-side and orthogonal to the recall filter under test here, so
    we force the persisted status to 'verified' directly and assert the recall
    cold-fallback keeps it (only the UNVERIFIED conversational class is hidden).
    """
    import sqlite3

    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    sm.store(sem.Fact(id="cv", proposition="widget pipeline deploys via foo",
                  topic="cap/x", created_at=now, last_verified_at=now,
                  writer_role="conversational_promotion", status="model_claim"),
             embed="defer")
    with sqlite3.connect(str(sm.db_path)) as c:
        c.execute("UPDATE facts SET status='verified' WHERE id='cv'")
        c.commit()
    _force_cold(monkeypatch)
    got = _ids(sm.recall(_QUERY, k=10))
    assert "cv" in got, "a VERIFIED conversational fact must be kept"
