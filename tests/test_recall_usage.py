"""Cycle #120 (2026-05-17) — Recall usage observability.

Aurelio direttiva: "memoria AI-driven pilotata da te". Cycle 117 ha
dato visibility (TrustSignal). Ora chiudiamo il loop: l'AI **dichiara**
post-recall quali fact ha usato e quali ha ignorato, con ragione.

Persistito in `recall_usage` (schema v5):
    query, hit_fact_id, used (bool), reason, ts.

Aggregato fornisce signal usage_ratio per fact:
    usage_ratio = times_used / times_recalled.

Fact con usage_ratio basso dopo N recalls (default 5) sono candidati
per stale-degrade o retire — segnale empirico che vale più del solo
age-based decay.

Test plan
---------
1. Schema: `RecallUsageStore` crea tabella idempotently.
2. `record(query, hit_fact_id, used, reason)` persiste 1 riga.
3. `usage_stats(fact_id)` ritorna n_recalled, n_used, ratio.
4. `low_usage_facts(min_recalls=5, max_ratio=0.2)` ritorna candidati
   per future retire.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "verimem.db"


class TestRecallUsageStoreSchema:
    """Schema creation is idempotent."""

    def test_init_creates_table(self, db_path: Path) -> None:
        from verimem.recall_usage import RecallUsageStore
        _ = RecallUsageStore(db_path)
        # Second call should not raise (idempotent CREATE TABLE).
        _ = RecallUsageStore(db_path)


class TestRecord:
    def test_record_persists_row(self, db_path: Path) -> None:
        from verimem.recall_usage import RecallUsageStore
        s = RecallUsageStore(db_path)
        s.record(
            query="X memory", hit_fact_id="f-1", used=True,
            reason="cited verbatim",
        )
        rows = s.all_for_fact("f-1")
        assert len(rows) == 1
        assert rows[0].hit_fact_id == "f-1"
        assert rows[0].used is True
        assert rows[0].reason == "cited verbatim"
        assert rows[0].query == "X memory"

    def test_multiple_records_same_fact(self, db_path: Path) -> None:
        from verimem.recall_usage import RecallUsageStore
        s = RecallUsageStore(db_path)
        for i in range(3):
            s.record(
                query=f"q{i}", hit_fact_id="f-1", used=(i % 2 == 0),
                reason=f"r{i}",
            )
        rows = s.all_for_fact("f-1")
        assert len(rows) == 3


class TestUsageStats:
    def test_zero_when_no_records(self, db_path: Path) -> None:
        from verimem.recall_usage import RecallUsageStore
        s = RecallUsageStore(db_path)
        stats = s.usage_stats("f-never")
        assert stats["n_recalled"] == 0
        assert stats["n_used"] == 0
        assert stats["ratio"] == 0.0

    def test_ratio_computation(self, db_path: Path) -> None:
        from verimem.recall_usage import RecallUsageStore
        s = RecallUsageStore(db_path)
        # 5 recalls, 1 used → ratio 0.2
        for i in range(5):
            s.record(
                query=f"q{i}", hit_fact_id="f-1", used=(i == 0),
                reason="",
            )
        stats = s.usage_stats("f-1")
        assert stats["n_recalled"] == 5
        assert stats["n_used"] == 1
        assert abs(stats["ratio"] - 0.2) < 1e-9


class TestLowUsageFacts:
    def test_low_usage_filter(self, db_path: Path) -> None:
        from verimem.recall_usage import RecallUsageStore
        s = RecallUsageStore(db_path)
        # f-low: 6 recalls 1 used (ratio 0.17 < 0.2)
        for i in range(6):
            s.record(query=f"q{i}", hit_fact_id="f-low",
                     used=(i == 0), reason="")
        # f-high: 6 recalls 5 used (ratio 0.83)
        for i in range(6):
            s.record(query=f"q{i}", hit_fact_id="f-high",
                     used=(i < 5), reason="")
        # f-few: only 2 recalls (below min_recalls threshold)
        for i in range(2):
            s.record(query=f"q{i}", hit_fact_id="f-few",
                     used=False, reason="")

        candidates = s.low_usage_facts(min_recalls=5, max_ratio=0.2)
        ids = {c["fact_id"] for c in candidates}
        assert "f-low" in ids
        assert "f-high" not in ids
        # f-few has only 2 recalls — below min_recalls, must be excluded.
        assert "f-few" not in ids


class TestRecordBatch:
    """Convenience helper to record a whole recall set at once."""

    def test_record_batch(self, db_path: Path) -> None:
        from verimem.recall_usage import RecallUsageStore
        s = RecallUsageStore(db_path)
        usage_decisions = [
            ("f-1", True, "matched"),
            ("f-2", False, "stale"),
            ("f-3", True, ""),
        ]
        s.record_batch(query="X", decisions=usage_decisions)
        assert len(s.all_for_fact("f-1")) == 1
        assert len(s.all_for_fact("f-2")) == 1
        assert len(s.all_for_fact("f-3")) == 1
        assert s.usage_stats("f-1")["n_used"] == 1
        assert s.usage_stats("f-2")["n_used"] == 0
