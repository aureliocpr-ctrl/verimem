"""Cycle #54 — tests for briefing_stats observability."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from verimem.briefing_stats import compute_stats


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def test_stats_no_file_returns_defaults(tmp_path: Path) -> None:
    out = compute_stats(tmp_path / "nope.jsonl")
    assert out["ok"] is True
    assert out["n_firings"] == 0
    assert out["hit_rate"] == 0.0
    assert out["suggested_min_matched"] == 2


def test_stats_aggregates_records(tmp_path: Path) -> None:
    path = tmp_path / "b.jsonl"
    now = time.time()
    _write_jsonl(path, [
        {"ts": now, "prompt_excerpt": "a", "n_keywords": 5,
         "n_hits": 2, "n_dup_filtered": 0,
         "top_matched": 3, "top_id": "f1",
         "min_matched_used": 2, "latency_ms": 12.0},
        {"ts": now, "prompt_excerpt": "b", "n_keywords": 4,
         "n_hits": 0, "n_dup_filtered": 1,
         "top_matched": 0, "top_id": "",
         "min_matched_used": 2, "latency_ms": 8.0},
        {"ts": now, "prompt_excerpt": "c", "n_keywords": 6,
         "n_hits": 3, "n_dup_filtered": 0,
         "top_matched": 4, "top_id": "f5",
         "min_matched_used": 2, "latency_ms": 15.0},
    ])
    out = compute_stats(path)
    assert out["ok"] is True
    assert out["n_firings"] == 3
    assert out["n_zero_hits"] == 1
    assert out["n_dup_filtered_total"] == 1
    # hit_rate is rounded to 3 decimals (observability tolerance)
    assert abs(out["hit_rate"] - 2 / 3) < 1e-3
    assert out["avg_keywords"] == 5.0
    # Latencies: 8,12,15 sorted; p50=12, p95=15 (interpolated near 15)
    assert out["p50_latency_ms"] == 12.0
    # Histogram: top_matched={3,4} once each (zero excluded)
    assert out["top_matched_histogram"] == {3: 1, 4: 1}


def test_stats_suggests_lower_threshold_on_low_hit_rate(
    tmp_path: Path,
) -> None:
    """When most firings have 0 hits, suggest lowering min_matched."""
    path = tmp_path / "b.jsonl"
    records = []
    # 10 firings, only 1 with hits → hit_rate = 10%
    for i in range(10):
        records.append({
            "ts": time.time(), "prompt_excerpt": f"p{i}",
            "n_keywords": 5,
            "n_hits": 1 if i == 0 else 0,
            "n_dup_filtered": 0,
            "top_matched": 2 if i == 0 else 0,
            "top_id": "x" if i == 0 else "",
            "min_matched_used": 3, "latency_ms": 10.0,
        })
    _write_jsonl(path, records)
    out = compute_stats(path)
    assert out["hit_rate"] == 0.1
    assert out["suggested_min_matched"] == 2  # current 3 - 1


def test_stats_suggests_raise_threshold_on_high_quality_hits(
    tmp_path: Path,
) -> None:
    """When hit_rate is high AND many hits have top_matched > current+1,
    suggest raising min_matched to be more selective."""
    path = tmp_path / "b.jsonl"
    records = []
    # 10 firings all hit, all with top_matched=5 (very high)
    for i in range(10):
        records.append({
            "ts": time.time(), "prompt_excerpt": f"p{i}",
            "n_keywords": 7,
            "n_hits": 2,
            "n_dup_filtered": 0,
            "top_matched": 5,
            "top_id": f"f{i}",
            "min_matched_used": 2, "latency_ms": 10.0,
        })
    _write_jsonl(path, records)
    out = compute_stats(path)
    assert out["hit_rate"] == 1.0
    assert out["suggested_min_matched"] == 3  # raise from 2 to 3


def test_stats_max_records_tail(tmp_path: Path) -> None:
    """Only the last `max_records` lines are aggregated."""
    path = tmp_path / "b.jsonl"
    records = []
    # 100 records, first 90 with 0 hits, last 10 with hits
    for i in range(100):
        records.append({
            "ts": time.time(), "prompt_excerpt": f"p{i}",
            "n_keywords": 5,
            "n_hits": 1 if i >= 90 else 0,
            "n_dup_filtered": 0,
            "top_matched": 3 if i >= 90 else 0,
            "top_id": "x" if i >= 90 else "",
            "min_matched_used": 2, "latency_ms": 10.0,
        })
    _write_jsonl(path, records)
    out = compute_stats(path, max_records=10)
    # Only last 10 considered: all have hits
    assert out["n_firings"] == 10
    assert out["hit_rate"] == 1.0


def test_stats_handles_malformed_lines(tmp_path: Path) -> None:
    """Malformed JSON lines are silently skipped, no crash."""
    path = tmp_path / "b.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write('{"ts":1,"n_hits":1,"top_matched":2,"min_matched_used":2,"latency_ms":10}\n')
        f.write("NOT JSON\n")
        f.write('{"ts":2,"n_hits":0,"top_matched":0,"min_matched_used":2,"latency_ms":12}\n')
    out = compute_stats(path)
    assert out["ok"] is True
    assert out["n_firings"] == 2  # malformed skipped
