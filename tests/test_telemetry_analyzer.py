"""Cycle #115.A — Analyzer for mcp_audit.log → ROI tabular report.

The MCP server logs one JSONL record per call (`<engram>/mcp_audit.log`).
Cycle #115.A added `latency_ms`. This analyzer reads the file and
produces a per-tool aggregate:

    { tool: { count, latency_p50_ms, latency_p99_ms, latency_max_ms,
              n_unique_pids, outcomes: {ok: int, rejected_*: int, ...} } }

plus a totals section. Used by `scripts/analyze_telemetry.py` to show
"how often is each MCP tool actually called, and how long does it take".
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _write_log(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


class TestAnalyzeEmpty:
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        from engram.telemetry_analyzer import analyze_audit_log
        report = analyze_audit_log(tmp_path / "missing.log")
        assert report["total_calls"] == 0
        assert report["per_tool"] == {}

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        from engram.telemetry_analyzer import analyze_audit_log
        p = tmp_path / "empty.log"
        p.write_text("", encoding="utf-8")
        report = analyze_audit_log(p)
        assert report["total_calls"] == 0


class TestAnalyzeCounts:
    def test_counts_per_tool(self, tmp_path: Path) -> None:
        from engram.telemetry_analyzer import analyze_audit_log
        p = tmp_path / "log.jsonl"
        _write_log(p, [
            {"ts": 1, "tool": "hippo_recall", "caller_pid": 100,
             "args_hash": "a", "outcome": "ok", "error": "",
             "latency_ms": 12.0},
            {"ts": 2, "tool": "hippo_recall", "caller_pid": 100,
             "args_hash": "b", "outcome": "ok", "error": "",
             "latency_ms": 22.0},
            {"ts": 3, "tool": "hippo_remember", "caller_pid": 200,
             "args_hash": "c", "outcome": "ok", "error": "",
             "latency_ms": 5.0},
        ])

        report = analyze_audit_log(p)
        assert report["total_calls"] == 3
        assert report["per_tool"]["hippo_recall"]["count"] == 2
        assert report["per_tool"]["hippo_remember"]["count"] == 1


class TestAnalyzeLatencyPercentiles:
    def test_p50_and_p99(self, tmp_path: Path) -> None:
        from engram.telemetry_analyzer import analyze_audit_log
        p = tmp_path / "log.jsonl"
        # 100 records, latency 1..100ms in order
        records = []
        for i in range(1, 101):
            records.append({
                "ts": float(i), "tool": "hippo_recall",
                "caller_pid": 100, "args_hash": str(i),
                "outcome": "ok", "error": "", "latency_ms": float(i),
            })
        _write_log(p, records)

        report = analyze_audit_log(p)
        rec = report["per_tool"]["hippo_recall"]
        assert rec["count"] == 100
        # p50 ≈ 50 (median of 1..100)
        assert 49.0 <= rec["latency_p50_ms"] <= 51.0
        # p99 ≈ 99
        assert 98.0 <= rec["latency_p99_ms"] <= 100.0
        assert rec["latency_max_ms"] == 100.0

    def test_missing_latency_skipped_safely(self, tmp_path: Path) -> None:
        from engram.telemetry_analyzer import analyze_audit_log
        p = tmp_path / "log.jsonl"
        _write_log(p, [
            {"ts": 1, "tool": "hippo_recall", "caller_pid": 1,
             "args_hash": "a", "outcome": "ok", "error": ""},  # no latency
            {"ts": 2, "tool": "hippo_recall", "caller_pid": 1,
             "args_hash": "b", "outcome": "ok", "error": "",
             "latency_ms": 50.0},
        ])

        report = analyze_audit_log(p)
        rec = report["per_tool"]["hippo_recall"]
        # both calls counted, but percentiles only from the one with latency
        assert rec["count"] == 2
        assert rec["latency_p50_ms"] == 50.0


class TestAnalyzeOutcomes:
    def test_outcomes_breakdown(self, tmp_path: Path) -> None:
        from engram.telemetry_analyzer import analyze_audit_log
        p = tmp_path / "log.jsonl"
        _write_log(p, [
            {"ts": 1, "tool": "hippo_run_task", "caller_pid": 1,
             "args_hash": "a", "outcome": "ok", "error": "",
             "latency_ms": 100.0},
            {"ts": 2, "tool": "hippo_run_task", "caller_pid": 1,
             "args_hash": "b", "outcome": "rejected_empty", "error": "",
             "latency_ms": 1.0},
            {"ts": 3, "tool": "hippo_run_task", "caller_pid": 1,
             "args_hash": "c", "outcome": "rejected_empty", "error": "",
             "latency_ms": 1.0},
        ])

        report = analyze_audit_log(p)
        rec = report["per_tool"]["hippo_run_task"]
        assert rec["outcomes"]["ok"] == 1
        assert rec["outcomes"]["rejected_empty"] == 2


class TestAnalyzeSessions:
    def test_unique_pid_count(self, tmp_path: Path) -> None:
        from engram.telemetry_analyzer import analyze_audit_log
        p = tmp_path / "log.jsonl"
        _write_log(p, [
            {"ts": 1, "tool": "hippo_recall", "caller_pid": 100,
             "args_hash": "a", "outcome": "ok", "error": "",
             "latency_ms": 5.0},
            {"ts": 2, "tool": "hippo_recall", "caller_pid": 200,
             "args_hash": "b", "outcome": "ok", "error": "",
             "latency_ms": 5.0},
            {"ts": 3, "tool": "hippo_recall", "caller_pid": 200,
             "args_hash": "c", "outcome": "ok", "error": "",
             "latency_ms": 5.0},
        ])

        report = analyze_audit_log(p)
        rec = report["per_tool"]["hippo_recall"]
        assert rec["n_unique_pids"] == 2


class TestAnalyzeMalformedLineTolerance:
    """Robustness: a corrupt JSONL line must not crash the analyzer."""

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        from engram.telemetry_analyzer import analyze_audit_log
        p = tmp_path / "log.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            f.write('{"ts": 1, "tool": "hippo_x", "caller_pid": 1, '
                    '"args_hash": "a", "outcome": "ok", "error": "", '
                    '"latency_ms": 5.0}\n')
            f.write("this is not json\n")
            f.write('{"ts": 2, "tool": "hippo_y", "caller_pid": 1, '
                    '"args_hash": "b", "outcome": "ok", "error": "", '
                    '"latency_ms": 7.0}\n')

        report = analyze_audit_log(p)
        assert report["total_calls"] == 2
        assert "hippo_x" in report["per_tool"]
        assert "hippo_y" in report["per_tool"]
