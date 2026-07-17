"""FORGIA pezzo #224 — Wave 23: outcome timeseries.

Per-day (or per-week) success/failure breakdown across episodes.
Powers the "trends over time" view: are we improving?

Bucketing: bucket="day" → 86400s windows; bucket="week" → 7-day.
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _FakeEp:
    outcome: str = "success"
    created_at: float = 0.0


def test_empty_returns_empty_buckets():
    from verimem.outcome_timeseries import outcome_timeseries

    out = outcome_timeseries([])
    assert out["buckets"] == []
    assert out["bucket_kind"] in ("day", "week")


def test_one_bucket_per_day():
    from verimem.outcome_timeseries import outcome_timeseries

    # CYCLE #15 fix: usa timestamp DETERMINISTICO (mezzogiorno UTC fissato)
    # invece di time.time(). Con time.time() il test era brittle: se 'now'
    # cade vicino a midnight UTC, base-86400-100 può finire 2 giorni prima
    # invece di 1, producendo 3 bucket invece dei 2 attesi.
    # Fissato a 2026-01-15 12:00:00 UTC (lontano da midnight boundaries).
    base = 1_768_521_600.0  # 2026-01-15 12:00:00 UTC (mezzogiorno, no boundary issue)
    eps = [
        _FakeEp("success", created_at=base),
        _FakeEp("success", created_at=base + 3600),  # same day
        _FakeEp("failure", created_at=base - 86400 - 100),  # day before
    ]
    # window_days alto per non scartare il timestamp deterministico.
    out = outcome_timeseries(eps, bucket="day", window_days=99999)
    # We see 2 distinct days.
    assert len(out["buckets"]) == 2


def test_success_failure_counts_per_bucket():
    from verimem.outcome_timeseries import outcome_timeseries

    base = time.time()
    eps = [
        _FakeEp("success", created_at=base),
        _FakeEp("success", created_at=base + 60),
        _FakeEp("failure", created_at=base + 120),
    ]
    out = outcome_timeseries(eps, bucket="day")
    # All on the same day.
    assert len(out["buckets"]) == 1
    bucket = out["buckets"][0]
    assert bucket["n_success"] == 2
    assert bucket["n_failure"] == 1


def test_window_days_filters_old():
    from verimem.outcome_timeseries import outcome_timeseries

    base = time.time()
    eps = [
        _FakeEp("success", created_at=base),
        _FakeEp("failure", created_at=base - 86400 * 100),  # 100 days ago
    ]
    out = outcome_timeseries(eps, bucket="day", window_days=30)
    # Only the recent one survives.
    assert len(out["buckets"]) == 1
    assert out["buckets"][0]["n_success"] == 1


def test_buckets_sorted_chronologically():
    from verimem.outcome_timeseries import outcome_timeseries

    base = time.time()
    eps = [
        _FakeEp("success", created_at=base - 86400 * 5),
        _FakeEp("success", created_at=base - 86400 * 1),
        _FakeEp("success", created_at=base - 86400 * 3),
    ]
    out = outcome_timeseries(eps, bucket="day")
    starts = [b["bucket_start"] for b in out["buckets"]]
    assert starts == sorted(starts)


def test_includes_date_str():
    from verimem.outcome_timeseries import outcome_timeseries

    eps = [_FakeEp("success", created_at=time.time())]
    out = outcome_timeseries(eps)
    assert "date" in out["buckets"][0]
    # ISO format YYYY-MM-DD prefix.
    assert len(out["buckets"][0]["date"]) >= 10


def test_week_bucketing():
    """Two events 3 days apart should land in the same week bucket.

    Brittleness fix (cycle #88-CI 2026-05-16): the previous version used
    ``time.time()`` as base, so when the run happened on Fri/Sat/Sun the
    ``base + 3 days`` event crossed an ISO-week boundary and produced 2
    buckets instead of 1. We now floor ``time.time()`` to the current
    week's Monday 00:00 UTC so:
      * ``base`` always lands on a Monday (within window).
      * ``base + 3 days`` always lands on the Thursday of the same week.
    """
    from datetime import datetime, timedelta, timezone

    from verimem.outcome_timeseries import outcome_timeseries

    now_dt = datetime.now(timezone.utc)
    monday_dt = (now_dt - timedelta(days=now_dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    base = monday_dt.timestamp()
    eps = [
        _FakeEp("success", created_at=base),
        _FakeEp("success", created_at=base + 86400 * 3),
    ]
    out = outcome_timeseries(eps, bucket="week", window_days=30)
    # Single week bucket.
    assert len(out["buckets"]) == 1
    assert out["buckets"][0]["n_success"] == 2


def test_payload_shape_complete():
    from verimem.outcome_timeseries import outcome_timeseries

    out = outcome_timeseries([])
    for k in ("buckets", "bucket_kind", "window_days"):
        assert k in out
