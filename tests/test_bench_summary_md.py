"""FORGIA pezzo #56 — smoke test for `scripts/bench_summary_md.py`.

The renderer turns a `bench_with_without_hippo.summary.json` into a
markdown table for embedding in docs / PR comments. We pin the
output shape so a column rename / reorder doesn't silently break
the docs that depend on it.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bench_summary_md.py"


def test_renders_table(tmp_path: Path):
    payload = {
        "raw|anthropic": {
            "n": 5.0,
            "success_rate": 1.0,
            "mean_tokens": 50.0,
            "mean_latency_s": 0.5,
            "mean_attempts": 1.0,
            "n_errors": 0.0,
        },
        "hippo_warm|anthropic": {
            "n": 5.0,
            "success_rate": 1.0,
            "mean_tokens": 3000.0,
            "mean_latency_s": 2.0,
            "mean_attempts": 1.5,
            "n_errors": 0.0,
        },
    }
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps(payload), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(summary)],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    # Header row present
    assert "provider" in out
    assert "condition" in out
    assert "tokens" in out
    # Both rows present, sorted by provider then condition
    lines = [line for line in out.splitlines() if line.strip().startswith("|")]
    assert len(lines) >= 4  # header + separator + 2 data rows
    # Cells contain expected numbers
    table_text = out
    assert "anthropic" in table_text
    assert "hippo_warm" in table_text
    assert "raw" in table_text


def test_missing_file_returns_nonzero(tmp_path: Path):
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(tmp_path / "nope.json")],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode != 0


def test_empty_file_returns_nonzero(tmp_path: Path):
    """FORGIA pezzo #95: empty file → exit 1, clear stderr message."""
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(empty)],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 1
    assert "empty" in proc.stderr.lower()


def test_corrupt_json_returns_nonzero(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json}", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(bad)],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 1
    assert "valid json" in proc.stderr.lower()


def test_non_object_payload_returns_nonzero(tmp_path: Path):
    listy = tmp_path / "list.json"
    listy.write_text("[1,2,3]", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(listy)],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 1
    assert "json object" in proc.stderr.lower()


def test_tok_success_column_renders(tmp_path: Path):
    """FORGIA pezzo #119: header has 'tok/success'; rendered for present cells."""
    payload = {
        "raw|p1": {
            "n": 5.0, "success_rate": 1.0, "mean_tokens": 100.0,
            "mean_latency_s": 0.5, "mean_attempts": 1.0, "n_errors": 0.0,
            "tokens_per_success": 100.0,
        },
    }
    summary = tmp_path / "s.json"
    summary.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(summary)],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "tok/success" in out


def test_filter_keeps_only_matching_provider(tmp_path: Path):
    """FORGIA pezzo #123: --filter shows only cells of the named provider."""
    payload = {
        "raw|anthropic": {
            "n": 5.0, "success_rate": 1.0, "mean_tokens": 50.0,
            "mean_latency_s": 0.5, "mean_attempts": 1.0, "n_errors": 0.0,
        },
        "raw|deepseek": {
            "n": 5.0, "success_rate": 1.0, "mean_tokens": 47.0,
            "mean_latency_s": 0.7, "mean_attempts": 1.0, "n_errors": 0.0,
        },
    }
    p = tmp_path / "s.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(p), "--filter", "anthropic"],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "anthropic" in out
    assert "deepseek" not in out


def test_filter_no_match_returns_nonzero(tmp_path: Path):
    payload = {
        "raw|anthropic": {
            "n": 5.0, "success_rate": 1.0, "mean_tokens": 50.0,
            "mean_latency_s": 0.5, "mean_attempts": 1.0, "n_errors": 0.0,
        },
    }
    p = tmp_path / "s.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(p), "--filter", "nonexistent"],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 1


def test_sort_by_metric(tmp_path: Path):
    """FORGIA pezzo #127: --sort-by re-orders rows by descending metric."""
    payload = {
        "raw|p_low": {
            "n": 5.0, "success_rate": 0.5, "mean_tokens": 50.0,
            "mean_latency_s": 0.5, "mean_attempts": 1.0, "n_errors": 0.0,
        },
        "raw|p_high": {
            "n": 5.0, "success_rate": 1.0, "mean_tokens": 50.0,
            "mean_latency_s": 5.0, "mean_attempts": 1.0, "n_errors": 0.0,
        },
    }
    p = tmp_path / "s.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(p),
         "--sort-by", "mean_latency_s"],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    # p_high (lat=5.0) appears before p_low (lat=0.5) when sorted desc.
    pos_high = out.find("p_high")
    pos_low = out.find("p_low")
    assert pos_high > 0 and pos_low > 0
    assert pos_high < pos_low


def test_csv_mode_outputs_csv(tmp_path: Path):
    """FORGIA pezzo #105: --csv flag outputs CSV header + rows."""
    payload = {
        "raw|anthropic": {
            "n": 5.0, "success_rate": 1.0, "mean_tokens": 50.0,
            "mean_latency_s": 0.5, "mean_attempts": 1.0, "n_errors": 0.0,
        },
    }
    p = tmp_path / "summary.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(p), "--csv"],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    # CSV header
    assert "provider,condition,n,success_rate" in out
    # Data row, no markdown pipes
    assert "anthropic,raw" in out
    assert "|" not in out  # not the markdown table


def test_renders_by_iter_table(tmp_path: Path):
    """FORGIA pezzo #78: --by-iter uses the by_iter JSON shape."""
    payload = {
        "raw|anthropic|iter0": {
            "n": 5.0, "success_rate": 0.5, "mean_tokens": 50.0,
            "mean_latency_s": 0.5,
        },
        "raw|anthropic|iter1": {
            "n": 5.0, "success_rate": 0.5, "mean_tokens": 50.0,
            "mean_latency_s": 0.4,
        },
        "hippo_warm|anthropic|iter0": {
            "n": 5.0, "success_rate": 1.0, "mean_tokens": 3000.0,
            "mean_latency_s": 4.0,
        },
        "hippo_warm|anthropic|iter1": {
            "n": 5.0, "success_rate": 1.0, "mean_tokens": 3000.0,
            "mean_latency_s": 1.5,
        },
    }
    p = tmp_path / "by_iter.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(p), "--by-iter"],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "iter" in out
    # Both iterations of the warm cell present.
    assert "hippo_warm" in out
    # Anthropic iter=0 latency 4.00s present.
    assert "4.00" in out
